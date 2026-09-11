# Release acceptance checklist — v3.0 engineering upgrade

This is an acceptance checklist, not a claim that the release is accepted.

## Required before release

- [ ] Full local regression suite passes on the release candidate.
- [ ] UI smoke covers calculation, systems, comparison, recommendations, history, engineering KB and inspection.
- [ ] Compatibility UI verified for ALLOWED, WARNING, UNKNOWN and source-backed FORBIDDEN.
- [ ] Inspection workflow verified with an observation, measurement, defect and UNKNOWN acceptance state.
- [ ] Engineering context and surface condition survive save/restore.
- [ ] Material snapshot integrity and legacy snapshot restore verified.
- [ ] SQLite backup/restore verified on a copy of the production-like database.
- [ ] Alembic migration path verified without destructive downgrade assumptions.
- [ ] Excel/PDF outputs checked against the same calculation result.
- [ ] Missing commercial price remains explicitly unknown rather than silently zero.
- [ ] No unverified PDF extraction is promoted to a normative rule.
- [ ] No GitHub Actions run is required for this acceptance record; local evidence must be recorded here.

## Evidence log

Record command, date, result and relevant commit SHA for every completed item.

| Check | Evidence | Status |
|---|---|---|
| Regression | — | PENDING |
| UI smoke | — | PENDING |
| Compatibility | — | PENDING |
| Inspection | — | PENDING |
| Persistence | — | PENDING |
| DB backup/restore | — | PENDING |
| Excel/PDF consistency | — | PENDING |
| Documentation | — | PENDING |
