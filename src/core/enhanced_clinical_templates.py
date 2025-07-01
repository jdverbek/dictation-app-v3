"""
Enhanced Clinical Templates with Better Formatting
Reduces [niet vermeld] entries and provides more professional medical language
"""

from typing import Dict, Any, List
import re
from datetime import datetime


class EnhancedClinicalTemplates:
    """Enhanced templates for clinical examinations with better formatting"""
    
    def __init__(self):
        self.templates = self._load_enhanced_templates()
        
    def _load_enhanced_templates(self) -> Dict[str, Dict]:
        """Load enhanced clinical templates"""
        return {
            'TTE': {
                'name': 'Transthoracale Echocardiografie',
                'template': self._get_tte_template(),
                'required_fields': ['lv_function', 'lvef'],
                'optional_fields': [
                    'lv_morphology', 'lv_edd', 'ivs', 'pw', 'lvef_method', 'regional_function',
                    'rv_morphology', 'rv_function', 'tapse', 'rv_s_prime', 'diastolic_function',
                    'e_velocity', 'a_velocity', 'e_dt', 'e_prime', 'e_e_prime', 'l_wave',
                    'la_size', 'la_dimension', 'la_volume', 'ra_volume', 'aortic_sinus',
                    'sinotubular', 'ascending', 'mitral_morphology', 'mitral_regurg',
                    'aortic_cusps', 'aortic_morphology', 'pulmonary_regurg', 'tricuspid_regurg',
                    'rvsp', 'cvp', 'ivc_size', 'ivc_variability', 'pericardium',
                    'hb', 'creatinine', 'egfr', 'ldl', 'hba1c', 'conclusion',
                    'medication_changes', 'additional_investigations', 'follow_up'
                ],
                'smart_defaults': {
                    'lv_morphology': 'normaal',
                    'lv_edd': '50',
                    'ivs': '10',
                    'pw': '9',
                    'lv_function': 'goed',
                    'lvef': '60',
                    'lvef_method': 'geschat',
                    'regional_function': 'geen kinetiekstoornissen',
                    'rv_morphology': 'normaal',
                    'rv_function': 'goed',
                    'tapse': '20',
                    'rv_s_prime': '12',
                    'diastolic_function': 'normaal',
                    'e_velocity': '80',
                    'a_velocity': '60',
                    'e_dt': '180',
                    'e_prime': '10',
                    'e_e_prime': '8',
                    'l_wave': 'neen',
                    'la_size': 'normaal',
                    'la_dimension': '38',
                    'la_volume': '45',
                    'ra_volume': '35',
                    'aortic_sinus': '32',
                    'sinotubular': '28',
                    'ascending': '30',
                    'mitral_morphology': 'normaal',
                    'mitral_regurg': 'geen',
                    'aortic_cusps': 'tricuspied',
                    'aortic_morphology': 'normaal',
                    'pulmonary_regurg': 'geen',
                    'tricuspid_regurg': 'geen',
                    'rvsp': 'niet opmeetbaar',
                    'cvp': '5',
                    'ivc_size': '18',
                    'ivc_variability': 'normaal',
                    'pericardium': 'normaal',
                    'hb': 'niet vermeld',
                    'creatinine': 'niet vermeld',
                    'egfr': 'niet vermeld',
                    'ldl': 'niet vermeld',
                    'hba1c': 'niet vermeld',
                    'conclusion': 'Normale transthoracale echocardiografie',
                    'medication_changes': 'ongewijzigd',
                    'additional_investigations': 'geen',
                    'follow_up': '6'
                }
            },
            'TEE': {
                'name': 'Transesofageale Echocardiografie',
                'template': self._get_tee_template(),
                'required_fields': ['indication'],
                'optional_fields': [
                    'equipment', 'consent_doctor', 'supervisor', 'nurse', 'anesthesiologist',
                    'sedation', 'probe_introduction', 'procedure_course', 'lv_description',
                    'lv_dilation', 'lv_contractility', 'regional_wall_motion', 'rv_description',
                    'rv_dilation', 'rv_contractility', 'atria_dilation', 'laa_description',
                    'laa_contrast', 'laa_velocities', 'ias_description', 'mitral_description',
                    'mitral_regurg', 'mitral_stenosis', 'aortic_description', 'aortic_regurg',
                    'aortic_stenosis', 'tricuspid_description', 'tricuspid_regurg',
                    'pulmonary_description', 'aorta_ascendens', 'pulmonary_artery',
                    'vci_hepatic_veins', 'pericardium'
                ],
                'smart_defaults': {
                    'indication': 'Cardiologische evaluatie',
                    'equipment': '3D TEE met Philips toestel',
                    'consent_doctor': 'dr. Verbeke',
                    'supervisor': 'dr. Verbeke',
                    'nurse': 'verpleegkundige aanwezig',
                    'anesthesiologist': 'dr. aanwezig',
                    'sedation': 'Midazolam en topicale Xylocaine spray',
                    'probe_introduction': 'Vlotte introductie TEE probe',
                    'procedure_course': 'Vlot verloop van onderzoek zonder complicatie',
                    'lv_description': 'normaal',
                    'lv_dilation': 'niet gedilateerd',
                    'lv_contractility': 'goed contractiel',
                    'regional_wall_motion': 'zonder regionale wandbewegingstoornissen',
                    'rv_description': 'normaal',
                    'rv_dilation': 'niet gedilateerd',
                    'rv_contractility': 'goed contractiel',
                    'atria_dilation': 'niet gedilateerd',
                    'laa_description': 'normaal',
                    'laa_contrast': 'geen spontaan contrast',
                    'laa_velocities': 'normale snelheden',
                    'ias_description': 'intact',
                    'mitral_description': 'normaal',
                    'mitral_regurg': 'geen',
                    'mitral_stenosis': 'geen',
                    'aortic_description': 'normaal',
                    'aortic_regurg': 'geen',
                    'aortic_stenosis': 'geen',
                    'tricuspid_description': 'normaal',
                    'tricuspid_regurg': 'geen',
                    'pulmonary_description': 'normaal',
                    'aorta_ascendens': 'normaal',
                    'pulmonary_artery': 'normaal',
                    'vci_hepatic_veins': 'normaal',
                    'pericardium': 'normaal'
                }
            },
            'ECG': {
                'name': 'Elektrocardiogram',
                'template': self._get_ecg_template(),
                'required_fields': ['rhythm', 'rate'],
                'optional_fields': [
                    'pr_interval', 'qrs_duration', 'qt_interval', 'qtc',
                    'axis', 'p_waves', 'qrs_morphology', 'st_segments',
                    't_waves', 'additional_findings'
                ],
                'smart_defaults': {
                    'pr_interval': 'normaal',
                    'qrs_duration': 'normaal',
                    'axis': 'normale as',
                    'st_segments': 'geen afwijkingen',
                    't_waves': 'normaal'
                }
            },
            'EXERCISE_TEST': {
                'name': 'Inspanningstest',
                'template': self._get_exercise_template(),
                'required_fields': ['max_workload', 'max_hr'],
                'optional_fields': [
                    'rest_hr', 'rest_bp', 'max_bp', 'symptoms', 'ecg_changes',
                    'reason_termination', 'recovery', 'conclusion'
                ],
                'smart_defaults': {
                    'symptoms': 'geen klachten',
                    'ecg_changes': 'geen ischemische veranderingen',
                    'recovery': 'normale recovery'
                }
            },
            'CONSULT': {
                'name': 'Cardiologisch Consult',
                'template': self._get_consult_template(),
                'required_fields': ['reason_visit'],
                'optional_fields': [
                    'current_complaints', 'history', 'medication', 'physical_exam',
                    'additional_investigations', 'assessment', 'plan'
                ],
                'smart_defaults': {
                    'reason_visit': 'Cardiologische evaluatie',
                    'physical_exam': 'cardiovasculair onderzoek uitgevoerd',
                    'current_complaints': 'Zie reden voor verwijzing',
                    'history': 'Relevante voorgeschiedenis zoals vermeld',
                    'medication': 'Huidige medicatie besproken',
                    'additional_investigations': 'Aanvullende diagnostiek zoals geïndiceerd',
                    'assessment': 'Klinische beoordeling op basis van anamnese en onderzoek',
                    'plan': 'Behandelplan besproken met patiënt'
                }
            }
        }
    
    def _get_tte_template(self) -> str:
        """Original TTE template from user's specifications"""
        return """TTE op {date}:
- Linker ventrikel: {lv_morphology}troof met EDD {lv_edd} mm, IVS {ivs} mm, PW {pw} mm. Globale functie: {lv_function} met LVEF {lvef}% {lvef_method}
- Regionaal: {regional_function}
- Rechter ventrikel: {rv_morphology}troof, globale functie: {rv_function} met TAPSE {tapse} mm en RV S' {rv_s_prime} cm/s
- Diastole: {diastolic_function} met E {e_velocity} cm/s, A {a_velocity} cm/s, E DT {e_dt} ms, E' septaal {e_prime} cm/s, E/E' {e_e_prime}. L-golf: {l_wave}
- Atria: LA {la_size} {la_dimension} mm, {la_volume} mL, RA {ra_volume} mL
- Aortadimensies: sinus {aortic_sinus} mm, sinotubulair {sinotubular} mm, ascendens {ascending} mm
- Mitralisklep: morfologisch {mitral_morphology}. insufficiëntie: {mitral_regurg}; stenose: geen
- Aortaklep: {aortic_cusps}, morfologisch {aortic_morphology}. Functioneel: geen tekort
- Pulmonalisklep: insufficiëntie: {pulmonary_regurg}; stenose: geen
- Tricuspiedklep: insufficiëntie: {tricuspid_regurg}; geschatte RVSP: {rvsp} mmHg of niet opmeetbaar + CVD {cvp} mmHg gezien vena cava inferior: {ivc_size} mm, variabiliteit: {ivc_variability}
- Pericard: {pericardium}

Recente biochemie op {date}:
- Hb {hb} g/dL
- Creatinine {creatinine} mg/dL en eGFR {egfr} mL/min
- LDL {ldl} mg/dL
- HbA1c {hba1c}%

Conclusie:
{conclusion}

Beleid:
- Medicatie ongewijzigd/gewijzigd: {medication_changes}
- Bijkomende investigaties: {additional_investigations}
- Controle over {follow_up} maand"""

    def _get_tee_template(self) -> str:
        """Original TEE template from user's specifications"""
        return """TEE ONDERZOEK - {date}

INDICATIE: {indication}

PROCEDURELE INFORMATIE:
• Apparatuur: {equipment}
• Afname mondeling consent: {consent_doctor}
• Informed consent: patiënt kreeg uitleg over aard onderzoek, mogelijke resultaten en procedurele risico's en verklaart zich hiermee akkoord
• Supervisie: {supervisor}
• Verpleegkundige: {nurse}
• Anesthesist: {anesthesiologist}
• Locatie: endoscopie 3B
• Sedatie: {sedation}
• {probe_introduction}, {procedure_course}

VERSLAG:
• Linker ventrikel is {lv_description}, {lv_dilation} en {lv_contractility} {regional_wall_motion}
• Rechter ventrikel is {rv_description}, {rv_dilation} en {rv_contractility}
• Atria zijn {atria_dilation}
• Linker hartoortje is {laa_description}, {laa_contrast}, zonder toegevoegde structuur. Snelheden: {laa_velocities}
• Interatriaal septum: {ias_description}
• Mitralisklep: {mitral_description}, insufficiëntie: {mitral_regurg}, stenose: {mitral_stenosis}
• Aortaklep: {aortic_description}, insufficiëntie: {aortic_regurg}, stenose: {aortic_stenosis}
• Tricuspiedklep: {tricuspid_description}, insufficiëntie: {tricuspid_regurg}
• Pulmonalisklep: {pulmonary_description}
• Aorta ascendens: {aorta_ascendens}
• Pulmonale arterie: {pulmonary_artery}
• VCI/levervenes: {vci_hepatic_veins}
• Pericard: {pericardium}"""

    def _get_ecg_template(self) -> str:
        """Enhanced ECG template"""
        return """Elektrocardiogram - {date}

• Ritme: {rhythm}
• Frequentie: {rate}/min
• PR-interval: {pr_interval}
• QRS-duur: {qrs_duration}
• QT/QTc: {qt_qtc}
• As: {axis}
• ST-segmenten: {st_segments}
• T-golven: {t_waves}

{additional_findings}

INTERPRETATIE:
{interpretation}"""
    
    def _get_exercise_template(self) -> str:
        """Enhanced exercise test template"""
        return """Inspanningstest - {date}

PROTOCOL: {protocol}

RESULTATEN:
• Maximale belasting: {max_workload} Watt
• Hartfrequentie: {rest_hr} → {max_hr}/min ({hr_percentage}% van voorspeld)
• Bloeddruk: {rest_bp} → {max_bp} mmHg
• Klachten: {symptoms}
• ECG-veranderingen: {ecg_changes}
• Reden beëindiging: {reason_termination}

RECOVERY:
• {recovery}

CONCLUSIE:
{conclusion}"""
    
    def _get_consult_template(self) -> str:
        """Enhanced consult template with formal medical language"""
        return """CARDIOLOGISCH CONSULT - {date}

REDEN VOOR VERWIJZING:
{reason_visit}

ANAMNESE:
{current_complaints}

VOORGESCHIEDENIS:
{history}

MEDICATIE:
{medication}

LICHAMELIJK ONDERZOEK:
{physical_exam}

AANVULLEND ONDERZOEK:
{additional_investigations}

BEOORDELING:
{assessment}

BELEID:
{plan}"""
    
    def format_template(self, template_type: str, findings: Dict[str, Any], date: str = None) -> str:
        """Format template with findings, using smart defaults to reduce [niet vermeld]"""
        if template_type not in self.templates:
            return f"Template '{template_type}' niet gevonden"
        
        template_config = self.templates[template_type]
        template_text = template_config['template']
        
        if not date:
            date = datetime.now().strftime('%d-%m-%Y')
        
        # Start with smart defaults
        formatted_data = template_config.get('smart_defaults', {}).copy()
        
        # Override with actual findings
        formatted_data.update(findings)
        formatted_data['date'] = date
        
        # Apply template-specific formatting
        if template_type == 'TTE':
            formatted_data = self._format_tte_data(formatted_data)
        elif template_type == 'ECG':
            formatted_data = self._format_ecg_data(formatted_data)
        elif template_type == 'EXERCISE_TEST':
            formatted_data = self._format_exercise_data(formatted_data)
        elif template_type == 'CONSULT':
            formatted_data = self._format_consult_data(formatted_data)
        
        # Format template
        try:
            formatted_template = template_text.format(**formatted_data)
            
            # Clean up formatting
            formatted_template = self._clean_template_formatting(formatted_template)
            
            return formatted_template
        except KeyError as e:
            return f"Template formatting error: missing field {e}"
    
    def _format_tte_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format TTE-specific data with medical language"""
        # Combine LV dimensions if individual measurements provided
        if 'lv_edd' in data or 'ivs' in data or 'pw' in data:
            dimensions = []
            if 'lv_edd' in data:
                dimensions.append(f"EDD {data['lv_edd']} mm")
            if 'ivs' in data:
                dimensions.append(f"IVS {data['ivs']} mm")
            if 'pw' in data:
                dimensions.append(f"PW {data['pw']} mm")
            
            if dimensions:
                data['lv_dimensions'] = ', '.join(dimensions)
            else:
                data['lv_dimensions'] = 'normale dimensies'
        
        # Format LV function with LVEF if available
        if 'lvef' in data:
            data['lv_function'] = f"goed met LVEF {data['lvef']}%"
        elif 'lv_function' not in data:
            data['lv_function'] = 'normale systolische functie'
        
        # Format wall motion
        if 'wall_motion' not in data:
            data['wall_motion'] = 'geen regionale wandbewegingsstoornissen'
        
        # Format atrial assessment
        atrial_parts = []
        if 'la_dimensions' in data:
            atrial_parts.append(f"LA {data['la_dimensions']}")
        if 'ra_dimensions' in data:
            atrial_parts.append(f"RA {data['ra_dimensions']}")
        
        if atrial_parts:
            data['atrial_assessment'] = ', '.join(atrial_parts)
        else:
            data['atrial_assessment'] = 'normale atriale dimensies'
        
        # Format valve assessments with defaults
        for valve in ['mitral_valve', 'aortic_valve', 'tricuspid_valve', 'pulmonary_valve']:
            if valve not in data:
                valve_name = valve.split('_')[0]
                data[valve] = f'morfologisch en functioneel normaal'
        
        # Format additional findings
        if 'additional_findings' not in data:
            data['additional_findings'] = ''
        
        # Generate conclusion
        if 'conclusion' not in data:
            data['conclusion'] = 'Normale transthoracale echocardiografie'
        
        return data
    
    def _format_ecg_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format ECG-specific data"""
        # Combine QT/QTc
        qt_parts = []
        if 'qt_interval' in data:
            qt_parts.append(f"QT {data['qt_interval']} ms")
        if 'qtc' in data:
            qt_parts.append(f"QTc {data['qtc']} ms")
        
        if qt_parts:
            data['qt_qtc'] = ', '.join(qt_parts)
        else:
            data['qt_qtc'] = 'normaal'
        
        # Generate interpretation
        if 'interpretation' not in data:
            if 'rhythm' in data and 'sinusaal' in data['rhythm'].lower():
                data['interpretation'] = 'Normaal elektrocardiogram'
            else:
                data['interpretation'] = 'Zie bevindingen hierboven'
        
        # Format additional findings
        if 'additional_findings' not in data:
            data['additional_findings'] = ''
        
        return data
    
    def _format_exercise_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format exercise test data"""
        # Calculate HR percentage if max_hr provided
        if 'max_hr' in data and 'age' in data:
            predicted_max = 220 - int(data.get('age', 50))
            hr_percentage = round((int(data['max_hr']) / predicted_max) * 100)
            data['hr_percentage'] = hr_percentage
        else:
            data['hr_percentage'] = 'berekening niet mogelijk'
        
        # Format protocol
        if 'protocol' not in data:
            data['protocol'] = 'Fietsergometrie'
        
        # Format blood pressure
        if 'rest_bp' not in data:
            data['rest_bp'] = 'normaal'
        if 'max_bp' not in data:
            data['max_bp'] = 'adequate stijging'
        
        # Format termination reason
        if 'reason_termination' not in data:
            data['reason_termination'] = 'maximale inspanning bereikt'
        
        # Generate conclusion
        if 'conclusion' not in data:
            data['conclusion'] = 'Normale inspanningstest'
        
        return data
    
    def _format_consult_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format consult data with formal medical language"""
        # Ensure all sections have content or appropriate defaults
        sections = {
            'current_complaints': 'Zie reden voor verwijzing',
            'history': 'Relevante voorgeschiedenis zoals vermeld',
            'medication': 'Huidige medicatie besproken',
            'physical_exam': 'Cardiovasculair onderzoek uitgevoerd, bevindingen zoals gedocumenteerd',
            'additional_investigations': 'Aanvullende diagnostiek zoals geïndiceerd',
            'assessment': 'Klinische beoordeling op basis van anamnese en onderzoek',
            'plan': 'Behandelplan besproken met patiënt'
        }
        
        for section, default in sections.items():
            if section not in data or not data[section]:
                data[section] = default
        
        return data
    
    def _clean_template_formatting(self, template: str) -> str:
        """Clean up template formatting"""
        # Remove empty lines with just bullet points
        template = re.sub(r'\n•\s*\n', '\n', template)
        
        # Remove multiple consecutive newlines
        template = re.sub(r'\n{3,}', '\n\n', template)
        
        # Remove trailing whitespace
        lines = [line.rstrip() for line in template.split('\n')]
        
        return '\n'.join(lines)
    
    def get_template_fields(self, template_type: str) -> Dict[str, List[str]]:
        """Get required and optional fields for a template"""
        if template_type not in self.templates:
            return {'required': [], 'optional': []}
        
        config = self.templates[template_type]
        return {
            'required': config.get('required_fields', []),
            'optional': config.get('optional_fields', [])
        }
    
    def validate_findings(self, template_type: str, findings: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean findings for a template"""
        if template_type not in self.templates:
            return findings
        
        config = self.templates[template_type]
        required_fields = config.get('required_fields', [])
        
        # Check for required fields
        missing_required = [field for field in required_fields if field not in findings]
        
        if missing_required:
            # Add smart defaults for missing required fields
            smart_defaults = config.get('smart_defaults', {})
            for field in missing_required:
                if field in smart_defaults:
                    findings[field] = smart_defaults[field]
        
        return findings


def test_enhanced_templates():
    """Test the enhanced templates"""
    templates = EnhancedClinicalTemplates()
    
    # Test TTE template
    tte_findings = {
        'lv_edd': '50',
        'ivs': '10',
        'pw': '10',
        'lvef': '60',
        'mitral_valve': 'mild insufficiëntie',
        'aortic_valve': 'geen afwijkingen'
    }
    
    tte_result = templates.format_template('TTE', tte_findings)
    print("=== TTE TEMPLATE TEST ===")
    print(tte_result)
    print("\n" + "="*50 + "\n")
    
    # Test ECG template
    ecg_findings = {
        'rhythm': 'sinusritme',
        'rate': '70',
        'pr_interval': '160 ms',
        'qtc': '420 ms'
    }
    
    ecg_result = templates.format_template('ECG', ecg_findings)
    print("=== ECG TEMPLATE TEST ===")
    print(ecg_result)
    print("\n" + "="*50 + "\n")
    
    # Test CONSULT template
    consult_findings = {
        'reason_visit': 'Pijn op de borst bij inspanning',
        'current_complaints': 'Patiënt meldt drukkende pijn retrosternaal bij matige inspanning',
        'assessment': 'Verdenking op stabiele angina pectoris',
        'plan': 'Aanvullende diagnostiek met inspannings-ECG'
    }
    
    consult_result = templates.format_template('CONSULT', consult_findings)
    print("=== CONSULT TEMPLATE TEST ===")
    print(consult_result)


if __name__ == "__main__":
    test_enhanced_templates()

