"""
Odd Words Detection Agent
Identifies words that don't make sense in medical context and flags them as potential drug names
Part of the multi-agent iterative feedback system
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import sqlite3
from collections import Counter

logger = logging.getLogger(__name__)

@dataclass
class OddWord:
    """Represents a word that seems out of place"""
    word: str
    position: int
    context_before: str
    context_after: str
    oddness_score: float
    potential_type: str  # 'drug', 'medical_term', 'unknown'
    suggestions: List[str]

class OddWordsDetector:
    """Detects words that seem odd in medical context and suggests corrections"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.medical_vocabulary = set()
        self.common_words = set()
        self.drug_patterns = {}
        self._initialize_vocabularies()
    
    def _initialize_vocabularies(self):
        """Initialize medical and common vocabularies"""
        
        # Common Dutch medical vocabulary
        self.medical_vocabulary = {
            # Body parts
            'hart', 'longen', 'lever', 'nieren', 'maag', 'darm', 'hoofd', 'nek', 'borst',
            'buik', 'rug', 'armen', 'benen', 'handen', 'voeten', 'ogen', 'oren', 'neus',
            'mond', 'keel', 'huid', 'spieren', 'botten', 'gewrichten',
            
            # Medical conditions
            'hypertensie', 'diabetes', 'hartfalen', 'angina', 'aritmie', 'infectie',
            'koorts', 'pijn', 'hoofdpijn', 'buikpijn', 'rugpijn', 'hoest', 'kortademigheid',
            'misselijkheid', 'braken', 'diarree', 'constipatie', 'duizeligheid',
            'vermoeidheid', 'zwakte', 'oedeem', 'zwelling',
            
            # Medical procedures
            'onderzoek', 'bloedonderzoek', 'urine', 'röntgen', 'echo', 'ct', 'mri',
            'ecg', 'ekg', 'bloeddruk', 'pols', 'temperatuur', 'gewicht', 'lengte',
            
            # Medical terms
            'diagnose', 'behandeling', 'medicatie', 'dosering', 'bijwerkingen',
            'contraindicaties', 'interacties', 'monitoring', 'follow-up', 'controle',
            'therapie', 'prognose', 'symptomen', 'klachten', 'anamnese',
            
            # Time/frequency
            'dagelijks', 'tweemaal', 'driemaal', 'ochtend', 'middag', 'avond', 'nacht',
            'voor', 'na', 'tijdens', 'maaltijd', 'week', 'maand', 'jaar',
            
            # Dosage terms
            'milligram', 'gram', 'tablet', 'capsule', 'druppels', 'siroop',
            'injectie', 'infuus', 'pleister', 'zalf', 'crème'
        }
        
        # Common Dutch words
        self.common_words = {
            'de', 'het', 'een', 'en', 'van', 'in', 'op', 'met', 'voor', 'door',
            'bij', 'aan', 'uit', 'over', 'onder', 'tussen', 'tegen', 'zonder',
            'is', 'was', 'zijn', 'heeft', 'had', 'kan', 'moet', 'zal', 'zou',
            'deze', 'die', 'dit', 'dat', 'hier', 'daar', 'waar', 'wanneer',
            'hoe', 'wat', 'wie', 'waarom', 'omdat', 'als', 'maar', 'dus',
            'ook', 'nog', 'wel', 'niet', 'geen', 'alle', 'veel', 'weinig',
            'groot', 'klein', 'goed', 'slecht', 'nieuw', 'oud', 'jong',
            'patiënt', 'patient', 'meneer', 'mevrouw', 'man', 'vrouw'
        }
        
        # Drug name patterns (phonetic patterns that suggest drug names)
        self.drug_patterns = {
            'beta_blocker': [
                r'\w*olol\w*',  # -olol ending (atenolol, bisoprolol)
                r'\w*prol\w*',  # -prol pattern
            ],
            'ace_inhibitor': [
                r'\w*pril\w*',  # -pril ending (enalapril, lisinopril)
            ],
            'arb': [
                r'\w*sartan\w*',  # -sartan ending (losartan, valsartan)
            ],
            'statin': [
                r'\w*statin\w*',  # -statin ending (atorvastatin)
            ],
            'calcium_blocker': [
                r'\w*dipine\w*',  # -dipine ending (amlodipine)
            ],
            'diuretic': [
                r'\w*ide\w*',     # -ide ending (furosemide)
                r'\w*thiazide\w*' # thiazide pattern
            ],
            'anticoagulant': [
                r'\w*arin\w*',    # -arin ending (warfarin)
                r'\w*xaban\w*',   # -xaban ending (rivaroxaban)
                r'\w*gatran\w*'   # -gatran ending (dabigatran)
            ]
        }
    
    def detect_odd_words(self, transcript: str, context: str = "") -> List[OddWord]:
        """Detect words that seem odd in medical context"""
        
        words = re.findall(r'\b\w+\b', transcript)
        odd_words = []
        
        for i, word in enumerate(words):
            word_lower = word.lower()
            
            # Skip if it's a known medical or common word
            if (word_lower in self.medical_vocabulary or 
                word_lower in self.common_words or
                len(word) < 3 or
                word.isdigit()):
                continue
            
            # Calculate oddness score
            oddness_score = self._calculate_oddness_score(word, i, words, context)
            
            if oddness_score > 0.4:  # Lowered threshold to catch more potential drugs
                # Get context
                context_before = ' '.join(words[max(0, i-3):i])
                context_after = ' '.join(words[i+1:min(len(words), i+4)])
                
                # Determine potential type
                potential_type = self._classify_odd_word(word, context_before, context_after)
                
                # Get suggestions
                suggestions = self._get_suggestions(word, potential_type, context_before + " " + context_after)
                
                odd_word = OddWord(
                    word=word,
                    position=i,
                    context_before=context_before,
                    context_after=context_after,
                    oddness_score=oddness_score,
                    potential_type=potential_type,
                    suggestions=suggestions
                )
                
                odd_words.append(odd_word)
        
        return odd_words
    
    def _calculate_oddness_score(self, word: str, position: int, all_words: List[str], context: str) -> float:
        """Calculate how 'odd' a word is in medical context"""
        
        score = 0.0
        word_lower = word.lower()
        
        # First check if it's a known correction - if so, mark as very odd
        known_corrections = {
            'sedocar': 'cedocard', 'sedocard': 'cedocard', 'biso': 'bisoprolol',
            'metro': 'metoprolol', 'aten': 'atenolol', 'carve': 'carvedilol'
        }
        
        if word_lower in known_corrections:
            return 0.9  # Very high oddness for known mispronunciations
        
        # 1. Check if it looks like a drug name pattern
        drug_pattern_score = self._check_drug_patterns(word)
        score += drug_pattern_score * 0.4
        
        # 2. Check if it's in a drug context
        context_score = self._check_drug_context(position, all_words)
        score += context_score * 0.3
        
        # 3. Check phonetic similarity to known drugs
        phonetic_score = self._check_phonetic_drug_similarity(word)
        score += phonetic_score * 0.2
        
        # 4. Check if it's a non-Dutch word pattern
        foreign_score = self._check_foreign_pattern(word)
        score += foreign_score * 0.1
        
        # 5. Check if it's not in any vocabulary (unknown word)
        if (word_lower not in self.medical_vocabulary and 
            word_lower not in self.common_words and
            len(word) > 4):
            score += 0.3  # Unknown words are potentially odd
        
        return min(score, 1.0)
    
    def _check_drug_patterns(self, word: str) -> float:
        """Check if word matches drug name patterns"""
        
        word_lower = word.lower()
        pattern_score = 0.0
        
        for drug_class, patterns in self.drug_patterns.items():
            for pattern in patterns:
                if re.match(pattern, word_lower):
                    pattern_score = max(pattern_score, 0.8)
        
        # Additional drug-like patterns
        drug_indicators = [
            r'^[a-z]+ol$',      # ends with -ol
            r'^[a-z]+ine$',     # ends with -ine
            r'^[a-z]+ide$',     # ends with -ide
            r'^[a-z]+rin$',     # ends with -rin
            r'^[a-z]+tan$',     # ends with -tan
            r'^[a-z]+pril$',    # ends with -pril
            r'^[a-z]+statin$',  # ends with -statin
            r'^[a-z]*card$',    # ends with -card (like cedocard)
            r'^[a-z]*car$',     # ends with -car (like sedocar)
            r'^[a-z]+mide$',    # ends with -mide
        ]
        
        for pattern in drug_indicators:
            if re.match(pattern, word_lower):
                pattern_score = max(pattern_score, 0.6)
        
        return pattern_score
    
    def _check_drug_context(self, position: int, words: List[str]) -> float:
        """Check if word appears in drug-related context"""
        
        # Get surrounding context
        start = max(0, position - 5)
        end = min(len(words), position + 6)
        context_words = [w.lower() for w in words[start:end]]
        
        # Drug context indicators
        drug_context_words = {
            'medicatie', 'medicijn', 'geneesmiddel', 'tablet', 'capsule',
            'voorschrijven', 'innemen', 'slikken', 'dosering', 'mg', 'gram',
            'dagelijks', 'tweemaal', 'driemaal', 'ochtend', 'avond',
            'behandeling', 'therapie', 'stoppen', 'starten', 'verhogen',
            'verlagen', 'bijwerkingen', 'allergisch', 'contra-indicatie'
        }
        
        context_score = 0.0
        for context_word in drug_context_words:
            if context_word in context_words:
                context_score += 0.2
        
        return min(context_score, 1.0)
    
    def _check_phonetic_drug_similarity(self, word: str) -> float:
        """Check phonetic similarity to known drugs"""
        
        # Known Belgian drug names for comparison
        known_drugs = [
            'bisoprolol', 'atenolol', 'metoprolol', 'carvedilol', 'nebivolol',
            'enalapril', 'lisinopril', 'ramipril', 'perindopril',
            'losartan', 'valsartan', 'irbesartan', 'candesartan',
            'amlodipine', 'nifedipine', 'felodipine',
            'furosemide', 'hydrochlorothiazide', 'spironolactone',
            'atorvastatin', 'simvastatin', 'rosuvastatin',
            'warfarin', 'rivaroxaban', 'apixaban', 'dabigatran',
            'metformin', 'gliclazide', 'insulin',
            'paracetamol', 'ibuprofen', 'diclofenac',
            'amoxicillin', 'azithromycin', 'ciprofloxacin',
            'cedocard', 'isosorbide', 'nitroglycerin'  # Added Cedocard and related
        ]
        
        max_similarity = 0.0
        word_lower = word.lower()
        
        for drug in known_drugs:
            similarity = self._phonetic_similarity(word_lower, drug)
            max_similarity = max(max_similarity, similarity)
        
        return max_similarity
    
    def _check_foreign_pattern(self, word: str) -> float:
        """Check if word has foreign/pharmaceutical naming patterns"""
        
        word_lower = word.lower()
        
        # Pharmaceutical naming patterns
        pharma_patterns = [
            r'[xz]',           # Contains x or z (common in drug names)
            r'ph',             # Contains ph
            r'th',             # Contains th
            r'qu',             # Contains qu
            r'[aeiou]{3,}',    # Multiple vowels together
            r'[bcdfghjklmnpqrstvwxyz]{3,}',  # Multiple consonants
        ]
        
        pattern_score = 0.0
        for pattern in pharma_patterns:
            if re.search(pattern, word_lower):
                pattern_score += 0.2
        
        return min(pattern_score, 1.0)
    
    def _classify_odd_word(self, word: str, context_before: str, context_after: str) -> str:
        """Classify what type of odd word this might be"""
        
        # Check drug patterns
        if self._check_drug_patterns(word) > 0.5:
            return 'drug'
        
        # Check medical term patterns
        medical_suffixes = ['itis', 'osis', 'emia', 'uria', 'algia', 'pathy', 'scopy']
        if any(word.lower().endswith(suffix) for suffix in medical_suffixes):
            return 'medical_term'
        
        # Check context clues
        full_context = (context_before + " " + context_after).lower()
        
        if any(indicator in full_context for indicator in ['medicatie', 'tablet', 'mg', 'dosering']):
            return 'drug'
        elif any(indicator in full_context for indicator in ['diagnose', 'aandoening', 'ziekte']):
            return 'medical_term'
        
        return 'unknown'
    
    def _get_suggestions(self, word: str, potential_type: str, context: str) -> List[str]:
        """Get suggestions for what the odd word might be"""
        
        suggestions = []
        
        if potential_type == 'drug':
            # Get drug suggestions based on phonetic similarity
            drug_suggestions = self._get_drug_suggestions(word, context)
            suggestions.extend(drug_suggestions)
        
        elif potential_type == 'medical_term':
            # Get medical term suggestions
            medical_suggestions = self._get_medical_term_suggestions(word, context)
            suggestions.extend(medical_suggestions)
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def _get_drug_suggestions(self, word: str, context: str) -> List[str]:
        """Get drug name suggestions for an odd word"""
        
        # Known drug corrections for common speech recognition errors
        common_corrections = {
            'sedocar': 'cedocard',
            'sedocard': 'cedocard',
            'cedo card': 'cedocard',
            'sedo card': 'cedocard',
            'biso': 'bisoprolol',
            'aten': 'atenolol',
            'metro': 'metoprolol',
            'carve': 'carvedilol',
            'enal': 'enalapril',
            'lisin': 'lisinopril',
            'losar': 'losartan',
            'valsar': 'valsartan',
            'amlo': 'amlodipine',
            'furo': 'furosemide',
            'ator': 'atorvastatin',
            'simva': 'simvastatin',
            'para': 'paracetamol',
            'ibu': 'ibuprofen',
            'amoxi': 'amoxicillin',
            'azithro': 'azithromycin',
            # Add more common mispronunciations
            'isosorbid': 'isosorbide',
            'nitroglycerine': 'nitroglycerin',
            'acetylsalicyl': 'acetylsalicylic acid'
        }
        
        word_lower = word.lower()
        suggestions = []
        
        # Check direct corrections
        if word_lower in common_corrections:
            suggestions.append(common_corrections[word_lower])
        
        # Check partial matches
        for partial, full in common_corrections.items():
            if partial in word_lower or word_lower in partial:
                if full not in suggestions:
                    suggestions.append(full)
        
        # Phonetic matching with known drugs
        known_drugs = [
            'bisoprolol', 'atenolol', 'metoprolol', 'carvedilol', 'nebivolol', 'propranolol',
            'enalapril', 'lisinopril', 'ramipril', 'perindopril',
            'losartan', 'valsartan', 'irbesartan', 'candesartan',
            'amlodipine', 'nifedipine', 'felodipine',
            'furosemide', 'hydrochlorothiazide', 'spironolactone',
            'atorvastatin', 'simvastatin', 'rosuvastatin',
            'warfarin', 'rivaroxaban', 'apixaban', 'dabigatran',
            'metformin', 'gliclazide', 'insulin',
            'paracetamol', 'ibuprofen', 'diclofenac',
            'amoxicillin', 'azithromycin', 'ciprofloxacin',
            'cedocard', 'isosorbide', 'nitroglycerin'
        ]
        
        for drug in known_drugs:
            similarity = self._phonetic_similarity(word_lower, drug)
            if similarity > 0.6 and drug not in suggestions:
                suggestions.append(drug)
        
        return suggestions
    
    def _get_medical_term_suggestions(self, word: str, context: str) -> List[str]:
        """Get medical term suggestions"""
        
        medical_terms = [
            'hypertensie', 'hypotensie', 'tachycardie', 'bradycardie',
            'aritmie', 'fibrillatie', 'angina', 'infarct',
            'diabetes', 'hyperglykemie', 'hypoglykemie',
            'pneumonie', 'bronchitis', 'astma', 'copd',
            'gastritis', 'ulcus', 'reflux', 'colitis'
        ]
        
        suggestions = []
        word_lower = word.lower()
        
        for term in medical_terms:
            similarity = self._phonetic_similarity(word_lower, term)
            if similarity > 0.6:
                suggestions.append(term)
        
        return suggestions
    
    def _phonetic_similarity(self, word1: str, word2: str) -> float:
        """Calculate phonetic similarity between words"""
        
        # Simple phonetic similarity
        if not word1 or not word2:
            return 0.0
        
        # Normalize for comparison
        w1 = re.sub(r'[^a-z]', '', word1.lower())
        w2 = re.sub(r'[^a-z]', '', word2.lower())
        
        if w1 == w2:
            return 1.0
        
        # Calculate character overlap
        common_chars = set(w1) & set(w2)
        total_chars = set(w1) | set(w2)
        
        if not total_chars:
            return 0.0
        
        char_similarity = len(common_chars) / len(total_chars)
        
        # Calculate position-based similarity
        min_len = min(len(w1), len(w2))
        max_len = max(len(w1), len(w2))
        
        position_matches = 0
        for i in range(min_len):
            if w1[i] == w2[i]:
                position_matches += 1
        
        position_similarity = position_matches / max_len if max_len > 0 else 0
        
        # Combine similarities
        return (char_similarity * 0.4 + position_similarity * 0.6)
    
    def process_transcript_for_odd_words(self, transcript: str, medical_context: str = "") -> Dict:
        """Process transcript to find and suggest corrections for odd words"""
        
        try:
            odd_words = self.detect_odd_words(transcript, medical_context)
            
            corrected_transcript = transcript
            corrections_made = []
            
            # Process odd words from end to start to maintain positions
            for odd_word in reversed(odd_words):
                if odd_word.suggestions and odd_word.oddness_score > 0.7:
                    # Use the best suggestion
                    best_suggestion = odd_word.suggestions[0]
                    
                    # Replace in transcript
                    words = transcript.split()
                    if odd_word.position < len(words):
                        original_word = words[odd_word.position]
                        words[odd_word.position] = best_suggestion
                        corrected_transcript = ' '.join(words)
                        
                        corrections_made.append({
                            'original': original_word,
                            'corrected': best_suggestion,
                            'confidence': 1.0 - odd_word.oddness_score,
                            'type': odd_word.potential_type,
                            'context': f"{odd_word.context_before} [{original_word}] {odd_word.context_after}",
                            'reasoning': f"Detected as odd word (score: {odd_word.oddness_score:.2f}), suggested: {best_suggestion}"
                        })
            
            return {
                'corrected_transcript': corrected_transcript,
                'odd_words_found': len(odd_words),
                'corrections_made': corrections_made,
                'odd_words_details': [
                    {
                        'word': ow.word,
                        'oddness_score': ow.oddness_score,
                        'type': ow.potential_type,
                        'suggestions': ow.suggestions
                    } for ow in odd_words
                ]
            }
            
        except Exception as e:
            logger.error(f"Odd words processing error: {e}")
            return {
                'corrected_transcript': transcript,
                'odd_words_found': 0,
                'corrections_made': [],
                'error': str(e)
            }
    
    def add_to_vocabulary(self, word: str, word_type: str = 'medical'):
        """Add word to appropriate vocabulary to reduce false positives"""
        
        if word_type == 'medical':
            self.medical_vocabulary.add(word.lower())
        elif word_type == 'common':
            self.common_words.add(word.lower())
    
    def get_detection_stats(self) -> Dict:
        """Get statistics about the odd words detection"""
        
        return {
            'medical_vocabulary_size': len(self.medical_vocabulary),
            'common_vocabulary_size': len(self.common_words),
            'drug_patterns_count': sum(len(patterns) for patterns in self.drug_patterns.values()),
            'detection_threshold': 0.6,
            'supported_languages': ['Dutch', 'Medical Latin']
        }

def get_odd_words_detector(db_path: str) -> OddWordsDetector:
    """Get or create the odd words detector"""
    return OddWordsDetector(db_path)

