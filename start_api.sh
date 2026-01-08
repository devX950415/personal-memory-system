#!/bin/bash

# Start PersonalMem API Server

echo "================================"
echo "Starting PersonalMem API"
echo "================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo ""
    echo "Please create a .env file with your configuration:"
    echo "  cp env_example.txt .env"
    echo "  nano .env"
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

# Check if MongoDB is running
echo "🔍 Checking MongoDB connection..."
if python3 -c "from pymongo import MongoClient; MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=2000).server_info()" 2>/dev/null; then
    echo "✅ MongoDB is running"
else
    echo "⚠️  MongoDB is not running!"
    echo ""
    echo "Start MongoDB with: docker-compose up -d"
    echo ""
    echo "Continuing anyway (server will fail if MongoDB is not available)..."
fi

echo ""
echo "🚀 Starting API server..."
echo "📍 API will be available at: http://localhost:8000"
echo "📚 API docs at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python api.py

