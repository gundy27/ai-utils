## Webapp Starter

Next.js app that proxies to the FastAPI LLM service for chat and streaming.

### Run with Docker Compose

```bash
cd templates/webapp-starter
docker compose up --build
```

Open `http://localhost:3000`. The app uses `API_URL=http://api:8001` (internal service name) to call the API.

### Local Dev (optional)

```bash
npm i
npm run dev
```

## Chatbot Webapp Starter

Stack: Next.js + Supabase + OpenAI API (provider-agnostic option recommended).

Includes

- Authenticated chat UI, session history, env-driven provider configuration.
- Hooks for analytics and edge/server action patterns.

Use as cookiecutter or copy into client repos.
