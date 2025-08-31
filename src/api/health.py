"""
Health check endpoints for monitoring system status
"""

from flask import Blueprint, jsonify
import redis
import os
from datetime import datetime

health_bp = Blueprint('health', __name__)

@health_bp.route('/api/health', methods=['GET'])
def health_check():
    """Comprehensive health check endpoint"""
    try:
        status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'services': {}
        }
        
        # Check Redis connection
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            r = redis.from_url(redis_url)
            r.ping()
            status['services']['redis'] = 'connected'
        except Exception as e:
            status['services']['redis'] = f'error: {str(e)}'
            status['status'] = 'degraded'
        
        # Check OpenAI API key
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            status['services']['openai'] = 'configured'
        else:
            status['services']['openai'] = 'not_configured'
            status['status'] = 'degraded'
        
        # Check Claude API key
        claude_key = os.getenv('CLAUDE_API_KEY')
        if claude_key:
            status['services']['claude'] = 'configured'
        else:
            status['services']['claude'] = 'not_configured'
            status['status'] = 'degraded'
        
        return jsonify(status), 200 if status['status'] == 'healthy' else 503
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

@health_bp.route('/api/ready', methods=['GET'])
def readiness_check():
    """Readiness check for deployment"""
    return jsonify({
        'status': 'ready',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

