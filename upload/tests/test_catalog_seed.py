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
    payload=json.loads(CATALOG.read_text(encoding="utf-8")); assert payload["source_repository"]=="kappamaag-crypto/SPKEFFA"
    for item in payload["materials"]:
        if item.get("solids_by_volume_percent") is None:
            assert item.get("solids_by_volume_percent") is None

def test_seed_catalog_is_idempotent() -> None:
    engine=create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine); Session=sessionmaker(bind=engine,expire_on_commit=False)
    with Session() as session:
        first=seed_spkeffa_catalog(session); session.commit(); counts=(session.query(MaterialORM).count(),session.query(MaterialMixORM).count(),session.query(MaterialComponentORM).count())
        second=seed_spkeffa_catalog(session); session.commit(); counts2=(session.query(MaterialORM).count(),session.query(MaterialMixORM).count(),session.query(MaterialComponentORM).count())
    assert first and second==first and counts2==counts
