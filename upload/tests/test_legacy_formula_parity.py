"""§19 legacy parity: core АКЗ formulas v2 ↔ v3.

v3 keeps full float precision (no intermediate round3). v2 applied round3 on
WFT / coverage / consumption_kg. Algebraic identities are the same; numerical
drift from intermediate rounding is an intentional v3 invariant, not a defect.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from app.domain import formulas as v3f


def _load_v2_formulas():
    root = Path(__file__).resolve().parents[2]
    path = root / "v2" / "app" / "domain" / "formulas.py"
    if not path.exists():
        pytest.skip("v2 formulas baseline not present")
    name = "v2_formulas_parity_test"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def v2f():
    return _load_v2_formulas()


def test_formula_version_is_declared_in_v3():
    assert getattr(v3f, "FORMULA_VERSION", None) == "3.0"


@pytest.mark.parametrize(
    "dft,solids",
    [(100, 50), (120, 40), (1, 100), (0, 50), (100, 0)],
)
def test_wft_algebra_matches_v2_when_no_rounding_needed(v2f, dft, solids):
    assert v3f.calculate_wft(dft, solids) == v2f.calculate_wft(dft, solids)


def test_wft_v3_keeps_full_precision_vs_v2_round3(v2f):
    """80 µm @ 60% SV → 133.3…; v2 rounds to 133.333, v3 keeps full float."""
    v2 = v2f.calculate_wft(80, 60)
    v3 = v3f.calculate_wft(80, 60)
    assert v2 == 133.333
    assert v3 == pytest.approx(80 * 100.0 / 60, rel=0, abs=0)
    assert v3 != v2  # intentional divergence


@pytest.mark.parametrize("losses", [0, 10, 30, 50, 99])
def test_loss_coefficient_matches_v2_on_valid_range(v2f, losses):
    assert v3f.calculate_loss_coefficient(losses) == v2f.calculate_loss_coefficient(losses)


@pytest.mark.parametrize("bad", [-1, 100, 150])
def test_loss_coefficient_v3_rejects_invalid_where_v2_returned_one(v2f, bad):
    assert v2f.calculate_loss_coefficient(bad) == 1.0
    with pytest.raises(ValueError):
        v3f.calculate_loss_coefficient(bad)


def test_theoretical_and_practical_coverage_algebra(v2f):
    # Exact binary-friendly inputs → same results
    assert v3f.calculate_theoretical_coverage(200.0) == v2f.calculate_theoretical_coverage(200.0)
    assert v3f.calculate_practical_coverage(10.0, 1.0) == v2f.calculate_practical_coverage(10.0, 1.0)
    # Intermediate rounding in v2 only
    v2 = v2f.calculate_practical_coverage(5.0, 1.3)
    v3 = v3f.calculate_practical_coverage(5.0, 1.3)
    assert v2 == 3.846
    assert v3 == pytest.approx(5.0 / 1.3, rel=0, abs=0)


def test_consumption_l_matches_v2(v2f):
    for cov in (5.0, 10.0, 4.0, 0.0):
        assert v3f.calculate_consumption_l(cov) == v2f.calculate_consumption_l(cov)


def test_consumption_kg_no_intermediate_round(v2f):
    # 0.25 * 1.35 = 0.3375 exact; v2 round3 → 0.338
    assert v2f.calculate_consumption_kg(0.25, 1.35) == 0.338
    assert v3f.calculate_consumption_kg(0.25, 1.35) == pytest.approx(0.3375, rel=0, abs=0)


def test_chain_identity_matches_system_precision_invariant():
    """Independent chain without intermediate rounding (v3 invariant)."""
    dft, sv, losses, density = 83.5, 61.7, 3.75, 1.31
    wft = v3f.calculate_wft(dft, sv)
    theor = v3f.calculate_theoretical_coverage(wft)
    k = v3f.calculate_loss_coefficient(losses)
    pract = v3f.calculate_practical_coverage(theor, k)
    cons_l = v3f.calculate_consumption_l(pract)
    cons_kg = v3f.calculate_consumption_kg(cons_l, density)
    # Independent algebra
    base_l = (dft * 100.0 / sv) / 1000.0
    practical_l = base_l * 100.0 / (100.0 - losses)
    practical_kg = practical_l * density
    assert cons_l == pytest.approx(practical_l, rel=1e-13, abs=1e-14)
    assert cons_kg == pytest.approx(practical_kg, rel=1e-13, abs=1e-14)
