# Multi-stage build for PersonalMem with integrated MongoDB
FROM python:3.11-slim

# Install MongoDB and supervisor
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    supervisor \
    && wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | apt-key add - \
    && echo "deb http://repo.mongodb.org/apt/debian bullseye/mongodb-org/7.0 main" | tee /etc/apt/sources.list.d/mongodb-org-7.0.list \
    && apt-get update \
    && apt-get install -y mongodb-org \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create MongoDB data directory
RUN mkdir -p /data/db && chown -R mongodb:mongodb /data/db

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY api.py app.py memory_service.py config.py ./
COPY frontend/ ./frontend/

# Copy environment template
COPY env_example.txt .

# Create supervisor configuration
RUN mkdir -p /var/log/supervisor

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose ports
EXPOSE 27017 8888

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8888/health')" || exit 1

# Start supervisor to manage both MongoDB and FastAPI
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
