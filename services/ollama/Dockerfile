FROM ollama/ollama:latest

# Default model to pull on startup (1b is smaller/faster to download)
ENV OLLAMA_MODEL=llama3.2:1b
# Bind to all interfaces on port 11434
ENV OLLAMA_HOST=0.0.0.0:11434

# Copy startup script
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Ollama uses 11434
EXPOSE 11434

ENTRYPOINT ["/start.sh"]
