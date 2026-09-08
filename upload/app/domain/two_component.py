"""Инженерный расчёт 2К материалов."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_CEILING
from typing import Optional

from app.domain.models import MaterialComponent, MaterialMix

RATIO_MASS = "mass"
RATIO_VOLUME = "volume"


@dataclass(frozen=True)
class ComponentPurchase:
    component_code: str
    required_kg: float
    purchase_kg: float
    packages: int
    remainder_kg: float
    cost: Optional[Decimal]


@dataclass(frozen=True)
class TwoComponentResult:
    required_mix_kg: float
    component_a_kg: float
    component_b_kg: float
    sets: int
    purchase_a_kg: float
    purchase_b_kg: float
    remainder_a_kg: float
    remainder_b_kg: float
    cost_a: Optional[Decimal]
    cost_b: Optional[Decimal]
    total_cost: Optional[Decimal]
    components: tuple[ComponentPurchase, ...] = field(default_factory=tuple)


class TwoComponentCalculationError(ValueError):
    """Некорректные данные 2К материала."""


class TwoComponentService:
    """Расчёт компонентов A/B по массе или объёму."""

    @staticmethod
    def calculate(required_mix_kg: float, mix: MaterialMix, component_a: MaterialComponent, component_b: MaterialComponent) -> TwoComponentResult:
        if required_mix_kg <= 0:
            raise TwoComponentCalculationError("Потребность смеси должна быть больше нуля.")
        if mix.mix_ratio_a <= 0 or mix.mix_ratio_b <= 0:
            raise TwoComponentCalculationError("Соотношение компонентов должно быть положительным.")
        if mix.ratio_basis not in (RATIO_MASS, RATIO_VOLUME):
            raise TwoComponentCalculationError(f"Неизвестная база соотношения: {mix.ratio_basis}")

        if mix.ratio_basis == RATIO_MASS:
            total_ratio = mix.mix_ratio_a + mix.mix_ratio_b
            a_kg = required_mix_kg * mix.mix_ratio_a / total_ratio
            b_kg = required_mix_kg * mix.mix_ratio_b / total_ratio
            sets, purchase_a, purchase_b = TwoComponentService._mass_packages(a_kg, b_kg, component_a, component_b)
        else:
            if not component_a.density_kg_l or component_a.density_kg_l <= 0 or not component_b.density_kg_l or component_b.density_kg_l <= 0:
                raise TwoComponentCalculationError("Для объёмного соотношения нужны положительные плотности A и B.")
            total_ratio = mix.mix_ratio_a + mix.mix_ratio_b
            mix_volume_l = required_mix_kg / (
                (mix.mix_ratio_a / total_ratio) * component_a.density_kg_l
                + (mix.mix_ratio_b / total_ratio) * component_b.density_kg_l
            )
            a_l = mix_volume_l * mix.mix_ratio_a / total_ratio
            b_l = mix_volume_l * mix.mix_ratio_b / total_ratio
            a_kg = a_l * component_a.density_kg_l
            b_kg = b_l * component_b.density_kg_l
            sets, purchase_a, purchase_b = TwoComponentService._volume_packages(a_l, b_l, component_a, component_b)

        remainder_a = purchase_a - a_kg
        remainder_b = purchase_b - b_kg
        cost_a = TwoComponentService._component_cost(purchase_a, component_a)
        cost_b = TwoComponentService._component_cost(purchase_b, component_b)
        total_cost = cost_a + cost_b if cost_a is not None and cost_b is not None else None
        purchases = (
            ComponentPurchase(component_a.component_code, a_kg, purchase_a, sets, remainder_a, cost_a),
            ComponentPurchase(component_b.component_code, b_kg, purchase_b, sets, remainder_b, cost_b),
        )
        return TwoComponentResult(required_mix_kg, a_kg, b_kg, sets, purchase_a, purchase_b, remainder_a, remainder_b, cost_a, cost_b, total_cost, purchases)

    @staticmethod
    def _mass_packages(required_a: float, required_b: float, a: MaterialComponent, b: MaterialComponent) -> tuple[int, float, float]:
        if not a.packaging_kg or not b.packaging_kg or a.packaging_kg <= 0 or b.packaging_kg <= 0:
            raise TwoComponentCalculationError("Для расчёта комплектов нужны фасовки A и B в кг.")
        sets_a = int((Decimal(str(required_a)) / Decimal(str(a.packaging_kg))).to_integral_value(rounding=ROUND_CEILING))
        sets_b = int((Decimal(str(required_b)) / Decimal(str(b.packaging_kg))).to_integral_value(rounding=ROUND_CEILING))
        sets = max(sets_a, sets_b)
        return sets, sets * a.packaging_kg, sets * b.packaging_kg

    @staticmethod
    def _volume_packages(required_a_l: float, required_b_l: float, a: MaterialComponent, b: MaterialComponent) -> tuple[int, float, float]:
        if not a.packaging_l or not b.packaging_l or a.packaging_l <= 0 or b.packaging_l <= 0:
            raise TwoComponentCalculationError("Для объёмного соотношения нужны фасовки A и B в л.")
        sets_a = int((Decimal(str(required_a_l)) / Decimal(str(a.packaging_l))).to_integral_value(rounding=ROUND_CEILING))
        sets_b = int((Decimal(str(required_b_l)) / Decimal(str(b.packaging_l))).to_integral_value(rounding=ROUND_CEILING))
        sets = max(sets_a, sets_b)
        return sets, sets * a.packaging_l * a.density_kg_l, sets * b.packaging_l * b.density_kg_l

    @staticmethod
    def _component_cost(purchase_kg: float, component: MaterialComponent) -> Optional[Decimal]:
        if component.price_per_kg is not None:
            return (Decimal(str(purchase_kg)) * Decimal(str(component.price_per_kg))).quantize(Decimal("0.01"))
        if component.price_per_liter is not None and component.density_kg_l and component.density_kg_l > 0:
            liters = Decimal(str(purchase_kg)) / Decimal(str(component.density_kg_l))
            return (liters * Decimal(str(component.price_per_liter))).quantize(Decimal("0.01"))
        return None
