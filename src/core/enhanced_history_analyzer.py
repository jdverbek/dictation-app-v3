"""
Enhanced History Collection System - Improved Version
CRITICAL: NEVER fabricate or make up any medical information
Only extract and structure explicitly mentioned information with better pattern recognition
"""

import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class SymptomDetail:
    """Structure for storing symptom details - only from explicit mentions"""
    symptom: str
    onset: Optional[str] = None
    duration: Optional[str] = None
    character: Optional[str] = None
    location: Optional[str] = None
    radiation: Optional[str] = None
    aggravating_factors: Optional[List[str]] = None
    relieving_factors: Optional[List[str]] = None
    timing: Optional[str] = None
    severity: Optional[str] = None
    associated_symptoms: Optional[List[str]] = None
    confidence_score: float = 0.0
    source_text: str = ""  # Original text where this was mentioned


@dataclass
class HistoryAnalysis:
    """Complete history analysis result"""
    reason_for_encounter: str
    chief_complaints: List[SymptomDetail]
    relevant_history: List[str]
    red_flags: List[str]
    information_gaps: List[str]
    confidence_scores: Dict[str, float]
    source_validation: Dict[str, str]  # Maps extracted info to source text


class EnhancedHistoryAnalyzer:
    """
    Enhanced analyzer for doctor-patient conversations
    Better pattern recognition while maintaining strict extraction rules
    """
    
    def __init__(self):
        self.medical_terms = self._load_medical_terms()
        self.symptom_patterns = self._create_enhanced_symptom_patterns()
        self.conversation_markers = self._load_conversation_markers()
        
    def _load_medical_terms(self) -> Dict[str, List[str]]:
        """Load comprehensive medical terminology patterns"""
        return {
            'pain_descriptors': [
                'pijn', 'zeer', 'kramp', 'steek', 'druk', 'brand', 'scheur',
                'klop', 'bonk', 'priem', 'mes', 'naald', 'drukkend', 'stekend',
                'brandend', 'knagend', 'zeurend', 'scherp', 'dof'
            ],
            'symptoms': [
                'pijn', 'kortademig', 'moe', 'duizelig', 'misselijk', 'braken',
                'koorts', 'rillingen', 'zweten', 'hartkloppingen', 'palpitaties',
                'benauwdheid', 'hoest', 'sputum', 'bloedspuwen', 'syncope',
                'flauwvallen', 'zwelling', 'oedeem', 'tintelingen', 'gevoelloosheid'
            ],
            'temporal_markers': [
                'sinds', 'vanaf', 'gedurende', 'tijdens', 'na', 'voor',
                'gisteren', 'vandaag', 'vorige week', 'maand geleden',
                'jaar geleden', 'plots', 'geleidelijk', 'acuut', 'chronisch',
                'opeens', 'plotseling', 'langzaam', 'steeds', 'altijd'
            ],
            'severity_markers': [
                'licht', 'mild', 'matig', 'ernstig', 'hevig', 'ondraaglijk',
                'weinig', 'veel', 'erg', 'verschrikkelijk', 'nauwelijks',
                'heel erg', 'niet zo erg', 'behoorlijk', 'flink'
            ],
            'location_markers': [
                'borst', 'hart', 'arm', 'nek', 'kaak', 'rug', 'buik',
                'been', 'hoofd', 'links', 'rechts', 'midden', 'boven',
                'onder', 'binnen', 'buiten', 'voor', 'achter'
            ],
            'triggers': [
                'inspanning', 'rust', 'stress', 'eten', 'drinken', 'liggen',
                'zitten', 'staan', 'lopen', 'rennen', 'trap', 'emotie',
                'koud', 'warm', 'weer', 'nacht', 'ochtend', 'avond'
            ]
        }
    
    def _load_conversation_markers(self) -> Dict[str, List[str]]:
        """Load markers to identify patient vs doctor speech"""
        return {
            'patient_markers': [
                'ik heb', 'ik voel', 'ik krijg', 'ik ben', 'ik word',
                'mij', 'mijn', 'bij mij', 'voor mij', 'ik denk',
                'ik merk', 'ik ervaar', 'ik kom', 'me', 'mezelf'
            ],
            'doctor_markers': [
                'u heeft', 'u voelt', 'u krijgt', 'uw', 'bij u',
                'kunt u', 'heeft u', 'voelt u', 'wanneer heeft u',
                'hoe lang', 'waar precies', 'kunt u beschrijven',
                'wat voor', 'hoe erg', 'op een schaal'
            ]
        }
    
    def _create_enhanced_symptom_patterns(self) -> List[str]:
        """Create comprehensive regex patterns for symptom detection"""
        return [
            # Direct symptom statements
            r'ik heb (.+?)(?:\.|,|en|$)',
            r'ik voel (.+?)(?:\.|,|en|$)', 
            r'ik krijg (.+?)(?:\.|,|en|$)',
            r'ik ben (.+?)(?:\.|,|en|$)',
            r'ik word (.+?)(?:\.|,|en|$)',
            
            # Pain descriptions
            r'(.+?) doet (?:pijn|zeer)',
            r'pijn (?:in|op|aan|bij) (.+?)(?:\.|,|en|$)',
            r'(.+?) pijn',
            r'het doet pijn (?:in|op|aan|bij) (.+?)(?:\.|,|en|$)',
            
            # Complaint patterns
            r'last van (.+?)(?:\.|,|en|$)',
            r'klachten (?:van|over) (.+?)(?:\.|,|en|$)',
            r'problemen met (.+?)(?:\.|,|en|$)',
            r'moeilijkheden met (.+?)(?:\.|,|en|$)',
            
            # Temporal patterns
            r'sinds (.+?) heb ik (.+?)(?:\.|,|en|$)',
            r'vanaf (.+?) (.+?)(?:\.|,|en|$)',
            r'(.+?) sinds (.+?)(?:\.|,|en|$)',
            
            # Severity patterns
            r'(.+?) is (?:heel|erg|zeer|behoorlijk|flink) (.+?)(?:\.|,|en|$)',
            r'(?:heel|erg|zeer|behoorlijk|flink) (.+?)(?:\.|,|en|$)',
            
            # Location patterns
            r'(?:links|rechts|midden) (.+?)(?:\.|,|en|$)',
            r'(.+?) (?:links|rechts|in het midden)(?:\.|,|en|$)'
        ]
    
    def analyze_conversation(self, transcript: str) -> HistoryAnalysis:
        """
        Enhanced analysis function with better extraction
        """
        if not transcript or not transcript.strip():
            return self._empty_analysis("No transcript provided")
        
        # Clean transcript
        cleaned_transcript = self._clean_transcript(transcript)
        
        # Extract symptoms with enhanced patterns
        symptoms = self._extract_symptoms_enhanced(cleaned_transcript)
        
        # Extract reason for encounter
        reason = self._extract_reason_enhanced(cleaned_transcript, symptoms)
        
        # Extract relevant history
        relevant_history = self._extract_history_enhanced(cleaned_transcript)
        
        # Identify red flags
        red_flags = self._identify_red_flags_enhanced(cleaned_transcript)
        
        # Identify information gaps
        gaps = self._identify_gaps_enhanced(cleaned_transcript, symptoms)
        
        # Calculate confidence scores
        confidence_scores = self._calculate_confidence_enhanced(symptoms, cleaned_transcript)
        
        # Create source validation
        source_validation = self._create_source_validation_enhanced(symptoms, cleaned_transcript)
        
        return HistoryAnalysis(
            reason_for_encounter=reason,
            chief_complaints=symptoms,
            relevant_history=relevant_history,
            red_flags=red_flags,
            information_gaps=gaps,
            confidence_scores=confidence_scores,
            source_validation=source_validation
        )
    
    def _clean_transcript(self, transcript: str) -> str:
        """Clean and normalize transcript"""
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', transcript.strip())
        
        # Normalize punctuation
        cleaned = re.sub(r'[.]{2,}', '.', cleaned)
        cleaned = re.sub(r'[,]{2,}', ',', cleaned)
        
        return cleaned
    
    def _extract_symptoms_enhanced(self, transcript: str) -> List[SymptomDetail]:
        """Enhanced symptom extraction with better pattern matching"""
        symptoms = []
        sentences = self._split_into_sentences(transcript)
        
        for sentence in sentences:
            # Only process patient statements
            if self._is_patient_statement_enhanced(sentence):
                # Try each pattern
                for pattern in self.symptom_patterns:
                    matches = re.finditer(pattern, sentence.lower(), re.IGNORECASE)
                    for match in matches:
                        symptom_text = self._extract_symptom_from_match(match, sentence)
                        if symptom_text and self._is_valid_symptom_enhanced(symptom_text):
                            symptom = SymptomDetail(
                                symptom=symptom_text,
                                source_text=sentence.strip(),
                                confidence_score=self._calculate_symptom_confidence_enhanced(symptom_text, sentence)
                            )
                            
                            # Extract additional details
                            symptom = self._extract_symptom_details_enhanced(symptom, sentence)
                            symptoms.append(symptom)
        
        return self._deduplicate_symptoms_enhanced(symptoms)
    
    def _is_patient_statement_enhanced(self, sentence: str) -> bool:
        """Enhanced detection of patient vs doctor statements"""
        sentence_lower = sentence.lower()
        
        # Check for explicit patient markers
        patient_score = sum(1 for marker in self.conversation_markers['patient_markers'] 
                          if marker in sentence_lower)
        
        # Check for doctor markers
        doctor_score = sum(1 for marker in self.conversation_markers['doctor_markers'] 
                         if marker in sentence_lower)
        
        # If sentence starts with "Patiënt:" or similar
        if re.match(r'^\s*patiënt\s*:', sentence_lower):
            return True
        
        # If sentence starts with "Dokter:" or similar  
        if re.match(r'^\s*(?:dokter|arts|dr\.)\s*:', sentence_lower):
            return False
        
        # Score-based decision
        return patient_score > doctor_score
    
    def _extract_symptom_from_match(self, match, sentence: str) -> Optional[str]:
        """Extract symptom text from regex match"""
        try:
            if match.lastindex and match.lastindex >= 1:
                symptom_text = match.group(1).strip()
                
                # Clean up the extracted text
                symptom_text = re.sub(r'^(?:dat|het|een|de)\s+', '', symptom_text)
                symptom_text = re.sub(r'\s+(?:dat|het|een|de)$', '', symptom_text)
                
                return symptom_text if len(symptom_text) > 2 else None
            return None
        except:
            return None
    
    def _is_valid_symptom_enhanced(self, text: str) -> bool:
        """Enhanced validation of extracted symptom text"""
        if not text or len(text.strip()) < 3:
            return False
        
        # Filter out non-medical terms
        invalid_terms = [
            'het', 'een', 'de', 'dat', 'dit', 'wat', 'hoe', 'waar',
            'wanneer', 'waarom', 'misschien', 'denk', 'weet', 'zeg',
            'wel', 'niet', 'ook', 'maar', 'en', 'of', 'want'
        ]
        
        text_lower = text.lower().strip()
        
        # Reject if it's just invalid terms
        if text_lower in invalid_terms:
            return False
        
        # Must contain at least one medical-related term
        medical_indicators = (
            self.medical_terms['pain_descriptors'] + 
            self.medical_terms['symptoms'] +
            ['klacht', 'probleem', 'last', 'moeilijkheid']
        )
        
        has_medical_term = any(term in text_lower for term in medical_indicators)
        
        # Or be a body part/location
        has_location = any(loc in text_lower for loc in self.medical_terms['location_markers'])
        
        return has_medical_term or has_location
    
    def _extract_symptom_details_enhanced(self, symptom: SymptomDetail, sentence: str) -> SymptomDetail:
        """Enhanced extraction of symptom details from sentence"""
        sentence_lower = sentence.lower()
        
        # Extract onset/timing
        for temporal in self.medical_terms['temporal_markers']:
            if temporal in sentence_lower:
                symptom.onset = temporal
                break
        
        # Extract character/quality
        for descriptor in self.medical_terms['pain_descriptors']:
            if descriptor in sentence_lower:
                symptom.character = descriptor
                break
        
        # Extract location
        for location in self.medical_terms['location_markers']:
            if location in sentence_lower:
                symptom.location = location
                break
        
        # Extract severity
        for severity in self.medical_terms['severity_markers']:
            if severity in sentence_lower:
                symptom.severity = severity
                break
        
        # Extract triggers/aggravating factors
        triggers = []
        for trigger in self.medical_terms['triggers']:
            if trigger in sentence_lower:
                triggers.append(trigger)
        if triggers:
            symptom.aggravating_factors = triggers
        
        return symptom
    
    def _extract_reason_enhanced(self, transcript: str, symptoms: List[SymptomDetail]) -> str:
        """Enhanced extraction of reason for encounter"""
        # Look for explicit reason statements
        reason_patterns = [
            r'ik kom (?:hier )?voor (.+?)(?:\.|,|$)',
            r'ik ben hier voor (.+?)(?:\.|,|$)',
            r'het probleem is (.+?)(?:\.|,|$)',
            r'mijn klacht is (.+?)(?:\.|,|$)',
            r'ik heb last van (.+?)(?:\.|,|$)',
            r'de reden (?:dat|waarom) ik kom is (.+?)(?:\.|,|$)'
        ]
        
        for pattern in reason_patterns:
            match = re.search(pattern, transcript.lower())
            if match:
                reason = match.group(1).strip()
                # Keep it concise (max 4 words as requested)
                words = reason.split()[:4]
                return ' '.join(words)
        
        # If no explicit reason, use first/main symptom
        if symptoms:
            main_symptom = symptoms[0].symptom
            words = main_symptom.split()[:3]  # Max 3 words
            return ' '.join(words)
        
        return "Niet expliciet vermeld"
    
    def _extract_history_enhanced(self, transcript: str) -> List[str]:
        """Enhanced extraction of relevant medical history"""
        history_items = []
        
        # Enhanced history patterns
        history_patterns = [
            r'ik heb (?:eerder|vroeger|in het verleden) (.+?)(?:\.|,|$)',
            r'ik had (?:vroeger|eerder) (.+?)(?:\.|,|$)',
            r'vorig jaar (.+?)(?:\.|,|$)',
            r'(?:vorige|afgelopen) (?:maand|week) (.+?)(?:\.|,|$)',
            r'familie heeft (.+?)(?:\.|,|$)',
            r'mijn (?:vader|moeder|broer|zus|opa|oma) (?:heeft|had) (.+?)(?:\.|,|$)',
            r'in de familie (.+?)(?:\.|,|$)',
            r'medicatie (?:voor|tegen) (.+?)(?:\.|,|$)',
            r'ik gebruik (.+?)(?:\.|,|$)',
            r'operatie (?:aan|voor) (.+?)(?:\.|,|$)',
            r'ziekenhuis (?:voor|wegens) (.+?)(?:\.|,|$)'
        ]
        
        for pattern in history_patterns:
            matches = re.finditer(pattern, transcript.lower())
            for match in matches:
                history_item = match.group(1).strip()
                if len(history_item) > 2 and history_item not in history_items:
                    history_items.append(history_item)
        
        return history_items[:10]  # Limit to 10 most relevant items
    
    def _identify_red_flags_enhanced(self, transcript: str) -> List[str]:
        """Enhanced identification of red flag symptoms"""
        red_flags = []
        
        red_flag_patterns = [
            r'(?:plots|plotseling|opeens) (.+?)(?:\.|,|$)',
            r'(?:heel erg|ondraaglijk|verschrikkelijk) (.+?)(?:\.|,|$)',
            r'(?:flauwgevallen|bewusteloos|syncope)',
            r'(?:bloedspuwen|hemoptoe)',
            r'(?:hartkloppingen|palpitaties) (?:in rust|\'s nachts)',
            r'(?:kortademig|benauwd) (?:in rust|bij weinig inspanning)',
            r'(?:zwelling|oedeem) (?:benen|enkels)',
            r'(?:pijn|druk) (?:uitstralend naar|in) (?:arm|nek|kaak)'
        ]
        
        for pattern in red_flag_patterns:
            matches = re.finditer(pattern, transcript.lower())
            for match in matches:
                red_flag = match.group(0).strip()
                if red_flag not in red_flags:
                    red_flags.append(red_flag)
        
        return red_flags
    
    def _identify_gaps_enhanced(self, transcript: str, symptoms: List[SymptomDetail]) -> List[str]:
        """Enhanced identification of information gaps"""
        gaps = []
        
        for symptom in symptoms:
            # Check for missing details
            if not symptom.onset:
                gaps.append(f"Onset van '{symptom.symptom}' niet vermeld")
            if not symptom.character:
                gaps.append(f"Karakter van '{symptom.symptom}' niet beschreven")
            if not symptom.severity:
                gaps.append(f"Ernst van '{symptom.symptom}' niet vermeld")
            if not symptom.aggravating_factors:
                gaps.append(f"Uitlokkende factoren van '{symptom.symptom}' niet vermeld")
        
        return gaps[:5]  # Limit to 5 most important gaps
    
    def _calculate_confidence_enhanced(self, symptoms: List[SymptomDetail], transcript: str) -> Dict[str, float]:
        """Enhanced confidence calculation"""
        confidence_scores = {}
        
        for symptom in symptoms:
            score = 0.5  # Base score
            
            # Increase confidence based on detail level
            if symptom.onset: score += 0.1
            if symptom.character: score += 0.1
            if symptom.location: score += 0.1
            if symptom.severity: score += 0.1
            if symptom.aggravating_factors: score += 0.1
            
            # Increase confidence if mentioned multiple times
            mentions = transcript.lower().count(symptom.symptom.lower())
            score += min(mentions * 0.05, 0.15)
            
            confidence_scores[symptom.symptom] = min(score, 1.0)
        
        return confidence_scores
    
    def _create_source_validation_enhanced(self, symptoms: List[SymptomDetail], transcript: str) -> Dict[str, str]:
        """Enhanced source validation mapping"""
        validation = {}
        
        for symptom in symptoms:
            validation[symptom.symptom] = symptom.source_text
        
        return validation
    
    def _deduplicate_symptoms_enhanced(self, symptoms: List[SymptomDetail]) -> List[SymptomDetail]:
        """Enhanced deduplication of symptoms"""
        unique_symptoms = []
        seen_symptoms = set()
        
        for symptom in symptoms:
            # Create a normalized key for comparison
            key = symptom.symptom.lower().strip()
            
            if key not in seen_symptoms:
                seen_symptoms.add(key)
                unique_symptoms.append(symptom)
            else:
                # Merge details if symptom already exists
                for existing in unique_symptoms:
                    if existing.symptom.lower().strip() == key:
                        # Merge missing details
                        if not existing.onset and symptom.onset:
                            existing.onset = symptom.onset
                        if not existing.character and symptom.character:
                            existing.character = symptom.character
                        # etc.
                        break
        
        return unique_symptoms
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _calculate_symptom_confidence_enhanced(self, symptom: str, sentence: str) -> float:
        """Calculate confidence score for a symptom"""
        score = 0.5  # Base score
        
        # Increase if contains medical terms
        if any(term in symptom.lower() for term in self.medical_terms['symptoms']):
            score += 0.2
        
        # Increase if contains descriptive terms
        if any(desc in sentence.lower() for desc in self.medical_terms['pain_descriptors']):
            score += 0.1
        
        # Increase if contains temporal information
        if any(temp in sentence.lower() for temp in self.medical_terms['temporal_markers']):
            score += 0.1
        
        return min(score, 1.0)
    
    def _empty_analysis(self, reason: str) -> HistoryAnalysis:
        """Return empty analysis with reason"""
        return HistoryAnalysis(
            reason_for_encounter=reason,
            chief_complaints=[],
            relevant_history=[],
            red_flags=[],
            information_gaps=[],
            confidence_scores={},
            source_validation={}
        )
    
    def format_structured_output(self, analysis: HistoryAnalysis) -> str:
        """Format analysis into structured medical report"""
        output = []
        
        # Header
        output.append("🧠 INTELLIGENTE ANAMNESE ANALYSE")
        output.append("=" * 50)
        output.append("")
        
        # Reason for encounter
        output.append(f"📋 Reden van komst: {analysis.reason_for_encounter}")
        output.append("")
        
        # Chief complaints
        if analysis.chief_complaints:
            output.append("🔍 Hoofdklachten:")
            for i, complaint in enumerate(analysis.chief_complaints, 1):
                output.append(f"{i}. {complaint.symptom}")
                
                details = []
                if complaint.onset:
                    details.append(f"Onset: {complaint.onset}")
                if complaint.character:
                    details.append(f"Karakter: {complaint.character}")
                if complaint.location:
                    details.append(f"Lokalisatie: {complaint.location}")
                if complaint.severity:
                    details.append(f"Ernst: {complaint.severity}")
                if complaint.aggravating_factors:
                    details.append(f"Uitlokkende factoren: {', '.join(complaint.aggravating_factors)}")
                
                for detail in details:
                    output.append(f"   - {detail}")
                
                output.append(f"   - Bron: \"{complaint.source_text[:100]}...\"")
                output.append("")
        else:
            output.append("🔍 Hoofdklachten: Geen specifieke klachten geëxtraheerd")
            output.append("")
        
        # Relevant history
        if analysis.relevant_history:
            output.append("📚 Relevante voorgeschiedenis:")
            for item in analysis.relevant_history:
                output.append(f"- {item}")
            output.append("")
        
        # Red flags
        if analysis.red_flags:
            output.append("⚠️ Aandachtspunten (Red Flags):")
            for flag in analysis.red_flags:
                output.append(f"- {flag}")
            output.append("")
        
        # Information gaps
        if analysis.information_gaps:
            output.append("❓ Ontbrekende informatie:")
            for gap in analysis.information_gaps:
                output.append(f"- {gap}")
            output.append("")
        
        # Confidence scores
        if analysis.confidence_scores:
            output.append("📊 Betrouwbaarheidsscores:")
            for item, score in analysis.confidence_scores.items():
                confidence_level = "Hoog" if score > 0.8 else "Matig" if score > 0.6 else "Laag"
                output.append(f"- {item}: {score:.2f} ({confidence_level})")
            output.append("")
        
        # Footer
        output.append("=" * 50)
        output.append("✅ Analyse voltooid - Alleen expliciet vermelde informatie geëxtraheerd")
        
        return "\n".join(output)


def test_enhanced_history_analyzer():
    """Test function for the enhanced history analyzer"""
    analyzer = EnhancedHistoryAnalyzer()
    
    # Test conversation
    test_transcript = """
    Dokter: Goedemorgen, waarmee kan ik u helpen?
    Patiënt: Ik kom hier voor pijn op de borst. Ik heb sinds gisteren een drukkende pijn.
    Dokter: Kunt u de pijn beschrijven?
    Patiënt: Het is een drukkende pijn, vooral links op de borst. Ik krijg het vooral bij inspanning.
    Dokter: Heeft u dit eerder gehad?
    Patiënt: Nee, dit is de eerste keer. Mijn vader heeft wel een hartaanval gehad toen hij 55 was.
    Dokter: Gebruikt u medicatie?
    Patiënt: Ik gebruik bloeddrukmedicatie, lisinopril 10 mg.
    """
    
    analysis = analyzer.analyze_conversation(test_transcript)
    formatted_output = analyzer.format_structured_output(analysis)
    
    print("=== ENHANCED HISTORY ANALYSIS TEST ===")
    print(formatted_output)
    print("\n=== RAW ANALYSIS DATA ===")
    print(f"Reason: {analysis.reason_for_encounter}")
    print(f"Complaints: {len(analysis.chief_complaints)}")
    print(f"History items: {len(analysis.relevant_history)}")
    print(f"Red flags: {len(analysis.red_flags)}")


if __name__ == "__main__":
    test_enhanced_history_analyzer()

