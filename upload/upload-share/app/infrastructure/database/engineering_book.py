"""ORM persistence for source-linked engineering book search chunks."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.engine import Base


class EngineeringBookChunkORM(Base):
    """One searchable chunk retained with immutable source identity."""

    __tablename__ = "engineering_book_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    relative_path: Mapped[str] = mapped_column(String(1000), nullable=False, index=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    locator: Mapped[str] = mapped_column(String(100), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "relative_path",
            "sha256",
            "locator",
            name="uq_engineering_book_chunk_source_locator",
        ),
    )
