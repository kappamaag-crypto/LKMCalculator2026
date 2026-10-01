"""Pure-domain PTM (reduced steel thickness) calculations.

The PTM layer is deliberately independent from fire-protection coating
materials. It only resolves steel section geometry/sortament and calculates
F, P and derived surface values.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional
import json


class PTMProfileType(str, Enum):
    I_BEAM = "Двутавр"
    CHANNEL = "Швеллер"
    ANGLE = "Уголок"
    BOX = "Профиль"
    PIPE = "Труба"
    ROUND_BAR = "Круг"
    SHEET = "Лист"


class HeatingMode(str, Enum):
    FOUR_SIDES = "4 стороны"
    THREE_SIDES = "3 стороны"
    TWO_SIDES = "2 стороны"
    CUSTOM = "Пользовательский периметр"


# Required sortament choices. Fixed tables are populated independently from
# the calculation engine; dimensions-only types use the same UI with manual
# geometry inputs.
STANDARD_OPTIONS: dict[PTMProfileType, tuple[str, ...]] = {
    PTMProfileType.I_BEAM: (
        "ГОСТ Р 57837-2017",
        "СТО АСЧМ 20-93",
        "ГОСТ 26020-83",
        "ГОСТ 8239-89",
        "ГОСТ 19425-74",
        "DIN 1025",
        "СВАРНОЙ по размерам",
    ),
    PTMProfileType.CHANNEL: (
        "ГОСТ 8240-97",
        "DIN 1026",
        "ГОСТ 8278-83",
    ),
    PTMProfileType.ANGLE: (
        "ГОСТ 8509-93, 8510-86",
        "DIN EN 10056-1-1998",
    ),
    PTMProfileType.BOX: (
        "ГОСТ 32931-2015",
        "ГОСТ 30245-2003",
        "DIN EN 10210-2-2006",
        "DIN EN 10219-2-2006",
    ),
    PTMProfileType.PIPE: ("По размерам",),
    PTMProfileType.ROUND_BAR: ("По размерам",),
    PTMProfileType.SHEET: ("По толщине",),
}


@dataclass(frozen=True)
class PTMProfile:
    standard: str
    profile_type: PTMProfileType
    name: str
    area_cm2: Optional[float]
    mass_kg_per_m: Optional[float]
    height_mm: Optional[float] = None
    width_mm: Optional[float] = None
    web_thickness_mm: Optional[float] = None
    flange_thickness_mm: Optional[float] = None
    leg_a_mm: Optional[float] = None
    leg_b_mm: Optional[float] = None
    wall_thickness_mm: Optional[float] = None
    outside_diameter_mm: Optional[float] = None
    diameter_mm: Optional[float] = None
    sheet_thickness_mm: Optional[float] = None
    perimeter_all_sides_mm: Optional[float] = None
    source: str = ""
    source_url: str = ""
    notes: str = ""


@dataclass(frozen=True)
class PTMCalculationInput:
    profile: PTMProfile
    heating_mode: HeatingMode = HeatingMode.FOUR_SIDES
    heated_perimeter_mm: Optional[float] = None
    length_m: float = 1.0
    quantity: int = 1


@dataclass(frozen=True)
class PTMCalculationResult:
    ptm_mm: float
    section_area_cm2: float
    heated_perimeter_mm: float
    surface_m2_per_m: float
    surface_m2_per_t: Optional[float]
    length_m: float
    quantity: int
    total_surface_m2: float
    total_mass_kg: Optional[float]


def _positive(value: float, field: str) -> float:
    if value <= 0:
        raise ValueError(f"{field} должно быть больше нуля.")
    return value


def calculate_ptm(area_cm2: float, heated_perimeter_mm: float) -> float:
    """F/P with cm² and mm units, returned as mm."""
    _positive(area_cm2, "Площадь сечения")
    _positive(heated_perimeter_mm, "Обогреваемый периметр")
    return area_cm2 * 10.0 / heated_perimeter_mm


def i_beam_perimeter(height_mm: float, width_mm: float, web_thickness_mm: float, mode: HeatingMode) -> float:
    h = _positive(height_mm, "Высота")
    b = _positive(width_mm, "Ширина полки")
    s = _positive(web_thickness_mm, "Толщина стенки")
    if mode == HeatingMode.FOUR_SIDES:
        return 2.0 * h + 4.0 * b - 2.0 * s
    if mode == HeatingMode.THREE_SIDES:
        return 2.0 * h + 3.0 * b - 2.0 * s
    if mode == HeatingMode.TWO_SIDES:
        return 2.0 * h + 2.0 * b - 2.0 * s
    raise ValueError("Для пользовательского периметра используйте HeatingMode.CUSTOM.")


def channel_perimeter(height_mm: float, width_mm: float, web_thickness_mm: float, mode: HeatingMode) -> float:
    h = _positive(height_mm, "Высота")
    b = _positive(width_mm, "Ширина полки")
    s = _positive(web_thickness_mm, "Толщина стенки")
    if mode == HeatingMode.FOUR_SIDES:
        return 2.0 * h + 4.0 * b - 2.0 * s
    if mode == HeatingMode.THREE_SIDES:
        return 2.0 * h + 3.0 * b - 2.0 * s
    if mode == HeatingMode.TWO_SIDES:
        return 2.0 * h + 2.0 * b
    raise ValueError("Для пользовательского периметра используйте HeatingMode.CUSTOM.")


def angle_perimeter(leg_a_mm: float, leg_b_mm: float, mode: HeatingMode) -> float:
    a = _positive(leg_a_mm, "Полка A")
    b = _positive(leg_b_mm, "Полка B")
    if mode == HeatingMode.FOUR_SIDES:
        return 2.0 * (a + b)
    if mode == HeatingMode.THREE_SIDES:
        return 2.0 * a + b
    if mode == HeatingMode.TWO_SIDES:
        return a + b
    raise ValueError("Для пользовательского периметра используйте HeatingMode.CUSTOM.")


def box_perimeter(width_mm: float, height_mm: float, mode: HeatingMode) -> float:
    w = _positive(width_mm, "Ширина")
    h = _positive(height_mm, "Высота")
    if mode == HeatingMode.FOUR_SIDES:
        return 2.0 * (w + h)
    if mode == HeatingMode.THREE_SIDES:
        return 2.0 * w + h
    if mode == HeatingMode.TWO_SIDES:
        return w + h
    raise ValueError("Для пользовательского периметра используйте HeatingMode.CUSTOM.")


def pipe_area_cm2(outside_diameter_mm: float, wall_thickness_mm: float) -> float:
    d = _positive(outside_diameter_mm, "Наружный диаметр")
    t = _positive(wall_thickness_mm, "Толщина стенки")
    inner = d - 2.0 * t
    if inner <= 0:
        raise ValueError("Толщина стенки должна быть меньше половины наружного диаметра.")
    return math.pi * (d * d - inner * inner) / 4.0 / 100.0


def pipe_perimeter(outside_diameter_mm: float) -> float:
    return math.pi * _positive(outside_diameter_mm, "Наружный диаметр")


def round_bar_area_cm2(diameter_mm: float) -> float:
    d = _positive(diameter_mm, "Диаметр")
    return math.pi * d * d / 4.0 / 100.0


def round_bar_perimeter(diameter_mm: float) -> float:
    return math.pi * _positive(diameter_mm, "Диаметр")


def sheet_area_for_one_m(width_mm: float, thickness_mm: float) -> float:
    w = _positive(width_mm, "Ширина листа")
    t = _positive(thickness_mm, "Толщина листа")
    return w * t / 100.0


def sheet_perimeter_for_one_m(width_mm: float, mode: HeatingMode) -> float:
    """Flat sheet approximation for a 1 m length.

    Four/three/two-side modes correspond to heating both broad faces, one broad
    face plus one edge, or one broad face respectively. This keeps the
    geometry explicit instead of hiding a coefficient.
    """
    w = _positive(width_mm, "Ширина листа")
    if mode == HeatingMode.FOUR_SIDES:
        return 2.0 * w + 2000.0
    if mode == HeatingMode.THREE_SIDES:
        return 2.0 * w + 1000.0
    if mode == HeatingMode.TWO_SIDES:
        return w
    raise ValueError("Для пользовательского периметра используйте HeatingMode.CUSTOM.")


def resolve_profile_area(profile: PTMProfile) -> float:
    if profile.area_cm2 is not None:
        return _positive(profile.area_cm2, "Площадь сечения")

    p = profile
    if p.profile_type == PTMProfileType.PIPE:
        if p.outside_diameter_mm is None or p.wall_thickness_mm is None:
            raise ValueError("Для трубы не заданы наружный диаметр и толщина стенки.")
        return pipe_area_cm2(p.outside_diameter_mm, p.wall_thickness_mm)

    if p.profile_type == PTMProfileType.ROUND_BAR:
        if p.diameter_mm is None:
            raise ValueError("Для круга не задан диаметр.")
        return round_bar_area_cm2(p.diameter_mm)

    if p.profile_type == PTMProfileType.SHEET:
        if p.sheet_thickness_mm is None:
            raise ValueError("Для листа не задана толщина.")
        # The PTM for sheet is independent of arbitrary sheet width. A 1 m
        # wide strip is used as the calculation reference.
        return sheet_area_for_one_m(1000.0, p.sheet_thickness_mm)

    if p.profile_type == PTMProfileType.I_BEAM:
        if None in (p.height_mm, p.width_mm, p.web_thickness_mm, p.flange_thickness_mm):
            raise ValueError("Для двутавра не заданы размеры.")
        h, b, s, t = p.height_mm, p.width_mm, p.web_thickness_mm, p.flange_thickness_mm
        return (2.0 * b * t + (h - 2.0 * t) * s) / 100.0

    if p.profile_type == PTMProfileType.CHANNEL:
        if None in (p.height_mm, p.width_mm, p.web_thickness_mm, p.flange_thickness_mm):
            raise ValueError("Для швеллера не заданы размеры.")
        h, b, s, t = p.height_mm, p.width_mm, p.web_thickness_mm, p.flange_thickness_mm
        return (2.0 * b * t + (h - 2.0 * t) * s) / 100.0

    if p.profile_type == PTMProfileType.ANGLE:
        if None in (p.leg_a_mm, p.leg_b_mm, p.wall_thickness_mm):
            raise ValueError("Для уголка не заданы размеры.")
        return (
            p.leg_a_mm * p.wall_thickness_mm
            + (p.leg_b_mm - p.wall_thickness_mm) * p.wall_thickness_mm
        ) / 100.0

    if p.profile_type == PTMProfileType.BOX:
        if None in (p.height_mm, p.width_mm, p.wall_thickness_mm):
            raise ValueError("Для профиля не заданы размеры.")
        h, b, t = p.height_mm, p.width_mm, p.wall_thickness_mm
        if 2.0 * t >= min(h, b):
            raise ValueError("Толщина стенки слишком велика относительно размеров профиля.")
        return 2.0 * t * (h + b - 2.0 * t) / 100.0

    raise ValueError(f"Неизвестный тип профиля: {p.profile_type.value}")


def resolve_heated_perimeter(inp: PTMCalculationInput) -> float:
    p = inp.profile
    if inp.heating_mode == HeatingMode.CUSTOM:
        return _positive(inp.heated_perimeter_mm or 0.0, "Пользовательский обогреваемый периметр")

    if p.perimeter_all_sides_mm is not None and inp.heating_mode == HeatingMode.FOUR_SIDES:
        return _positive(p.perimeter_all_sides_mm, "Обогреваемый периметр")

    if p.profile_type == PTMProfileType.I_BEAM:
        if None not in (p.height_mm, p.width_mm, p.web_thickness_mm):
            return i_beam_perimeter(p.height_mm, p.width_mm, p.web_thickness_mm, inp.heating_mode)

    if p.profile_type == PTMProfileType.CHANNEL:
        if None not in (p.height_mm, p.width_mm, p.web_thickness_mm):
            return channel_perimeter(p.height_mm, p.width_mm, p.web_thickness_mm, inp.heating_mode)

    if p.profile_type == PTMProfileType.ANGLE:
        if None not in (p.leg_a_mm, p.leg_b_mm):
            return angle_perimeter(p.leg_a_mm, p.leg_b_mm, inp.heating_mode)

    if p.profile_type == PTMProfileType.BOX:
        if None not in (p.width_mm, p.height_mm):
            return box_perimeter(p.width_mm, p.height_mm, inp.heating_mode)

    if p.profile_type == PTMProfileType.PIPE:
        if p.outside_diameter_mm is not None:
            # Round pipe is the explicit exception where the heated perimeter
            # cannot be toggled side-by-side in the reference UI.
            return pipe_perimeter(p.outside_diameter_mm)

    if p.profile_type == PTMProfileType.ROUND_BAR:
        if p.diameter_mm is not None:
            return round_bar_perimeter(p.diameter_mm)

    if p.profile_type == PTMProfileType.SHEET:
        return sheet_perimeter_for_one_m(1000.0, inp.heating_mode)

    raise ValueError(
        f"Для профиля «{p.name}» отсутствует подтверждённая геометрия "
        "для выбранного режима обогрева."
    )


def calculate(inp: PTMCalculationInput) -> PTMCalculationResult:
    if inp.length_m <= 0:
        raise ValueError("Длина должна быть больше нуля.")
    if inp.quantity <= 0:
        raise ValueError("Количество должно быть больше нуля.")

    area = resolve_profile_area(inp.profile)
    perimeter = resolve_heated_perimeter(inp)
    ptm = calculate_ptm(area, perimeter)
    surface_per_m = perimeter / 1000.0

    mass_per_m = inp.profile.mass_kg_per_m
    if mass_per_m is None:
        # Steel density reference 7850 kg/m³ => 0.785 kg per metre per cm².
        mass_per_m = area * 0.785

    surface_per_t = surface_per_m * 1000.0 / mass_per_m if mass_per_m > 0 else None
    total_surface = surface_per_m * inp.length_m * inp.quantity
    total_mass = mass_per_m * inp.length_m * inp.quantity if mass_per_m > 0 else None

    return PTMCalculationResult(
        ptm_mm=ptm,
        section_area_cm2=area,
        heated_perimeter_mm=perimeter,
        surface_m2_per_m=surface_per_m,
        surface_m2_per_t=surface_per_t,
        length_m=inp.length_m,
        quantity=inp.quantity,
        total_surface_m2=total_surface,
        total_mass_kg=total_mass,
    )


def list_standards(profile_type: Optional[PTMProfileType] = None) -> list[str]:
    if profile_type is None:
        values = {name for items in STANDARD_OPTIONS.values() for name in items}
        return sorted(values)
    return list(STANDARD_OPTIONS.get(profile_type, ()))


# The full catalogue is stored outside the code so it can be rebuilt from
# source tables without changing the calculation engine.
CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "ptm_sortament_v1.json"

def _enum_profile_type(value: str) -> PTMProfileType:
    for item in PTMProfileType:
        if item.value == value:
            return item
    raise ValueError(f"Unknown PTM profile type: {value}")

def _load_catalog() -> tuple[PTMProfile, ...]:
    fallback = (
        PTMProfile(
            standard="ГОСТ Р 57837-2017",
            profile_type=PTMProfileType.I_BEAM,
            name="20Б1",
            area_cm2=27.16,
            mass_kg_per_m=21.3,
            height_mm=200.0,
            width_mm=100.0,
            web_thickness_mm=5.5,
            flange_thickness_mm=8.0,
            source="ГОСТ Р 57837-2017 / сортамент",
            source_url="https://engineerum.com/sortament/gost-r-57837-2017/",
            notes="Fallback reference row.",
        ),
    )
    try:
        payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        profiles = []
        for row in payload.get("profiles", []):
            try:
                profiles.append(
                    PTMProfile(
                        standard=str(row.get("standard") or ""),
                        profile_type=_enum_profile_type(str(row.get("profile_type") or "")),
                        name=str(row.get("name") or ""),
                        area_cm2=row.get("area_cm2"),
                        mass_kg_per_m=row.get("mass_kg_per_m"),
                        height_mm=row.get("height_mm"),
                        width_mm=row.get("width_mm"),
                        web_thickness_mm=row.get("web_thickness_mm"),
                        flange_thickness_mm=row.get("flange_thickness_mm"),
                        leg_a_mm=row.get("leg_a_mm"),
                        leg_b_mm=row.get("leg_b_mm"),
                        wall_thickness_mm=row.get("wall_thickness_mm"),
                        outside_diameter_mm=row.get("outside_diameter_mm"),
                        diameter_mm=row.get("diameter_mm"),
                        sheet_thickness_mm=row.get("sheet_thickness_mm"),
                        perimeter_all_sides_mm=row.get("perimeter_all_sides_mm"),
                        source=str(row.get("source") or ""),
                        source_url=str(row.get("source_url") or ""),
                        notes=str(row.get("notes") or ""),
                    )
                )
            except (TypeError, ValueError):
                continue
        if profiles:
            return tuple(profiles)
    except (OSError, ValueError, TypeError):
        pass
    return fallback

PTM_PROFILES: tuple[PTMProfile, ...] = _load_catalog()


def list_profiles(
    standard: Optional[str] = None,
    profile_type: Optional[PTMProfileType] = None,
) -> list[PTMProfile]:
    rows = list(PTM_PROFILES)
    if standard:
        rows = [p for p in rows if p.standard == standard]
    if profile_type:
        rows = [p for p in rows if p.profile_type == profile_type]
    return sorted(rows, key=lambda p: p.name)
