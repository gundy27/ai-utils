## Security & Privacy

- Keep reusable modules data-agnostic; avoid embedding client-specific data or credentials.
- Configuration pattern: `.env`-driven with typed `config.py` (Python) or `env.ts` (Node).
- Never commit secrets; ensure `.gitignore` covers `.env*`, datasets, and credentials.
- Prefer provider SDK best practices (token scopes, short-lived creds, least privilege).
- Add basic input validation and rate limiting hooks for API starters.
