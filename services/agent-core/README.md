# Agent Core

Centralized AI chatbot backend for Babble Buddy.

## Quick Start

1. Copy environment file:
   ```bash
   cp .env.example .env
   ```

2. Start services:
   ```bash
   docker-compose up -d
   ```

3. Create an app token:
   ```bash
   curl -X POST http://localhost:8000/api/v1/admin/tokens \
     -H "Authorization: Bearer change-me-in-production" \
     -H "Content-Type: application/json" \
     -d '{"name": "my-app", "description": "My application"}'
   ```

4. Send a chat message:
   ```bash
   curl -X POST http://localhost:8000/api/v1/chat \
     -H "Authorization: Bearer <your-app-token>" \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello!"}'
   ```

## Local Development (without Docker)

1. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

2. Start PostgreSQL and set `DATABASE_URL`

3. Run the server:
   ```bash
   uvicorn app.main:app --reload
   ```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/chat` | POST | Send chat message |
| `/api/v1/chat/stream` | POST | Stream chat response (SSE) |
| `/api/v1/admin/tokens` | POST | Create app token |
| `/api/v1/admin/tokens` | GET | List app tokens |
| `/api/v1/admin/tokens/{id}` | DELETE | Revoke app token |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3.2` | Model to use |
| `RATE_LIMIT_PER_MINUTE` | `60` | Rate limit per token |
| `ADMIN_API_KEY` | `change-me-in-production` | Admin API key for token management |
