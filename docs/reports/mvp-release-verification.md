# MVP release verification

Verified locally on 2026-08-24 against the synthetic offline/demo profile.

| Gate | Result |
|---|---|
| Database | Alembic `b81f43e9f755 (head)`; PostgreSQL healthy |
| Dataset | Full manifest valid; 4 artifacts; checksums, splits and provenance valid |
| Python quality | Ruff clean; strict mypy clean |
| Python tests | 61 passed: unit 33, contract 7, integration 14, security 3, E2E 1, workflow 3 |
| Web quality | ESLint and strict TypeScript clean; Vitest 1 passed; Next.js production build passed |
| Compose smoke | API `/ready` 200; Web 200; MinIO live probe 200; API and Web healthy |
| OCR | Vietnamese degraded fixture passed in 27.81 seconds under 4 GB memory and 2 CPU |
| Backup/restore | Isolated PostgreSQL restore retained counts `36,54,57,5`; temporary drill assets removed |
| Vulnerabilities | API 0 critical; Web 0 critical; OCR worker 0 critical |

SBOM and critical-scan artifacts are stored beside this report as `ar-api.*`, `ar-web.*`, and `ar-document-worker.*`.

The provider regression is an offline contract run. Live provider and Gmail sandbox smokes remain credential-dependent operational checks, not release blockers for the reproducible offline MVP.
