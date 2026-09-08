"""Информационные данные о 2К материалах.

2К-компоненты здесь описываются только для инженерной информации.
Расчёт закупки, комплектов и остатков намеренно отсутствует: калькулятор
отвечает за потребность материала и стоимость работ, а не за складской учёт.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.domain.models import MaterialComponent, MaterialMix

RATIO_MASS = "mass"
RATIO_VOLUME = "volume"


@dataclass(frozen=True)
class TwoComponentResult:
    """Информационная карточка 2К материала без закупочных расчётов."""

    ratio_a: float
    ratio_b: float
    ratio_basis: str
    component_a: MaterialComponent
    component_b: MaterialComponent
    working_time_minutes: Optional[float] = None
    induction_time_minutes: Optional[float] = None
    temperature_reference: Optional[float] = None
    notes: str = ""

    @property
    def ratio_text(self) -> str:
        basis = "по массе" if self.ratio_basis == RATIO_MASS else "по объёму"
        return f"{self.ratio_a:g}:{self.ratio_b:g} {basis}"


class TwoComponentCalculationError(ValueError):
    """Некорректные данные 2К материала."""


class TwoComponentService:
    """Проверка и представление справочной информации 2К материала."""

    @staticmethod
    def describe(
        mix: MaterialMix,
        component_a: MaterialComponent,
        component_b: MaterialComponent,
    ) -> TwoComponentResult:
        if mix.mix_ratio_a <= 0 or mix.mix_ratio_b <= 0:
            raise TwoComponentCalculationError("Соотношение компонентов должно быть положительным.")
        if mix.ratio_basis not in (RATIO_MASS, RATIO_VOLUME):
            raise TwoComponentCalculationError(f"Неизвестная база соотношения: {mix.ratio_basis}")

        return TwoComponentResult(
            ratio_a=mix.mix_ratio_a,
            ratio_b=mix.mix_ratio_b,
            ratio_basis=mix.ratio_basis,
            component_a=component_a,
            component_b=component_b,
            working_time_minutes=mix.working_time_minutes,
            induction_time_minutes=mix.induction_time_minutes,
            temperature_reference=mix.temperature_reference,
            notes=mix.notes,
        )
