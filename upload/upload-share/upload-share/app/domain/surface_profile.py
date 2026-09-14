"""Structured surface-preparation and roughness data.

The model intentionally keeps grade identifiers source-backed instead of
hard-coding normative meanings. This prevents an absent standard/source from
being interpreted as a permission or prohibition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .normative import NormativeSource, UNKNOWN

PreparationMethod = Literal["Sa", "St", "OTHER", "UNKNOWN"]
ProfileMeasurement = Literal["Rz", "Ry5", "Rmax", "UNKNOWN"]


@dataclass(frozen=True)
class SurfacePreparation:
    """A structured surface-cleanliness record."""

    method: PreparationMethod = "UNKNOWN"
    grade: str = ""
    standard: NormativeSource | None = None
    assessment: str = UNKNOWN
    notes: str = ""

    def __post_init__(self) -> None:
        method = self.method
        if method not in {"Sa", "St", "OTHER", "UNKNOWN"}:
            raise ValueError("unsupported surface preparation method")
        assessment = self.assessment.strip().upper()
        if assessment not in {"KNOWN", UNKNOWN}:
            raise ValueError("assessment must be KNOWN or UNKNOWN")
        if assessment == "KNOWN" and self.standard is None:
            raise ValueError("KNOWN preparation assessment requires a standard/source")
        object.__setattr__(self, "assessment", assessment)

    @property
    def is_known(self) -> bool:
        return self.assessment == "KNOWN"


@dataclass(frozen=True)
class SurfaceProfile:
    """Measured or specified blast profile, kept independent from Sa/St grade."""

    measurement: ProfileMeasurement = "UNKNOWN"
    minimum_um: float | None = None
    nominal_um: float | None = None
    maximum_um: float | None = None
    standard: NormativeSource | None = None
    assessment: str = UNKNOWN
    notes: str = ""

    def __post_init__(self) -> None:
        if self.measurement not in {"Rz", "Ry5", "Rmax", "UNKNOWN"}:
            raise ValueError("unsupported profile measurement")
        for name in ("minimum_um", "nominal_um", "maximum_um"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.minimum_um is not None and self.maximum_um is not None and self.minimum_um > self.maximum_um:
            raise ValueError("minimum_um cannot exceed maximum_um")
        if self.assessment.strip().upper() not in {"KNOWN", UNKNOWN}:
            raise ValueError("assessment must be KNOWN or UNKNOWN")
        if self.assessment.strip().upper() == "KNOWN" and self.standard is None:
            raise ValueError("KNOWN profile assessment requires a standard/source")
        object.__setattr__(self, "assessment", self.assessment.strip().upper())

    @property
    def is_measured(self) -> bool:
        return any(value is not None for value in (self.minimum_um, self.nominal_um, self.maximum_um))

    @property
    def is_known(self) -> bool:
        return self.assessment == "KNOWN"


@dataclass(frozen=True)
class SurfaceCondition:
    """Combined structured surface state used by future validation services."""

    preparation: SurfacePreparation = SurfacePreparation()
    profile: SurfaceProfile = SurfaceProfile()
    substrate: str = ""
    contamination_status: str = UNKNOWN
    moisture_status: str = UNKNOWN

    def __post_init__(self) -> None:
        for field_name in ("contamination_status", "moisture_status"):
            value = getattr(self, field_name).strip().upper()
            if value not in {"KNOWN", "ACCEPTABLE", "UNACCEPTABLE", UNKNOWN}:
                raise ValueError(f"unsupported {field_name}: {value}")
            object.__setattr__(self, field_name, value)
