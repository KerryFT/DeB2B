FROM python:3.12.11-slim
WORKDIR /app
ENV PADDLE_PDX_CACHE_HOME=/app/.cache/paddlex
ENV XDG_CACHE_HOME=/app/.cache
COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /uvx /bin/
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core libgl1 libglib2.0-0 libgomp1 \
    && apt-get purge -y --allow-remove-essential perl-base \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --group documents --no-dev --no-install-project
COPY backend backend
COPY services services
COPY tools tools
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --group documents --no-dev
CMD ["uv", "run", "--no-sync", "python", "-m", "tools.spikes.ocr_smoke"]
