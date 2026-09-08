"""Инженерный расчёт 2К материалов.

Сервис работает с фактическими компонентами A/B и комплектами. Он не знает
о UI и не смешивает стоимость/расход с коммерческой наценкой.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_CEILING
from typing import Optional, Sequence


RATIO_MASS = "mass"
RATIO_VOLUME = "volume"


@dataclass(frozen=True)
class MaterialComponent:
    id: Optional[int] = None
    material_id: Optional[int] = None
    component_code: str = "A"
    name: str = ""
    density_kg_l: Optional[float] = None
    price_per_kg: Optional[float] = None
    price_per_liter: Optional[float] = None
    packaging_kg: Optional[float] = None
    packaging_l: Optional[float] = None
    active: bool = True


@dataclass(frozen=True)
class MaterialMix:
    material_id: int
    mix_ratio_a: float
    mix_ratio_b: float
    ratio_basis: str = RATIO_MASS
    working_time_minutes: Optional[float] = None
    induction_time_minutes: Optional[float] = None
    temperature_reference: Optional[float] = None
    notes: str = ""


@dataclass(frozen=True)
class Package:
    id: Optional[int] = None
    material_id: Optional[int] = None
    component_id: Optional[int] = None
    package_name: str = ""
    net_weight_kg: Optional[float] = None
    net_volume_l: Optional[float] = None
    units_per_set: int = 1
    package_type: str = "single"
    is_component_package: bool = False
    active: bool = True


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
    def calculate(
        required_mix_kg: float,
        mix: MaterialMix,
        component_a: MaterialComponent,
        component_b: MaterialComponent,
    ) -> TwoComponentResult:
        if required_mix_kg <= 0:
            raise TwoComponentCalculationError("Потребность смеси должна быть больше нуля.")
        if mix.mix_ratio_a <= 0 or mix.mix_ratio_b <= 0:
            raise TwoComponentCalculationError("Соотношение компонентов должно быть положительным.")
        if mix.ratio_basis not in (RATIO_MASS, RATIO_VOLUME):
            raise TwoComponentCalculationError(f"Неизвестная база соотношения: {mix.ratio_basis}")

        if mix.ratio_basis == RATIO_MASS:
            ratio_total = mix.mix_ratio_a + mix.mix_ratio_b
            a_kg = required_mix_kg * mix.mix_ratio_a / ratio_total
            b_kg = required_mix_kg * mix.mix_ratio_b / ratio_total
            sets, purchase_a, purchase_b = TwoComponentService._mass_packages(a_kg, b_kg, component_a, component_b)
        else:
            if not component_a.density_kg_l or component_a.density_kg_l <= 0:
                raise TwoComponentCalculationError("Для объёмного соотношения нужна плотность компонента A.")
            if not component_b.density_kg_l or component_b.density_kg_l <= 0:
                raise TwoComponentCalculationError("Для объёмного соотношения нужна плотность компонента B.")
            ratio_total = mix.mix_ratio_a + mix.mix_ratio_b
            volume_total = required_mix_kg / (
                (mix.mix_ratio_a / ratio_total) * component_a.density_kg_l
                + (mix.mix_ratio_b / ratio_total) * component_b.density_kg_l
            )
            a_l = volume_total * mix.mix_ratio_a / ratio_total
            b_l = volume_total * mix.mix_ratio_b / ratio_total
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
        return TwoComponentResult(
            required_mix_kg=required_mix_kg,
            component_a_kg=a_kg,
            component_b_kg=b_kg,
            sets=sets,
            purchase_a_kg=purchase_a,
            purchase_b_kg=purchase_b,
            remainder_a_kg=remainder_a,
            remainder_b_kg=remainder_b,
            cost_a=cost_a,
            cost_b=cost_b,
            total_cost=total_cost,
            components=purchases,
        )

    @staticmethod
    def _mass_packages(required_a: float, required_b: float, a: MaterialComponent, b: MaterialComponent) -> tuple[int, float, float]:
        if not a.packaging_kg or not b.packaging_kg or a.packaging_kg <= 0 or b.packaging_kg <= 0:
            raise TwoComponentCalculationError("Для расчёта комплектов нужны фасовки A и B в кг.")
        sets_a = int((Decimal(str(required_a)) / Decimal(str(a.packaging_kg))).to_integral_value(rounding=ROUND_CEILING))
        sets_b = int((Decimal(str(required_b)) / Decimal(str(b.packaging_kg))).to_integral_value(rounding=ROUND_CEILING))
        # Для набора A+B количество комплектов определяется минимальным целым числом,
        # которое обеспечивает оба компонента. Фасовки могут быть разными.
        sets = max(sets_a, sets_b)
        return sets, sets * a.packaging_kg, sets * b.packaging_kg

    @staticmethod
    def _volume_packages(required_a_l: float, required_b_l: float, a: MaterialComponent, b: MaterialComponent) -> tuple[int, float, float]:
        if not a.packaging_l or not b.packaging_l or a.packaging_l <= 0 or b.packaging_l <= 0:
            raise TwoComponentCalculationError("Для объёмного соотношения нужны фасовки A и B в л.")
        sets_a = int((Decimal(str(required_a_l)) / Decimal(str(a.packaging_l))).to_integral_value(rounding=ROUND_CEILING))
        sets_b = int((Decimal(str(required_b_l)) / Decimal(str(b.packaging_l))).to_integral_value(rounding=ROUND_CEILING))
        sets = max(sets_a, sets_b)
        return sets, sets * a.packaging_l * (a.density_kg_l or 0), sets * b.packaging_l * (b.density_kg_l or 0)

    @staticmethod
    def _component_cost(purchase_kg: float, component: MaterialComponent) -> Optional[Decimal]:
        if component.price_per_kg is not None:
            return (Decimal(str(purchase_kg)) * Decimal(str(component.price_per_kg))).quantize(Decimal("0.01"))
        if component.price_per_liter is not None and component.density_kg_l and component.density_kg_l > 0:
            liters = Decimal(str(purchase_kg)) / Decimal(str(component.density_kg_l))
            return (liters * Decimal(str(component.price_per_liter))).quantize(Decimal("0.01"))
        return None
