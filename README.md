# AR Operations Agent

Evidence-first MVP for B2B accounts-receivable operations. The deterministic core owns money,
dates and state; document AI and provider-neutral LLM adapters produce reviewable proposals;
Temporal provides durable orchestration; a human approves every Gmail draft.

## Development

1. Copy `.env.example` to `.env` and keep development defaults.
2. Run `make bootstrap` (or `corepack pnpm install` and `uv sync --all-groups`).
3. Run `docker compose up -d`, `uv run alembic upgrade head`, and `uv run uvicorn services.api.main:app --reload`.
4. Run `pnpm dev` for the web application.

The offline demo uses fake Gmail and LLM adapters and never sends email.

