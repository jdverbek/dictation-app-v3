"""
Background task processing with Celery
"""

from celery import Celery
from celery.result import AsyncResult
import redis
import json
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery(
    'medical_transcription',
    broker=os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Amsterdam',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max
    task_soft_time_limit=540,  # 9 minutes soft limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    task_reject_on_worker_lost=True,
)

@celery_app.task(bind=True)
def process_medical_recording(self, job_data):
    """
    Background task for processing medical recordings
    """
    try:
        logger.info(f"Starting background processing for job {job_data['job_id']}")
        
        # Update task state
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Starting transcription...', 'progress': 10}
        )
        
        # Initialize orchestrator
        from .orchestrator import IntelligentOrchestrator, ProcessingJob
        orchestrator = IntelligentOrchestrator()
        
        # Create job object
        job = ProcessingJob(
            job_id=job_data['job_id'],
            patient_id=job_data['patient_id'],
            patient_dob=job_data['patient_dob'],
            audio_file_path=job_data['audio_file_path'],
            status='processing',
            created_at=datetime.now()
        )
        
        # Update progress
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Analyzing transcription...', 'progress': 30}
        )
        
        # Process with self-correction
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                orchestrator.process_with_self_correction(job)
            )
        finally:
            loop.close()
        
        # Update progress
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Finalizing report...', 'progress': 90}
        )
        
        # Store result in Redis for retrieval
        redis_client = redis.Redis.from_url(
            os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
            decode_responses=True
        )
        
        redis_client.setex(
            f"job_result:{job.job_id}",
            86400 * 7,  # Expire after 7 days
            json.dumps(result)
        )
        
        logger.info(f"Completed processing for job {job_data['job_id']}")
        
        return {
            'status': 'completed',
            'job_id': job.job_id,
            'message': 'Processing completed successfully',
            'progress': 100
        }
        
    except Exception as e:
        logger.error(f"Background task error: {str(e)}")
        # Log error
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'progress': 0}
        )
        raise

@celery_app.task
def cleanup_old_jobs():
    """Periodic task to clean up old jobs"""
    try:
        redis_client = redis.Redis.from_url(
            os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
            decode_responses=True
        )
        
        # Get all job keys
        job_keys = redis_client.keys('job_*')
        result_keys = redis_client.keys('job_result:*')
        iteration_keys = redis_client.keys('iteration:*')
        
        current_time = datetime.now()
        cleaned_count = 0
        
        # Clean up old job status entries (older than 1 day)
        for key in job_keys:
            try:
                job_data = json.loads(redis_client.get(key) or '{}')
                updated_at = job_data.get('updated_at')
                if updated_at:
                    updated_time = datetime.fromisoformat(updated_at)
                    if (current_time - updated_time).days > 1:
                        redis_client.delete(key)
                        cleaned_count += 1
            except:
                # Delete malformed entries
                redis_client.delete(key)
                cleaned_count += 1
        
        # Clean up old results (older than 7 days)
        for key in result_keys:
            try:
                result_data = json.loads(redis_client.get(key) or '{}')
                completed_at = result_data.get('completed_at')
                if completed_at:
                    completed_time = datetime.fromisoformat(completed_at)
                    if (current_time - completed_time).days > 7:
                        redis_client.delete(key)
                        cleaned_count += 1
            except:
                redis_client.delete(key)
                cleaned_count += 1
        
        # Clean up old iteration data (older than 7 days)
        for key in iteration_keys:
            try:
                iteration_data = json.loads(redis_client.get(key) or '{}')
                timestamp = iteration_data.get('timestamp')
                if timestamp:
                    iter_time = datetime.fromisoformat(timestamp)
                    if (current_time - iter_time).days > 7:
                        redis_client.delete(key)
                        cleaned_count += 1
            except:
                redis_client.delete(key)
                cleaned_count += 1
        
        logger.info(f"Cleanup completed: removed {cleaned_count} old entries")
        return f"Cleaned up {cleaned_count} old entries"
        
    except Exception as e:
        logger.error(f"Cleanup task error: {str(e)}")
        raise

@celery_app.task
def health_check():
    """Health check task for monitoring"""
    try:
        redis_client = redis.Redis.from_url(
            os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        )
        
        # Test Redis connection
        redis_client.ping()
        
        # Test OpenAI API
        from openai import OpenAI
        client = OpenAI()
        
        # Simple test call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=5
        )
        
        return {
            'status': 'healthy',
            'redis': 'connected',
            'openai': 'connected',
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# Configure periodic tasks
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'cleanup-old-jobs': {
        'task': 'src.core.background_tasks.cleanup_old_jobs',
        'schedule': crontab(hour=2, minute=0),  # Run at 2 AM daily
    },
    'health-check': {
        'task': 'src.core.background_tasks.health_check',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
}

# Utility functions for job management
def get_job_status(job_id: str) -> Dict:
    """Get job status from Redis"""
    try:
        redis_client = redis.Redis.from_url(
            os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
            decode_responses=True
        )
        
        job_data = redis_client.get(f"job:{job_id}")
        if job_data:
            return json.loads(job_data)
        
        # Check if it's a Celery task
        task_result = AsyncResult(job_id, app=celery_app)
        if task_result.state:
            return {
                'job_id': job_id,
                'status': task_result.state.lower(),
                'message': str(task_result.info) if task_result.info else '',
                'progress': task_result.info.get('progress', 0) if isinstance(task_result.info, dict) else 0
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        return None

def get_job_result(job_id: str) -> Dict:
    """Get job result from Redis"""
    try:
        redis_client = redis.Redis.from_url(
            os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
            decode_responses=True
        )
        
        result_data = redis_client.get(f"job_result:{job_id}")
        if result_data:
            return json.loads(result_data)
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting job result: {str(e)}")
        return None

