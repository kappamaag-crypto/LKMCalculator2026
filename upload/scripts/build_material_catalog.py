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

import csv
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
CSV_OUT = ROOT / "upload" / "data" / "material_catalog_master_v3.csv"
REVIEW_CSV_OUT = ROOT / "upload" / "data" / "material_catalog_review_candidates_v3.csv"
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


def likely_material(v: Any, vals: list[Any] | None = None, col: int | None = None, headers: dict[str, list[int]] | None = None) -> bool:
    s = text(v)
    n = norm(s)
    if not n or len(s) > 180:
        return False
    negative = (
        "определите", "выберите", "протокол ил", "предел огнестойкости", "описание",
        "антикоррозионная защита", "внутреннее покрытие", "наружное покрытие",
        "описание:", "на сварных швах", "толщина сухого слоя",
        "расход лкм", "практический расход", "теоретический расход",
        "площадь", "увеличение количества", "группы лакокрасочных",
        "без лакокрасочного", "для цинкового покрытия", "кол-во разбавителя",
        "цена с ндс", "стоимость", "нанесение грунтовочного",
        "нанесение финишного", "углеродистая и низколегированная сталь",
        "материал металлических защитных покрытий", "сайт:", ".ru", ".com",
        "ооо ", "оао ", "пао ", "техническое задание", "инструкция",
    )
    if any(x in n for x in negative):
        return False
    if re.match(r"^(разбавитель|растворитель)\b", n, re.I):
        return True
    generic = {
        "грунт", "эмаль", "краска", "покрытие", "состав", "лкм",
        "растворитель", "разбавитель", "эпоксид", "полиуретан",
        "акрил", "фенолэпоксид", "эпоксидная грунт эмаль",
    }
    if n in generic:
        return False
    positive = (
        "blank", "эффа", "литап", "литакоут", "литамастик", "литатанк",
        "литатерм", "литачар", "kindur", "neomarine", "inelka", "prim",
        "globalcoat", "globaltop", "ametcor", "декотерм", "изолэ",
        "ecomast", "masscotank", "stelpant", "wg-", "эметалл",
        "эпипрайм", "эпоксикоут", "dyopox", "церта", "гф-021",
        "эп-0199", "эп-0110", "полак", "политон", "lakra", "урпейнт",
        "dyo", "veksa",
    )
    if any(x in n for x in positive):
        return True
    if re.search(r"\b(?:эп|пф|гф|ко|ур|прим|стелпант|полак|политон)[- ]?\d{2,}", n, re.I):
        return True
    if vals is not None and col is not None and headers is not None:
        if col in headers.get("material", []):
            return True
        property_cols: list[int] = []
        for kind in ("density", "solids", "price_kg", "price_l", "dft", "coverage", "theor_consumption", "pract_consumption"):
            property_cols.extend(headers.get(kind, []))
        if any(abs(col - pc) <= 6 for pc in property_cols):
            for pc in property_cols:
                if 0 <= pc < len(vals) and abs(col - pc) <= 6:
                    value = vals[pc]
                    if num(value) is not None:
                        return True
                    parts = split_multi(value)
                    if len(parts) >= 2 and all(num(p) is not None for p in parts):
                        return True
    return False


def canonicalize_material_name(raw: str) -> str | None:
    s = text(raw).replace("ё", "е")
    n = norm(s)

    # Explicit thinner entity.
    if re.match(r"^(разбавитель|растворитель)\b", n, re.I):
        return re.sub(r"\s+", " ", s).strip()

    rejects = (
        r"^описание\b", r"^протокол\s", r"^система(\s|$)", r"^акз(\s|$)",
        r"^антикоррозионная\s+защита", r"^внутренн", r"^наружн",
        r"^площад", r"^определ", r"^выбер", r"^без\s+лакокрасоч",
        r"^толщина\s", r"^кол-во\s+разбав", r"^предел\s+огнестой",
        r"^группы\s+лакокрасоч", r"^нанесение\s", r"^увеличение\s",
        r"^материал\s+металлических", r"^ооо\s", r"^цена\s+с\s+ндс",
        r"^площаль\b", r"^площадь\b", r"^кол-во\s+разбав",
        r"^стоимость", r"^полиуретан$", r"^эпоксид$", r"^связующее$",
        r"^пк\s", r"\bсайт\s*:", r"\.ru\b", r"\.com\b", r"^ооо\s", r"^оао\s", r"^пао\s",
    )
    if any(re.search(p, n, re.I) for p in rejects):
        return None

    # Composite/system labels are not standalone material entities.
    if " + " in s or " плюс " in n:
        return None

    # Remove layer counters and product-type prefixes.
    s = re.sub(r"^\s*\d+\s*(?:слой|слоя)\s+", "", s, flags=re.I)
    s = re.sub(
        r"^(?:грунт-?эмаль|грунтовка|грунт|эмаль|краска|"
        r"огнезащитный состав|огнезащита|теплоизолирующий состав|"
        r"теплоогнезащитный состав)\s*[:：]?\s*",
        "",
        s,
        flags=re.I,
    )

    # Remove RAL and explicit fire-test qualifiers from the material key.
    s = re.sub(r"\s+Ral\s*[-:]?\s*\d{3,4}\b", "", s, flags=re.I)
    s = re.sub(r"\s+R\s*\d+\b.*$", "", s, flags=re.I)
    s = re.sub(r"\s+ПТМ\s*[-–—:]?\s*[0-9.,]+\s*мм.*$", "", s, flags=re.I)
    s = re.sub(r"\s+(?:для\s+УГВ\s+режима|УГВ)$", "", s, flags=re.I)
    s = re.sub(r"\s+(?:или\s+ЭФФА[- ]?ЭП[- ]?150К)$", "", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip(" -–—:;,")
    if not s:
        return None

    aliases = {
        "blank universal": "Blank Universal",
        "blank finish": "Blank Finish",
        "blank hp": "Blank HP",
        "blank tank": "Blank Tank",
        "blank tank lp": "Blank Tank LP",
        "blank mio": "Blank MIO",
        "blank zinc": "Blank Zinc",
        "blank dtm": "Blank DTM",
        "blank one": "Blank One",
        "литатанк стандарт": "Литатанк Стандарт",
        "литатанк стронг": "Литатанк Стронг",
        "литакоут классик": "Литакоут Классик",
        "литакоут классик фрост": "Литакоут Классик (Фрост)",
        "литакоут классик/фрост": "Литакоут Классик/Фрост",
    }
    key = norm(s)
    if "blank mio" in key:
        return "Blank MIO"
    if "blank zinc" in key:
        return "Blank Zinc"
    if "blank universal" in key:
        return "Blank Universal"
    if "blank finish" in key:
        return "Blank Finish"
    if "blank tank lp" in key:
        return "Blank Tank LP"
    if "blank tank" in key:
        return "Blank Tank"
    if "blank hp" in key:
        return "Blank HP"
    if key in aliases:
        return aliases[key]
    return s


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
    candidates = [(i, text(v)) for i, v in enumerate(vals) if likely_material(v, vals, i, headers)]
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
            "material_column": col,
            "source": {
                "file": file_name,
                "sheet": sheet,
                "row": row_number,
            },
        }

        def take_near(columns: list[int], numeric_only: bool = False) -> Any:
            ordered = sorted((x for x in columns if x >= col), key=lambda x: x - col)
            for c in ordered:
                if c >= len(vals):
                    continue
                value = vals[c]
                if not numeric_only:
                    return value
                parts = split_multi(value)
                if num(value) is not None or (len(parts) > 1 and all(num(p) is not None for p in parts)):
                    return value
            return None

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
    """Map packed A/B/C side-by-side properties by material-cell order."""
    by_row: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for o in rows_obs:
        s = o["source"]
        by_row[(s["file"], s["sheet"], s["row"])].append(o)

    fields = (
        "density", "solids_by_volume_percent", "price_per_kg", "price_per_liter",
        "recommended_dft", "theoretical_consumption_kg_m2", "practical_consumption_kg_m2",
    )
    for group in by_row.values():
        if len(group) < 2:
            continue
        group = sorted(group, key=lambda x: x.get("material_column", 0))
        for field in fields:
            raw_key = field + "_raw"
            packed_source = None
            for o in group:
                raw = o.get(raw_key, "")
                parts = split_multi(raw)
                if len(parts) == len(group):
                    packed_source = parts
                    break
            if packed_source is None:
                continue
            for o, p in zip(group, packed_source):
                o[raw_key] = p
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
    return uniq[0] if len(uniq) == 1 else None


SOURCE_PRIORITY = {
    "Таблица на 1 кв.м ЛКМ основная.xlsx": 100,
    "Системы 3.xlsx": 90,
    "Системы 4.xlsx": 80,
    "Системы 2.XLSX": 70,
    "Системы 1.xls": 60,
}


def choose_preferred(
    observations: list[dict[str, Any]],
    field: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float | None:
    ranked: list[tuple[int, float]] = []
    for o in observations:
        value = o.get(field)
        if not isinstance(value, (int, float)):
            continue
        value = float(value)
        if minimum is not None and value < minimum:
            continue
        if maximum is not None and value > maximum:
            continue
        source = o.get("source", {}).get("file", "")
        ranked.append((SOURCE_PRIORITY.get(source, 0), value))

    if not ranked:
        return None

    highest = max(p for p, _ in ranked)
    top = [v for p, v in ranked if p == highest]
    counts = Counter(round(v, 8) for v in top)
    return float(counts.most_common(1)[0][0])



def finalize(materials: dict[str, dict[str, Any]], review_candidates: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    result: list[dict[str, Any]] = []

    for key, item in materials.items():
        observations = item.get("observations", [])
        catalog = item.get("catalog_fields", {})

        density = choose_preferred(observations, "density", minimum=0.5, maximum=5.0)
        sv = choose_preferred(observations, "solids_by_volume_percent", minimum=5.0, maximum=100.0)
        pk = choose_preferred(observations, "price_per_kg", minimum=0.0, maximum=100000.0)
        pl = choose_preferred(observations, "price_per_liter", minimum=0.0, maximum=200000.0)
        dft = choose_preferred(observations, "recommended_dft", minimum=0.0, maximum=10000.0)
        tc = choose_preferred(observations, "theoretical_consumption_kg_m2", minimum=0.0, maximum=1000.0)
        pc = choose_preferred(observations, "practical_consumption_kg_m2", minimum=0.0, maximum=1000.0)

        if density is None and isinstance(catalog.get("density"), (int, float)):
            cv = float(catalog["density"])
            if 0.5 <= cv <= 5:
                density = cv
        if sv is None and isinstance(catalog.get("solids_by_volume_percent"), (int, float)):
            cv = float(catalog["solids_by_volume_percent"])
            if 5 <= cv <= 100:
                sv = cv

        aliases = sorted({x for x in item.get("aliases", []) if x})
        if item.get("material_name") not in aliases:
            aliases.insert(0, item["material_name"])

        out = {
            "material_name": item["material_name"],
            "status": (
                "THINNER"
                if re.match(r"^(разбавитель|растворитель)\b", norm(item["material_name"]), re.I)
                else "MATERIAL"
            ),
            "aliases": aliases,
            "manufacturer": catalog.get("manufacturer") or next(
                (o.get("manufacturer") for o in observations if o.get("manufacturer")), ""
            ),
            "brand": catalog.get("brand") or next(
                (o.get("brand") for o in observations if o.get("brand")), ""
            ),
            "binder": catalog.get("binder_type") or next(
                (o.get("binder") for o in observations if o.get("binder")), ""
            ),
            "material_type": catalog.get("material_type", ""),
            "density": density,
            "solids_by_volume_percent": sv,
            "density_values": sorted({
                round(float(o["density"]), 8)
                for o in observations
                if isinstance(o.get("density"), (int, float)) and 0.5 <= float(o["density"]) <= 5
            }),
            "solids_by_volume_values": sorted({
                round(float(o["solids_by_volume_percent"]), 8)
                for o in observations
                if isinstance(o.get("solids_by_volume_percent"), (int, float))
                and 5 <= float(o["solids_by_volume_percent"]) <= 100
            }),
            "price_per_kg": pk,
            "price_per_liter": pl,
            "price_observations": sorted({
                round(float(o["price_per_kg"]), 8)
                for o in observations
                if isinstance(o.get("price_per_kg"), (int, float))
                and 0 <= float(o["price_per_kg"]) <= 100000
            }),
            "price_liter_observations": sorted({
                round(float(o["price_per_liter"]), 8)
                for o in observations
                if isinstance(o.get("price_per_liter"), (int, float))
                and 0 <= float(o["price_per_liter"]) <= 200000
            }),
            "recommended_dft": dft,
            "theoretical_consumption_kg_m2": tc,
            "practical_consumption_kg_m2": pc,
            "calculation_ready": density is not None and sv is not None,
            "data_quality_status": (\n                "READY" if density is not None and sv is not None\n                else "PARTIAL_DENSITY" if density is not None\n                else "PARTIAL_SOLIDS_BY_VOLUME" if sv is not None\n                else "NAME_ONLY"\n            ),\n            "conflict_fields": [\n                fld for fld, values in (\n                    ("density", sorted({round(float(o["density"]), 8) for o in observations if isinstance(o.get("density"), (int, float)) and 0.5 <= float(o["density"]) <= 5})),\n                    ("solids_by_volume_percent", sorted({round(float(o["solids_by_volume_percent"]), 8) for o in observations if isinstance(o.get("solids_by_volume_percent"), (int, float)) and 5 <= float(o["solids_by_volume_percent"]) <= 100})),\n                ) if len(values) > 1\n            ],\n            "source_records": item.get("source_records", []),
            "observations": observations,
            "catalog_fields": catalog,
        }

        ranges = []
        for o in observations:
            for fld in ("density", "solids_by_volume_percent", "price_per_kg", "price_per_liter"):
                rk = fld + "_range_text"
                if o.get(rk):
                    ranges.append({"field": fld, "value": o[rk], "source": o["source"]})
        if ranges:
            out["range_values"] = ranges

        result.append(out)

    result.sort(key=lambda x: norm(x["material_name"]))
    ready = sum(1 for x in result if x["calculation_ready"])
    material_count = sum(1 for x in result if x["status"] == "MATERIAL")
    thinner_count = sum(1 for x in result if x["status"] == "THINNER")
    observations = sum(len(x["observations"]) for x in result)

    return {
        "schema_version": "3.0-material-master-4",
        "generated_by": "upload/scripts/build_material_catalog.py",
        "generated_from": list(WORKBOOKS) + ["upload/data/spkeffa_catalog.json"],
        "project_semantics": {
            "excel_dry_residue_means_volumetric_dry_solids_percent": True,
            "do_not_convert_or_reinterpret_excel_dry_residue_as_mass_solids": True,
            "preserve_conflicts_as_observations": True,
            "preserve_ranges": True,
            "preserve_source_sheet_row_column": True,
            "source_priority_for_primary_values": [
                "Таблица на 1 кв.м ЛКМ основная.xlsx",
                "Системы 3.xlsx",
                "Системы 4.xlsx",
                "Системы 2.XLSX",
                "Системы 1.xls",
            ],
        },
        "summary": {
            "material_records": material_count,
            "thinner_records": thinner_count,
            "all_records": len(result),
            "calculation_ready_records": ready,
            "observations": observations,
            "source_workbooks": len(WORKBOOKS),
            "excel_dry_residue_semantics": "VOLUMETRIC_DRY_SOLIDS_PERCENT",
        },
        "materials": result,
        "review_candidates": sorted((review_candidates or {}).values(), key=lambda x: norm(x["material_name"])),
    }



def validate_output(output: dict[str, Any]) -> None:
    """Fail the build if obvious system/instruction prose leaked into materials."""
    bad_tokens = (
        "описание", "предел огнестойкости", "антикоррозионная защита",
        "определите", "выберите", "практический расход", "теоретический расход",
        "внутреннее покрытие", "наружное покрытие", "система ", "протокол ил",
        "площадь ", "кол-во разбавителя", "нанесение грунтовочного",
    )
    leaked = [
        m["material_name"]
        for m in output.get("materials", [])
        if m.get("status") == "MATERIAL"
        and any(token in norm(m.get("material_name", "")) for token in bad_tokens)
    ]
    if leaked:
        raise RuntimeError(
            "Material catalog validation failed; non-material names leaked: "
            + "; ".join(leaked[:20])
        )


def main() -> None:
    all_observations: list[dict[str, Any]] = []
    missing: list[str] = []

    for file_name in WORKBOOKS:
        path = BOOKS / file_name
        if not path.exists():
            missing.append(file_name)
            continue
        rows = load_rows(path)
        rows_by_sheet: dict[str, list[tuple[str, int, list[Any]]]] = defaultdict(list)
        for row in rows:
            rows_by_sheet[row[0]].append(row)

        for sheet, sheet_rows in rows_by_sheet.items():
            # Each sheet can have a different layout. Never reuse column maps
            # from another sheet in the same workbook.
            headers = header_columns(sheet_rows)
            for _sheet, rn, vals in sheet_rows:
                all_observations.extend(
                    observation_from_row(file_name, sheet, rn, vals, headers)
                )

    enrich_slash_values(all_observations)

    materials: dict[str, dict[str, Any]] = {}
    review_candidates: dict[str, dict[str, Any]] = {}
    rejected_nonmaterial_observations = 0

    for o in all_observations:
        raw = o["material_name_raw"]
        if not likely_material(raw):
            has_properties = any(
                isinstance(o.get(f), (int, float))
                for f in ("density", "solids_by_volume_percent", "price_per_kg", "price_per_liter", "recommended_dft", "theoretical_consumption_kg_m2", "practical_consumption_kg_m2")
            )
            if has_properties and raw:
                k = norm(raw)
                rc = review_candidates.setdefault(k, {
                    "material_name": raw,
                    "aliases": [],
                    "observations": [],
                    "reason": "property-backed but not confidently classified as a material",
                })
                rc["aliases"].append(raw)
                rc["observations"].append(o)
            rejected_nonmaterial_observations += 1
            continue

        canonical = canonicalize_material_name(raw)
        if canonical is None:
            rejected_nonmaterial_observations += 1
            continue

        canonical_key = norm(canonical)
        target = materials.setdefault(
            canonical_key,
            {
                "material_name": canonical,
                "aliases": [],
                "observations": [],
                "source_records": [],
            },
        )
        target["aliases"].append(raw)
        target["observations"].append(o)
        target["source_records"].append(o["source"])

    add_spkeffa_sources(materials)

    out = finalize(materials, review_candidates)
    validate_output(out)
    out["missing_workbooks"] = missing
    out["summary"]["rejected_nonmaterial_observations"] = rejected_nonmaterial_observations
    out["summary"]["review_candidates"] = len(out.get("review_candidates", []))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    fields = [
        "status", "material_name", "data_quality_status", "calculation_ready",
        "manufacturer", "brand", "binder", "material_type", "density",
        "solids_by_volume_percent", "price_per_kg", "price_per_liter",
        "recommended_dft", "theoretical_consumption_kg_m2", "practical_consumption_kg_m2",
        "conflict_fields", "observation_count", "alias_count", "source_workbooks",
    ]
    with CSV_OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in out["materials"]:
            row2 = dict(row)
            row2["conflict_fields"] = ", ".join(row.get("conflict_fields", []))
            row2["observation_count"] = len(row.get("observations", []))
            row2["alias_count"] = len(row.get("aliases", []))
            sources = sorted({o.get("source", {}).get("file") for o in row.get("observations", []) if o.get("source")})
            row2["source_workbooks"] = " | ".join(sources)
            w.writerow(row2)

    review_fields = ["material_name", "alias_count", "observation_count", "reason", "sources"]
    with REVIEW_CSV_OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=review_fields)
        w.writeheader()
        for row in out.get("review_candidates", []):
            sources = sorted({o.get("source", {}).get("file") for o in row.get("observations", []) if o.get("source")})
            w.writerow({
                "material_name": row.get("material_name", ""),
                "alias_count": len(set(row.get("aliases", []))),
                "observation_count": len(row.get("observations", [])),
                "reason": row.get("reason", ""),
                "sources": " | ".join(sources),
            })

    print(json.dumps(out["summary"] | {"missing_workbooks": missing}, ensure_ascii=False))


if __name__ == "__main__":
    main()
