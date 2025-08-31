"""
Main orchestrator that handles iterative verification behind the scenes
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid
import redis
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)

@dataclass
class ProcessingJob:
    job_id: str
    patient_id: str
    patient_dob: str
    audio_file_path: str
    status: str  # 'pending', 'processing', 'verifying', 'completed', 'failed'
    iterations: int = 0
    max_iterations: int = 5
    current_report: Optional[Dict] = None
    verification_feedback: Optional[List[Dict]] = None
    final_report: Optional[Dict] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    transcript: Optional[str] = None

class IntelligentOrchestrator:
    """
    Orchestrates the entire process with internal verification loops
    """
    
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.openai_client = OpenAI()
        self.verification_agents = self._initialize_verification_agents()
        
    def _initialize_verification_agents(self):
        """Initialize internal verification agents"""
        from .hallucination_detector import HallucinationDetector
        from .enhanced_medical_processor import EnhancedMedicalProcessor
        from .claude_medical_validator import ClaudeMedicalValidator
        
        return {
            'hallucination_detector': HallucinationDetector(),
            'medical_processor': EnhancedMedicalProcessor(),
            'claude_validator': ClaudeMedicalValidator(),
        }
    
    async def process_with_self_correction(self, job: ProcessingJob) -> Dict:
        """
        Main processing loop with automatic self-correction
        """
        try:
            logger.info(f"Starting processing for job {job.job_id}")
            
            # Update status
            self._update_job_status(job.job_id, 'processing')
            
            # Step 1: Initial transcription
            transcription = await self._transcribe_audio(job.audio_file_path)
            job.transcript = transcription
            self._current_transcription = transcription  # Store for Claude validator
            
            # Step 2: Generate initial report
            current_report = await self._generate_initial_report(
                transcription, 
                job.patient_id,
                job.patient_dob
            )
            
            # Step 3: Iterative verification and correction loop
            while job.iterations < job.max_iterations:
                job.iterations += 1
                logger.info(f"Starting iteration {job.iterations} for job {job.job_id}")
                
                # Run all verification checks
                verification_results = await self._run_verification_suite(
                    current_report, 
                    transcription
                )
                
                # Check if all verifications passed
                if self._all_verifications_passed(verification_results):
                    job.final_report = current_report
                    logger.info(f"All verifications passed for job {job.job_id}")
                    break
                
                # Generate feedback for correction
                feedback = self._compile_feedback(verification_results)
                job.verification_feedback = feedback
                
                # Self-correct based on feedback
                current_report = await self._self_correct_report(
                    current_report, 
                    feedback,
                    transcription
                )
                
                # Store iteration data
                self._store_iteration_data(job.job_id, job.iterations, feedback)
            
            # Final validation
            if not job.final_report:
                # Max iterations reached, use best version
                job.final_report = current_report
                logger.warning(f"Max iterations reached for job {job.job_id}")
            
            # Store final result
            job.completed_at = datetime.now()
            self._store_final_report(job)
            self._update_job_status(job.job_id, 'completed')
            
            return {
                'success': True,
                'job_id': job.job_id,
                'patient_id': job.patient_id,
                'patient_dob': job.patient_dob,
                'transcript': job.transcript,
                'report': job.final_report,
                'iterations': job.iterations,
                'confidence_score': self._calculate_confidence(job.final_report),
                'completed_at': job.completed_at.isoformat() if job.completed_at else None
            }
            
        except Exception as e:
            logger.error(f"Error processing job {job.job_id}: {str(e)}")
            self._update_job_status(job.job_id, 'failed', str(e))
            return {
                'success': False,
                'job_id': job.job_id,
                'error': str(e)
            }
    
    async def _transcribe_audio(self, audio_file_path: str) -> str:
        """Transcribe audio using OpenAI Whisper"""
        try:
            with open(audio_file_path, 'rb') as audio_file:
                transcript = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="nl"  # Dutch
                )
            return transcript.text
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            raise
    
    async def _generate_initial_report(self, transcription: str, patient_id: str, patient_dob: str) -> Dict:
        """Generate initial medical report from transcription"""
        from .enhanced_medical_processor import EnhancedMedicalProcessor
        
        processor = EnhancedMedicalProcessor()
        
        # Determine if this is history or examination
        report_type = self._determine_report_type(transcription)
        
        if report_type == "history":
            from .enhanced_history_analyzer import EnhancedHistoryAnalyzer
            analyzer = EnhancedHistoryAnalyzer()
            result = analyzer.analyze_conversation(transcription)
            
            return {
                'type': 'history',
                'patient_id': patient_id,
                'patient_dob': patient_dob,
                'content': result,
                'timestamp': datetime.now().isoformat()
            }
        else:
            from .clinical_examiner import ClinicalExaminer
            examiner = ClinicalExaminer()
            result = examiner.analyze_examination(transcription, report_type)
            
            return {
                'type': 'examination',
                'examination_type': report_type,
                'patient_id': patient_id,
                'patient_dob': patient_dob,
                'content': result,
                'timestamp': datetime.now().isoformat()
            }
    
    def _determine_report_type(self, transcription: str) -> str:
        """Determine if transcription is history or examination"""
        # Keywords that indicate examination types
        examination_keywords = {
            'ecg': ['ecg', 'elektrocardiogram', 'ritme', 'hartslag'],
            'echo': ['echo', 'echocardiogram', 'tte', 'tee'],
            'exercise': ['inspanningstest', 'fietstest', 'watt', 'belasting'],
            'holter': ['holter', '24-uurs', 'monitoring'],
            'device': ['pacemaker', 'icd', 'device', 'apparaat']
        }
        
        text_lower = transcription.lower()
        
        for exam_type, keywords in examination_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return exam_type
        
        # Default to history if no examination keywords found
        return "history"
    
    async def _run_verification_suite(self, report: Dict, transcription: str) -> Dict:
        """Run all verification checks in parallel"""
        tasks = []
        
        # Hallucination check
        tasks.append(self._check_hallucination(report, transcription))
        
        # Consistency check
        tasks.append(self._check_consistency(report))
        
        # Medical validation
        tasks.append(self._validate_medical_logic(report))
        
        # Completeness check
        tasks.append(self._check_completeness(report))
        
        # Terminology check
        tasks.append(self._check_terminology(report))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            'hallucination': results[0] if not isinstance(results[0], Exception) else {'passed': False, 'error': str(results[0])},
            'consistency': results[1] if not isinstance(results[1], Exception) else {'passed': False, 'error': str(results[1])},
            'medical_logic': results[2] if not isinstance(results[2], Exception) else {'passed': False, 'error': str(results[2])},
            'completeness': results[3] if not isinstance(results[3], Exception) else {'passed': False, 'error': str(results[3])},
            'terminology': results[4] if not isinstance(results[4], Exception) else {'passed': False, 'error': str(results[4])}
        }
    
    async def _check_hallucination(self, report: Dict, transcription: str) -> Dict:
        """Check for hallucinations using existing detector"""
        try:
            detector = self.verification_agents['hallucination_detector']
            is_hallucination, reason, patterns = detector.detect_hallucination(transcription)
            
            if is_hallucination:
                return {
                    'passed': False,
                    'issues': patterns,
                    'suggestions': [f"Remove hallucinated content: {reason}"]
                }
            else:
                return {
                    'passed': True,
                    'issues': [],
                    'suggestions': []
                }
        except Exception as e:
            logger.error(f"Hallucination check error: {str(e)}")
            return {'passed': False, 'error': str(e)}
    
    async def _check_consistency(self, report: Dict) -> Dict:
        """Check internal consistency of the report"""
        try:
            prompt = f"""
            Analyze this medical report for internal consistency. Check for:
            1. Contradictory statements
            2. Inconsistent measurements or values
            3. Logical inconsistencies in medical findings
            
            Report:
            {json.dumps(report, indent=2)}
            
            Return JSON with:
            - passed: boolean
            - issues: list of consistency issues found
            - suggestions: list of corrections
            """
            
            response = await self._call_gpt4(prompt, temperature=0)
            return json.loads(response)
        except Exception as e:
            logger.error(f"Consistency check error: {str(e)}")
            return {'passed': False, 'error': str(e)}
    
    async def _validate_medical_logic(self, report: Dict) -> Dict:
        """Validate medical logic using Claude Opus"""
        try:
            claude_validator = self.verification_agents['claude_validator']
            
            # Get the original transcription from the report context
            transcription = getattr(self, '_current_transcription', '')
            
            result = await claude_validator.validate_medical_logic(report, transcription)
            return result
        except Exception as e:
            logger.error(f"Claude medical validation error: {str(e)}")
            return {'passed': False, 'error': str(e)}
    
    async def _check_completeness(self, report: Dict) -> Dict:
        """Check if report is complete for its type"""
        try:
            report_type = report.get('type', 'unknown')
            
            prompt = f"""
            Check if this {report_type} report is complete. For this type of report, verify:
            1. All required sections are present
            2. No incomplete sentences or missing information
            3. Proper structure and formatting
            
            Report:
            {json.dumps(report, indent=2)}
            
            Return JSON with:
            - passed: boolean
            - issues: list of completeness issues
            - suggestions: list of improvements
            """
            
            response = await self._call_gpt4(prompt, temperature=0)
            return json.loads(response)
        except Exception as e:
            logger.error(f"Completeness check error: {str(e)}")
            return {'passed': False, 'error': str(e)}
    
    async def _check_terminology(self, report: Dict) -> Dict:
        """Check Dutch medical terminology"""
        try:
            prompt = f"""
            Check the Dutch medical terminology in this report. Verify:
            1. Correct Dutch medical terms are used
            2. Proper spelling of medical terminology
            3. Appropriate formality level for medical documentation
            4. Consistency in terminology usage
            
            Report:
            {json.dumps(report, indent=2)}
            
            Return JSON with:
            - passed: boolean
            - issues: list of terminology issues
            - suggestions: list of terminology corrections
            """
            
            response = await self._call_gpt4(prompt, temperature=0)
            return json.loads(response)
        except Exception as e:
            logger.error(f"Terminology check error: {str(e)}")
            return {'passed': False, 'error': str(e)}
    
    async def _self_correct_report(self, report: Dict, feedback: List[Dict], transcription: str) -> Dict:
        """Self-correct the report based on feedback"""
        try:
            prompt = f"""
            You are a medical report correction system. Fix the following issues in the report.
            
            Current report:
            {json.dumps(report, indent=2)}
            
            Issues to fix:
            {json.dumps(feedback, indent=2)}
            
            Original transcription for reference:
            {transcription}
            
            Rules:
            1. ONLY use information explicitly mentioned in the transcription
            2. Fix all identified issues
            3. Do not introduce new information
            4. Maintain proper Dutch medical terminology
            5. Return corrected report in same JSON structure
            6. Preserve the original structure and format
            """
            
            response = await self._call_gpt4(prompt, temperature=0)
            corrected_report = json.loads(response)
            
            # Ensure we maintain the original structure
            corrected_report['patient_id'] = report['patient_id']
            corrected_report['patient_dob'] = report['patient_dob']
            corrected_report['timestamp'] = datetime.now().isoformat()
            
            return corrected_report
        except Exception as e:
            logger.error(f"Self-correction error: {str(e)}")
            return report  # Return original if correction fails
    
    async def _call_gpt4(self, prompt: str, temperature: float = 0) -> str:
        """Call GPT-4 with the given prompt"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a medical AI assistant specialized in Dutch medical documentation. Always respond with valid JSON when requested."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"GPT-4 call error: {str(e)}")
            raise
    
    def _all_verifications_passed(self, results: Dict) -> bool:
        """Check if all verifications passed"""
        return all(
            result.get('passed', False) 
            for result in results.values()
            if 'error' not in result
        )
    
    def _compile_feedback(self, results: Dict) -> List[Dict]:
        """Compile feedback from all verification results"""
        feedback = []
        
        for check_name, result in results.items():
            if not result.get('passed', False) and 'error' not in result:
                feedback.append({
                    'check': check_name,
                    'issues': result.get('issues', []),
                    'suggestions': result.get('suggestions', [])
                })
        
        return feedback
    
    def _calculate_confidence(self, report: Dict) -> int:
        """Calculate confidence score for the report"""
        # Simple confidence calculation based on completeness and structure
        score = 100
        
        if not report:
            return 0
        
        # Check for required fields
        required_fields = ['patient_id', 'patient_dob', 'content']
        for field in required_fields:
            if field not in report or not report[field]:
                score -= 20
        
        # Check content completeness
        content = report.get('content', {})
        if isinstance(content, dict):
            if len(content) < 3:  # Expect at least 3 sections
                score -= 15
        
        return max(0, min(100, score))
    
    def _update_job_status(self, job_id: str, status: str, message: str = ""):
        """Update job status in Redis"""
        try:
            job_data = {
                'job_id': job_id,
                'status': status,
                'message': message,
                'updated_at': datetime.now().isoformat()
            }
            
            self.redis_client.setex(
                f"job:{job_id}",
                86400,  # Expire after 24 hours
                json.dumps(job_data)
            )
        except Exception as e:
            logger.error(f"Error updating job status: {str(e)}")
    
    def _store_iteration_data(self, job_id: str, iteration: int, feedback: List[Dict]):
        """Store iteration data for debugging"""
        try:
            iteration_data = {
                'job_id': job_id,
                'iteration': iteration,
                'feedback': feedback,
                'timestamp': datetime.now().isoformat()
            }
            
            self.redis_client.setex(
                f"iteration:{job_id}:{iteration}",
                86400,  # Expire after 24 hours
                json.dumps(iteration_data)
            )
        except Exception as e:
            logger.error(f"Error storing iteration data: {str(e)}")
    
    def _store_final_report(self, job: ProcessingJob):
        """Store final report in Redis"""
        try:
            result_data = {
                'job_id': job.job_id,
                'patient_id': job.patient_id,
                'patient_dob': job.patient_dob,
                'transcript': job.transcript,
                'report': job.final_report,
                'iterations': job.iterations,
                'confidence_score': self._calculate_confidence(job.final_report),
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'verification_feedback': job.verification_feedback
            }
            
            self.redis_client.setex(
                f"job_result:{job.job_id}",
                86400 * 7,  # Expire after 7 days
                json.dumps(result_data)
            )
        except Exception as e:
            logger.error(f"Error storing final report: {str(e)}")

