FROM python:3.13.14-alpine3.23
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend backend
COPY services services
RUN uv sync --frozen --no-dev
ENV UV_CACHE_DIR=/tmp/uv-cache
USER 65532:65532
CMD ["uv", "run", "--no-sync", "python", "-m", "services.worker.main"]
