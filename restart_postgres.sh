#!/bin/bash

echo "=========================================="
echo "Restarting PostgreSQL with fixed init script"
echo "=========================================="

cd /home/devx/Documents/PersonalMem

echo ""
echo "1. Stopping PostgreSQL container..."
sudo docker compose down postgres

echo ""
echo "2. Removing old data volume (to apply fixed init script)..."
sudo docker volume rm personalmem_postgres_data 2>/dev/null || echo "   Volume doesn't exist or already removed"

echo ""
echo "3. Starting PostgreSQL with fixed init script..."
sudo docker compose up -d postgres

echo ""
echo "4. Waiting for PostgreSQL to be ready..."
sleep 3

echo ""
echo "5. Checking PostgreSQL status..."
sudo docker logs personalmem_postgres | tail -n 10

echo ""
echo "6. Testing connection..."
sudo docker exec personalmem_postgres psql -U postgres -d personalmem -c "SELECT version();" 2>/dev/null && echo "✅ PostgreSQL is ready!" || echo "❌ PostgreSQL not ready yet, wait a few more seconds"

echo ""
echo "=========================================="
echo "Done! You can now restart the API server."
echo "=========================================="

