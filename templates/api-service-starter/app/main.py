from __future__ import annotations

import os
from typing import Dict, Iterable, List, Optional

import backoff
import structlog
from dotenv import load_dotenv
import time
from collections import defaultdict, deque
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from openai import APIConnectionError, APIError, RateLimitError, Timeout
from gundy_ai.llm import OpenAIClient
from pydantic import BaseModel, Field


logger = structlog.get_logger(__name__)
load_dotenv(override=False)

app = FastAPI(title="LLM API Starter")


# -------------------------
# Metrics (Prometheus)
# -------------------------
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency (seconds)",
    ["method", "path"],
)


# -------------------------
# Structured request logging
# -------------------------
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "-")
    path = request.url.path
    method = request.method
    logger.info(
        "request.start", method=method, path=path, client_ip=client_ip, ua=user_agent
    )
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "request.exception",
            method=method,
            path=path,
            client_ip=client_ip,
            ua=user_agent,
            duration_ms=duration_ms,
            error=str(e),
        )
        REQUEST_COUNT.labels(method=method, path=path, status="500").inc()
        REQUEST_LATENCY.labels(method=method, path=path).observe(
            (time.time() - start_time)
        )
        raise
    duration_ms = int((time.time() - start_time) * 1000)
    logger.info(
        "request.end",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
    )
    REQUEST_COUNT.labels(method=method, path=path, status=str(status_code)).inc()
    REQUEST_LATENCY.labels(method=method, path=path).observe((time.time() - start_time))
    return response


# -------------------------
# Simple per-IP rate limiting
# -------------------------
_requests_by_ip: defaultdict[str, deque] = defaultdict(deque)


def _rate_limit_params() -> tuple[bool, int, int]:
    enabled = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() in {
        "1",
        "true",
        "yes",
    }
    window_seconds = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "10"))
    max_requests = int(os.environ.get("RATE_LIMIT_MAX_REQUESTS", "30"))
    return enabled, window_seconds, max_requests


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    enabled, window_seconds, max_requests = _rate_limit_params()
    if not enabled:
        return await call_next(request)
    # Skip health
    if request.url.path == "/health":
        return await call_next(request)

    now = time.time()
    client_ip = request.client.host if request.client else "unknown"
    dq = _requests_by_ip[client_ip]
    # purge old
    cutoff = now - window_seconds
    while dq and dq[0] < cutoff:
        dq.popleft()
    if len(dq) >= max_requests:
        logger.warning(
            "rate_limit.blocked",
            client_ip=client_ip,
            window_seconds=window_seconds,
            max_requests=max_requests,
        )
        raise HTTPException(status_code=429, detail="Too Many Requests")
    dq.append(now)
    return await call_next(request)


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = Field(default="gpt-4o-mini")
    messages: List[Message]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    extra: Optional[Dict[str, object]] = None


def _is_retryable(exc: Exception) -> bool:
    return isinstance(exc, (RateLimitError, APIConnectionError, Timeout)) or (
        isinstance(exc, APIError) and (500 <= getattr(exc, "status_code", 500) < 600)
    )


def _get_client() -> OpenAIClient:
    try:
        return OpenAIClient()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/chat")
def chat(req: ChatRequest) -> Dict[str, str]:
    client = _get_client()

    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_time=60 * 5,
        giveup=lambda e: not _is_retryable(e),
    )
    def _call() -> str:
        logger.info("api.chat.request", model=req.model)
        content = client.chat(
            model=req.model,
            messages=[m.model_dump() for m in req.messages],
            temperature=req.temperature,
            top_p=req.top_p,
            max_tokens=req.max_tokens,
            extra=req.extra,
        )
        logger.info("api.chat.response", model=req.model)
        return content

    try:
        content = _call()
        return {"content": content}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("api.chat.error", error=str(e))
        raise HTTPException(status_code=502, detail="Upstream error")


@app.post("/chat/stream")
def chat_stream(req: ChatRequest) -> StreamingResponse:
    client = _get_client()

    def iterator() -> Iterable[bytes]:
        logger.info("api.chat_stream.request", model=req.model)
        stream = client.chat_stream(
            model=req.model,
            messages=[m.model_dump() for m in req.messages],
            temperature=req.temperature,
            top_p=req.top_p,
            max_tokens=req.max_tokens,
            extra=req.extra,
        )
        for text in stream:
            yield text.encode("utf-8")

    return StreamingResponse(iterator(), media_type="text/plain")
