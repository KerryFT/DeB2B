# V2 operations runbook

## Immediate automation shutdown

Set `AUTOMATION_GLOBAL_KILL_SWITCH=true` and restart API/workers. In the UI choose **Automation →
Disable + kill switch** to persist the tenant lock. Verify `/api/v2/automation/policy` reports
`mode=disabled`, tenant/global kill true and external delivery false. Do not delete action history.

## Model rollback and stale behavior

Mark the prior model registry record `CHAMPION`, the rejected record `ROLLED_BACK`, then replay the
idempotent derived job for the required `as_of`. If no fresh champion exists, the service falls back
to `segment-beta-baseline-v1`; predictions remain decision support only.

## Rebuild/replay

Create a derived job key from tenant, job type, as-of, feature version and checkpoint. Re-running the
same key must reuse/complete the existing job. Rebuild snapshots from canonical events, never from
later predictions. For late-arriving events, create a new snapshot/run; do not mutate historical
`as_of` output silently.

## Taxonomy/profile correction

Use the dispute correction API with evidence IDs and an authorized actor. Recompute affected
customer profiles and aggregates, keeping the original audit entry. Merge/split corrections must
rebuild all affected entity snapshots.

## Duplicate or wrong-recipient investigation

Activate both kill switches, inspect the decision idempotency key, case version, recipient evidence,
outbox and provider external ID. Never replay until current paid/dispute/recipient state passes
revalidation. Preserve audit/outbox rows for incident analysis.

## Local demo lifecycle

Start dependencies with `docker compose up -d`, migrate with
`.venv/Scripts/alembic.exe upgrade head`, seed using `.venv/Scripts/python.exe tools/seed_demo.py`,
then start API/web via the repository Makefile or package scripts. Stop with `docker compose down`;
volumes are retained unless explicitly removed.
