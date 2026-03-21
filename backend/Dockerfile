# Railway / any container host: Python 3.12 + uv + ffmpeg (helps yt-dlp / audio)
FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

ENV PYTHONUNBUFFERED=1
# Railway injects PORT; default 8000 for local docker run
ENV PORT=8000

EXPOSE 8000

# Shell form so $PORT expands at runtime
CMD uv run uvicorn main:app --host 0.0.0.0 --port ${PORT}
