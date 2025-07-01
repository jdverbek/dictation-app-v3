"""
Enhanced Medical Processor
Integrates enhanced templates and reduces [niet vermeld] entries
Provides better medical language and structure
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from .enhanced_clinical_templates import EnhancedClinicalTemplates
except ImportError:
    from enhanced_clinical_templates import EnhancedClinicalTemplates


class EnhancedMedicalProcessor:
    """Enhanced processor for medical transcriptions with better templates"""
    
    def __init__(self):
        self.templates = EnhancedClinicalTemplates()
        self.extraction_patterns = self._load_extraction_patterns()
        
    def _load_extraction_patterns(self) -> Dict[str, Dict]:
        """Load patterns for extracting medical information"""
        return {
            'TTE': {
                'lv_edd': [
                    r'(?:EDD|end.?diastolische diameter).*?(\d+)\s*mm',
                    r'linker ventrikel.*?(\d+)\s*mm',
                    r'LV.*?(\d+)\s*mm'
                ],
                'lvef': [
                    r'(?:LVEF|ejectiefractie).*?(\d+)\s*%',
                    r'functie.*?(\d+)\s*%',
                    r'(\d+)\s*procent'
                ],
                'ivs': [
                    r'(?:IVS|interventriculair septum).*?(\d+)\s*mm',
                    r'septum.*?(\d+)\s*mm'
                ],
                'pw': [
                    r'(?:PW|posterior wall|achterwand).*?(\d+)\s*mm',
                    r'wand.*?(\d+)\s*mm'
                ],
                'mitral_valve': [
                    r'mitralis(?:klep)?.*?(normaal|insufficiëntie|stenose|prolaps)',
                    r'mitraal.*?(normaal|insufficiëntie|stenose|prolaps)',
                    r'MV.*?(normaal|insufficiëntie|stenose|prolaps)'
                ],
                'aortic_valve': [
                    r'aorta(?:klep)?.*?(normaal|insufficiëntie|stenose|sclerose)',
                    r'AV.*?(normaal|insufficiëntie|stenose|sclerose)'
                ],
                'lv_function': [
                    r'(?:LV|linker ventrikel).*?functie.*?(goed|normaal|verminderd|slecht)',
                    r'systolische functie.*?(goed|normaal|verminderd|slecht)',
                    r'contractiliteit.*?(goed|normaal|verminderd|slecht)'
                ]
            },
            'ECG': {
                'rhythm': [
                    r'ritme.*?(sinusaal|sinusritme|VKF|voorkamerflutter|atriale tachycardie)',
                    r'(sinusaal|sinusritme|VKF|voorkamerflutter|atriale tachycardie)',
                    r'rhythm.*?(sinus|atrial fibrillation|atrial flutter)'
                ],
                'rate': [
                    r'(?:hartslag|frequentie|rate).*?(\d+)(?:/min|bpm|\s*per minuut)',
                    r'(\d+)\s*(?:slagen|/min|bpm|per minuut)',
                    r'(\d+)\s*(?=\s*(?:slagen|per minuut|/min))'
                ],
                'pr_interval': [
                    r'PR(?:\s*interval)?.*?(\d+)\s*ms',
                    r'PQ(?:\s*tijd)?.*?(\d+)\s*ms'
                ],
                'qtc': [
                    r'QTc.*?(\d+)\s*ms',
                    r'gecorrigeerde QT.*?(\d+)\s*ms'
                ],
                'qrs_duration': [
                    r'QRS(?:\s*duur)?.*?(\d+)\s*ms',
                    r'QRS.*?(\d+)\s*ms'
                ]
            },
            'EXERCISE_TEST': {
                'max_workload': [
                    r'(?:maximale belasting|max.*?belasting).*?(\d+)\s*(?:watt|W)',
                    r'(\d+)\s*(?:watt|W).*?(?:maximaal|bereikt)',
                    r'belasting.*?(\d+)\s*(?:watt|W)'
                ],
                'max_hr': [
                    r'(?:maximale|max).*?(?:hartslag|HR).*?(\d+)',
                    r'hartslag.*?(\d+).*?(?:maximaal|max)',
                    r'(\d+)\s*(?:/min|bpm).*?(?:maximaal|max)'
                ],
                'max_bp': [
                    r'(?:maximale|max).*?(?:bloeddruk|RR).*?(\d+/\d+)',
                    r'bloeddruk.*?(\d+/\d+).*?(?:maximaal|max)',
                    r'RR.*?(\d+/\d+)'
                ],
                'symptoms': [
                    r'klachten.*?(geen|wel|pijn|kortademig|moe|duizelig)',
                    r'symptomen.*?(geen|wel|pijn|kortademig|moe|duizelig)',
                    r'(geen klachten|pijn|kortademigheid|vermoeidheid)'
                ]
            },
            'CONSULT': {
                'reason_visit': [
                    r'(?:reden|aanmelding|verwijzing).*?(?:voor|wegens)\s*(.+?)(?:\.|$)',
                    r'komt voor\s*(.+?)(?:\.|$)',
                    r'verwezen wegens\s*(.+?)(?:\.|$)'
                ],
                'current_complaints': [
                    r'(?:klachten|symptomen|problemen).*?(.+?)(?:\.|voorgeschiedenis|medicatie|onderzoek)',
                    r'patiënt meldt\s*(.+?)(?:\.|voorgeschiedenis|medicatie|onderzoek)',
                    r'anamnese.*?(.+?)(?:\.|voorgeschiedenis|medicatie|onderzoek)'
                ],
                'medication': [
                    r'medicatie.*?(.+?)(?:\.|onderzoek|beoordeling|plan)',
                    r'gebruikt.*?(.+?)(?:\.|onderzoek|beoordeling|plan)',
                    r'therapie.*?(.+?)(?:\.|onderzoek|beoordeling|plan)'
                ]
            }
        }
    
    def process_transcription(self, text: str, report_type: str, date: str = None) -> str:
        """Process transcription using enhanced templates"""
        if not date:
            date = datetime.now().strftime('%d-%m-%Y')
        
        # Extract findings from text
        findings = self._extract_findings(text, report_type)
        
        # Validate and enhance findings
        findings = self.templates.validate_findings(report_type, findings)
        
        # Format using enhanced template
        formatted_report = self.templates.format_template(report_type, findings, date)
        
        return formatted_report
    
    def _extract_findings(self, text: str, report_type: str) -> Dict[str, Any]:
        """Extract medical findings from transcription text"""
        findings = {}
        
        if report_type not in self.extraction_patterns:
            return findings
        
        patterns = self.extraction_patterns[report_type]
        text_lower = text.lower()
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    # Extract the captured group
                    value = match.group(1).strip()
                    
                    # Clean and validate the value
                    cleaned_value = self._clean_extracted_value(value, field)
                    if cleaned_value:
                        findings[field] = cleaned_value
                        break  # Use first match for each field
        
        # Apply report-specific post-processing
        if report_type == 'TTE':
            findings = self._post_process_tte_findings(findings, text)
        elif report_type == 'ECG':
            findings = self._post_process_ecg_findings(findings, text)
        elif report_type == 'EXERCISE_TEST':
            findings = self._post_process_exercise_findings(findings, text)
        elif report_type == 'CONSULT':
            findings = self._post_process_consult_findings(findings, text)
        
        return findings
    
    def _clean_extracted_value(self, value: str, field: str) -> Optional[str]:
        """Clean and validate extracted values"""
        if not value or len(value.strip()) < 1:
            return None
        
        value = value.strip()
        
        # Remove common artifacts
        value = re.sub(r'^(?:is|was|heeft|toont|van)\s+', '', value, flags=re.IGNORECASE)
        value = re.sub(r'\s+(?:mm|ms|%|watt|W)$', '', value)
        
        # Validate based on field type
        if field.endswith('_hr') or field.endswith('_rate'):
            # Should be numeric for heart rate
            if not re.match(r'^\d+$', value):
                return None
        elif field.endswith('_bp'):
            # Should be in format xxx/xxx for blood pressure
            if not re.match(r'^\d+/\d+$', value):
                return None
        elif field in ['lv_edd', 'ivs', 'pw', 'pr_interval', 'qtc', 'qrs_duration']:
            # Should be numeric for measurements
            if not re.match(r'^\d+$', value):
                return None
        elif field == 'lvef':
            # Should be numeric percentage
            if not re.match(r'^\d+$', value):
                return None
            # Validate reasonable range
            if not (10 <= int(value) <= 80):
                return None
        
        return value
    
    def _post_process_tte_findings(self, findings: Dict[str, Any], text: str) -> Dict[str, Any]:
        """Post-process TTE findings for better formatting"""
        text_lower = text.lower()
        
        # Enhance valve descriptions
        for valve in ['mitral_valve', 'aortic_valve', 'tricuspid_valve', 'pulmonary_valve']:
            if valve in findings:
                valve_value = findings[valve]
                
                # Look for severity indicators
                if 'mild' in text_lower or 'licht' in text_lower:
                    if 'insufficiëntie' in valve_value:
                        findings[valve] = f'milde {valve_value}'
                elif 'matig' in text_lower or 'moderate' in text_lower:
                    if 'insufficiëntie' in valve_value:
                        findings[valve] = f'matige {valve_value}'
                elif 'ernstig' in text_lower or 'severe' in text_lower:
                    if 'insufficiëntie' in valve_value:
                        findings[valve] = f'ernstige {valve_value}'
        
        # Look for additional descriptive information
        if 'wall_motion' not in findings:
            if any(term in text_lower for term in ['hypokinese', 'akinese', 'dyskinese']):
                findings['wall_motion'] = 'regionale wandbewegingsstoornissen aanwezig'
        
        return findings
    
    def _post_process_ecg_findings(self, findings: Dict[str, Any], text: str) -> Dict[str, Any]:
        """Post-process ECG findings"""
        text_lower = text.lower()
        
        # Enhance rhythm description
        if 'rhythm' in findings:
            rhythm = findings['rhythm']
            if 'sinusaal' in rhythm or 'sinus' in rhythm:
                if 'tachycardie' in text_lower:
                    findings['rhythm'] = 'sinustachycardie'
                elif 'bradycardie' in text_lower:
                    findings['rhythm'] = 'sinusbradycardie'
        
        # Look for ST-segment changes
        if 'st_segments' not in findings:
            if any(term in text_lower for term in ['st-elevatie', 'st-depressie', 'st-veranderingen']):
                findings['st_segments'] = 'ST-segmentveranderingen aanwezig'
        
        # Look for T-wave changes
        if 't_waves' not in findings:
            if any(term in text_lower for term in ['t-inversie', 't-afvlakking', 't-veranderingen']):
                findings['t_waves'] = 'T-golfveranderingen aanwezig'
        
        return findings
    
    def _post_process_exercise_findings(self, findings: Dict[str, Any], text: str) -> Dict[str, Any]:
        """Post-process exercise test findings"""
        text_lower = text.lower()
        
        # Determine protocol if not specified
        if 'protocol' not in findings:
            if 'fiets' in text_lower:
                findings['protocol'] = 'Fietsergometrie'
            elif 'loop' in text_lower or 'treadmill' in text_lower:
                findings['protocol'] = 'Loopbandtest'
        
        # Enhance symptom description
        if 'symptoms' in findings and findings['symptoms'] == 'geen':
            findings['symptoms'] = 'geen klachten tijdens inspanning'
        
        return findings
    
    def _post_process_consult_findings(self, findings: Dict[str, Any], text: str) -> Dict[str, Any]:
        """Post-process consult findings with formal medical language"""
        text_lower = text.lower()
        
        # Enhance reason for visit
        if 'reason_visit' in findings:
            reason = findings['reason_visit']
            # Make it more formal
            if 'pijn' in reason and 'borst' in reason:
                findings['reason_visit'] = 'Thoracale pijn bij inspanning'
            elif 'kortademig' in reason:
                findings['reason_visit'] = 'Progressieve dyspnoe'
            elif 'hartkloppingen' in reason:
                findings['reason_visit'] = 'Palpitaties'
        
        # Enhance current complaints with medical terminology
        if 'current_complaints' in findings:
            complaints = findings['current_complaints']
            # Replace common terms with medical equivalents
            complaints = re.sub(r'\bpijn\b', 'pijn', complaints)
            complaints = re.sub(r'\bkortademig\b', 'dyspnoe', complaints)
            complaints = re.sub(r'\bhartkloppingen\b', 'palpitaties', complaints)
            complaints = re.sub(r'\bduizelig\b', 'duizeligheid', complaints)
            findings['current_complaints'] = complaints
        
        return findings
    
    def get_processing_summary(self, findings: Dict[str, Any], report_type: str) -> str:
        """Get a summary of what was processed"""
        template_fields = self.templates.get_template_fields(report_type)
        required_fields = template_fields['required']
        optional_fields = template_fields['optional']
        
        extracted_required = [f for f in required_fields if f in findings]
        extracted_optional = [f for f in optional_fields if f in findings]
        
        summary = f"Verwerkt: {len(extracted_required)}/{len(required_fields)} verplichte velden, "
        summary += f"{len(extracted_optional)}/{len(optional_fields)} optionele velden"
        
        return summary


def test_enhanced_processor():
    """Test the enhanced medical processor"""
    processor = EnhancedMedicalProcessor()
    
    # Test TTE processing
    tte_text = """
    Transthoracale echocardiografie uitgevoerd.
    Linker ventrikel EDD 52 mm, IVS 11 mm, PW 10 mm.
    LVEF is 65 procent, goede systolische functie.
    Mitralisklep toont milde insufficiëntie.
    Aortaklep is normaal.
    Geen regionale wandbewegingsstoornissen.
    """
    
    tte_result = processor.process_transcription(tte_text, 'TTE')
    print("=== TTE PROCESSING TEST ===")
    print(tte_result)
    print("\n" + "="*50 + "\n")
    
    # Test ECG processing
    ecg_text = """
    ECG toont sinusritme met hartslag 75 per minuut.
    PR interval is 160 ms, QRS duur normaal.
    QTc is 420 ms, normale as.
    Geen ST-segmentveranderingen.
    """
    
    ecg_result = processor.process_transcription(ecg_text, 'ECG')
    print("=== ECG PROCESSING TEST ===")
    print(ecg_result)
    print("\n" + "="*50 + "\n")
    
    # Test CONSULT processing
    consult_text = """
    Patiënt komt voor pijn op de borst bij inspanning.
    Klachten bestaan uit drukkende pijn retrosternaal.
    Gebruikt lisinopril 10 mg voor hypertensie.
    Cardiovasculair onderzoek toont regelmatige hartslag.
    Verdenking op stabiele angina pectoris.
    Plan: inspannings-ECG en eventueel coronair angiogram.
    """
    
    consult_result = processor.process_transcription(consult_text, 'CONSULT')
    print("=== CONSULT PROCESSING TEST ===")
    print(consult_result)


if __name__ == "__main__":
    test_enhanced_processor()

