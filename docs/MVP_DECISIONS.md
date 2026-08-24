# MVP Decisions and Approval Log

Status values: `proposed`, `approved`, `superseded`. All are `proposed` until the sponsor explicitly approves the plan.

## ADR index / assumptions selected

| ADR | Status | Decision |
|---|---|---|
| ADR-001 | proposed | Evidence-first deterministic core; PostgreSQL truth, Temporal lifecycle, LLM proposals only, human external-action approval. |
| ADR-002 | proposed | Monorepo: Next.js 16/Node 24 LTS; FastAPI/Python 3.13; PostgreSQL 18; Temporal Python 1.31; exact lock/digest. |
| ADR-003 | proposed | No pgvector until eval proves retrieval need. Matching uses tenant blocking + identifiers/money/date/fuzzy rules. |
| ADR-004 | proposed | S3-compatible storage port; local compatible service, production GCS; immutable SHA-256 versions. |
| ADR-005 | proposed | Gmail scopes `gmail.readonly` + `gmail.compose`; label-only business filtering; daily watch renewal + sync fallback; adapter has no send capability. |
| ADR-006 | proposed | Portable LLM gateway with OpenAI/Gemini/Anthropic adapters; task/capability config; bounded repair/fallback; fake provider in CI. |
| ADR-007 | proposed | Native parser → Docling → PaddleOCR → controlled vision fallback; critical fields require evidence or review. |
| ADR-008 | proposed | OIDC issuer/JWT authentication, DB membership/RBAC and forced PostgreSQL RLS; dev identity impossible in non-dev. |
| ADR-009 | proposed | Full evaluation corpus is seeded synthetic; public/real data not required; no paid/network CI. |
| ADR-010 | proposed | Pilot deploy path is Cloud Run/Cloud SQL/GCS/PubSub/Secret Manager in Singapore + Temporal Cloud; no Kubernetes. |

## Important reversible assumptions

- One pilot tenant but multi-tenant schema and tests from day one.
- One invoice per case for early slice; association schema supports many.
- 25 MB/100-page initial upload limits and Vietnamese-first UX.
- Auto-match thresholds 0.95/0.75 are calibration starting points, not fixed policy.
- Development can demonstrate fake Gmail/LLM fully offline; real Gmail/provider is optional sandbox profile.
- Default data retention proposal is raw 365 days after close and audit/derived 7 years, configurable and subject to legal approval.

## Sponsor approvals required before P0

### D1 — Deployment baseline

**Recommended:** GCP Singapore + Temporal Cloud; local Compose. Fastest Gmail/PubSub path and least workflow operations. Trade-off: two managed vendors and recurring cost. Alternative: self-host Temporal/object store, lower vendor cost but materially higher operations and schedule risk.

### D2 — Authentication

**Recommended:** portable OIDC with a managed issuer selected during P0 procurement, roles in PostgreSQL; dev-only local issuer. Avoids binding domain logic to Auth0/WorkOS/Supabase. Trade-off: initial issuer configuration. Alternative: custom password auth is cheaper to start but increases security scope and is not recommended.

### D3 — Gmail pilot availability

**Recommended:** start Google OAuth verification/security review immediately, while demo uses internal Workspace/sandbox plus fake connector. Trade-off: production onboarding may wait for Google review. Alternative: poll/import `.eml` only reduces approval work but fails the required real connector path.

### D4 — Retention/deletion policy

**Recommended:** raw email/files 365 days after case close; derived/audit 7 years; tenant-configurable shorter raw retention and documented export/delete. Trade-off: storage/compliance burden. Alternative: 90-day raw retention reduces exposure but weakens later dispute evidence.

### D5 — Delivery constraint

**Recommended:** two developers for 5–6 weeks plus part-time product/QA; keep all five blockers and gates. Trade-off: higher staffing. Alternative: one developer for 8–10 weeks; forcing six weeks with one developer should reduce live integrations/UX polish, not safety gates.

## Explicit non-decisions until evidence

- Production LLM provider/model and task routes: choose from cross-provider eval and tenant data policy; IDs remain config.
- GPU vs CPU OCR: P0 resource/accuracy spike.
- pgvector/semantic retrieval: add only if deterministic held-out recall is inadequate.
- Auto-link and reconciliation thresholds: set from calibration with confidence intervals.
- Production-scale SLO/capacity: refine from P6 load and pilot traffic.

Approval record to append after sponsor response: date, approver, approved decision IDs, exceptions and resulting ADR/task changes.

