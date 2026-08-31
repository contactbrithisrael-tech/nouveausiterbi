"""Découpage des documents en chunks destinés au RAG.

Principe
--------
Un chunk doit être **autonome** : il sera lu par Claude hors de son document,
sans les pages voisines. D'où trois exigences, dans cet ordre de priorité :

1. **Ne pas couper au milieu d'une phrase.** Une phrase tronquée produit un
   embedding bruité et une citation incompréhensible. Le découpage suit donc
   la hiérarchie naturelle du texte : paragraphes, puis phrases, et ne
   coupe brutalement qu'en dernier recours (une « phrase » de 6 000
   caractères, typique d'un PDF mal extrait).

2. **Conserver la localisation.** Page, section et titre voyagent avec le
   chunk : sans eux, aucune citation honnête n'est possible et Joshua serait
   contraint d'inventer une référence.

3. **Recouvrir les frontières.** Un recouvrement de ~120 tokens garantit
   qu'une idée à cheval sur deux chunks reste entièrement présente dans au
   moins l'un des deux. Le recouvrement reprend des PHRASES entières, jamais
   un nombre fixe de caractères.

Sur le comptage en caractères plutôt qu'en tokens
-------------------------------------------------
Anthropic ne publie pas de tokenizer local, et compter exactement imposerait
un appel réseau par chunk — rédhibitoire sur des millions de chunks. On
convertit donc tokens ↔ caractères via ``CHARS_PER_TOKEN`` (3.6, mesuré sur
du français). L'erreur est de l'ordre de 10 %, absorbée par la marge de la
fenêtre de contexte, et le sens de l'erreur est le bon : on sous-estime
rarement la place occupée.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Iterator

# Frontière de phrase : ponctuation forte suivie d'une espace et d'une
# majuscule ou d'un guillemet.
#
# Les abréviations sont protégées par des lookbehind qui INCLUENT le point.
# Le détail compte : « (?<!\bM) » évalué juste après le point regarde le
# caractère « . » et laisse donc passer « M. Dupont ». Seul « (?<!\bM\.) »
# bloque réellement la coupure.
#
# « (?<![A-Z]\.) » protège les initiales de prénoms (« J. Dupont »). Le prix
# est de ne pas couper après une phrase se terminant par une lettre capitale
# isolée — situation bien plus rare qu'une initiale en milieu de phrase.
_ABREVIATIONS = (
    r"(?<!\bM\.)(?<!\bMM\.)(?<!\bMme\.)(?<!\bDr\.)(?<!\bSt\.)(?<!\bSte\.)"
    r"(?<!\bcf\.)(?<!\bp\.)(?<!\bpp\.)(?<!\bvol\.)(?<!\bfig\.)(?<!\bart\.)"
    r"(?<!\bchap\.)(?<!\bibid\.)(?<!\bal\.)(?<!\betc\.)(?<![A-Z]\.)"
)
_FIN_DE_PHRASE = re.compile(rf"{_ABREVIATIONS}(?<=[.!?…])[\"'»”\)]?\s+(?=[A-ZÀ-ÖØ-Þ«\"'\d])")
_PARAGRAPHE = re.compile(r"\n\s*\n")


@dataclass(slots=True)
class Bloc:
    """Fragment de texte issu d'un parseur, avec sa localisation.

    Les parseurs produisent des blocs ; le chunker les recompose. Cette
    séparation permet d'écrire un parseur sans rien connaître de la
    stratégie de découpage, et inversement.
    """

    texte: str
    page: int | None = None
    section: str | None = None
    title: str | None = None


@dataclass(slots=True)
class Chunk:
    texte: str
    page: int | None = None
    section: str | None = None
    title: str | None = None
    index: int = 0
    #: Nombre de caractères, utile aux statistiques et aux tests.
    taille: int = field(default=0)

    def __post_init__(self) -> None:
        if not self.taille:
            self.taille = len(self.texte)


def decouper_en_phrases(texte: str) -> list[str]:
    """Découpe un paragraphe en phrases, en conservant la ponctuation."""
    texte = texte.strip()
    if not texte:
        return []
    morceaux = _FIN_DE_PHRASE.split(texte)
    return [m.strip() for m in morceaux if m.strip()]


def _decoupe_dure(texte: str, taille_max: int) -> list[str]:
    """Dernier recours : coupe sur une espace proche de la limite.

    Utilisé quand une « phrase » dépasse à elle seule la taille cible — cas
    réel des PDF dont l'extraction perd toute ponctuation. On préfère encore
    couper sur une espace que sur un caractère arbitraire.
    """
    morceaux: list[str] = []
    reste = texte
    while len(reste) > taille_max:
        fenetre = reste[:taille_max]
        coupe = fenetre.rfind(" ")
        if coupe < taille_max * 0.6:  # aucune espace exploitable
            coupe = taille_max
        morceaux.append(reste[:coupe].strip())
        reste = reste[coupe:].strip()
    if reste:
        morceaux.append(reste)
    return morceaux


def _recouvrement(phrases: list[str], taille_cible: int) -> list[str]:
    """Dernières phrases d'un chunk, dans la limite du recouvrement voulu.

    On reprend des phrases entières en partant de la fin : reprendre N
    caractères produirait un début de chunk tronqué, exactement ce que le
    recouvrement est censé éviter.
    """
    if taille_cible <= 0 or not phrases:
        return []
    reprises: list[str] = []
    total = 0
    for phrase in reversed(phrases):
        if total + len(phrase) > taille_cible:
            break
        reprises.insert(0, phrase)
        total += len(phrase) + 1

    if reprises:
        return reprises

    # Aucune phrase entière ne tient dans le budget de recouvrement : la
    # dernière est plus longue que le recouvrement lui-même. Reprendre cette
    # phrase entière ferait dépasser le chunk suivant de sa propre longueur —
    # jusqu'à doubler la taille cible. On reprend donc sa FIN, coupée sur une
    # espace : le recouvrement reste borné, et le raccord reste lisible.
    derniere = phrases[-1]
    queue = derniere[-taille_cible:]
    espace = queue.find(" ")
    return [queue[espace + 1 :] if 0 <= espace < len(queue) - 1 else queue]


def chunker_blocs(
    blocs: Iterable[Bloc],
    taille_cible: int,
    recouvrement: int,
    taille_min: int,
) -> Iterator[Chunk]:
    """Transforme un flux de blocs en flux de chunks.

    Générateur et non liste : un livre de 900 pages ne doit jamais être
    entièrement matérialisé en mémoire, ni ses chunks accumulés avant
    encodage. C'est la condition pour ingérer une bibliothèque entière sur
    une machine ordinaire.

    Un changement de page ou de section **ne force pas** la fermeture du
    chunk : une idée qui traverse une fin de page resterait sinon coupée en
    deux. La localisation retenue est celle du DÉBUT du chunk, seule
    référence honnête pour une citation.
    """
    index = 0
    courant: list[str] = []
    taille_courante = 0
    page_debut: int | None = None
    section_debut: str | None = None
    titre_debut: str | None = None

    def emettre() -> Iterator[Chunk]:
        nonlocal index, courant, taille_courante, page_debut, section_debut, titre_debut
        texte = " ".join(courant).strip()
        if texte:
            yield Chunk(
                texte=texte,
                page=page_debut,
                section=section_debut,
                title=titre_debut,
                index=index,
            )
            index += 1

    for bloc in blocs:
        texte_bloc = (bloc.texte or "").strip()
        if not texte_bloc:
            continue

        for paragraphe in _PARAGRAPHE.split(texte_bloc):
            paragraphe = paragraphe.strip()
            if not paragraphe:
                continue

            phrases = decouper_en_phrases(paragraphe)
            # Une phrase plus longue que la cible est redécoupée avant d'être
            # traitée : sinon elle produirait à elle seule un chunk hors norme.
            phrases_normalisees: list[str] = []
            for phrase in phrases:
                if len(phrase) > taille_cible:
                    phrases_normalisees.extend(_decoupe_dure(phrase, taille_cible))
                else:
                    phrases_normalisees.append(phrase)

            for phrase in phrases_normalisees:
                if page_debut is None and not courant:
                    page_debut, section_debut, titre_debut = bloc.page, bloc.section, bloc.title

                if taille_courante + len(phrase) + 1 > taille_cible and courant:
                    yield from emettre()
                    reprises = _recouvrement(courant, recouvrement)
                    courant = list(reprises)
                    taille_courante = sum(len(p) + 1 for p in courant)
                    # La localisation repart du bloc courant : le recouvrement
                    # appartient au chunk précédent, mais le nouveau chunk
                    # commence bien ici.
                    page_debut, section_debut, titre_debut = bloc.page, bloc.section, bloc.title

                courant.append(phrase)
                taille_courante += len(phrase) + 1

    # Dernier chunk : émis même s'il est court, SAUF s'il est ridiculement
    # petit et qu'un chunk précédent existe — un fragment de dix mots ne
    # porte aucun sens et pollue l'index.
    texte_final = " ".join(courant).strip()
    if texte_final and (len(texte_final) >= taille_min or index == 0):
        yield from emettre()


def chunker_document(blocs: Iterable[Bloc], settings) -> Iterator[Chunk]:
    """Point d'entrée utilisant la configuration de l'application."""
    return chunker_blocs(
        blocs,
        taille_cible=settings.chunk_target_chars,
        recouvrement=settings.chunk_overlap_chars,
        taille_min=settings.chunk_min_chars,
    )
