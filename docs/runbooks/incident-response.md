# Incident and alert response

Alerts: API error rate above 2% for 10 minutes, Gmail cursor stale for 30 minutes, Temporal task
age above 10 minutes, OCR failure above 10%, provider schema failure above 5%, any dead-letter,
and PostgreSQL/MinIO health failure.

First identify tenant/correlation ID without logging document content. Pause the affected connector
or provider route, keep cases in manual review, inspect the failure record, and retry only through
the idempotent operation. Recipient mismatch, RLS failure, or suspected prompt injection is a
security incident: disable the external action path, preserve audit/outbox records, rotate affected
credentials, and notify the tenant owner. Recovery closes only after a synthetic probe succeeds and
backlog age returns below the threshold.
