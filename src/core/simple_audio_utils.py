"""
Simple audio utilities for file size validation
Handles OpenAI API file size limits without complex dependencies
"""

import io
from typing import Tuple


class SimpleAudioProcessor:
    """Simple audio file processor for OpenAI API compatibility"""
    
    # OpenAI Whisper API limits
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB in bytes
    SUPPORTED_FORMATS = ['wav', 'mp3', 'webm', 'm4a', 'aac', 'flac', 'ogg']
    
    @staticmethod
    def get_file_size(file_obj) -> int:
        """Get file size in bytes"""
        file_obj.seek(0, 2)  # Seek to end
        size = file_obj.tell()
        file_obj.seek(0)  # Reset to beginning
        return size
    
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
        format_ext = SimpleAudioProcessor.get_file_format(filename)
        return format_ext in SimpleAudioProcessor.SUPPORTED_FORMATS
    
    @staticmethod
    def validate_audio_file(file_obj, filename: str) -> Tuple[bool, str]:
        """
        Validate audio file for OpenAI API compatibility
        Returns (is_valid, message)
        """
        # Check if file format is supported
        if not SimpleAudioProcessor.is_supported_format(filename):
            supported = ', '.join(SimpleAudioProcessor.SUPPORTED_FORMATS)
            return False, f"❌ Niet-ondersteund bestandsformaat. Ondersteunde formaten: {supported}"
        
        # Check file size
        file_size = SimpleAudioProcessor.get_file_size(file_obj)
        if file_size == 0:
            return False, "❌ Bestand is leeg"
        
        formatted_size = SimpleAudioProcessor.format_file_size(file_size)
        
        if file_size > SimpleAudioProcessor.MAX_FILE_SIZE:
            max_size = SimpleAudioProcessor.format_file_size(SimpleAudioProcessor.MAX_FILE_SIZE)
            return False, f"❌ Bestand te groot ({formatted_size}). Maximum: {max_size}"
        
        return True, f"✅ Bestand geaccepteerd ({formatted_size})"


def get_simple_audio_tips() -> str:
    """Get tips for users on how to reduce audio file size"""
    return """
💡 Tips voor het verkleinen van audiobestanden:

1. **Gebruik MP3-formaat** in plaats van WAV
2. **Verlaag de bitrate** naar 128kbps of lager  
3. **Converteer naar mono** in plaats van stereo
4. **Verkort de opname** door stiltes te verwijderen
5. **Gebruik online converters** zoals CloudConvert of Zamzar

📏 **Limieten:**
- Maximum bestandsgrootte: 25MB
- Ondersteunde formaten: MP3, WAV, M4A, WebM, AAC, FLAC, OGG

🔧 **Snelle oplossing:**
Upload uw bestand naar een online audio compressor en download het gecomprimeerde bestand.
"""

