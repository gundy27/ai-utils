from __future__ import annotations

import time

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from .auth.keys import get_jwks
from .middleware.rate_limit import RateLimitMiddleware
from .audit.middleware import AuditMiddleware

logger = structlog.get_logger(__name__)

app = FastAPI(title="Auth & Secrets Service")


# Metrics
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "path", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency (seconds)",
    ["method", "path"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start = time.time()
    method = request.method
    path = request.url.path
    logger.info("request.start", method=method, path=path)
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        REQUEST_COUNT.labels(method=method, path=path, status="500").inc()
        REQUEST_LATENCY.labels(method=method, path=path).observe(time.time() - start)
        logger.error("request.exception", method=method, path=path, error=str(e))
        raise
    REQUEST_COUNT.labels(method=method, path=path, status=str(status_code)).inc()
    REQUEST_LATENCY.labels(method=method, path=path).observe(time.time() - start)
    logger.info("request.end", method=method, path=path, status_code=status_code)
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Routers
from .routers import audit, auth, secrets, oauth2, token_exchange  # noqa: E402

app.include_router(secrets.router, prefix="/secrets", tags=["secrets"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(audit.router, prefix="/audit", tags=["audit"])
app.include_router(oauth2.router, tags=["oauth2"])
app.include_router(token_exchange.router, tags=["token-exchange"])

# Middleware
app.add_middleware(AuditMiddleware)
app.add_middleware(RateLimitMiddleware)


@app.get("/.well-known/jwks.json")
def jwks() -> JSONResponse:
    return JSONResponse(get_jwks())
