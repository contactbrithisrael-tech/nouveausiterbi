"""Accès aux données : toutes les requêtes SQL du projet vivent ici.

Pourquoi une couche dédiée
--------------------------
Le reste du code (bot, RAG, ingestion) ne construit jamais de requête. Cela
donne un seul endroit où vérifier qu'aucune boucle ne déclenche une requête
par élément — l'erreur qui rend une ingestion de plusieurs millions de chunks
impraticable. Les insertions en masse passent par ``bulk_*`` et par
``ON CONFLICT``, jamais par un ``for`` autour d'un ``add()``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.database.models import (
    Conversation,
    Document,
    IngestionJob,
    Message,
    StatutDocument,
    StatutJob,
    Utilisateur,
    maintenant,
)

# ═══════════════════════════════════════════════════════════════════
# Utilisateurs et conversations (asynchrone — chemin du bot)
# ═══════════════════════════════════════════════════════════════════


async def obtenir_ou_creer_utilisateur(
    session: AsyncSession,
    telegram_user_id: int,
    username: str | None = None,
    first_name: str | None = None,
    language_code: str | None = None,
) -> Utilisateur:
    """Upsert atomique.

    ``ON CONFLICT DO UPDATE`` plutôt qu'un SELECT suivi d'un INSERT : deux
    messages envoyés simultanément par un nouvel utilisateur provoqueraient
    sinon une violation de contrainte d'unicité, et l'un des deux serait
    perdu. La base tranche, pas le code.
    """
    stmt = (
        pg_insert(Utilisateur)
        .values(
            telegram_user_id=telegram_user_id,
            username=username,
            first_name=first_name,
            language_code=language_code,
            first_seen=maintenant(),
            last_seen=maintenant(),
        )
        .on_conflict_do_update(
            index_elements=[Utilisateur.telegram_user_id],
            set_={"last_seen": maintenant(), "username": username, "first_name": first_name},
        )
        .returning(Utilisateur)
    )
    resultat = await session.execute(stmt)
    return resultat.scalar_one()


async def obtenir_ou_creer_conversation(
    session: AsyncSession, user_id: int, telegram_chat_id: int
) -> Conversation:
    stmt = select(Conversation).where(
        Conversation.user_id == user_id,
        Conversation.telegram_chat_id == telegram_chat_id,
        Conversation.is_active.is_(True),
    )
    conversation = (await session.execute(stmt)).scalar_one_or_none()
    if conversation is None:
        conversation = Conversation(user_id=user_id, telegram_chat_id=telegram_chat_id)
        session.add(conversation)
        await session.flush()
    return conversation


async def ajouter_message(
    session: AsyncSession,
    conversation_id: int,
    role: str,
    content: str,
    sources: dict[str, Any] | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    latency_ms: float | None = None,
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources=sources,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=latency_ms,
    )
    session.add(message)
    await session.flush()
    return message


async def messages_recents(
    session: AsyncSession, conversation_id: int, limite: int, apres_id: int | None = None
) -> list[Message]:
    """Les ``limite`` derniers messages, rendus dans l'ordre chronologique.

    Le tri descendant sert l'index ; l'inversion se fait en Python sur une
    liste de vingt éléments, ce qui est gratuit. Trier en ascendant avec
    OFFSET obligerait PostgreSQL à parcourir tout l'historique.
    """
    stmt = select(Message).where(Message.conversation_id == conversation_id)
    if apres_id is not None:
        stmt = stmt.where(Message.id > apres_id)
    stmt = stmt.order_by(Message.created_at.desc(), Message.id.desc()).limit(limite)
    lignes = list((await session.execute(stmt)).scalars())
    return list(reversed(lignes))


async def compter_messages_conversation(session: AsyncSession, conversation_id: int) -> int:
    stmt = select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
    return int((await session.execute(stmt)).scalar_one())


async def enregistrer_resume(
    session: AsyncSession, conversation_id: int, resume: str, jusqu_au_message_id: int
) -> None:
    await session.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(summary=resume, summary_until_message_id=jusqu_au_message_id)
    )


async def statistiques(session: AsyncSession) -> dict[str, int]:
    """Compteurs pour /stats.

    Une seule requête par agrégat, sans jointure : les compteurs sont
    indépendants et les combiner ne ferait qu'alourdir le plan.
    """
    utilisateurs = (await session.execute(select(func.count(Utilisateur.id)))).scalar_one()
    messages = (await session.execute(select(func.count(Message.id)))).scalar_one()
    documents = (
        await session.execute(
            select(func.count(Document.id)).where(Document.status == StatutDocument.INDEXE)
        )
    ).scalar_one()
    chunks = (
        await session.execute(
            select(func.coalesce(func.sum(Document.chunk_count), 0)).where(
                Document.status == StatutDocument.INDEXE
            )
        )
    ).scalar_one()
    return {
        "utilisateurs": int(utilisateurs),
        "messages": int(messages),
        "documents": int(documents),
        "chunks": int(chunks),
    }


async def sources_principales(session: AsyncSession, limite: int = 20) -> list[tuple[str, int]]:
    """Documents les plus volumineux de l'index, pour /sources."""
    stmt = (
        select(Document.filename, Document.chunk_count)
        .where(Document.status == StatutDocument.INDEXE)
        .order_by(Document.chunk_count.desc())
        .limit(limite)
    )
    return [(f, int(c)) for f, c in (await session.execute(stmt)).all()]


# ═══════════════════════════════════════════════════════════════════
# Documents (synchrone — chemin de l'ingestion)
# ═══════════════════════════════════════════════════════════════════


def document_par_checksum(session: Session, checksum: str) -> Document | None:
    return session.execute(
        select(Document).where(Document.checksum == checksum)
    ).scalar_one_or_none()


def document_par_chemin(session: Session, chemin: str) -> Document | None:
    return session.execute(
        select(Document).where(Document.original_path == chemin)
    ).scalar_one_or_none()


def checksums_connus(session: Session) -> set[str]:
    """Toutes les empreintes déjà indexées, en une requête.

    Chargées une fois en mémoire au début d'un scan plutôt qu'interrogées
    fichier par fichier : sur 50 000 livres, cela remplace 50 000
    allers-retours par un seul, et l'ensemble tient dans quelques mégaoctets.
    """
    lignes = session.execute(select(Document.checksum)).scalars()
    return set(lignes)


def index_bibliotheque(session: Session) -> dict[str, tuple[str, str, float | None]]:
    """Index ``chemin -> (id, checksum, mtime)`` pour les scans incrémentaux."""
    lignes = session.execute(
        select(Document.original_path, Document.id, Document.checksum, Document.source_mtime)
    ).all()
    return {chemin: (doc_id, checksum, mtime) for chemin, doc_id, checksum, mtime in lignes}


def enregistrer_document(session: Session, valeurs: dict[str, Any]) -> Document:
    """Insère ou met à jour un document par son empreinte.

    Le conflit se résout sur ``checksum`` : réimporter un fichier identique
    depuis un autre chemin met simplement à jour le chemin connu, sans créer
    de doublon ni relancer d'indexation.
    """
    stmt = (
        pg_insert(Document)
        .values(**valeurs)
        .on_conflict_do_update(
            index_elements=[Document.checksum],
            set_={
                k: valeurs[k]
                for k in (
                    "original_path",
                    "relative_path",
                    "filename",
                    "status",
                    "chunk_count",
                    "indexed_at",
                    "source_mtime",
                    "error_message",
                )
                if k in valeurs
            },
        )
        .returning(Document)
    )
    return session.execute(stmt).scalar_one()


def marquer_documents(session: Session, ids: Sequence[str], statut: StatutDocument) -> int:
    """Change le statut d'un lot de documents en une seule requête."""
    if not ids:
        return 0
    resultat = session.execute(
        update(Document).where(Document.id.in_(list(ids))).values(status=statut)
    )
    return int(resultat.rowcount or 0)


def creer_job(session: Session, source_path: str, mode: str) -> IngestionJob:
    job = IngestionJob(source_path=source_path, mode=mode)
    session.add(job)
    session.flush()
    return job


def cloturer_job(
    session: Session, job: IngestionJob, compteurs: dict[str, int], erreur: str | None = None
) -> None:
    job.files_seen = compteurs.get("vus", 0)
    job.files_indexed = compteurs.get("indexes", 0)
    job.files_skipped = compteurs.get("ignores", 0)
    job.files_failed = compteurs.get("erreurs", 0)
    job.chunks_created = compteurs.get("chunks", 0)
    job.status = StatutJob.ERREUR if erreur else StatutJob.TERMINE
    job.error_message = erreur
    job.finished_at = datetime.now(timezone.utc)
    session.add(job)
