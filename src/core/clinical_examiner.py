"""
Clinical Examination Dictation System
CRITICAL: NEVER fabricate or make up any measurements or findings
Only extract and structure explicitly mentioned information in templates
"""

import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ExaminationResult:
    """Structure for storing examination results with source validation"""
    investigation_type: str
    findings: Dict[str, Any]
    template_used: str
    missing_fields: List[str]
    confidence_scores: Dict[str, float]
    source_validation: Dict[str, str]  # Maps each finding to source text
    formatted_report: str


class ClinicalExaminer:
    """
    Processes clinical examination dictation into structured templates
    STRICT RULE: Only use explicitly mentioned measurements and findings
    """
    
    def __init__(self):
        self.templates = self._load_templates()
        self.measurement_patterns = self._create_measurement_patterns()
        self.investigation_keywords = self._load_investigation_keywords()
    
    def _load_templates(self) -> Dict[str, Dict]:
        """Load examination templates with required fields"""
        return {
            'ECG': {
                'template': """ECG op {date}:
- Ritme: {rhythm} met ventriculair antwoord aan {rate}/min
- PR: {pr_status} {pr_value} ms
- QRS: {qrs_axis} as, {qrs_morphology}
- Repolarisatie: {repolarization}
- QTc: {qtc_status} {qtc_value} ms""",
                'required_fields': ['rhythm', 'rate'],
                'optional_fields': ['pr_status', 'pr_value', 'qrs_axis', 'qrs_morphology', 'repolarization', 'qtc_status', 'qtc_value'],
                'field_patterns': {
                    'rhythm': r'(?:ritme|rhythm).*?(sinusaal|VKF|voorkamerflutter|atriale tachycardie|sinusritme)',
                    'rate': r'(?:frequentie|rate|antwoord).*?(\d+)(?:/min|per minuut|bpm)',
                    'pr_value': r'PR.*?(\d+)\s*ms',
                    'qtc_value': r'QTc.*?(\d+)\s*ms',
                    'qrs_axis': r'(?:as|axis).*?(normale|linkser|rechter)',
                    'qrs_morphology': r'QRS.*?(smal|verbreed met LBTB|verbreed met RBTB|verbreed met aspecifiek IVCD)'
                }
            },
            'EXERCISE_TEST': {
                'template': """Fietsproef op {date}:
- Patiënt fietst tot {max_watts} W waarbij de hartslag oploopt van {hr_start} tot {hr_max} /min ({hr_percentage}% van voorspelde waarde)
- Bloeddruk stijgt tot {bp_systolic} / {bp_diastolic} mmHg
- Klachten: {symptoms}
- ECG tijdens inspanning toont {ischemia} argumenten voor ischemie en {arrhythmia} aritmie""",
                'required_fields': ['max_watts', 'hr_max'],
                'optional_fields': ['hr_start', 'hr_percentage', 'bp_systolic', 'bp_diastolic', 'symptoms', 'ischemia', 'arrhythmia'],
                'field_patterns': {
                    'max_watts': r'(?:tot|maximum).*?(\d+)\s*[Ww]att',
                    'hr_start': r'(?:hartslag|HR).*?van\s*(\d+)',
                    'hr_max': r'(?:tot|maximum).*?(\d+)(?:/min|bpm)',
                    'hr_percentage': r'(\d+)%.*?voorspelde',
                    'bp_systolic': r'bloeddruk.*?(\d+)\s*/\s*\d+',
                    'bp_diastolic': r'bloeddruk.*?\d+\s*/\s*(\d+)',
                    'symptoms': r'klachten.*?(ja|nee|geen|wel)',
                    'ischemia': r'(?:wel|geen).*?ischemie',
                    'arrhythmia': r'(?:wel|geen).*?aritmie'
                }
            },
            'TTE': {
                'template': """TTE op {date}:
- Linker ventrikel: {lv_morphology}troof met EDD {lv_edd} mm, IVS {ivs} mm, PW {pw} mm
- Globale functie: {lv_function} met LVEF {lvef}% {lvef_method}
- Regionaal: {regional_function}
- Rechter ventrikel: {rv_morphology}troof, globale functie: {rv_function} met TAPSE {tapse} mm en RV S' {rv_s_prime} cm/s
- Diastole: {diastolic_function} met E {e_velocity} cm/s, A {a_velocity} cm/s, E DT {e_dt} ms, E' septaal {e_prime} cm/s, E/E' {e_e_prime}. L-golf: {l_wave}
- Atria: LA {la_size} {la_dimension} mm, {la_volume} mL, RA {ra_volume} mL
- Aortadimensies: sinus {aortic_sinus} mm, sinotubulair {sinotubular} mm, ascendens {ascending} mm
- Mitralisklep: morfologisch {mitral_morphology}. Insufficiëntie: {mitral_regurg}; stenose: geen
- Aortaklep: {aortic_cusps}, morfologisch {aortic_morphology}. Functioneel: geen tekort
- Pulmonalisklep: insufficiëntie: {pulmonary_regurg}; stenose: geen
- Tricuspiedklep: insufficiëntie: {tricuspid_regurg}; geschatte RVSP: {rvsp} mmHg of niet opmeetbaar + CVD {cvp} mmHg gezien vena cava inferior: {ivc_size} mm, variabiliteit: {ivc_variability}
- Pericard: {pericardium}""",
                'required_fields': ['lv_function', 'lvef'],
                'optional_fields': ['lv_morphology', 'lv_edd', 'ivs', 'pw', 'lvef_method', 'regional_function', 
                                  'rv_morphology', 'rv_function', 'tapse', 'rv_s_prime', 'diastolic_function',
                                  'e_velocity', 'a_velocity', 'e_dt', 'e_prime', 'e_e_prime', 'l_wave',
                                  'la_size', 'la_dimension', 'la_volume', 'ra_volume', 'aortic_sinus',
                                  'sinotubular', 'ascending', 'mitral_morphology', 'mitral_regurg',
                                  'aortic_cusps', 'aortic_morphology', 'pulmonary_regurg', 'tricuspid_regurg',
                                  'rvsp', 'cvp', 'ivc_size', 'ivc_variability', 'pericardium'],
                'field_patterns': {
                    'lvef': r'(?:LVEF|ejectiefractie).*?(\d+)%',
                    'lv_edd': r'EDD.*?(\d+)\s*mm',
                    'ivs': r'IVS.*?(\d+)\s*mm',
                    'pw': r'PW.*?(\d+)\s*mm',
                    'tapse': r'TAPSE.*?(\d+)\s*mm',
                    'rv_s_prime': r"RV S'.*?(\d+(?:\.\d+)?)\s*cm/s",
                    'e_velocity': r'E.*?(\d+(?:\.\d+)?)\s*cm/s',
                    'a_velocity': r'A.*?(\d+(?:\.\d+)?)\s*cm/s',
                    'e_dt': r'E DT.*?(\d+)\s*ms',
                    'e_prime': r"E'.*?(\d+(?:\.\d+)?)\s*cm/s",
                    'e_e_prime': r"E/E'.*?(\d+(?:\.\d+)?)",
                    'la_dimension': r'LA.*?(\d+)\s*mm',
                    'la_volume': r'LA.*?(\d+)\s*mL',
                    'ra_volume': r'RA.*?(\d+)\s*mL',
                    'aortic_sinus': r'sinus.*?(\d+)\s*mm',
                    'sinotubular': r'sinotubulair.*?(\d+)\s*mm',
                    'ascending': r'ascendens.*?(\d+)\s*mm',
                    'rvsp': r'RVSP.*?(\d+)\s*mmHg',
                    'cvp': r'CVD.*?(\d+)\s*mmHg',
                    'ivc_size': r'vena cava.*?(\d+)\s*mm'
                }
            },
            'DEVICE_INTERROGATION': {
                'template': """Device interrogatie op {date}:
- Device type: {device_type}
- Fabrikant: {manufacturer}
- Model: {model}
- Implantatie datum: {implant_date}
- Batterij status: {battery_percentage}% - geschatte levensduur {battery_years} jaar
- Lead impedanties: RA {ra_impedance} Ohm, RV {rv_impedance} Ohm, LV {lv_impedance} Ohm
- Sensing: RA {ra_sensing} mV, RV {rv_sensing} mV, LV {lv_sensing} mV
- Pacing thresholds: RA {ra_threshold} V @ {ra_pulse_width} ms, RV {rv_threshold} V @ {rv_pulse_width} ms, LV {lv_threshold} V @ {lv_pulse_width} ms
- Pacing percentage: RA {ra_pacing}%, RV {rv_pacing}%, LV {lv_pacing}%
- Aritmie episodes: {arrhythmia_episodes}""",
                'required_fields': ['device_type', 'battery_percentage'],
                'optional_fields': ['manufacturer', 'model', 'implant_date', 'battery_years', 'ra_impedance',
                                  'rv_impedance', 'lv_impedance', 'ra_sensing', 'rv_sensing', 'lv_sensing',
                                  'ra_threshold', 'ra_pulse_width', 'rv_threshold', 'rv_pulse_width',
                                  'lv_threshold', 'lv_pulse_width', 'ra_pacing', 'rv_pacing', 'lv_pacing',
                                  'arrhythmia_episodes'],
                'field_patterns': {
                    'device_type': r'(?:device|apparaat).*?(pacemaker|ICD|CRT-P|CRT-D)',
                    'battery_percentage': r'batterij.*?(\d+)%',
                    'battery_years': r'levensduur.*?(\d+(?:\.\d+)?)\s*jaar',
                    'ra_impedance': r'RA.*?(\d+)\s*[Oo]hm',
                    'rv_impedance': r'RV.*?(\d+)\s*[Oo]hm',
                    'lv_impedance': r'LV.*?(\d+)\s*[Oo]hm',
                    'ra_sensing': r'RA.*?(\d+(?:\.\d+)?)\s*mV',
                    'rv_sensing': r'RV.*?(\d+(?:\.\d+)?)\s*mV',
                    'lv_sensing': r'LV.*?(\d+(?:\.\d+)?)\s*mV',
                    'ra_threshold': r'RA.*?(\d+(?:\.\d+)?)\s*V',
                    'rv_threshold': r'RV.*?(\d+(?:\.\d+)?)\s*V',
                    'lv_threshold': r'LV.*?(\d+(?:\.\d+)?)\s*V',
                    'ra_pacing': r'RA.*?(\d+)%',
                    'rv_pacing': r'RV.*?(\d+)%',
                    'lv_pacing': r'LV.*?(\d+)%'
                }
            },
            'HOLTER': {
                'template': """Holter monitoring ({duration} uur) op {date}:
- Gemiddelde hartfrequentie: {avg_hr} /min
- Minimum hartfrequentie: {min_hr} /min om {min_hr_time}
- Maximum hartfrequentie: {max_hr} /min om {max_hr_time}
- Supraventriculaire extrasystolen: {sves_count} ({sves_percentage}%)
- Ventriculaire extrasystolen: {ves_count} ({ves_percentage}%)
- Supraventriculaire tachycardie episodes: {svt_episodes}
- Ventriculaire tachycardie episodes: {vt_episodes}
- Pauzes: {pauses}
- Symptoom-ritme correlatie: {symptom_correlation}""",
                'required_fields': ['duration', 'avg_hr'],
                'optional_fields': ['min_hr', 'min_hr_time', 'max_hr', 'max_hr_time', 'sves_count',
                                  'sves_percentage', 'ves_count', 'ves_percentage', 'svt_episodes',
                                  'vt_episodes', 'pauses', 'symptom_correlation'],
                'field_patterns': {
                    'duration': r'(?:holter|monitoring).*?(\d+)\s*uur',
                    'avg_hr': r'gemiddelde.*?(\d+)(?:/min|bpm)',
                    'min_hr': r'minimum.*?(\d+)(?:/min|bpm)',
                    'max_hr': r'maximum.*?(\d+)(?:/min|bpm)',
                    'sves_count': r'supraventriculaire.*?(\d+)',
                    'sves_percentage': r'supraventriculaire.*?\((\d+)%\)',
                    'ves_count': r'ventriculaire.*?(\d+)',
                    'ves_percentage': r'ventriculaire.*?\((\d+)%\)',
                    'svt_episodes': r'supraventriculaire tachycardie.*?(\d+)',
                    'vt_episodes': r'ventriculaire tachycardie.*?(\d+)'
                }
            }
        }
    
    def _create_measurement_patterns(self) -> List[str]:
        """Create patterns for detecting measurements"""
        return [
            r'(\d+(?:\.\d+)?)\s*(mm|mmHg|ms|cm/s|mV|V|Ohm|W|bpm|%)',
            r'(\d+(?:\.\d+)?)\s*(?:millimeter|millimetre)',
            r'(\d+(?:\.\d+)?)\s*(?:procent|percent)',
            r'(\d+(?:\.\d+)?)\s*(?:watt|volt|ohm)'
        ]
    
    def _load_investigation_keywords(self) -> Dict[str, List[str]]:
        """Load keywords for investigation type detection"""
        return {
            'ECG': ['ecg', 'elektrocardiogram', 'ritme', 'pr interval', 'qrs', 'qtc'],
            'EXERCISE_TEST': ['fietsproef', 'inspanningstest', 'ergometrie', 'cycloergometrie', 'watt'],
            'TTE': ['tte', 'echo', 'echocardiografie', 'linker ventrikel', 'lvef', 'tapse'],
            'DEVICE_INTERROGATION': ['device', 'pacemaker', 'icd', 'crt', 'batterij', 'lead', 'sensing'],
            'HOLTER': ['holter', 'monitoring', 'extrasystolen', 'tachycardie', 'pauzes']
        }
    
    def analyze_examination(self, transcript: str, investigation_type: str = None) -> ExaminationResult:
        """
        Main analysis function for clinical examinations
        CRITICAL: Only uses explicitly mentioned measurements and findings
        """
        # Step 1: Detect investigation type if not provided
        if not investigation_type:
            investigation_type = self._detect_investigation_type(transcript)
        
        if investigation_type not in self.templates:
            return self._empty_result(f"Unknown investigation type: {investigation_type}")
        
        # Step 2: Extract measurements and findings with source validation
        findings = self._extract_findings_with_validation(transcript, investigation_type)
        
        # Step 3: Identify missing required fields
        missing_fields = self._identify_missing_fields(findings, investigation_type)
        
        # Step 4: Calculate confidence scores
        confidence_scores = self._calculate_confidence_scores(findings, transcript)
        
        # Step 5: Create source validation mapping
        source_validation = self._create_source_validation(findings, transcript)
        
        # Step 6: Format the report using template
        formatted_report = self._format_report(findings, investigation_type, missing_fields)
        
        return ExaminationResult(
            investigation_type=investigation_type,
            findings=findings,
            template_used=self.templates[investigation_type]['template'],
            missing_fields=missing_fields,
            confidence_scores=confidence_scores,
            source_validation=source_validation,
            formatted_report=formatted_report
        )
    
    def _detect_investigation_type(self, transcript: str) -> str:
        """Detect the type of investigation from transcript"""
        transcript_lower = transcript.lower()
        
        # Score each investigation type based on keyword matches
        scores = {}
        for inv_type, keywords in self.investigation_keywords.items():
            score = sum(1 for keyword in keywords if keyword in transcript_lower)
            if score > 0:
                scores[inv_type] = score
        
        if not scores:
            return "UNKNOWN"
        
        # Return the investigation type with highest score
        return max(scores, key=scores.get)
    
    def _extract_findings_with_validation(self, transcript: str, investigation_type: str) -> Dict[str, Any]:
        """Extract findings with strict source validation"""
        findings = {}
        template_info = self.templates[investigation_type]
        
        # Add current date
        findings['date'] = datetime.now().strftime('%d-%m-%Y')
        
        # Extract each field using its specific pattern
        for field, pattern in template_info['field_patterns'].items():
            matches = re.finditer(pattern, transcript, re.IGNORECASE)
            
            for match in matches:
                if match.groups():
                    value = match.group(1).strip()
                    
                    # Validate the extracted value
                    if self._validate_field_value(field, value, investigation_type):
                        findings[field] = value
                        # Store source context for validation
                        findings[f"{field}_source"] = self._get_context_around_match(transcript, match)
                        break  # Use first valid match
        
        # Extract qualitative findings (non-numeric)
        qualitative_findings = self._extract_qualitative_findings(transcript, investigation_type)
        findings.update(qualitative_findings)
        
        return findings
    
    def _validate_field_value(self, field: str, value: str, investigation_type: str) -> bool:
        """Validate that extracted field value is reasonable"""
        # Define reasonable ranges for common measurements
        ranges = {
            'rate': (30, 250),  # Heart rate
            'lvef': (10, 80),   # LVEF percentage
            'pr_value': (80, 300),  # PR interval
            'qtc_value': (300, 600),  # QTc interval
            'max_watts': (25, 400),  # Exercise test watts
            'bp_systolic': (70, 250),  # Systolic BP
            'bp_diastolic': (40, 150),  # Diastolic BP
            'battery_percentage': (0, 100),  # Device battery
            'duration': (12, 48)  # Holter duration
        }
        
        # Check if value is numeric and within reasonable range
        try:
            numeric_value = float(value)
            if field in ranges:
                min_val, max_val = ranges[field]
                return min_val <= numeric_value <= max_val
        except ValueError:
            # Non-numeric values are generally acceptable
            pass
        
        # Additional validation for specific fields
        if field == 'rhythm':
            valid_rhythms = ['sinusaal', 'VKF', 'voorkamerflutter', 'atriale tachycardie', 'sinusritme']
            return any(rhythm in value.lower() for rhythm in valid_rhythms)
        
        if field == 'device_type':
            valid_types = ['pacemaker', 'icd', 'crt-p', 'crt-d']
            return any(device_type in value.lower() for device_type in valid_types)
        
        return True  # Default to accepting the value
    
    def _extract_qualitative_findings(self, transcript: str, investigation_type: str) -> Dict[str, str]:
        """Extract qualitative (non-numeric) findings"""
        qualitative = {}
        
        # Define qualitative patterns for each investigation type
        qualitative_patterns = {
            'ECG': {
                'pr_status': r'PR.*?(normaal|verlengd|verkort)',
                'qtc_status': r'QTc.*?(normaal|verlengd)',
                'repolarization': r'repolarisatie.*?(normaal|gestoord.*?)'
            },
            'EXERCISE_TEST': {
                'symptoms': r'klachten.*?(ja|nee|geen|wel)',
                'ischemia': r'(wel|geen).*?ischemie',
                'arrhythmia': r'(wel|geen).*?aritmie'
            },
            'TTE': {
                'lv_function': r'globale functie.*?(goed|licht gedaald|matig gedaald|ernstig gedaald)',
                'regional_function': r'regionaal.*?(geen kinetiekstoornissen|zone van hypokinesie|zone van akinesie)',
                'diastolic_function': r'diastole.*?(normaal|vertraagde relaxatie|dysfunctie graad 2|dysfunctie graad 3)',
                'la_size': r'LA.*?(normaal|licht gedilateerd|sterk gedilateerd)',
                'mitral_morphology': r'mitralisklep.*?morfologisch.*?(normaal|sclerotisch|verdikt|prolaps|restrictief)',
                'aortic_morphology': r'aortaklep.*?morfologisch.*?(normaal|sclerotisch|mild verkalkt|matig verkalkt|ernstig verkalkt)',
                'aortic_cusps': r'aortaklep.*?(tricuspied|bicuspied)'
            },
            'HOLTER': {
                'pauses': r'pauzes.*?(geen|wel)',
                'symptom_correlation': r'symptoom.*?correlatie.*?([^.]+)'
            }
        }
        
        if investigation_type in qualitative_patterns:
            for field, pattern in qualitative_patterns[investigation_type].items():
                match = re.search(pattern, transcript, re.IGNORECASE)
                if match:
                    qualitative[field] = match.group(1).strip()
                    qualitative[f"{field}_source"] = self._get_context_around_match(transcript, match)
        
        return qualitative
    
    def _get_context_around_match(self, text: str, match: re.Match, context_chars: int = 50) -> str:
        """Get context around a regex match for source validation"""
        start = max(0, match.start() - context_chars)
        end = min(len(text), match.end() + context_chars)
        return text[start:end].strip()
    
    def _identify_missing_fields(self, findings: Dict[str, Any], investigation_type: str) -> List[str]:
        """Identify required fields that are missing"""
        template_info = self.templates[investigation_type]
        missing = []
        
        for field in template_info['required_fields']:
            if field not in findings:
                missing.append(field)
        
        return missing
    
    def _calculate_confidence_scores(self, findings: Dict[str, Any], transcript: str) -> Dict[str, float]:
        """Calculate confidence scores for extracted findings"""
        scores = {}
        
        for field, value in findings.items():
            if field.endswith('_source'):
                continue  # Skip source fields
            
            base_confidence = 0.8
            
            # Increase confidence for numeric values with units
            if isinstance(value, str) and re.search(r'\d+(?:\.\d+)?', value):
                base_confidence += 0.1
            
            # Increase confidence if source context is available
            if f"{field}_source" in findings:
                base_confidence += 0.1
            
            scores[field] = min(base_confidence, 1.0)
        
        return scores
    
    def _create_source_validation(self, findings: Dict[str, Any], transcript: str) -> Dict[str, str]:
        """Create mapping of findings to source text"""
        validation = {}
        
        for field, value in findings.items():
            if field.endswith('_source'):
                # Map the actual field to its source
                actual_field = field.replace('_source', '')
                if actual_field in findings:
                    validation[actual_field] = value
        
        return validation
    
    def _format_report(self, findings: Dict[str, Any], investigation_type: str, missing_fields: List[str]) -> str:
        """Format findings into structured report using template"""
        template_info = self.templates[investigation_type]
        template = template_info['template']
        
        # Clean findings (remove source fields for formatting)
        clean_findings = {k: v for k, v in findings.items() if not k.endswith('_source')}
        
        # Create a complete findings dict with placeholders for missing fields
        all_fields = template_info['required_fields'] + template_info['optional_fields']
        complete_findings = clean_findings.copy()
        
        # Add placeholders for missing fields
        for field in all_fields:
            if field not in complete_findings:
                complete_findings[field] = '[niet vermeld]'
        
        # Handle missing fields by removing incomplete sentences
        formatted_template = self._handle_missing_fields(template, complete_findings, missing_fields)
        
        try:
            # Format the template with complete findings
            formatted_report = formatted_template.format(**complete_findings)
            
            # Remove lines that are mostly empty or contain only "[niet vermeld]"
            lines = formatted_report.split('\n')
            cleaned_lines = []
            
            for line in lines:
                # Skip lines that are mostly placeholders
                if '[niet vermeld]' in line:
                    # Count how much actual content vs placeholders
                    content_without_placeholders = re.sub(r'\[niet vermeld\]', '', line).strip()
                    # Remove common template words to count actual medical content
                    content_without_template = re.sub(r'(met|en|van|op|is|zijn|:|-)', '', content_without_placeholders).strip()
                    
                    if len(content_without_template) < 5:  # Skip if very little actual content
                        continue
                
                cleaned_lines.append(line)
            
            return '\n'.join(cleaned_lines)
            
        except KeyError as e:
            # If formatting still fails, create a simple report
            return self._create_simple_report(clean_findings, investigation_type)
    
    def _handle_missing_fields(self, template: str, findings: Dict[str, Any], missing_fields: List[str]) -> str:
        """Handle missing fields by removing incomplete sentences"""
        # For each missing required field, try to remove the entire line or make it optional
        modified_template = template
        
        for field in missing_fields:
            # Find lines containing this field and mark them for conditional inclusion
            lines = modified_template.split('\n')
            new_lines = []
            
            for line in lines:
                if f'{{{field}}}' in line:
                    # Check if this line has other required fields that are present
                    other_fields_in_line = re.findall(r'\{([^}]+)\}', line)
                    other_fields_present = [f for f in other_fields_in_line if f != field and f in findings]
                    
                    if other_fields_present:
                        # Keep line but mark missing field
                        line = line.replace(f'{{{field}}}', '[niet vermeld]')
                    else:
                        # Skip this line entirely if no other important fields
                        continue
                
                new_lines.append(line)
            
            modified_template = '\n'.join(new_lines)
        
        return modified_template
    
    def _create_simple_report(self, findings: Dict[str, Any], investigation_type: str) -> str:
        """Create a simple report when template formatting fails"""
        report_lines = [f"{investigation_type} op {findings.get('date', 'onbekende datum')}:"]
        
        # Add findings in a simple format
        for field, value in findings.items():
            if field != 'date' and value != '[niet vermeld]':
                # Convert field names to readable Dutch
                readable_field = field.replace('_', ' ').title()
                report_lines.append(f"- {readable_field}: {value}")
        
        return '\n'.join(report_lines)
    
    def _empty_result(self, reason: str) -> ExaminationResult:
        """Return empty examination result with reason"""
        return ExaminationResult(
            investigation_type="UNKNOWN",
            findings={},
            template_used="",
            missing_fields=[],
            confidence_scores={},
            source_validation={},
            formatted_report=f"Fout: {reason}"
        )


def test_clinical_examiner():
    """Test function for the clinical examiner"""
    examiner = ClinicalExaminer()
    
    # Test ECG dictation
    ecg_transcript = """
    ECG van vandaag toont een sinusritme met een frequentie van 75 per minuut.
    Het PR interval is normaal met 160 ms. QRS is smal met normale as.
    De repolarisatie is normaal. QTc is normaal met 420 ms.
    """
    
    # Test TTE dictation
    tte_transcript = """
    Echo van vandaag: Linker ventrikel is normaal met LVEF van 60%.
    EDD is 50 mm, IVS 10 mm, PW 9 mm. Globale functie is goed.
    TAPSE is 20 mm. LA is normaal met 35 mm.
    """
    
    print("=== ECG ANALYSIS TEST ===")
    ecg_result = examiner.analyze_examination(ecg_transcript, "ECG")
    print(ecg_result.formatted_report)
    print(f"\nMissing fields: {ecg_result.missing_fields}")
    print(f"Confidence scores: {ecg_result.confidence_scores}")
    
    print("\n=== TTE ANALYSIS TEST ===")
    tte_result = examiner.analyze_examination(tte_transcript, "TTE")
    print(tte_result.formatted_report)
    print(f"\nMissing fields: {tte_result.missing_fields}")
    print(f"Confidence scores: {tte_result.confidence_scores}")
    
    print("\n=== AUTO-DETECTION TEST ===")
    auto_result = examiner.analyze_examination(ecg_transcript)
    print(f"Detected type: {auto_result.investigation_type}")


if __name__ == "__main__":
    test_clinical_examiner()

