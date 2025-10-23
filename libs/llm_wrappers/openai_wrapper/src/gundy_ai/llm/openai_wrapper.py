from __future__ import annotations

import os
import time
from collections.abc import Generator, Iterable

import backoff
import httpx
import structlog
from dotenv import load_dotenv
from openai import APIConnectionError, APIError, OpenAI, RateLimitError, Timeout

logger = structlog.get_logger(__name__)


def _mask(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return value[:4] + "***" + value[-4:]


class OpenAIClient:
    """Secure OpenAI client with retries, structured logging, and streaming.

    Configuration via environment variables:
      - OPENAI_API_KEY
      - OPENAI_BASE_URL (optional)
      - OPENAI_ORG_ID (optional)
      - OPENAI_PROJECT_ID (optional)
      - OPENAI_TIMEOUT_SECONDS (default 60)
      - OPENAI_MAX_RETRIES (default 3)
    """

    def __init__(self) -> None:
        load_dotenv(override=False)

        self.api_key: str = os.environ.get("OPENAI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required")

        base_url: str | None = os.environ.get("OPENAI_BASE_URL")
        organization: str | None = os.environ.get("OPENAI_ORG_ID")
        project: str | None = os.environ.get("OPENAI_PROJECT_ID")
        timeout_seconds: int = int(os.environ.get("OPENAI_TIMEOUT_SECONDS", "60"))
        max_retries: int = int(os.environ.get("OPENAI_MAX_RETRIES", "3"))

        logger.info(
            "openai_client.init",
            base_url=base_url,
            organization=organization,
            project=project,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            api_key=_mask(self.api_key),
        )

        self._client = OpenAI(
            api_key=self.api_key,
            base_url=base_url,
            organization=organization,
            project=project,
            timeout=timeout_seconds,
            max_retries=max_retries,
            http_client=httpx.Client(timeout=timeout_seconds),
        )

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        return isinstance(exc, (RateLimitError, APIConnectionError, Timeout)) or (
            isinstance(exc, APIError) and (500 <= getattr(exc, "status_code", 500) < 600)
        )

    def _backoff_handler(self, details: dict[str, object]) -> None:
        wait = details.get("wait")
        tries = details.get("tries")
        exc = details.get("exception")
        logger.warning("openai_client.retry", tries=tries, wait=wait, error=str(exc))

    def _giveup_handler(self, details: dict[str, object]) -> None:
        tries = details.get("tries")
        exc = details.get("exception")
        logger.error("openai_client.giveup", tries=tries, error=str(exc))

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, object]],
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
        extra: dict[str, object] | None = None,
    ) -> str:
        """Non-streaming chat completion returning the full text content.

        Raises on failure after retries.
        """

        @backoff.on_exception(
            backoff.expo,
            Exception,
            max_time=60 * 5,
            giveup=lambda e: not self._is_retryable(e),
            on_backoff=self._backoff_handler,
            on_giveup=self._giveup_handler,
        )
        def _call() -> str:
            start = time.time()
            logger.info("openai_client.chat.request", model=model)
            resp = self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                **(extra or {}),
            )
            duration = time.time() - start
            logger.info(
                "openai_client.chat.response",
                model=model,
                duration_ms=int(duration * 1000),
            )
            if not resp.choices:
                return ""
            message = resp.choices[0].message
            content = getattr(message, "content", None)
            return content or ""

        return _call()

    def chat_stream(
        self,
        *,
        model: str,
        messages: list[dict[str, object]],
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
        extra: dict[str, object] | None = None,
    ) -> Iterable[str]:
        """Streaming chat completion yielding text chunks.

        Yields text deltas as they arrive.
        """

        @backoff.on_exception(
            backoff.expo,
            Exception,
            max_time=60 * 5,
            giveup=lambda e: not self._is_retryable(e),
            on_backoff=self._backoff_handler,
            on_giveup=self._giveup_handler,
        )
        def _call() -> Generator[str, None, None]:
            logger.info("openai_client.chat_stream.request", model=model)
            with self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stream=True,
                **(extra or {}),
            ) as stream:
                for event in stream:
                    try:
                        delta = event.choices[0].delta
                        text = getattr(delta, "content", None)
                        if text:
                            yield text
                    except Exception as e:  # defensive; ignore malformed chunks
                        logger.warning("openai_client.chat_stream.chunk_error", error=str(e))

        return _call()
