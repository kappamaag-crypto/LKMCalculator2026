"""Application service for PTM calculations."""
from __future__ import annotations

from app.domain.ptm import (
    HeatingMode,
    PTMCalculationInput,
    PTMCalculationResult,
    PTMProfile,
    PTMProfileType,
    calculate,
    list_profiles,
    list_standards,
)


class PTMService:
    """Thin application boundary around the pure PTM domain model."""

    def list_standards(
        self,
        profile_type: PTMProfileType | None = None,
    ) -> list[str]:
        return list_standards(profile_type=profile_type)

    def list_profiles(
        self,
        standard: str | None = None,
        profile_type: PTMProfileType | None = None,
    ) -> list[PTMProfile]:
        return list_profiles(standard=standard, profile_type=profile_type)

    def calculate(
        self,
        profile: PTMProfile,
        *,
        heating_mode: HeatingMode = HeatingMode.FOUR_SIDES,
        heated_perimeter_mm: float | None = None,
        length_m: float = 1.0,
        quantity: int = 1,
    ) -> PTMCalculationResult:
        return calculate(
            PTMCalculationInput(
                profile=profile,
                heating_mode=heating_mode,
                heated_perimeter_mm=heated_perimeter_mm,
                length_m=length_m,
                quantity=quantity,
            )
        )
