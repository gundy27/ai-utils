## Starter Templates

Use these starters as cookiecutter-style templates or `npx create-...` scaffolds. Keep them in `templates/` and evolve them as best practices improve.

### LLM API Server

- **Stack**: FastAPI + LangChain (or LlamaIndex) wrapper + logging + monitoring.
- **Goals**: Production-ready API surface, request/response logging, tracing, configurable model backends.
- **Includes**: `.env` config pattern, health checks, rate limiting hooks, basic eval endpoint.

### Chatbot Webapp

- **Stack**: Next.js + Supabase (auth/storage) + OpenAI API (or provider-agnostic).
- **Goals**: Authenticated chat UI, session history, server actions / edge functions, RSC-friendly data flow.
- **Includes**: Minimal theming, analytics hook, env-configured providers.

### Evaluation Harness

- **Stack**: Python CLI + dataset loader + metrics + report generator.
- **Goals**: Reproducible evals for prompts/models/tools, exportable reports (Markdown/HTML/CSV).
- **Includes**: Dataset adapters, metric registry, simple runner with YAML config.

Placeholders live under `templates/`:

- `templates/api-service-starter/`
- `templates/webapp-starter/`
- `templates/cli-starter/` (use for the evaluation harness CLI)
