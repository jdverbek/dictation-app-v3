"""
Contextual Drug Selection System
Intelligently selects the correct drug based on medical context, patient history, and clinical indicators
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class DrugContext:
    """Context information for drug selection"""
    medical_condition: str
    department: str
    patient_age_group: str  # pediatric, adult, geriatric
    contraindications: List[str]
    current_medications: List[str]
    allergies: List[str]
    severity: str  # mild, moderate, severe
    urgency: str   # routine, urgent, emergency

@dataclass
class DrugRecommendation:
    """Drug recommendation with reasoning"""
    generic_name: str
    brand_names: List[str]
    confidence: float
    reasoning: str
    contraindication_warnings: List[str]
    interaction_warnings: List[str]
    dosage_suggestion: str
    monitoring_requirements: List[str]

class ContextualDrugSelector:
    """Intelligent drug selection based on medical context"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.clinical_guidelines = {}
        self.drug_interactions = {}
        self.contraindication_rules = {}
        self._initialize_clinical_knowledge()
    
    def _initialize_clinical_knowledge(self):
        """Initialize clinical decision-making knowledge"""
        
        # Belgian clinical guidelines for drug selection
        self.clinical_guidelines = {
            'hypertensie': {
                'first_line': {
                    'adult': ['amlodipine', 'enalapril', 'losartan', 'hydrochlorothiazide'],
                    'elderly': ['amlodipine', 'enalapril', 'losartan'],  # Avoid thiazides in elderly
                    'diabetes': ['enalapril', 'losartan', 'amlodipine'],  # ACE/ARB preferred
                    'heart_failure': ['enalapril', 'bisoprolol', 'furosemide'],
                    'kidney_disease': ['amlodipine', 'losartan']  # Avoid ACE if severe
                },
                'second_line': ['bisoprolol', 'metoprolol', 'spironolactone'],
                'avoid_combinations': [
                    ['enalapril', 'losartan'],  # Don't combine ACE + ARB
                    ['spironolactone', 'enalapril']  # Monitor potassium
                ]
            },
            
            'hartfalen': {
                'first_line': {
                    'acute': ['furosemide', 'enalapril'],
                    'chronic': ['bisoprolol', 'enalapril', 'spironolactone'],
                    'severe': ['carvedilol', 'furosemide', 'spironolactone']
                },
                'contraindications': ['nifedipine', 'verapamil'],  # Negative inotropes
                'monitoring': ['potassium', 'creatinine', 'blood_pressure']
            },
            
            'diabetes': {
                'first_line': {
                    'type2_initial': ['metformin'],
                    'type2_add_on': ['gliclazide', 'insulin'],
                    'type1': ['insulin']
                },
                'cardiovascular_protection': ['enalapril', 'atorvastatin', 'acetylsalicylic acid'],
                'avoid': ['thiazides_high_dose', 'beta_blockers_non_selective']
            },
            
            'angina_pectoris': {
                'first_line': ['bisoprolol', 'metoprolol', 'amlodipine'],
                'second_line': ['isosorbide', 'nitroglycerin'],
                'long_term': ['acetylsalicylic acid', 'atorvastatin']
            },
            
            'aritmie': {
                'atrial_fibrillation': {
                    'rate_control': ['metoprolol', 'bisoprolol'],
                    'rhythm_control': ['amiodarone', 'flecainide'],
                    'anticoagulation': ['warfarin', 'rivaroxaban', 'apixaban']
                },
                'ventricular': ['amiodarone', 'lidocaine'],
                'avoid': ['sotalol']  # Pro-arrhythmic
            },
            
            'infectie': {
                'respiratory': ['amoxicillin', 'azithromycin'],
                'urinary': ['nitrofurantoin', 'ciprofloxacin'],
                'skin': ['flucloxacillin', 'clindamycin'],
                'severe': ['amoxicillin_clavulanate', 'ceftriaxone']
            },
            
            'pijn': {
                'mild': ['paracetamol'],
                'moderate': ['ibuprofen', 'diclofenac'],
                'severe': ['tramadol', 'morphine'],
                'chronic': ['gabapentin', 'pregabalin'],
                'neuropathic': ['gabapentin', 'amitriptyline']
            }
        }
        
        # Drug interaction database
        self.drug_interactions = {
            'warfarin': {
                'major': ['aspirin', 'clopidogrel', 'amiodarone'],
                'moderate': ['atorvastatin', 'omeprazole'],
                'monitoring': 'INR'
            },
            'enalapril': {
                'major': ['spironolactone', 'potassium'],
                'moderate': ['ibuprofen', 'diclofenac'],
                'monitoring': 'potassium, creatinine'
            },
            'metformin': {
                'major': ['contrast_agents'],
                'moderate': ['furosemide'],
                'monitoring': 'creatinine, lactate'
            },
            'digoxin': {
                'major': ['amiodarone', 'verapamil', 'furosemide'],
                'monitoring': 'digoxin_levels, potassium'
            }
        }
        
        # Contraindication rules
        self.contraindication_rules = {
            'asthma': ['propranolol', 'atenolol', 'metoprolol'],  # Non-selective beta-blockers
            'copd': ['propranolol'],  # Non-selective beta-blockers
            'heart_block': ['bisoprolol', 'metoprolol', 'verapamil'],
            'kidney_disease': ['enalapril', 'lisinopril', 'metformin'],
            'liver_disease': ['paracetamol', 'atorvastatin'],
            'pregnancy': ['enalapril', 'losartan', 'warfarin', 'atorvastatin'],
            'elderly': ['long_acting_benzodiazepines', 'tricyclic_antidepressants']
        }
    
    def select_optimal_drug(self, 
                           condition: str, 
                           patient_context: DrugContext,
                           spoken_drug_candidates: List[str]) -> List[DrugRecommendation]:
        """Select optimal drug based on condition and patient context"""
        
        try:
            recommendations = []
            condition_lower = condition.lower()
            
            # Get guideline-based recommendations
            guideline_drugs = self._get_guideline_drugs(condition_lower, patient_context)
            
            # If specific drugs were mentioned, validate them
            if spoken_drug_candidates:
                for candidate in spoken_drug_candidates:
                    recommendation = self._evaluate_drug_candidate(
                        candidate, condition_lower, patient_context
                    )
                    if recommendation:
                        recommendations.append(recommendation)
            
            # Add guideline-based recommendations
            for drug in guideline_drugs:
                if not any(rec.generic_name == drug for rec in recommendations):
                    recommendation = self._create_guideline_recommendation(
                        drug, condition_lower, patient_context
                    )
                    recommendations.append(recommendation)
            
            # Sort by confidence and clinical appropriateness
            recommendations.sort(key=lambda x: x.confidence, reverse=True)
            
            return recommendations[:5]  # Return top 5 recommendations
            
        except Exception as e:
            logger.error(f"Drug selection error: {e}")
            return []
    
    def _get_guideline_drugs(self, condition: str, context: DrugContext) -> List[str]:
        """Get drugs recommended by clinical guidelines"""
        drugs = []
        
        if condition in self.clinical_guidelines:
            guidelines = self.clinical_guidelines[condition]
            
            # Get first-line drugs based on patient characteristics
            if 'first_line' in guidelines:
                first_line = guidelines['first_line']
                
                # Age-based selection
                if context.patient_age_group == 'elderly' and 'elderly' in first_line:
                    drugs.extend(first_line['elderly'])
                elif context.patient_age_group == 'adult' and 'adult' in first_line:
                    drugs.extend(first_line['adult'])
                
                # Comorbidity-based selection
                for comorbidity in ['diabetes', 'heart_failure', 'kidney_disease']:
                    if comorbidity in context.medical_condition.lower() and comorbidity in first_line:
                        drugs.extend(first_line[comorbidity])
                
                # Severity-based selection
                if context.severity in first_line:
                    drugs.extend(first_line[context.severity])
            
            # Add second-line if needed
            if context.severity == 'severe' and 'second_line' in guidelines:
                drugs.extend(guidelines['second_line'])
        
        return list(set(drugs))  # Remove duplicates
    
    def _evaluate_drug_candidate(self, drug_name: str, condition: str, context: DrugContext) -> Optional[DrugRecommendation]:
        """Evaluate if a mentioned drug is appropriate for the condition"""
        
        # Check contraindications
        contraindication_warnings = []
        for contraindication in context.contraindications:
            if contraindication.lower() in self.contraindication_rules:
                if drug_name in self.contraindication_rules[contraindication.lower()]:
                    contraindication_warnings.append(
                        f"Contraindicated in {contraindication}"
                    )
        
        # Check drug interactions
        interaction_warnings = []
        if drug_name in self.drug_interactions:
            interactions = self.drug_interactions[drug_name]
            for current_med in context.current_medications:
                if current_med.lower() in [med.lower() for med in interactions.get('major', [])]:
                    interaction_warnings.append(
                        f"Major interaction with {current_med}"
                    )
        
        # Calculate confidence
        confidence = self._calculate_clinical_confidence(drug_name, condition, context)
        
        # Reduce confidence for contraindications
        if contraindication_warnings:
            confidence *= 0.3  # Significant reduction for contraindications
        elif interaction_warnings:
            confidence *= 0.7  # Moderate reduction for interactions
        
        # Get dosage suggestion
        dosage = self._get_dosage_suggestion(drug_name, context)
        
        # Get monitoring requirements
        monitoring = self._get_monitoring_requirements(drug_name, context)
        
        # Create reasoning
        reasoning = self._create_reasoning(drug_name, condition, context, confidence)
        
        return DrugRecommendation(
            generic_name=drug_name,
            brand_names=self._get_brand_names(drug_name),
            confidence=confidence,
            reasoning=reasoning,
            contraindication_warnings=contraindication_warnings,
            interaction_warnings=interaction_warnings,
            dosage_suggestion=dosage,
            monitoring_requirements=monitoring
        )
    
    def _calculate_clinical_confidence(self, drug_name: str, condition: str, context: DrugContext) -> float:
        """Calculate clinical confidence for drug selection"""
        base_confidence = 0.5
        
        # Check if drug is in guidelines for this condition
        if condition in self.clinical_guidelines:
            guidelines = self.clinical_guidelines[condition]
            
            # First-line drug
            first_line_drugs = []
            if 'first_line' in guidelines:
                for key, drugs in guidelines['first_line'].items():
                    if isinstance(drugs, list):
                        first_line_drugs.extend(drugs)
            
            if drug_name in first_line_drugs:
                base_confidence = 0.9
            elif 'second_line' in guidelines and drug_name in guidelines['second_line']:
                base_confidence = 0.7
        
        # Age appropriateness
        if context.patient_age_group == 'elderly':
            elderly_appropriate = ['amlodipine', 'enalapril', 'losartan', 'bisoprolol']
            if drug_name in elderly_appropriate:
                base_confidence += 0.1
        
        # Department appropriateness
        dept_drugs = {
            'cardiologie': ['bisoprolol', 'metoprolol', 'atorvastatin', 'clopidogrel'],
            'interne': ['metformin', 'enalapril', 'furosemide'],
            'pneumologie': ['salbutamol', 'budesonide']
        }
        
        if context.department.lower() in dept_drugs:
            if drug_name in dept_drugs[context.department.lower()]:
                base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def _create_guideline_recommendation(self, drug_name: str, condition: str, context: DrugContext) -> DrugRecommendation:
        """Create recommendation based on clinical guidelines"""
        
        confidence = self._calculate_clinical_confidence(drug_name, condition, context)
        reasoning = f"Recommended by Belgian clinical guidelines for {condition}"
        
        # Check for contraindications
        contraindications = []
        interactions = []
        
        for contraindication in context.contraindications:
            if contraindication.lower() in self.contraindication_rules:
                if drug_name in self.contraindication_rules[contraindication.lower()]:
                    contraindications.append(f"Contraindicated in {contraindication}")
                    confidence *= 0.3
        
        dosage = self._get_dosage_suggestion(drug_name, context)
        monitoring = self._get_monitoring_requirements(drug_name, context)
        
        return DrugRecommendation(
            generic_name=drug_name,
            brand_names=self._get_brand_names(drug_name),
            confidence=confidence,
            reasoning=reasoning,
            contraindication_warnings=contraindications,
            interaction_warnings=interactions,
            dosage_suggestion=dosage,
            monitoring_requirements=monitoring
        )
    
    def _get_dosage_suggestion(self, drug_name: str, context: DrugContext) -> str:
        """Get dosage suggestion based on drug and patient context"""
        
        # Standard Belgian dosages
        standard_dosages = {
            'bisoprolol': {
                'hypertensie': '5-10 mg 1x/dag',
                'hartfalen': '1.25 mg 1x/dag, optitreren tot 10 mg',
                'elderly': '2.5-5 mg 1x/dag'
            },
            'enalapril': {
                'hypertensie': '5-10 mg 2x/dag',
                'hartfalen': '2.5 mg 2x/dag, optitreren tot 20 mg 2x/dag',
                'elderly': '2.5 mg 1x/dag'
            },
            'metformin': {
                'diabetes': '500 mg 2x/dag bij maaltijd, optitreren tot 1000 mg 2x/dag',
                'elderly': '500 mg 1x/dag'
            },
            'furosemide': {
                'hartfalen': '20-40 mg 1x/dag ochtend',
                'acute': '40-80 mg IV',
                'elderly': '20 mg 1x/dag'
            },
            'atorvastatin': {
                'cholesterol': '20 mg 1x/dag avond',
                'high_risk': '40-80 mg 1x/dag avond'
            }
        }
        
        if drug_name in standard_dosages:
            dosage_info = standard_dosages[drug_name]
            
            # Age-based adjustment
            if context.patient_age_group == 'elderly' and 'elderly' in dosage_info:
                return dosage_info['elderly']
            
            # Condition-based dosage
            for condition_key in dosage_info:
                if condition_key in context.medical_condition.lower():
                    return dosage_info[condition_key]
            
            # Return first available dosage
            return list(dosage_info.values())[0]
        
        return "Zie BCFI voor dosering"
    
    def _get_monitoring_requirements(self, drug_name: str, context: DrugContext) -> List[str]:
        """Get monitoring requirements for the drug"""
        
        monitoring_requirements = {
            'enalapril': ['Kalium', 'Creatinine', 'Bloeddruk'],
            'losartan': ['Kalium', 'Creatinine', 'Bloeddruk'],
            'furosemide': ['Kalium', 'Natrium', 'Creatinine'],
            'spironolactone': ['Kalium', 'Creatinine'],
            'warfarin': ['INR', 'Bloedingsrisico'],
            'metformin': ['Creatinine', 'Lactaat', 'HbA1c'],
            'atorvastatin': ['Leverenzymen', 'CK', 'Cholesterol'],
            'digoxin': ['Digoxine spiegel', 'Kalium', 'Creatinine'],
            'amiodarone': ['Schildklierfunctie', 'Leverenzymen', 'Longfunctie']
        }
        
        return monitoring_requirements.get(drug_name, ['Klinische respons'])
    
    def _get_brand_names(self, drug_name: str) -> List[str]:
        """Get common Belgian brand names for the drug"""
        
        belgian_brands = {
            'bisoprolol': ['Bisoprolol EG', 'Bisoprolol Sandoz', 'Bisoprolol Teva', 'Bisocard'],
            'enalapril': ['Enalapril EG', 'Renitec', 'Enalapril Sandoz'],
            'metformin': ['Metformin EG', 'Glucophage', 'Metformin Sandoz'],
            'furosemide': ['Furosemide EG', 'Lasix', 'Furosemide Sandoz'],
            'atorvastatin': ['Atorvastatin EG', 'Lipitor', 'Atorvastatin Sandoz'],
            'amlodipine': ['Amlodipine EG', 'Norvasc', 'Amlodipine Sandoz'],
            'losartan': ['Losartan EG', 'Cozaar', 'Losartan Sandoz'],
            'paracetamol': ['Paracetamol EG', 'Dafalgan', 'Panadol'],
            'ibuprofen': ['Ibuprofen EG', 'Brufen', 'Nurofen']
        }
        
        return belgian_brands.get(drug_name, [f"{drug_name} EG", f"{drug_name} Sandoz"])
    
    def _create_reasoning(self, drug_name: str, condition: str, context: DrugContext, confidence: float) -> str:
        """Create clinical reasoning for drug selection"""
        
        reasons = []
        
        # Guideline-based reasoning
        if condition in self.clinical_guidelines:
            guidelines = self.clinical_guidelines[condition]
            
            first_line_drugs = []
            if 'first_line' in guidelines:
                for drugs in guidelines['first_line'].values():
                    if isinstance(drugs, list):
                        first_line_drugs.extend(drugs)
            
            if drug_name in first_line_drugs:
                reasons.append("Eerste keuze volgens Belgische richtlijnen")
            elif 'second_line' in guidelines and drug_name in guidelines['second_line']:
                reasons.append("Tweede keuze medicatie")
        
        # Patient-specific reasoning
        if context.patient_age_group == 'elderly':
            elderly_safe = ['amlodipine', 'enalapril', 'losartan']
            if drug_name in elderly_safe:
                reasons.append("Geschikt voor ouderen")
        
        # Department-specific reasoning
        if context.department.lower() == 'cardiologie':
            cardio_drugs = ['bisoprolol', 'atorvastatin', 'clopidogrel']
            if drug_name in cardio_drugs:
                reasons.append("Standaard in cardiologie")
        
        # Severity-based reasoning
        if context.severity == 'severe':
            reasons.append("Geschikt voor ernstige gevallen")
        
        if not reasons:
            reasons.append("Klinisch geïndiceerd voor deze aandoening")
        
        return "; ".join(reasons)
    
    def analyze_prescription_context(self, transcript: str) -> DrugContext:
        """Analyze transcript to extract prescription context"""
        
        transcript_lower = transcript.lower()
        
        # Extract medical conditions
        conditions = []
        condition_patterns = {
            'hypertensie': r'\b(hypertensie|hoge bloeddruk|hypertension)\b',
            'hartfalen': r'\b(hartfalen|heart failure|decompensatie)\b',
            'diabetes': r'\b(diabetes|suikerziekte|dm type)\b',
            'angina': r'\b(angina|pijn op de borst|chest pain)\b',
            'aritmie': r'\b(aritmie|fibrillatie|tachycardie|bradycardie)\b',
            'infectie': r'\b(infectie|koorts|antibiotica)\b',
            'pijn': r'\b(pijn|pain|analgesie)\b'
        }
        
        for condition, pattern in condition_patterns.items():
            if re.search(pattern, transcript_lower):
                conditions.append(condition)
        
        # Extract age indicators
        age_group = 'adult'  # default
        if re.search(r'\b(ouder|elderly|geriatrisch|80|90)\b', transcript_lower):
            age_group = 'elderly'
        elif re.search(r'\b(kind|pediatr|jong)\b', transcript_lower):
            age_group = 'pediatric'
        
        # Extract severity
        severity = 'moderate'  # default
        if re.search(r'\b(ernstig|severe|acuut|emergency)\b', transcript_lower):
            severity = 'severe'
        elif re.search(r'\b(mild|licht|stabiel)\b', transcript_lower):
            severity = 'mild'
        
        # Extract urgency
        urgency = 'routine'  # default
        if re.search(r'\b(urgent|spoed|emergency|acuut)\b', transcript_lower):
            urgency = 'urgent'
        
        # Extract contraindications
        contraindications = []
        contraindication_patterns = {
            'asthma': r'\b(astma|asthma|bronchospasme)\b',
            'copd': r'\b(copd|emphyseem|chronische bronchitis)\b',
            'kidney_disease': r'\b(nierinsufficiëntie|kidney|creatinine)\b',
            'liver_disease': r'\b(leverinsufficiëntie|liver|hepatisch)\b',
            'pregnancy': r'\b(zwanger|pregnancy|gravida)\b'
        }
        
        for contraindication, pattern in contraindication_patterns.items():
            if re.search(pattern, transcript_lower):
                contraindications.append(contraindication)
        
        # Extract current medications
        current_meds = []
        # This would need more sophisticated NLP to extract current medications
        # For now, look for common patterns
        med_patterns = [
            r'neemt al (\w+)',
            r'gebruikt (\w+)',
            r'op (\w+)',
            r'krijgt (\w+)'
        ]
        
        for pattern in med_patterns:
            matches = re.findall(pattern, transcript_lower)
            current_meds.extend(matches)
        
        return DrugContext(
            medical_condition=', '.join(conditions) if conditions else 'onbekend',
            department='General',  # Would need to be passed from session
            patient_age_group=age_group,
            contraindications=contraindications,
            current_medications=current_meds,
            allergies=[],  # Would need to extract from transcript
            severity=severity,
            urgency=urgency
        )
    
    def get_drug_alternatives(self, drug_name: str, reason: str = "") -> List[Dict]:
        """Get alternative drugs for a given drug"""
        
        alternatives = {
            'bisoprolol': [
                {'name': 'metoprolol', 'reason': 'Andere cardioselectieve bètablokker'},
                {'name': 'atenolol', 'reason': 'Alternatieve bètablokker'},
                {'name': 'amlodipine', 'reason': 'Calciumantagonist als alternatief'}
            ],
            'enalapril': [
                {'name': 'lisinopril', 'reason': 'Andere ACE-remmer'},
                {'name': 'losartan', 'reason': 'ARB als alternatief'},
                {'name': 'amlodipine', 'reason': 'Calciumantagonist'}
            ],
            'metformin': [
                {'name': 'gliclazide', 'reason': 'Sulfonylureum als alternatief'},
                {'name': 'sitagliptin', 'reason': 'DPP-4 remmer'},
                {'name': 'insulin', 'reason': 'Bij onvoldoende controle'}
            ]
        }
        
        return alternatives.get(drug_name, [])

def get_contextual_drug_selector(db_path: str) -> ContextualDrugSelector:
    """Get or create the contextual drug selector"""
    return ContextualDrugSelector(db_path)

