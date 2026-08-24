.PHONY: bootstrap up down migrate seed-demo demo-smoke lint typecheck test test-unit test-contract test-integration test-workflow build
bootstrap:
	corepack enable
	pnpm install --frozen-lockfile
	uv sync --all-groups
up:
	docker compose up -d
down:
	docker compose down
migrate:
	uv run alembic upgrade head
seed-demo:
	uv run python -m tools.seed_demo
demo-smoke:
	uv run python -m tools.seed_demo
	uv run pytest tests/e2e -q
lint:
	uv run ruff check .
	pnpm lint
typecheck:
	uv run mypy backend services
	pnpm typecheck
test:
	uv run pytest

test-unit:
	uv run pytest tests/unit
test-contract:
	uv run pytest tests/contract
test-integration:
	uv run pytest tests/integration
test-workflow:
	uv run pytest tests/workflow
build:
	pnpm build
