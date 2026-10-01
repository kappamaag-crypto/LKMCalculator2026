from upload.app.domain.ptm import (
    HeatingMode,
    PTMCalculationInput,
    PTMProfile,
    PTMProfileType,
    PTM_PROFILES,
    STANDARD_OPTIONS,
    calculate,
    calculate_ptm,
    i_beam_perimeter,
    pipe_area_cm2,
    pipe_perimeter,
    round_bar_area_cm2,
)


def test_ptm_formula():
    assert calculate_ptm(27.16, 789.0) == 27.16 * 10.0 / 789.0


def test_gost_57837_full_profile_catalog_is_loaded():
    assert len(PTM_PROFILES) == 302
    counts = {}
    for profile in PTM_PROFILES:
        counts[profile.subtype] = counts.get(profile.subtype, 0) + 1
    assert counts == {
        "балочный нормальный": 50,
        "балочный широкополочный": 66,
        "колонный": 89,
        "свайный": 14,
        "дополнительной серии балочный": 55,
        "дополнительной серии колонный": 28,
    }

def test_reference_profile_20b1_is_present():
    profile = next(
        p for p in PTM_PROFILES
        if p.standard == "ГОСТ Р 57837-2017" and p.name == "20Б1"
    )
    assert profile.profile_type is PTMProfileType.I_BEAM
    assert profile.area_cm2 == 27.16
    assert profile.mass_kg_per_m == 21.3


def test_20b1_four_side_perimeter_and_result():
    profile = next(
        p for p in PTM_PROFILES
        if p.standard == "ГОСТ Р 57837-2017" and p.name == "20Б1"
    )
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


def test_required_sortament_choices_are_explicit():
    assert STANDARD_OPTIONS[PTMProfileType.I_BEAM] == (
        "ГОСТ Р 57837-2017",
        "СТО АСЧМ 20-93",
        "ГОСТ 26020-83",
        "ГОСТ 8239-89",
        "ГОСТ 19425-74",
        "DIN 1025",
        "СВАРНОЙ по размерам",
    )
    assert STANDARD_OPTIONS[PTMProfileType.CHANNEL] == (
        "ГОСТ 8240-97",
        "DIN 1026",
        "ГОСТ 8278-83",
    )
    assert STANDARD_OPTIONS[PTMProfileType.ANGLE] == (
        "ГОСТ 8509-93, 8510-86",
        "DIN EN 10056-1-1998",
    )
    assert STANDARD_OPTIONS[PTMProfileType.BOX] == (
        "ГОСТ 32931-2015",
        "ГОСТ 30245-2003",
        "DIN EN 10210-2-2006",
        "DIN EN 10219-2-2006",
    )


def test_pipe_and_round_bar_dimension_calculation():
    assert abs(pipe_area_cm2(100.0, 5.0) - 14.922565) < 1e-5
    assert abs(pipe_perimeter(100.0) - 314.159265) < 1e-6
    assert abs(round_bar_area_cm2(100.0) - 78.539816) < 1e-6


def test_manual_pipe_profile_produces_ptm():
    profile = PTMProfile(
        standard="По размерам",
        profile_type=PTMProfileType.PIPE,
        name="Ручная труба",
        area_cm2=None,
        mass_kg_per_m=None,
        outside_diameter_mm=100.0,
        wall_thickness_mm=5.0,
    )
    result = calculate(PTMCalculationInput(profile=profile))
    assert result.section_area_cm2 > 0
    assert result.heated_perimeter_mm > 0
    assert result.ptm_mm > 0
