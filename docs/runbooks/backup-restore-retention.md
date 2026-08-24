# Backup, restore, export, delete, and retention

MVP drill uses `pg_dump --format=custom` against PostgreSQL and restores into an isolated
database before comparing tenant, invoice, audit, and document metadata counts. Never restore
over the active database. MinIO objects are inventoried by tenant prefix and their SHA-256 values
are compared with `documents.sha256`.

Tenant export contains relational JSON plus immutable object hashes. Tenant deletion requires an
admin approval, first marks the tenant `DELETE_PENDING`, exports an audit manifest, deletes object
prefixes, then deletes relational rows in one maintenance transaction. Audit retention is 7 years;
raw uploaded documents default to 2 years unless a legal hold is active. Connector credentials are
deleted immediately on disconnect. The drill must record counts before/after and the restore DB is
removed after verification.
