"""
Enhanced audio utilities specifically designed for medical recordings
Handles quiet recordings, long silences, and provides better feedback
"""
import os
import io
import logging

logger = logging.getLogger(__name__)

class EnhancedAudioProcessor:
    """Enhanced audio processor optimized for medical recordings"""
    
    SUPPORTED_FORMATS = {
        'mp3': 'audio/mpeg',
        'wav': 'audio/wav', 
        'webm': 'audio/webm',
        'm4a': 'audio/mp4',
        'aac': 'audio/aac',
        'flac': 'audio/flac',
        'ogg': 'audio/ogg'
    }
    
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB OpenAI limit
    
    @classmethod
    def validate_audio_file(cls, file_obj, filename):
        """Validate audio file with medical recording considerations"""
        try:
            # Get file size
            file_obj.seek(0, 2)  # Seek to end
            file_size = file_obj.tell()
            file_obj.seek(0)  # Reset to beginning
            
            # Check file format
            file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
            if file_ext not in cls.SUPPORTED_FORMATS:
                return False, f"❌ Niet-ondersteund formaat: .{file_ext}", {}
            
            # Format file size
            size_mb = file_size / (1024 * 1024)
            size_formatted = f"{size_mb:.1f} MB"
            
            # Check size limit
            if file_size > cls.MAX_FILE_SIZE:
                return False, f"❌ Bestand te groot: {size_formatted} (max 25MB)", {}
            
            # Determine if it's a large file
            is_large = file_size > 15 * 1024 * 1024  # 15MB threshold
            
            # Generate medical recording specific recommendations
            recommendations = []
            if size_mb > 20:
                recommendations.append("Groot bestand - verwacht 5-10 minuten verwerkingstijd")
            if size_mb > 10:
                recommendations.append("Voor stille opnames: controleer volume niveau")
            if file_ext in ['wav', 'flac']:
                recommendations.append("Ongecomprimeerd formaat - ideaal voor zachte spraak")
            elif file_ext in ['mp3', 'aac'] and size_mb > 15:
                recommendations.append("Lange opname - mogelijk met stiltes tijdens onderzoek")
            
            metadata = {
                'size_bytes': file_size,
                'size_formatted': size_formatted,
                'format': file_ext,
                'content_type': cls.SUPPORTED_FORMATS[file_ext],
                'is_large': is_large,
                'is_medical_length': size_mb > 10,  # Likely medical consultation/procedure
                'recommendations': recommendations
            }
            
            success_msg = f"✅ Bestand geaccepteerd ({size_formatted})"
            return True, success_msg, metadata
            
        except Exception as e:
            logger.error(f"File validation error: {e}")
            return False, f"❌ Fout bij bestandsvalidatie: {str(e)}", {}
    
    @classmethod
    def prepare_file_for_api(cls, file_obj, filename):
        """Prepare file for OpenAI API with medical recording optimizations"""
        try:
            # Reset file pointer
            file_obj.seek(0)
            
            logger.info(f"Prepared medical recording {filename} for API submission")
            return file_obj, None
            
        except Exception as e:
            error_msg = f"❌ Fout bij bestandsvoorbereiding: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

def get_whisper_params_for_medical(metadata):
    """Get optimized Whisper API parameters for medical recordings"""
    params = {
        "model": "whisper-1",
        "language": "nl",
        "temperature": 0.0  # More deterministic for medical content
    }
    
    # Add prompt for medical context to help with quiet recordings
    if metadata.get('is_medical_length', False):
        params["prompt"] = "Dit is een medische opname met mogelijk zachte spraak, lange pauzes tijdens onderzoek, en medische terminologie."
    
    return params

def handle_empty_transcription(metadata, filename):
    """Handle cases where transcription returns empty or minimal text"""
    size_mb = metadata.get('size_bytes', 0) / (1024 * 1024)
    
    feedback = f"""
🔇 **Transcriptie resulteerde in weinig of geen tekst**

📊 **Bestandsinfo:**
• Bestand: {filename}
• Grootte: {metadata.get('size_formatted', 'Onbekend')}
• Formaat: {metadata.get('format', 'Onbekend').upper()}

🔍 **Mogelijke oorzaken:**
• Opname is te stil (volume te laag)
• Lange stiltes tijdens onderzoek (echo, ECG, etc.)
• Achtergrondgeluid overstemt spraak
• Microfoon stond te ver van spreker
• Technische problemen tijdens opname

{get_quiet_recording_solutions()}

💡 **Voor medische opnames:**
• Pauzeer opname tijdens lange onderzoeken
• Dicteer bevindingen direct na observatie
• Gebruik push-to-talk functie indien beschikbaar
• Test audio niveau vooraf met korte test-opname
    """
    
    return feedback

def get_quiet_recording_solutions():
    """Get specific solutions for quiet medical recordings"""
    return """
🔧 **Oplossingen voor stille opnames:**

**Directe oplossingen:**
• Verhoog volume van originele opname (Audacity, GarageBand)
• Normaliseer audio naar -6dB tot -3dB niveau
• Verwijder lange stiltes aan begin/einde
• Splits opname: spraak apart van onderzoek-momenten

**Voor toekomstige opnames:**
• Houd microfoon 5-15cm van mond
• Spreek iets luider dan normaal
• Pauzeer tijdens stille onderzoek-momenten
• Test volume vooraf met korte opname
• Gebruik externe microfoon indien mogelijk

**Audio bewerking tools:**
• Audacity (gratis): Amplify + Noise Reduction
• GarageBand (Mac): Volume normalisatie
• Online tools: TwistedWave, AudioMass
    """

def get_medical_recording_tips():
    """Get comprehensive tips for medical recordings"""
    return """
💡 **Tips voor medische opnames:**

**Tijdens consultatie:**
• Leg microfoon tussen arts en patiënt
• Spreek duidelijk naar microfoon
• Herhaal belangrijke informatie indien onduidelijk
• Vermijd ritselen met papieren bij microfoon

**Tijdens onderzoek:**
• Pauzeer opname tijdens stille procedures
• Dicteer bevindingen direct na observatie
• Beschrijf wat je doet: "Ik ga nu luisteren naar het hart"
• Gebruik korte, duidelijke zinnen

**Technische tips:**
• Test audio niveau vooraf (30 seconden test)
• Gebruik push-to-talk indien beschikbaar
• Houd microfoon consistent op zelfde afstand
• Vermijd ademgeluiden direct in microfoon
    """

def get_error_solutions(error_type):
    """Get specific solutions for different error types"""
    solutions = {
        'file_too_large': """
🔧 **Oplossingen voor grote bestanden:**
• Comprimeer naar MP3 met 64-128 kbps bitrate
• Splits lange opnames in segmenten van 15-20 minuten
• Verwijder stiltes aan begin/einde (kan 30-50% besparen)
• Gebruik online compressie tools: CloudConvert, Audacity
        """,
        'timeout': """
⏰ **Oplossingen voor timeout:**
• Probeer opnieuw - API kan soms overbelast zijn
• Splits opname in kortere segmenten (< 15 minuten)
• Controleer internetverbinding stabiliteit
• Probeer op ander tijdstip (minder druk)
        """,
        'quiet_recording': get_quiet_recording_solutions(),
        'format_error': """
📁 **Oplossingen voor formaat problemen:**
• Converteer naar MP3, WAV, of M4A
• Controleer of bestand niet beschadigd is
• Gebruik betrouwbare converter (Audacity, CloudConvert)
• Probeer opnieuw op te nemen in ondersteund formaat
        """
    }
    return solutions.get(error_type, "")

