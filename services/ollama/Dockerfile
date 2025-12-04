FROM ollama/ollama:latest

# Default model to pull on startup
ENV OLLAMA_MODEL=llama3.2
ENV OLLAMA_HOST=0.0.0.0

# Copy startup script
COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 11434

ENTRYPOINT ["/start.sh"]
