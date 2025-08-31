#!/bin/bash

# Stop all services for the enhanced medical dictation app

echo "🛑 Stopping Enhanced Medical Dictation App Services..."

# Stop Celery workers
echo "⚡ Stopping Celery workers..."
pkill -f "celery.*worker"

# Stop Celery beat
echo "⏰ Stopping Celery beat..."
pkill -f "celery.*beat"

# Stop Flask app
echo "🏥 Stopping Flask application..."
pkill -f "python3.*app.py"

# Stop Redis (optional - comment out if you want to keep Redis running)
# echo "📡 Stopping Redis server..."
# redis-cli shutdown

echo "✅ All services stopped"

