"""Controlled loss assumptions for coating calculations."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LossProfile:
    """Explicit, traceable loss assumption used by the calculation domain."""

    name: str
    percent: float
    source: str = "USER"
    note: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("LossProfile name must not be empty")
        if not self.source.strip():
            raise ValueError("LossProfile source must not be empty")
        self._validate_percent(self.percent)

    @staticmethod
    def _validate_percent(percent: float) -> None:
        if percent < 0 or percent >= 100:
            raise ValueError("LossProfile percent must be >= 0 and < 100")

    def resolve(self, explicit_percent: Optional[float] = None) -> float:
        """Return an explicit override when supplied, otherwise profile value."""
        if explicit_percent is None:
            return self.percent
        self._validate_percent(explicit_percent)
        return explicit_percent

    @classmethod
    def none(cls) -> "LossProfile":
        """Profile representing an explicit zero-loss assumption."""
        return cls(name="Без потерь", percent=0.0, source="SYSTEM")


@dataclass(frozen=True)
class ResolvedLosses:
    """Traceable resolved loss percent for LayerResult provenance (§28 / §26)."""

    percent: float
    source: str  # EXPLICIT | PROFILE | DEFAULT
    profile_name: str = ""
    note: str = ""

    def __post_init__(self) -> None:
        if self.source not in {"EXPLICIT", "PROFILE", "DEFAULT"}:
            raise ValueError("ResolvedLosses.source must be EXPLICIT, PROFILE, or DEFAULT")
        LossProfile._validate_percent(self.percent)
