# Babble Buddy

An embeddable AI chatbot widget that connects to self-hosted AI backends.

## Live Demo

- **Demo Page**: [demo-production-d4be.up.railway.app](https://demo-production-d4be.up.railway.app)
- **API**: [babble-buddy-api.cjunker.dev](https://babble-buddy-api.cjunker.dev)

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

## Features

- **Embeddable widget** - Drop into any web app with a single script tag
- **Customizable themes** - Match your brand colors and style
- **Markdown support** - Code blocks, inline code, bold, italic, links
- **Streaming responses** - Real-time token streaming
- **Session management** - Maintains conversation context
- **Self-hosted AI** - Connect to Ollama or other backends
- **Token authentication** - Secure multi-tenant access

## Services

| Service | Description | Directory |
|---------|-------------|-----------|
| **Agent Core** | Python FastAPI backend for AI interactions | `services/agent-core/` |
| **Ollama** | Self-hosted LLM inference server | `services/ollama/` |
| **Widget** | Embeddable TypeScript chat widget | `packages/widget/` |

---

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

1. Click **New** → **GitHub Repo** → Select your repo
2. Set **Root Directory**: `services/ollama`
3. Set environment variable:
   - `OLLAMA_MODEL` = `llama3.2`
4. **Add a Volume** (recommended):
   - Settings → Volumes → Mount path: `/root/.ollama`
5. Wait for deploy (first time takes 3-5 min to pull model)
6. Note the **private** hostname (e.g., `ollama.railway.internal`)

### Step 3: Deploy Agent Core

1. Click **New** → **GitHub Repo** → Select your repo
2. Set **Root Directory**: `services/agent-core`
3. Set environment variables:
   ```
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   OLLAMA_HOST=http://ollama.railway.internal:11434
   ADMIN_API_KEY=your-secure-random-key
   ```
4. Generate a public domain or add custom domain

### Step 4: Deploy Widget (Optional)

1. Click **New** → **GitHub Repo** → Select your repo
2. Set **Root Directory**: `packages/widget`
3. Set environment variables:
   ```
   BABBLE_BUDDY_API_URL=https://your-agent-core-url
   BABBLE_BUDDY_TOKEN=bb_your_token
   ```
4. This hosts the demo page for testing

### Step 5: Create App Token

```bash
curl -X POST https://your-agent-core-url/api/v1/admin/tokens \
  -H "Authorization: Bearer your-secure-random-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-app"}'
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
| `OLLAMA_MAX_TOKENS` | No | `512` | Max tokens in response |
| `OLLAMA_TEMPERATURE` | No | `0.7` | Response creativity (0.0-1.0) |
| `ADMIN_API_KEY` | Yes | - | Admin key for token management |
| `RATE_LIMIT_PER_MINUTE` | No | `60` | Rate limit per token |

### Widget (Demo Page)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BABBLE_BUDDY_API_URL` | No | `http://localhost:8000` | Agent Core URL |
| `BABBLE_BUDDY_TOKEN` | No | `demo-token` | App token for demo |
| `BABBLE_BUDDY_GREETING` | No | `Hi! How can I help you today?` | Initial greeting |

### Ollama

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OLLAMA_MODEL` | No | `llama3.2` | Model to pull on startup |

---

## Embed the Widget

```html
<script src="https://your-widget-url/babble-buddy.umd.cjs"></script>
<script>
  BabbleBuddy.init({
    appToken: 'bb_your_token_here',
    apiUrl: 'https://your-agent-core-url',
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
  apiUrl: 'https://your-agent-core-url',

  // Optional
  position: 'bottom-right',  // bottom-left, top-right, top-left
  greeting: 'Hi! How can I help?',
  context: {
    app: 'my-app',
    instructions: 'Help users build SQL queries'
  },
  theme: {
    primaryColor: '#0f172a',    // Button & header color
    backgroundColor: '#ffffff', // Chat window background
    textColor: '#1e293b',       // Text color
    fontFamily: 'system-ui',    // Font stack
    borderRadius: '12px'        // Corner rounding
  }
});
```

### Theme Examples

```javascript
// Dark theme
theme: {
  primaryColor: '#18181b',
  backgroundColor: '#27272a',
  textColor: '#fafafa'
}

// Blue theme
theme: { primaryColor: '#2563eb' }

// Green theme
theme: { primaryColor: '#059669' }
```

### JavaScript API

```javascript
BabbleBuddy.open();           // Open chat window
BabbleBuddy.close();          // Close chat window
BabbleBuddy.destroy();        // Remove widget from page
BabbleBuddy.setContext({...}); // Update context dynamically
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
