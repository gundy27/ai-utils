from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..rbac.middleware import rbac_middleware
from ..rbac.models import Permission
from ..audit.models import (
    AuditEvent,
    AuditEventType,
    AuditQuery,
    AuditQueryResponse,
    AuditResult,
)
from ..audit.storage import audit_storage

router = APIRouter()


class AuditStatsResponse(BaseModel):
    """Response for audit statistics."""

    total_events: int
    successful_events: int
    failed_events: int
    unique_actors: int
    unique_resources: int


@router.get("/logs", response_model=AuditQueryResponse)
async def get_logs(
    tenant_id: str,
    event_types: str | None = None,
    results: str | None = None,
    actor_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    search_text: str | None = None,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "timestamp",
    sort_order: str = "desc",
    request: Request = None,
) -> AuditQueryResponse:
    """Retrieve audit logs with filtering and pagination."""
    # RBAC: Require AUDIT_READ permission for the target tenant
    user = await rbac_middleware.validate_request(
        request, Permission.AUDIT_READ, tenant_id
    )

    # Parse query parameters
    query = AuditQuery(
        tenant_id=tenant_id,
        event_types=AuditEventType(event_types.split(",")) if event_types else None,
        results=AuditResult(results.split(",")) if results else None,
        actor_id=actor_id,
        resource_type=resource_type,
        resource_id=resource_id,
        start_time=start_time,
        end_time=end_time,
        search_text=search_text,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Query audit storage
    response = audit_storage.query_events(query)
    return response


@router.get("/stats", response_model=AuditStatsResponse)
async def get_stats(
    tenant_id: str,
    days: int = 30,
    request: Request = None,
) -> AuditStatsResponse:
    """Get audit statistics for a tenant."""
    # RBAC: Require AUDIT_READ permission for the target tenant
    user = await rbac_middleware.validate_request(
        request, Permission.AUDIT_READ, tenant_id
    )

    stats = audit_storage.get_tenant_stats(tenant_id, days)
    return AuditStatsResponse(**stats)


@router.get("/export")
async def export_logs(
    tenant_id: str,
    format: str = "json",
    request: Request = None,
) -> str:
    """Export audit logs for a tenant."""
    # RBAC: Require AUDIT_READ permission for the target tenant
    user = await rbac_middleware.validate_request(
        request, Permission.AUDIT_READ, tenant_id
    )

    # Export audit data
    exported_data = audit_storage.export_events(tenant_id, format)
    return exported_data
