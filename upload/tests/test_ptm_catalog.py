from upload.scripts import rebuild_ptm_catalog as builder


def test_target_url_matches_calculator_contract():
    url = builder.build_target_url("1", "20-93", "25С1")
    assert "tb=1" in url
    assert "sn=20-93" in url
    assert "pn=25" in url


def test_result_parser_reads_reference_fields():
    html = """
    <div>Приведенная толщина металла:</div><input value="5,57">
    <div>Площадь сечения:</div><input value="82">
    <div>Обогреваемый периметр:</div><input value="1472">
    <div>Площадь поверхности / 1 м:</div><input value="1,472">
    <div>Площадь поверхности / 1 т:</div><input value="1,79">
    """
    values = builder.extract_result_values(html)
    assert values["ptm_mm"] == 5.57
    assert values["area_cm2"] == 82.0
    assert values["perimeter_mm"] == 1472.0
    assert values["surface_m2_per_m"] == 1.472
    assert values["surface_m2_per_t"] == 1.79


def test_profile_options_parser_ignores_placeholder():
    html = """
    <select name="pn">
      <option value="">Выберите</option>
      <option value="20Б1">20Б1</option>
      <option value="25С1">25С1</option>
    </select>
    """
    assert builder.extract_profile_options(html) == ["20Б1", "25С1"]


def test_required_target_standard_groups_are_present():
    assert any(sn == "20-93" for sn, _ in builder.TARGET_STANDARDS["1"])
    assert any(sn == "57837-2017" for sn, _ in builder.TARGET_STANDARDS["1"])
    assert any(sn == "8240-97" for sn, _ in builder.TARGET_STANDARDS["2"])
    assert any(sn == "8509-93" for sn, _ in builder.TARGET_STANDARDS["3"])
    assert any(sn == "30245-2003" for sn, _ in builder.TARGET_STANDARDS["4"])


def test_mass_can_be_recovered_from_surface_values():
    surface_m = 1.472
    surface_t = 1.79
    mass = surface_m * 1000.0 / surface_t
    assert abs(mass - 822.346368715) < 1e-9
