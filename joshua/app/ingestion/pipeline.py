"""Pipeline d'ingestion : du fichier au vecteur indexé.

Contraintes qui dictent la conception
-------------------------------------
* **La mémoire est le facteur limitant, pas le CPU.** Le pipeline est une
  chaîne de générateurs : à aucun moment la liste des documents, ni celle des
  chunks d'un document, n'existe entièrement en mémoire. Seul un lot
  (``EMBEDDING_BATCH_SIZE`` chunks) est matérialisé à la fois.

* **Un document en erreur ne doit jamais arrêter l'import.** Une bibliothèque
  réelle contient des PDF corrompus, des DOCX protégés, des EPUB tronqués.
  L'échec est capturé, journalisé, enregistré sur le document, et l'ingestion
  continue. Un import de 40 000 livres qui s'arrête au 12 000ᵉ est inutilisable.

* **Aucune requête par chunk.** Les écritures PostgreSQL se font par document
  (une ligne), et les écritures Qdrant par lot. Une requête par chunk
  multiplierait par mille le nombre d'allers-retours.

* **L'ordre des étapes n'est pas négociable.** La déduplication par empreinte
  précède l'extraction : sur une réindexation, la quasi-totalité des fichiers
  est écartée pour le prix d'un ``stat``, sans jamais ouvrir de PDF.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator

from app.config import Settings
from app.database.models import Document, StatutDocument
from app.database.repository import (
    enregistrer_document,
    index_bibliotheque,
    marquer_documents,
)
from app.embeddings.base import EmbeddingProvider
from app.ingestion.chunker import Bloc, Chunk, chunker_document
from app.ingestion.deduplication import DeduplicateurChunks, checksum_fichier, fichier_inchange
from app.ingestion.loader import FichierDecouvert, parcourir
from app.ingestion.parser import FormatNonSupporte, extraire, mime_type
from app.security.sanitization import normaliser_texte
from app.utils.logging import get_logger
from app.vectorstore.qdrant import assurer_collection, construire_point, supprimer_par_document, upsert_batch

log = get_logger(__name__)


@dataclass
class Compteurs:
    vus: int = 0
    indexes: int = 0
    ignores: int = 0
    erreurs: int = 0
    icloud_absents: int = 0
    chunks: int = 0
    doublons_chunks: int = 0
    supprimes: int = 0
    details: list[str] = field(default_factory=list)

    def resume(self) -> dict[str, int]:
        return {
            "vus": self.vus,
            "indexes": self.indexes,
            "ignores": self.ignores,
            "erreurs": self.erreurs,
            "icloud": self.icloud_absents,
            "chunks": self.chunks,
            "doublons": self.doublons_chunks,
            "supprimes": self.supprimes,
        }


def _lots(iterable: Iterable[Any], taille: int) -> Iterator[list[Any]]:
    """Regroupe un flux en lots, sans jamais le matérialiser entièrement."""
    lot: list[Any] = []
    for element in iterable:
        lot.append(element)
        if len(lot) >= taille:
            yield lot
            lot = []
    if lot:
        yield lot


def _payload_commun(
    document_id: str,
    fichier: FichierDecouvert,
    infos: dict[str, Any],
    checksum: str,
    settings: Settings,
    source: str,
    categorie: str | None,
    tags: list[str] | None,
) -> dict[str, Any]:
    """Payload partagé par tous les chunks d'un document.

    Il est construit UNE fois puis copié : le recalculer par chunk gaspillerait
    du temps sur des millions d'itérations, et surtout ferait courir le risque
    que deux chunks du même document portent des métadonnées différentes.
    """
    return {
        "document_id": document_id,
        "source": source,
        "filename": fichier.chemin.name,
        "relative_path": fichier.chemin_relatif,
        "document_type": fichier.document_type,
        "category": categorie,
        "tags": tags or [],
        "checksum": checksum,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "title": infos.get("title"),
        "author": infos.get("author"),
        "language": infos.get("language"),
        "year": infos.get("year"),
        # Empreinte du modèle : permet de détecter un index construit avec un
        # modèle différent de celui utilisé pour interroger.
        "model_id": None,
    }


def indexer_fichier(
    fichier: FichierDecouvert,
    settings: Settings,
    provider: EmbeddingProvider,
    session,
    dedup: DeduplicateurChunks,
    source: str = "library",
    categorie: str | None = None,
    tags: list[str] | None = None,
    collection: str | None = None,
) -> tuple[int, str]:
    """Indexe un fichier. Retourne ``(nombre_de_chunks, document_id)``.

    Les exceptions ne sont PAS capturées ici : l'appelant décide quoi faire
    d'un document en échec (le marquer, le compter, poursuivre). Mélanger les
    deux responsabilités rendrait la fonction inutilisable dans un autre
    contexte.
    """
    checksum = checksum_fichier(fichier.chemin)
    document_id = str(uuid.uuid4())

    blocs, infos = extraire(fichier.chemin)
    payload_base = _payload_commun(
        document_id, fichier, infos, checksum, settings, source, categorie, tags
    )
    payload_base["model_id"] = provider.model_id

    def blocs_nettoyes() -> Iterator[Bloc]:
        """Normalise le texte au fil de l'eau, bloc par bloc."""
        for bloc in blocs:
            texte = normaliser_texte(bloc.texte)
            if texte:
                yield Bloc(texte=texte, page=bloc.page, section=bloc.section, title=bloc.title)

    def chunks_utiles() -> Iterator[Chunk]:
        for chunk in chunker_document(blocs_nettoyes(), settings):
            if len(chunk.texte) < settings.chunk_min_chars and chunk.index > 0:
                continue
            if not dedup.est_nouveau(chunk.texte):
                continue
            yield chunk

    total = 0
    for lot in _lots(chunks_utiles(), settings.EMBEDDING_BATCH_SIZE):
        vecteurs = provider.embed_documents([c.texte for c in lot])
        points = []
        for chunk, vecteur in zip(lot, vecteurs):
            # UUID5 dérivé de (document_id, index) : l'identifiant d'un chunk
            # est donc DÉTERMINISTE. Réindexer le même document réécrit les
            # mêmes points au lieu d'en créer de nouveaux, ce qui rend
            # l'opération idempotente même si la suppression préalable a échoué.
            chunk_id = str(uuid.uuid5(uuid.UUID(document_id), str(chunk.index)))
            payload = dict(payload_base)
            payload.update({"chunk_id": chunk_id, "chunk_index": chunk.index, "page": chunk.page,
                            "section": chunk.section})
            points.append(construire_point(chunk_id, vecteur, chunk.texte, payload))

        # Les lots Qdrant sont indépendants des lots d'embeddings : le premier
        # est dimensionné par le réseau, le second par la mémoire du modèle.
        for sous_lot in _lots(points, settings.QDRANT_BATCH_SIZE):
            upsert_batch(settings, sous_lot, collection)
        total += len(points)

    enregistrer_document(
        session,
        {
            "id": document_id,
            "filename": fichier.chemin.name,
            "original_path": str(fichier.chemin),
            "relative_path": fichier.chemin_relatif,
            "checksum": checksum,
            "mime_type": mime_type(fichier.chemin),
            "size": fichier.taille,
            "document_type": fichier.document_type,
            "category": categorie,
            "source": source,
            "title": infos.get("title"),
            "author": infos.get("author"),
            "language": infos.get("language"),
            "isbn": infos.get("isbn"),
            "publisher": infos.get("publisher"),
            "year": infos.get("year"),
            "chunk_count": total,
            "status": StatutDocument.INDEXE if total else StatutDocument.IGNORE,
            "indexed_at": datetime.now(timezone.utc),
            "source_mtime": fichier.mtime,
            "error_message": None,
            "doc_metadata": {k: v for k, v in infos.items() if k not in {"title", "author"}},
        },
    )
    return total, document_id


def ingerer(
    racine: str | Path,
    settings: Settings,
    provider: EmbeddingProvider,
    session,
    mode: str = "incremental",
    source: str = "library",
    categorie: str | None = None,
    tags: list[str] | None = None,
    progression: Callable[[str, Compteurs], None] | None = None,
    supprimer_absents: bool = False,
    extensions: set[str] | None = None,
    profondeur_max: int | None = None,
) -> Compteurs:
    """Ingère un dossier entier.

    ``mode='full'`` réindexe tout ; ``mode='incremental'`` (défaut) n'indexe
    que les fichiers nouveaux ou modifiés. Le mode incrémental est le défaut
    parce que c'est celui qu'on exécute cent fois, alors qu'une reconstruction
    complète est un événement rare.

    ``extensions`` et ``profondeur_max`` sont transmis tels quels à
    ``parcourir``. Ils EXISTENT pour que l'inventaire préalable (mode
    « --dry-run » d'un script d'import) et l'import réel parcourent
    exactement le même ensemble de fichiers. Sans eux, un appelant pouvait
    restreindre son inventaire puis lancer une ingestion non restreinte :
    l'aperçu annonçait trois documents et l'import en avalait deux cents.
    """
    compteurs = Compteurs()
    assurer_collection(settings, provider.dimension)

    # Index chargé une fois : voir repository.index_bibliotheque.
    connus = index_bibliotheque(session) if mode != "full" else {}
    vus_sur_disque: set[str] = set()
    dedup = DeduplicateurChunks()

    for fichier in parcourir(
        racine,
        extensions=extensions,
        taille_max_mo=settings.INGEST_MAX_FILE_MB,
        profondeur_max=profondeur_max,
    ):
        compteurs.vus += 1
        chemin_str = str(fichier.chemin)
        vus_sur_disque.add(chemin_str)

        if fichier.icloud_absent:
            compteurs.icloud_absents += 1
            compteurs.details.append(f"icloud_not_downloaded: {fichier.chemin_relatif}")
            _marquer_erreur(session, fichier, StatutDocument.ICLOUD_NON_TELECHARGE,
                            "Fichier iCloud non téléchargé localement")
            if progression:
                progression(fichier.chemin_relatif, compteurs)
            continue

        entree = connus.get(chemin_str)
        if entree and fichier_inchange(fichier.chemin, entree[1], entree[2]):
            compteurs.ignores += 1
            if progression:
                progression(fichier.chemin_relatif, compteurs)
            continue

        debut = time.perf_counter()
        try:
            if entree:
                # Réindexation : les anciens chunks sont retirés AVANT d'écrire
                # les nouveaux, sinon l'index cumulerait deux versions du même
                # document et les citations deviendraient contradictoires.
                supprimer_par_document(settings, entree[0])

            nb, _ = indexer_fichier(
                fichier, settings, provider, session, dedup,
                source=source, categorie=categorie, tags=tags,
            )
            compteurs.indexes += 1
            compteurs.chunks += nb
            log.info(
                "document_indexe",
                file=fichier.chemin_relatif,
                chunks=nb,
                duration_ms=round((time.perf_counter() - debut) * 1000, 1),
            )
        except FormatNonSupporte:
            compteurs.ignores += 1
        except Exception as exc:  # capture large : voir docstring du module
            compteurs.erreurs += 1
            compteurs.details.append(f"error: {fichier.chemin_relatif} — {type(exc).__name__}: {exc}")
            log.error("document_erreur", file=fichier.chemin_relatif, error=str(exc), exc_info=True)
            _marquer_erreur(session, fichier, StatutDocument.ERREUR, f"{type(exc).__name__}: {exc}"[:2000])

        if progression:
            progression(fichier.chemin_relatif, compteurs)

    compteurs.doublons_chunks = dedup.doublons

    if supprimer_absents and mode != "full":
        # Un fichier absent du disque n'est marqué supprimé QUE si la racine a
        # bien été parcourue : un volume iCloud non monté ferait sinon
        # disparaître toute la bibliothèque de l'index.
        disparus = [
            doc_id for chemin, (doc_id, _, _) in connus.items()
            if chemin.startswith(str(Path(racine).expanduser())) and chemin not in vus_sur_disque
        ]
        for doc_id in disparus:
            supprimer_par_document(settings, doc_id)
        compteurs.supprimes = marquer_documents(session, disparus, StatutDocument.SUPPRIME)

    return compteurs


def _marquer_erreur(session, fichier: FichierDecouvert, statut: StatutDocument, message: str) -> None:
    """Trace l'échec sans interrompre le flux.

    L'écriture est elle-même protégée : si la base est momentanément
    indisponible, la perte de la trace est préférable à l'arrêt de l'import.
    """
    try:
        enregistrer_document(
            session,
            {
                "id": str(uuid.uuid4()),
                "filename": fichier.chemin.name,
                "original_path": str(fichier.chemin),
                "relative_path": fichier.chemin_relatif,
                # Empreinte de substitution : le contenu est inaccessible, mais
                # la contrainte d'unicité exige une valeur stable pour ce chemin.
                "checksum": f"unavailable:{abs(hash(str(fichier.chemin)))}",
                "size": fichier.taille,
                "document_type": fichier.document_type,
                "status": statut,
                "error_message": message,
                "source_mtime": fichier.mtime,
                "chunk_count": 0,
            },
        )
    except Exception as exc:  # pragma: no cover
        log.warning("trace_erreur_impossible", error=str(exc))
