#!/bin/bash

# Medical Dictation App Setup Script
# This script helps set up the application for development or production

set -e  # Exit on any error

echo "🩺 Medical Dictation App Setup"
echo "=============================="

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "Python version: $python_version"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    echo "❌ Error: Python 3.8 or higher is required"
    exit 1
fi

echo "✅ Python version is compatible"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file and add your OpenAI API key"
    echo "✅ .env file created"
else
    echo "✅ .env file already exists"
fi

# Check if OpenAI API key is set
if [ -f ".env" ]; then
    if grep -q "your_openai_api_key_here" .env; then
        echo "⚠️  Warning: Please update your OpenAI API key in .env file"
    else
        echo "✅ OpenAI API key appears to be configured"
    fi
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p logs
mkdir -p uploads
mkdir -p recordings

# Set permissions
chmod +x scripts/*.sh

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your OpenAI API key"
echo "2. Run the application:"
echo "   source venv/bin/activate"
echo "   python src/app.py"
echo ""
echo "For production deployment:"
echo "   gunicorn --bind 0.0.0.0:10000 src.app:app"
echo ""
echo "For testing:"
echo "   python -m pytest tests/"
echo ""

