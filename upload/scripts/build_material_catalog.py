#!/usr/bin/env python3
"""Build the v3 master material catalog from the project Excel sources.

Builder revision: 2026-09-29/full-workbook-pass.

Rules:
- Every source observation is preserved with workbook/sheet/row provenance.
- In the five Excel workbooks the "Сухой остаток" field is treated as
  volumetric dry solids (%) as defined by the project owner.
- Never silently replace a source value when sources disagree.
- Numeric ranges such as "95 +/- 3" keep their nominal value plus raw range text.
- Prices and consumption values remain observations when multiple values exist.
"""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict, Counter
from pathlib import Path
from statistics import median
from typing import Any

from openpyxl import load_workbook
import xlrd


ROOT = Path(__file__).resolve().parents[2]
BOOKS = ROOT / "books"
OUT = ROOT / "upload" / "data" / "material_catalog_master_v3.json"
SPKEFFA = ROOT / "upload" / "data" / "spkeffa_catalog.json"

WORKBOOKS = (
    "Системы 1.xls",
    "Системы 2.XLSX",
    "Системы 3.xlsx",
    "Системы 4.xlsx",
    "Таблица на 1 кв.м ЛКМ основная.xlsx",
)

PRODUCT_KEYWORDS = (
    "blank", "эффа", "лит", "kindur", "neomarine", "inelka", "primacor",
    "globalcoat", "ametcor", "декотерм", "изолэо", "церта", "эпипрайм",
    "ппг", "гф-", "эп-", "эпокс", "полиур", "mio", "zinc", "dtm", "tank",
    "finish", "universal", "primer", "coat", "one", "краск", "эмал",
    "грунт", "покрыт", "разбавител", "растворител",
)
GENERIC_EXCLUDE = (
    "система", "антикоррозионн", "предел огнестойкости", "расход лкм",
    "практический расход", "теоретический расход", "толщина покрытия",
    "толщина пленки", "площадь", "цвет", "связующее", "плотность",
    "сухой остаток", "стоимость", "укрывистость", "условия",
)
HEADER_HINTS = {
    "material": ("система покрытия", "материал", "лкм", "наименование"),
    "binder": ("связующее", "тип связующего"),
    "density": ("плотность",),
    "solids": ("сухой остаток", "объемный сухой остаток", "объёмный сухой остаток"),
    "price_kg": ("цена с ндс за кг", "цена за кг", "цена/кг", "цена кг"),
    "price_l": ("цена с ндс за литр", "цена за литр", "цена/л", "цена л"),
    "dft": ("толщина пленки", "толщина плёнки", "толщина покрытия"),
    "coverage": ("укрывистость", "теоретическая укрывистость"),
    "theor_consumption": ("теоретический расход", "теоретический рассход"),
    "pract_consumption": ("практический расход", "практический расход max", "расход с потерями"),
    "manufacturer": ("производитель", "изготовитель"),
    "brand": ("бренд", "марка"),
    "ral": ("ral",),
}


def text(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def norm(s: str) -> str:
    s = text(s).lower().replace("ё", "е")
    s = re.sub(r"[""«»„“”']", " ", s)
    s = re.sub(r"[^0-9a-zа-я.+/-]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def num(v: Any) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return float(v)
    s = text(v)
    if not s:
        return None
    m = re.match(r"^\s*([-+]?\d+(?:[.,]\d+)?)", s.replace("\u00a0", " "))
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def range_text(v: Any) -> str | None:
    s = text(v)
    if "±" in s or "+-" in s or "+/−" in s or "+/-" in s:
        return s
    return None


def likely_material(v: Any) -> bool:
    s = text(v)
    n = norm(s)
    if not n or len(s) > 220:
        return False
    if n in {norm(x) for x in GENERIC_EXCLUDE}:
        return False
    if any(x in n for x in GENERIC_EXCLUDE):
        # Fire-protection product names containing ЭФФА are still accepted.
        if "эффа" not in n and not any(k in n for k in ("blank", "лит", "kindur", "inelka", "primacor", "globalcoat", "ametcor")):
            return False
    if any(k in n for k in PRODUCT_KEYWORDS):
        if n in {"грунт", "эмаль", "краска", "покрытие", "лкм", "растворитель", "разбавитель"}:
            return False
        return True
    return False


def split_multi(v: Any) -> list[str]:
    s = text(v)
    if not s:
        return []
    parts = [p.strip() for p in re.split(r"\s*/\s*|\s*;\s*", s)]
    return [p for p in parts if p]


def load_rows(path: Path) -> list[tuple[str, int, list[Any]]]:
    rows: list[tuple[str, int, list[Any]]] = []
    if path.suffix.lower() == ".xls":
        wb = xlrd.open_workbook(path.as_posix(), on_demand=True)
        try:
            for sh in wb.sheets():
                for r in range(sh.nrows):
                    vals = sh.row_values(r)
                    if any(text(v) for v in vals):
                        rows.append((sh.name, r + 1, vals))
        finally:
            wb.release_resources()
        return rows

    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        for sh in wb.worksheets:
            for rn, row in enumerate(sh.iter_rows(values_only=True), 1):
                vals = list(row)
                if any(text(v) for v in vals):
                    rows.append((sh.title, rn, vals))
    finally:
        wb.close()
    return rows


def header_columns(rows: list[tuple[str, int, list[Any]]]) -> dict[str, list[int]]:
    result: dict[str, list[int]] = defaultdict(list)
    for _sheet, _rn, vals in rows[:80]:
        for col, v in enumerate(vals):
            n = norm(v)
            if not n:
                continue
            for kind, hints in HEADER_HINTS.items():
                if any(h in n for h in hints) and col not in result[kind]:
                    result[kind].append(col)
    return dict(result)


def nearest_right(col: int, cols: list[int], row_len: int) -> int | None:
    choices = [x for x in cols if x >= col]
    if not choices:
        return None
    return min(choices, key=lambda x: x - col) if min(choices, key=lambda x: x - col) - col <= max(30, row_len // 2) else None


def observation_from_row(
    file_name: str,
    sheet: str,
    row_number: int,
    vals: list[Any],
    headers: dict[str, list[int]],
) -> list[dict[str, Any]]:
    candidates = [(i, text(v)) for i, v in enumerate(vals) if likely_material(v)]
    if not candidates:
        return []

    obs: list[dict[str, Any]] = []
    density_cols = headers.get("density", [])
    solid_cols = headers.get("solids", [])
    pk_cols = headers.get("price_kg", [])
    pl_cols = headers.get("price_l", [])
    dft_cols = headers.get("dft", [])
    cov_cols = headers.get("coverage", [])
    tc_cols = headers.get("theor_consumption", [])
    pc_cols = headers.get("pract_consumption", [])
    binder_cols = headers.get("binder", [])
    maker_cols = headers.get("manufacturer", [])
    brand_cols = headers.get("brand", [])
    ral_cols = headers.get("ral", [])

    for col, name in candidates:
        o: dict[str, Any] = {
            "material_name_raw": name,
            "source": {
                "file": file_name,
                "sheet": sheet,
                "row": row_number,
            },
        }

        def take_near(columns: list[int], numeric_only: bool = False) -> Any:
            c = nearest_right(col, columns, len(vals))
            if c is None or c >= len(vals):
                return None
            return vals[c]

        density = take_near(density_cols, True)
        solids = take_near(solid_cols, True)
        pk = take_near(pk_cols, True)
        pl = take_near(pl_cols, True)
        dft = take_near(dft_cols, True)
        cov = take_near(cov_cols, True)
        tc = take_near(tc_cols, True)
        pc = take_near(pc_cols, True)
        maker = take_near(maker_cols)
        brand = take_near(brand_cols)
        binder = take_near(binder_cols)
        ral = take_near(ral_cols)

        # If one property cell contains slash-separated layer values, map the
        # values by candidate order later in the aggregation stage.
        for key, value in (
            ("density", density),
            ("solids_by_volume_percent", solids),
            ("price_per_kg", pk),
            ("price_per_liter", pl),
            ("recommended_dft", dft),
            ("coverage_m2_l", cov),
            ("theoretical_consumption_kg_m2", tc),
            ("practical_consumption_kg_m2", pc),
        ):
            if value not in (None, ""):
                o[key + "_raw"] = text(value)
                parsed = num(value)
                if parsed is not None:
                    o[key] = parsed
                rt = range_text(value)
                if rt:
                    o[key + "_range_text"] = rt

        if maker not in (None, ""):
            o["manufacturer"] = text(maker)
        if brand not in (None, ""):
            o["brand"] = text(brand)
        if binder not in (None, ""):
            o["binder"] = text(binder)
        if ral not in (None, ""):
            o["ral"] = text(ral)
        obs.append(o)

    return obs


def enrich_slash_values(rows_obs: list[dict[str, Any]]) -> None:
    """Repair common side-by-side rows where property cells are packed A/B/C."""
    by_row: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for o in rows_obs:
        s = o["source"]
        by_row[(s["file"], s["sheet"], s["row"])].append(o)

    for group in by_row.values():
        if len(group) < 2:
            continue
        fields = (
            "density", "solids_by_volume_percent", "price_per_kg", "price_per_liter",
            "recommended_dft", "theoretical_consumption_kg_m2", "practical_consumption_kg_m2",
        )
        for field in fields:
            raw_key = field + "_raw"
            packed = [o.get(raw_key, "") for o in group]
            packed_source = next((x for x in packed if "/" in x), None)
            if not packed_source:
                continue
            parts = split_multi(packed_source)
            if len(parts) != len(group):
                continue
            for o, p in zip(sorted(group, key=lambda x: x["source"]["row"]), parts):
                o[field + "_raw"] = p
                v = num(p)
                if v is not None:
                    o[field] = v
                rt = range_text(p)
                if rt:
                    o[field + "_range_text"] = rt


def add_spkeffa_sources(materials: dict[str, dict[str, Any]]) -> None:
    if not SPKEFFA.exists():
        return
    payload = json.loads(SPKEFFA.read_text(encoding="utf-8"))
    for item in payload.get("materials", []):
        raw_name = text(item.get("material_name"))
        if not raw_name:
            continue
        key = norm(raw_name)
        target = materials.setdefault(
            key,
            {
                "material_name": raw_name,
                "aliases": [],
                "observations": [],
                "source_records": [],
            },
        )
        target["aliases"].append(raw_name)
        target["source_records"].append(
            {
                "source": "upload/data/spkeffa_catalog.json",
                "source_ref": payload.get("source_ref"),
                "source_updated": payload.get("source_updated"),
            }
        )
        target.setdefault("catalog_fields", {}).update(
            {k: item.get(k) for k in (
                "manufacturer", "brand", "material_type", "binder_type", "density",
                "solids_percent", "solids_by_volume_percent", "price_per_kg",
                "price_per_liter", "recommended_dft_min", "recommended_dft_max",
                "max_single_layer_dft", "datasheet", "source_url", "notes",
            )}
        )


def choose_single(values: list[float]) -> float | None:
    uniq = sorted({round(v, 8) for v in values})
    if len(uniq) == 1:
        return uniq[0]
    return None


def finalize(materials: dict[str, dict[str, Any]]) -> dict[str, Any]:
    result: list[dict[str, Any]] = []
    for key, item in materials.items():
        observations = item.get("observations", [])
        def vals(field: str) -> list[float]:
            return [float(o[field]) for o in observations if isinstance(o.get(field), (int, float))]

        dens, solids, pk, pl, dft, tc, pc = (
            vals("density"),
            vals("solids_by_volume_percent"),
            vals("price_per_kg"),
            vals("price_per_liter"),
            vals("recommended_dft"),
            vals("theoretical_consumption_kg_m2"),
            vals("practical_consumption_kg_m2"),
        )

        density = choose_single(dens)
        sv = choose_single(solids)

        catalog = item.get("catalog_fields", {})
        if density is None and isinstance(catalog.get("density"), (int, float)):
            density = float(catalog["density"])
        if sv is None and isinstance(catalog.get("solids_by_volume_percent"), (int, float)):
            sv = float(catalog["solids_by_volume_percent"])

        aliases = sorted({x for x in item.get("aliases", []) if x})
        if item.get("material_name") not in aliases:
            aliases.insert(0, item["material_name"])

        out = {
            "material_name": item["material_name"],
            "aliases": aliases,
            "manufacturer": catalog.get("manufacturer") or next((o.get("manufacturer") for o in observations if o.get("manufacturer")), ""),
            "brand": catalog.get("brand") or next((o.get("brand") for o in observations if o.get("brand")), ""),
            "binder": catalog.get("binder_type") or next((o.get("binder") for o in observations if o.get("binder")), ""),
            "material_type": catalog.get("material_type", ""),
            "density": density,
            "solids_by_volume_percent": sv,
            "density_values": sorted({round(v, 8) for v in dens}),
            "solids_by_volume_values": sorted({round(v, 8) for v in solids}),
            "price_per_kg": choose_single(pk),
            "price_per_liter": choose_single(pl),
            "price_observations": sorted({round(v, 8) for v in pk}),
            "price_liter_observations": sorted({round(v, 8) for v in pl}),
            "recommended_dft": choose_single(dft),
            "theoretical_consumption_kg_m2": choose_single(tc),
            "practical_consumption_kg_m2": choose_single(pc),
            "calculation_ready": density is not None and sv is not None,
            "source_records": item.get("source_records", []),
            "observations": observations,
            "catalog_fields": catalog,
        }

        ranges = []
        for o in observations:
            for f in ("density", "solids_by_volume_percent", "price_per_kg", "price_per_liter"):
                rk = f + "_range_text"
                if o.get(rk):
                    ranges.append({"field": f, "value": o[rk], "source": o["source"]})
        if ranges:
            out["range_values"] = ranges

        result.append(out)

    result.sort(key=lambda x: norm(x["material_name"]))
    ready = sum(1 for x in result if x["calculation_ready"])
    named = len(result)
    observations = sum(len(x["observations"]) for x in result)
    return {
        "schema_version": "3.0-material-master-2",
        "generated_by": "upload/scripts/build_material_catalog.py",
        "generated_from": list(WORKBOOKS) + ["upload/data/spkeffa_catalog.json"],
        "project_semantics": {
            "excel_dry_residue_means_volumetric_dry_solids_percent": True,
            "do_not_convert_or_reinterpret_excel_dry_residue_as_mass_solids": True,
            "preserve_conflicts_as_observations": True,
            "preserve_ranges": True,
            "preserve_source_sheet_row": True,
        },
        "summary": {
            "material_records": named,
            "calculation_ready_records": ready,
            "observations": observations,
            "source_workbooks": len(WORKBOOKS),
        },
        "materials": result,
    }


def main() -> None:
    all_observations: list[dict[str, Any]] = []
    missing: list[str] = []

    for file_name in WORKBOOKS:
        path = BOOKS / file_name
        if not path.exists():
            missing.append(file_name)
            continue
        rows = load_rows(path)
        headers = header_columns(rows)
        for sheet, rn, vals in rows:
            all_observations.extend(observation_from_row(file_name, sheet, rn, vals, headers))

    enrich_slash_values(all_observations)

    materials: dict[str, dict[str, Any]] = {}
    for o in all_observations:
        raw = o["material_name_raw"]
        # Remove generic "Грунт"/"Эмаль" prefixes only for canonical key matching;
        # keep the original raw name in aliases and provenance.
        canonical_key = norm(re.sub(r"^(грунт-?эмаль|грунт|эмаль)\s+", "", raw, flags=re.I))
        canonical_key = canonical_key or norm(raw)
        target = materials.setdefault(
            canonical_key,
            {
                "material_name": raw,
                "aliases": [raw],
                "observations": [],
                "source_records": [],
            },
        )
        if len(text(raw)) > len(text(target["material_name"])):
            # Prefer the more descriptive variant when names are variants.
            target["material_name"] = raw
        target["aliases"].append(raw)
        target["observations"].append(o)
        target["source_records"].append(o["source"])

    add_spkeffa_sources(materials)

    out = finalize(materials)
    out["missing_workbooks"] = missing
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out["summary"] | {"missing_workbooks": missing}, ensure_ascii=False))


if __name__ == "__main__":
    main()
