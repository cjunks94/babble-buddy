# Babble Buddy - Project Plan

## Vision

An embeddable AI chatbot agent (like Clippy) that can be dropped into any application. It connects to a centralized, self-hosted AI backend (Ollama or other providers) to assist users with context-aware tasks.

**Example Use Case:** Helping users build SQL queries in the Exportee app.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Host Applications                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Exportee   │  │   App 2     │  │   App N     │              │
│  │             │  │             │  │             │              │
│  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │              │
│  │ │ Widget  │ │  │ │ Widget  │ │  │ │ Widget  │ │              │
│  │ └────┬────┘ │  │ └────┬────┘ │  │ └────┬────┘ │              │
│  └──────┼──────┘  └──────┼──────┘  └──────┼──────┘              │
└─────────┼────────────────┼────────────────┼─────────────────────┘
          │                │                │
          │  App Token A   │  App Token B   │  App Token N
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Agent Core (Python)                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                      API Gateway                          │   │
│  │  • Token Authentication & Rate Limiting                   │   │
│  │  • Request Routing                                        │   │
│  │  • Context Management                                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   Provider Abstraction                    │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                │   │
│  │  │  Ollama  │  │ OpenAI   │  │  Future  │                │   │
│  │  │ Provider │  │ Provider │  │ Provider │                │   │
│  │  └──────────┘  └──────────┘  └──────────┘                │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AI Providers (External)                      │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │    Ollama    │  │   OpenAI     │                             │
│  │ (Self-hosted)│  │   (Cloud)    │                             │
│  └──────────────┘  └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Sub-Services

### 1. Agent Core (Python) - `services/agent-core/`
Centralized backend service that handles all AI interactions.

**Responsibilities:**
- App token generation and authentication
- Rate limiting per app/token
- Chat session management
- Provider abstraction (Ollama, OpenAI, etc.)
- Context/system prompt management per app
- Streaming responses

### 2. Widget (TypeScript) - `packages/widget/`
Embeddable frontend component that drops into host applications.

**Responsibilities:**
- Lightweight, framework-agnostic chat UI
- App token authentication
- Context passing from host app
- Streaming message display
- Customizable appearance

---

## MVP Phases

### Phase 1: Agent Core MVP (Current Focus)

**Goal:** Deployable backend that can receive chat messages and return AI responses via Ollama.

#### 1.1 Core Features

| Feature | Priority | Description |
|---------|----------|-------------|
| Health endpoint | P0 | Basic `/health` endpoint for deployment verification |
| Chat endpoint | P0 | `POST /api/v1/chat` - Send message, get response |
| Ollama provider | P0 | Connect to Ollama API, send prompts, receive responses |
| App token auth | P0 | Validate app tokens on requests |
| Token management | P1 | CLI or admin endpoint to generate/revoke tokens |
| Streaming | P1 | SSE streaming for chat responses |
| System prompts | P2 | Per-app customizable system prompts |
| Conversation history | P2 | Maintain context within a session |

#### 1.2 Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Framework | FastAPI | Async, modern, great OpenAPI docs |
| Database | PostgreSQL | Familiar, production-ready, stores app tokens |
| ORM | SQLAlchemy + asyncpg | Async support, well-documented |
| Ollama client | Raw HTTP (httpx) | Flexibility, async support |
| Auth | Bearer tokens (DB-stored) | Tokens stored in PostgreSQL with metadata |
| Sessions | In-memory | Simple for MVP, no persistence needed |
| Rate limiting | slowapi | Basic per-token limits from day one |
| Config | Environment variables | Standard, 12-factor app compliant |
| Ollama endpoint | Configurable | `OLLAMA_HOST` env var, defaults to `localhost:11434` |

#### 1.3 API Design

```
POST /api/v1/chat
Headers:
  Authorization: Bearer <app_token>
  X-App-Context: <optional JSON context from host app>
Body:
  {
    "message": "Help me write a SQL query to get all users",
    "session_id": "optional-session-id",
    "context": {
      "app": "exportee",
      "schema": ["users", "orders"],  // Optional app-specific context
    }
  }
Response:
  {
    "response": "Sure! Here's a query...",
    "session_id": "abc123"
  }

GET /api/v1/chat/stream
  Same as above but returns SSE stream

GET /health
Response: { "status": "ok", "ollama": "connected" }
```

#### 1.4 Directory Structure (Agent Core)

```
services/agent-core/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry
│   ├── config.py            # Settings from env
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── chat.py      # Chat endpoints
│   │   │   ├── health.py    # Health check
│   │   │   └── tokens.py    # Token management endpoints
│   │   └── deps.py          # Dependencies (auth, rate limit, etc.)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── auth.py          # Token validation
│   │   ├── rate_limit.py    # Rate limiting config
│   │   └── sessions.py      # Session management (in-memory)
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py      # Async SQLAlchemy setup
│   │   └── models.py        # AppToken model
│   └── providers/
│       ├── __init__.py
│       ├── base.py          # Abstract provider interface
│       └── ollama.py        # Ollama implementation
├── alembic/                  # Database migrations
│   └── ...
├── tests/
│   └── ...
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml        # Includes PostgreSQL
└── README.md
```

---

### Phase 2: Widget MVP (After Agent Core)

**Goal:** Minimal embeddable chat widget that connects to Agent Core.

#### 2.1 Core Features

| Feature | Priority | Description |
|---------|----------|-------------|
| Chat UI | P0 | Simple message list + input |
| API integration | P0 | Connect to Agent Core with app token |
| Embed script | P0 | Single `<script>` tag to embed |
| Streaming display | P1 | Show streamed responses in real-time |
| Theming | P2 | CSS variables for customization |
| Context injection | P2 | Host app can pass context to widget |

#### 2.2 Embed API (Target)

```html
<!-- Drop this in any app -->
<script src="https://your-domain.com/babble-buddy.js"></script>
<script>
  BabbleBuddy.init({
    appToken: 'app_xxxxx',
    apiUrl: 'https://agent-core.your-domain.com',
    position: 'bottom-right',  // Optional
    context: {                  // Optional - app-specific context
      app: 'exportee',
      schema: window.EXPORTEE_SCHEMA
    }
  });
</script>
```

---

### Phase 3: Enhanced Features (Future)

- Multi-provider support (OpenAI, Anthropic, etc.)
- Conversation history persistence (database)
- Admin dashboard for token management
- Analytics and usage tracking
- Custom tools/functions per app
- RAG integration for documentation

---

## Decisions Made

| Question | Decision |
|----------|----------|
| Token storage | PostgreSQL database |
| Session persistence | In-memory only (MVP) |
| Rate limiting | Basic per-token limits from day one |
| Ollama endpoint | Fully configurable via `OLLAMA_HOST` env var |

---

## Next Steps

1. [x] Review and approve this plan
2. [x] Answer open questions
3. [ ] Begin Agent Core MVP implementation
   - [ ] Set up Python project structure (pyproject.toml, docker-compose)
   - [ ] Database setup (PostgreSQL, SQLAlchemy models, Alembic)
   - [ ] Implement health endpoint
   - [ ] Implement Ollama provider
   - [ ] Implement chat endpoint
   - [ ] Add token authentication + rate limiting
   - [ ] Token management endpoints (create/list/revoke)
