#!/usr/bin/env python3
"""One-time import of the generated master material catalog into the v3 SQLite DB.

The importer deliberately does NOT deduplicate records. The user requested that
duplicate cleanup remain manual after the full source import.

Excel semantics:
- 'Сухой остаток' from the five workbooks is volumetric dry solids and is
  stored only in MaterialORM.solids_by_volume_percent.
- solids_percent is left untouched/None for these workbook-derived records.

Idempotency:
- A marker file in data/ prevents the application from re-importing the same
  catalog revision after the user manually removes duplicates.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import DATA_DIR
from app.infrastructure.database.engine import get_engine, get_session_factory, init_db
from app.infrastructure.database.models import MaterialORM
from app.domain.enums import MaterialType, BinderType

CATALOG_PATH = DATA_DIR / "material_catalog_master_v3.json"
IMPORT_MARKER = DATA_DIR / ".material_master_imported_v4"
IMPORT_SOURCE_VERSION = "4"

TYPE_MAP = {x.value: x.value for x in MaterialType}
BINDER_MAP = {x.value: x.value for x in BinderType}


def _safe_type(value: Any, status: str) -> str:
    if status == "THINNER":
        return MaterialType.THINNER.value
    if isinstance(value, str) and value in TYPE_MAP:
        return value
    return MaterialType.OTHER.value


def _safe_binder(value: Any) -> str:
    if isinstance(value, str) and value in BINDER_MAP:
        return value
    return BinderType.UNKNOWN.value


def _source_note(item: dict[str, Any]) -> str:
    observations = item.get("observations", [])
    sources = sorted({
        o.get("source", {}).get("file", "")
        for o in observations
        if o.get("source", {}).get("file")
    })
    aliases = [x for x in item.get("aliases", []) if x]
    parts = [
        "Импорт из master-каталога v3.",
        f"Наблюдений: {len(observations)}.",
        f"Источники: {'; '.join(sources)}." if sources else "",
        f"Алиасы: {'; '.join(dict.fromkeys(aliases))}." if aliases else "",
        "Сухой остаток Excel интерпретирован как объёмный сухой остаток."
        if item.get("solids_by_volume_percent") is not None else "",
    ]
    if item.get("range_values"):
        parts.append("Диапазонные значения сохранены в master JSON.")
    return " ".join(x for x in parts if x)


def _build_fields(item: dict[str, Any]) -> dict[str, Any]:
    status = item.get("status", "MATERIAL")
    density = item.get("density")
    sv = item.get("solids_by_volume_percent")
    fields: dict[str, Any] = {
        "manufacturer": item.get("manufacturer") or "",
        "brand": item.get("brand") or "",
        "material_name": item["material_name"],
        "material_type": _safe_type(item.get("material_type"), status),
        "binder_type": _safe_binder(item.get("binder")),
        "description": "",
        "density": density,
        # Do not copy Excel dry residue into mass-solids field.
        "solids_percent": None,
        "solids_by_volume_percent": sv,
        "price_per_kg": item.get("price_per_kg"),
        "price_per_liter": item.get("price_per_liter"),
        "prices_include_vat": True,
        "recommended_dft_min": None,
        "recommended_dft_max": None,
        "is_two_component": False,
        "is_active": True,
        "is_incomplete": density is None or sv is None,
        "notes": _source_note(item),
    }
    # A single recommended DFT is not copied into min/max because doing so
    # would manufacture a range that the source did not provide.
    if item.get("catalog_fields"):
        catalog = item["catalog_fields"]
        for key in (
            "manufacturer", "brand", "price_per_kg", "price_per_liter",
            "recommended_dft_min", "recommended_dft_max", "max_single_layer_dft",
            "voc", "color", "ral", "theoretical_coverage",
            "min_application_temperature", "max_application_temperature",
            "min_recoat_time_h", "max_recoat_time_h", "drying_time_h",
            "full_cure_time_h", "pot_life_h", "induction_time_min",
            "max_relative_humidity", "min_dew_point_margin_c",
            "thinner_required", "thinner_name", "thinner_percent_min",
            "thinner_percent_max", "thinner_basis", "packaging_kg",
            "packaging_l", "is_two_component", "datasheet", "datasheet_version",
            "datasheet_date", "safety_data_sheet", "certificate",
            "certificate_version", "test_protocol",
        ):
            if catalog.get(key) is not None:
                fields[key] = catalog[key]
        # Keep workbook volumetric solids authoritative for Excel-derived records.
        if sv is not None:
            fields["solids_by_volume_percent"] = sv
        if density is not None:
            fields["density"] = density
        fields["is_incomplete"] = fields["density"] is None or fields["solids_by_volume_percent"] is None
    return fields


def import_master(*, force: bool = False) -> dict[str, int]:
    if IMPORT_MARKER.exists() and not force:
        return {"inserted": 0, "updated": 0, "skipped_marker": 1}

    if not CATALOG_PATH.exists():
        raise FileNotFoundError(f"Master catalog not found: {CATALOG_PATH}")

    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    records = payload.get("materials", [])
    now = datetime.now(timezone.utc)

    init_db()
    session_factory = get_session_factory(get_engine())
    inserted = 0
    updated = 0

    with session_factory() as session:
        for item in records:
            name = str(item.get("material_name") or "").strip()
            if not name:
                continue
            fields = _build_fields(item)
            existing = session.query(MaterialORM).filter_by(material_name=name).first()
            if existing is None:
                session.add(MaterialORM(**fields, created_at=now, updated_at=now))
                inserted += 1
            else:
                # Update only fields represented by the master catalog; do not
                # erase manually enriched values when master has no value.
                for key, value in fields.items():
                    if key in {"manufacturer", "brand", "material_type", "binder_type", "is_active", "is_incomplete", "notes"}:
                        setattr(existing, key, value)
                    elif value is not None:
                        setattr(existing, key, value)
                existing.updated_at = now
                updated += 1
        session.commit()

    IMPORT_MARKER.write_text(
        json.dumps(
            {
                "import_version": IMPORT_SOURCE_VERSION,
                "catalog_schema_version": payload.get("schema_version"),
                "imported_at": now.isoformat(),
                "records_seen": len(records),
                "inserted": inserted,
                "updated": updated,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {"inserted": inserted, "updated": updated, "records_seen": len(records)}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Run even when the import marker exists.")
    args = parser.parse_args()
    print(json.dumps(import_master(force=args.force), ensure_ascii=False))
