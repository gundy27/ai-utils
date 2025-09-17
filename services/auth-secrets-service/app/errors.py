from __future__ import annotations

from fastapi.responses import JSONResponse


def error_response(
    status: int,
    code: str,
    message: str,
    details: dict | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    if request_id:
        body["error"]["request_id"] = request_id
    return JSONResponse(status_code=status, content=body)
