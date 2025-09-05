## API Service Starter

Stack: FastAPI + LangChain wrapper + logging/monitoring.

Includes

- Health checks, env-based config, simple request/response logging.
- Hooks for tracing and rate limiting.

Use as cookiecutter or copy into client repos.

### Run locally

```bash
cd templates/api-service-starter
python3 -m poetry install
cp .env.example .env  # set OPENAI_API_KEY
python3 -m poetry run uvicorn app.main:app --reload
```

### Endpoints

- `GET /health`: service health
- `POST /chat`: non-streaming chat completion
- `POST /chat/stream`: server-sent events stream
- `GET /metrics`: Prometheus metrics

### Environment

- `OPENAI_API_KEY` (required)
- `OPENAI_BASE_URL` (optional)
- `OPENAI_TIMEOUT_SECONDS` (default 60)
- `OPENAI_MAX_RETRIES` (default 3)
- `RATE_LIMIT_ENABLED` (default true)
- `RATE_LIMIT_WINDOW_SECONDS` (default 10)
- `RATE_LIMIT_MAX_REQUESTS` (default 30)

### Docker

```bash
cd templates/api-service-starter
# Build image (context is repo root to include wrapper path dependency)
docker build -t ai-utils-api -f Dockerfile ../..

# Or via compose
docker compose up --build
```
