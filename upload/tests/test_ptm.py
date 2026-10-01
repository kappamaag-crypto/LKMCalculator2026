from upload.app.domain.ptm import (
    HeatingMode,
    PTMCalculationInput,
    PTMProfileType,
    PTM_PROFILES,
    calculate,
    calculate_ptm,
    i_beam_perimeter,
)


def test_ptm_formula():
    assert calculate_ptm(27.16, 789.0) == 27.16 * 10.0 / 789.0


def test_reference_profile_20b1_is_present():
    profile = next(p for p in PTM_PROFILES if p.standard == "ГОСТ Р 57837-2017" and p.name == "20Б1")
    assert profile.profile_type is PTMProfileType.I_BEAM
    assert profile.area_cm2 == 27.16
    assert profile.mass_kg_per_m == 21.3


def test_20b1_four_side_perimeter_and_result():
    profile = next(p for p in PTM_PROFILES if p.standard == "ГОСТ Р 57837-2017" and p.name == "20Б1")
    perimeter = i_beam_perimeter(200.0, 100.0, 5.5, HeatingMode.FOUR_SIDES)
    assert perimeter == 789.0
    result = calculate(PTMCalculationInput(profile=profile))
    assert result.heated_perimeter_mm == 789.0
    assert abs(result.surface_m2_per_m - 0.789) < 1e-12
    assert abs(result.surface_m2_per_t - (0.789 * 1000.0 / 21.3)) < 1e-12


def test_custom_heated_perimeter():
    profile = next(p for p in PTM_PROFILES if p.name == "20Б1")
    result = calculate(
        PTMCalculationInput(
            profile=profile,
            heating_mode=HeatingMode.CUSTOM,
            heated_perimeter_mm=500.0,
        )
    )
    assert result.ptm_mm == 27.16 * 10.0 / 500.0
