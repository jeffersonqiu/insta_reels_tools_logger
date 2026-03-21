# Build from **repository root** (monorepo). Copies only `backend/` into the image.
# Use this when Railway’s service root is the repo root (default on first import).
FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/ ./

ENV PYTHONUNBUFFERED=1
ENV PORT=8000
EXPOSE 8000

CMD uv run uvicorn main:app --host 0.0.0.0 --port ${PORT}
