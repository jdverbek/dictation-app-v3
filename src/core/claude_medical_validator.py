"""
Claude Opus-powered medical validator for enhanced verification
"""

import json
import logging
from typing import Dict, List
import requests

logger = logging.getLogger(__name__)

class ClaudeMedicalValidator:
    """
    Medical validator using Claude Opus for sophisticated medical reasoning
    """
    
    def __init__(self, api_key: str = "your_claude_api_key_here"):
        self.api_key = api_key
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.model = "claude-3-opus-20240229"
        
    async def validate_medical_logic(self, report: Dict, transcription: str) -> Dict:
        """
        Validate medical logic using Claude Opus's advanced reasoning
        """
        try:
            prompt = self._create_medical_validation_prompt(report, transcription)
            
            response = await self._call_claude(prompt)
            
            # Parse Claude's response
            validation_result = self._parse_validation_response(response)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Claude medical validation error: {str(e)}")
            return {
                'passed': False,
                'error': str(e),
                'issues': ['Validation service temporarily unavailable'],
                'suggestions': ['Please review manually']
            }
    
    def _create_medical_validation_prompt(self, report: Dict, transcription: str) -> str:
        """Create comprehensive medical validation prompt for Claude"""
        
        report_type = report.get('type', 'unknown')
        examination_type = report.get('examination_type', '')
        
        prompt = f"""
You are a senior medical consultant with expertise in Dutch medical practice and documentation. 
Please perform a comprehensive medical validation of this {report_type} report.

ORIGINAL TRANSCRIPTION:
{transcription}

GENERATED REPORT:
{json.dumps(report, indent=2)}

VALIDATION REQUIREMENTS:

1. **Medical Accuracy**: 
   - Check if all medical findings are physiologically possible
   - Verify that measurements fall within normal or pathological ranges
   - Ensure medical terminology is used correctly
   - Validate that conclusions match the findings

2. **Clinical Logic**:
   - Check for logical consistency between symptoms and findings
   - Verify that diagnostic reasoning is sound
   - Ensure recommendations are appropriate for the findings
   - Check for missing critical information

3. **Dutch Medical Standards**:
   - Verify compliance with Dutch medical documentation standards
   - Check proper use of Dutch medical terminology
   - Ensure appropriate formality and structure

4. **Safety Validation**:
   - Identify any potentially dangerous omissions
   - Check for critical findings that require immediate attention
   - Verify that urgent findings are properly highlighted

5. **Data Integrity**:
   - Ensure all data comes from the original transcription
   - Check for any fabricated or hallucinated information
   - Verify numerical accuracy and unit consistency

SPECIFIC CHECKS FOR {examination_type.upper() if examination_type else 'GENERAL'} EXAMINATION:
{self._get_specific_validation_criteria(examination_type)}

Please respond with a JSON object containing:
{{
    "passed": boolean,
    "confidence_score": number (0-100),
    "issues": [
        {{
            "category": "medical_accuracy|clinical_logic|dutch_standards|safety|data_integrity",
            "severity": "critical|high|medium|low",
            "description": "detailed description of the issue",
            "location": "where in the report this issue occurs"
        }}
    ],
    "suggestions": [
        {{
            "issue": "description of what needs to be fixed",
            "correction": "specific correction to apply",
            "rationale": "medical reasoning for this correction"
        }}
    ],
    "medical_assessment": {{
        "overall_quality": "excellent|good|acceptable|poor",
        "clinical_relevance": "high|medium|low",
        "completeness": "complete|mostly_complete|incomplete",
        "safety_concerns": "none|minor|moderate|major"
    }}
}}

Focus on being thorough but practical. Only flag genuine medical concerns, not minor stylistic issues.
"""
        
        return prompt
    
    def _get_specific_validation_criteria(self, examination_type: str) -> str:
        """Get specific validation criteria based on examination type"""
        
        criteria_map = {
            'ecg': """
- Verify heart rate is within physiological range (30-200 bpm)
- Check that rhythm descriptions match rate and morphology
- Validate interval measurements (PR, QRS, QT)
- Ensure axis calculations are correct
- Check for proper description of ST-segment and T-wave changes
""",
            'echo': """
- Validate chamber dimensions and wall thickness measurements
- Check ejection fraction calculations and classifications
- Verify valve function descriptions match severity grades
- Ensure Doppler measurements are physiologically possible
- Check for proper assessment of diastolic function
""",
            'exercise': """
- Verify maximum heart rate achieved vs age-predicted maximum
- Check blood pressure responses during exercise
- Validate workload progression and metabolic equivalents
- Ensure symptom descriptions match exercise capacity
- Check for proper risk stratification
""",
            'holter': """
- Verify total monitoring duration
- Check heart rate variability parameters
- Validate arrhythmia burden calculations
- Ensure symptom-rhythm correlation is documented
- Check for proper circadian rhythm analysis
""",
            'device': """
- Verify device settings are within programmable ranges
- Check battery status and longevity estimates
- Validate sensing and pacing thresholds
- Ensure arrhythmia detection settings are appropriate
- Check for proper lead impedance values
"""
        }
        
        return criteria_map.get(examination_type, "- Perform general medical validation appropriate for the examination type")
    
    async def _call_claude(self, prompt: str) -> str:
        """Call Claude Opus API"""
        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": self.model,
                "max_tokens": 4000,
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['content'][0]['text']
            else:
                logger.error(f"Claude API error: {response.status_code} - {response.text}")
                raise Exception(f"Claude API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            raise
    
    def _parse_validation_response(self, response: str) -> Dict:
        """Parse Claude's validation response"""
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                validation_result = json.loads(json_str)
                
                # Ensure required fields exist
                if 'passed' not in validation_result:
                    validation_result['passed'] = len(validation_result.get('issues', [])) == 0
                
                if 'confidence_score' not in validation_result:
                    validation_result['confidence_score'] = 85 if validation_result['passed'] else 60
                
                return validation_result
            else:
                # Fallback parsing
                return self._fallback_parse(response)
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            return self._fallback_parse(response)
    
    def _fallback_parse(self, response: str) -> Dict:
        """Fallback parsing when JSON extraction fails"""
        # Simple heuristic parsing
        issues = []
        suggestions = []
        
        # Look for common issue indicators
        if any(word in response.lower() for word in ['error', 'incorrect', 'invalid', 'concern']):
            issues.append({
                'category': 'general',
                'severity': 'medium',
                'description': 'Potential issues detected in validation',
                'location': 'general'
            })
        
        # Look for suggestions
        if any(word in response.lower() for word in ['suggest', 'recommend', 'should', 'consider']):
            suggestions.append({
                'issue': 'General improvements needed',
                'correction': 'Review Claude\'s detailed feedback',
                'rationale': 'Based on medical best practices'
            })
        
        return {
            'passed': len(issues) == 0,
            'confidence_score': 75,
            'issues': issues,
            'suggestions': suggestions,
            'medical_assessment': {
                'overall_quality': 'acceptable',
                'clinical_relevance': 'medium',
                'completeness': 'mostly_complete',
                'safety_concerns': 'minor' if issues else 'none'
            },
            'raw_response': response
        }

