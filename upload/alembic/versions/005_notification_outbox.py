"""Add durable notification outbox for reliable email delivery."""

from alembic import op
import sqlalchemy as sa

revision = "005_notification_outbox"
down_revision = "004_nullable_calculation_inputs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("recipient", sa.String(length=320), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_notification_outbox_idempotency_key"),
    )
    op.create_index("ix_notification_outbox_idempotency_key", "notification_outbox", ["idempotency_key"], unique=True)
    op.create_index("ix_notification_outbox_status", "notification_outbox", ["status"])


def downgrade() -> None:
    op.drop_index("ix_notification_outbox_status", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_idempotency_key", table_name="notification_outbox")
    op.drop_table("notification_outbox")
