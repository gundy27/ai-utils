# Auth Secrets Service - Import Reference

## Quick Import Guide

### Core JWT Functions

```python
from app.auth.jwt_service import issue_jwt, validate_jwt
from app.auth.keys import get_kid, get_private_key, get_public_pem
```

### Provider Classes

```python
from app.providers.base import SecretsProvider, SecretRef
from app.providers.env import EnvSecretsProvider
from app.providers.aws_sm import AwsSecretsManagerProvider
```

### Services & Models

```python
from app.oauth2.service import OAuth2Service
from app.token_exchange.service import TokenExchangeService
from app.audit.models import AuditEvent
from app.rbac.models import Role, Permission
```

### Main App

```python
from app.main import app
```

## Common Import Mistakes to Avoid

❌ **Don't use these names:**

- `JWTService` → Use `issue_jwt`, `validate_jwt` functions
- `BaseProvider` → Use `SecretsProvider`
- `EnvProvider` → Use `EnvSecretsProvider`
- `AWSSecretsManagerProvider` → Use `AwsSecretsManagerProvider`

✅ **Correct naming pattern:**

- JWT: Functions, not classes
- Providers: `{Name}SecretsProvider` format
- AWS: `Aws` prefix (not `AWS`)

## Test Status

- Total tests: 85 items
- All modules import successfully
- All test suites pass (audit, oauth2, rbac, token_exchange)
- FastAPI app creates successfully

## Last Updated

2025-01-17 - Module import verification completed
