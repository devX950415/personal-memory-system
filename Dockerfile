# PersonalMem API Container
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY api.py app.py memory_service.py config.py ./
COPY frontend/ ./frontend/

# Expose API port
EXPOSE 8888

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8888/health')" || exit 1

# Run the API with 5 workers
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8888", "--workers", "5"]
