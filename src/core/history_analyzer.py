"""
Intelligent History Collection System
CRITICAL: NEVER fabricate or make up any medical information
Only extract and structure explicitly mentioned information
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


class HistoryAnalyzer:
    """
    Analyzes doctor-patient conversations to extract medical history
    STRICT RULE: Only extract explicitly mentioned information
    """
    
    def __init__(self):
        self.medical_terms = self._load_medical_terms()
        self.symptom_patterns = self._create_symptom_patterns()
        
    def _load_medical_terms(self) -> Dict[str, List[str]]:
        """Load medical terminology patterns for recognition"""
        return {
            'pain_descriptors': [
                'pijn', 'zeer', 'kramp', 'steek', 'druk', 'brand', 'scheur',
                'klop', 'bonk', 'priem', 'mes', 'naald'
            ],
            'temporal_markers': [
                'sinds', 'vanaf', 'gedurende', 'tijdens', 'na', 'voor',
                'gisteren', 'vandaag', 'vorige week', 'maand geleden',
                'jaar geleden', 'plots', 'geleidelijk', 'acuut', 'chronisch'
            ],
            'severity_markers': [
                'licht', 'mild', 'matig', 'ernstig', 'hevig', 'ondraaglijk',
                'weinig', 'veel', 'erg', 'verschrikkelijk', 'nauwelijks'
            ],
            'location_markers': [
                'borst', 'hart', 'arm', 'nek', 'kaak', 'rug', 'buik',
                'been', 'hoofd', 'links', 'rechts', 'midden'
            ]
        }
    
    def _create_symptom_patterns(self) -> List[str]:
        """Create regex patterns for symptom detection"""
        return [
            r'ik heb (.+?)(?:\.|,|$)',
            r'ik voel (.+?)(?:\.|,|$)',
            r'ik krijg (.+?)(?:\.|,|$)',
            r'er is (.+?)(?:\.|,|$)',
            r'(.+?) doet pijn',
            r'pijn (?:in|op|aan) (.+?)(?:\.|,|$)',
            r'last van (.+?)(?:\.|,|$)',
            r'klachten van (.+?)(?:\.|,|$)'
        ]
    
    def analyze_conversation(self, transcript: str) -> HistoryAnalysis:
        """
        Main analysis function - extracts history from conversation
        CRITICAL: Only uses explicitly mentioned information
        """
        # Step 1: Clean and validate input
        if not transcript or not transcript.strip():
            return self._empty_analysis("No transcript provided")
        
        # Step 2: Extract symptoms and complaints with source validation
        symptoms = self._extract_symptoms_with_validation(transcript)
        
        # Step 3: Extract reason for encounter (only from explicit mentions)
        reason = self._extract_reason_for_encounter(transcript)
        
        # Step 4: Extract relevant history (only mentioned items)
        relevant_history = self._extract_relevant_history(transcript)
        
        # Step 5: Identify red flags (only from explicit concerning mentions)
        red_flags = self._identify_red_flags(transcript)
        
        # Step 6: Identify information gaps (what was asked but not answered)
        gaps = self._identify_information_gaps(transcript, symptoms)
        
        # Step 7: Calculate confidence scores based on source validation
        confidence_scores = self._calculate_confidence_scores(symptoms, transcript)
        
        # Step 8: Create source validation mapping
        source_validation = self._create_source_validation(symptoms, transcript)
        
        return HistoryAnalysis(
            reason_for_encounter=reason,
            chief_complaints=symptoms,
            relevant_history=relevant_history,
            red_flags=red_flags,
            information_gaps=gaps,
            confidence_scores=confidence_scores,
            source_validation=source_validation
        )
    
    def _extract_symptoms_with_validation(self, transcript: str) -> List[SymptomDetail]:
        """Extract symptoms with strict source validation"""
        symptoms = []
        sentences = self._split_into_sentences(transcript)
        
        for sentence in sentences:
            # Only extract if explicitly mentioned by patient
            if self._is_patient_statement(sentence):
                symptom_matches = self._find_symptom_mentions(sentence)
                
                for match in symptom_matches:
                    symptom = SymptomDetail(
                        symptom=match['symptom'],
                        source_text=sentence.strip(),
                        confidence_score=match['confidence']
                    )
                    
                    # Extract additional details only if explicitly mentioned
                    symptom = self._extract_symptom_details(symptom, sentence)
                    symptoms.append(symptom)
        
        return self._deduplicate_symptoms(symptoms)
    
    def _is_patient_statement(self, sentence: str) -> bool:
        """Determine if sentence is from patient (not doctor)"""
        patient_indicators = [
            'ik heb', 'ik voel', 'ik krijg', 'mij', 'mijn',
            'ik ben', 'ik word', 'bij mij', 'voor mij'
        ]
        doctor_indicators = [
            'u heeft', 'u voelt', 'u krijgt', 'uw',
            'kunt u', 'heeft u', 'voelt u', 'wanneer heeft u'
        ]
        
        sentence_lower = sentence.lower()
        
        # If contains doctor indicators, likely doctor speaking
        if any(indicator in sentence_lower for indicator in doctor_indicators):
            return False
        
        # If contains patient indicators, likely patient speaking
        if any(indicator in sentence_lower for indicator in patient_indicators):
            return True
        
        # Default to uncertain - require explicit patient indicators
        return False
    
    def _find_symptom_mentions(self, sentence: str) -> List[Dict]:
        """Find symptom mentions in sentence with confidence scoring"""
        matches = []
        
        for pattern in self.symptom_patterns:
            regex_matches = re.finditer(pattern, sentence.lower())
            for match in regex_matches:
                symptom_text = match.group(1).strip()
                
                # Validate it's actually a symptom/complaint
                if self._is_valid_symptom(symptom_text):
                    matches.append({
                        'symptom': symptom_text,
                        'confidence': self._calculate_symptom_confidence(symptom_text, sentence),
                        'position': match.span()
                    })
        
        return matches
    
    def _is_valid_symptom(self, text: str) -> bool:
        """Validate if extracted text represents a valid symptom"""
        # Filter out non-medical terms
        invalid_terms = [
            'het', 'een', 'de', 'dat', 'dit', 'wat', 'hoe', 'waar',
            'wanneer', 'waarom', 'misschien', 'denk', 'weet', 'zeg'
        ]
        
        if text.lower() in invalid_terms:
            return False
        
        # Must contain medical or symptom-related terms
        medical_indicators = [
            'pijn', 'zeer', 'last', 'klacht', 'probleem', 'moeilijk',
            'zwelling', 'koorts', 'misselijk', 'duizelig', 'moe',
            'kortademig', 'hoest', 'jeuk', 'uitslag', 'hoofdpijn'
        ]
        
        return any(indicator in text.lower() for indicator in medical_indicators)
    
    def _extract_symptom_details(self, symptom: SymptomDetail, sentence: str) -> SymptomDetail:
        """Extract additional symptom details only if explicitly mentioned"""
        sentence_lower = sentence.lower()
        
        # Extract onset (only if explicitly mentioned)
        onset_patterns = [
            r'sinds (.+?)(?:\.|,|en|$)',
            r'vanaf (.+?)(?:\.|,|en|$)',
            r'(.+?) geleden',
            r'na (.+?)(?:\.|,|en|$)'
        ]
        
        for pattern in onset_patterns:
            match = re.search(pattern, sentence_lower)
            if match:
                symptom.onset = match.group(1).strip()
                break
        
        # Extract severity (only if explicitly mentioned)
        for severity in self.medical_terms['severity_markers']:
            if severity in sentence_lower:
                symptom.severity = severity
                break
        
        # Extract location (only if explicitly mentioned)
        for location in self.medical_terms['location_markers']:
            if location in sentence_lower:
                symptom.location = location
                break
        
        # Extract character/quality (only if explicitly mentioned)
        for descriptor in self.medical_terms['pain_descriptors']:
            if descriptor in sentence_lower:
                symptom.character = descriptor
                break
        
        return symptom
    
    def _extract_reason_for_encounter(self, transcript: str) -> str:
        """Extract reason for encounter - only from explicit mentions"""
        # Look for explicit statements about why patient came
        reason_patterns = [
            r'ik kom (?:hier )?voor (.+?)(?:\.|,|$)',
            r'ik ben hier voor (.+?)(?:\.|,|$)',
            r'het probleem is (.+?)(?:\.|,|$)',
            r'mijn klacht is (.+?)(?:\.|,|$)',
            r'ik heb last van (.+?)(?:\.|,|$)'
        ]
        
        for pattern in reason_patterns:
            match = re.search(pattern, transcript.lower())
            if match:
                reason = match.group(1).strip()
                # Keep it concise (few words as requested)
                words = reason.split()[:4]  # Max 4 words
                return ' '.join(words)
        
        # If no explicit reason found, try to extract from first complaint
        sentences = self._split_into_sentences(transcript)
        for sentence in sentences[:5]:  # Check first 5 sentences
            if self._is_patient_statement(sentence):
                symptoms = self._find_symptom_mentions(sentence)
                if symptoms:
                    # Use first mentioned symptom as reason
                    words = symptoms[0]['symptom'].split()[:3]  # Max 3 words
                    return ' '.join(words)
        
        return "Niet expliciet vermeld"
    
    def _extract_relevant_history(self, transcript: str) -> List[str]:
        """Extract relevant medical history - only explicitly mentioned items"""
        history_items = []
        
        # Look for explicit mentions of past medical events
        history_patterns = [
            r'ik heb gehad (.+?)(?:\.|,|$)',
            r'ik had (.+?)(?:\.|,|$)',
            r'vorig jaar (.+?)(?:\.|,|$)',
            r'eerder (.+?)(?:\.|,|$)',
            r'in het verleden (.+?)(?:\.|,|$)',
            r'familie heeft (.+?)(?:\.|,|$)'
        ]
        
        for pattern in history_patterns:
            matches = re.finditer(pattern, transcript.lower())
            for match in matches:
                history_item = match.group(1).strip()
                if self._is_relevant_medical_history(history_item):
                    history_items.append(history_item)
        
        return list(set(history_items))  # Remove duplicates
    
    def _is_relevant_medical_history(self, text: str) -> bool:
        """Check if mentioned history is medically relevant"""
        relevant_terms = [
            'hartaanval', 'infarct', 'operatie', 'ziekenhuis', 'medicijn',
            'diabetes', 'hypertensie', 'kanker', 'allergie', 'astma',
            'depressie', 'angst', 'epilepsie', 'migraine', 'artritis'
        ]
        
        return any(term in text.lower() for term in relevant_terms)
    
    def _identify_red_flags(self, transcript: str) -> List[str]:
        """Identify red flags - only from explicit concerning mentions"""
        red_flags = []
        
        # Define red flag patterns (only if explicitly mentioned)
        red_flag_terms = [
            'plotse', 'acute', 'ernstige', 'ondraaglijke', 'verschrikkelijke',
            'bewusteloos', 'flauwgevallen', 'hartkloppingen', 'kortademig',
            'bloeding', 'zwart', 'bloed', 'koorts', 'rillingen'
        ]
        
        sentences = self._split_into_sentences(transcript)
        for sentence in sentences:
            sentence_lower = sentence.lower()
            for term in red_flag_terms:
                if term in sentence_lower and self._is_patient_statement(sentence):
                    red_flags.append(f"Patiënt meldt: {sentence.strip()}")
                    break
        
        return list(set(red_flags))
    
    def _identify_information_gaps(self, transcript: str, symptoms: List[SymptomDetail]) -> List[str]:
        """Identify what information is missing but should be asked"""
        gaps = []
        
        for symptom in symptoms:
            # Check what details are missing for each symptom
            if not symptom.onset:
                gaps.append(f"Onset van '{symptom.symptom}' niet vermeld")
            if not symptom.severity:
                gaps.append(f"Ernst van '{symptom.symptom}' niet vermeld")
            if not symptom.character:
                gaps.append(f"Karakter van '{symptom.symptom}' niet beschreven")
        
        return gaps
    
    def _calculate_confidence_scores(self, symptoms: List[SymptomDetail], transcript: str) -> Dict[str, float]:
        """Calculate confidence scores for extracted information"""
        scores = {}
        
        for symptom in symptoms:
            # Base confidence on how explicitly the symptom was mentioned
            base_score = symptom.confidence_score
            
            # Increase confidence if multiple details are provided
            detail_count = sum([
                1 for attr in [symptom.onset, symptom.severity, symptom.character, 
                              symptom.location] if attr is not None
            ])
            
            final_score = min(base_score + (detail_count * 0.1), 1.0)
            scores[symptom.symptom] = final_score
        
        return scores
    
    def _create_source_validation(self, symptoms: List[SymptomDetail], transcript: str) -> Dict[str, str]:
        """Create mapping of extracted info to source text for validation"""
        validation = {}
        
        for symptom in symptoms:
            validation[symptom.symptom] = symptom.source_text
            
            if symptom.onset:
                validation[f"{symptom.symptom}_onset"] = symptom.source_text
            if symptom.severity:
                validation[f"{symptom.symptom}_severity"] = symptom.source_text
        
        return validation
    
    def _calculate_symptom_confidence(self, symptom_text: str, sentence: str) -> float:
        """Calculate confidence score for symptom extraction"""
        base_confidence = 0.7
        
        # Increase confidence for clear symptom statements
        if any(pattern in sentence.lower() for pattern in ['ik heb', 'ik voel', 'ik krijg']):
            base_confidence += 0.2
        
        # Increase confidence for medical terms
        if any(term in symptom_text.lower() for term in self.medical_terms['pain_descriptors']):
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _deduplicate_symptoms(self, symptoms: List[SymptomDetail]) -> List[SymptomDetail]:
        """Remove duplicate symptoms"""
        seen = set()
        unique_symptoms = []
        
        for symptom in symptoms:
            if symptom.symptom not in seen:
                seen.add(symptom.symptom)
                unique_symptoms.append(symptom)
        
        return unique_symptoms
    
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
        """Format analysis into structured medical history report"""
        output = []
        
        output.append(f"Reden van komst: {analysis.reason_for_encounter}")
        output.append("")
        
        if analysis.chief_complaints:
            output.append("Hoofdklachten:")
            for i, complaint in enumerate(analysis.chief_complaints, 1):
                output.append(f"{i}. {complaint.symptom}")
                if complaint.onset:
                    output.append(f"   - Onset: {complaint.onset}")
                if complaint.severity:
                    output.append(f"   - Ernst: {complaint.severity}")
                if complaint.character:
                    output.append(f"   - Karakter: {complaint.character}")
                if complaint.location:
                    output.append(f"   - Lokalisatie: {complaint.location}")
                output.append(f"   - Bron: \"{complaint.source_text}\"")
                output.append("")
        
        if analysis.relevant_history:
            output.append("Relevante voorgeschiedenis:")
            for item in analysis.relevant_history:
                output.append(f"- {item}")
            output.append("")
        
        if analysis.red_flags:
            output.append("⚠️ Aandachtspunten:")
            for flag in analysis.red_flags:
                output.append(f"- {flag}")
            output.append("")
        
        if analysis.information_gaps:
            output.append("Ontbrekende informatie:")
            for gap in analysis.information_gaps:
                output.append(f"- {gap}")
            output.append("")
        
        # Add confidence scores
        if analysis.confidence_scores:
            output.append("Betrouwbaarheidsscores:")
            for item, score in analysis.confidence_scores.items():
                output.append(f"- {item}: {score:.2f}")
        
        return "\n".join(output)


def test_history_analyzer():
    """Test function for the history analyzer"""
    analyzer = HistoryAnalyzer()
    
    # Test conversation
    test_transcript = """
    Dokter: Goedemorgen, waarmee kan ik u helpen?
    Patiënt: Ik heb sinds gisteren pijn op de borst. Het voelt als een druk.
    Dokter: Kunt u de pijn beschrijven?
    Patiënt: Het is een drukkende pijn, vooral links. Ik krijg het vooral bij inspanning.
    Dokter: Heeft u dit eerder gehad?
    Patiënt: Nee, dit is de eerste keer. Mijn vader heeft wel een hartaanval gehad.
    """
    
    analysis = analyzer.analyze_conversation(test_transcript)
    formatted_output = analyzer.format_structured_output(analysis)
    
    print("=== HISTORY ANALYSIS TEST ===")
    print(formatted_output)
    print("\n=== RAW ANALYSIS DATA ===")
    print(f"Reason: {analysis.reason_for_encounter}")
    print(f"Complaints: {len(analysis.chief_complaints)}")
    print(f"History items: {len(analysis.relevant_history)}")
    print(f"Red flags: {len(analysis.red_flags)}")


if __name__ == "__main__":
    test_history_analyzer()

