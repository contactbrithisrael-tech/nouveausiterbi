"""Mode d'accès persistant par utilisateur.

Corrige la cause d'un symptôme classique : une authentification acceptée puis
« oubliée » au message suivant. L'état ne peut pas vivre en mémoire de
processus — il ne survivrait ni à un redémarrage, ni à une seconde instance
du bot.

Revision ID: 0002
Revises: 0001
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # server_default : les utilisateurs déjà en base reçoivent « public ».
    # Une colonne nullable aurait laissé des NULL, et tout code lisant un NULL
    # comme « pas encore défini » aurait fini par le traiter comme un cas
    # particulier — donc comme un risque.
    op.add_column(
        "users",
        sa.Column("mode", sa.String(16), nullable=False, server_default="public"),
    )
    op.add_column("users", sa.Column("mode_set_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "mode_set_at")
    op.drop_column("users", "mode")
