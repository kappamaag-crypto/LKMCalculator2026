# Legacy parity matrix — v2 → v3

This matrix defines what must be compared before declaring legacy parity. It intentionally records verification status separately from implementation status.

| Area | Legacy v2 baseline | v3 target | Verification |
|---|---|---|---|
| Calculation formulas | `v2/app/domain/calculator.py`, `formulas.py` | `upload/app/domain/calculator.py`, `formulas.py` | PENDING |
| Multilayer calculation | v2 calculation flow | `SystemCalculationResult` / system calculator | PENDING |
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
