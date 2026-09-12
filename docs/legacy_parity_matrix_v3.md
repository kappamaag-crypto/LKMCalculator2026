# Legacy parity matrix — v2 → v3

This matrix defines what must be compared before declaring legacy parity. It intentionally records verification status separately from implementation status.

| Area | Legacy v2 baseline | v3 target | Verification |
|---|---|---|---|
| Calculation formulas | `v2/app/domain/calculator.py`, `formulas.py` | `upload/app/domain/calculator.py`, `formulas.py` | VERIFIED — algebraic identity; intentional: v3 no intermediate round3; invalid losses → ValueError (v2 returned 1.0). Evidence: `upload/tests/test_legacy_formula_parity.py` |
| Multilayer calculation | v2 calculation flow | `SystemCalculationResult` / system calculator | VERIFIED — sum-of-layers aggregation; binary-friendly inputs match v2 numerically; invalid losses → validation error. Evidence: `upload/tests/test_legacy_multilayer_parity.py` |
| Two-component materials | v2 material/calculation behavior | v3 2K domain/service | PENDING |
| Material persistence | v2 repository/SQLite | v3 repositories + migrations | PENDING |
| History | v2 history service/view | immutable snapshots + integrity | PENDING |
| Recommendations | v2 recommendation engine | v3 recommendation engine + engineering limitations | PENDING |
| Excel export | v2 exporter | v3 engineering/customer exporters | PENDING |
| PDF export | v2 exporter | v3 exporter from calculation result | PENDING |
| UI calculation workflow | v2 calculation view | v3 calculation view | PENDING |
| Systems editor | legacy behavior | v3 systems view | PENDING |
| Comparison | legacy comparison | v3 comparison engine/view | PENDING |
| Unknown inputs | legacy fallback behavior | explicit UNKNOWN semantics | PENDING |

## Rule

A row is not `PASS` merely because the v3 implementation exists. It requires a reproducible comparison against the legacy behavior or an explicit documented reason why parity is not applicable.

## Evidence notes

### Calculation formulas (2026-09-12)
- Core identities (WFT, loss coefficient on valid range, consumption_l, exact binary-friendly cases) match v2 numerically.
- v2 applied intermediate `round3` on WFT / theoretical coverage / practical coverage / consumption_kg; v3 keeps full float precision (no intermediate rounding invariant, aligned with §7).
- Invalid `losses_percent` (<0 or ≥100): v2 returned `1.0`; v3 raises `ValueError` (stricter validation, not silent fallback).
- Regression: `upload/tests/test_legacy_formula_parity.py` (19 cases).

### Multilayer calculation (2026-09-12)
- System totals = sum of per-layer per-m² results; `total_cost` scales by area.
- Binary-friendly inputs (SV=50, dens=1, losses=0) match v2 totals exactly for DFT / L / kg / cost_per_m².
- v3 multilayer totals match independent no-intermediate-rounding algebra (aligned with §7).
- Invalid losses_percent (≥100): v3 returns validation error `LAYER_LOSSES_INVALID` (no silent K=1 fallback).
- Regression: `upload/tests/test_legacy_multilayer_parity.py` (3 cases).
