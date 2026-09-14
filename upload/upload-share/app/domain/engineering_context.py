"""Immutable engineering context carried alongside a calculation."""

from __future__ import annotations

from dataclasses import dataclass

from .normative import NormativeModel, UNKNOWN
from .surface_profile import SurfaceCondition


@dataclass(frozen=True)
class EngineeringContext:
    """Source-backed normative and surface context for an engineering result."""

    normative_model: NormativeModel | None = None
    surface_condition: SurfaceCondition = SurfaceCondition()

    @property
    def normative_status(self) -> str:
        """Return KNOWN only when at least one explicit normative rule is known."""
        if self.normative_model is None:
            return UNKNOWN
        return "KNOWN" if self.normative_model.known_rules() else UNKNOWN

    @property
    def has_known_surface_assessment(self) -> bool:
        return self.surface_condition.preparation.is_known or self.surface_condition.profile.is_known
