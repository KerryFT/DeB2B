# Production release checklist

The full production checklist remains blocked. The constrained portfolio release has a separate
scope and P1 closure matrix in `PORTFOLIO_DEPLOYMENT.md`; do not use its conditional approval for
real customer data, background automation, webhooks, uploads or external sends.

Current gate: **NO-GO**. Checked items have local evidence; unchecked P0/P1 items block public launch.

## Code and data

- [x] Lockfiles present; Ruff and strict mypy pass.
- [x] Frontend lint/type/test/production build pass.
- [x] API and workflow-worker images build.
- [x] Local migration to head and targeted auth/RLS/API regression pass.
- [x] Full Python suite passes on the final worktree: 105 passed.
- [x] Empty DB upgrade/downgrade/upgrade and isolated logical dump/restore pass locally.
- [ ] Composite tenant ownership/IDOR suite covers all raw, derived, file, aggregate and export data.
- [ ] Pilot-scale latency/throughput/DB/worker/OCR resilience measurements recorded.

## Identity and security

- [x] Production rejects dev auth, fake storage/scanner and unsafe automation config.
- [x] Application uses least-privilege `ar_app`; audit privilege regression passes.
- [x] CORS/security headers/metrics protection and bounded upload reads are present.
- [ ] Production OIDC browser login/session/logout/revocation/CSRF is implemented and tested.
- [ ] Rate limits/WAF and trusted proxy behavior are deployed/tested.
- [ ] Upload parser budgets, quarantine lifecycle and malware test event pass.
- [ ] Final dependency/image scan has zero unaccepted critical findings; SBOM retained.
- [ ] Secrets are sealed/managed, rotation tested, and absent from Git/image/client/logs.

## Reliability and operations

- [ ] Temporal API/outbox/activity/replay/version path works end-to-end.
- [ ] OCR durable worker, progress, retry, DLQ/manual review and stuck detection work.
- [ ] PostgreSQL backups/PITR configured; isolated restore drill meets measured RPO/RTO.
- [ ] Object versioning/retention/inventory/restore and orphan cleanup verified.
- [ ] Logs, metrics, traces, dashboards and owner-routed alert test events work.
- [ ] Rollback of previous immutable app artifact has been rehearsed.

## External actions and intelligence

- [x] Global kill ON, external delivery OFF, connector dry-run ON by default.
- [x] Auto-send decision safeguards have synthetic tests; no live send was made.
- [ ] Outlook/Gmail webhooks have verification, replay protection, durable inbox and catch-up.
- [ ] MISA/Outlook/Zalo/LLM status is explicitly recorded as disabled/fake/sandbox/live.
- [ ] Tenant data calibration/backtest approved; UI communicates uncertainty/staleness.

## Infrastructure, domain and launch

- [x] Railway IaC intent and Dockerfiles are prepared; no resource was applied.
- [ ] Existing Railway project selected or new-project budget approved.
- [ ] Owner explicitly decides whether existing apex WordPress is replaced or preserved on another host.
- [ ] Staging plan reviewed; service/storage/Temporal/OIDC secrets configured.
- [ ] Synthetic staging smoke matrix passes with zero real external sends.
- [ ] DNS pre-change snapshot saved; exact Railway routing + TXT records approved/applied.
- [ ] Apex/API TLS, HTTP redirect, canonical `www` redirect, headers and mixed content verified.
- [ ] Production synthetic smoke passes step-by-step; release SHA/time/flags recorded.

The owner must record `GO` only when every P0/P1 checkbox is complete or an explicit, expiry-dated
mitigation is accepted by the accountable owner. This checklist does not authorize purchases,
resource deletion, nameserver changes, customer-data import or real external sends.
