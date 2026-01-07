# Agent Core

Centralized AI chatbot backend with long-term memory for Babble Buddy widgets.

## Quick Start

```bash
# 1. Setup
cp .env.example .env

# 2. Start services
docker-compose up -d

# 3. Create an app token
curl -X POST http://localhost:8000/api/v1/admin/tokens \
  -H "Authorization: Bearer change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-app"}'

# 4. Chat!
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer <your-app-token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'
```

## API Reference

### Chat
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check + cache stats |
| `/api/v1/chat` | POST | Send message |
| `/api/v1/chat/stream` | POST | Stream response (SSE) |

### Memory
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/memory` | POST | Store a memory |
| `/api/v1/memory/search` | POST | Search by similarity |
| `/api/v1/memory` | DELETE | Clear memories |

### Suggestions
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/suggestions` | POST | Get context-aware prompts |

### Admin
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/admin/tokens` | POST | Create app token |
| `/api/v1/admin/tokens` | GET | List tokens |
| `/api/v1/admin/tokens/{id}` | DELETE | Revoke token |
| `/api/v1/admin/extraction/status` | GET | Pending extraction count |
| `/api/v1/admin/extraction/run` | POST | Trigger batch extraction |

### Agents (Multi-Agent Orchestration)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/admin/agents` | POST | Create an agent |
| `/api/v1/admin/agents` | GET | List agents (filter by app_id, role) |
| `/api/v1/admin/agents/{id}` | GET | Get agent details |
| `/api/v1/admin/agents/{id}` | PATCH | Update agent |
| `/api/v1/admin/agents/{id}` | DELETE | Delete agent |

> **Note:** Agent endpoints require `FEATURE_MULTI_AGENT=true`

## Authentication

**App Token** — For chat/memory endpoints:
```bash
curl -H "Authorization: Bearer bb_your-app-token" ...
```

**Admin Key** — For token management (set via `ADMIN_API_KEY`):
```bash
curl -H "Authorization: Bearer your-admin-key" ...
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| **Core** |||
| `DATABASE_URL` | — | PostgreSQL connection string |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3.2` | Chat model |
| `RATE_LIMIT_PER_MINUTE` | `60` | Requests per token per minute |
| `ADMIN_API_KEY` | `change-me-in-production` | Admin authentication |
| **Memory** |||
| `FEATURE_MEMORY` | `true` | Enable memory system |
| `MEMORY_EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model |
| `MEMORY_RECALL_LIMIT` | `5` | Max memories per request |
| `MEMORY_MIN_SIMILARITY` | `0.6` | Similarity threshold (0-1) |
| **Structured Extraction** |||
| `MEMORY_EXTRACTION_ENABLED` | `true` | Enable knowledge extraction |
| `MEMORY_EXTRACTION_INLINE` | `true` | Extract per-message (vs batch) |
| `MEMORY_EXTRACTION_MODEL` | `llama3.2` | Extraction model |
| `MEMORY_HIGH_IMPORTANCE_THRESHOLD` | `0.9` | Auto-inject threshold |
| `MEMORY_EXTRACTION_BATCH_SIZE` | `50` | Turns per batch job |
| **Performance** |||
| `MEMORY_EMBEDDING_CACHE_SIZE` | `10000` | LRU cache entries |
| `MEMORY_EMBEDDING_CACHE_TTL` | `3600` | Cache TTL (seconds) |
| **Multi-Agent** |||
| `FEATURE_MULTI_AGENT` | `false` | Enable multi-agent orchestration |
| `FEATURE_EXTERNAL_PROVIDERS` | `false` | Enable Claude/OpenAI/Gemini |
| `ENCRYPTION_KEY` | — | Fernet key for API key encryption |

## Features

### Memory System

Stores conversation context and recalls relevant information automatically.

**Requirements:**
- PostgreSQL with pgvector (`CREATE EXTENSION vector;`)
- Ollama with `nomic-embed-text` (`ollama pull nomic-embed-text`)

**How it works:**
1. On each request, relevant memories are recalled via semantic search
2. Memories are injected into the system prompt
3. Apps can store facts via `/api/v1/memory`

If pgvector is unavailable, the app starts with memory disabled.

### Structured Extraction

Extracts knowledge graph tuples from conversations (e.g., "user is allergic to shellfish").

- **Subject/predicate/object** — Atomic facts
- **Importance scoring** — Critical info (allergies) = 1.0, preferences ≤ 0.7
- **Auto-injection** — High-importance memories always included

**Scaling:**
| Mode | Config | Best for |
|------|--------|----------|
| Inline | `MEMORY_EXTRACTION_INLINE=true` | Small/medium — extracts immediately |
| Batch | `MEMORY_EXTRACTION_INLINE=false` | Scale — use scheduled jobs |

### Embedding Cache

LRU cache reduces Ollama embedding calls. Check stats via `/health`:

```json
{
  "cache": {
    "embedding": { "size": 142, "hits": 1893, "hit_rate": 0.93 }
  }
}
```

### Multi-Agent Orchestration

Route requests through multiple AI agents with different roles and providers.

**Supported Providers:**
- Ollama (self-hosted)
- Anthropic (Claude)
- OpenAI (GPT)
- Google Gemini

**Agent Roles:**
| Role | Purpose |
|------|---------|
| `leader` | Coordinates tasks, makes decisions |
| `coder` | Writes and generates code |
| `reviewer` | Reviews output, provides feedback |
| `researcher` | Gathers information |

**Orchestration Strategies:**
| Strategy | Behavior |
|----------|----------|
| `single` | Route to one specific agent |
| `leader` | Leader coordinates with specialists |
| `parallel` | Run all agents concurrently |
| `chain` | Sequential: researcher → coder → reviewer |

**Setup:**
```bash
# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Enable in .env
FEATURE_MULTI_AGENT=true
ENCRYPTION_KEY=<your-generated-key>
```

## Development

```bash
# Install
pip install -e ".[dev]"

# Run (requires PostgreSQL)
uvicorn app.main:app --reload

# Run tests
pytest -v

# Run tests with coverage
pytest --cov=app --cov-report=term-missing
```

## Testing

The test suite includes 155+ tests covering:
- Multi-agent orchestration strategies
- Memory extraction and retrieval
- API endpoint authentication
- Embedding cache performance
- Provider integrations

**Coverage:** 72%+ (enforced by CI)
