"""Construction du contexte documentaire envoyé à Claude.

Le budget de contexte est une ressource rare
--------------------------------------------
Chaque caractère envoyé est payé, à chaque message. Injecter les trente
candidats retournés par Qdrant coûterait cinq fois plus cher pour une réponse
souvent moins bonne : au-delà d'une dizaine d'extraits, le signal se dilue et
le modèle perd en précision. On sélectionne donc, on ordonne, et on tronque
explicitement.

Trois décisions structurent ce module :

1. **Diversification (MMR).** Sans elle, les dix meilleurs résultats
   proviennent souvent de la même page d'un même ouvrage — dix formulations
   du même passage, aucune information nouvelle. Le MMR arbitre entre
   pertinence et diversité.

2. **Numérotation stable.** Chaque extrait porte le numéro [n] que Claude
   devra citer. La correspondance numéro → source est conservée côté serveur :
   c'est ce qui permet de vérifier après coup qu'une citation est réelle, et
   d'empêcher une référence inventée d'atteindre l'utilisateur.

3. **Neutralisation systématique.** Le texte de chaque extrait passe par
   ``neutraliser_contenu_document`` avant d'entrer dans le prompt.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.security.sanitization import neutraliser_contenu_document
from app.vectorstore.qdrant import ResultatRecherche


@dataclass(slots=True)
class Source:
    """Une source citable, telle qu'elle sera présentée à l'utilisateur."""

    numero: int
    filename: str
    page: int | None
    section: str | None
    document_id: str
    chunk_id: str
    score: float

    def libelle(self) -> str:
        """Référence lisible. Ne contient QUE des métadonnées réelles."""
        if self.page:
            return f"{self.filename} — page {self.page}"
        if self.section:
            return f"{self.filename} — {self.section}"
        return self.filename


def _similarite_lexicale(a: str, b: str) -> float:
    """Jaccard sur les mots, utilisé comme mesure de redondance.

    Les vecteurs ne sont volontairement pas rapatriés depuis Qdrant (4 Ko par
    point) : mesurer la redondance sur le texte coûte quelques microsecondes
    et suffit largement à repérer deux extraits quasi identiques, seul cas que
    la diversification doit traiter.
    """
    mots_a = set(a.lower().split())
    mots_b = set(b.lower().split())
    if not mots_a or not mots_b:
        return 0.0
    intersection = len(mots_a & mots_b)
    return intersection / float(len(mots_a | mots_b))


def selectionner(
    candidats: list[ResultatRecherche],
    limite: int,
    lambda_mmr: float = 0.7,
    max_par_document: int = 4,
) -> list[ResultatRecherche]:
    """Choisit les extraits finaux parmi les candidats.

    ``max_par_document`` empêche un seul ouvrage volumineux de monopoliser le
    contexte : sur une bibliothèque, le livre le plus verbeux sur un sujet
    n'est pas nécessairement le plus juste, et une réponse appuyée sur
    plusieurs sources est plus solide.
    """
    if not candidats:
        return []

    retenus: list[ResultatRecherche] = []
    restants = list(candidats)
    compte_par_document: dict[str, int] = {}

    while restants and len(retenus) < limite:
        meilleur = None
        meilleur_score = -math.inf
        for candidat in restants:
            if compte_par_document.get(candidat.document_id, 0) >= max_par_document:
                continue
            redondance = max(
                (_similarite_lexicale(candidat.text, r.text) for r in retenus), default=0.0
            )
            score_mmr = lambda_mmr * candidat.score - (1 - lambda_mmr) * redondance
            if score_mmr > meilleur_score:
                meilleur_score = score_mmr
                meilleur = candidat
        if meilleur is None:
            break
        retenus.append(meilleur)
        restants.remove(meilleur)
        compte_par_document[meilleur.document_id] = compte_par_document.get(meilleur.document_id, 0) + 1

    return retenus


def construire(
    resultats: list[ResultatRecherche], max_chars: int
) -> tuple[list[str], list[Source]]:
    """Formate les extraits et la table des sources.

    Retourne ``(extraits_formatés, sources)``. La troncature au budget de
    caractères est faite ici, sur des extraits ENTIERS : couper un extrait en
    deux produirait une citation partielle attribuée à une page qui ne la
    contient plus.
    """
    extraits: list[str] = []
    sources: list[Source] = []
    total = 0

    for i, resultat in enumerate(resultats, start=1):
        source = Source(
            numero=i,
            filename=resultat.filename,
            page=resultat.page,
            section=resultat.section,
            document_id=resultat.document_id,
            chunk_id=resultat.chunk_id,
            score=resultat.score,
        )
        texte = neutraliser_contenu_document(resultat.text)
        entete = f"[{i}] {source.libelle()}"
        bloc = f"{entete}\n{texte}"

        if total + len(bloc) > max_chars and extraits:
            break

        extraits.append(bloc)
        sources.append(source)
        total += len(bloc)

    return extraits, sources


def formater_sources(sources: list[Source], utilisees: set[int] | None = None) -> str:
    """Bloc de références ajouté sous la réponse.

    Si ``utilisees`` est fourni, seules les sources réellement citées par
    Claude sont listées : afficher une source non utilisée laisserait croire
    qu'elle étaye la réponse.
    """
    retenues = [s for s in sources if utilisees is None or s.numero in utilisees]
    if not retenues:
        return ""
    lignes = [f"[{s.numero}] {s.libelle()}" for s in retenues]
    return "\n".join(lignes)
