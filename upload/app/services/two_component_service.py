"""Сервис информационного представления 2К-материалов.

Сервис намеренно не содержит закупочной логики: только данные компонентов,
соотношение смешения и технологические ограничения.
"""

from __future__ import annotations

from typing import Optional

from app.domain.models import MaterialComponent, MaterialMix
from app.domain.two_component import TwoComponentResult


class TwoComponentService:
    """Формирует информационную карточку 2К-материала."""

    @staticmethod
    def describe(
        mix: MaterialMix,
        component_a: Optional[MaterialComponent] = None,
        component_b: Optional[MaterialComponent] = None,
    ) -> TwoComponentResult:
        if mix.mix_ratio_a <= 0 or mix.mix_ratio_b <= 0:
            raise ValueError("Соотношение компонентов должно быть больше нуля")
        if mix.ratio_basis not in {"mass", "volume"}:
            raise ValueError("Основа соотношения должна быть mass или volume")

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
