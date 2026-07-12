"""Schéma initial : museums, events, alert_subscriptions

Revision ID: 0001
Revises:
Create Date: 2026-07-12

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "museums",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), unique=True),
        sa.Column("address", sa.Text()),
        sa.Column("city", sa.String(100)),
        sa.Column("postal_code", sa.String(10)),
        sa.Column("department", sa.String(50)),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("website_url", sa.String(500)),
        sa.Column("openagenda_uid", sa.String(100)),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("museum_id", sa.Integer(), sa.ForeignKey("museums.id")),
        sa.Column("external_id", sa.String(255)),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("event_type", sa.String(50)),
        sa.Column("date_start", sa.Date(), nullable=False),
        sa.Column("date_end", sa.Date()),
        sa.Column("time_start", sa.Time()),
        sa.Column("time_end", sa.Time()),
        sa.Column("is_permanent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("price_info", sa.String(255)),
        sa.Column("image_url", sa.String(500)),
        sa.Column("event_url", sa.String(500)),
        sa.Column("audience", sa.String(100)),
        sa.Column("raw_data", JSON_TYPE),
        sa.Column("is_duplicate", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("duplicate_of_id", sa.Integer(), sa.ForeignKey("events.id")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("source", "external_id", name="uq_events_source_external_id"),
    )
    op.create_index("ix_events_museum_id", "events", ["museum_id"])
    op.create_index("ix_events_date_start", "events", ["date_start"])
    op.create_index("ix_events_event_type", "events", ["event_type"])
    op.create_index("ix_events_is_duplicate", "events", ["is_duplicate"])

    op.create_table(
        "alert_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("filters", JSON_TYPE),
        sa.Column("frequency", sa.String(20), nullable=False, server_default="weekly"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("token", sa.Uuid(), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("last_sent_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("alert_subscriptions")
    op.drop_index("ix_events_is_duplicate", table_name="events")
    op.drop_index("ix_events_event_type", table_name="events")
    op.drop_index("ix_events_date_start", table_name="events")
    op.drop_index("ix_events_museum_id", table_name="events")
    op.drop_table("events")
    op.drop_table("museums")
