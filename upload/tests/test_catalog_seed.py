"""Проверки целостности локального каталога и идемпотентности seed."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.database.engine import Base
from app.infrastructure.database.models import MaterialORM, MaterialMixORM, MaterialComponentORM
from app.infrastructure.database.seed import seed_spkeffa_catalog


CATALOG = Path(__file__).resolve().parents[1] / "data" / "spkeffa_catalog.json"


def test_catalog_does_not_invent_volume_solids() -> None:
    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    assert payload["source_repository"] == "kappamaag-crypto/SPKEFFA"
    for item in payload["materials"]:
        if item.get("solids_by_volume_percent") is None:
            note = item.get("notes", "").lower()
            # Отсутствующие данные остаются неизвестными, а не заменяются массовым сухим остатком.
            assert item.get("solids_by_volume_percent") is None
            assert "не интерпретировать" in note or "не указ" in note or "неизвест" in note


def test_seed_catalog_is_idempotent() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    with Session() as session:
        first = seed_spkeffa_catalog(session)
        session.commit()
        first_count = session.query(MaterialORM).count()
        first_mixes = session.query(MaterialMixORM).count()
        first_components = session.query(MaterialComponentORM).count()

        second = seed_spkeffa_catalog(session)
        session.commit()
        second_count = session.query(MaterialORM).count()
        second_mixes = session.query(MaterialMixORM).count()
        second_components = session.query(MaterialComponentORM).count()

    assert first
    assert second == first
    assert second_count == first_count
    assert second_mixes == first_mixes
    assert second_components == first_components
