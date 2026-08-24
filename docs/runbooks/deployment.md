# Staging deployment and rollback

Use locked Python/Node dependencies and pinned container tags. Apply Alembic migrations before API
traffic, run `/live`, `/ready`, Temporal, MinIO and ClamAV probes, then execute `make demo-smoke`.
Generate an SBOM for API, web and OCR images and retain the vulnerability report. Critical findings
block release unless the artifact is unreachable and an expiry-dated exception is approved.

Rollback application images first; database migrations are backward compatible within one release.
For a migration rollback, stop writers, take a backup, run the tested Alembic downgrade, then restore
traffic. OCR failure routes documents to manual review and does not require API rollback.
