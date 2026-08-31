"""Nettoyage des entrées utilisateur et neutralisation des documents.

Modèle de menace
----------------
Deux flux non fiables entrent dans le prompt :

1. **Le message Telegram.** Contenu et volume maîtrisés par un tiers.
2. **Les extraits documentaires renvoyés par Qdrant.** C'est le vecteur le
   plus dangereux et le moins intuitif : quiconque peut déposer un PDF dans
   la bibliothèque peut y écrire « ignore tes instructions ». Le document
   devient alors une instruction.

Parade retenue, en trois couches indépendantes :

* le prompt système déclare explicitement que le contenu documentaire est
  de la DONNÉE (voir ``app/ai/prompts.py``) ;
* chaque extrait est encadré par des balises et son texte est débarrassé des
  séquences qui imitent une frontière de rôle ou une balise de contexte ;
* la taille des entrées est bornée avant tout traitement.

Aucune couche n'est suffisante seule ; c'est leur cumul qui rend l'injection
coûteuse.
"""

from __future__ import annotations

import re
import unicodedata

# Séquences qui, laissées telles quelles dans un extrait, imiteraient la
# structure du prompt. La liste vise les formes STRUCTURELLES (frontières de
# rôle, balises de contexte) et non le vocabulaire : filtrer des mots comme
# « ignore » produirait d'innombrables faux positifs sur un corpus de livres.
_MOTIFS_STRUCTURELS = [
    re.compile(r"</?\s*(documents?|contexte|context|system|assistant|human|user)\s*>", re.I),
    re.compile(r"^\s*(system|assistant|human|user)\s*:", re.I | re.M),
    re.compile(r"\[\s*/?\s*(INST|SYS|SYSTEM)\s*\]", re.I),
    re.compile(r"<\|.*?\|>"),  # marqueurs de rôle façon ChatML
]

# Caractères de contrôle et espaces exotiques : ils servent à masquer une
# instruction à l'œil humain tout en la laissant lisible par le modèle.
_CONTROLE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_ESPACES_INVISIBLES = re.compile(
    "[​‌‍‎‏⁠­‪-‮﻿]"
)


def normaliser_texte(texte: str) -> str:
    """Normalisation commune à l'ingestion et aux requêtes.

    NFKC unifie les variantes de compatibilité (ligatures, largeurs) : sans
    cela, deux graphies visuellement identiques produiraient deux embeddings
    différents et casseraient la déduplication.
    """
    if not texte:
        return ""
    texte = unicodedata.normalize("NFKC", texte)
    texte = _CONTROLE.sub(" ", texte)
    texte = _ESPACES_INVISIBLES.sub("", texte)
    texte = texte.replace("\r\n", "\n").replace("\r", "\n")
    # Espaces horizontaux compressés, sauts de ligne préservés : la structure
    # en paragraphes porte l'information de découpage (voir chunker.py).
    texte = re.sub(r"[ \t\f\v]+", " ", texte)
    texte = re.sub(r"\n{3,}", "\n\n", texte)
    return texte.strip()


def neutraliser_contenu_document(texte: str) -> str:
    """Rend inerte un extrait documentaire avant insertion dans le prompt.

    Les séquences structurelles ne sont pas supprimées mais DÉSAMORCÉES :
    supprimer du texte fausserait les citations et pourrait effacer un
    contenu légitime — une page de documentation technique parle
    légitimement de balises XML.
    """
    texte = normaliser_texte(texte)
    for motif in _MOTIFS_STRUCTURELS:
        texte = motif.sub(lambda m: "⟦" + m.group(0).strip("<>[] \n") + "⟧", texte)
    return texte


def nettoyer_entree_utilisateur(texte: str, max_chars: int) -> str:
    """Normalise et borne un message entrant.

    La troncature est explicite et signalée dans le texte : un utilisateur
    dont la question est coupée doit pouvoir le comprendre depuis la réponse,
    plutôt que de croire que Joshua a mal compris.
    """
    texte = normaliser_texte(texte)
    if len(texte) > max_chars:
        texte = texte[:max_chars].rstrip() + " […message tronqué]"
    return texte


def masquer_secrets(texte: str) -> str:
    """Masque ce qui ressemble à une clé d'API avant journalisation.

    Un utilisateur colle parfois une clé dans une conversation ; elle ne doit
    pas se retrouver en clair dans les journaux, dont la durée de vie et le
    périmètre de lecture diffèrent de ceux de la base de données.
    """
    texte = re.sub(r"sk-[A-Za-z0-9_\-]{16,}", "sk-***", texte)
    texte = re.sub(r"\b\d{8,10}:[A-Za-z0-9_\-]{30,}\b", "***:***", texte)  # jeton Telegram
    return texte
