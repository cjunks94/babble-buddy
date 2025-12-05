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

### Chat
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | None | Health check |
| `/api/v1/chat` | POST | App Token | Send chat message |
| `/api/v1/chat/stream` | POST | App Token | Stream chat response (SSE) |

### Memory (requires pgvector)
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/memory` | POST | App Token | Store a memory (fact/preference/summary) |
| `/api/v1/memory/search` | POST | App Token | Search memories by semantic similarity |
| `/api/v1/memory` | DELETE | App Token | Clear memories |

### Admin
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/admin/tokens` | POST | Admin Key | Create app token |
| `/api/v1/admin/tokens` | GET | Admin Key | List app tokens |
| `/api/v1/admin/tokens/{id}` | DELETE | Admin Key | Revoke app token |

## Authentication

**App Token** - Used by your apps to access chat/memory:
```bash
curl -H "Authorization: Bearer bb_your-app-token" ...
```

**Admin Key** - Used to manage app tokens (set via `ADMIN_API_KEY` env var):
```bash
curl -H "Authorization: Bearer your-admin-key" ...
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3.2` | Model to use |
| `RATE_LIMIT_PER_MINUTE` | `60` | Rate limit per token |
| `ADMIN_API_KEY` | `change-me-in-production` | Admin API key for token management |
| `FEATURE_MEMORY` | `true` | Enable semantic memory |
| `MEMORY_EMBEDDING_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `MEMORY_RECALL_LIMIT` | `5` | Max memories to inject per request |
| `MEMORY_MIN_SIMILARITY` | `0.6` | Minimum similarity threshold |

## Memory Feature

The memory system stores conversation context and recalls relevant information automatically.

**Requirements:**
- PostgreSQL with pgvector extension (`CREATE EXTENSION vector;`)
- Ollama with `nomic-embed-text` model (`ollama pull nomic-embed-text`)

**How it works:**
1. On each chat request, relevant memories are recalled via semantic search
2. Memories are injected into the system prompt as context
3. Apps can store facts/preferences via the `/api/v1/memory` endpoint

If pgvector is not available, the app starts normally with memory disabled.

## Structured Memory Extraction

Beyond basic vector storage, the system supports **structured memory extraction** - a knowledge graph approach that extracts atomic facts from conversations.

**Features:**
- Extracts subject/predicate/object tuples (e.g., "user hates olives")
- Importance scoring (0.0-1.0) - critical info like allergies = 1.0
- Automatic injection of high-importance memories
- Expiring memories for temporary facts
- Application grouping for multi-tenant deployments

**How it works:**
1. Conversation turns are stored in a queue
2. Admin triggers batch extraction via `/api/v1/admin/extraction/run`
3. LLM extracts structured memories from conversations
4. High-importance memories (≥0.9) are always injected into prompts
5. Other memories are recalled via semantic search

**Admin Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/admin/extraction/status` | GET | Get pending turn count |
| `/api/v1/admin/extraction/run` | POST | Trigger batch extraction |

**Example extraction request:**
```bash
curl -X POST http://localhost:8000/api/v1/admin/extraction/run \
  -H "Authorization: Bearer $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"limit": 50}'
```

**Configuration:**
| Variable | Default | Description |
|----------|---------|-------------|
| `MEMORY_EXTRACTION_ENABLED` | `true` | Enable structured extraction |
| `MEMORY_EXTRACTION_MODEL` | `llama3.2` | Model for extraction |
| `MEMORY_HIGH_IMPORTANCE_THRESHOLD` | `0.9` | Always-inject threshold |
| `MEMORY_ALWAYS_INJECT_HIGH_IMPORTANCE` | `true` | Auto-inject critical memories |
| `MEMORY_EXTRACTION_BATCH_SIZE` | `50` | Max turns per batch |
