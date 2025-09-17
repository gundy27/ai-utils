# Auth & Secrets Service

FastAPI-based, API-first service for authentication (JWT/OAuth2.1) and secrets management with RBAC (Role-Based Access Control).

## Features

- **Multi-tenant secrets management** with AWS Secrets Manager and Environment providers
- **JWT-based authentication** with RS256 signing and JWKS endpoint
- **Role-Based Access Control (RBAC)** with tenant isolation
- **Comprehensive audit logging** with 28 event types for compliance
- **Rate limiting** and structured logging
- **Prometheus metrics** for observability
- **Advanced audit querying** with filtering, pagination, and export

## RBAC Roles & Permissions

### Roles

- `tenant_admin`: Full access to tenant resources
- `tenant_user`: Read/write access to secrets, validate JWTs
- `tenant_readonly`: Read-only access to secrets
- `system_admin`: Full system access across all tenants
- `service_account`: Limited access for automated services

### Permissions

- `secret:read`, `secret:write`, `secret:rotate`, `secret:delete`
- `jwt:issue`, `jwt:validate`, `oauth:token`
- `audit:read`, `audit:write`
- `tenant:manage`, `user:manage`, `system:admin`

## Quick Start

Run locally:

```bash
python3 -m poetry install
python3 -m poetry run uvicorn app.main:app --host 127.0.0.1 --port 8011 --reload
```

## API Endpoints

### Secrets

- `POST /secrets/fetch` - Retrieve secret (requires `secret:read`)
- `POST /secrets/rotate` - Rotate secret (requires `secret:rotate`)
- `POST /secrets/list` - List secrets for tenant/scope (requires `secret:read`, Vault provider only)

### Authentication

- `POST /auth/jwt/issue` - Issue JWT token (requires `jwt:issue`)
- `POST /auth/jwt/validate` - Validate JWT token (requires `jwt:validate`)
- `POST /auth/oauth/token` - OAuth2 token endpoint (requires `oauth:token`)

### OAuth2

- `GET /oauth2/authorize` - OAuth2 authorization endpoint
- `POST /oauth2/token` - OAuth2 token endpoint
- `POST /oauth2/clients` - Register OAuth2 client (requires `client:manage`)
- `GET /oauth2/clients` - List OAuth2 clients (requires `client:read`)
- `GET /oauth2/pkce/challenge` - Generate PKCE challenge

### Token Exchange & Delegation

- `POST /token-exchange/token` - Exchange token for different scopes/audience
- `POST /token-exchange/delegate` - Delegate token to microservices (requires `delegate:token`)
- `POST /token-exchange/impersonate` - Impersonate user (requires `impersonate:user`)
- `POST /token-exchange/policies` - Create delegation policy (requires `delegation_policy:manage`)
- `GET /token-exchange/policies` - List delegation policies (requires `delegation_policy:read`)
- `GET /token-exchange/audit/events` - Get token exchange audit events (requires `audit:read`)
- `GET /token-exchange/audit/stats` - Get token exchange statistics (requires `audit:read`)

### Audit

- `GET /audit/logs` - Retrieve audit logs with filtering (requires `audit:read`)
- `GET /audit/stats` - Get audit statistics for tenant (requires `audit:read`)
- `GET /audit/export` - Export audit logs as JSON/CSV (requires `audit:read`)

### System

- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `GET /.well-known/jwks.json` - JWKS for JWT validation

## Configuration

Set environment variables:

```bash
# Provider selection
export SECRETS_PROVIDER=aws  # or 'env'

# JWT settings
export JWT_ISSUER=https://auth.local

# AWS (if using AWS Secrets Manager)
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_DEFAULT_REGION=us-east-1

# Environment provider (if using env)
export ENV_SECRET__acme_prod_app__API_KEY__v1=your-secret-value
```

## Testing

Run tests:

```bash
python3 -m poetry run pytest tests/ -v
```

Run RBAC demo:

```bash
python3 -m poetry run python examples/rbac_demo.py
```

Run audit logging demo:

```bash
python3 -m poetry run python examples/audit_demo.py
```

## Audit Logging

The service provides comprehensive audit logging for compliance with SOC2, HIPAA, and GDPR requirements:

### Event Types (28 total)

- **Authentication**: login, logout, token issued/validated/invalid/expired
- **Secret Management**: fetch, rotate, delete (success/failure)
- **Access Control**: granted, denied, permission checks, tenant access
- **Administrative**: user/tenant creation/updates, role assignments
- **System**: startup, shutdown, configuration changes, errors

### Features

- **Thread-safe storage** with configurable retention (default: 7 years)
- **Advanced querying** with filtering by event type, result, actor, resource, time range
- **Pagination support** for large result sets
- **Statistics and analytics** per tenant
- **Export capabilities** (JSON/CSV) for compliance reporting
- **Automatic HTTP request logging** via middleware
- **Custom event logging** for business-specific actions

### Query Examples

```bash
# Get all events for a tenant
GET /audit/logs?tenant_id=acme-corp

# Filter by event type
GET /audit/logs?tenant_id=acme-corp&event_types=secret.fetch,auth.token_issued

# Filter by result
GET /audit/logs?tenant_id=acme-corp&results=success,failure

# Filter by actor
GET /audit/logs?tenant_id=acme-corp&actor_id=user-123

# Time range filtering
GET /audit/logs?tenant_id=acme-corp&start_time=2024-01-01&end_time=2024-01-31

# Pagination
GET /audit/logs?tenant_id=acme-corp&page=2&page_size=25

# Export data
GET /audit/export?tenant_id=acme-corp&format=json
GET /audit/export?tenant_id=acme-corp&format=csv
```

## HashiCorp Vault Integration

The service now supports HashiCorp Vault as a secrets provider with multiple authentication methods:

### Supported Authentication Methods

1. **Token Authentication**

   ```bash
   export VAULT_ADDR="https://vault.example.com"
   export VAULT_AUTH_METHOD="token"
   export VAULT_TOKEN="hvs.xxxxxxxxxxxxxxxxxxxxxxxxx"
   export VAULT_MOUNT_POINT="secret"
   ```

2. **AppRole Authentication**

   ```bash
   export VAULT_AUTH_METHOD="approle"
   export VAULT_ROLE_ID="your-role-id"
   export VAULT_SECRET_ID="your-secret-id"
   export VAULT_APPROLE_MOUNT="approle"
   ```

3. **Kubernetes Authentication**

   ```bash
   export VAULT_AUTH_METHOD="kubernetes"
   export VAULT_K8S_ROLE="your-k8s-role"
   export VAULT_K8S_TOKEN_PATH="/var/run/secrets/kubernetes.io/serviceaccount/token"
   export VAULT_K8S_MOUNT="kubernetes"
   ```

4. **AWS IAM Authentication**
   ```bash
   export VAULT_AUTH_METHOD="aws"
   export VAULT_AWS_ROLE="your-aws-role"
   export AWS_ACCESS_KEY_ID="your-access-key"
   export AWS_SECRET_ACCESS_KEY="your-secret-key"
   export AWS_DEFAULT_REGION="us-east-1"
   export VAULT_AWS_MOUNT="aws"
   ```

### Vault Configuration

Set the provider to use Vault:

```bash
export SECRETS_PROVIDER="vault"
```

### Secret Path Structure

Secrets are stored in Vault using the path structure:

```
{mount_point}/data/{tenant_id}/{scope}/{name}
```

For example: `secret/data/acme-corp/prod/api-key`

### Vault-Specific Features

- **Version Support**: Access specific secret versions using the `version` parameter
- **Secret Listing**: List all secrets for a tenant/scope
- **Secret Rotation**: Rotate secrets with audit trail
- **Secret Deletion**: Soft delete secrets (mark for deletion)
- **Metadata Tracking**: Full metadata including creation time, versions, etc.

### Example Usage

```python
# Set up environment
os.environ["SECRETS_PROVIDER"] = "vault"
os.environ["VAULT_ADDR"] = "https://vault.example.com"
os.environ["VAULT_AUTH_METHOD"] = "token"
os.environ["VAULT_TOKEN"] = "your-token"

# Use the service
from app.providers.dispatcher import get_provider
from app.providers.base import SecretRef

provider = get_provider()
ref = SecretRef("acme-corp", "prod", "api-key")
value, metadata = provider.get_secret(ref)
```

### Demo Script

Run the Vault demo to see all features:

```bash
python examples/vault_demo.py
```

## OAuth2 Authorization Flows

The service now supports comprehensive OAuth2 authorization flows with PKCE for secure authentication:

### Supported Grant Types

1. **Authorization Code Flow with PKCE** (Recommended for web and mobile apps)
2. **Client Credentials Flow** (For server-to-server authentication)
3. **Refresh Token Flow** (For token renewal)

### Client Types

- **Public Clients**: Cannot securely store secrets (mobile apps, SPAs)
- **Confidential Clients**: Can securely store secrets (server-side applications)

### OAuth2 Flow Example

#### 1. Register a Client

```bash
curl -X POST http://localhost:8011/oauth2/clients \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Web App",
    "description": "Web application client",
    "client_type": "public",
    "redirect_uris": ["https://myapp.com/callback"],
    "allowed_scopes": ["read", "write"]
  }'
```

Response:

```json
{
  "client_id": "client_abc123",
  "client_secret": null,
  "client_type": "public",
  "name": "My Web App",
  "redirect_uris": ["https://myapp.com/callback"],
  "allowed_scopes": ["read", "write"],
  "tenant_id": "your-tenant"
}
```

#### 2. Generate PKCE Challenge (for public clients)

```bash
curl -X GET http://localhost:8011/oauth2/pkce/challenge
```

Response:

```json
{
  "code_verifier": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
  "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
  "code_challenge_method": "S256"
}
```

#### 3. Authorization Request

Direct user to authorization URL:

```
https://localhost:8011/oauth2/authorize?
  client_id=client_abc123&
  redirect_uri=https://myapp.com/callback&
  response_type=code&
  scope=read+write&
  state=random_state_value&
  code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM&
  code_challenge_method=S256
```

#### 4. Token Exchange

```bash
curl -X POST http://localhost:8011/oauth2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&
      code=AUTH_CODE_FROM_CALLBACK&
      redirect_uri=https://myapp.com/callback&
      client_id=client_abc123&
      code_verifier=dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
```

Response:

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "refresh_token_xyz789",
  "scope": "read write"
}
```

#### 5. Refresh Token

```bash
curl -X POST http://localhost:8011/oauth2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token&
      refresh_token=refresh_token_xyz789&
      client_id=client_abc123"
```

### Client Credentials Flow (Server-to-Server)

```bash
curl -X POST http://localhost:8011/oauth2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&
      client_id=confidential_client_id&
      client_secret=client_secret&
      scope=read"
```

### Security Features

- **PKCE (Proof Key for Code Exchange)**: Prevents authorization code interception attacks
- **State Parameter**: Prevents CSRF attacks
- **Token Expiration**: Access tokens expire in 1 hour by default
- **Refresh Token Rotation**: New refresh token issued on each use
- **Audit Logging**: All OAuth2 events are logged for compliance
- **RBAC Integration**: Client management requires appropriate permissions

### OAuth2 Permissions

- `client:read` - View OAuth2 clients
- `client:write` - Create/update OAuth2 clients
- `client:manage` - Full client management (create, update, delete)

## Token Exchange & Delegation

The service now supports comprehensive token exchange and delegation for microservices architectures and delegated access patterns:

### Supported Exchange Types

1. **Token Exchange** - Exchange tokens for different scopes/audiences
2. **Token Delegation** - Delegate tokens to microservices with scope reduction
3. **User Impersonation** - Admin impersonation for support operations

### Token Exchange Example

#### 1. Exchange Token for Different Scopes

```bash
curl -X POST http://localhost:8011/token-exchange/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=urn:ietf:params:oauth:grant-type:token-exchange&
      subject_token=YOUR_ACCESS_TOKEN&
      subject_token_type=urn:ietf:params:oauth:token-type:access_token&
      requested_token_type=urn:ietf:params:oauth:token-type:access_token&
      audience=api.example.com&
      scope=read"
```

Response:

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "issued_token_type": "urn:ietf:params:oauth:token-type:access_token",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "read"
}
```

#### 2. Delegate Token to Microservice

```bash
curl -X POST http://localhost:8011/token-exchange/delegate \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_token": "YOUR_ACCESS_TOKEN",
    "target_audience": "microservice.example.com",
    "target_scopes": ["read"],
    "delegation_chain": ["token1", "token2"],
    "expires_in": 3600,
    "metadata": {
      "delegation_reason": "Microservice communication",
      "source_service": "api-gateway"
    }
  }'
```

Response:

```json
{
  "delegated_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "read",
  "audience": "microservice.example.com",
  "delegation_chain": ["token1", "token2", "delegated_token"]
}
```

#### 3. Impersonate User (Admin Operation)

```bash
curl -X POST http://localhost:8011/token-exchange/impersonate \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_token": "ADMIN_ACCESS_TOKEN",
    "target_user_id": "user123",
    "target_tenant_id": "tenant456",
    "impersonation_reason": "Admin support request",
    "target_scopes": ["admin:read", "admin:write"],
    "expires_in": 1800
  }'
```

Response:

```json
{
  "impersonation_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 1800,
  "scope": "admin:read admin:write",
  "impersonated_user_id": "user123",
  "impersonated_tenant_id": "tenant456",
  "impersonation_reason": "Admin support request"
}
```

### Delegation Policy Management

#### Create Delegation Policy

```bash
curl -X POST http://localhost:8011/token-exchange/policies \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": "microservice-delegation",
    "name": "Microservice Delegation Policy",
    "description": "Allow API Gateway to delegate to microservices",
    "source_scopes": ["read", "write"],
    "target_scopes": ["read"],
    "allowed_audiences": ["microservice.example.com"],
    "max_delegation_depth": 3,
    "requires_impersonation_permission": false,
    "conditions": {
      "time_restriction": "business_hours",
      "ip_whitelist": ["192.168.1.0/24"]
    }
  }'
```

#### List Delegation Policies

```bash
curl -X GET http://localhost:8011/token-exchange/policies \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Security Features

- **Delegation Policies** - Fine-grained control over token delegation
- **Scope Reduction** - Delegated tokens can only have subset of original scopes
- **Delegation Chain Tracking** - Prevents delegation loops and tracks token lineage
- **Audit Logging** - Complete audit trail for all token operations
- **Time Limits** - Configurable expiration for delegated tokens
- **Impersonation Controls** - Admin-only user impersonation with reason tracking

### Token Exchange Permissions

- `delegate:token` - Delegate tokens to other services
- `impersonate:user` - Impersonate other users (admin only)
- `delegation_policy:read` - View delegation policies
- `delegation_policy:write` - Create/update delegation policies
- `delegation_policy:manage` - Full delegation policy management

### Use Cases

1. **Microservices Architecture** - API Gateway delegates tokens to downstream services
2. **Scope Reduction** - Reduce token permissions for less privileged services
3. **Service-to-Service Auth** - Secure communication between microservices
4. **Admin Support** - Impersonate users for troubleshooting and support
5. **Delegated Access** - Allow services to act on behalf of users with reduced permissions

## Developer Reference

### Import Patterns

When importing modules, use these correct names:

```python
# JWT functions (not classes)
from app.auth.jwt_service import issue_jwt, validate_jwt
from app.auth.keys import get_kid, get_private_key, get_public_pem

# Provider classes
from app.providers.base import SecretsProvider, SecretRef
from app.providers.env import EnvSecretsProvider  # not EnvProvider
from app.providers.aws_sm import AwsSecretsManagerProvider  # not AWSSecretsManagerProvider

# Services & Models
from app.oauth2.service import OAuth2Service
from app.token_exchange.service import TokenExchangeService
from app.audit.models import AuditEvent
from app.rbac.models import Role, Permission
```

**Common mistakes to avoid:**

- `JWTService` → Use `issue_jwt`, `validate_jwt` functions
- `BaseProvider` → Use `SecretsProvider`
- `EnvProvider` → Use `EnvSecretsProvider`
- `AWSSecretsManagerProvider` → Use `AwsSecretsManagerProvider`

See `IMPORT_REFERENCE.md` for complete details.

## Next Steps

- [x] ✅ **RBAC implementation** - Complete with tenant isolation
- [x] ✅ **Comprehensive audit logging** - 28 event types, querying, export
- [x] ✅ **HashiCorp Vault provider** - Multiple auth methods, full CRUD operations
- [x] ✅ **OAuth2 flows** - Authorization Code + PKCE, Client Credentials, Refresh Token
- [x] ✅ **Token Exchange & Delegation** - Microservices delegation, impersonation, policy management
- [ ] Add policy engine integration
- [ ] Create Python SDK
