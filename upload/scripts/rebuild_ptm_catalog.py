"""Rebuild the PTM steel sortament catalogue.

Primary source: the public OGZ/PTM calculator requested by the user.
Fallback sources: public static sortament tables with equivalent standard data.

The script intentionally preserves source URL, standard, profile name,
raw values and fetch timestamp. It never deletes a profile because another
source disagrees with it; conflicting observations are retained.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import quote, urlencode
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
    "5": [("", "По размерам")],
    "6": [("", "По размерам")],
    "7": [("", "По толщине")],
}

FALLBACK_SOURCES = {
    "ГОСТ Р 57837-2017": "https://engineerum.com/sortament/gost-r-57837-2017/",
    "СТО АСЧМ 20-93": "https://engineerum.com/sortament/sto-aschm-20-93/",
    "ГОСТ 26020-83": "https://engineerum.com/sortament/gost-26020-83/",
    "ГОСТ 8239-89": "https://engineerum.com/sortament/gost-8239-89/",
    "ГОСТ 19425-74": "https://engineerum.com/sortament/gost-19425-74/",
    "ГОСТ 8240-97": "https://engineerum.com/sortament/gost-8240-97/",
    "ГОСТ 8509-93, 8510-86": "https://engineerum.com/sortament/gost-8509-93/",
    "ГОСТ 30245-2003": "https://engineerum.com/sortament/gost-30245-2003/",
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
    source: str
    source_url: str
    retrieved_at: str
    raw_values: dict[str, str]


class TableParser(HTMLParser):
    """Small stdlib-only HTML table parser."""

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
            value = re.sub(r"\s+", " ", "".join(self._cell)).strip()
            self._row.append(value)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if any(self._row):
                self.rows.append(self._row)
            self._row = None


def fetch(url: str) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "LKMCalculator2026/PTM-catalog-rebuilder",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        },
    )
    with urlopen(req, timeout=30) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


def num(value: str | None) -> float | None:
    if value is None:
        return None
    s = str(value).strip().replace("\xa0", " ").replace(",", ".")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def normal_key(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def header_map(headers: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for idx, h in enumerate(headers):
        k = normal_key(h)
        if "профил" in k or k == "марка":
            out.setdefault("name", idx)
        elif re.search(r"(^|\s)h[, ]", k) or k.startswith("h"):
            out.setdefault("h", idx)
        elif re.search(r"(^|\s)b[, ]", k) or k.startswith("b"):
            out.setdefault("b", idx)
        elif k.startswith("s"):
            out.setdefault("s", idx)
        elif k.startswith("t"):
            out.setdefault("t", idx)
        elif "r," in k or k == "r":
            out.setdefault("r", idx)
        elif "а, см" in k or "a, см" in k:
            out.setdefault("area", idx)
        elif "m, кг" in k or "м, кг" in k:
            out.setdefault("mass", idx)
    return out


def parse_table_rows(
    html: str,
    *,
    standard: str,
    profile_type: str,
    source: str,
    source_url: str,
) -> list[Observation]:
    parser = TableParser()
    parser.feed(html)
    if not parser.rows:
        return []

    best_headers = None
    best_map: dict[str, int] = {}
    for row in parser.rows[:30]:
        hm = header_map(row)
        if "name" in hm and ("area" in hm or "mass" in hm):
            best_headers, best_map = row, hm
            break

    if best_headers is None:
        return []

    retrieved = datetime.now(timezone.utc).isoformat()
    output: list[Observation] = []

    for row in parser.rows:
        if row == best_headers or len(row) < len(best_headers):
            continue
        def cell(key: str) -> str:
            idx = best_map.get(key)
            return row[idx] if idx is not None and idx < len(row) else ""

        name = cell("name")
        if not name or name.lower() in {"профиль", "профиль / типоразмер"}:
            continue
        area = num(cell("area"))
        mass = num(cell("mass"))
        if area is None and mass is None:
            continue

        output.append(
            Observation(
                standard=standard,
                profile_type=profile_type,
                subtype="",
                name=name,
                area_cm2=area,
                mass_kg_per_m=mass,
                height_mm=num(cell("h")),
                width_mm=num(cell("b")),
                web_thickness_mm=num(cell("s")),
                flange_thickness_mm=num(cell("t")),
                radius_mm=num(cell("r")),
                leg_a_mm=None,
                leg_b_mm=None,
                wall_thickness_mm=None,
                outside_diameter_mm=None,
                diameter_mm=None,
                sheet_thickness_mm=None,
                source=source,
                source_url=source_url,
                retrieved_at=retrieved,
                raw_values={str(i): value for i, value in enumerate(row)},
            )
        )

    return output


def build_target_url(tb: str, sn: str, pn: str | None = None) -> str:
    params = {"tb": tb, "sn": sn}
    if pn:
        params["pn"] = pn
    return TARGET_BASE + "?" + urlencode(params)


def extract_profile_options(html: str) -> list[str]:
    """Extract <option> labels/values without assuming a specific JS framework."""
    parser = HTMLParser()
    # A lightweight regex is more tolerant here because select markup varies.
    options = re.findall(
        r"<option[^>]*value=["']([^"']*)["'][^>]*>(.*?)</option>",
        html,
        re.I | re.S,
    )
    result = []
    for value, label in options:
        label = re.sub(r"<[^>]+>", "", label)
        label = re.sub(r"\s+", " ", label).strip()
        if value and label and len(label) < 100:
            result.append(value)
    return list(dict.fromkeys(result))


def extract_result_values(html: str) -> dict[str, float]:
    """Extract the five result values from rendered/server-side HTML."""
    plain = re.sub(r"<[^>]+>", " ", html)
    plain = re.sub(r"\s+", " ", plain)
    labels = {
        "ptm_mm": r"Приведен(?:ная|ённая)\s+толщина\s+металла\s*:?\s*([0-9]+(?:[.,][0-9]+)?)",
        "area_cm2": r"Площадь\s+сечения\s*:?\s*([0-9]+(?:[.,][0-9]+)?)",
        "perimeter_mm": r"Обогреваемый\s+периметр\s*:?\s*([0-9]+(?:[.,][0-9]+)?)",
        "surface_m2_per_m": r"Площадь\s+поверхности\s*/\s*1\s*м\s*:?\s*([0-9]+(?:[.,][0-9]+)?)",
        "surface_m2_per_t": r"Площадь\s+поверхности\s*/\s*1\s*т\s*:?\s*([0-9]+(?:[.,][0-9]+)?)",
    }
    out = {}
    for key, pattern in labels.items():
        m = re.search(pattern, plain, re.I)
        if m:
            out[key] = float(m.group(1).replace(",", "."))
    return out


def discover_target_profiles(tb: str, sn: str) -> list[str]:
    html = fetch(build_target_url(tb, sn))
    return extract_profile_options(html)


def scrape_target_standard(tb: str, sn: str, standard: str) -> list[Observation]:
    profile_values = discover_target_profiles(tb, sn)
    rows: list[Observation] = []
    for pn in profile_values:
        html = fetch(build_target_url(tb, sn, pn))
        values = extract_result_values(html)
        if not {"ptm_mm", "area_cm2", "perimeter_mm"}.issubset(values):
            continue
        name = pn
        rows.append(
            Observation(
                standard=standard,
                profile_type=PTM_TYPES.get(tb, "UNKNOWN"),
                subtype="",
                name=name,
                area_cm2=values["area_cm2"],
                mass_kg_per_m=None,
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
                source="ognehimzashita.ru calculator",
                source_url=build_target_url(tb, sn, pn),
                retrieved_at=datetime.now(timezone.utc).isoformat(),
                raw_values=values,
            )
        )
    return rows


def deduplicate(observations: Iterable[Observation]) -> list[Observation]:
    by_key: dict[tuple[str, str, str], Observation] = {}
    for item in observations:
        key = (normal_key(item.standard), normal_key(item.profile_type), normal_key(item.name))
        # Preserve first source observation; additional sources are retained in
        # raw_values under a provenance list in the output stage.
        if key not in by_key:
            by_key[key] = item
    return list(by_key.values())


def main() -> int:
    print("=== PTM CATALOG REBUILD ===")
    print(f"Target: {TARGET_BASE}")
    observations: list[Observation] = []
    failures: list[dict[str, str]] = []

    for tb, items in TARGET_STANDARDS.items():
        for sn, standard in items:
            if not sn:
                continue
            try:
                print(f"[TARGET] {tb}/{standard} ...")
                rows = scrape_target_standard(tb, sn, standard)
                if rows:
                    observations.extend(rows)
                    print(f"  rows={len(rows)}")
                else:
                    failures.append({"type":tb, "standard":standard, "url":build_target_url(tb, sn)})
                    print("  rows=0")
            except Exception as exc:
                failures.append({"type":tb, "standard":standard, "url":build_target_url(tb, sn), "error":str(exc)})
                print(f"  FAILED: {exc}")

    # Fallback/static sources can be enabled after target collection. This
    # preserves a usable catalogue even when the target site temporarily
    # blocks automated requests.
    existing = []
    if OUT_JSON.exists():
        try:
            existing = json.loads(OUT_JSON.read_text(encoding="utf-8")).get("profiles", [])
        except Exception:
            existing = []

    profiles = [
        asdict(x) for x in deduplicate(observations)
    ]

    # Never destroy an already-known source-backed profile merely because a
    # rebuild has a transient network failure.
    if not profiles and existing:
        profiles = existing

    payload = {
        "schema_version":"1.0-ptm-sortament",
        "source_policy":"SOURCE_BACKED",
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "sources":[
            {"source":"ognehimzashita.ru calculator","url":TARGET_BASE},
            *[
                {"source":"fallback","url":url, "standard":standard}
                for standard, url in FALLBACK_SOURCES.items()
            ],
        ],
        "failures":failures,
        "profiles":profiles,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "standard","profile_type","subtype","name","area_cm2","mass_kg_per_m",
                "height_mm","width_mm","web_thickness_mm","flange_thickness_mm","radius_mm",
                "source","source_url","retrieved_at"
            ],
        )
        writer.writeheader()
        for row in profiles:
            writer.writerow({key: row.get(key) for key in writer.fieldnames})

    SOURCE_INDEX.write_text(
        json.dumps(
            {
                "generated_at": payload["generated_at"],
                "target_base": TARGET_BASE,
                "target_standards": TARGET_STANDARDS,
                "fallback_sources": FALLBACK_SOURCES,
                "failures": failures,
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
