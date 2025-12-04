#!/bin/bash

echo "Starting Ollama server..."
ollama serve &

# Wait for server to be ready
echo "Waiting for Ollama to be ready..."
until curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
  sleep 1
done

echo "Ollama is ready. Pulling model: $OLLAMA_MODEL"
ollama pull $OLLAMA_MODEL

echo "Model pulled. Ollama is fully ready."

# Keep the server running
wait
