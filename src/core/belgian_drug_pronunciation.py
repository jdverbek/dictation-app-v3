"""
Belgian Drug Pronunciation System
Handles how Belgian doctors pronounce drug names in Dutch/French medical context
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import sqlite3

logger = logging.getLogger(__name__)

@dataclass
class PronunciationVariant:
    """Represents different ways a drug can be pronounced"""
    original_name: str
    pronunciation_variants: List[str]
    phonetic_pattern: str
    language: str  # 'nl', 'fr', 'mixed'
    confidence: float

class BelgianDrugPronunciation:
    """Handles Belgian-specific drug pronunciation patterns"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.pronunciation_db = {}
        self.phonetic_patterns = {}
        self._initialize_pronunciation_database()
    
    def _initialize_pronunciation_database(self):
        """Initialize the pronunciation database with Belgian patterns"""
        
        # Common Belgian pronunciation patterns for drug names
        self.belgian_patterns = {
            # Beta-blockers
            'bisoprolol': [
                'biso prolol', 'biso prol ol', 'bisoprolol', 'biso', 'bisoprol',
                'bisocard', 'bisobloc', 'bisoprolol eg', 'bisoprolol sandoz'
            ],
            'atenolol': [
                'atenolol', 'aten olol', 'aten ol', 'tenormin', 'atenol'
            ],
            'metoprolol': [
                'metoprolol', 'meto prolol', 'meto prol', 'lopressor', 'seloken',
                'metoprolol tartrate', 'metoprolol succinate'
            ],
            'carvedilol': [
                'carvedilol', 'carve dilol', 'kredex', 'dilatrend'
            ],
            'nebivolol': [
                'nebivolol', 'nebi volol', 'nebi vol', 'nobiten'
            ],
            'propranolol': [
                'propranolol', 'propran olol', 'inderal', 'propra'
            ],
            
            # ACE Inhibitors
            'enalapril': [
                'enalapril', 'enal april', 'renitec', 'enalapril eg'
            ],
            'lisinopril': [
                'lisinopril', 'lisin opril', 'zestril', 'prinivil'
            ],
            'ramipril': [
                'ramipril', 'rami pril', 'tritace', 'ramipril eg'
            ],
            'perindopril': [
                'perindopril', 'perin dopril', 'coversyl', 'perindopril eg'
            ],
            
            # ARBs (Sartans)
            'losartan': [
                'losartan', 'losar tan', 'cozaar', 'losartan eg'
            ],
            'valsartan': [
                'valsartan', 'valsar tan', 'diovan', 'valsartan eg'
            ],
            'irbesartan': [
                'irbesartan', 'irbe sartan', 'aprovel', 'irbesartan eg'
            ],
            'candesartan': [
                'candesartan', 'cande sartan', 'atacand', 'candesartan eg'
            ],
            
            # Diuretics
            'furosemide': [
                'furosemide', 'furo semide', 'lasix', 'furosemide eg'
            ],
            'hydrochlorothiazide': [
                'hydrochlorothiazide', 'hydrochloro thiazide', 'hctz', 'esidrex'
            ],
            'spironolactone': [
                'spironolactone', 'spirono lactone', 'aldactone'
            ],
            
            # Statins
            'atorvastatin': [
                'atorvastatin', 'ator vastatin', 'lipitor', 'atorvastatin eg'
            ],
            'simvastatin': [
                'simvastatin', 'simva statin', 'zocor', 'simvastatin eg'
            ],
            'rosuvastatin': [
                'rosuvastatin', 'rosu vastatin', 'crestor', 'rosuvastatin eg'
            ],
            
            # Calcium Channel Blockers
            'amlodipine': [
                'amlodipine', 'amlo dipine', 'norvasc', 'amlodipine eg'
            ],
            'nifedipine': [
                'nifedipine', 'nife dipine', 'adalat', 'nifedipine eg'
            ],
            
            # Anticoagulants
            'warfarin': [
                'warfarin', 'warfa rin', 'marevan', 'coumadin'
            ],
            'rivaroxaban': [
                'rivaroxaban', 'riva roxaban', 'xarelto'
            ],
            'apixaban': [
                'apixaban', 'api xaban', 'eliquis'
            ],
            'dabigatran': [
                'dabigatran', 'dabi gatran', 'pradaxa'
            ],
            
            # Antiplatelets
            'clopidogrel': [
                'clopidogrel', 'clopi dogrel', 'plavix', 'clopidogrel eg'
            ],
            'acetylsalicylic acid': [
                'acetylsalicylic acid', 'aspirin', 'aspirine', 'cardioaspirin',
                'acetyl salicyl', 'asa', 'asaflow'
            ],
            
            # Diabetes medications
            'metformin': [
                'metformin', 'metfor min', 'glucophage', 'metformin eg'
            ],
            'gliclazide': [
                'gliclazide', 'glic lazide', 'diamicron', 'gliclazide eg'
            ],
            
            # Antibiotics
            'amoxicillin': [
                'amoxicillin', 'amoxi cillin', 'clamoxyl', 'amoxicillin eg'
            ],
            'azithromycin': [
                'azithromycin', 'azithro mycin', 'zithromax', 'azithromycin eg'
            ],
            
            # Pain medications
            'paracetamol': [
                'paracetamol', 'para cetamol', 'dafalgan', 'panadol', 'acetaminophen'
            ],
            'ibuprofen': [
                'ibuprofen', 'ibu profen', 'brufen', 'nurofen', 'ibuprofen eg'
            ],
            'diclofenac': [
                'diclofenac', 'diclo fenac', 'voltaren', 'diclofenac eg'
            ]
        }
        
        # Belgian-specific pronunciation rules
        self.belgian_pronunciation_rules = {
            # Dutch pronunciation patterns
            'nl': {
                'ij': 'ei',  # Dutch ij sound
                'ch': 'g',   # Dutch ch sound
                'sch': 'sg', # Dutch sch sound
                'oe': 'u',   # Dutch oe sound
            },
            # French pronunciation patterns
            'fr': {
                'ph': 'f',
                'th': 't',
                'ch': 'sh',
                'qu': 'k'
            }
        }
        
        self._build_pronunciation_database()
    
    def _build_pronunciation_database(self):
        """Build the pronunciation database"""
        for generic_name, variants in self.belgian_patterns.items():
            self.pronunciation_db[generic_name] = PronunciationVariant(
                original_name=generic_name,
                pronunciation_variants=variants,
                phonetic_pattern=self._create_phonetic_pattern(generic_name),
                language='mixed',  # Most Belgian doctors use mixed Dutch/French
                confidence=0.9
            )
    
    def _create_phonetic_pattern(self, drug_name: str) -> str:
        """Create phonetic pattern for drug name"""
        # Simplify to phonetic representation
        phonetic = drug_name.lower()
        
        # Apply Belgian pronunciation rules
        phonetic = re.sub(r'ph', 'f', phonetic)
        phonetic = re.sub(r'th', 't', phonetic)
        phonetic = re.sub(r'ch', 'k', phonetic)
        phonetic = re.sub(r'qu', 'k', phonetic)
        phonetic = re.sub(r'x', 'ks', phonetic)
        phonetic = re.sub(r'c([ei])', r'z\1', phonetic)  # c before e/i becomes z
        
        return phonetic
    
    def find_drug_by_pronunciation(self, spoken_text: str, context: str = "") -> List[Dict]:
        """Find drugs based on how they might be pronounced"""
        spoken_text = spoken_text.lower().strip()
        matches = []
        
        for generic_name, pronunciation_data in self.pronunciation_db.items():
            # Check exact matches first
            for variant in pronunciation_data.pronunciation_variants:
                if variant.lower() in spoken_text:
                    confidence = self._calculate_confidence(spoken_text, variant, context, generic_name)
                    matches.append({
                        'generic_name': generic_name,
                        'matched_variant': variant,
                        'confidence': confidence,
                        'match_type': 'exact'
                    })
            
            # Check phonetic similarity
            phonetic_score = self._phonetic_similarity(spoken_text, pronunciation_data.phonetic_pattern)
            if phonetic_score > 0.7:
                confidence = phonetic_score * self._get_context_boost(generic_name, context)
                matches.append({
                    'generic_name': generic_name,
                    'matched_variant': pronunciation_data.phonetic_pattern,
                    'confidence': confidence,
                    'match_type': 'phonetic'
                })
        
        # Sort by confidence and return top matches
        matches.sort(key=lambda x: x['confidence'], reverse=True)
        return matches[:5]  # Return top 5 matches
    
    def _calculate_confidence(self, spoken_text: str, variant: str, context: str, generic_name: str) -> float:
        """Calculate confidence score for drug match"""
        base_confidence = 0.8
        
        # Exact match bonus
        if variant.lower() == spoken_text.lower():
            base_confidence = 0.95
        elif variant.lower() in spoken_text.lower():
            base_confidence = 0.85
        
        # Context boost
        context_boost = self._get_context_boost(generic_name, context)
        
        # Length similarity
        length_similarity = 1 - abs(len(variant) - len(spoken_text)) / max(len(variant), len(spoken_text))
        
        return min(base_confidence * context_boost * (0.7 + 0.3 * length_similarity), 1.0)
    
    def _get_context_boost(self, generic_name: str, context: str) -> float:
        """Get context-based confidence boost"""
        if not context:
            return 1.0
        
        context_lower = context.lower()
        
        # Medical condition context mapping
        condition_drug_mapping = {
            'hypertensie': ['bisoprolol', 'atenolol', 'metoprolol', 'amlodipine', 'enalapril', 'losartan'],
            'hartfalen': ['bisoprolol', 'carvedilol', 'enalapril', 'furosemide', 'spironolactone'],
            'diabetes': ['metformin', 'gliclazide', 'insulin'],
            'cholesterol': ['atorvastatin', 'simvastatin', 'rosuvastatin'],
            'angina': ['bisoprolol', 'metoprolol', 'amlodipine', 'isosorbide'],
            'aritmie': ['metoprolol', 'propranolol', 'sotalol', 'amiodarone'],
            'anticoagulatie': ['warfarin', 'rivaroxaban', 'apixaban', 'dabigatran'],
            'pijn': ['paracetamol', 'ibuprofen', 'diclofenac', 'tramadol'],
            'infectie': ['amoxicillin', 'azithromycin', 'ciprofloxacin']
        }
        
        boost = 1.0
        for condition, drugs in condition_drug_mapping.items():
            if condition in context_lower and generic_name in drugs:
                boost += 0.3
        
        # Department context
        department_drug_mapping = {
            'cardiologie': ['bisoprolol', 'metoprolol', 'atorvastatin', 'clopidogrel', 'warfarin'],
            'interne': ['metformin', 'furosemide', 'enalapril', 'amlodipine'],
            'pneumologie': ['salbutamol', 'budesonide', 'theophylline'],
            'neurologie': ['levodopa', 'gabapentin', 'phenytoin']
        }
        
        for dept, drugs in department_drug_mapping.items():
            if dept in context_lower and generic_name in drugs:
                boost += 0.2
        
        return min(boost, 2.0)  # Cap at 2x boost
    
    def _phonetic_similarity(self, text1: str, text2: str) -> float:
        """Calculate phonetic similarity between two texts"""
        # Simple phonetic similarity based on character patterns
        text1 = re.sub(r'[^a-z]', '', text1.lower())
        text2 = re.sub(r'[^a-z]', '', text2.lower())
        
        if not text1 or not text2:
            return 0.0
        
        # Calculate Levenshtein distance
        distance = self._levenshtein_distance(text1, text2)
        max_len = max(len(text1), len(text2))
        
        return 1 - (distance / max_len)
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def enhance_drug_recognition(self, transcript: str, medical_context: str = "") -> Dict:
        """Enhance drug recognition in transcript using Belgian pronunciation patterns"""
        try:
            enhanced_transcript = transcript
            drug_corrections = []
            
            # Split transcript into words for analysis
            words = re.findall(r'\b\w+\b', transcript.lower())
            
            # Look for potential drug mentions
            for i, word in enumerate(words):
                # Get context around the word
                context_start = max(0, i - 5)
                context_end = min(len(words), i + 6)
                local_context = ' '.join(words[context_start:context_end])
                
                # Find potential drug matches
                matches = self.find_drug_by_pronunciation(word, medical_context + " " + local_context)
                
                if matches and matches[0]['confidence'] > 0.7:
                    best_match = matches[0]
                    
                    # Replace in transcript
                    pattern = re.compile(re.escape(word), re.IGNORECASE)
                    enhanced_transcript = pattern.sub(best_match['generic_name'], enhanced_transcript, count=1)
                    
                    drug_corrections.append({
                        'original': word,
                        'corrected': best_match['generic_name'],
                        'confidence': best_match['confidence'],
                        'match_type': best_match['match_type'],
                        'context': local_context
                    })
            
            # Look for multi-word drug names
            enhanced_transcript, multi_word_corrections = self._find_multi_word_drugs(enhanced_transcript, medical_context)
            drug_corrections.extend(multi_word_corrections)
            
            return {
                'enhanced_transcript': enhanced_transcript,
                'drug_corrections': drug_corrections,
                'enhancement_applied': len(drug_corrections) > 0
            }
            
        except Exception as e:
            logger.error(f"Drug recognition enhancement error: {e}")
            return {
                'enhanced_transcript': transcript,
                'drug_corrections': [],
                'enhancement_applied': False,
                'error': str(e)
            }
    
    def _find_multi_word_drugs(self, transcript: str, context: str) -> Tuple[str, List[Dict]]:
        """Find multi-word drug names that might be split in speech"""
        corrections = []
        enhanced = transcript
        
        # Common multi-word patterns in Belgian medical speech
        multi_word_patterns = {
            'acetyl salicyl': 'acetylsalicylic acid',
            'hydrochloro thiazide': 'hydrochlorothiazide',
            'spirono lactone': 'spironolactone',
            'metro prolol': 'metoprolol',
            'biso prolol': 'bisoprolol',
            'carve dilol': 'carvedilol',
            'ator vastatin': 'atorvastatin',
            'simva statin': 'simvastatin',
            'rosu vastatin': 'rosuvastatin'
        }
        
        for pattern, correct_name in multi_word_patterns.items():
            if pattern in transcript.lower():
                # Calculate confidence based on context
                confidence = 0.8 * self._get_context_boost(correct_name, context)
                
                if confidence > 0.6:
                    enhanced = re.sub(pattern, correct_name, enhanced, flags=re.IGNORECASE)
                    corrections.append({
                        'original': pattern,
                        'corrected': correct_name,
                        'confidence': confidence,
                        'match_type': 'multi_word',
                        'context': context
                    })
        
        return enhanced, corrections
    
    def get_drug_context_suggestions(self, partial_drug: str, medical_context: str) -> List[Dict]:
        """Get drug suggestions based on partial input and medical context"""
        suggestions = []
        
        # Find matches
        matches = self.find_drug_by_pronunciation(partial_drug, medical_context)
        
        for match in matches:
            if match['confidence'] > 0.5:
                suggestions.append({
                    'drug_name': match['generic_name'],
                    'confidence': match['confidence'],
                    'reason': f"Matches '{match['matched_variant']}' with {match['confidence']:.1%} confidence",
                    'context_relevant': self._get_context_boost(match['generic_name'], medical_context) > 1.0
                })
        
        return suggestions
    
    def add_custom_pronunciation(self, generic_name: str, pronunciation_variants: List[str]):
        """Add custom pronunciation variants for a drug"""
        if generic_name not in self.belgian_patterns:
            self.belgian_patterns[generic_name] = []
        
        self.belgian_patterns[generic_name].extend(pronunciation_variants)
        
        # Update pronunciation database
        self.pronunciation_db[generic_name] = PronunciationVariant(
            original_name=generic_name,
            pronunciation_variants=self.belgian_patterns[generic_name],
            phonetic_pattern=self._create_phonetic_pattern(generic_name),
            language='mixed',
            confidence=0.8
        )
    
    def get_pronunciation_stats(self) -> Dict:
        """Get statistics about the pronunciation database"""
        return {
            'total_drugs': len(self.pronunciation_db),
            'total_variants': sum(len(data.pronunciation_variants) for data in self.pronunciation_db.values()),
            'languages_supported': ['Dutch', 'French', 'Mixed'],
            'pattern_types': ['exact', 'phonetic', 'multi_word', 'brand_name']
        }

def get_belgian_pronunciation_system(db_path: str) -> BelgianDrugPronunciation:
    """Get or create the Belgian pronunciation system"""
    return BelgianDrugPronunciation(db_path)

