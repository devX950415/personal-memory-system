#!/bin/bash

# Start PersonalMem API with Frontend

echo "================================"
echo "Starting PersonalMem API + Frontend"
echo "================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo ""
    echo "Please create a .env file with your configuration:"
    echo "  See env_example.txt"
    echo ""
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo ""
    echo "Please run setup first:"
    echo "  ./setup.sh"
    echo ""
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if PostgreSQL is running
echo "🔍 Checking PostgreSQL connection..."
if python3 -c "import psycopg2; psycopg2.connect(host='localhost', port=5432, dbname='personalmem', user='postgres', password='postgres', connect_timeout=2).close()" 2>/dev/null; then
    echo "✅ PostgreSQL is running"
else
    echo "⚠️  PostgreSQL is not running!"
    echo ""
    echo "Start PostgreSQL with: docker compose up -d postgres"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "🚀 Starting API server..."
echo ""
echo "📍 API will be available at: http://localhost:8888"
echo "🌐 Frontend will be available at: http://localhost:8888/"
echo "📚 API docs at: http://localhost:8888/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uvicorn api:app_api --reload --host 0.0.0.0 --port 8888

