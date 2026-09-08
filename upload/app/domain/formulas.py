"""
Расчётные формулы ЛКМ / АКЗ.

Формулы разделяют сухую плёнку, мокрую плёнку, разбавление и потери.
Критически важно: процент разбавления не может трактоваться одинаково
для всех производителей, поэтому basis задаётся явно.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# Допустимые основания дозирования разбавителя.
# BY_PAINT_VOLUME: X% от объёма исходного ЛКМ — наиболее распространённая модель.
# BY_MIX_VOLUME: X% от конечного объёма смеси.
# BY_MASS: X% от массы исходного ЛКМ.
# BY_COMPONENT_VOLUME: X% от объёма компонента/смеси, используемого как база.
DILUTION_BASIS_BY_PAINT_VOLUME = "BY_PAINT_VOLUME"
DILUTION_BASIS_BY_MIX_VOLUME = "BY_MIX_VOLUME"
DILUTION_BASIS_BY_MASS = "BY_MASS"
DILUTION_BASIS_BY_COMPONENT_VOLUME = "BY_COMPONENT_VOLUME"


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
    thinner_basis: str = DILUTION_BASIS_BY_PAINT_VOLUME


@dataclass(frozen=True)
class LayerCalcResult:
    """Результат расчёта одного слоя (на 1 м²)."""

    wft: float                          # мкм, итоговая мокрая толщина смеси
    theoretical_coverage: float         # м²/л, по итоговому WFT смеси
    practical_coverage: float           # м²/л
    theoretical_consumption_l: float    # л/м², объём исходного ЛКМ
    practical_consumption_l: float      # л/м², объём исходного ЛКМ
    theoretical_consumption_kg: float   # кг/м², исходный ЛКМ
    practical_consumption_kg: float     # кг/м², исходный ЛКМ
    cost_per_m2: float                  # руб/м² (исходный ЛКМ)
    loss_coefficient: float

    thinner_consumption_l: float = 0.0
    thinner_consumption_kg: float = 0.0
    thinner_cost_per_m2: float = 0.0


def round3(value: float) -> float:
    """Округление отображаемого значения до 3 знаков."""
    return round(float(value), 3)


def calculate_wft(dft: float, solids_percent: float) -> float:
    """WFT без разбавителя: DFT / (SV/100)."""
    if dft <= 0 or solids_percent <= 0:
        return 0.0
    return round3(dft * 100.0 / solids_percent)


def calculate_wft_with_dilution(
    dft: float,
    solids_percent: float,
    thinner_percent: float = 0.0,
    thinner_density: float = 1.0,
    paint_density: float = 1.0,
    basis: str = DILUTION_BASIS_BY_PAINT_VOLUME,
) -> float:
    """
    WFT с учётом разбавителя.

    Сухой остаток содержится в исходном ЛКМ. Разбавитель добавляет мокрый
    объём, но не добавляет сухого остатка. Поэтому сначала определяется
    базовый WFT ЛКМ, затем к нему добавляется объём разбавителя.

    BY_PAINT_VOLUME:
        thinner = paint_volume * p/100.
    BY_MIX_VOLUME:
        thinner = final_mix * p/100, поэтому final_mix = paint/(1-p).
    BY_MASS:
        thinner_mass = paint_mass * p/100; объём зависит от плотности.
    BY_COMPONENT_VOLUME:
        трактуется как объёмная дозировка относительно базового компонента,
        аналогично BY_PAINT_VOLUME, но оставлена отдельной для явной фиксации.
    """
    base_wft = calculate_wft(dft, solids_percent)
    if base_wft <= 0 or thinner_percent <= 0:
        return base_wft

    p = thinner_percent / 100.0
    if p >= 1.0:
        raise ValueError("Процент разбавления должен быть меньше 100%.")

    if basis in (DILUTION_BASIS_BY_PAINT_VOLUME, DILUTION_BASIS_BY_COMPONENT_VOLUME):
        added_volume_ratio = p
    elif basis == DILUTION_BASIS_BY_MIX_VOLUME:
        added_volume_ratio = p / (1.0 - p)
    elif basis == DILUTION_BASIS_BY_MASS:
        if paint_density <= 0 or thinner_density <= 0:
            raise ValueError("Для разбавления по массе нужны положительные плотности.")
        # На 1 л исходного ЛКМ добавляем (density * p) кг разбавителя.
        added_volume_ratio = paint_density * p / thinner_density
    else:
        raise ValueError(f"Неизвестное основание разбавления: {basis}")

    return round3(base_wft * (1.0 + added_volume_ratio))


def calculate_theoretical_coverage(wft: float) -> float:
    """Теоретическая укрывистость по итоговой мокрой толщине, м²/л."""
    if wft <= 0:
        return 0.0
    return round3(1000.0 / wft)


def calculate_loss_coefficient(losses_percent: float) -> float:
    """Коэффициент потерь: K = 100 / (100 − losses)."""
    if losses_percent < 0 or losses_percent >= 100:
        return 1.0
    return 100.0 / (100.0 - losses_percent)


def calculate_practical_coverage(theoretical_coverage: float, loss_coefficient: float) -> float:
    """Практическая укрывистость = theoretical / K_loss."""
    if theoretical_coverage <= 0 or loss_coefficient <= 0:
        return 0.0
    return round3(theoretical_coverage / loss_coefficient)


def calculate_consumption_l(coverage: float) -> float:
    """Расход исходного ЛКМ (л/м²) = 1 / укрывистость."""
    if coverage <= 0:
        return 0.0
    return 1.0 / coverage


def calculate_consumption_kg(consumption_l: float, density: float) -> float:
    """Расход (кг/м²) = расход (л/м²) × плотность."""
    if consumption_l <= 0 or density <= 0:
        return 0.0
    return round3(consumption_l * density)


def calculate_cost(consumption_kg: float, price_per_kg: float) -> float:
    """Стоимость = расход кг/м² × цена за кг."""
    if consumption_kg <= 0 or price_per_kg <= 0:
        return 0.0
    return round3(consumption_kg * price_per_kg)


def calculate_thinner(
    parent_consumption_l: float,
    thinner_percent: float,
    thinner_density: float,
    thinner_price_per_kg: float,
    basis: str = DILUTION_BASIS_BY_PAINT_VOLUME,
    parent_density: float = 1.0,
) -> tuple[float, float, float]:
    """Расчёт фактического расхода разбавителя на 1 м²."""
    if parent_consumption_l <= 0 or thinner_percent <= 0:
        return 0.0, 0.0, 0.0
    if thinner_density <= 0:
        raise ValueError("Плотность разбавителя должна быть положительной.")

    p = thinner_percent / 100.0
    if p >= 1.0:
        raise ValueError("Процент разбавления должен быть меньше 100%.")

    if basis in (DILUTION_BASIS_BY_PAINT_VOLUME, DILUTION_BASIS_BY_COMPONENT_VOLUME):
        thinner_l = parent_consumption_l * p
    elif basis == DILUTION_BASIS_BY_MIX_VOLUME:
        thinner_l = parent_consumption_l * p / (1.0 - p)
    elif basis == DILUTION_BASIS_BY_MASS:
        if parent_density <= 0:
            raise ValueError("Плотность ЛКМ должна быть положительной для дозирования по массе.")
        thinner_l = parent_consumption_l * parent_density * p / thinner_density
    else:
        raise ValueError(f"Неизвестное основание разбавления: {basis}")

    thinner_l = round3(thinner_l)
    thinner_kg = round3(thinner_l * thinner_density)
    cost = calculate_cost(thinner_kg, thinner_price_per_kg)
    return thinner_l, thinner_kg, cost


def calculate_layer(inp: LayerCalcInput) -> LayerCalcResult:
    """Полный расчёт одного слоя на 1 м²."""
    wft = calculate_wft_with_dilution(
        inp.dry_thickness,
        inp.solids_percent,
        inp.thinner_percent,
        inp.thinner_density,
        inp.density,
        inp.thinner_basis,
    )

    # Расход исходного ЛКМ определяется сухим остатком, а не объёмом
    # разбавленной смеси. Это принципиально для корректной закупки ЛКМ.
    base_wft = calculate_wft(inp.dry_thickness, inp.solids_percent)
    theor_paint_l = 0.0 if base_wft <= 0 else 1000.0 / base_wft

    k_loss = calculate_loss_coefficient(inp.losses_percent)
    pract_paint_l = theor_paint_l * k_loss

    theor_cov = 0.0 if theor_paint_l <= 0 else 1.0 / theor_paint_l
    pract_cov = 0.0 if pract_paint_l <= 0 else 1.0 / pract_paint_l

    theor_kg = calculate_consumption_kg(theor_paint_l, inp.density)
    pract_kg = calculate_consumption_kg(pract_paint_l, inp.density)
    cost = calculate_cost(pract_kg, inp.price_per_kg)

    thinner_l, thinner_kg, thinner_cost = calculate_thinner(
        parent_consumption_l=pract_paint_l,
        thinner_percent=inp.thinner_percent,
        thinner_density=inp.thinner_density,
        thinner_price_per_kg=inp.thinner_price_per_kg,
        basis=inp.thinner_basis,
        parent_density=inp.density,
    )

    return LayerCalcResult(
        wft=wft,
        theoretical_coverage=round3(theor_cov),
        practical_coverage=round3(pract_cov),
        theoretical_consumption_l=round3(theor_paint_l),
        practical_consumption_l=round3(pract_paint_l),
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
    """Расчёт количества упаковок фиксированного веса."""
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
