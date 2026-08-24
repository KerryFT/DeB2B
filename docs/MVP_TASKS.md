# MVP Tasks

All tasks start `pending`. Commands are planned, not executed. Dependencies use task IDs; acceptance is the minimum close condition.

## P0 — Foundation

| Status | ID | Task / target paths | Depends | Acceptance |
|---|---|---|---|---|
| completed | P0-T01 | Workspace manifests, tool versions, Make targets; root, `apps/`, `services/`, `backend/` | approval | Clean `make bootstrap`; locked Node/Python deps |
| completed | P0-T02 | Architecture contracts/value objects; `backend/domain`, `packages/contracts` | T01 | Money/date/tenant/idempotency unit tests pass |
| completed | P0-T03 | PostgreSQL/Alembic tenant schema + forced RLS; `migrations/` | T02 | API role cross-tenant read/write denied |
| completed | P0-T04 | Audit/outbox/idempotency primitives | T03 | Atomic mutation+event; duplicate command returns original |
| completed | P0-T05 | Auth OIDC verifier, membership/RBAC, dev-only issuer | T03 | forged tenant/role and disabled dev auth rejected |
| completed | P0-T06 | Storage/Gmail/LLM ports and deterministic fakes | T02 | Shared offline contract tests pass |
| completed | P0-T07 | Temporal worker skeleton, replay/time-skip test | T02,T04 | Workflow survives worker restart/replay |
| completed | P0-T08 | Compose/CI/telemetry and OCR compatibility spike | T01,T03,T06 | Clean Linux profile healthy; OCR fixture bounded; fallback documented |

Validation: `make lint typecheck test-unit test-contract test-integration test-workflow build`. Failure: keep risky adapter behind feature flag; Python 3.12/OCR-service fallback. Demo: authenticated tenant-scoped health + replay + fake provider.

## P1 — Intake and data

| Status | ID | Task | Depends | Acceptance |
|---|---|---|---|---|
| completed | P1-T01 | Seeded generator + manifest + CI smoke corpus | P0-T01 | Same seed produces same checksums; no real PII |
| completed | P1-T02 | CSV/XLSX mapping/preview/validation staging | P0-T03 | Malformed rows isolated with field errors |
| completed | P1-T03 | Customer/Invoice/PaymentCase transactional upsert | T02,P0-T04 | Reimport produces no duplicates; money exact |
| completed | P1-T04 | Quarantine upload, signature/MIME/size/malware checks | P0-T06 | Disguised/oversize/macro/archive rejected |
| completed | P1-T05 | Immutable document version/hash/object metadata | T04,P0-T03 | Same tenant+hash reuses object; provenance retained |
| completed | P1-T06 | Import/upload UI and basic case list/detail | T03,T05,P0-T05 | Loading/empty/error/success E2E passes |

Validation: unit/import integration/RLS/file-security/Playwright smoke. Failure: reject batch or bad rows without partial hidden mutation. Demo: import 100 invoices and upload a safe document.

## P2 — Early vertical slice

| Status | ID | Task | Depends | Acceptance |
|---|---|---|---|---|
| completed | P2-T01 | Gmail fixture connector and normalized communication/attachment | P0-T06,P1-T05 | Replay fixture idempotent by message/attachment ID/hash |
| completed | P2-T02 | Native extraction + minimal EvidenceSpan for invoice/acceptance | P1-T05 | Critical fields link to page/cell evidence |
| completed | P2-T03 | Deterministic match + missing-document blocker + next task | P1-T03,T02 | Explained blocker reproducible; ambiguity reviews |
| completed | P2-T04 | PaymentCase Temporal workflow/signals/timer | P0-T07,T03 | Restart/time-skip retains state and task |
| completed | P2-T05 | Review + approval aggregate and guardrail | T03,P0-T04 | Edit invalidates approval; unauthorized approval rejected |
| completed | P2-T06 | Fake Gmail draft effect + idempotent outbox | T05,P0-T06 | Repeated activity creates exactly one draft |
| completed | P2-T07 | Case timeline/evidence/approval UI | T02,T05,T06 | Reviewer can trace evidence and approve end-to-end |

Validation: `make demo-smoke` plus workflow/E2E/idempotency/security. Failure: fake connectors/manual review. Demo is the required early vertical slice.

## P3 — Documents, providers, blockers

| Status | ID | Task | Depends | Acceptance |
|---|---|---|---|---|
| completed | P3-T01 | Page profiling/preprocess/native/Docling routing/cache | P2-T02 | Text PDFs avoid OCR; versioned reprocess works |
| completed | P3-T02 | PaddleOCR PP-StructureV3 worker and resource limits | T01,P0-T08 | Vietnamese degraded fixtures produce polygons; bomb times out |
| completed | P3-T03 | Canonical schemas for five document families | T01,T02 | Schema/semantic validators and evidence rules pass |
| completed | P3-T04 | OpenAI/Gemini/Anthropic adapters + portable schema compiler | P0-T06,T03 | All shared offline contracts; optional live smoke manual |
| completed | P3-T05 | Router, bounded repair/fallback, privacy/cost/audit | T04,P0-T04 | No forbidden fallback/infinite loop; lineage complete |
| completed | P3-T06 | Full deterministic matching features + calibration output | T03,P1-T01 | Precision/recall/reliability plot; thresholds config |
| completed | P3-T07 | Five blocker engine + multiple blockers/abstention | T03,T05,T06 | Held-out macro-F1 reported; unsupported goes review |
| completed | P3-T08 | Evidence viewer and manual extraction/link correction | T03,T07 | PDF polygon/XLSX cell and audit correction E2E |

Validation: full document eval, adapter contract, prompt-injection, evidence faithfulness, UI E2E. Failure: per-type/provider manual-review route. Demo: varied scans and all blockers.

## P4 — Gmail and communication lifecycle

| Status | ID | Task | Depends | Acceptance |
|---|---|---|---|---|
| completed | P4-T01 | Gmail OAuth encrypted credential + least scopes | P0-T05 | revoke/refresh/auth-required flows tested |
| completed | P4-T02 | Label initial pagination/full sync and incremental history cursor | T01,P2-T01 | cursor commit ordering; 404 performs safe full sync |
| completed | P4-T03 | Watch renewal/PubSub handler/reconciliation poll | T02 | duplicate/dropped/out-of-order notifications converge |
| completed | P4-T04 | Email summary/dispute/PTP extraction with evidence | P3-T05 | held-out metrics + ambiguity review |
| completed | P4-T05 | Promise/due timers, workflow update/version/replay | T04,P2-T04 | restart and promise-broken time-skip pass |
| completed | P4-T06 | Follow-up proposal/versioned approval | T04,P2-T05 | blocker-specific supported claims only |
| completed | P4-T07 | Gmail draft create-only adapter + final guardrail | T06,T02 | wrong recipient=0, duplicate=0, no send method |
| completed | P4-T08 | Connector/settings/approval UI health states | T03,T07 | expired auth/stale sync/retry states usable |

Failure: switch off push to scheduled sync; revoke/disable connector; sandbox/fake draft remains. Demo: labeled real sandbox thread to approved Gmail draft.

## P5 — Reconciliation and operations UI

| Status | ID | Task | Depends | Acceptance |
|---|---|---|---|---|
| completed | P5-T01 | Bank CSV mapping/staging/dedupe | P1-T02 | malformed/duplicate transactions isolated |
| completed | P5-T02 | Candidate matcher for exact/fuzzy/split/combined payments | T01,P3-T06 | explained candidates; ambiguous never auto-PAID |
| completed | P5-T03 | Allocation review + financial invariants/state transition | T02,P2-T04 | false PAID impossible; concurrent confirmation safe |
| completed | P5-T04 | Dashboard aggregates and case queue filters | T03 | totals reconcile to DB fixtures; stale indicator |
| completed | P5-T05 | Reconciliation/settings UI and accessible responsive states | T03,T04 | Playwright/a11y smoke passes |

Failure: all candidates manual; proposals can be rejected without altering source. Demo: exact, split and ambiguous transactions.

## P6 — Hardening/release

| Status | ID | Task | Depends | Acceptance |
|---|---|---|---|---|
| completed | P6-T01 | Full dataset generation/validation/versioned gold review | P1-T01,P3 | counts/checksums/splits/provenance valid |
| completed | P6-T02 | Cross-provider regression report and calibrated gates | T01,P3-T05 | quality/latency/cost matrix; route decision recorded |
| completed | P6-T03 | Tenant/upload/prompt-injection/recipient security suite | P4,P5 | all zero-tolerance gates pass |
| completed | P6-T04 | 5k/month load profile, failure queue and recovery | P4,P5 | agreed SLO or capacity/fallback documented |
| completed | P6-T05 | Backup/PITR restore, export/delete, retention drill | P0-T03 | isolated restore verified; objects and rows accounted |
| completed | P6-T06 | Metrics/alerts/dashboards/runbooks | T04,T05 | injected connector/provider/workflow failures actionable |
| completed | P6-T07 | Staging deployment/SBOM/vulnerability scan | T03-T06 | pinned artifacts, no critical unresolved vulnerability |
| completed | P6-T08 | Demo rehearsal and release checklist | all | fresh environment end-to-end; hard gates green |

Failure/rollback: do not release; disable risky route, raise abstention/manual review, deploy prior replay-compatible images or compatible fix forward. Deliverable: staging MVP and reproducible offline demo.
