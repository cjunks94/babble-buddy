# Ollama Service

Self-hosted Ollama instance for Babble Buddy.

## Deploy to Railway

1. Create a new service from this repo
2. Set **Root Directory**: `services/ollama`
3. Set environment variable:
   - `OLLAMA_MODEL`: Model to use (default: `llama3.2`)

### Available Models

| Model | Size | Description |
|-------|------|-------------|
| `llama3.2` | 2GB | Default, good balance of speed/quality |
| `llama3.2:1b` | 1.3GB | Smaller, faster |
| `mistral` | 4.1GB | Strong general purpose |
| `codellama` | 3.8GB | Optimized for code |
| `phi3` | 2.2GB | Microsoft's efficient model |

See [ollama.com/library](https://ollama.com/library) for all models.

## Important Notes

### Railway Considerations

- **First deploy is slow**: Model download happens on first start (~2-5 min depending on model size)
- **Ephemeral storage**: Models re-download on each deploy. Consider using Railway volumes for persistence.
- **Memory**: Larger models need more RAM. Railway's default should handle 7B models.

### Add Persistent Storage (Recommended)

In Railway dashboard:
1. Go to Ollama service → Settings → Volumes
2. Add volume mounted at `/root/.ollama`
3. This persists models between deploys

## Local Development

```bash
# Run with Docker
docker build -t babble-buddy-ollama .
docker run -p 11434:11434 -e OLLAMA_MODEL=llama3.2 babble-buddy-ollama

# Or use Ollama directly
ollama serve
ollama pull llama3.2
```

## API

Once running, Ollama is available at `http://localhost:11434` (or your Railway URL).

Test it:
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Hello!"
}'
```
