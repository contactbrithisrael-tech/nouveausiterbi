"""Pipeline RAG : question → passages pertinents → contexte prêt pour Claude.

Enchaînement
------------
    question → normalisation → embedding (mis en cache) → recherche Qdrant
    → sélection/diversification → construction du contexte → sources

Décisions structurantes
-----------------------
* **Deux tailles distinctes.** ``RAG_CANDIDATES`` (30) est ce que l'on
  demande à Qdrant ; ``RAG_FINAL_CHUNKS`` (10) est ce que l'on envoie à
  Claude. Chercher large coûte quelques millisecondes et améliore nettement
  le rappel ; envoyer large coûte des jetons à chaque message et dégrade la
  précision. Les deux paramètres n'ont donc aucune raison d'être égaux.

* **Cache des embeddings de requêtes.** Les questions se répètent beaucoup
  plus qu'on ne le croit (« résume », « et ensuite ? », reformulations
  identiques). Encoder coûte ~50 ms de CPU ; un aller-retour Redis coûte
  1 ms. Le cache porte sur la question NORMALISÉE, ce qui capte aussi les
  variantes de casse et de ponctuation.

* **Seuil de score.** En dessous de ``RAG_MIN_SCORE``, un passage n'est pas
  « moins pertinent », il est hors sujet. L'envoyer inviterait Claude à
  bâtir une réponse sur du bruit ; mieux vaut un contexte vide et un aveu
  d'ignorance.

* **Vérification des citations.** Les numéros que Claude cite sont
  confrontés aux sources réellement fournies. Une référence inventée est
  ainsi détectable — c'est la dernière ligne de défense contre une citation
  fabriquée.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

from app.ai.context_builder import Source, construire, selectionner
from app.ai.prompts import bloc_documents
from app.config import Settings
from app.embeddings.base import EmbeddingProvider
from app.security.sanitization import normaliser_texte
from app.utils.logging import get_logger
from app.vectorstore.qdrant import QdrantRecherche, ResultatRecherche

log = get_logger(__name__)

_CITATION = re.compile(r"\[(\d{1,2})\]")


@dataclass(slots=True)
class ContexteRAG:
    contexte: str
    sources: list[Source] = field(default_factory=list)
    candidats: int = 0
    retenus: int = 0
    score_max: float = 0.0

    @property
    def a_des_sources(self) -> bool:
        return bool(self.sources)


class MoteurRAG:
    def __init__(
        self,
        settings: Settings,
        provider: EmbeddingProvider,
        recherche: QdrantRecherche,
        redis_client=None,
    ) -> None:
        self._settings = settings
        self._provider = provider
        self._recherche = recherche
        self._redis = redis_client

    async def _embedding_question(self, question: str) -> list[float]:
        """Encode la question, avec cache Redis si disponible.

        La clé inclut l'identifiant du modèle : changer de modèle
        d'embeddings invalide automatiquement le cache, au lieu de renvoyer
        silencieusement des vecteurs incompatibles avec l'index.
        """
        cle = None
        if self._redis is not None:
            empreinte = hashlib.sha256(question.encode("utf-8")).hexdigest()[:32]
            cle = f"joshua:emb:{self._provider.model_id}:{empreinte}"
            try:
                cache = await self._redis.get(cle)
                if cache:
                    return json.loads(cache)
            except Exception as exc:  # pragma: no cover - dépend de l'infra
                log.warning("cache_embedding_lecture_echouee", error=str(exc))

        vecteur = await self._provider.aembed_query(question)

        if cle is not None:
            try:
                await self._redis.setex(
                    cle, self._settings.EMBEDDING_CACHE_TTL_SECONDS, json.dumps(vecteur)
                )
            except Exception as exc:  # pragma: no cover
                log.warning("cache_embedding_ecriture_echouee", error=str(exc))
        return vecteur

    async def recuperer(
        self, question: str, filtres: dict[str, Any] | None = None
    ) -> ContexteRAG:
        """Récupère et met en forme le contexte documentaire d'une question."""
        question_normalisee = normaliser_texte(question)
        if not question_normalisee:
            return ContexteRAG(contexte=bloc_documents([]))

        vecteur = await self._embedding_question(question_normalisee)

        candidats: list[ResultatRecherche] = await self._recherche.rechercher(
            vecteur=vecteur,
            limite=self._settings.RAG_CANDIDATES,
            filtres=filtres,
            score_min=self._settings.RAG_MIN_SCORE,
        )

        if not candidats:
            log.info("rag_aucun_resultat", question_len=len(question_normalisee))
            return ContexteRAG(contexte=bloc_documents([]))

        retenus = selectionner(
            candidats,
            limite=self._settings.RAG_FINAL_CHUNKS,
            lambda_mmr=self._settings.RAG_MMR_LAMBDA,
        )
        extraits, sources = construire(retenus, self._settings.RAG_MAX_CONTEXT_CHARS)

        log.info(
            "rag_contexte_construit",
            candidats=len(candidats),
            retenus=len(sources),
            score_max=round(candidats[0].score, 4),
        )
        return ContexteRAG(
            contexte=bloc_documents(extraits),
            sources=sources,
            candidats=len(candidats),
            retenus=len(sources),
            score_max=candidats[0].score,
        )


def citations_utilisees(reponse: str, sources: list[Source]) -> set[int]:
    """Numéros de sources réellement cités dans la réponse.

    Un numéro cité mais absent de la table est signalé : c'est le symptôme
    d'une référence inventée, et il vaut mieux le voir dans les journaux que
    le laisser passer pour argent comptant.
    """
    disponibles = {s.numero for s in sources}
    cites = {int(m) for m in _CITATION.findall(reponse)}
    fantomes = cites - disponibles
    if fantomes:
        log.warning("citations_fantomes", numeros=sorted(fantomes))
    return cites & disponibles
