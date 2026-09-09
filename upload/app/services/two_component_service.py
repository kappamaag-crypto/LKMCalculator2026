"""Сервис информационного представления 2К-материалов.

Сервис намеренно не содержит закупочной логики: только данные компонентов,
соотношение смешения и технологические ограничения.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.domain.models import MaterialComponent, MaterialMix
from app.domain.two_component import TwoComponentResult
from app.infrastructure.database.two_component_repository import TwoComponentRepository


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

    @classmethod
    def describe_from_database(cls, session: Session, material_id: int) -> Optional[TwoComponentResult]:
        """Получить карточку 2К из БД. Если подтверждённых данных нет — вернуть None."""
        repository = TwoComponentRepository(session)
        mix = repository.get_mix(material_id)
        if mix is None:
            return None
        components = repository.get_components(material_id)
        component_a = next((c for c in components if c.component_code.upper() == "A"), None)
        component_b = next((c for c in components if c.component_code.upper() == "B"), None)
        return cls.describe(mix, component_a, component_b)
