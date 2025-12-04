#!/bin/bash
set -e

echo "=== Starting Ollama Server ==="
echo "Model: ${OLLAMA_MODEL:-llama3.2}"

# Start Ollama in background
ollama serve &
OLLAMA_PID=$!

# Wait for server to be ready (up to 60 seconds)
echo "Waiting for Ollama server to start..."
for i in {1..60}; do
  if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Ollama server is up!"
    break
  fi
  echo "  Attempt $i/60..."
  sleep 1
done

# Pull model
echo "=== Pulling model: ${OLLAMA_MODEL:-llama3.2} ==="
ollama pull ${OLLAMA_MODEL:-llama3.2}

echo "=== Ollama is fully ready ==="
echo "Listening on port 11434"

# Keep container running
wait $OLLAMA_PID
