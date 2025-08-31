#!/bin/bash

# Start all services for the enhanced medical dictation app

echo "🚀 Starting Enhanced Medical Dictation App Services..."

# Set environment variables
export FLASK_APP=src/app.py
export FLASK_ENV=development
export REDIS_URL=redis://localhost:6379/0

# Start Redis if not running
echo "📡 Starting Redis server..."
redis-server --daemonize yes
sleep 2

# Test Redis connection
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis server is running"
else
    echo "❌ Redis server failed to start"
    exit 1
fi

# Start Celery worker in background
echo "⚡ Starting Celery worker..."
cd src
celery -A core.background_tasks.celery_app worker --loglevel=info --detach

# Start Celery beat scheduler in background
echo "⏰ Starting Celery beat scheduler..."
celery -A core.background_tasks.celery_app beat --loglevel=info --detach

# Wait a moment for services to start
sleep 3

echo "🏥 Starting Flask application..."
echo "📍 Application will be available at: http://localhost:5000"
echo "📄 Enhanced features:"
echo "   - Claude Opus medical validation"
echo "   - Patient ID OCR"
echo "   - Background processing with Celery"
echo "   - Enhanced audio recording"
echo "   - Comprehensive review interface"
echo ""
echo "🔧 To stop services, use: ./stop_services.sh"
echo ""

# Start Flask app
python3 app.py

