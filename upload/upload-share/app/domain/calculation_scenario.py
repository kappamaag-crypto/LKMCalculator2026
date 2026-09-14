"""Domain model for calculation scenarios.

A scenario is a named set of coating-system alternatives evaluated against the
same object/context. It deliberately contains no calculation formulas and does
not duplicate CalculationService.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from app.domain.models import CoatingSystem, ObjectData
from app.domain.engineering_context import EngineeringContext


@dataclass(frozen=True)
class CalculationScenario:
    name: str
    object_data: ObjectData
    alternatives: Tuple[CoatingSystem, ...]
    engineering_context: EngineeringContext | None = None
    notes: str = ""

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("Scenario name is required")
        if not self.alternatives:
            raise ValueError("Scenario requires at least one system alternative")
        seen: set[str] = set()
        for system in self.alternatives:
            label = (system.system_name or "").strip()
            if not label:
                raise ValueError("Scenario alternative requires a system name")
            key = label.casefold()
            if key in seen:
                raise ValueError(f"Duplicate scenario alternative: {label}")
            seen.add(key)
            if not system.layers:
                raise ValueError(f"Scenario system has no layers: {label}")

    @property
    def alternative_count(self) -> int:
        return len(self.alternatives)
