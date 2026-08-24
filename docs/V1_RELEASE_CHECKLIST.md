# V1 release verification — 2026-08-24

- [x] Python Ruff and strict mypy pass.
- [x] Full Python suite: 72 passed (unit, contract, integration, security, workflow, E2E).
- [x] Frontend ESLint, TypeScript, Vitest (1 passed) and Next production build pass (11 routes).
- [x] Alembic offline forward and rollback SQL render successfully.
- [x] Live PostgreSQL `b81f43e9f755 -> f19c7a4d2e10 -> b81f43e9f755 -> f19c7a4d2e10` succeeds.
- [x] RLS/cross-tenant negative, immutable audit and tenant lifecycle tests pass.
- [x] Fake MISA pagination/throttle/duplicate/replay tests pass.
- [x] Fake Outlook delta/duplicate/draft and webhook lifecycle policy tests pass.
- [x] Fake Zalo consent/template/quiet-hours/approval/idempotency tests pass.
- [x] Advanced reconciliation, rules, bulk selection, forecast/backtest and LLM pricing tests pass.
- [x] Synthetic V2 full dataset regenerated deterministically; manifest validation reports 5 artifacts.
- [x] Default external mode remains dry-run/read-only; no live vendor call was made.

Live MISA, Microsoft Graph and Zalo tenant sandboxes were not tested because no credential was
provided. Follow `V1_OPERATIONS.md`; this is intentionally separate from the offline release gate.
