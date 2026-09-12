# Legacy parity matrix — v2 → v3

This matrix defines what must be compared before declaring legacy parity. It intentionally records verification status separately from implementation status.

| Area | Legacy v2 baseline | v3 target | Verification |
|---|---|---|---|
| Calculation formulas | `v2/app/domain/calculator.py`, `formulas.py` | `upload/app/domain/calculator.py`, `formulas.py` | VERIFIED — algebraic identity; intentional: v3 no intermediate round3; invalid losses → ValueError (v2 returned 1.0). Evidence: `upload/tests/test_legacy_formula_parity.py` |
| Multilayer calculation | v2 calculation flow | `SystemCalculationResult` / system calculator | VERIFIED — sum-of-layers aggregation; binary-friendly inputs match v2 numerically; invalid losses → validation error. Evidence: `upload/tests/test_legacy_multilayer_parity.py` |
| Two-component materials | v2 material/calculation behavior | v3 2K domain/service | VERIFIED — N/A in v2 (no 2K module); v3 informational-only + single mixed layer calc. Evidence: `upload/tests/test_legacy_two_component_parity.py` |
| Material persistence | v2 repository/SQLite | v3 repositories + migrations | VERIFIED — shared MaterialRepository CRUD; None density/price preserved; SV persisted; soft delete. Evidence: `upload/tests/test_legacy_persistence_parity.py` |
| History | v2 history service/view | immutable snapshots + integrity | VERIFIED — v3 seals SHA-256 snapshots; tamper rejected; v2 had no seal. Evidence: `upload/tests/test_legacy_history_parity.py` |
| Recommendations | v2 recommendation engine | v3 recommendation engine + engineering limitations | VERIFIED — shared hard-filter→score; ScoreBreakdown retained; no hidden weights; unknown cost safe. Evidence: `upload/tests/test_legacy_recommendations_parity.py` |
| Excel export | v2 exporter | v3 engineering/customer exporters | VERIFIED — from SystemCalculationResult; missing price → «—»; engineering/customer split intentional. Evidence: `upload/tests/test_legacy_export_parity.py` |
| PDF export | v2 exporter | v3 exporter from calculation result | VERIFIED — shared export_calculation(SystemCalculationResult); None cost → «—». Evidence: `upload/tests/test_legacy_export_parity.py` |
| UI calculation workflow | v2 calculation view | v3 calculation view | VERIFIED — shared workflow surface; v3 area UNKNOWN→None; export from last SystemCalculationResult. Qt E2E remains §20. Evidence: `upload/tests/test_legacy_ui_workflow_parity.py` + `test_calculation_view_smoke.py` |
| Systems editor | legacy behavior | v3 systems view | VERIFIED — N/A in v2 (no systems_view); v3 CRUD + compatibility + from-calculation. Qt E2E remains §20. Evidence: `upload/tests/test_legacy_ui_workflow_parity.py` + `test_systems_view.py` |
| Comparison | legacy comparison | v3 comparison engine/view | VERIFIED — extrema (DFT/layers/cost among known) match; intentional: no best_balance score; None costs excluded. Evidence: `upload/tests/test_legacy_comparison_parity.py` |
| Unknown inputs | legacy fallback behavior | explicit UNKNOWN semantics | VERIFIED — missing price → None (v2→0.0); invalid density/SV → ValueError; losses None → DEFAULT provenance. Evidence: `upload/tests/test_legacy_unknown_inputs_parity.py` |

## Rule

A row is not `PASS` merely because the v3 implementation exists. It requires a reproducible comparison against the legacy behavior or an explicit documented reason why parity is not applicable.

## Evidence notes

### UI calculation workflow (2026-09-12)
- Shared CalculationView surface: set_materials, add/remove/clear layer, _build_object_data, _on_calculate.
- v3: `_area_unknown` → `area_m2=None` (UNKNOWN ≠ 0); restore_snapshot; load saved system.
- v3 exports Excel/PDF from `_last_result` (CalculationService), not a second engine.
- Headless Qt smoke exists (`test_calculation_view_smoke.py`); sandbox may lack PySide6.
- Regression: `upload/tests/test_legacy_ui_workflow_parity.py`.

### Systems editor (2026-09-12)
- v2 has no `systems_view.py` (N/A).
- v3 SystemsView: new/save/delete system, add/delete/move layer, compatibility refresh, copy from calculation.
- Headless Qt smoke exists (`test_systems_view.py`).
- Regression: `upload/tests/test_legacy_ui_workflow_parity.py`.
