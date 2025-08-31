"""
Knowledge API endpoints for drug management and document learning
"""

import os
import json
import logging
from flask import Blueprint, request, jsonify, session
from functools import wraps
import sqlite3

# Import the knowledge system
try:
    from core.medical_knowledge_system import get_knowledge_system, Drug
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.medical_knowledge_system import get_knowledge_system, Drug

knowledge_api = Blueprint('knowledge_api', __name__, url_prefix='/api/knowledge')
logger = logging.getLogger(__name__)

def login_required(f):
    """Decorator to require login for API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

@knowledge_api.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """Get knowledge base statistics"""
    try:
        system = get_knowledge_system()
        stats = system.get_stats()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@knowledge_api.route('/drugs/search', methods=['GET'])
@login_required
def search_drugs():
    """Search for drugs"""
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify({'success': False, 'error': 'Query parameter required'}), 400
        
        system = get_knowledge_system()
        results = system.search_drugs(query)
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Drug search error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@knowledge_api.route('/drugs/add', methods=['POST'])
@login_required
def add_drug():
    """Add a new drug to the database"""
    try:
        data = request.get_json()
        
        required_fields = ['generic_name', 'brand_names', 'atc_code', 'indications']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400
        
        # Parse brand names
        brand_names = []
        if isinstance(data['brand_names'], str):
            brand_names = [name.strip() for name in data['brand_names'].split(',') if name.strip()]
        elif isinstance(data['brand_names'], list):
            brand_names = data['brand_names']
        
        drug = Drug(
            generic_name=data['generic_name'],
            brand_names=brand_names,
            atc_code=data['atc_code'],
            indications=data['indications'],
            dosage_forms=data.get('dosage_forms', []),
            contraindications=data.get('contraindications', ''),
            interactions=data.get('interactions', ''),
            source='manual'
        )
        
        system = get_knowledge_system()
        success = system.add_drug(drug)
        
        if success:
            return jsonify({'success': True, 'message': 'Drug added successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to add drug'}), 500
            
    except Exception as e:
        logger.error(f"Add drug error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@knowledge_api.route('/documents/learn', methods=['POST'])
@login_required
def learn_document():
    """Learn from a medical document"""
    try:
        # Handle file upload or text input
        content = None
        
        if 'file' in request.files:
            file = request.files['file']
            if file.filename:
                content = file.read().decode('utf-8')
        elif request.is_json:
            data = request.get_json()
            content = data.get('content')
        else:
            content = request.form.get('content')
        
        if not content:
            return jsonify({'success': False, 'error': 'No content provided'}), 400
        
        doc_type = request.form.get('document_type') or (request.get_json() or {}).get('document_type', 'general')
        patient_id = request.form.get('patient_id') or (request.get_json() or {}).get('patient_id')
        department = request.form.get('department') or (request.get_json() or {}).get('department', 'General')
        
        system = get_knowledge_system()
        result = system.learn_from_document(content, doc_type, patient_id, department)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Document learning error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@knowledge_api.route('/search', methods=['POST'])
@login_required
def search_knowledge():
    """Search the knowledge base"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        doc_types = data.get('document_types', [])
        limit = data.get('limit', 5)
        
        if not query:
            return jsonify({'success': False, 'error': 'Query required'}), 400
        
        system = get_knowledge_system()
        results = system.search_knowledge_base(query, doc_types, limit)
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Knowledge search error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@knowledge_api.route('/enhance', methods=['POST'])
@login_required
def enhance_transcription():
    """Enhance a transcription with drug recognition and knowledge"""
    try:
        data = request.get_json()
        transcript = data.get('transcript', '')
        patient_id = data.get('patient_id')
        
        if not transcript:
            return jsonify({'success': False, 'error': 'Transcript required'}), 400
        
        system = get_knowledge_system()
        enhancement = system.enhance_transcription(transcript, patient_id)
        
        return jsonify({
            'success': True,
            'enhancement': enhancement
        })
        
    except Exception as e:
        logger.error(f"Enhancement error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@knowledge_api.route('/bcfi/import', methods=['POST'])
@login_required
def import_bcfi():
    """Import drugs from BCFI.be"""
    try:
        data = request.get_json()
        category_url = data.get('category_url', '/nl/chapters/1?frag=')
        
        system = get_knowledge_system()
        result = system.import_from_bcfi(category_url)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"BCFI import error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def enhance_existing_transcription(transcript: str, patient_id: str = None) -> Dict:
    """Helper function to enhance existing transcriptions"""
    try:
        system = get_knowledge_system()
        return system.enhance_transcription(transcript, patient_id)
    except Exception as e:
        logger.error(f"Enhancement helper error: {e}")
        return {
            'enhanced_transcript': transcript,
            'drugs_found': [],
            'drug_corrections': [],
            'context_used': [],
            'enhancement_applied': False,
            'error': str(e)
        }

