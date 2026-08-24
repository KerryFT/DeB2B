# MVP release checklist

- [x] Fresh Compose profile is healthy; database migration reaches head.
- [x] Synthetic full dataset manifest, checksums, splits and blocker report validate.
- [x] Python lint, strict typing, unit, contract, integration, workflow and security suites pass.
- [x] Web lint, TypeScript, unit smoke and production build pass.
- [x] OCR degraded Vietnamese fixture returns text, confidence and polygon within 4 GB/2 CPU.
- [x] Import/reimport, evidence correction, approval, draft idempotency and reconciliation demo pass.
- [x] Cross-tenant access, unsafe uploads, forbidden LLM fallback and wrong recipients remain zero.
- [x] Backup restores into an isolated database and object/hash inventory reconciles.
- [x] SBOM generated for API, Web and OCR worker; all critical-vulnerability scans report zero.
- [x] Metrics, alerts, failure recovery, incident and rollback runbooks reviewed.

Verified locally on 2026-08-24. Alembic head: `b81f43e9f755`. Compose endpoints: Web `3000`, API `8000`, Temporal UI `8233`, MinIO `9000/9001`, PostgreSQL `55432`.
