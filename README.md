# Babble Buddy

An embeddable AI chatbot agent (like Clippy) that connects to self-hosted AI backends.

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
| **Widget** | Embeddable TypeScript chat widget | `packages/widget/` |

## Quick Start (Local)

### 1. Start Agent Core

```bash
cd services/agent-core
cp .env.example .env
docker-compose up -d
```

### 2. Create an App Token

```bash
curl -X POST http://localhost:8000/api/v1/admin/tokens \
  -H "Authorization: Bearer change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-app"}'
```

### 3. Start Widget Dev Server

```bash
cd packages/widget
npm install
npm run dev
```

### 4. Test

Open `http://localhost:5173` and chat!

## Deploy to Railway

### Option 1: One-Click Deploy

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/babble-buddy)

### Option 2: Manual Deploy

1. **Create a new Railway project**

2. **Add PostgreSQL**
   - Click "New" → "Database" → "PostgreSQL"

3. **Deploy Agent Core**
   - Click "New" → "GitHub Repo" → Select this repo
   - Set **Root Directory**: `services/agent-core`
   - Add environment variables:
     ```
     DATABASE_URL=${{Postgres.DATABASE_URL}}
     OLLAMA_HOST=https://your-ollama-instance.com
     ADMIN_API_KEY=your-secure-admin-key
     ```

4. **Deploy Widget** (optional - for hosting demo)
   - Click "New" → "GitHub Repo" → Select this repo
   - Set **Root Directory**: `packages/widget`

5. **Connect Ollama**
   - Deploy Ollama separately or use an existing instance
   - Set `OLLAMA_HOST` in Agent Core to point to it

### Environment Variables (Agent Core)

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `OLLAMA_HOST` | Yes | Ollama API endpoint |
| `OLLAMA_MODEL` | No | Model name (default: `llama3.2`) |
| `ADMIN_API_KEY` | Yes | Admin key for token management |
| `RATE_LIMIT_PER_MINUTE` | No | Rate limit per token (default: `60`) |

## Embed the Widget

```html
<script src="https://your-widget-url.com/babble-buddy.umd.cjs"></script>
<script>
  BabbleBuddy.init({
    appToken: 'bb_your_token_here',
    apiUrl: 'https://your-agent-core-url.railway.app',
    context: {
      app: 'my-app',
      instructions: 'Help users with their questions'
    }
  });
</script>
```

## API Reference

See [Agent Core README](services/agent-core/README.md) for full API documentation.

## License

MIT
