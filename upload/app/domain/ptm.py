"""Pure-domain PTM (reduced steel thickness) calculations for fire protection.

The module contains no UI or ORM dependencies. Standard/profile data is kept
separate from formulas so the catalogue can be expanded independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PTMProfileType(str, Enum):
    I_BEAM = "Двутавр"
    CHANNEL = "Швеллер"
    ANGLE = "Уголок"
    BOX = "Профиль"
    PIPE = "Труба"
    CUSTOM = "Ручной ввод"


class HeatingMode(str, Enum):
    FOUR_SIDES = "4 стороны"
    THREE_SIDES = "3 стороны"
    TWO_SIDES = "2 стороны"
    CUSTOM = "Пользовательский периметр"


@dataclass(frozen=True)
class PTMProfile:
    standard: str
    profile_type: PTMProfileType
    name: str
    area_cm2: float
    mass_kg_per_m: Optional[float]
    height_mm: Optional[float] = None
    width_mm: Optional[float] = None
    web_thickness_mm: Optional[float] = None
    flange_thickness_mm: Optional[float] = None
    perimeter_all_sides_mm: Optional[float] = None
    source: str = ""
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
    """PTM in mm from section area in cm² and heated perimeter in mm.

    Equivalent dimensional form to x = S * 10 / P.
    """
    _positive(area_cm2, "Площадь сечения")
    _positive(heated_perimeter_mm, "Обогреваемый периметр")
    return area_cm2 * 10.0 / heated_perimeter_mm


def i_beam_perimeter(height_mm: float, width_mm: float, web_thickness_mm: float, mode: HeatingMode) -> float:
    """Simplified I-beam heated-perimeter formulas.

    These are the conventional cross-section approximations used by the
    public reference calculator and its explanatory material; corner radii
    are intentionally not modelled here.
    """
    h = _positive(height_mm, "Высота")
    b = _positive(width_mm, "Ширина полки")
    tw = _positive(web_thickness_mm, "Толщина стенки")
    if tw >= min(h, b):
        raise ValueError("Толщина стенки не может быть равна/больше габаритов профиля.")
    if mode == HeatingMode.FOUR_SIDES:
        return 2.0 * h + 4.0 * b - 2.0 * tw
    if mode == HeatingMode.THREE_SIDES:
        return 2.0 * h + 3.0 * b - 2.0 * tw
    if mode == HeatingMode.TWO_SIDES:
        return 2.0 * h + 2.0 * b - 2.0 * tw
    raise ValueError("Для пользовательского периметра используйте HeatingMode.CUSTOM.")


def channel_perimeter(height_mm: float, width_mm: float, web_thickness_mm: float, mode: HeatingMode) -> float:
    h = _positive(height_mm, "Высота")
    b = _positive(width_mm, "Ширина")
    tw = _positive(web_thickness_mm, "Толщина стенки")
    if mode == HeatingMode.FOUR_SIDES:
        return 2.0 * h + 4.0 * b - 2.0 * tw
    if mode == HeatingMode.THREE_SIDES:
        return 2.0 * h + 3.0 * b - 2.0 * tw
    if mode == HeatingMode.TWO_SIDES:
        return 1.0 * h + 2.0 * b - 2.0 * tw
    raise ValueError("Для пользовательского периметра используйте HeatingMode.CUSTOM.")


def angle_perimeter(leg_a_mm: float, leg_b_mm: float, thickness_mm: float, mode: HeatingMode) -> float:
    a = _positive(leg_a_mm, "Полка A")
    b = _positive(leg_b_mm, "Полка B")
    t = _positive(thickness_mm, "Толщина")
    if mode == HeatingMode.FOUR_SIDES:
        # Outer perimeter approximation of an unequal/equal angle cross-section.
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


def resolve_heated_perimeter(inp: PTMCalculationInput) -> float:
    profile = inp.profile
    if inp.heating_mode == HeatingMode.CUSTOM:
        return _positive(
            inp.heated_perimeter_mm or 0.0,
            "Пользовательский обогреваемый периметр",
        )

    if profile.perimeter_all_sides_mm is not None:
        if inp.heating_mode == HeatingMode.FOUR_SIDES:
            return _positive(profile.perimeter_all_sides_mm, "Обогреваемый периметр")
        # For catalogue rows with only an all-side reference value, do not
        # silently invent a partial-heating value. The UI can use CUSTOM.
        raise ValueError(
            f"Для профиля «{profile.name}» отсутствует подтверждённый периметр "
            f"для режима «{inp.heating_mode.value}». Используйте пользовательский периметр."
        )

    if profile.profile_type == PTMProfileType.I_BEAM:
        if None in (profile.height_mm, profile.width_mm, profile.web_thickness_mm):
            raise ValueError("Для двутавра не заданы геометрические размеры.")
        return i_beam_perimeter(
            profile.height_mm,
            profile.width_mm,
            profile.web_thickness_mm,
            inp.heating_mode,
        )

    if profile.profile_type == PTMProfileType.CHANNEL:
        if None in (profile.height_mm, profile.width_mm, profile.web_thickness_mm):
            raise ValueError("Для швеллера не заданы геометрические размеры.")
        return channel_perimeter(
            profile.height_mm,
            profile.width_mm,
            profile.web_thickness_mm,
            inp.heating_mode,
        )

    if profile.profile_type == PTMProfileType.BOX:
        if None in (profile.width_mm, profile.height_mm):
            raise ValueError("Для профиля не заданы геометрические размеры.")
        return box_perimeter(profile.width_mm, profile.height_mm, inp.heating_mode)

    raise ValueError(
        f"Для типа «{profile.profile_type.value}» пока нужен пользовательский обогреваемый периметр."
    )


def calculate(inp: PTMCalculationInput) -> PTMCalculationResult:
    if inp.length_m <= 0:
        raise ValueError("Длина должна быть больше нуля.")
    if inp.quantity <= 0:
        raise ValueError("Количество должно быть больше нуля.")

    perimeter = resolve_heated_perimeter(inp)
    ptm = calculate_ptm(inp.profile.area_cm2, perimeter)
    surface_per_m = perimeter / 1000.0
    surface_per_t = None
    if inp.profile.mass_kg_per_m is not None and inp.profile.mass_kg_per_m > 0:
        surface_per_t = surface_per_m * 1000.0 / inp.profile.mass_kg_per_m

    total_surface = surface_per_m * inp.length_m * inp.quantity
    total_mass = None
    if inp.profile.mass_kg_per_m is not None and inp.profile.mass_kg_per_m > 0:
        total_mass = inp.profile.mass_kg_per_m * inp.length_m * inp.quantity

    return PTMCalculationResult(
        ptm_mm=ptm,
        section_area_cm2=inp.profile.area_cm2,
        heated_perimeter_mm=perimeter,
        surface_m2_per_m=surface_per_m,
        surface_m2_per_t=surface_per_t,
        length_m=inp.length_m,
        quantity=inp.quantity,
        total_surface_m2=total_surface,
        total_mass_kg=total_mass,
    )


# First lossless seed for the exact profile referenced by the user's URL.
# Geometry is kept as catalogue data; the calculation engine derives PTM from
# area/perimeter instead of hardcoding a final result.
PTM_PROFILES: tuple[PTMProfile, ...] = (
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
        source="ГОСТ Р 57837-2017; публичные сортаментные таблицы",
        notes="Геометрия и масса сохранены отдельно от расчётной формулы; угловые скругления не моделируются.",
    ),
)


def list_standards() -> list[str]:
    return sorted({p.standard for p in PTM_PROFILES})


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
