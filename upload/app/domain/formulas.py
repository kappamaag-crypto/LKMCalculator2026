"""
Расчётные формулы ЛКМ / АКЗ.

ВАЖНО: формулы зафиксированы 1:1 по аудиту существующего калькулятора
(Calv1Grah1.py → update_layer_calculations и Excel).

Не изменять без явного согласования и обновления unit-тестов.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LayerCalcInput:
    """Входные данные для расчёта одного слоя."""

    density: float                  # кг/л
    solids_percent: float           # % (объёмный сухой остаток)
    dry_thickness: float            # мкм (DFT)
    losses_percent: float = 0.0     # %
    price_per_kg: float = 0.0       # руб/кг
    thinner_percent: float = 0.0    # %
    thinner_density: float = 1.0    # кг/л
    thinner_price_per_kg: float = 0.0


@dataclass(frozen=True)
class LayerCalcResult:
    """Результат расчёта одного слоя (на 1 м²)."""

    wft: float                          # мкм
    theoretical_coverage: float         # м²/л
    practical_coverage: float           # м²/л
    theoretical_consumption_l: float    # л/м²
    practical_consumption_l: float      # л/м²
    theoretical_consumption_kg: float   # кг/м²
    practical_consumption_kg: float     # кг/м²
    cost_per_m2: float                  # руб/м² (материал)
    loss_coefficient: float

    thinner_consumption_l: float = 0.0
    thinner_consumption_kg: float = 0.0
    thinner_cost_per_m2: float = 0.0


def round3(value: float) -> float:
    """Округление до 3 знаков (как в старом калькуляторе)."""
    return round(float(value), 3)


def calculate_wft(dft: float, solids_percent: float) -> float:
    """
    Толщина мокрой плёнки (мкм).

    WFT = DFT × 100 / solids_%
    """
    if dft <= 0 or solids_percent <= 0:
        return 0.0
    return round3(dft * 100.0 / solids_percent)


def calculate_theoretical_coverage(wft: float) -> float:
    """
    Теоретическая укрывистость (м²/л).

    Covering = 1000 / WFT
    """
    if wft <= 0:
        return 0.0
    return round3(1000.0 / wft)


def calculate_loss_coefficient(losses_percent: float) -> float:
    """
    Коэффициент потерь.

    K = 100 / (100 − losses_%)
    """
    if losses_percent < 0 or losses_percent >= 100:
        return 1.0
    return 100.0 / (100.0 - losses_percent)


def calculate_practical_coverage(theoretical_coverage: float, loss_coefficient: float) -> float:
    """Практическая укрывистость (м²/л) = theor / K_loss."""
    if theoretical_coverage <= 0 or loss_coefficient <= 0:
        return 0.0
    return round3(theoretical_coverage / loss_coefficient)


def calculate_consumption_l(coverage: float) -> float:
    """Расход (л/м²) = 1 / укрывистость."""
    if coverage <= 0:
        return 0.0
    return 1.0 / coverage


def calculate_consumption_kg(consumption_l: float, density: float) -> float:
    """Расход (кг/м²) = расход (л/м²) × плотность."""
    if consumption_l <= 0 or density <= 0:
        return 0.0
    return round3(consumption_l * density)


def calculate_cost(consumption_kg: float, price_per_kg: float) -> float:
    """Стоимость (руб/м²) = расход кг/м² × цена за кг."""
    if consumption_kg <= 0 or price_per_kg <= 0:
        return 0.0
    return round3(consumption_kg * price_per_kg)


def calculate_thinner(
    parent_consumption_l: float,
    thinner_percent: float,
    thinner_density: float,
    thinner_price_per_kg: float,
) -> tuple[float, float, float]:
    """
    Расчёт разбавителя/растворителя.

    Returns:
        (consumption_l, consumption_kg, cost_per_m2)
    """
    if parent_consumption_l <= 0 or thinner_percent <= 0:
        return 0.0, 0.0, 0.0

    thinner_l = round3(parent_consumption_l * (thinner_percent / 100.0))
    density = thinner_density if thinner_density > 0 else 1.0
    thinner_kg = round3(thinner_l * density)
    cost = calculate_cost(thinner_kg, thinner_price_per_kg)
    return thinner_l, thinner_kg, cost


def calculate_layer(inp: LayerCalcInput) -> LayerCalcResult:
    """
    Полный расчёт одного слоя (на 1 м²).

    Формулы строго соответствуют старому update_layer_calculations.
    """
    wft = calculate_wft(inp.dry_thickness, inp.solids_percent)
    theor_cov = calculate_theoretical_coverage(wft)
    k_loss = calculate_loss_coefficient(inp.losses_percent)
    pract_cov = calculate_practical_coverage(theor_cov, k_loss)

    theor_l = calculate_consumption_l(theor_cov)
    pract_l = calculate_consumption_l(pract_cov)

    theor_kg = calculate_consumption_kg(theor_l, inp.density)
    pract_kg = calculate_consumption_kg(pract_l, inp.density)

    cost = calculate_cost(pract_kg, inp.price_per_kg)

    thinner_l, thinner_kg, thinner_cost = calculate_thinner(
        parent_consumption_l=pract_l,
        thinner_percent=inp.thinner_percent,
        thinner_density=inp.thinner_density,
        thinner_price_per_kg=inp.thinner_price_per_kg,
    )

    return LayerCalcResult(
        wft=wft,
        theoretical_coverage=theor_cov,
        practical_coverage=pract_cov,
        theoretical_consumption_l=round3(theor_l),
        practical_consumption_l=round3(pract_l),
        theoretical_consumption_kg=theor_kg,
        practical_consumption_kg=pract_kg,
        cost_per_m2=cost,
        loss_coefficient=k_loss,
        thinner_consumption_l=thinner_l,
        thinner_consumption_kg=thinner_kg,
        thinner_cost_per_m2=thinner_cost,
    )


def scale_to_area(per_m2: float, area_m2: float) -> float:
    """Масштабирование значения с 1 м² на заданную площадь."""
    if area_m2 <= 0:
        return 0.0
    return round3(per_m2 * area_m2)


def calculate_packages(required_kg: float, packaging_kg: Optional[float]) -> tuple[int, float, float]:
    """
    Расчёт количества упаковок.

    Returns:
        (packages_count, purchase_kg, remainder_kg)
    """
    if required_kg <= 0 or not packaging_kg or packaging_kg <= 0:
        return 0, 0.0, 0.0

    import math
    packages = math.ceil(required_kg / packaging_kg)
    purchase = round3(packages * packaging_kg)
    remainder = round3(purchase - required_kg)
    return packages, purchase, remainder


def total_area(area_per_element: float, elements_count: int) -> float:
    """Общая площадь = площадь одного элемента × количество."""
    if area_per_element <= 0 or elements_count <= 0:
        return 0.0
    return round3(area_per_element * elements_count)