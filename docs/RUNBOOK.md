# Production runbook

## Ownership and SLO

The production owner is the on-call engineering owner named in the release record; no alert may be
enabled without an owner. Pilot SLO is 99.5% monthly web/API availability, accepted-event recovery,
and zero cross-tenant access, wrong recipient or duplicate external send.

## Triage

1. Assign severity: P0 data/tenant/financial/send/secret; P1 core outage/recovery/auth; P2 degraded;
   P3 improvement.
2. Stop harm before restoring throughput. Enable global kill and connector dry-run for any external
   action anomaly. Do not delete audit/outbox/job evidence.
3. Use correlation ID, tenant-safe IDs, release SHA and deployment ID. Never copy raw sensitive
   payloads into incident chat.
4. Declare rollback if a new release correlates with P0/P1 or readiness failures.

## Immediate automation shutdown

Set `AUTOMATION_GLOBAL_KILL_SWITCH=true` and
`AUTOMATION_EXTERNAL_DELIVERY_ENABLED=false`, redeploy/restart API and workers, then persist each
tenant policy as `mode=disabled, kill_switch=true`. Verify policy API reports all locks. Also keep
`EXTERNAL_CONNECTORS_DRY_RUN=true`; revoke provider send capability if runtime state is uncertain.

## Common incidents

### API unavailable / latency

- Check deployment health, error rate, p95/p99, DB connections/locks and recent migration.
- Shed expensive OCR/AI work; it must not run on the request path.
- If release-related, roll back image. Do not downgrade DB without the recovery procedure.

### Database capacity or corruption

- Stop nonessential workers and writes; snapshot/backup before intervention.
- Prefer PITR/backup restore to a sibling service; source remains untouched.
- Validate Alembic head, tenant/invoice/audit/document counts and selected financial totals.
- Cut over only after two-person review. Target RPO ≤24h/RTO ≤4h until measured better.

Railway restore guidance: https://docs.railway.com/guides/postgres-backups-restores

### Stuck workflow / backlog

- Inspect task queue/backlog, worker deployment, Temporal namespace and workflow history.
- Do not terminate/replay until workflow version compatibility and external idempotency are checked.
- If OCR fails, route documents to manual review; never acknowledge completed extraction.

### Webhook failures

- Keep the endpoint disabled if verification/durable inbox is unavailable.
- Inspect signature/client-state, timestamp, dedup ID and cursor staleness; backfill via provider delta.
- Never treat HTTP receipt alone as successful business processing.

### Wrong recipient / duplicate send

- Activate both kills, revoke send scope/token if necessary, and preserve decision/outbox/provider ID.
- Reconstruct case version, approval, verified recipient, suppression/payment/dispute state and key.
- Notify security/privacy/legal owners according to the approved incident plan. Never replay first.

### Suspected cross-tenant access

- P0: disable affected endpoint/public traffic and preserve logs.
- Identify actor, tenant context, SQL relation/object key/export and time window.
- Run read-only scope queries as a privileged incident role; do not mutate evidence.
- Patch and prove a negative regression across relational/object/derived/export boundaries before reopen.

## Backup and restore exercise

Enable daily (6-day), weekly (1-month) and monthly (3-month) volume backups plus PITR if budget is
approved. Before release, create a logical `pg_dump --format=custom --no-owner`, restore into an
isolated sibling, apply no production traffic, and compare row counts, tenant-filtered financial
totals, audit counts and object SHA-256 inventory. Record dump age and elapsed restore time. Remove
temporary drill resources only with explicit approval because deletion is destructive.

## Secret rotation

1. Create a new credential/version in the provider or managed secret store.
2. Grant least privilege and update the runtime secret reference; do not rebuild frontend.
3. Restart one instance, verify auth/connector health and redaction, then roll the rest.
4. Revoke the old credential only after verification; record owner/time/affected services.
5. For compromise, skip overlap where safe, activate kill switches and treat as P0.

## Monitoring minimum

| Alert | Threshold | Severity | Action |
|---|---|---|---|
| API availability | 5xx/failed probes >2% for 5m | P1 | rollback/scale/DB triage |
| API latency | p95 >1s for 10m | P2 | inspect DB/blocking jobs |
| DB capacity | connections >80% or disk >80% | P1/P2 | shed/scale/back up |
| Worker lag | oldest task >10m | P1 | worker/Temporal triage |
| Webhook failure | verified events failing >1%/5m | P1 | disable/backfill |
| Outbox/DLQ | oldest >10m / any poison loop | P1 | stop retry storm |
| External send anomaly | duplicate/wrong recipient >0 | P0 | kills + incident |
| LLM spend | daily >2× 14-day baseline | P2 | cap/route/disable |
| Backup | missed schedule or PITR unhealthy | P1 | restore coverage triage |

The release is not operational until these alerts are deployed and test events reach the owner.
