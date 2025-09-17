# gundy_ai-rest-client

Reusable HTTP REST client with:

- OAuth2 client credentials token fetch/refresh
- Exponential backoff for 429/5xx and transport timeouts
- Structured errors with a unified shape
- Optional Pydantic response validation

## Usage

```python
from gundy_ai.http import RestClient, OAuth2Client, OAuth2Config
from pydantic import BaseModel

class Repo(BaseModel):
    full_name: str

oauth = OAuth2Client(OAuth2Config(
    token_url="https://auth.example.com/oauth/token",
    client_id="...",
    client_secret="...",
    scopes=["read"],
))

client = RestClient("https://api.example.com", oauth2=oauth)
repo = client.get("/repos/org/name", response_model=Repo)
print(repo.full_name)
```
