# V1 implementation tasks

Status is based on the repository validation commands, not on live vendor credentials.

| ID | Dependency | Status | Acceptance evidence |
|---|---|---|---|
| V1-00 | MVP | completed | repo/docs audit, baseline, official integration research, migration note |
| V1-08 | V1-00 | completed | centralized deny-by-default permission matrix, server dependencies, RLS migration, negative tests |
| V1-05 | V1-08 | completed | schema-validated rule DSL, precedence, conflict detection, simulation, maker-checker publish |
| V1-04 | V1-05 | completed | split/aggregate/partial allocation invariants, fee/tolerance/FX review, reversal path and tests |
| V1-02 | V1-08 | completed | Graph delta port/adapter, webhook validation/dedup/renewal helpers, create-only draft and fake contract tests |
| V1-01 | V1-08 | completed | read-only configured MISA port/adapter, cursor/pages/backoff/dedupe and fake replay tests |
| V1-03 | V1-08 | completed | versioned template/recipient policy, quiet hours/consent/suppression, dry-run preview and negative tests |
| V1-06 | V1-03 | completed | bounded homogeneous preview, version/permission/policy/risk revalidation and per-item schema |
| V1-09 | V1-08 | completed | effective-dated pricing, missing usage, online/offline split, redacted RBAC API/UI and tests |
| V1-07 | V1-05 | completed | deterministic baseline, promise/history handling, intervals, buckets, backtest metrics and UI |
| V1-10 | all | completed | 72 Python + 1 frontend test, lint/type/build, live Postgres migration round-trip, integration/E2E green |

Live vendor sandbox smoke tests remain opt-in and do not block offline automated validation.
