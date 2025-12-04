FROM ollama/ollama:latest

# Default model to pull on startup
ENV OLLAMA_MODEL=llama3.2
# Bind to all interfaces on port 11434
ENV OLLAMA_HOST=0.0.0.0:11434

# Copy startup script
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Ollama uses 11434
EXPOSE 11434

ENTRYPOINT ["/start.sh"]
