"""Accès à Qdrant : création de collection, upsert par lots, recherche filtrée.

Choix d'architecture
--------------------
* **Deux clients, deux usages.** ``QdrantClient`` synchrone pour l'ingestion
  (un long traitement séquentiel, où l'asynchrone n'apporte rien et
  complique le code) et ``AsyncQdrantClient`` pour le bot (où bloquer la
  boucle bloquerait tous les utilisateurs). Les deux partagent la même
  configuration de collection.

* **Payload indexé explicitement.** Qdrant ne crée pas d'index de payload
  tout seul : sans ``create_payload_index``, un filtre sur ``category``
  déclenche un balayage complet. À plusieurs millions de points, la
  différence n'est pas une optimisation, c'est la différence entre 40 ms et
  plusieurs secondes.

* **Vecteurs stockés sur disque (``on_disk=True``).** Un million de vecteurs
  en 1024 dimensions représente ~4 Go en float32. Les garder en RAM
  imposerait une machine surdimensionnée ; l'index HNSW, lui, reste en
  mémoire, ce qui préserve la latence de recherche.

* **Identifiants de points en UUID.** Qdrant n'accepte que des entiers ou
  des UUID ; l'UUID du chunk est donc utilisé tel quel, ce qui permet de
  retrouver ou de supprimer un chunk sans table de correspondance.

* **``model_id`` dans chaque payload.** Changer de modèle d'embeddings rend
  l'index incohérent. Conserver l'empreinte du modèle permet de détecter le
  mélange plutôt que de le subir sous forme de résultats absurdes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from qdrant_client import AsyncQdrantClient, QdrantClient
from qdrant_client.http import models as qm

from app.config import Settings
from app.utils.logging import get_logger

log = get_logger(__name__)

# Champs de payload filtrables. Chacun reçoit un index dédié : la liste est
# volontairement courte, chaque index ayant un coût en mémoire et en écriture.
CHAMPS_INDEXES: tuple[tuple[str, Any], ...] = (
    ("document_id", qm.PayloadSchemaType.KEYWORD),
    ("category", qm.PayloadSchemaType.KEYWORD),
    ("document_type", qm.PayloadSchemaType.KEYWORD),
    ("source", qm.PayloadSchemaType.KEYWORD),
    ("tags", qm.PayloadSchemaType.KEYWORD),
    ("checksum", qm.PayloadSchemaType.KEYWORD),
    ("language", qm.PayloadSchemaType.KEYWORD),
)


@dataclass(slots=True)
class ResultatRecherche:
    """Résultat normalisé, indépendant du SDK Qdrant.

    Le RAG et le constructeur de contexte manipulent cet objet plutôt que le
    type du client : changer de base vectorielle ne toucherait alors que ce
    fichier.
    """

    chunk_id: str
    document_id: str
    score: float
    text: str
    payload: dict[str, Any]

    @property
    def filename(self) -> str:
        return self.payload.get("filename") or self.payload.get("source") or "source inconnue"

    @property
    def page(self) -> int | None:
        page = self.payload.get("page")
        return int(page) if isinstance(page, (int, float)) else None

    @property
    def section(self) -> str | None:
        return self.payload.get("section") or self.payload.get("title") or None


def _client_sync(settings: Settings) -> QdrantClient:
    return QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY or None,
        timeout=120,  # l'upsert d'un gros lot peut être long
    )


def _client_async(settings: Settings) -> AsyncQdrantClient:
    return AsyncQdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY or None,
        timeout=30,
    )


def assurer_collection(settings: Settings, dimension: int, nom: str | None = None) -> str:
    """Crée la collection et ses index si nécessaire. Idempotent.

    Appelée à chaque démarrage d'ingestion : une collection absente est le
    premier écueil d'une installation neuve, et échouer là-dessus après vingt
    minutes d'extraction de texte serait inacceptable.
    """
    collection = nom or settings.QDRANT_COLLECTION
    client = _client_sync(settings)
    try:
        existantes = {c.name for c in client.get_collections().collections}
        if collection not in existantes:
            client.create_collection(
                collection_name=collection,
                vectors_config=qm.VectorParams(
                    size=dimension,
                    distance=qm.Distance.COSINE,  # normalisé : cohérent avec E5
                    on_disk=True,
                ),
                hnsw_config=qm.HnswConfigDiff(
                    m=settings.QDRANT_HNSW_M,
                    ef_construct=settings.QDRANT_HNSW_EF_CONSTRUCT,
                ),
                optimizers_config=qm.OptimizersConfigDiff(
                    # Indexation différée : pendant un import massif, Qdrant
                    # accumule les points en segments non indexés et ne
                    # construit l'index HNSW qu'au-delà du seuil. Indexer en
                    # continu ralentirait l'ingestion d'un ordre de grandeur.
                    indexing_threshold=20_000,
                ),
            )
            log.info("qdrant_collection_creee", collection=collection, dim=dimension)

        for champ, schema in CHAMPS_INDEXES:
            try:
                client.create_payload_index(
                    collection_name=collection, field_name=champ, field_schema=schema
                )
            except Exception:
                # L'index existe déjà : Qdrant renvoie une erreur qu'il n'y a
                # aucune raison de propager sur un appel idempotent.
                pass
        return collection
    finally:
        client.close()


def upsert_batch(settings: Settings, points: Sequence[qm.PointStruct], collection: str | None = None) -> int:
    """Écrit un lot de points. Retourne le nombre écrit."""
    if not points:
        return 0
    client = _client_sync(settings)
    try:
        client.upsert(
            collection_name=collection or settings.QDRANT_COLLECTION,
            points=list(points),
            wait=False,  # l'ingestion n'attend pas l'indexation : voir ci-dessus
        )
        return len(points)
    finally:
        client.close()


def construire_point(
    chunk_id: str, vecteur: list[float], texte: str, payload: dict[str, Any]
) -> qm.PointStruct:
    """Assemble un point Qdrant.

    Le texte du chunk est stocké DANS le payload : Qdrant devient ainsi la
    seule source à interroger au moment de répondre. L'alternative — ne
    stocker que des identifiants et relire PostgreSQL — ajouterait un
    aller-retour sur le chemin critique de chaque question.
    """
    return qm.PointStruct(id=chunk_id, vector=vecteur, payload={**payload, "text": texte})


def supprimer_par_document(settings: Settings, document_id: str, collection: str | None = None) -> None:
    """Supprime tous les chunks d'un document (réindexation, fichier disparu)."""
    client = _client_sync(settings)
    try:
        client.delete(
            collection_name=collection or settings.QDRANT_COLLECTION,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(
                    must=[qm.FieldCondition(key="document_id", match=qm.MatchValue(value=document_id))]
                )
            ),
        )
    finally:
        client.close()


def _construire_filtre(filtres: dict[str, Any] | None) -> qm.Filter | None:
    """Traduit un dictionnaire simple en filtre Qdrant.

    Les listes deviennent des ``MatchAny`` (OU), les scalaires des
    ``MatchValue`` (ET entre clés différentes). Cette convention couvre les
    besoins réels (« catégorie X ET tags parmi [a, b] ») sans exposer la
    syntaxe complète de Qdrant au reste du code.
    """
    if not filtres:
        return None
    conditions: list[qm.FieldCondition] = []
    for cle, valeur in filtres.items():
        if valeur is None:
            continue
        if isinstance(valeur, (list, tuple, set)):
            conditions.append(qm.FieldCondition(key=cle, match=qm.MatchAny(any=list(valeur))))
        else:
            conditions.append(qm.FieldCondition(key=cle, match=qm.MatchValue(value=valeur)))
    return qm.Filter(must=conditions) if conditions else None


class QdrantRecherche:
    """Façade asynchrone utilisée par le bot.

    Le client est conservé pour toute la durée de vie de l'application : sa
    création ouvre un pool HTTP, en instancier un par requête serait un
    gaspillage mesurable sous charge.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = _client_async(settings)

    async def rechercher(
        self,
        vecteur: list[float],
        limite: int,
        filtres: dict[str, Any] | None = None,
        score_min: float | None = None,
        collection: str | None = None,
    ) -> list[ResultatRecherche]:
        reponse = await self._client.query_points(
            collection_name=collection or self._settings.QDRANT_COLLECTION,
            query=vecteur,
            limit=limite,
            query_filter=_construire_filtre(filtres),
            score_threshold=score_min,
            with_payload=True,
            # Les vecteurs ne sont PAS rapatriés : ils pèsent 4 Ko par point
            # et ne servent pas à la génération de la réponse.
            with_vectors=False,
        )
        resultats: list[ResultatRecherche] = []
        for point in reponse.points:
            payload = dict(point.payload or {})
            texte = payload.pop("text", "")
            resultats.append(
                ResultatRecherche(
                    chunk_id=str(point.id),
                    document_id=str(payload.get("document_id", "")),
                    score=float(point.score),
                    text=texte,
                    payload=payload,
                )
            )
        return resultats

    async def compter(self, collection: str | None = None) -> int:
        info = await self._client.count(
            collection_name=collection or self._settings.QDRANT_COLLECTION, exact=False
        )
        return int(info.count)

    async def sante(self) -> bool:
        try:
            await self._client.get_collections()
            return True
        except Exception as exc:
            log.warning("qdrant_indisponible", error=str(exc))
            return False

    async def fermer(self) -> None:
        await self._client.close()
