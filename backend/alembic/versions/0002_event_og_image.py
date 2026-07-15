"""Ajoute og_image_url / og_image_checked aux événements

Repli d'image : miniature de prévisualisation (og:image) de la page source,
récupérée à la demande quand l'événement n'a pas d'image propre.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-15

"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("events", sa.Column("og_image_url", sa.String(500), nullable=True))
    op.add_column(
        "events",
        sa.Column(
            "og_image_checked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("events", "og_image_checked")
    op.drop_column("events", "og_image_url")
