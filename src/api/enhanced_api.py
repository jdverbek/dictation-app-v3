"""
Enhanced API with all integrated features
"""

from flask import Blueprint, request, jsonify, render_template
import uuid
from werkzeug.utils import secure_filename
import os
import sys
import json
import logging
from datetime import datetime

# Add the src directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Import core modules with error handling
try:
    from core.orchestrator import MedicalOrchestrator
    from core.patient_ocr import PatientOCR
    from core.background_tasks import start_processing_job, get_job_status
except ImportError as e:
    print(f"Warning: Could not import core modules: {e}")
    # Create dummy classes for graceful degradation
    class MedicalOrchestrator:
        def process_medical_dictation(self, *args, **kwargs):
            return {"error": "Core modules not available"}
    
    class PatientOCR:
        def extract_patient_info(self, *args, **kwargs):
            return {"success": False, "error": "OCR not available"}
    
    def start_processing_job(*args, **kwargs):
        return str(uuid.uuid4())
    
    def get_job_status(*args, **kwargs):
        return {"status": "error", "error": "Background processing not available"}

logger = logging.getLogger(__name__)

enhanced_api = Blueprint('enhanced_api', __name__)

@enhanced_api.route('/api/process', methods=['POST'])
def process_recording():
    """Main endpoint for processing medical recordings"""
    try:
        logger.info("Processing new recording request")
        
        # Get files and data
        audio_file = request.files.get('audio_file')
        patient_id = request.form.get('patient_id')
        patient_dob = request.form.get('patient_dob')
        patient_image = request.files.get('patient_image')
        
        # If patient image provided, extract ID and DOB
        if patient_image and not patient_id:
            logger.info("Extracting patient info from image")
            from ..core.patient_ocr import PatientIDExtractor
            extractor = PatientIDExtractor()
            
            # Save image temporarily
            image_filename = secure_filename(f"temp_{uuid.uuid4()}_{patient_image.filename}")
            image_path = os.path.join('uploads', 'temp', image_filename)
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            patient_image.save(image_path)
            
            try:
                extracted_id, extracted_dob = extractor.extract_from_image(image_path)
                if extracted_id:
                    patient_id = extracted_id
                if extracted_dob:
                    patient_dob = extracted_dob
                    
                logger.info(f"Extracted from image - ID: {patient_id}, DOB: {patient_dob}")
            finally:
                # Clean up temp image
                if os.path.exists(image_path):
                    os.remove(image_path)
        
        # Validate inputs
        if not audio_file:
            return jsonify({'error': 'No audio file provided'}), 400
        
        if not patient_id:
            return jsonify({'error': 'Patient ID required'}), 400
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        logger.info(f"Created job {job_id} for patient {patient_id}")
        
        # Create uploads directory
        upload_dir = os.path.join('uploads', 'audio')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save audio file
        filename = secure_filename(f"{job_id}_{audio_file.filename}")
        filepath = os.path.join(upload_dir, filename)
        audio_file.save(filepath)
        
        logger.info(f"Audio saved to {filepath}")
        
        # Create background task
        from ..core.background_tasks import process_medical_recording
        task = process_medical_recording.delay({
            'job_id': job_id,
            'patient_id': patient_id,
            'patient_dob': patient_dob or '',
            'audio_file_path': filepath
        })
        
        logger.info(f"Background task created: {task.id}")
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'task_id': task.id,
            'message': 'Processing started in background'
        })
        
    except Exception as e:
        logger.error(f"Process recording error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@enhanced_api.route('/api/job/status/<job_id>')
def get_job_status(job_id):
    """Get status of processing job"""
    try:
        from ..core.background_tasks import get_job_status
        
        status = get_job_status(job_id)
        if not status:
            return jsonify({'error': 'Job not found'}), 404
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Get job status error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@enhanced_api.route('/review/<job_id>')
def review_report(job_id):
    """Review and edit interface"""
    try:
        logger.info(f"Loading review page for job {job_id}")
        
        from ..core.background_tasks import get_job_result
        
        # Get job result
        result = get_job_result(job_id)
        if not result:
            return render_template('error.html', 
                                 message="Job not found or still processing",
                                 job_id=job_id), 404
        
        # Extract report content
        report_content = ""
        if result.get('report') and result['report'].get('content'):
            content = result['report']['content']
            if isinstance(content, dict):
                # Format structured content
                report_content = json.dumps(content, indent=2, ensure_ascii=False)
            else:
                report_content = str(content)
        
        return render_template('review.html',
            job_id=job_id,
            patient_id=result.get('patient_id', 'Unknown'),
            patient_dob=result.get('patient_dob', 'Unknown'),
            transcript=result.get('transcript', ''),
            structured_report=report_content,
            confidence=result.get('confidence_score', 0),
            iterations=result.get('iterations', 0),
            status='completed',
            process_time=result.get('completed_at', '')
        )
        
    except Exception as e:
        logger.error(f"Review page error: {str(e)}")
        return render_template('error.html', 
                             message=f"Error loading review page: {str(e)}",
                             job_id=job_id), 500

@enhanced_api.route('/api/job/<job_id>/save', methods=['POST'])
def save_report(job_id):
    """Save edited report"""
    try:
        data = request.get_json()
        report = data.get('report')
        version = data.get('version', 1)
        
        if not report:
            return jsonify({'error': 'No report content provided'}), 400
        
        # Store version in Redis
        import redis
        redis_client = redis.Redis.from_url(
            os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
            decode_responses=True
        )
        
        version_data = {
            'number': version,
            'content': report,
            'timestamp': datetime.now().isoformat(),
            'job_id': job_id
        }
        
        # Store version
        redis_client.setex(
            f"version:{job_id}:{version}",
            86400 * 7,  # Expire after 7 days
            json.dumps(version_data)
        )
        
        # Update job result with latest version
        result_key = f"job_result:{job_id}"
        result_data = redis_client.get(result_key)
        if result_data:
            result = json.loads(result_data)
            result['report']['content'] = report
            result['last_saved'] = datetime.now().isoformat()
            redis_client.setex(result_key, 86400 * 7, json.dumps(result))
        
        logger.info(f"Saved version {version} for job {job_id}")
        
        return jsonify({
            'success': True,
            'version': version_data
        })
        
    except Exception as e:
        logger.error(f"Save report error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@enhanced_api.route('/api/job/<job_id>/autosave', methods=['POST'])
def autosave_report(job_id):
    """Auto-save edited report"""
    try:
        data = request.get_json()
        report = data.get('report')
        timestamp = data.get('timestamp')
        
        if not report:
            return jsonify({'error': 'No report content provided'}), 400
        
        # Store auto-save in Redis with shorter expiration
        import redis
        redis_client = redis.Redis.from_url(
            os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
            decode_responses=True
        )
        
        autosave_data = {
            'content': report,
            'timestamp': timestamp,
            'job_id': job_id
        }
        
        redis_client.setex(
            f"autosave:{job_id}",
            3600,  # Expire after 1 hour
            json.dumps(autosave_data)
        )
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Auto-save error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@enhanced_api.route('/api/job/<job_id>/validate', methods=['POST'])
def validate_report(job_id):
    """Validate report using Claude Opus"""
    try:
        data = request.get_json()
        report = data.get('report')
        
        if not report:
            return jsonify({'error': 'No report content provided'}), 400
        
        # Get original transcription
        from ..core.background_tasks import get_job_result
        result = get_job_result(job_id)
        
        if not result:
            return jsonify({'error': 'Original job data not found'}), 404
        
        transcription = result.get('transcript', '')
        
        # Create report structure for validation
        report_dict = {
            'type': 'manual_edit',
            'content': report,
            'patient_id': result.get('patient_id'),
            'patient_dob': result.get('patient_dob'),
            'timestamp': datetime.now().isoformat()
        }
        
        # Use Claude validator
        from ..core.claude_medical_validator import ClaudeMedicalValidator
        validator = ClaudeMedicalValidator()
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            validation_result = loop.run_until_complete(
                validator.validate_medical_logic(report_dict, transcription)
            )
        finally:
            loop.close()
        
        logger.info(f"Validation completed for job {job_id}")
        
        return jsonify(validation_result)
        
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@enhanced_api.route('/api/job/<job_id>/versions')
def get_versions(job_id):
    """Get version history for a job"""
    try:
        import redis
        redis_client = redis.Redis.from_url(
            os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
            decode_responses=True
        )
        
        # Get all version keys for this job
        version_keys = redis_client.keys(f"version:{job_id}:*")
        versions = []
        
        for key in version_keys:
            version_data = redis_client.get(key)
            if version_data:
                version = json.loads(version_data)
                versions.append(version)
        
        # Sort by version number
        versions.sort(key=lambda x: x.get('number', 0), reverse=True)
        
        return jsonify(versions)
        
    except Exception as e:
        logger.error(f"Get versions error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@enhanced_api.route('/api/extract-patient-id', methods=['POST'])
def extract_patient_id():
    """Extract patient ID from uploaded image"""
    try:
        patient_image = request.files.get('patient_image')
        
        if not patient_image:
            return jsonify({'error': 'No image provided'}), 400
        
        # Save image temporarily
        image_filename = secure_filename(f"temp_{uuid.uuid4()}_{patient_image.filename}")
        image_path = os.path.join('uploads', 'temp', image_filename)
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        patient_image.save(image_path)
        
        try:
            from ..core.patient_ocr import PatientIDExtractor
            extractor = PatientIDExtractor()
            
            patient_id, patient_dob = extractor.extract_from_image(image_path)
            
            return jsonify({
                'success': True,
                'patient_id': patient_id,
                'patient_dob': patient_dob
            })
            
        finally:
            # Clean up temp image
            if os.path.exists(image_path):
                os.remove(image_path)
        
    except Exception as e:
        logger.error(f"Patient ID extraction error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@enhanced_api.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        # Check Redis connection
        import redis
        redis_client = redis.Redis.from_url(
            os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        )
        redis_client.ping()
        
        # Check OpenAI API
        from openai import OpenAI
        client = OpenAI()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'redis': 'connected',
                'openai': 'available',
                'claude': 'available'
            }
        })
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# Error handlers
@enhanced_api.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@enhanced_api.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

