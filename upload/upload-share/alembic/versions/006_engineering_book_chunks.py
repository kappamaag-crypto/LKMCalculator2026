"""Persist source-linked engineering book search chunks."""

from alembic import op
import sqlalchemy as sa

revision = "006_engineering_book_chunks"
down_revision = "005_notification_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "engineering_book_chunks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("relative_path", sa.String(length=1000), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("locator", sa.String(length=100), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("indexed_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "relative_path",
            "sha256",
            "locator",
            name="uq_engineering_book_chunk_source_locator",
        ),
    )
    op.create_index(
        "ix_engineering_book_chunks_relative_path",
        "engineering_book_chunks",
        ["relative_path"],
    )
    op.create_index(
        "ix_engineering_book_chunks_sha256",
        "engineering_book_chunks",
        ["sha256"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_engineering_book_chunks_sha256",
        table_name="engineering_book_chunks",
    )
    op.drop_index(
        "ix_engineering_book_chunks_relative_path",
        table_name="engineering_book_chunks",
    )
    op.drop_table("engineering_book_chunks")
