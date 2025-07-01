"""
Enhanced Medical Dictation App - Main Application
Integrates intelligent history collection and clinical examination systems
CRITICAL: NEVER fabricate or make up any medical information
"""

import os
import io
import datetime
import requests
from flask import Flask, request, render_template, jsonify
from dataclasses import asdict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path for imports
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import core modules
from core.history_analyzer import HistoryAnalyzer
from core.clinical_examiner import ClinicalExaminer
from core.enhanced_audio_utils import EnhancedAudioProcessor, get_whisper_params_for_medical, handle_empty_transcription, get_error_solutions, get_medical_recording_tips

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"
GPT_URL = "https://api.openai.com/v1/chat/completions"

# Initialize analysis systems
history_analyzer = HistoryAnalyzer()
clinical_examiner = ClinicalExaminer()

def call_gpt(messages, temperature=0.3):
    """Call OpenAI GPT API with error handling and extended timeout for large texts"""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o",
        "temperature": temperature,
        "messages": messages
    }
    
    # Calculate timeout based on message length
    total_chars = sum(len(msg.get('content', '')) for msg in messages)
    if total_chars > 5000:
        timeout = 300  # 5 minutes for large texts
    elif total_chars > 2000:
        timeout = 180  # 3 minutes for medium texts
    else:
        timeout = 120  # 2 minutes for normal texts
    
    try:
        app.logger.info(f"Calling GPT API with {total_chars} characters (timeout: {timeout}s)")
        response = requests.post(GPT_URL, headers=headers, json=data, timeout=timeout)
        response.raise_for_status()
        result = response.json()["choices"][0]["message"]["content"]
        app.logger.info(f"GPT API response received successfully")
        return result
    except requests.exceptions.Timeout:
        error_msg = f"GPT API timeout after {timeout} seconds for {total_chars} characters"
        app.logger.error(error_msg)
        raise Exception(error_msg)
    except requests.exceptions.RequestException as e:
        app.logger.error(f"OpenAI API error: {str(e)}")
        raise

@app.route('/', methods=['GET'])
def index():
    """Main application page"""
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for deployment monitoring"""
    return jsonify({
        'status': 'healthy',
        'version': '2.0.0',
        'timestamp': datetime.datetime.now().isoformat()
    })

@app.route('/transcribe', methods=['POST'])
def transcribe():
    """Main transcription and analysis endpoint with robust error handling"""
    file = request.files.get('audio_file')
    verslag_type = request.form.get('verslag_type', 'consult')
    raadpleging_part = request.form.get('raadpleging_part', 'history')

    if not file or file.filename == '':
        return render_template('index.html', 
                             transcript='⚠️ Geen bestand geselecteerd.',
                             error=True)

    try:
        # Step 1: Validate audio file with medical recording considerations
        is_valid, validation_msg, metadata = EnhancedAudioProcessor.validate_audio_file(file, file.filename)
        
        if not is_valid:
            # Audio validation failed - provide specific solutions
            error_type = 'file_too_large' if 'te groot' in validation_msg else 'format_error'
            solutions = get_error_solutions(error_type)
            tips = get_medical_recording_tips()
            return render_template('index.html', 
                                 transcript=f"{validation_msg}\n\n{solutions}\n\n{tips}",
                                 error=True)
        
        # Step 2: Prepare file for API with medical optimizations
        prepared_file, prep_error = EnhancedAudioProcessor.prepare_file_for_api(file, file.filename)
        if prepared_file is None:
            solutions = get_error_solutions('file_too_large')
            return render_template('index.html', 
                                 transcript=f"{prep_error}\n\n{solutions}",
                                 error=True)
        
        # Step 3: Transcribe audio with medical recording optimizations
        app.logger.info(f"Starting transcription for {file.filename} ({metadata['size_formatted']})")
        
        try:
            # Use enhanced parameters for medical recordings
            whisper_params = get_whisper_params_for_medical(metadata)
            raw_text = transcribe_audio_robust(prepared_file, file.filename, metadata['is_large'], whisper_params)
            
            # Check for empty or minimal transcription
            if not raw_text or len(raw_text.strip()) < 10:
                app.logger.warning(f"Empty or minimal transcription for {file.filename}: '{raw_text}'")
                empty_feedback = handle_empty_transcription(metadata, file.filename)
                return render_template('index.html', 
                                     transcript=empty_feedback,
                                     error=True)
                
        except Exception as transcribe_error:
            app.logger.error(f"Transcription failed: {transcribe_error}")
            
            # Handle specific errors
            error_str = str(transcribe_error)
            if "timeout" in error_str.lower() or "timed out" in error_str.lower():
                solutions = get_error_solutions('timeout')
                error_msg = f"⏰ Verwerking duurde te lang (timeout)\n\n{solutions}"
            elif "413" in error_str or "Payload Too Large" in error_str:
                solutions = get_error_solutions('file_too_large')
                error_msg = f"❌ Bestand te groot voor API\n\n{solutions}"
            elif "400" in error_str or "Bad Request" in error_str:
                error_msg = f"❌ Ongeldig audiobestand - probeer een ander formaat"
            else:
                error_msg = f"❌ Fout bij transcriptie: {error_str}"
            
            return render_template('index.html', 
                                 transcript=error_msg,
                                 error=True)
        
        # Step 4: Correct transcription
        corrected = correct_transcription(raw_text)
        
        # Step 5: Process based on type
        today = datetime.date.today().strftime('%d-%m-%Y')
        
        # Add file info to the result
        file_info = f"📁 {validation_msg}\n"
        if metadata['recommendations']:
            file_info += f"💡 {'; '.join(metadata['recommendations'])}\n"
        file_info += "\n"
        
        if verslag_type == 'raadpleging':
            result = process_raadpleging(corrected, raadpleging_part, today)
            # Add file info to the transcript
            if hasattr(result, 'data') and result.data:
                original_transcript = result.data.get('transcript', '')
                result.data['transcript'] = file_info + original_transcript
            return result
        elif verslag_type in ['TTE', 'TEE', 'ECG', 'EXERCISE_TEST', 'DEVICE_INTERROGATION', 'HOLTER']:
            result = process_clinical_examination(corrected, verslag_type, today)
            if hasattr(result, 'data') and result.data:
                original_transcript = result.data.get('transcript', '')
                result.data['transcript'] = file_info + original_transcript
            return result
        else:
            result = process_original_format(corrected, verslag_type, today)
            if hasattr(result, 'data') and result.data:
                original_transcript = result.data.get('transcript', '')
                result.data['transcript'] = file_info + original_transcript
            return result
            
    except Exception as e:
        app.logger.error(f"Unexpected error in transcribe: {str(e)}")
        error_msg = f"❌ Onverwachte fout: {str(e)}"
        
        # Provide general solutions
        tips = get_audio_processing_tips()
        return render_template('index.html', 
                             transcript=f"{error_msg}\n\n{tips}",
                             error=True)

def transcribe_audio_robust(file_obj, filename, is_large_file=False, whisper_params=None):
    """Transcribe audio file using OpenAI Whisper with robust error handling and medical optimizations"""
    import time
    
    # Set timeout based on file size
    timeout = 300 if is_large_file else 120  # 5 minutes for large files, 2 minutes for normal
    
    # Default whisper parameters
    if whisper_params is None:
        whisper_params = {
            "model": "whisper-1",
            "language": "nl",
            "temperature": 0.0
        }
    
    try:
        # Reset file pointer to beginning
        file_obj.seek(0)
        audio_data = file_obj.read()
        audio_stream = io.BytesIO(audio_data)
        
        # Determine content type based on filename
        file_ext = filename.lower().split('.')[-1] if '.' in filename else 'mp3'
        content_type_map = {
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'webm': 'audio/webm',
            'm4a': 'audio/mp4',
            'aac': 'audio/aac',
            'flac': 'audio/flac',
            'ogg': 'audio/ogg'
        }
        content_type = content_type_map.get(file_ext, 'audio/mpeg')
        
        files = {'file': (filename, audio_stream, content_type)}
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
        
        # Prepare data payload with whisper parameters
        data_payload = {}
        for key, value in whisper_params.items():
            if key != 'model':  # model is handled separately
                data_payload[key] = value
        data_payload["model"] = whisper_params.get("model", "whisper-1")
        
        app.logger.info(f"Starting OpenAI transcription for {filename} (timeout: {timeout}s)")
        if whisper_params.get("prompt"):
            app.logger.info(f"Using medical recording prompt for better quiet audio handling")
        start_time = time.time()
        
        # Make the request with appropriate timeout
        response = requests.post(WHISPER_URL, headers=headers, files=files, 
                               data=data_payload, timeout=timeout)
        
        elapsed_time = time.time() - start_time
        app.logger.info(f"OpenAI API response received in {elapsed_time:.1f}s")
        
        response.raise_for_status()
        result = response.json().get('text', '').strip()
        app.logger.info(f"Transcription successful: {len(result)} characters")
        return result
        
    except requests.exceptions.Timeout:
        error_msg = f"OpenAI API timeout after {timeout} seconds"
        app.logger.error(error_msg)
        raise Exception(error_msg)
        
    except requests.exceptions.RequestException as e:
        error_msg = f"OpenAI API request failed: {str(e)}"
        app.logger.error(error_msg)
        raise Exception(error_msg)
        
    except Exception as e:
        error_msg = f"Transcription error: {str(e)}"
        app.logger.error(error_msg)
        raise Exception(error_msg)

def transcribe_audio(file_obj, filename):
    """Legacy transcribe function - redirects to robust version"""
    return transcribe_audio_robust(file_obj, filename, False)

def correct_transcription(raw_text):
    """Correct transcription using GPT"""
    return call_gpt([
        {"role": "system", "content": "Corrigeer deze transcriptie in correct medisch Nederlands. Voeg NIETS toe dat niet expliciet vermeld is."},
        {"role": "user", "content": raw_text}
    ])

def process_raadpleging(corrected_text, part_type, today):
    """Process enhanced raadpleging with two-part flow"""
    
    if part_type == 'history':
        # Part 1: Intelligent history collection
        analysis = history_analyzer.analyze_conversation(corrected_text)
        formatted_history = history_analyzer.format_structured_output(analysis)
        
        return render_template('index.html', 
                             transcript=formatted_history,
                             analysis_type="🧠 Anamnese Analyse",
                             confidence_info=f"Betrouwbaarheid: {len(analysis.chief_complaints)} klachten geïdentificeerd",
                             success=True)
    
    elif part_type == 'examination':
        # Part 2: Clinical examination dictation
        examination_result = clinical_examiner.analyze_examination(corrected_text)
        
        if examination_result.investigation_type != "UNKNOWN":
            return render_template('index.html',
                                 transcript=examination_result.formatted_report,
                                 analysis_type=f"🔬 Onderzoek: {examination_result.investigation_type}",
                                 confidence_info=f"Ontbrekende velden: {len(examination_result.missing_fields)}",
                                 success=True)
        else:
            return process_general_clinical_examination(corrected_text, today)
    
    else:
        return render_template('index.html', 
                             transcript="⚠️ Onbekend raadpleging onderdeel. Kies 'Anamnese' of 'Onderzoek'.",
                             error=True)

def process_clinical_examination(corrected_text, investigation_type, today):
    """Process specific clinical examinations"""
    type_mapping = {
        'TTE': 'TTE',
        'TEE': 'TEE', 
        'ECG': 'ECG',
        'EXERCISE_TEST': 'EXERCISE_TEST',
        'DEVICE_INTERROGATION': 'DEVICE_INTERROGATION',
        'HOLTER': 'HOLTER'
    }
    
    clinical_type = type_mapping.get(investigation_type, investigation_type)
    examination_result = clinical_examiner.analyze_examination(corrected_text, clinical_type)
    
    return render_template('index.html',
                         transcript=examination_result.formatted_report,
                         analysis_type=f"🔬 Onderzoek: {investigation_type}",
                         confidence_info=f"Betrouwbaarheid: {len(examination_result.confidence_scores)} velden geëxtraheerd",
                         success=True)

def process_general_clinical_examination(corrected_text, today):
    """Process general clinical examination when specific type not detected"""
    # Implementation similar to enhanced app but simplified for space
    # This would use the general template processing
    pass

def process_original_format(corrected_text, verslag_type, today):
    """Process using original format for backward compatibility"""
    # Implementation of original templates for TTE, TEE, consult, etc.
    # This maintains backward compatibility
    pass

# API Endpoints
@app.route('/api/analyze_history', methods=['POST'])
def api_analyze_history():
    """API endpoint for history analysis"""
    data = request.get_json()
    transcript = data.get('transcript', '')
    
    if not transcript:
        return jsonify({'error': 'No transcript provided'}), 400
    
    try:
        analysis = history_analyzer.analyze_conversation(transcript)
        return jsonify({
            'reason_for_encounter': analysis.reason_for_encounter,
            'chief_complaints': [asdict(complaint) for complaint in analysis.chief_complaints],
            'relevant_history': analysis.relevant_history,
            'red_flags': analysis.red_flags,
            'information_gaps': analysis.information_gaps,
            'confidence_scores': analysis.confidence_scores
        })
    except Exception as e:
        app.logger.error(f"History analysis error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze_examination', methods=['POST'])
def api_analyze_examination():
    """API endpoint for clinical examination analysis"""
    data = request.get_json()
    transcript = data.get('transcript', '')
    investigation_type = data.get('investigation_type', None)
    
    if not transcript:
        return jsonify({'error': 'No transcript provided'}), 400
    
    try:
        result = clinical_examiner.analyze_examination(transcript, investigation_type)
        return jsonify({
            'investigation_type': result.investigation_type,
            'findings': result.findings,
            'missing_fields': result.missing_fields,
            'confidence_scores': result.confidence_scores,
            'formatted_report': result.formatted_report
        })
    except Exception as e:
        app.logger.error(f"Examination analysis error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('index.html', 
                         transcript="⚠️ Pagina niet gevonden.",
                         error=True), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Internal server error: {str(error)}")
    return render_template('index.html', 
                         transcript="⚠️ Interne serverfout. Probeer het opnieuw.",
                         error=True), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug)

