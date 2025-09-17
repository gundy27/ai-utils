from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, TypeVar

import backoff
import httpx
import structlog
from pydantic import BaseModel, ValidationError

logger = structlog.get_logger(__name__)


class ErrorResponse(BaseModel):
    error_code: str | None = None
    message: str
    details: dict[str, Any] | None = None
    status: int
    retry_after: float | None = None


class RestClientError(RuntimeError):
    def __init__(self, error: ErrorResponse):
        super().__init__(error.message)
        self.error = error


@dataclass
class OAuth2Config:
    token_url: str
    client_id: str
    client_secret: str
    scopes: list[str] | None = None


class OAuth2Client:
    def __init__(
        self, config: OAuth2Config, transport: httpx.BaseTransport | None = None
    ):
        self._config = config
        self._client = httpx.Client(transport=transport, timeout=30)
        self._token: str | None = None
        self._expires_at: float = 0.0

    def _fetch_token(self) -> None:
        data = {
            "grant_type": "client_credentials",
            "client_id": self._config.client_id,
            "client_secret": self._config.client_secret,
        }
        if self._config.scopes:
            data["scope"] = " ".join(self._config.scopes)
        r = self._client.post(self._config.token_url, data=data)
        r.raise_for_status()
        payload = r.json()
        self._token = payload.get("access_token")
        expires_in = int(payload.get("expires_in", 3600))
        # clock-skew safety margin
        self._expires_at = time.time() + max(0, expires_in - 60)

    def get_token(self) -> str:
        if not self._token or time.time() >= self._expires_at:
            self._fetch_token()
        assert self._token is not None
        return self._token


T = TypeVar("T", bound=BaseModel)


def _is_retryable(status: int | None, exc: Exception | None) -> bool:
    if status is not None and status in {429}:
        return True
    if status is not None and 500 <= status < 600:
        return True
    if exc is not None and isinstance(
        exc, httpx.TimeoutException | httpx.TransportError
    ):
        return True
    return False


class RestClient:
    def __init__(
        self,
        base_url: str,
        oauth2: OAuth2Client | None = None,
        default_headers: dict[str, str] | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._oauth2 = oauth2
        self._default_headers = default_headers or {}
        self._client = httpx.Client(
            base_url=self._base_url, timeout=timeout, transport=transport
        )

    def _auth_header(self) -> dict[str, str]:
        if not self._oauth2:
            return {}
        return {"Authorization": f"Bearer {self._oauth2.get_token()}"}

    def _error(self, r: httpx.Response) -> RestClientError:
        retry_after = None
        if "retry-after" in r.headers:
            try:
                retry_after = float(r.headers.get("retry-after", "0"))
            except Exception:
                retry_after = None
        try:
            data = r.json()
            message = data.get("message") or data.get("error") or r.text
            code = data.get("code") or data.get("error_code")
            details = (
                data.get("details") if isinstance(data.get("details"), dict) else None
            )
        except Exception:
            message = r.text
            code = None
            details = None
        return RestClientError(
            ErrorResponse(
                error_code=str(code) if code is not None else None,
                message=message,
                details=details,
                status=r.status_code,
                retry_after=retry_after,
            )
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        response_model: type[T] | None = None,
        retry_non_idempotent: bool = False,
    ) -> T | dict[str, Any]:
        url = path if path.startswith("/") else f"/{path}"

        def _do() -> httpx.Response:
            req_headers = {
                **self._default_headers,
                **(headers or {}),
                **self._auth_header(),
            }
            logger.info(
                "rest.request",
                method=method,
                url=url,
                params=bool(params),
                has_json=bool(json),
            )
            try:
                r = self._client.request(
                    method, url, params=params, json=json, headers=req_headers
                )
            except Exception as e:
                logger.warning(
                    "rest.transport_error", method=method, url=url, error=str(e)
                )
                raise
            logger.info("rest.response", method=method, url=url, status=r.status_code)
            if r.status_code >= 400:
                raise self._error(r)
            return r

        @backoff.on_exception(  # type: ignore[misc]
            backoff.expo,
            (RestClientError, httpx.TimeoutException, httpx.TransportError),
            giveup=lambda e: not _is_retryable(
                getattr(getattr(e, "error", None), "status", None), e
            ),
            max_time=60,
            on_backoff=lambda d: logger.warning(
                "rest.retry", method=method, url=url, wait_s=int(d["wait"])
            ),
        )
        def _call() -> httpx.Response:
            return _do()

        # Guard for non-idempotent methods
        if (
            method.upper() not in {"GET", "HEAD", "OPTIONS"}
            and not retry_non_idempotent
        ):
            try:
                r = _do()
            except RestClientError as e:
                raise e
        else:
            r = _call()

        data = (
            r.json()
            if r.headers.get("content-type", "").startswith("application/json")
            else {}
        )
        if response_model is not None:
            try:
                return response_model.model_validate(data)
            except ValidationError as ve:
                raise RestClientError(
                    ErrorResponse(
                        error_code="validation_error",
                        message="Response validation failed",
                        details={"errors": ve.errors()},
                        status=502,
                    )
                ) from ve
        return data

    # Public methods
    def get(self, path: str, **kwargs: Any):
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any):
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any):
        return self._request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any):
        return self._request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any):
        return self._request("DELETE", path, **kwargs)
