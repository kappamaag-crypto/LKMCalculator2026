# Release acceptance checklist — v3.0 engineering upgrade

This is an acceptance checklist, not a claim that the release is accepted.

HEAD at evidence capture: `f1a382b` (branch `v3.0-engineering-upgrade`).  
Evidence date: 2026-09-13 (local sandbox, no GitHub Actions).

## Required before release

- [x] Core domain/service regression subset passes (see Evidence log).
- [ ] Full local regression suite on the release candidate (full tree, all deps).
- [ ] UI smoke covers calculation, systems, comparison, recommendations, history, engineering KB and inspection (needs PySide6).
- [x] Compatibility engine source-backed matrix covered by `test_layer_compatibility.py`.
- [ ] Inspection UI workflow E2E (observation/measurement/defect) — domain tests exist; UI E2E pending.
- [x] Material snapshot integrity and restore verified (`test_snapshot_integrity.py`, `test_snapshot_restore.py`).
- [x] SQLite backup/restore + Alembic head verified (`test_database_safety.py`).
- [x] Excel/PDF export parity / unknown cost (`test_legacy_export_parity.py`).
- [x] Missing commercial price remains None, not zero (`test_legacy_unknown_inputs_parity.py`).
- [x] No invented dew-margin (`test_pre_application.py`).
- [x] Durable notification outbox without SMTP secrets in DB (`test_notification_outbox.py`).
- [x] PackagingPlanner without warehouse (`test_packaging.py`).
- [ ] No unverified PDF extraction promoted to normative rule (process gate; SPKEFFA read-only).
- [x] No GitHub Actions required for this acceptance record.

## Evidence log

| Check | Evidence | Status |
|---|---|---|
| Core regression subset | `PYTHONPATH=. python -m pytest` on: `test_database_safety`, `test_snapshot_integrity`, `test_snapshot_restore`, `test_notification_outbox`, `test_packaging`, `test_pre_application`, `test_legacy_formula_parity`, `test_legacy_unknown_inputs_parity`, `test_legacy_export_parity`, `test_chemical_resistance`, `test_layer_compatibility`, `test_legacy_persistence_parity` → **94 passed** (2026-09-13, HEAD base `f1a382b`) | DONE |
| UI smoke | PySide6 not available in sandbox | PENDING |
| Compatibility | `test_layer_compatibility.py` in subset | DONE (engine) |
| Inspection domain | Covered elsewhere; UI E2E PENDING | PARTIAL |
| Persistence / snapshots | integrity + restore + persistence parity in subset | DONE |
| DB backup/restore | `test_database_safety.py` (7) | DONE |
| Excel/PDF consistency | `test_legacy_export_parity.py` | DONE |
| UNKNOWN price ≠ 0 | `test_legacy_unknown_inputs_parity.py` | DONE |
| Pre-application no invented dew | `test_pre_application.py` (8) | DONE |
| Notification outbox | `test_notification_outbox.py` (6) | DONE |
| Documentation / parity matrix | `docs/legacy_parity_matrix_v3.md` all rows VERIFIED | DONE |

## Explicitly still open for full release

1. Full pytest of entire `upload/tests` tree on a clean env.
2. Qt UI smoke / E2E (§2, §20).
3. Live SMTP delivery (optional; outbox logic closed).
4. OGZ §15 (deferred).
5. Material-specific TDS-backed compatibility conditions beyond Table 1 (§22).
