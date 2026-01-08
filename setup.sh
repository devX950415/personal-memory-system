#!/bin/bash

# PersonalMem Setup Script

echo "================================"
echo "PersonalMem Setup"
echo "================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "================================"
echo "✅ Setup Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Set up environment variables:"
echo "   cp env_example.txt .env"
echo "   nano .env  # Edit with your API keys"
echo ""
echo "2. Start MongoDB (using Docker):"
echo "   docker-compose up -d"
echo ""
echo "3. Run the demo:"
echo "   source venv/bin/activate"
echo "   python app.py"
echo ""
echo "4. Or start the API server:"
echo "   python api.py"
echo ""
echo "For more information, see README.md"
echo ""

