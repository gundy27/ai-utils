from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from collections.abc import Iterable
from math import sqrt
from pathlib import Path

import backoff
import structlog
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from gundy_ai.http import (
    OAuth2Client,
    OAuth2Config,
    RestClient,
    RestClientError,
)
from gundy_ai.llm import OpenAIClient
from openai import APIConnectionError, APIError, OpenAI, RateLimitError, Timeout
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)
load_dotenv(override=False)

app = FastAPI(title="LLM API Starter")


# -------------------------
# Retrieval + Sessions setup
# -------------------------
_embedding_model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
_corpus_dir = Path(__file__).parent / "corpus"

# In-memory corpus: list of (text, embedding)
_corpus: list[tuple[str, list[float]]] = []


class _SessionState(BaseModel):
    summary: str = ""
    last_messages: list[dict[str, str]] = []  # role/content dicts
    turns: int = 0


_sessions: dict[str, _SessionState] = {}


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = 0.0
    na = 0.0
    nb = 0.0
    for i in range(min(len(a), len(b))):
        va = a[i]
        vb = b[i]
        dot += va * vb
        na += va * va
        nb += vb * vb
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (sqrt(na) * sqrt(nb))


def _get_embedding_client() -> OpenAI:
    try:
        return OpenAI()
    except Exception as e:
        logger.error("embedding.client.error", error=str(e))
        raise


def _embed_texts(texts: list[str]) -> list[list[float]]:
    client = _get_embedding_client()
    embeddings: list[list[float]] = []
    for t in texts:
        resp = client.embeddings.create(model=_embedding_model, input=t)
        embeddings.append(resp.data[0].embedding)  # type: ignore[attr-defined]
    return embeddings


def _load_corpus() -> None:
    global _corpus
    _corpus = []
    if not _corpus_dir.exists():
        logger.info("corpus.missing", path=str(_corpus_dir))
        return
    chunks: list[str] = []
    for p in sorted(_corpus_dir.glob("*.txt")):
        try:
            content = p.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning("corpus.read_error", file=str(p), error=str(e))
            continue
        for para in [s.strip() for s in content.split("\n\n") if s.strip()]:
            chunks.append(para)
    if not chunks:
        logger.info("corpus.empty")
        return
    logger.info(
        "corpus.embedding_start", num_chunks=len(chunks), model=_embedding_model
    )
    vecs = _embed_texts(chunks)
    _corpus = list(zip(chunks, vecs, strict=False))
    logger.info("corpus.embedding_done", num_chunks=len(_corpus))


@app.on_event("startup")
def _startup_load_corpus() -> None:
    _load_corpus()


def _get_or_create_session(session_id: str) -> _SessionState:
    s = _sessions.get(session_id)
    if s is None:
        s = _SessionState()
        _sessions[session_id] = s
    return s


def _augment_messages(
    session_id: str | None, req_messages: list[dict[str, str]]
) -> list[dict[str, str]]:
    user_msgs = [m for m in req_messages if m.get("role") == "user"]
    query = user_msgs[-1]["content"] if user_msgs else ""

    retrieved_context = ""
    if _corpus and query:
        q_vec = _embed_texts([query])[0]
        scored = [(_cosine_similarity(q_vec, vec), text) for text, vec in _corpus]
        scored.sort(key=lambda x: x[0], reverse=True)
        top_k = int(os.environ.get("RETRIEVAL_TOP_K", "3"))
        top_chunks = [t for _, t in scored[:top_k]]
        if top_chunks:
            retrieved_context = "\n\n".join(top_chunks)

    summary = ""
    if session_id and session_id in _sessions:
        summary = _sessions[session_id].summary

    system_preamble_parts: list[str] = []
    if retrieved_context:
        system_preamble_parts.append(
            "Use the following context snippets if relevant to answer.\n"
            + retrieved_context
        )
    if summary:
        system_preamble_parts.append("Conversation summary so far:\n" + summary)

    augmented: list[dict[str, str]] = []
    if system_preamble_parts:
        augmented.append(
            {"role": "system", "content": "\n\n---\n".join(system_preamble_parts)}
        )
    augmented.extend(req_messages)
    return augmented


def _maybe_summarize(session_id: str, full_messages: list[dict[str, str]]) -> None:
    s = _get_or_create_session(session_id)
    s.turns += 1
    summarize_every = int(os.environ.get("SUMMARY_EVERY_TURNS", "4"))
    if s.turns % summarize_every != 0:
        return
    client = _get_client()
    prompt_messages = [
        {
            "role": "system",
            "content": "Summarize the conversation in 5-8 bullet points.",
        },
    ] + full_messages
    try:
        summary = client.chat(
            model=os.environ.get("SUMMARY_MODEL", "gpt-4o-mini"),
            messages=prompt_messages,
            max_tokens=300,
        )
        s.summary = summary
    except Exception as e:
        logger.warning("summary.error", error=str(e))


def _prune_history(
    session_id: str, req_messages: list[dict[str, str]], assistant_reply: str
) -> None:
    s = _get_or_create_session(session_id)
    combined = req_messages + [{"role": "assistant", "content": assistant_reply}]
    keep = int(os.environ.get("KEEP_LAST_MESSAGES", "6"))
    s.last_messages = combined[-keep:]


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
            time.time() - start_time
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
    REQUEST_LATENCY.labels(method=method, path=path).observe(time.time() - start_time)
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
    messages: list[Message]
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    extra: dict[str, object] | None = None
    session_id: str | None = Field(
        default=None, description="Client session identifier"
    )


def _is_retryable(exc: Exception) -> bool:
    return isinstance(exc, RateLimitError | APIConnectionError | Timeout) or (
        isinstance(exc, APIError) and (500 <= getattr(exc, "status_code", 500) < 600)
    )


def _get_client() -> OpenAIClient:
    try:
        return OpenAIClient()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


class DemoResponse(BaseModel):
    url: str
    origin: str | None = None
    headers: dict[str, str] | None = None


@app.get("/demo/httpbin")
def demo_httpbin() -> dict[str, object]:
    base = os.environ.get("DEMO_API_BASE", "https://httpbin.org")
    # OAuth optional demo: only used if DEMO_TOKEN_URL is set
    oauth: OAuth2Client | None = None
    if os.environ.get("DEMO_TOKEN_URL"):
        oauth = OAuth2Client(
            OAuth2Config(
                token_url=os.environ["DEMO_TOKEN_URL"],
                client_id=os.environ.get("DEMO_CLIENT_ID", ""),
                client_secret=os.environ.get("DEMO_CLIENT_SECRET", ""),
                scopes=os.environ.get("DEMO_SCOPES", "").split() or None,
            )
        )
    client = RestClient(base, oauth2=oauth, default_headers={"x-demo": "1"})
    try:
        data = client.get("/get", response_model=DemoResponse)
        return data.model_dump()
    except RestClientError as e:
        logger.error("demo.httpbin.error", error=e.error.model_dump())
        raise HTTPException(status_code=502, detail=e.error.model_dump()) from e


@app.post("/chat")
def chat(req: ChatRequest) -> dict[str, str]:
    client = _get_client()

    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_time=60 * 5,
        giveup=lambda e: not _is_retryable(e),
    )
    def _call() -> str:
        logger.info("api.chat.request", model=req.model)
        augmented_messages = _augment_messages(
            req.session_id, [m.model_dump() for m in req.messages]
        )
        content = client.chat(
            model=req.model,
            messages=augmented_messages,
            temperature=req.temperature,
            top_p=req.top_p,
            max_tokens=req.max_tokens,
            extra=req.extra,
        )
        logger.info("api.chat.response", model=req.model)
        return content

    try:
        content = _call()
        if req.session_id:
            _prune_history(
                req.session_id,
                [m.model_dump() for m in req.messages],
                content,
            )
            _maybe_summarize(req.session_id, _sessions[req.session_id].last_messages)
        return {"content": content}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("api.chat.error", error=str(e))
        raise HTTPException(status_code=502, detail="Upstream error") from e


@app.post("/chat/stream")
def chat_stream(req: ChatRequest) -> StreamingResponse:
    client = _get_client()

    def iterator() -> Iterable[bytes]:
        logger.info("api.chat_stream.request", model=req.model)
        augmented_messages = _augment_messages(
            req.session_id, [m.model_dump() for m in req.messages]
        )
        stream = client.chat_stream(
            model=req.model,
            messages=augmented_messages,
            temperature=req.temperature,
            top_p=req.top_p,
            max_tokens=req.max_tokens,
            extra=req.extra,
        )
        full_text = ""
        for text in stream:
            full_text += text
            yield text.encode("utf-8")
        if req.session_id:
            _prune_history(
                req.session_id, [m.model_dump() for m in req.messages], full_text
            )
            _maybe_summarize(req.session_id, _sessions[req.session_id].last_messages)

    return StreamingResponse(iterator(), media_type="text/plain")
