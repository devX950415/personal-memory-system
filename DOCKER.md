# Docker Deployment Guide

This guide explains how to build and run PersonalMem as a single Docker image with integrated MongoDB.

## Single Image Architecture

The Docker image includes:
- Python 3.11 runtime
- MongoDB 7.0
- FastAPI application
- Supervisor (process manager)

Both MongoDB and the API run in the same container, managed by Supervisor.

---

## Quick Start

### Option 1: Using Docker Compose (Recommended)

```bash
# 1. Create .env file with your credentials
cp env_example.txt .env
# Edit .env and add your AZURE_OPENAI_API_KEY

# 2. Build and start
docker compose up -d

# 3. Check logs
docker compose logs -f

# 4. Access the application
# API: http://localhost:8888
# Docs: http://localhost:8888/docs
```

### Option 2: Using Docker CLI

```bash
# 1. Build the image
docker build -t personalmem:latest .

# 2. Run the container
docker run -d \
  -p 8888:8888 \
  -p 27017:27017 \
  -e AZURE_OPENAI_API_KEY=your_key \
  -e AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/ \
  -e AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini \
  -e AZURE_OPENAI_MODEL=gpt-4o-mini \
  -v personalmem_data:/data/db \
  --name personalmem \
  personalmem:latest

# 3. Check logs
docker logs -f personalmem
```

---

## Build Script

Use the provided build script:

```bash
# Make executable (Linux/Mac)
chmod +x docker-build.sh

# Build
./docker-build.sh
```

---

## Environment Variables

Required environment variables:

```bash
# Azure OpenAI (Required)
AZURE_OPENAI_API_KEY=your_azure_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_MODEL=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2025-04-01-preview

# OR Regular OpenAI
OPENAI_API_KEY=sk-your-openai-key

# MongoDB (pre-configured internally)
MONGODB_URI=mongodb://admin:admin123@localhost:27017/
MONGODB_DATABASE=personalmem

# Application
LOG_LEVEL=INFO
```

---

## Ports

| Port | Service | Description |
|------|---------|-------------|
| 8888 | FastAPI | REST API and web interface |
| 27017 | MongoDB | Database (optional external access) |

---

## Volumes

The container uses a volume for MongoDB data persistence:

```bash
# List volumes
docker volume ls | grep personalmem

# Inspect volume
docker volume inspect personalmem_mongodb_data

# Backup data
docker run --rm -v personalmem_mongodb_data:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/mongodb-backup.tar.gz /data

# Restore data
docker run --rm -v personalmem_mongodb_data:/data -v $(pwd):/backup \
  ubuntu tar xzf /backup/mongodb-backup.tar.gz -C /
```

---

## Container Management

### Start/Stop

```bash
# Using docker-compose
docker compose start
docker compose stop
docker compose restart

# Using docker CLI
docker start personalmem
docker stop personalmem
docker restart personalmem
```

### View Logs

```bash
# All logs
docker compose logs -f

# Specific service logs (inside container)
docker exec personalmem tail -f /var/log/supervisor/fastapi.out.log
docker exec personalmem tail -f /var/log/supervisor/mongodb.out.log
```

### Access Container Shell

```bash
# Bash shell
docker exec -it personalmem bash

# MongoDB shell
docker exec -it personalmem mongosh \
  --username admin \
  --password admin123 \
  --authenticationDatabase admin
```

### Health Check

```bash
# Check container health
docker ps

# Manual health check
curl http://localhost:8888/health
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs personalmem

# Check supervisor status
docker exec personalmem supervisorctl status

# Restart services
docker exec personalmem supervisorctl restart all
```

### MongoDB Issues

```bash
# Check MongoDB logs
docker exec personalmem tail -100 /var/log/supervisor/mongodb.out.log

# Test MongoDB connection
docker exec personalmem mongosh \
  --username admin \
  --password admin123 \
  --authenticationDatabase admin \
  --eval "db.adminCommand('ping')"
```

### API Issues

```bash
# Check API logs
docker exec personalmem tail -100 /var/log/supervisor/fastapi.out.log

# Test API
curl http://localhost:8888/health
```

### Reset Everything

```bash
# Stop and remove container
docker compose down

# Remove volume (WARNING: deletes all data)
docker volume rm personalmem_mongodb_data

# Rebuild and start fresh
docker compose up -d --build
```

---

## Production Deployment

### Security Recommendations

1. **Change MongoDB credentials:**
   Edit `supervisord.conf` and rebuild:
   ```bash
   # Change admin123 to a strong password
   command=/bin/bash -c "sleep 15 && mongosh --eval \"db.getSiblingDB('admin').createUser({user: 'admin', pwd: 'YOUR_STRONG_PASSWORD', roles: [{role: 'root', db: 'admin'}]})\" || true"
   ```

2. **Use secrets management:**
   ```bash
   docker run -d \
     --env-file /secure/path/.env \
     personalmem:latest
   ```

3. **Limit port exposure:**
   ```yaml
   ports:
     - "8888:8888"  # Only expose API, not MongoDB
   ```

4. **Use reverse proxy:**
   Put behind nginx/traefik with HTTPS

5. **Resource limits:**
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 2G
       reservations:
         cpus: '1'
         memory: 1G
   ```

---

## Image Size Optimization

Current image size: ~800MB

To reduce size:

1. Use multi-stage build
2. Use Alpine-based images
3. Remove unnecessary packages
4. Combine RUN commands

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Build Docker image
        run: docker build -t personalmem:latest .
      
      - name: Push to registry
        run: |
          docker tag personalmem:latest registry.example.com/personalmem:latest
          docker push registry.example.com/personalmem:latest
```

---

## Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: personalmem
spec:
  replicas: 1
  selector:
    matchLabels:
      app: personalmem
  template:
    metadata:
      labels:
        app: personalmem
    spec:
      containers:
      - name: personalmem
        image: personalmem:latest
        ports:
        - containerPort: 8888
        - containerPort: 27017
        env:
        - name: AZURE_OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: openai-secret
              key: api-key
        volumeMounts:
        - name: mongodb-data
          mountPath: /data/db
      volumes:
      - name: mongodb-data
        persistentVolumeClaim:
          claimName: mongodb-pvc
```

---

## Support

For issues or questions:
1. Check logs: `docker logs personalmem`
2. Verify environment variables
3. Test MongoDB connection
4. Check API health endpoint
