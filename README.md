# Babble Buddy

An embeddable AI chatbot agent (like Clippy) that connects to self-hosted AI backends.

## 🚀 Live Demo

Try it now!

- **Demo Page**: [babble-buddy-demo.cjunker.dev](https://babble-buddy-demo.cjunker.dev)
- **API Endpoint**: [babble-buddy-api.cjunker.dev](https://babble-buddy-api.cjunker.dev)

## Architecture

```
┌─────────────────────┐     ┌─────────────────────┐
│   Your Application  │     │   Agent Core API    │
│                     │     │   (Python/FastAPI)  │
│  ┌───────────────┐  │     │                     │
│  │ Babble Buddy  │──┼────▶│  • Token Auth       │
│  │    Widget     │  │     │  • Rate Limiting    │
│  └───────────────┘  │     │  • Session Mgmt     │
│                     │     │                     │
└─────────────────────┘     └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │      Ollama         │
                            │   (Self-hosted AI)  │
                            └─────────────────────┘
```

## Services

| Service | Description | Directory |
|---------|-------------|-----------|
| **Agent Core** | Python FastAPI backend for AI interactions | `services/agent-core/` |
| **Ollama** | Self-hosted LLM inference server | `services/ollama/` |
| **Widget** | Embeddable TypeScript chat widget | `packages/widget/` |

## Quick Start (Local)

### 1. Start Ollama

```bash
# Option A: Use local Ollama
ollama serve
ollama pull llama3.2

# Option B: Use Docker
cd services/ollama
docker build -t babble-ollama .
docker run -p 11434:11434 babble-ollama
```

### 2. Start Agent Core

```bash
cd services/agent-core
cp .env.example .env
docker-compose up -d
```

### 3. Create an App Token

```bash
curl -X POST http://localhost:8000/api/v1/admin/tokens \
  -H "Authorization: Bearer change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-app"}'
```

### 4. Start Widget Dev Server

```bash
cd packages/widget
npm install
npm run dev
```

### 5. Test

Open `http://localhost:5173` and chat!

---

## Deploy to Railway

### Step 1: Create Project & Database

1. Go to [railway.app](https://railway.app) → **New Project**
2. Click **New** → **Database** → **PostgreSQL**

### Step 2: Deploy Ollama

1. Click **New** → **GitHub Repo** → Select `babble-buddy`
2. Set **Root Directory**: `services/ollama`
3. Set environment variable:
   - `OLLAMA_MODEL` = `llama3.2` (or your preferred model)
4. **Add a Volume** (recommended):
   - Go to Settings → Volumes
   - Mount path: `/root/.ollama`
   - This persists models between deploys
5. Wait for deploy (first time takes 3-5 min to pull model)
6. Copy the Ollama service URL (e.g., `https://ollama-xxx.railway.app`)

### Step 3: Deploy Agent Core

1. Click **New** → **GitHub Repo** → Select `babble-buddy`
2. Set **Root Directory**: `services/agent-core`
3. Set environment variables:
   ```
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   OLLAMA_HOST=https://ollama-xxx.railway.app  (from step 2)
   ADMIN_API_KEY=your-secure-random-key
   ```
4. Copy the Agent Core URL (e.g., `https://agent-core-xxx.railway.app`)

### Step 4: Deploy Widget (Optional Demo)

1. Click **New** → **GitHub Repo** → Select `babble-buddy`
2. Set **Root Directory**: `packages/widget`
3. This hosts a demo page where you can test the widget

### Step 5: Create App Token

```bash
curl -X POST https://agent-core-xxx.railway.app/api/v1/admin/tokens \
  -H "Authorization: Bearer your-secure-random-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-app", "description": "My first app"}'
```

Save the returned token (starts with `bb_`).

---

## Environment Variables

### Agent Core

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `OLLAMA_HOST` | Yes | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | No | `llama3.2` | Model to use |
| `ADMIN_API_KEY` | Yes | - | Admin key for token management |
| `RATE_LIMIT_PER_MINUTE` | No | `60` | Rate limit per token |

### Ollama

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OLLAMA_MODEL` | No | `llama3.2` | Model to pull on startup |

---

## Embed the Widget

```html
<script src="https://babble-buddy-demo.cjunker.dev/babble-buddy.umd.cjs"></script>
<script>
  BabbleBuddy.init({
    appToken: 'bb_your_token_here',
    apiUrl: 'https://babble-buddy-api.cjunker.dev',
    context: {
      app: 'my-app',
      instructions: 'Help users with their questions'
    }
  });
</script>
```

### Configuration Options

```javascript
BabbleBuddy.init({
  // Required
  appToken: 'bb_xxx',
  apiUrl: 'https://babble-buddy-api.cjunker.dev',

  // Optional
  position: 'bottom-right',  // bottom-left, top-right, top-left
  greeting: 'Hi! How can I help?',
  context: {
    app: 'exportee',
    schema: ['users', 'orders'],
    instructions: 'Help users build SQL queries'
  },
  theme: {
    primaryColor: '#6366f1',
    backgroundColor: '#ffffff',
    textColor: '#1f2937'
  }
});
```

---

## API Reference

See [Agent Core README](services/agent-core/README.md) for full API documentation.

## Recommended Models

| Model | Size | Best For |
|-------|------|----------|
| `llama3.2` | 2GB | General purpose, good default |
| `llama3.2:1b` | 1.3GB | Faster responses, lower memory |
| `codellama` | 3.8GB | Code generation, SQL help |
| `mistral` | 4.1GB | Strong reasoning |

## License

MIT
