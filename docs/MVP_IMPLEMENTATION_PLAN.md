# AR Operations Agent — MVP Implementation Plan

Trạng thái: **chờ phê duyệt**  
Ngày chốt nghiên cứu: 2026-08-23  
Nguồn sản phẩm: `../ar-operations-agent-implementation-plan.md` (SHA-256 đã đối chiếu với bản trong `docs/`)  
Tài liệu đi kèm: `MVP_TASKS.md`, `MVP_DATASET_AND_EVAL_PLAN.md`, `MVP_DECISIONS.md`

## 1. Tóm tắt và định nghĩa hoàn thành

MVP là một monorepo evidence-first: PostgreSQL giữ sự thật nghiệp vụ, Temporal giữ vòng đời dài hạn, rule deterministic sở hữu tiền/ngày/trạng thái, document pipeline tạo dữ liệu có `EvidenceSpan`, LLM đa provider chỉ hiểu nội dung mơ hồ và soạn thảo, con người duyệt trước khi tạo Gmail draft. Không có thao tác tự gửi email hay tự sửa dữ liệu tài chính.

MVP hoàn thành khi một máy sạch có thể dùng dữ liệu synthetic để: import CSV/XLSX → tạo Customer/Invoice/PaymentCase → đồng bộ một Gmail label hoặc fixture → ingest attachment/file → trích xuất trường trọng yếu kèm evidence → ghép và phát hiện đủ năm blocker → durable workflow tạo task/review → người dùng duyệt → tạo đúng một Gmail draft sandbox/mock → nhận promise-to-pay → import bank CSV → chỉ chuyển `PAID` khi rule/bằng chứng hợp lệ; đồng thời UI, audit, RLS, test/eval và runbook vượt release gates.

## 2. Scope khóa

**In:** B2B dịch vụ/phân phối, 100–5.000 invoice/tháng, CSV/XLSX AR source, Gmail label + attachment, upload PDF/PNG/JPEG/XLSX, năm nhóm document, năm blocker, one-tenant pilot nhưng mọi tenant row có `tenant_id`, dashboard/queue/detail/evidence/approval, bank CSV reconciliation, synthetic eval.

**Out:** MISA API/write-back, Outlook/Zalo/voice, bank API/scraping, auto-send, thương lượng/discount/sửa invoice, legal, scoring/forecast, multi-agent, fine-tuning, CRM/accounting replacement, V1/V2.

## 3. Assumption và điều chỉnh so với brief

- Brief gốc nói Temporal Cloud; MVP local dùng Temporal development server/container, staging chọn Temporal Cloud để tránh tự vận hành cluster.
- `pgvector` chưa đưa vào baseline. Deterministic/fuzzy matching đủ cho MVP; chỉ thêm qua ADR nếu eval chứng minh retrieval cần thiết.
- Gmail push/Pub/Sub là production path; local/demo có explicit sync/poll. Push không phải nguồn sự thật.
- Tạo draft chỉ sau approval; “Send” trong state machine brief được đổi thành `DRAFT_CREATED`, không có API send.
- Auth dùng OIDC-compatible issuer + RBAC trong DB; local có dev issuer/seed identity bị khóa ngoài development. Gmail OAuth là connector credential riêng.
- Một PaymentCase mặc định gắn một invoice ở vertical slice; schema association cho phép nhiều invoice để hỗ trợ thanh toán gộp/tách.
- Ngưỡng chất lượng brief là target ban đầu, không phải lời hứa. Safety/correctness zero-tolerance là release gate; threshold matching phải calibration.

## 4. Stack và version policy

| Lớp | Baseline khi bắt đầu P0 | Lý do/strategy |
|---|---|---|
| Web | Next.js 16.3.x, React 19.x, TypeScript 5.x; Node 24 LTS; pnpm 10.x | App Router; Node 20 đã EOL. Pin exact trong lockfile, Renovate theo patch/minor có CI. |
| API/worker | Python 3.13.x, FastAPI 0.136.x, Pydantic 2.x, SQLAlchemy 2.x, Alembic 1.x; `uv` 0.12.x | Python 3.13 có ecosystem support; một lockfile exact theo platform Linux. |
| Workflow | Temporal Python SDK 1.31.x; Temporal server image pin digest | Durable timer/retry; replay tests trước upgrade. |
| Data | PostgreSQL 18.x current minor | 5-year support, RLS; luôn lấy current minor/security patch. |
| Storage | S3 port; local MinIO-compatible image pin digest; production GCS via adapter | Hash-addressed object keys; không để business code phụ thuộc vendor. |
| Documents | native parsers first; Docling 2.117.x; PaddleOCR 3.7.x/PP-StructureV3; LibreOffice headless only if fixture conversion requires | Chạy OCR worker riêng; kiểm chứng CPU/RAM, Vietnamese accuracy và transitive licenses ở P0 spike. |
| LLM | OpenAI, Google GenAI, Anthropic official Python SDKs behind ports; versions exact in lock | Model IDs only from env/config; SDK bump qua shared contract/regression tests. |
| Auth/telemetry | OIDC/JWT + DB RBAC; OpenTelemetry + structured JSON logs + Sentry optional | Portable tenant context; no email/document body in logs. |

Version rule: manifest khai báo compatible range có chủ đích, lockfile và image digest quyết định build; patch update hàng tuần, minor hàng tháng, major qua ADR/migration/replay/regression. Không pin model name trong business code.

Nguồn primary (truy cập 2026-08-23):

- Next.js requirements/releases: https://nextjs.org/docs/app/getting-started/installation và https://nextjs.org/blog
- Node lifecycle: https://nodejs.org/en/about/previous-releases
- FastAPI releases: https://github.com/fastapi/fastapi/releases
- PostgreSQL support/RLS: https://www.postgresql.org/support/versioning/ và https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- Temporal SDK: https://github.com/temporalio/sdk-python/releases và https://docs.temporal.io/develop/python
- Docling: https://github.com/docling-project/docling/releases và https://docling-project.github.io/docling/getting_started/installation/
- PaddleOCR: https://github.com/PaddlePaddle/PaddleOCR/releases và https://www.paddleocr.ai/
- Gmail sync/push/draft/scopes: https://developers.google.com/workspace/gmail/api/guides/sync, https://developers.google.com/workspace/gmail/api/guides/push, https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.drafts/create, https://developers.google.com/identity/protocols/oauth2/scopes
- Structured output: https://platform.openai.com/docs/guides/structured-outputs, https://ai.google.dev/gemini-api/docs/structured-output, https://platform.claude.com/docs/en/build-with-claude/structured-outputs

## 5. Architecture và data flow

```text
Next.js ── REST/JSON ── FastAPI ── transaction/RLS ── PostgreSQL
   │                       │  ├── object port ── local S3 / GCS
   │                       │  ├── Gmail OAuth/API
   │                       │  └── Temporal client
   │                       ▼
   └── evidence pages ◄─ OCR/document workers ◄─ Temporal activities
                                     │
                                     └─ LLM gateway ─ OpenAI/Gemini/Anthropic

CSV/XLSX ─┐
Gmail ────┼→ immutable ingestion item → normalized entity → document/evidence
Upload ───┘       → deterministic match → blocker proposal → case workflow
                    → human review/approval → idempotent Gmail draft
Bank CSV → transaction candidates → deterministic review → payment allocation → PAID
```

Boundary: code validates file/import, normalizes identifiers/money/date, scores matches, enforces transitions/recipients/idempotency; Docling/OCR produces layout/text; LLM classifies/extracts ambiguous semantics/summarizes/drafts but returns proposals; Temporal schedules and waits but does not replace DB truth; human resolves ambiguity and authorizes external draft creation.

## 6. Monorepo target

```text
apps/web/                 Next.js screens, BFF client, auth session
services/api/             FastAPI routes, application services, tenant/RBAC
services/worker/          Temporal worker, activities, document/OCR jobs
packages/contracts/       OpenAPI-generated TS client, JSON schemas/event names
packages/ui/              shared accessible UI primitives
backend/domain/           entities, value objects, state machine, rules
backend/application/      commands/queries/ports/use cases
backend/infrastructure/   db, storage, Gmail, auth, LLM adapters, telemetry
backend/workflows/        deterministic workflows; no I/O in workflow code
migrations/               Alembic revisions and RLS policies
config/                   non-secret routing/prompt policy examples
prompts/                  versioned templates + schema references
tests/{unit,contract,integration,workflow,e2e,security,load}/
evals/                    harness, metrics, reports (no paid calls in CI)
data/{fixtures,manifests}/ committed small synthetic set
tools/dataset/            generators/augmenters/validators
deploy/{compose,gcp}/      local compose and deployment definitions
docs/runbooks/             connector, retry/DLQ, backup/restore, deletion
```

Imports enforce domain → no infrastructure dependency; workflow calls application only through activities; provider SDK types never cross adapter boundary.

## 7. Domain/data design

Core tables: `tenants`, `users`, `memberships(role)`, `customers`, `contacts`, `invoices`, `payment_cases`, `case_invoices`, `documents`, `document_versions`, `evidence_spans`, `extracted_fields`, `document_links`, `communications`, `gmail_connections`, `gmail_sync_cursors`, `ingestion_items`, `blockers`, `tasks`, `promise_to_pay`, `approvals`, `draft_actions`, `bank_imports`, `bank_transactions`, `payment_allocations`, `llm_calls`, `domain_events`, `audit_entries`, `outbox_events`.

- UUIDv7/UUID primary keys; all tenant-owned rows `tenant_id NOT NULL`; unique keys include tenant.
- Money is integer minor units + ISO currency; timestamps UTC; source-local date retained separately.
- Important uniqueness: `(tenant_id, source, external_id)`, `(tenant_id, sha256)`, `(tenant_id, invoice_number_normalized, seller_tax_id)`, `draft_actions(idempotency_key)`, outbox event ID.
- Index queue by `(tenant_id,status,next_action_at)`, invoice by tenant/customer/due_date, evidence by document/version/page, Gmail cursor by connection, audit by aggregate/time.
- RLS enabled and forced on tenant tables; request transaction sets verified tenant context; migration/admin role separate and never used by API. App authorization still checks membership/role (viewer, operator, approver, admin).
- `EvidenceSpan`: source hash/version, page or sheet/cell, normalized polygon `[0..1]`, char offsets, quote, parser version. Extracted critical field requires ≥1 evidence or `NEEDS_REVIEW`.
- Audit is append-only application role: actor/type, action, before/after hashes, reason, correlation/causation, approval/LLM references. Payload body stays in object storage; logs/audit keep redacted metadata.
- Default configurable retention: raw email/file 365 days after case close, derived records/audit 7 years for pilot assumption; deletion is tenant-scoped tombstone → workflow cancel → object purge → DB purge/anonymize with deletion audit. Final legal retention needs approval.

## 8. State machine and event catalog

Canonical status: `IMPORTED → COLLECTING_DOCUMENTS | READY_FOR_REVIEW`; then `READY_TO_SUBMIT → AWAITING_APPROVAL → DRAFT_CREATED → AWAITING_RESPONSE`; response may yield `DISPUTED`, `PROMISE_TO_PAY`, `OVERDUE`; valid evidence may yield `RECONCILIATION_REVIEW → PAID`; any active state may become `MANUAL_REVIEW`; terminal `PAID|CLOSED|CANCELLED`.

Events are facts: connector (`InvoiceImported`, `EmailObserved`, `DocumentObserved`, `BankTransactionImported`); deterministic rule (`DocumentMatched`, `BlockerDetected`, `PaymentMatchProposed`, `PromiseBroken`); LLM proposal (`ExtractionProposed`, `DisputeProposed`, `PromiseDateProposed`, `DraftProposed`); human (`MatchConfirmed`, `ApprovalGranted/Rejected`, `PaymentConfirmed`, `CaseClosed`); external-effect result (`GmailDraftCreated/Failed`). LLM events cannot mutate state until validation/rule or human command accepts them.

Invariants: tenant IDs match across links; outstanding never negative; allocation ≤ transaction and invoice outstanding; `PAID` requires confirmed allocations equal outstanding or explicit authorized adjustment (adjustment out of MVP); draft requires current approval, exact content/recipient/attachment hashes, approver role, allowed recipients and no unresolved critical review; terminal states reject workflow mutations except reopen by admin with reason. Illegal transitions return 409 and audit denial; duplicate commands return original result.

## 9. Contracts

- REST `/api/v1`: imports, documents/upload-url, cases/list/detail/events, reviews, approvals, connectors/gmail, drafts, bank-imports/matches, dashboard, settings, audit. Mutating calls require `Idempotency-Key`, optimistic `version`, tenant from verified token—not request body.
- Async jobs return `202 {job_id,status_url}`; UI polls/SSE for status. Standard error `{code,message,correlation_id,field_errors,retryable}`.
- Storage port: put/get signed URL/delete/head by tenant+hash; MIME and size metadata immutable.
- Gmail port: list label messages, fetch thread/attachment, create draft; no `send` method in interface.
- LLM port: `generate_structured(task,input,schema,prompt_version,route)` and `generate_text`; normalized result includes provider/model, request ID, usage, cost estimate, latency, finish/refusal/error, schema/semantic validity.
- OpenAPI is source for generated TS client; domain event JSON schemas are versioned and backward-compatible.

## 10. Ingestion/recovery

CSV/XLSX: upload quarantine → type/signature/size scan → mapping preview → row validation → staging → transactional upsert with source-file hash/row fingerprint → per-row result. Reimport is no-op/update by explicit policy; partial invalid rows do not contaminate valid transaction.

Gmail: OAuth least privilege (`gmail.readonly` + `gmail.compose`), configured label ID, initial paginated thread sync, store latest `historyId`, incremental `history.list`, dedupe message/attachment IDs and hashes. `watch` renewed daily (required within seven days); periodic reconciliation sync covers delayed/dropped push. Expired cursor/404 triggers bounded label full sync. Cursor advances only after durable ingestion commit. OAuth revoked → connector `AUTH_REQUIRED`, no retry storm.

Upload/Gmail attachment converge on one immutable pipeline. Max initial 25 MB/file, 100 pages, allowlisted PDF/PNG/JPEG/XLSX; archives/macros rejected. Backoff with jitter for retryable API errors; validation/policy errors non-retryable; exhausted items enter failure queue with retry/reprocess action and correlation ID.

## 11. Document, matching and blocker engines

Pipeline: quarantine/scan → SHA-256 cache lookup → native PDF/XLSX parser → page render/profile → Docling for structured PDF → PaddleOCR PP-StructureV3 for image/low-text pages → controlled vision LLM only for unresolved fields → canonical schema/Pydantic semantic checks → EvidenceSpan → manual review. Cache key includes file hash + pipeline/parser/model/config version. Never obey instructions inside content.

Matching priority: exact tenant + external/source ID; seller/buyer tax ID; normalized invoice/PO/contract number; currency/exact amount; date window; customer alias/fuzzy text. AI only ranks ambiguous candidates already tenant-blocked. Initial auto-link threshold ≥0.95 with no contradiction, review 0.75–0.95, reject <0.75; thresholds are placeholders until calibration. Persist feature vector, score, rule version and explanation.

Five blocker outputs may coexist: `MISSING_PAYMENT_DOCUMENT`, `INCORRECT_DOCUMENT_DATA`, `MISSING_ACCEPTANCE_OR_DELIVERY_CONFIRMATION`, `CUSTOMER_DISPUTE`, `BROKEN_PROMISE_TO_PAY`. Deterministic required-document matrix and field contradictions win over LLM. Each blocker has evidence, severity, confidence source, next action, owner; conflicting/unsupported output goes to review.

## 12. Temporal design

One workflow per `PaymentCase`, workflow ID `tenant/case`; activities: load snapshot, ingest source, process document, evaluate blockers, create task, prepare draft, create Gmail draft, reconcile payment, write outbox/audit. Signals: `document_added`, `review_resolved`, `approval_decided`, `email_observed`, `bank_match_confirmed`, `cancel`; queries return non-sensitive progress/status. Timers cover due date, promise date, connector backfill and approval expiry.

Workflow code is deterministic; all DB/network/clock randomness resides in activities. Activities have start-to-close and heartbeat timeouts, retry only timeout/rate-limit/5xx with bounded exponential policy; policy/input/auth errors non-retryable. Side effects use DB idempotency/outbox. Use worker build IDs/versioning plus replay tests against recorded histories before deploy; patch workflow branching or continue-as-new at safe boundary. Roll back workers only when replay-compatible; otherwise deploy compatible fix forward.

## 13. Approval and Gmail guardrail

Draft proposal freezes subject/body/To/Cc/Bcc/attachment hashes, case version and evidence citations. Approver sees diffs and evidence; edit creates new version and invalidates prior approval. Immediately before `drafts.create`, server rechecks membership, approval expiry/content hash, unresolved reviews, sender identity, recipients against case contacts/tenant domain policy, no Bcc by default, attachment ownership/hash/scan, and idempotency key. Gmail adapter exposes create only. Store returned draft ID; retry first searches local completed action and returns it. Wrong recipient and duplicate draft must be zero in tests.

## 14. LLM multi-provider

Application owns task schemas and prompts. `LLMRouter` selects capability (`fast_structured`, `reasoning_structured`, `draft_text`, `vision_fallback`) from config; adapters compile a portable JSON Schema subset for OpenAI, Gemini and Anthropic. Pydantic validates provider-independently, followed by semantic/evidence validation.

Timeout and at most two provider attempts total: same-provider retry for transient error; at most one schema repair; fallback only timeout/rate-limit/5xx/schema-invalid. No fallback for policy/refusal, invalid input, privacy-route restriction, or required human review. Circuit breaker and budget cap fail closed. Fake adapter supplies deterministic fixtures; a shared contract suite runs offline for all adapters, optional live canary is manual.

`llm_calls` records tenant/case/task, provider/model/config route, prompt/schema versions and hashes, input/output redacted hashes, latency, usage/cost, attempt/fallback lineage, error/refusal, schema and evidence validity. Minimize context to cited snippets, pseudonymize contacts, never send OAuth tokens/bank details, set provider storage off where supported, and allow tenant provider/data-region policy.

## 15. UX

- Dashboard: outstanding/overdue/document-blocked/broken-promise/collected, time range and stale-data marker.
- Queue: server filters/sort, blocker badges, owner, next action, bulk view only (no bulk approval).
- Detail: invoice facts, state/timeline, documents, email summary, blockers/tasks/promise/payment candidates.
- Evidence viewer: rendered page/image with polygon highlight; XLSX sheet/cell; extracted vs source and review decision.
- Approval inbox: recipient/attachment/content validation, evidence, edit/approve/reject and conflict handling.
- Settings: import mapping, Gmail connection/label/sync health, provider route status (no secret display), roles/retention.

Every screen has skeleton, empty, permission, stale/conflict, retryable and terminal error states. Desktop-first, functional ≥768 px; mobile read/review baseline; WCAG 2.1 AA keyboard/focus/color and localized Vietnamese-first formatting.

## 16. Security/threat model

Threats and controls: stolen OAuth/LLM secrets → encrypted secret store, envelope encryption, rotation/revoke; cross-tenant access → verified tenant claim + membership + forced RLS + negative tests; malicious upload → signature/MIME/size/page limits, randomized object key, quarantine, malware scan, no macro/archive, sandboxed resource-limited parser; parser bomb → time/memory/page ceilings; prompt injection → untrusted-data delimiters, no model tools/external actions, deterministic policy; recipient spoofing → approved contact allowlist and final hash check; replay/duplicate → idempotency/outbox; log leak → structured allowlist/redaction; SSRF → no arbitrary URL fetch; supply chain → lock/digest/SBOM/vulnerability scan.

TLS in transit, provider-managed encryption at rest plus app-level token encryption. Least privilege service accounts and separate dev/staging/prod. Export and deletion jobs are approved/audited. Backup encrypted and restore-tested. OAuth production verification/security-assessment lead time is a launch risk.

## 17. Local, deployment and operations

Planned env groups: database/Temporal/S3 endpoints, OIDC issuer/audience, Gmail OAuth/client + label, encryption key reference, LLM provider keys and model IDs/routes, upload/retention limits, telemetry endpoint. `.env.example` contains names only; secrets never committed.

Planned demo sequence after implementation: `make bootstrap`, `make up`, `make migrate`, `make seed-demo`, `make demo-smoke`; one `make demo` may wrap these. It must work with fake Gmail/LLM and CI fixture without internet/API keys; optional sandbox profile enables real Gmail/provider.

Local Compose: web, API, worker, PostgreSQL, Temporal dev/UI, S3-compatible storage, malware scanner and optional telemetry collector. Demo/staging: Cloud Run services/jobs in Singapore region, Cloud SQL PostgreSQL, GCS, Pub/Sub, Secret Manager, Temporal Cloud; web can run Cloud Run. Production path adds HA sizing, private networking, WAF, managed backup/PITR, separate projects and verified OAuth—no Kubernetes for MVP.

Health: `/live` process, `/ready` DB/storage/Temporal, connector-specific health separate (provider outage must not kill API readiness). Metrics: ingest lag/failure, queue age, workflow/activity failure, Gmail cursor/watch expiry, OCR latency, LLM validity/fallback/cost, approval age, draft duplicate attempts, reconciliation precision. Initial SLO: API 99.5% monthly, p95 reads <1 s excluding async jobs, 95% ingestion items start <5 min, zero unauthorized mutation. Alerts and runbooks cover auth revoked, Gmail cursor reset, failure queue, stuck workflow, provider outage, storage/DB restore.

## 18. Test/eval and release gates

Pyramid: pure domain/rule/unit; provider/storage/Gmail contract; Postgres RLS/import integration; Temporal time-skipping/replay/retry; connector fixtures; Playwright E2E; security/tenant/upload/prompt-injection; load at 5k invoices/month burst; backup/restore; regression eval. CI runs lint/format/type, unit/contract, migrations up/down-on-fresh DB, integration, workflow replay, web build/E2E smoke, secret/SCA/image scan; no network or paid LLM.

Hard release gates: wrong recipient 0; duplicate draft/external action 0; unauthorized mutation/cross-tenant read 0; financial state mutation by LLM 0; `PAID` without valid allocation 0; critical extracted fields with evidence or review 100%; schema validity after gateway 100%; prompt-injection external action 0. Quality targets: document classification ≥98%; clear-file MST/invoice/amount ≥99%; payment-term acceptable+evidence ≥95%; match precision ≥97%; blocker macro-F1 ≥90%; promise date ≥95%. Recall, thresholds, provider cost/latency and OCR degraded-set metrics remain calibration targets; report CIs and abstention rate.

Dataset/eval detail is authoritative in `MVP_DATASET_AND_EVAL_PLAN.md`.

## 19. Traceability

| MVP requirement | Component | Phase/tasks | Verification/acceptance |
|---|---|---|---|
| AR import/entities | import + domain | P1 | fixture upsert, row report, idempotent reimport |
| Gmail label/thread/attachment | Gmail connector | P2/P4 | pagination/history/404/full-sync/drop-push tests |
| File upload + five document types | pipeline | P1/P3 | allowlist, parser route, gold classification |
| Critical evidence | evidence model/viewer | P3 | 100% evidence-or-review gate |
| Deterministic matching | match engine | P3 | precision/recall/calibration report |
| Five blockers/tasks/review | blocker engine | P2/P3 | macro-F1 target; coexist/abstain tests |
| Durable case | Temporal | P2/P4 | restart/time-skip/replay/idempotency |
| Email dispute/PTP | communication analysis | P4 | held-out extraction + evidence |
| Approval then draft only | approval/Gmail | P2/P4 | wrong-recipient/duplicate = 0, no send port |
| Bank CSV/PAID | reconciliation | P5 | split/batch/amount invariant tests |
| Required UI | Next.js | P2–P5 | Playwright states/a11y smoke |
| Audit including LLM | audit/outbox/LLM gateway | P0/P2/P3 | complete lineage and denial audit |
| Reproducible eval/demo | generator/harness | P1/P6 | seed/checksum/offline CI/full local report |
| Security/operations | RLS/threat/runbooks | P0/P6 | negative tests, restore drill, health alerts |

## 20. Phases, critical path and rollback

Execution matrix (task-level dependency and acceptance live in `MVP_TASKS.md`):

| Phase | Primary paths/modules | Data/migration/config | Planned validation | Dependency / demo deliverable |
|---|---|---|---|---|
| P0 | root manifests, `backend/{domain,application,infrastructure,workflows}`, `services/*`, `apps/web`, `deploy/compose` | initial tenant/RLS/audit migration; env schema; fake routes | `make lint typecheck test-unit test-contract test-integration test-workflow build` | sponsor approval / tenant-safe foundation and risk-spike report |
| P1 | `services/api/imports`, `backend/infrastructure/storage`, `apps/web/imports`, `tools/dataset` | customer/invoice/case/document migrations; import mapping; smoke manifest | import/file-policy/RLS integration + Playwright smoke | P0 / imported invoices and safe uploads visible |
| P2 | `backend/{documents,matching,blockers,approvals,workflows}`, `apps/web/cases` | evidence/blocker/task/approval/outbox tables; fake connector route | `make demo-smoke`, replay, idempotency, security E2E | P1 / required early end-to-end slice |
| P3 | `services/worker/documents`, `backend/infrastructure/llm`, `prompts`, `evals`, evidence UI | extraction/link/LLM-call migrations; parser/provider/threshold configs | full document/provider/evidence/injection eval | P2 + corpus / five-document/five-blocker demo |
| P4 | `backend/infrastructure/gmail`, communication analysis, case workflow, settings/approval UI | OAuth/cursor/communication/promise/draft tables; Gmail label/watch config | Gmail fixture contract, cursor loss/revoke, timer/replay, recipient E2E | P2/P3 and sandbox credential / approved real draft |
| P5 | bank import/matching/allocation modules, dashboard/queue UI | bank/allocation migrations; reconciliation thresholds | bank invariant/concurrency tests + aggregate/E2E | P3/P4 / reviewed bank match to PAID |
| P6 | `tests/{security,load,e2e}`, `docs/runbooks`, `deploy/gcp`, eval reports | retention/deletion jobs, alert/deploy config; no breaking schema without rehearsal | release matrix, load, SBOM/SCA, backup/restore, fresh demo | all phases / staging candidate or fail-closed report |

### P0 — Foundation and risk spikes (3–4 dev-days)

Outcome: runnable skeleton plan becomes verified technical foundation after approval. Tasks P0-T01..T08 create workspace/tooling, contracts, DB/RLS/audit, ports/fakes, Compose/CI and spikes for OCR/Gmail/Temporal. Acceptance: clean bootstrap, RLS denial, fake provider contracts, Temporal replay sample, OCR Vietnamese sample within resource budget. Failure/fallback: pin Python 3.12 or isolate OCR image if 3.13 dependency conflict; use poll-only Gmail demo if Pub/Sub unavailable. No product state migration to roll back beyond reversible initial revision.

### P1 — Data intake and synthetic corpus (4–5 dev-days)

Outcome: user imports AR and files, sees normalized case and ingest status. Tasks build generator/smoke fixtures, import preview/upsert, object quarantine, document metadata and basic case UI. Acceptance: 100-invoice sample and malformed rows; duplicate input no duplicate entity; file policy tests. Rollback: disable failing parser route; retain immutable source + reprocess version.

### P2 — Early vertical slice (5–6 dev-days)

Outcome: one invoice + Gmail fixture + synthetic document → evidence → missing-document blocker → review/approval → exactly one fake/sandbox draft + audit. Adds minimal Temporal case workflow, Gmail fixture connector, manual review, approval/detail UI. This is the first end-to-end demo and critical path gate. Rollback: fake connector/provider profile; workflow build ID remains available.

### P3 — Full document intelligence and five blockers (7–9 dev-days)

Outcome: all document types and blockers with evidence/calibrated abstention. Implements native/Docling/OCR routing, three provider adapters, extraction/matching/blocker rules, evidence viewer and review queue. Acceptance: full held-out metrics report; critical evidence gate; adapters pass same contract. Rollback: route problematic type/provider to manual review; cache version allows reprocess.

### P4 — Real Gmail and durable communication lifecycle (5–7 dev-days)

Outcome: safe label sync, dispute/PTP, timers and approved Gmail drafts. Includes OAuth, pagination/history/watch/backfill, connector health, promise timer, final guardrails. Acceptance: cursor expiry, push loss, OAuth revoke, restart and duplicate activity tests; no send endpoint. Rollback: disable push/use scheduled sync; revoke connector; retain fake demo.

### P5 — Reconciliation and operational UI (4–5 dev-days)

Outcome: bank CSV proposes matches, reviewed allocation closes PAID; dashboard/queue/settings useful. Acceptance: exact/ambiguous, split/combined/duplicate bank cases; invariant prevents false PAID. Rollback: all bank matches manual; undo unconfirmed proposal, never overwrite source.

### P6 — Hardening/release (5–7 dev-days)

Outcome: reproducible demo/staging candidate. Full eval matrix, security/load/backup restore, observability/runbooks, deployment and acceptance rehearsal. Release only if hard gates pass; otherwise route low-confidence functionality to manual review or disable live connector/provider. Rollback uses prior image/workflow build, forward-compatible DB migration, feature flags and restored backup drill.

Critical path: P0 domain/RLS/ports → P1 canonical ingest → P2 vertical slice → P3 evidence/matching/blockers → P4 real Gmail/durable effects → P5 payment invariant → P6 gates. Dataset generator/UI primitives can parallelize after P0; Gmail OAuth preparation can parallelize P1–P3; reconciliation waits for invoice/case model; calibration waits for dataset and pipeline.

Estimate: 33–43 developer-days. Two developers: ~5–6 calendar weeks with dataset/UI/Gmail streams parallel; one developer: ~8–10 weeks including integration/hardening. External OAuth verification is excluded and may exceed build time.

## 21. Risk register

| Risk | P/I | Detection | Mitigation/fallback |
|---|---|---|---|
| Vietnamese OCR below target | H/H | degraded-set F1, review rate | native first, preprocess, per-page fallback, manual review |
| Gmail OAuth verification delay | H/H | consent/verification status | internal pilot/sandbox, fake connector; begin P0 paperwork |
| False match/false PAID | M/H | held-out precision, invariant alarms | high precision threshold, review, allocation evidence |
| Duplicate draft from retry | M/H | idempotency tests/metric | unique key, outbox, stored external ID, final recheck |
| Cross-tenant leak | L/H | RLS/security suite | forced RLS, non-owner API role, tenant negative E2E |
| Temporal nondeterminism | M/H | replay CI | activities for I/O, build IDs, patching, compatible rollback |
| Provider/schema drift | H/M | contract/canary failure | portable schema, config route, fake/offline, bounded fallback |
| OCR resource/Windows mismatch | M/M | P0 spike/runtime OOM | Linux worker container, CPU limits, Python 3.12 fallback |
| Synthetic-real domain gap | H/M | pilot abstention/error review | adversarial variants, calibration, manual-review-first |
| Sensitive data exposure | M/H | DLP/log/provider audit | context minimization, redaction, encryption, retention/delete |

## 22. Decisions requiring approval

See `MVP_DECISIONS.md`. Before P0, approve: deployment baseline, auth approach, Gmail pilot mode, retention, and delivery staffing/timebox. Recommended defaults allow P0 to proceed without architecture changes.
