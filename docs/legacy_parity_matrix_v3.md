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
| UI calculation workflow | v2 calculation view | v3 calculation view | PENDING |
| Systems editor | legacy behavior | v3 systems view | PENDING |
| Comparison | legacy comparison | v3 comparison engine/view | VERIFIED — extrema (DFT/layers/cost among known) match; intentional: no best_balance score; None costs excluded. Evidence: `upload/tests/test_legacy_comparison_parity.py` |
| Unknown inputs | legacy fallback behavior | explicit UNKNOWN semantics | VERIFIED — missing price → None (v2→0.0); invalid density/SV → ValueError; losses None → DEFAULT provenance. Evidence: `upload/tests/test_legacy_unknown_inputs_parity.py` |

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

### Unknown inputs (2026-09-12)
- Missing `price_per_kg`: v2 LayerCalculator used `0.0` (appears as free); v3 returns `cost_per_m2=None` / system `total_cost*=None`.
- Invalid density or solids_by_volume (≤0): v3 raises ValueError (no silent zero consumption).
- Unspecified `losses_percent=None`: resolved via LossProfile DEFAULT with `losses_source=DEFAULT` (not an invented engineering margin).
- Regression: `upload/tests/test_legacy_unknown_inputs_parity.py` (6 cases).

### Two-component materials (2026-09-12)
- v2 has no `two_component` domain module and no mix_ratio handling in calculator.
- v3 `TwoComponentService.describe` is informational only (ratio text, pot life, components); no purchase/sets/remainder fields.
- Calculation treats a 2K product as **one** mixed material layer (`is_two_component=True`); components are not separate consumption layers.
- Invalid ratios / ratio_basis raise `TwoComponentCalculationError`.
- Regression: `upload/tests/test_legacy_two_component_parity.py` (5 cases).

### Comparison (2026-09-12)
- Shared: compare 2–N systems; annotate thinnest/thickest/fewest_layers; transparent indicator table.
- DFT / layer-count extrema match v2 on binary-friendly inputs; cheapest among priced systems matches when all prices known.
- Intentional: v3 sets `best_balance_index=None` (no derived price/DFT «smart» score); v2 computed a balance ranking.
- Intentional: v3 cheapest/most_expensive only among systems with non-None `total_cost_per_m2` (UNKNOWN price excluded).
- v3 also enforces max 10 systems and rejects mixed areas in `compare_results`.
- Regression: `upload/tests/test_legacy_comparison_parity.py` (4 cases).

### Recommendations (2026-09-12)
- Shared two-stage architecture: `filter_systems` hard filter → `score_system` ranking; DISCLAIMER on result.
- Wrong corrosion category rejected by hard filter (same intent as v2).
- `RecommendationItem.breakdown` (ScoreBreakdown) retained; total matches score.
- Transparent weights only (corrosion/durability/technology/cost); hidden condition/compatibility weights stay 0 in total.
- Missing price does not invent a free-material cost advantage.
- Regression: `upload/tests/test_legacy_recommendations_parity.py` (7 cases).

### Excel / PDF export (2026-09-12)
- Both v2 and v3 PDF exporters expose `export_calculation(result: SystemCalculationResult, path)` — single calculation source, not a second engine.
- v3 PDF formats unknown costs as «—» via `_cost(None)` (aligned with UNKNOWN semantics).
- v3 Excel missing price produces a file without inventing 0 cost (see also `test_excel_missing_price.py`).
- Intentional: v3 splits engineering vs customer Excel exporters; v2 had a single excel_exporter.
- Regression: `upload/tests/test_legacy_export_parity.py` (5 cases).

### History (2026-09-12)
- v2 `HistoryService` persists calculations without integrity hash / seal helpers.
- v3 `snapshot_utils.seal_snapshot` / `verify_snapshot` / `load_and_verify_snapshot` (SHA-256 over canonical JSON).
- Tampered or unsealed payloads raise ValueError; `snapshot_number(None)` stays None (no invented zero).
- `HistoryService.save_calculation` documents immutable material snapshot capture.
- Regression: `upload/tests/test_legacy_history_parity.py` (6 cases).

### Material persistence (2026-09-12)
- Shared MaterialRepository API: get_by_id / get_by_name / list_all / add / update / delete.
- v3 preserves None for density, solids, price (UNKNOWN ≠ 0) through ORM mapping.
- solids_by_volume_percent persisted (engineering field).
- Soft delete removes material from active_only lists.
- Regression: `upload/tests/test_legacy_persistence_parity.py` (5 cases).
