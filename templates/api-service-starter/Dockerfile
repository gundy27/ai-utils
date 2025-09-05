FROM python:3.11-slim AS base

ENV POETRY_VERSION=1.8.3 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

# Copy entire repo to preserve local path dependency to libs/llm_wrappers/openai_wrapper
COPY . /app

WORKDIR /app/templates/api-service-starter

RUN poetry install --no-interaction --no-ansi

EXPOSE 8001

CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]


