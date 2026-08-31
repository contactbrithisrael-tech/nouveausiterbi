"""Schéma initial de Joshua.

Migration écrite à la main plutôt qu'autogénérée : le résultat est lisible,
les index portent des noms explicites, et l'ordre de création est maîtrisé.
Une première migration autogénérée est le plus souvent illisible et contient
des artefacts propres à la base de développement.

Revision ID: 0001
Revises:
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(128)),
        sa.Column("first_name", sa.String(128)),
        sa.Column("language_code", sa.String(16)),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_telegram_user_id", "users", ["telegram_user_id"], unique=True)

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("summary", sa.Text()),
        sa.Column("summary_until_message_id", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_conversations_user_chat", "conversations", ["user_id", "telegram_chat_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversation_id", sa.Integer(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sources", postgresql.JSONB()),
        sa.Column("tokens_in", sa.Integer()),
        sa.Column("tokens_out", sa.Integer()),
        sa.Column("latency_ms", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    # Index composite : sert la requête de l'historique récent, exécutée à
    # chaque message reçu. C'est le seul index réellement critique du schéma.
    op.create_index("ix_messages_conversation_created", "messages", ["conversation_id", "created_at"])

    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("original_path", sa.Text(), nullable=False),
        sa.Column("relative_path", sa.Text()),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("mime_type", sa.String(128)),
        sa.Column("size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("document_type", sa.String(32)),
        sa.Column("category", sa.String(64)),
        sa.Column("source", sa.String(64)),
        sa.Column("title", sa.String(512)),
        sa.Column("author", sa.String(512)),
        sa.Column("language", sa.String(16)),
        sa.Column("isbn", sa.String(32)),
        sa.Column("publisher", sa.String(256)),
        sa.Column("year", sa.Integer()),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text()),
        sa.Column("metadata", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("indexed_at", sa.DateTime(timezone=True)),
        sa.Column("source_mtime", sa.Float()),
    )
    # Contrainte d'unicité sur l'empreinte : c'est ELLE qui implémente la
    # déduplication, pas le code applicatif. Deux ingestions simultanées du
    # même fichier ne peuvent donc pas créer de doublon.
    op.create_unique_constraint("uq_documents_checksum", "documents", ["checksum"])
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_category", "documents", ["category"])
    op.create_index("ix_documents_original_path", "documents", ["original_path"])

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("mode", sa.String(32), nullable=False, server_default="incremental"),
        sa.Column("status", sa.String(32), nullable=False, server_default="running"),
        sa.Column("files_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_indexed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunks_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("ingestion_jobs")
    op.drop_index("ix_documents_original_path", table_name="documents")
    op.drop_index("ix_documents_category", table_name="documents")
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_messages_conversation_created", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_user_chat", table_name="conversations")
    op.drop_table("conversations")
    op.drop_index("ix_users_telegram_user_id", table_name="users")
    op.drop_table("users")
