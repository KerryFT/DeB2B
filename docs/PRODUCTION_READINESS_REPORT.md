# Production readiness report

> **Portfolio addendum — 2026-08-25:** The full production verdict below remains `NO-GO`.
> A separately constrained release at `app.deb2b.id.vn` is now live with `CONDITIONAL GO` after
> Vercel/Render/DNS/TLS and OAuth-redirect verification. Its closed scope and P1 dispositions are documented in
> `PORTFOLIO_DEPLOYMENT.md`. This is not a reclassification of the full product as production-ready.

**Audit date:** 2026-08-24 (Asia/Bangkok)
**Repository release:** `44be1be` for the live constrained portfolio; full production remains blocked
**Target:** `https://deb2b.id.vn`
**Verdict before remediation:** **NO-GO**
**Verdict after remediation:** **NO-GO for public production; internal staging only after OIDC is configured**

No full production deployment or apex DNS change was made. The constrained portfolio uses only
`app` and `api` subdomains. A successful portfolio deployment does not close the full-production P1 findings below.

## Evidence summary

| Gate | Result |
|---|---|
| Repository | MVP, V1 and V2 source, migrations and synthetic tests are present |
| Git safety | Existing untracked `docs/production-readiness-deployment.md` preserved |
| Python quality | Ruff clean; strict mypy clean (73 source files) |
| Python tests | 105 passed; one upstream Starlette/httpx deprecation warning |
| Frontend | ESLint, TypeScript, Vitest 1/1 and Next.js production build passed; 18 routes |
| Containers | API, web and Temporal workflow-worker images built locally; Docker Scout found 0 critical vulnerabilities in all three |
| Database | Local PostgreSQL migrated to head; empty upgrade/downgrade/upgrade and logical restore passed (`1,a42d7c91e6b3`) |
| Cloud tooling | Railway CLI authenticated, but no project is linked; project creation requires a cost/scope choice |
| IaC | Railway TypeScript intent prepared; plan validation deferred because it requires selecting/creating a project |
| DNS/live host | Apex currently resolves to three A + one AAAA and serves an existing WordPress site over TLS; `www`/`api` do not resolve |
| Live verification | Not performed: no safe release candidate, production OIDC, project, DNS or vendor credentials |

## Feature status

`Tested` below means synthetic/fake evidence unless explicitly marked live.

| Capability | Implemented | Tested | Live | Release status |
|---|---:|---:|---:|---|
| CSV/XLSX invoice import | Yes | Yes | No | code-complete |
| Upload, signature policy, evidence | Partial | Yes | No | production storage/scanner wired; OCR queue missing |
| Five blocker matching engine | Yes | Yes | No | synthetic accuracy only |
| PaymentCase state machine | Yes | Yes | No | domain tested |
| Temporal durable workflow | Partial | time-skipping test | No | timer shell; not connected to API/outbox activities |
| Approval and draft guardrails | Yes | fake contract | No | Gmail create-draft only; no live OAuth |
| Gmail ingestion | Partial | fake | No | sandbox/live unverified |
| MISA | Read-only adapter | fake | No | disabled until contract/credentials |
| Outlook delta/draft | Adapter present | fake | No | notification webhook intentionally disabled |
| Zalo | Preview/dry-run | fake | No | real send disabled |
| Bank reconciliation | Yes | unit/integration | No | financial invariants tested synthetically |
| Customer rules | Yes | Yes | No | maker-checker tested |
| Bulk approval | Yes | Yes | No | stale/idempotency paths tested |
| RBAC/RLS | Yes | negative tests | No | broad live IDOR suite still required |
| OpenAI/Gemini/Anthropic | Adapters | fake contracts | No | provider regression is not a live provider test |
| V1 aging forecast | Yes | synthetic backtest | No | business accuracy unverified |
| V2 probability/cash flow | Yes | synthetic baseline | No | pipeline verified; calibration on tenant data required |
| Dispute/profile/benchmark | Yes | synthetic | No | provenance/uncertainty present; business validity unverified |
| Auto-send | Safety decision path | safety tests | No | global kill ON; external delivery OFF |
| Web UI | Demo-oriented | build + 1 test | No | production interactive login absent |

## Findings

| ID | Sev | Status | Evidence and impact | Remediation / next gate |
|---|---|---|---|---|
| PR-001 | P0 | Fixed | `tenant_session` used the database owner rather than `ar_app`; application audit UPDATE/DELETE revocation was bypassable | Session now uses `SET LOCAL ROLE ar_app`; auth uses tenant context; regression added |
| PR-002 | P1 | Open | Browser code has no production OIDC authorization-code/PKCE or secure server session; removing demo headers leaves 401 responses | Select OIDC provider, implement login/callback/logout/session and test revocation/CSRF |
| PR-003 | P1 | Fixed | API always used `MemoryObjectStorage` and `FakeMalwareScanner` | Production builds S3 + ClamAV dependencies and fails fast if absent |
| PR-004 | P1 | Open | `PaymentCaseWorkflow` is a timer/state shell; API/outbox does not start/signal it and no activity/replay version contract exists | Integrate durable start/signal, versioning, stuck detection and recovery |
| PR-005 | P1 | Open | OCR module is a CLI, not a durable queue consumer; document status/progress/retry is absent | Implement document job worker, quarantine state, bounded retry and manual-review DLQ |
| PR-006 | P1 | Mitigated/disabled | Outlook webhook accepted arbitrary notifications with 202 but persisted nothing | Now returns 503 except validation handshake; add client-state/signature, timestamp, dedup and durable inbox before enable |
| PR-007 | P1 | Open | No deployed DB/bucket backup, PITR or restore exercise for the target | Enable daily/weekly backups + PITR, then restore into sibling and record RPO/RTO |
| PR-008 | P1 | Open | No production dashboards/alerts/error tracking; metrics existed publicly | Metrics now require bearer secret; deploy alert rules and verify redaction/event delivery |
| PR-009 | P1 | Open | Foreign keys are mostly single-column IDs rather than `(tenant_id,id)` composite ownership constraints | Add composite ownership constraints incrementally and negative tests for every relationship/export |
| PR-010 | P1 | Open/external | Railway has no linked project; provisioning would select/create billable resources | User must select an existing project or approve a new Pro/pilot project and budget |
| PR-011 | P1 | Open/external | Apex is already serving WordPress (HTTP 301→HTTPS, HTTPS 200) with HSTS `includeSubDomains`; replacing it would affect an existing service. `www`/`api` do not resolve and no DNS credential was available | User must explicitly choose whether to replace WordPress or preserve it and use a subdomain; snapshot records first and never change nameservers |
| PR-012 | P2 | Open | No distributed rate limiter/WAF rules for auth/upload/AI/webhooks | Add edge rules or Redis-backed limits before public exposure |
| PR-013 | P2 | Partial | Upload byte/signature/XLSX active-content checks exist, but PDF pages, archive expansion ratio and async quarantine lifecycle are incomplete | Enforce parser budgets and quarantine workflow before document pilot |
| PR-014 | P2 | Open | Sync SQLAlchemy work runs inside async endpoints; pool/timeouts are defaults | Bound pool/statement timeouts and move blocking work off the event loop |
| PR-015 | P2 | Open | Tests cover fake providers, not Gmail/Outlook/MISA/Zalo/LLM sandbox lifecycle | Execute the sandbox matrix in `DEPLOYMENT.md` |
| PR-016 | P2 | Open | UI has only one Vitest test and several pages expose raw JSON/demo flows | Add authenticated E2E critical path and production UX/error-state coverage |
| PR-017 | P1 | Fixed | Alembic ignored runtime `DATABASE_URL` and would use `alembic.ini` localhost during cloud pre-deploy | Migration env now reads validated settings; isolated migration drill added |
| PR-018 | P2 | Open | Downgrading tenant-scoped draft idempotency after duplicate keys exist across tenants cannot recreate the former global unique constraint | Roll forward in production; only test downgrade on an empty DB; restore backup for data-bearing rollback |

## Remediation delivered

- Strict production environment validation: HTTPS origins, non-local PostgreSQL, OIDC JWKS,
  object storage, ClamAV, metrics secret, non-fake LLM route, safe automation flags.
- Railway `postgres://` URLs normalize to the explicit Psycopg 3 SQLAlchemy driver.
- Least-privilege application DB role and tenant context are now used for normal requests and OIDC membership.
- Production S3 storage supports explicit SSE when the provider supports it; provider at-rest
  encryption must be verified. ClamAV INSTREAM is fail-closed.
- Upload reads are bounded; API and web security headers were added; production metrics are hidden without a secret.
- Demo tenant/user identifiers are environment-gated instead of embedded in frontend source.
- Outlook notifications are disabled rather than falsely acknowledged.
- Reproducible API/web/workflow worker containers, Railway IaC skeleton and stronger CI gates were added.
- Alembic now respects the validated runtime database URL; an isolated PostgreSQL logical restore
  and empty-schema migration round-trip completed successfully.

## Release decision

The application is suitable for continued local validation and, after configuring a real OIDC
provider, a private internal staging deployment with all external sends disabled. It is not ready
for a public pilot or the canonical domain. The next decision point is selecting the production
OIDC provider and an existing Railway project/budget; neither can be safely inferred.
