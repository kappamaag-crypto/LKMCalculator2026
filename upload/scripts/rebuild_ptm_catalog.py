"""Rebuild the PTM steel sortament catalogue.

Primary source: the public calculator requested by the user.
Fallback source: public static sortament tables when the target page is not
available from the local machine.

The output is source-backed and keeps source URL, raw values and retrieval
time. The calculator never depends on the remote site at runtime.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "data" / "ptm_sortament_v1.json"
OUT_CSV = ROOT / "data" / "ptm_sortament_v1.csv"
SOURCE_INDEX = ROOT / "data" / "ptm_sortament_sources_v1.json"

TARGET_BASE = "https://ognehimzashita.ru/calc"

PTM_TYPES = {
    "1": "Двутавр",
    "2": "Швеллер",
    "3": "Уголок",
    "4": "Профиль",
    "5": "Труба",
    "6": "Круг",
    "7": "Лист",
}

TARGET_STANDARDS = {
    "1": [
        ("20-93", "СТО АСЧМ 20-93"),
        ("57837-2017", "ГОСТ Р 57837-2017"),
        ("26020-83", "ГОСТ 26020-83"),
        ("8239-89", "ГОСТ 8239-89"),
        ("19425-74", "ГОСТ 19425-74"),
        ("1025", "DIN 1025"),
    ],
    "2": [
        ("8240-97", "ГОСТ 8240-97"),
        ("1026", "DIN 1026"),
        ("8278-83", "ГОСТ 8278-83"),
    ],
    "3": [
        ("8509-93", "ГОСТ 8509-93, 8510-86"),
        ("10056-1-1998", "DIN EN 10056-1-1998"),
    ],
    "4": [
        ("32931-2015", "ГОСТ 32931-2015"),
        ("30245-2003", "ГОСТ 30245-2003"),
        ("10210-2-2006", "DIN EN 10210-2-2006"),
        ("10219-2-2006", "DIN EN 10219-2-2006"),
    ],
}

FALLBACK_SOURCES = {
    "ГОСТ Р 57837-2017": ("Двутавр", "https://engineerum.com/sortament/gost-r-57837-2017/"),
    "СТО АСЧМ 20-93": ("Двутавр", "https://engineerum.com/sortament/sto-aschm-20-93/"),
    "ГОСТ 26020-83": ("Двутавр", "https://engineerum.com/sortament/gost-26020-83/"),
    "ГОСТ 8239-89": ("Двутавр", "https://engineerum.com/sortament/gost-8239-89/"),
    "ГОСТ 19425-74": ("Двутавр", "https://engineerum.com/sortament/gost-19425-74/"),
    "ГОСТ 8240-97": ("Швеллер", "https://engineerum.com/sortament/gost-8240-97/"),
    "ГОСТ 8509-93, 8510-86": ("Уголок", "https://engineerum.com/sortament/gost-8509-93/"),
    "ГОСТ 30245-2003": ("Профиль", "https://engineerum.com/sortament/gost-30245-2003/"),
}


@dataclass
class Observation:
    standard: str
    profile_type: str
    subtype: str
    name: str
    area_cm2: float | None
    mass_kg_per_m: float | None
    height_mm: float | None
    width_mm: float | None
    web_thickness_mm: float | None
    flange_thickness_mm: float | None
    radius_mm: float | None
    leg_a_mm: float | None
    leg_b_mm: float | None
    wall_thickness_mm: float | None
    outside_diameter_mm: float | None
    diameter_mm: float | None
    sheet_thickness_mm: float | None
    perimeter_all_sides_mm: float | None
    ptm_mm_source: float | None
    surface_m2_per_m_source: float | None
    surface_m2_per_t_source: float | None
    source: str
    source_url: str
    retrieved_at: str
    raw_values: dict[str, object]


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ("td", "th") and self._row is not None and self._cell is not None:
            self._row.append(re.sub(r"\\s+", " ", "".join(self._cell)).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if any(self._row):
                self.rows.append(self._row)
            self._row = None


def fetch(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "LKMCalculator2026/PTM-catalog-rebuilder",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        },
    )
    with urlopen(request, timeout=30) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


def num(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace("\\xa0", " ").replace(",", ".")
    match = re.search(r"-?\\d+(?:\\.\\d+)?", text)
    return float(match.group()) if match else None


def normal_key(value: str) -> str:
    return re.sub(r"\\s+", " ", str(value or "")).strip().casefold()


def build_target_url(tb: str, sn: str, pn: str | None = None) -> str:
    params = {"tb": tb, "sn": sn}
    if pn:
        params["pn"] = pn
    return TARGET_BASE + "?" + urlencode(params)


def extract_profile_options(html: str) -> list[str]:
    """Extract options from the profile selector, tolerating markup revisions."""
    scoped = re.findall(
        r"<select[^>]*(?:name|id)=[\"'](?:pn|profile|profile_id)[\"'][^>]*>(.*?)</select>",
        html,
        re.I | re.S,
    )
    source = "\\n".join(scoped) if scoped else html
    options = re.findall(
        r"<option[^>]*value=[\"']([^\"']*)[\"'][^>]*>(.*?)</option>",
        source,
        re.I | re.S,
    )
    values: list[str] = []
    for value, label in options:
        value = re.sub(r"\\s+", " ", value).strip()
        label = re.sub(r"<[^>]+>", "", label)
        label = re.sub(r"\\s+", " ", label).strip()
        if not value or not label or len(label) > 100:
            continue
        if normal_key(label) in {"выберите", "выбрать"}:
            continue
        values.append(value)
    return list(dict.fromkeys(values))


def extract_result_values(html: str) -> dict[str, float]:
    html_values = re.sub(
        r"<input[^>]*value=[\"']([^\"']*)[\"'][^>]*>",
        lambda m: " " + m.group(1) + " ",
        html,
        flags=re.I,
    )
    html_values = re.sub(
        r"<option[^>]*>(.*?)</option>",
        lambda m: " " + re.sub(r"<[^>]+>", "", m.group(1)) + " ",
        html_values,
        flags=re.I | re.S,
    )
    plain = re.sub(r"<[^>]+>", " ", html_values)
    plain = re.sub(r"\\s+", " ", plain)

    patterns = {
        "ptm_mm": r"Приведен(?:ная|ённая)\\s+толщина\\s+металла\\s*:?\\s*([0-9]+(?:[.,][0-9]+)?)",
        "area_cm2": r"Площадь\\s+сечения\\s*:?\\s*([0-9]+(?:[.,][0-9]+)?)",
        "perimeter_mm": r"Обогреваемый\\s+периметр\\s*:?\\s*([0-9]+(?:[.,][0-9]+)?)",
        "surface_m2_per_m": r"Площадь\\s+поверхности\\s*/\\s*1\\s*м\\s*:?\\s*([0-9]+(?:[.,][0-9]+)?)",
        "surface_m2_per_t": r"Площадь\\s+поверхности\\s*/\\s*1\\s*т\\s*:?\\s*([0-9]+(?:[.,][0-9]+)?)",
    }
    result: dict[str, float] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, plain, re.I)
        if match:
            result[key] = float(match.group(1).replace(",", "."))
    return result


def header_map(headers: list[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for index, header in enumerate(headers):
        key = normal_key(header)
        if "профил" in key or key in {"марка", "типоразмер"}:
            result.setdefault("name", index)
        elif re.search(r"(^|\\s)h[, ]", key) or key.startswith("h"):
            result.setdefault("h", index)
        elif re.search(r"(^|\\s)b[, ]", key) or key.startswith("b"):
            result.setdefault("b", index)
        elif key.startswith("s"):
            result.setdefault("s", index)
        elif key.startswith("t"):
            result.setdefault("t", index)
        elif key in {"r", "r, мм"} or "r, мм" in key:
            result.setdefault("r", index)
        elif "а, см" in key or "a, см" in key:
            result.setdefault("area", index)
        elif "m, кг" in key or "м, кг" in key:
            result.setdefault("mass", index)
    return result


def parse_static_table(
    html: str,
    standard: str,
    profile_type: str,
    source: str,
    source_url: str,
) -> list[Observation]:
    parser = TableParser()
    parser.feed(html)
    if not parser.rows:
        return []

    mapping: dict[str, int] | None = None
    for row in parser.rows[:50]:
        hm = header_map(row)
        if "name" in hm and ("area" in hm or "mass" in hm):
            mapping = hm
            break
    if mapping is None:
        return []

    def get(row: list[str], key: str) -> str:
        index = mapping.get(key)
        return row[index] if index is not None and index < len(row) else ""

    now = datetime.now(timezone.utc).isoformat()
    observations: list[Observation] = []
    for row in parser.rows:
        name = get(row, "name")
        if not name or normal_key(name) in {"профиль", "типоразмер"}:
            continue
        area = num(get(row, "area"))
        mass = num(get(row, "mass"))
        if area is None and mass is None:
            continue
        observations.append(
            Observation(
                standard=standard,
                profile_type=profile_type,
                subtype="",
                name=name,
                area_cm2=area,
                mass_kg_per_m=mass,
                height_mm=num(get(row, "h")),
                width_mm=num(get(row, "b")),
                web_thickness_mm=num(get(row, "s")),
                flange_thickness_mm=num(get(row, "t")),
                radius_mm=num(get(row, "r")),
                leg_a_mm=None,
                leg_b_mm=None,
                wall_thickness_mm=None,
                outside_diameter_mm=None,
                diameter_mm=None,
                sheet_thickness_mm=None,
                perimeter_all_sides_mm=None,
                ptm_mm_source=None,
                surface_m2_per_m_source=None,
                surface_m2_per_t_source=None,
                source=source,
                source_url=source_url,
                retrieved_at=now,
                raw_values={"cells": row},
            )
        )
    return observations


def scrape_target_standard(tb: str, sn: str, standard: str) -> list[Observation]:
    landing_url = build_target_url(tb, sn)
    landing_html = fetch(landing_url)
    profile_values = extract_profile_options(landing_html)
    observations: list[Observation] = []

    for pn in profile_values:
        url = build_target_url(tb, sn, pn)
        html = fetch(url)
        values = extract_result_values(html)
        required = {"ptm_mm", "area_cm2", "perimeter_mm"}
        if not required.issubset(values):
            continue

        mass = None
        if values.get("surface_m2_per_m") and values.get("surface_m2_per_t"):
            mass = values["surface_m2_per_m"] * 1000.0 / values["surface_m2_per_t"]

        observations.append(
            Observation(
                standard=standard,
                profile_type=PTM_TYPES.get(tb, "UNKNOWN"),
                subtype="",
                name=pn,
                area_cm2=values["area_cm2"],
                mass_kg_per_m=mass,
                height_mm=None,
                width_mm=None,
                web_thickness_mm=None,
                flange_thickness_mm=None,
                radius_mm=None,
                leg_a_mm=None,
                leg_b_mm=None,
                wall_thickness_mm=None,
                outside_diameter_mm=None,
                diameter_mm=None,
                sheet_thickness_mm=None,
                perimeter_all_sides_mm=values["perimeter_mm"],
                ptm_mm_source=values["ptm_mm"],
                surface_m2_per_m_source=values.get("surface_m2_per_m"),
                surface_m2_per_t_source=values.get("surface_m2_per_t"),
                source="ognehimzashita.ru calculator",
                source_url=url,
                retrieved_at=datetime.now(timezone.utc).isoformat(),
                raw_values=values,
            )
        )
    return observations


def merge_observations(observations: Iterable[Observation]) -> list[dict]:
    """Merge sources by standard/type/profile without losing provenance."""
    groups: dict[tuple[str, str, str], list[Observation]] = {}
    for item in observations:
        key = (normal_key(item.standard), normal_key(item.profile_type), normal_key(item.name))
        groups.setdefault(key, []).append(item)

    output: list[dict] = []
    for items in groups.values():
        primary = items[0]
        # Prefer the target calculator observation when it exists.
        for item in items:
            if item.source == "ognehimzashita.ru calculator":
                primary = item
                break

        row = asdict(primary)
        row["source_observations"] = [asdict(item) for item in items]

        # Fill missing tabular dimensions/mass from a static source only.
        for item in items:
            if item is primary:
                continue
            for field_name in (
                "subtype",
                "height_mm",
                "width_mm",
                "web_thickness_mm",
                "flange_thickness_mm",
                "radius_mm",
                "leg_a_mm",
                "leg_b_mm",
                "wall_thickness_mm",
                "outside_diameter_mm",
                "diameter_mm",
                "sheet_thickness_mm",
            ):
                if row.get(field_name) is None and getattr(item, field_name) is not None:
                    row[field_name] = getattr(item, field_name)
            if row.get("mass_kg_per_m") is None and item.mass_kg_per_m is not None:
                row["mass_kg_per_m"] = item.mass_kg_per_m

        output.append(row)
    return sorted(output, key=lambda x: (x["standard"], x["profile_type"], x["name"]))


def main() -> int:
    print("=== PTM CATALOG REBUILD ===")
    observations: list[Observation] = []
    failures: list[dict[str, str]] = []

    # Target calculator: this is the authoritative extraction route requested
    # by the user. It is intentionally cached into a local catalogue.
    for tb, items in TARGET_STANDARDS.items():
        for sn, standard in items:
            try:
                print(f"[TARGET] {tb} / {standard}")
                rows = scrape_target_standard(tb, sn, standard)
                print(f"  profiles={len(rows)}")
                observations.extend(rows)
            except Exception as exc:
                failures.append({
                    "stage": "target",
                    "type": tb,
                    "standard": standard,
                    "url": build_target_url(tb, sn),
                    "error": str(exc),
                })
                print(f"  FAILED: {exc}")

    # Public static fallback for standards that the target site did not yield.
    seen = {(normal_key(x.standard), normal_key(x.profile_type), normal_key(x.name)) for x in observations}
    for standard, (profile_type, url) in FALLBACK_SOURCES.items():
        try:
            html = fetch(url)
            rows = parse_static_table(
                html,
                standard=standard,
                profile_type=profile_type,
                source="public static sortament table",
                source_url=url,
            )
            added = 0
            for row in rows:
                key = (normal_key(row.standard), normal_key(row.profile_type), normal_key(row.name))
                if key not in seen:
                    observations.append(row)
                    seen.add(key)
                    added += 1
            print(f"[FALLBACK] {standard}: added={added}")
        except Exception as exc:
            failures.append({
                "stage": "fallback",
                "standard": standard,
                "url": url,
                "error": str(exc),
            })
            print(f"[FALLBACK] {standard}: FAILED: {exc}")

    profiles = merge_observations(observations)

    if not profiles and OUT_JSON.exists():
        try:
            old = json.loads(OUT_JSON.read_text(encoding="utf-8"))
            profiles = old.get("profiles", [])
            print("No new data; preserved existing PTM catalogue.")
        except Exception:
            pass

    payload = {
        "schema_version": "1.0-ptm-sortament",
        "source_policy": "SOURCE_BACKED",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_base": TARGET_BASE,
        "failures": failures,
        "profiles": profiles,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_fields = [
        "standard",
        "profile_type",
        "subtype",
        "name",
        "area_cm2",
        "mass_kg_per_m",
        "height_mm",
        "width_mm",
        "web_thickness_mm",
        "flange_thickness_mm",
        "radius_mm",
        "perimeter_all_sides_mm",
        "ptm_mm_source",
        "surface_m2_per_m_source",
        "surface_m2_per_t_source",
        "source",
        "source_url",
        "retrieved_at",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for row in profiles:
            writer.writerow({key: row.get(key) for key in csv_fields})

    SOURCE_INDEX.write_text(
        json.dumps(
            {
                "generated_at": payload["generated_at"],
                "target_base": TARGET_BASE,
                "target_standards": TARGET_STANDARDS,
                "fallback_sources": FALLBACK_SOURCES,
                "failures": failures,
                "profile_count": len(profiles),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"profiles={len(profiles)}")
    print(f"failures={len(failures)}")
    print(f"json={OUT_JSON}")
    print(f"csv={OUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
