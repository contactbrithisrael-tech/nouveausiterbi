"""Schéma relationnel de Joshua (SQLAlchemy 2.0).

Répartition des responsabilités
-------------------------------
PostgreSQL détient ce qui doit être **exact, transactionnel et interrogeable
par critère** : utilisateurs, conversations, messages, catalogue documentaire,
journal d'ingestion. Qdrant détient ce qui doit être **cherché par
similarité** : les chunks et leurs vecteurs.

Le texte intégral des chunks n'est PAS dupliqué ici. Le stocker aux deux
endroits doublerait le volume (plusieurs dizaines de Go sur une grande
bibliothèque) pour une donnée que Qdrant retourne déjà avec le résultat.
PostgreSQL conserve en revanche le *comptage* de chunks par document, qui
permet les statistiques sans interroger Qdrant.

Index
-----
Chaque index déclaré ci-dessous répond à une requête réellement effectuée
par le code (recherche par checksum à l'ingestion, historique récent d'une
conversation, documents par statut). Aucun index « au cas où » : ils coûtent
à chaque écriture, et l'ingestion est massivement en écriture.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def maintenant() -> datetime:
    """Horodatage UTC explicite.

    ``datetime.utcnow`` produit un objet naïf : mélangé à des dates
    conscientes du fuseau, il provoque des comparaisons interdites. On force
    donc le fuseau dès la création.
    """
    return datetime.now(timezone.utc)


def nouvel_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class StatutDocument(str, enum.Enum):
    EN_ATTENTE = "pending"
    EN_COURS = "processing"
    INDEXE = "indexed"
    ERREUR = "error"
    IGNORE = "skipped"
    #: Fichier iCloud visible mais non téléchargé localement.
    ICLOUD_NON_TELECHARGE = "icloud_not_downloaded"
    #: Fichier disparu de la bibliothèque source depuis la dernière indexation.
    SUPPRIME = "deleted"


class StatutJob(str, enum.Enum):
    EN_COURS = "running"
    TERMINE = "completed"
    ERREUR = "failed"


class Utilisateur(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # BigInteger obligatoire : les identifiants Telegram dépassent déjà la
    # plage d'un entier 32 bits signé.
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(128))
    first_name: Mapped[str | None] = mapped_column(String(128))
    language_code: Mapped[str | None] = mapped_column(String(16))
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant, nullable=False)

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="utilisateur")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    #: Résumé des échanges anciens, régénéré périodiquement (memory/summary.py).
    summary: Mapped[str | None] = mapped_column(Text)
    summary_until_message_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=maintenant, onupdate=maintenant, nullable=False
    )

    utilisateur: Mapped[Utilisateur] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation")

    __table_args__ = (
        # Une conversation active par salon : la contrainte est portée par la
        # base et non par le code, seule façon de résister à deux messages
        # arrivant simultanément.
        Index("ix_conversations_user_chat", "user_id", "telegram_chat_id"),
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    #: Sources citées, conservées pour l'audit d'une réponse passée.
    sources: Mapped[dict | None] = mapped_column(JSONB)
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant, nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")

    __table_args__ = (
        # Index composite descendant : l'historique récent est LA requête du
        # chemin critique, exécutée à chaque message reçu.
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=nouvel_uuid)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    original_path: Mapped[str] = mapped_column(Text, nullable=False)
    #: Chemin relatif à la racine de la bibliothèque : reste valable si la
    #: bibliothèque est montée ailleurs (autre machine, autre utilisateur).
    relative_path: Mapped[str | None] = mapped_column(Text)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128))
    size: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    document_type: Mapped[str | None] = mapped_column(String(32))
    category: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str | None] = mapped_column(String(64))

    # ── Métadonnées bibliographiques (livres) ───────────────────────
    title: Mapped[str | None] = mapped_column(String(512))
    author: Mapped[str | None] = mapped_column(String(512))
    language: Mapped[str | None] = mapped_column(String(16))
    isbn: Mapped[str | None] = mapped_column(String(32))
    publisher: Mapped[str | None] = mapped_column(String(256))
    year: Mapped[int | None] = mapped_column(Integer)

    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[StatutDocument] = mapped_column(
        Enum(StatutDocument, native_enum=False, length=32),
        default=StatutDocument.EN_ATTENTE,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    doc_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant, nullable=False)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    #: Date de modification du fichier source, comparée au scan suivant.
    source_mtime: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (
        # Unicité par empreinte : c'est la déduplication. Deux exemplaires du
        # même livre dans deux dossiers ne sont indexés qu'une fois.
        UniqueConstraint("checksum", name="uq_documents_checksum"),
        Index("ix_documents_status", "status"),
        Index("ix_documents_category", "category"),
        # Recherche par chemin lors des scans incrémentaux de bibliothèque.
        Index("ix_documents_original_path", "original_path"),
    )


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=nouvel_uuid)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(32), default="incremental", nullable=False)
    status: Mapped[StatutJob] = mapped_column(
        Enum(StatutJob, native_enum=False, length=32), default=StatutJob.EN_COURS, nullable=False
    )
    files_seen: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_indexed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunks_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
