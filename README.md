# AR Operations Agent

V2 adds point-in-time probability-to-pay, probabilistic cash flow, dispute root-cause analytics,
customer behavior, evidence-backed escalation recommendations, privacy-aware team benchmarks and
safe low-risk email automation infrastructure. Automation is disabled with kill switches on by
default; the local demo does not send external email. See `docs/V2_OPERATIONS.md`.

Evidence-first V1 for B2B accounts-receivable operations. The deterministic core owns money,
dates and state; document AI and provider-neutral LLM adapters produce reviewable proposals;
Temporal provides durable orchestration; a human approves every Gmail/Outlook draft and Zalo
notification. MISA is read-only and every external connector defaults to sandbox/dry-run.

## Development

1. Copy `.env.example` to `.env` and keep development defaults.
2. Run `make bootstrap` (or `corepack pnpm install` and `uv sync --all-groups`).
3. Run `docker compose up -d`, `uv run alembic upgrade head`, and `uv run uvicorn services.api.main:app --reload`.
4. Run `pnpm dev` for the web application.

The offline demo uses fake Gmail and LLM adapters and never sends email.

## Portfolio deployment

The zero-cost portfolio profile uses Next.js/Vercel, FastAPI/Render and PostgreSQL/Neon. It enables
MISA-compatible CSV/XLSX import plus Microsoft OAuth, manual Outlook delta sync and allowlisted
draft creation after human approval. Upload/OCR, Temporal, MISA API, Outlook webhooks and email send
are fail-closed. See `docs/PORTFOLIO_DEPLOYMENT.md`; this profile is not a full production release.

## V1 capabilities

V1 adds tenant-scoped MISA incremental sync, Outlook delta/webhook/draft support, controlled Zalo
OA previews, advanced bank allocation/reversal rules, versioned customer payment rules, safe bulk
approval, deterministic aging forecasts, permission-based RBAC, and redacted LLM cost/quality
analytics. Automated tests use fake connectors and require no external credential. See
`docs/V1_OPERATIONS.md` for sandbox opt-in and the release checklist.
