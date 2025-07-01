"""
Audio utilities for handling file size limits and compression
Ensures audio files meet OpenAI API requirements (max 25MB)
"""

import os
import io
import tempfile
from typing import Tuple, Optional
import subprocess


class AudioProcessor:
    """Handles audio file processing for OpenAI API compatibility"""
    
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
    def is_file_too_large(file_obj) -> bool:
        """Check if file exceeds OpenAI API limit"""
        return AudioProcessor.get_file_size(file_obj) > AudioProcessor.MAX_FILE_SIZE
    
    @staticmethod
    def get_file_format(filename: str) -> str:
        """Extract file format from filename"""
        return filename.lower().split('.')[-1] if '.' in filename else ''
    
    @staticmethod
    def is_supported_format(filename: str) -> bool:
        """Check if file format is supported"""
        format_ext = AudioProcessor.get_file_format(filename)
        return format_ext in AudioProcessor.SUPPORTED_FORMATS
    
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
    def validate_audio_file(file_obj, filename: str) -> Tuple[bool, str]:
        """
        Validate audio file for OpenAI API compatibility
        Returns (is_valid, error_message)
        """
        # Check if file format is supported
        if not AudioProcessor.is_supported_format(filename):
            supported = ', '.join(AudioProcessor.SUPPORTED_FORMATS)
            return False, f"Niet-ondersteund bestandsformaat. Ondersteunde formaten: {supported}"
        
        # Check file size
        file_size = AudioProcessor.get_file_size(file_obj)
        if file_size == 0:
            return False, "Bestand is leeg"
        
        if AudioProcessor.is_file_too_large(file_obj):
            current_size = AudioProcessor.format_file_size(file_size)
            max_size = AudioProcessor.format_file_size(AudioProcessor.MAX_FILE_SIZE)
            return False, f"Bestand te groot ({current_size}). Maximum: {max_size}"
        
        return True, ""
    
    @staticmethod
    def compress_audio_ffmpeg(input_file, output_format='mp3', quality='medium') -> Optional[io.BytesIO]:
        """
        Compress audio using ffmpeg (if available)
        Returns compressed audio as BytesIO object or None if compression fails
        """
        try:
            # Check if ffmpeg is available
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
        
        try:
            with tempfile.NamedTemporaryFile(suffix=f'.{output_format}') as temp_output:
                # Quality settings for different levels
                quality_settings = {
                    'low': ['-b:a', '64k'],
                    'medium': ['-b:a', '128k'],
                    'high': ['-b:a', '192k']
                }
                
                # Build ffmpeg command
                cmd = [
                    'ffmpeg', '-i', input_file, '-y',  # -y to overwrite output
                    '-acodec', 'mp3' if output_format == 'mp3' else 'aac',
                    *quality_settings.get(quality, quality_settings['medium']),
                    temp_output.name
                ]
                
                # Run compression
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    # Read compressed file
                    with open(temp_output.name, 'rb') as f:
                        compressed_data = f.read()
                    return io.BytesIO(compressed_data)
                
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def try_compress_audio(file_obj, filename: str) -> Tuple[Optional[io.BytesIO], str]:
        """
        Attempt to compress audio file to meet size requirements
        Returns (compressed_file_obj, status_message)
        """
        original_size = AudioProcessor.get_file_size(file_obj)
        
        # Save original file to temp location for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{AudioProcessor.get_file_format(filename)}') as temp_file:
            file_obj.seek(0)
            temp_file.write(file_obj.read())
            temp_file_path = temp_file.name
        
        try:
            # Try compression with different quality levels
            for quality in ['medium', 'low']:
                compressed = AudioProcessor.compress_audio_ffmpeg(temp_file_path, 'mp3', quality)
                
                if compressed:
                    compressed_size = AudioProcessor.get_file_size(compressed)
                    
                    if compressed_size < AudioProcessor.MAX_FILE_SIZE:
                        original_mb = AudioProcessor.format_file_size(original_size)
                        compressed_mb = AudioProcessor.format_file_size(compressed_size)
                        compression_ratio = (1 - compressed_size / original_size) * 100
                        
                        message = f"Bestand gecomprimeerd: {original_mb} → {compressed_mb} ({compression_ratio:.1f}% kleiner)"
                        return compressed, message
            
            # If compression didn't work or isn't available
            return None, "Compressie niet beschikbaar of niet effectief genoeg"
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file_path)
            except:
                pass
    
    @staticmethod
    def prepare_audio_for_api(file_obj, filename: str) -> Tuple[Optional[io.BytesIO], str, str]:
        """
        Prepare audio file for OpenAI API submission
        Returns (processed_file_obj, final_filename, status_message)
        """
        # First validate the file
        is_valid, error_msg = AudioProcessor.validate_audio_file(file_obj, filename)
        
        if not is_valid:
            return None, filename, f"❌ {error_msg}"
        
        # If file is within size limits, use as-is
        if not AudioProcessor.is_file_too_large(file_obj):
            file_size = AudioProcessor.format_file_size(AudioProcessor.get_file_size(file_obj))
            return file_obj, filename, f"✅ Bestand geaccepteerd ({file_size})"
        
        # File is too large, try compression
        compressed_file, compression_msg = AudioProcessor.try_compress_audio(file_obj, filename)
        
        if compressed_file:
            # Change filename to indicate compression
            base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
            compressed_filename = f"{base_name}_compressed.mp3"
            return compressed_file, compressed_filename, f"✅ {compression_msg}"
        
        # Compression failed
        file_size = AudioProcessor.format_file_size(AudioProcessor.get_file_size(file_obj))
        max_size = AudioProcessor.format_file_size(AudioProcessor.MAX_FILE_SIZE)
        return None, filename, f"❌ Bestand te groot ({file_size}) en compressie mislukt. Maximum: {max_size}"


def get_audio_processing_tips() -> str:
    """Get tips for users on how to reduce audio file size"""
    return """
💡 Tips voor het verkleinen van audiobestanden:

1. **Gebruik MP3-formaat** in plaats van WAV
2. **Verlaag de bitrate** naar 128kbps of lager
3. **Converteer naar mono** in plaats van stereo
4. **Verkort de opname** door stiltes te verwijderen
5. **Gebruik audio-editing software** zoals Audacity (gratis)

📏 **Limieten:**
- Maximum bestandsgrootte: 25MB
- Ondersteunde formaten: MP3, WAV, M4A, WebM, AAC, FLAC, OGG
"""

