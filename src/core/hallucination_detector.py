"""
Hallucination detection for Whisper transcriptions
Detects when Whisper generates repetitive or nonsensical content
"""
import re
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

class HallucinationDetector:
    """Detects hallucinations in Whisper transcriptions"""
    
    # Common hallucination patterns
    HALLUCINATION_PATTERNS = [
        # Repetitive phrases
        r'(.{10,50})\1{3,}',  # Same phrase repeated 3+ times
        
        # Common Dutch hallucination phrases
        r'(deze film|dit is|geschiedenis van|oorlog|informatie over).{0,50}\1',
        
        # Repetitive words
        r'\b(\w+)\s+\1\s+\1',  # Same word repeated 3 times
        
        # Medical hallucination patterns
        r'(medische|patiënt|arts|onderzoek).{0,30}\1.{0,30}\1',
        
        # West-Flemish specific patterns
        r'(west-vlaams|vlaams|nederlands).{0,50}\1.{0,50}\1',
    ]
    
    # Phrases that indicate hallucination
    HALLUCINATION_KEYWORDS = [
        'deze film is gespecialiseerd',
        'geschiedenis van de oorlog',
        'informatie over de geschiedenis',
        'dit is het gebouw waar',
        'we zijn op zoek naar',
    ]
    
    @classmethod
    def detect_hallucination(cls, text: str) -> Tuple[bool, str, List[str]]:
        """
        Detect if transcription contains hallucinations
        
        Returns:
            (is_hallucination, reason, detected_patterns)
        """
        if not text or len(text.strip()) < 10:
            return False, "Text too short to analyze", []
        
        text_lower = text.lower().strip()
        detected_patterns = []
        
        # Check for repetitive patterns
        for pattern in cls.HALLUCINATION_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                detected_patterns.append(f"Repetitive pattern: {pattern}")
                logger.warning(f"Detected repetitive pattern: {matches[:3]}")  # Log first 3 matches
        
        # Check for known hallucination keywords
        for keyword in cls.HALLUCINATION_KEYWORDS:
            if keyword in text_lower:
                detected_patterns.append(f"Hallucination keyword: {keyword}")
                logger.warning(f"Detected hallucination keyword: {keyword}")
        
        # Check repetition ratio
        words = text_lower.split()
        if len(words) > 10:
            unique_words = set(words)
            repetition_ratio = 1 - (len(unique_words) / len(words))
            
            if repetition_ratio > 0.7:  # More than 70% repetition
                detected_patterns.append(f"High repetition ratio: {repetition_ratio:.2f}")
                logger.warning(f"High repetition ratio detected: {repetition_ratio:.2f}")
        
        # Determine if it's a hallucination
        is_hallucination = len(detected_patterns) > 0
        
        if is_hallucination:
            reason = "Whisper hallucination detected - audio likely too quiet or unclear"
        else:
            reason = "Transcription appears legitimate"
        
        return is_hallucination, reason, detected_patterns
    
    @classmethod
    def get_hallucination_feedback(cls, text: str) -> str:
        """Get user-friendly feedback for hallucinated transcriptions"""
        
        is_hallucination, reason, patterns = cls.detect_hallucination(text)
        
        if not is_hallucination:
            return ""
        
        feedback = """
🚨 **Whisper Hallucinatie Gedetecteerd**

De transcriptie bevat herhalende of onzinnige inhoud. Dit gebeurt wanneer:
• De opname te zacht is
• Er lange stiltes zijn tijdens onderzoek
• De microfoon te ver staat
• Er veel achtergrondgeluid is

**🔧 Oplossingen:**

**Voor deze opname:**
1. **Volume verhogen** met audio-software:
   • Audacity (gratis): Effect → Amplify → +10dB tot +15dB
   • GarageBand: Track → Volume → Verhoog significant
   
2. **Stiltes verwijderen**:
   • Audacity: Effect → Truncate Silence
   • Knip handmatig stille delen weg

3. **Opname splitsen**:
   • Maak aparte bestanden voor gesprek vs onderzoek
   • Upload alleen de delen met spraak

**Voor toekomstige opnames:**
• Houd microfoon 5-15cm van mond
• Spreek iets luider dan normaal
• Pauzeer opname tijdens stille onderzoeken
• Test volume vooraf met korte opname

**💡 Tip:** Probeer eerst een klein segment (2-3 minuten) na volume-verhoging om te testen.
"""
        
        return feedback.strip()

    @classmethod
    def analyze_transcription_quality(cls, text: str) -> dict:
        """Comprehensive analysis of transcription quality"""
        
        if not text:
            return {
                'quality': 'empty',
                'score': 0,
                'issues': ['No transcription returned'],
                'recommendations': ['Check audio volume and clarity']
            }
        
        text_clean = text.strip()
        is_hallucination, reason, patterns = cls.detect_hallucination(text_clean)
        
        # Calculate quality score
        length_score = min(len(text_clean) / 100, 1.0)  # Longer is better (up to 100 chars)
        
        words = text_clean.split()
        unique_words = set(words)
        diversity_score = len(unique_words) / max(len(words), 1) if words else 0
        
        # Penalize hallucinations heavily
        hallucination_penalty = 0.8 if is_hallucination else 0
        
        quality_score = max(0, (length_score + diversity_score) / 2 - hallucination_penalty)
        
        # Determine quality level
        if quality_score < 0.2:
            quality = 'poor'
        elif quality_score < 0.5:
            quality = 'fair'
        elif quality_score < 0.8:
            quality = 'good'
        else:
            quality = 'excellent'
        
        # Identify issues
        issues = []
        recommendations = []
        
        if is_hallucination:
            issues.append('Hallucination detected')
            recommendations.append('Increase audio volume significantly')
            recommendations.append('Remove silent periods from recording')
        
        if len(text_clean) < 50:
            issues.append('Very short transcription')
            recommendations.append('Check if recording contains actual speech')
        
        if diversity_score < 0.3:
            issues.append('High repetition in content')
            recommendations.append('Verify audio quality and clarity')
        
        return {
            'quality': quality,
            'score': quality_score,
            'is_hallucination': is_hallucination,
            'issues': issues,
            'recommendations': recommendations,
            'detected_patterns': patterns,
            'character_count': len(text_clean),
            'word_count': len(words),
            'unique_word_ratio': diversity_score
        }

