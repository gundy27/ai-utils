# Authentication & Secrets Service - Requirements and Implementation Plan

This document captures goals, requirements, architecture, API spec, libraries, and phased plan.

## Goals

- Centralize authentication and secrets management
- SOC2, HIPAA, GDPR alignment
- API-first, language-agnostic service with thin SDKs
- Multi-tenant, extensible, policy-driven authorization

## Architecture Overview

- FastAPI service (Python), OpenAPI-first
- Secrets providers: AWS Secrets Manager, Vault, Env (pluggable)
- Auth: JWT issue/validate; OAuth2.1 (client credentials, auth code + PKCE, token exchange)
- Authorization: RBAC + policy-as-code (OPA/casbin/oso)
- Storage: Postgres (tenants, audit), Redis (caches)
- Observability: Prometheus metrics, OTEL tracing, structured logs

## API (selected)

- POST /secrets/fetch { tenant_id, scope, name, version? } -> { value, metadata }
- POST /secrets/rotate { tenant_id, scope, name, ... } -> { previous_version, new_version, status }
- POST /auth/jwt/issue { subject, tenant_id, scopes, audience, ttl_s } -> { access_token, ... }
- POST /auth/jwt/validate { token, audience? } -> { active, claims?, error? }
- POST /auth/oauth/token { grant_type=..., ... } -> { access_token, ... }
- GET /audit/logs { filters } -> { items }
- GET /.well-known/jwks.json -> JWKS

## Libraries

- fastapi, pydantic, httpx, backoff, structlog, uvicorn
- authlib or custom flows; pyjwt/python-jose, cryptography
- boto3 (AWS SM), hvac (Vault), redis, prometheus-client, opentelemetry

## Multi-tenancy

- Per-tenant config: providers, IdP, policies
- Namespaced scopes: tenant/project/env/resource
- Namespaced caches; strict tenant checks

## Security & Compliance

- No secret values in logs; TLS end-to-end; RBAC least-privilege
- Audit every secret fetch/rotate and token issue/validate
- Key rotation (JWT + providers); backups and DR

## Caching

- L1 in-process, L2 Redis; TTLs; negative cache for 404s

## Phased Plan

- Phase 1: AWS SM + Env providers, fetch/rotate APIs, JWT validate/issue (basic), RBAC minimal, metrics/logs/rate limits, Python SDK
- Phase 2: Vault provider, OAuth2 flows + Token Exchange, JWKS rotation, policy engine, CLI, production DB/Redis
- Phase 3: Advanced audit search, per-tenant policy bundles, SDKs (TS/Go), mTLS, enterprise features

## Example Scenarios

- End-user login with Auth Code + PKCE -> issue platform JWT
- Agent delegated access via Token Exchange -> scoped token with chain-of-custody
- Fetch secret by scope/version -> policy check -> provider -> audit -> return
- Validate JWT for protected route -> JWKS cache -> inject claims
- Rotate secret -> provider op -> cache invalidation -> audit -> return
