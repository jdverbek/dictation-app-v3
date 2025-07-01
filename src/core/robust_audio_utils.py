"""
Robust audio utilities with improved error handling and memory management
Handles large files and provides better error reporting
"""

import io
import os
import tempfile
from typing import Tuple, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RobustAudioProcessor:
    """Robust audio file processor with improved error handling"""
    
    # OpenAI Whisper API limits
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB in bytes
    RECOMMENDED_SIZE = 20 * 1024 * 1024  # 20MB recommended limit
    SUPPORTED_FORMATS = ['wav', 'mp3', 'webm', 'm4a', 'aac', 'flac', 'ogg']
    
    @staticmethod
    def get_file_size(file_obj) -> int:
        """Get file size in bytes with error handling"""
        try:
            current_pos = file_obj.tell()
            file_obj.seek(0, 2)  # Seek to end
            size = file_obj.tell()
            file_obj.seek(current_pos)  # Reset to original position
            return size
        except Exception as e:
            logger.error(f"Error getting file size: {e}")
            return 0
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    @staticmethod
    def get_file_format(filename: str) -> str:
        """Extract file format from filename"""
        return filename.lower().split('.')[-1] if '.' in filename else ''
    
    @staticmethod
    def is_supported_format(filename: str) -> bool:
        """Check if file format is supported"""
        format_ext = RobustAudioProcessor.get_file_format(filename)
        return format_ext in RobustAudioProcessor.SUPPORTED_FORMATS
    
    @staticmethod
    def validate_audio_file(file_obj, filename: str) -> Tuple[bool, str, dict]:
        """
        Validate audio file for OpenAI API compatibility
        Returns (is_valid, message, metadata)
        """
        metadata = {
            'filename': filename,
            'format': RobustAudioProcessor.get_file_format(filename),
            'size_bytes': 0,
            'size_formatted': '0 B',
            'is_large': False,
            'recommendations': []
        }
        
        try:
            # Check if file format is supported
            if not RobustAudioProcessor.is_supported_format(filename):
                supported = ', '.join(RobustAudioProcessor.SUPPORTED_FORMATS)
                return False, f"❌ Niet-ondersteund bestandsformaat. Ondersteunde formaten: {supported}", metadata
            
            # Check file size
            file_size = RobustAudioProcessor.get_file_size(file_obj)
            if file_size == 0:
                return False, "❌ Bestand is leeg of onleesbaar", metadata
            
            metadata['size_bytes'] = file_size
            metadata['size_formatted'] = RobustAudioProcessor.format_file_size(file_size)
            
            # Check if file is too large
            if file_size > RobustAudioProcessor.MAX_FILE_SIZE:
                max_size = RobustAudioProcessor.format_file_size(RobustAudioProcessor.MAX_FILE_SIZE)
                metadata['recommendations'] = [
                    "Gebruik een audio editor om het bestand te comprimeren",
                    "Converteer naar MP3 met lagere bitrate (64-128 kbps)",
                    "Verwijder stiltes aan het begin en einde",
                    "Splits lange opnames in kleinere delen"
                ]
                return False, f"❌ Bestand te groot ({metadata['size_formatted']}). Maximum: {max_size}", metadata
            
            # Check if file is large (but still acceptable)
            if file_size > RobustAudioProcessor.RECOMMENDED_SIZE:
                metadata['is_large'] = True
                metadata['recommendations'] = [
                    "Groot bestand - verwerking kan langer duren",
                    "Voor snellere verwerking: comprimeer naar <20MB"
                ]
                return True, f"⚠️ Groot bestand geaccepteerd ({metadata['size_formatted']}) - verwerking kan langer duren", metadata
            
            return True, f"✅ Bestand geaccepteerd ({metadata['size_formatted']})", metadata
            
        except Exception as e:
            logger.error(f"Error validating audio file: {e}")
            return False, f"❌ Fout bij validatie: {str(e)}", metadata
    
    @staticmethod
    def prepare_file_for_api(file_obj, filename: str) -> Tuple[Optional[io.BytesIO], str]:
        """
        Prepare file for API submission with memory management
        Returns (file_stream, error_message)
        """
        try:
            # Reset file pointer
            file_obj.seek(0)
            
            # Read file data
            file_data = file_obj.read()
            
            # Create new BytesIO stream
            file_stream = io.BytesIO(file_data)
            file_stream.seek(0)
            
            logger.info(f"Prepared file {filename} for API submission")
            return file_stream, ""
            
        except MemoryError:
            error_msg = "❌ Bestand te groot voor geheugen - probeer een kleiner bestand"
            logger.error(f"Memory error preparing file {filename}")
            return None, error_msg
            
        except Exception as e:
            error_msg = f"❌ Fout bij voorbereiden bestand: {str(e)}"
            logger.error(f"Error preparing file {filename}: {e}")
            return None, error_msg


def get_audio_processing_tips() -> str:
    """Get comprehensive tips for users on audio file optimization"""
    return """
💡 **Tips voor audiobestand optimalisatie:**

📏 **Bestandsgrootte verkleinen:**
• Gebruik MP3-formaat in plaats van WAV
• Verlaag bitrate naar 64-128 kbps
• Converteer naar mono (1 kanaal)
• Verwijder stiltes aan begin/einde

🔧 **Aanbevolen tools:**
• Audacity (gratis audio editor)
• Online converters (CloudConvert, Zamzar)
• VLC Media Player (kan converteren)

⚡ **Voor snelle verwerking:**
• Houd bestanden onder 20MB
• Gebruik MP3 64kbps mono
• Splits lange opnames (>30 min) op

📋 **Ondersteunde formaten:**
MP3, WAV, M4A, WebM, AAC, FLAC, OGG

🚨 **Bij problemen:**
• Probeer een kleiner bestand eerst
• Controleer internetverbinding
• Wacht tot verwerking compleet is
"""


def get_error_solutions(error_type: str) -> str:
    """Get specific solutions for common errors"""
    solutions = {
        'file_too_large': """
🔧 **Oplossingen voor te groot bestand:**
1. Comprimeer naar MP3 64kbps
2. Verwijder stiltes met Audacity
3. Splits in delen van max 20MB
4. Gebruik online compressor
        """,
        'timeout': """
🔧 **Oplossingen voor timeout:**
1. Probeer kleiner bestand (<10MB)
2. Controleer internetverbinding
3. Probeer op ander tijdstip
4. Splits lange opnames op
        """,
        'format_error': """
🔧 **Oplossingen voor formaat fout:**
1. Converteer naar MP3
2. Gebruik ondersteund formaat
3. Controleer bestandsextensie
4. Probeer ander bestand
        """
    }
    return solutions.get(error_type, "Probeer een ander bestand of neem contact op voor ondersteuning.")

