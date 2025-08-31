"""
Multi-Agent Orchestrator
Coordinates multiple AI agents with iterative feedback for intelligent medical transcription
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json

# Import all agent systems
try:
    from .odd_words_detector import get_odd_words_detector
    from .belgian_drug_pronunciation import get_belgian_pronunciation_system
    from .contextual_drug_selector import get_contextual_drug_selector, DrugContext
    from .medical_knowledge_system import get_knowledge_system
    from .claude_medical_validator import ClaudeMedicalValidator
    AGENTS_AVAILABLE = True
except ImportError as e:
    AGENTS_AVAILABLE = False
    print(f"Warning: Some agents not available: {e}")

logger = logging.getLogger(__name__)

@dataclass
class AgentResult:
    """Result from an individual agent"""
    agent_name: str
    success: bool
    confidence: float
    output: Dict
    processing_time: float
    suggestions: List[str]
    warnings: List[str]

@dataclass
class IterationResult:
    """Result from one iteration of the multi-agent process"""
    iteration_number: int
    transcript_version: str
    agent_results: List[AgentResult]
    overall_confidence: float
    improvements_made: List[str]
    convergence_score: float

class MultiAgentOrchestrator:
    """Orchestrates multiple agents with iterative feedback"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.agents = {}
        self.max_iterations = 5
        self.convergence_threshold = 0.95
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize all available agents"""
        
        if not AGENTS_AVAILABLE:
            logger.warning("Not all agents available - running in limited mode")
            return
        
        try:
            # Initialize each agent
            self.agents = {
                'odd_words_detector': get_odd_words_detector(self.db_path),
                'pronunciation_system': get_belgian_pronunciation_system(self.db_path),
                'drug_selector': get_contextual_drug_selector(self.db_path),
                'knowledge_system': get_knowledge_system(),
                'claude_validator': ClaudeMedicalValidator()
            }
            
            logger.info(f"Initialized {len(self.agents)} agents")
            
        except Exception as e:
            logger.error(f"Error initializing agents: {e}")
            self.agents = {}
    
    def process_transcript_intelligently(self, 
                                       original_transcript: str, 
                                       patient_id: str = None,
                                       medical_context: str = "",
                                       department: str = "General") -> Dict:
        """Process transcript through multi-agent system with iterative feedback"""
        
        if not self.agents:
            logger.warning("No agents available - returning original transcript")
            return {
                'final_transcript': original_transcript,
                'iterations': [],
                'total_improvements': 0,
                'confidence': 0.5,
                'agent_feedback': "Limited processing - agents not available"
            }
        
        try:
            iterations = []
            current_transcript = original_transcript
            previous_confidence = 0.0
            
            logger.info(f"Starting multi-agent processing for transcript: {original_transcript[:100]}...")
            
            for iteration in range(self.max_iterations):
                logger.info(f"Starting iteration {iteration + 1}")
                
                # Run all agents on current transcript
                iteration_result = self._run_agent_iteration(
                    current_transcript, 
                    patient_id, 
                    medical_context, 
                    department,
                    iteration + 1
                )
                
                iterations.append(iteration_result)
                
                # Update transcript with improvements
                if iteration_result.improvements_made:
                    current_transcript = iteration_result.transcript_version
                    logger.info(f"Iteration {iteration + 1}: Made {len(iteration_result.improvements_made)} improvements")
                
                # Check for convergence
                confidence_improvement = iteration_result.overall_confidence - previous_confidence
                
                if (iteration_result.overall_confidence >= self.convergence_threshold or
                    confidence_improvement < 0.05):  # Minimal improvement
                    logger.info(f"Converged after {iteration + 1} iterations")
                    break
                
                previous_confidence = iteration_result.overall_confidence
            
            # Generate final summary
            total_improvements = sum(len(iter_result.improvements_made) for iter_result in iterations)
            final_confidence = iterations[-1].overall_confidence if iterations else 0.5
            
            # Create agent feedback summary
            agent_feedback = self._create_agent_feedback_summary(iterations)
            
            return {
                'final_transcript': current_transcript,
                'original_transcript': original_transcript,
                'iterations': len(iterations),
                'iteration_details': [
                    {
                        'iteration': ir.iteration_number,
                        'confidence': ir.overall_confidence,
                        'improvements': len(ir.improvements_made),
                        'agents_used': len(ir.agent_results)
                    } for ir in iterations
                ],
                'total_improvements': total_improvements,
                'final_confidence': final_confidence,
                'agent_feedback': agent_feedback,
                'processing_successful': True
            }
            
        except Exception as e:
            logger.error(f"Multi-agent processing error: {e}")
            return {
                'final_transcript': original_transcript,
                'iterations': 0,
                'total_improvements': 0,
                'confidence': 0.3,
                'agent_feedback': f"Processing error: {str(e)}",
                'processing_successful': False
            }
    
    def _run_agent_iteration(self, 
                           transcript: str, 
                           patient_id: str, 
                           medical_context: str, 
                           department: str,
                           iteration_number: int) -> IterationResult:
        """Run one iteration of all agents"""
        
        agent_results = []
        current_transcript = transcript
        improvements_made = []
        
        # 1. Odd Words Detection Agent
        if 'odd_words_detector' in self.agents:
            start_time = datetime.now()
            try:
                odd_result = self.agents['odd_words_detector'].process_transcript_for_odd_words(
                    current_transcript, medical_context
                )
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                if odd_result.get('corrections_made'):
                    current_transcript = odd_result['corrected_transcript']
                    improvements_made.extend([
                        f"Corrected '{corr['original']}' to '{corr['corrected']}'"
                        for corr in odd_result['corrections_made']
                    ])
                
                agent_results.append(AgentResult(
                    agent_name='Odd Words Detector',
                    success=True,
                    confidence=0.8 if odd_result.get('corrections_made') else 0.9,
                    output=odd_result,
                    processing_time=processing_time,
                    suggestions=[corr['corrected'] for corr in odd_result.get('corrections_made', [])],
                    warnings=[]
                ))
                
            except Exception as e:
                logger.error(f"Odd words detector error: {e}")
        
        # 2. Belgian Pronunciation Agent
        if 'pronunciation_system' in self.agents:
            start_time = datetime.now()
            try:
                pronunciation_result = self.agents['pronunciation_system'].enhance_drug_recognition(
                    current_transcript, medical_context
                )
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                if pronunciation_result.get('enhancement_applied'):
                    current_transcript = pronunciation_result['enhanced_transcript']
                    improvements_made.extend([
                        f"Drug pronunciation: '{corr['original']}' → '{corr['corrected']}'"
                        for corr in pronunciation_result.get('drug_corrections', [])
                    ])
                
                agent_results.append(AgentResult(
                    agent_name='Belgian Pronunciation',
                    success=True,
                    confidence=0.85 if pronunciation_result.get('enhancement_applied') else 0.9,
                    output=pronunciation_result,
                    processing_time=processing_time,
                    suggestions=[corr['corrected'] for corr in pronunciation_result.get('drug_corrections', [])],
                    warnings=[]
                ))
                
            except Exception as e:
                logger.error(f"Pronunciation system error: {e}")
        
        # 3. Knowledge System Enhancement
        if 'knowledge_system' in self.agents:
            start_time = datetime.now()
            try:
                knowledge_result = self.agents['knowledge_system'].enhance_transcription(
                    current_transcript, patient_id
                )
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                if knowledge_result.get('enhancement_applied'):
                    current_transcript = knowledge_result['enhanced_transcript']
                    improvements_made.extend([
                        f"Knowledge enhancement: {len(knowledge_result.get('drug_corrections', []))} drug corrections"
                    ])
                
                agent_results.append(AgentResult(
                    agent_name='Knowledge System',
                    success=True,
                    confidence=0.9 if knowledge_result.get('enhancement_applied') else 0.8,
                    output=knowledge_result,
                    processing_time=processing_time,
                    suggestions=[],
                    warnings=[]
                ))
                
            except Exception as e:
                logger.error(f"Knowledge system error: {e}")
        
        # 4. Claude Medical Validator (final validation)
        if 'claude_validator' in self.agents:
            start_time = datetime.now()
            try:
                claude_result = self.agents['claude_validator'].validate_medical_content(
                    current_transcript, 
                    context={
                        'patient_id': patient_id,
                        'department': department,
                        'iteration': iteration_number
                    }
                )
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                warnings = []
                if not claude_result.get('is_valid', True):
                    warnings.extend(claude_result.get('issues', []))
                
                agent_results.append(AgentResult(
                    agent_name='Claude Medical Validator',
                    success=claude_result.get('is_valid', True),
                    confidence=claude_result.get('confidence', 0.8),
                    output=claude_result,
                    processing_time=processing_time,
                    suggestions=claude_result.get('suggestions', []),
                    warnings=warnings
                ))
                
            except Exception as e:
                logger.error(f"Claude validator error: {e}")
        
        # Calculate overall confidence and convergence
        overall_confidence = self._calculate_overall_confidence(agent_results)
        convergence_score = self._calculate_convergence_score(current_transcript, transcript)
        
        return IterationResult(
            iteration_number=iteration_number,
            transcript_version=current_transcript,
            agent_results=agent_results,
            overall_confidence=overall_confidence,
            improvements_made=improvements_made,
            convergence_score=convergence_score
        )
    
    def _calculate_overall_confidence(self, agent_results: List[AgentResult]) -> float:
        """Calculate overall confidence from all agent results"""
        
        if not agent_results:
            return 0.5
        
        # Weighted average of agent confidences
        weights = {
            'Odd Words Detector': 0.2,
            'Belgian Pronunciation': 0.25,
            'Knowledge System': 0.25,
            'Claude Medical Validator': 0.3
        }
        
        total_confidence = 0.0
        total_weight = 0.0
        
        for result in agent_results:
            weight = weights.get(result.agent_name, 0.1)
            total_confidence += result.confidence * weight
            total_weight += weight
        
        return total_confidence / total_weight if total_weight > 0 else 0.5
    
    def _calculate_convergence_score(self, current_transcript: str, original_transcript: str) -> float:
        """Calculate how much the transcript has converged"""
        
        if current_transcript == original_transcript:
            return 1.0
        
        # Calculate similarity
        words_original = set(original_transcript.lower().split())
        words_current = set(current_transcript.lower().split())
        
        if not words_original:
            return 1.0
        
        common_words = words_original & words_current
        return len(common_words) / len(words_original)
    
    def _create_agent_feedback_summary(self, iterations: List[IterationResult]) -> str:
        """Create a summary of agent feedback"""
        
        if not iterations:
            return "No agent processing performed"
        
        total_improvements = sum(len(iter_result.improvements_made) for iter_result in iterations)
        final_confidence = iterations[-1].overall_confidence
        
        feedback_parts = [
            f"🤖 Multi-Agent Processing: {len(iterations)} iterations",
            f"📊 Final Confidence: {final_confidence:.1%}",
            f"🔧 Total Improvements: {total_improvements}"
        ]
        
        # Agent-specific feedback
        agent_stats = {}
        for iteration in iterations:
            for agent_result in iteration.agent_results:
                agent_name = agent_result.agent_name
                if agent_name not in agent_stats:
                    agent_stats[agent_name] = {
                        'runs': 0,
                        'suggestions': 0,
                        'warnings': 0,
                        'avg_confidence': 0.0
                    }
                
                agent_stats[agent_name]['runs'] += 1
                agent_stats[agent_name]['suggestions'] += len(agent_result.suggestions)
                agent_stats[agent_name]['warnings'] += len(agent_result.warnings)
                agent_stats[agent_name]['avg_confidence'] += agent_result.confidence
        
        # Calculate averages
        for agent_name, stats in agent_stats.items():
            if stats['runs'] > 0:
                stats['avg_confidence'] /= stats['runs']
        
        # Add agent summaries
        for agent_name, stats in agent_stats.items():
            if stats['suggestions'] > 0 or stats['warnings'] > 0:
                feedback_parts.append(
                    f"• {agent_name}: {stats['suggestions']} suggestions, {stats['warnings']} warnings"
                )
        
        return " | ".join(feedback_parts)
    
    def get_processing_insights(self, processing_result: Dict) -> Dict:
        """Get insights about the processing for debugging/monitoring"""
        
        if not processing_result.get('processing_successful'):
            return {'error': 'Processing failed'}
        
        iterations = processing_result.get('iteration_details', [])
        
        insights = {
            'convergence_analysis': {
                'iterations_needed': len(iterations),
                'final_confidence': processing_result.get('final_confidence', 0),
                'improvement_trend': [iter_data['confidence'] for iter_data in iterations]
            },
            'agent_performance': {},
            'improvement_types': [],
            'processing_efficiency': {
                'total_improvements': processing_result.get('total_improvements', 0),
                'improvements_per_iteration': processing_result.get('total_improvements', 0) / max(len(iterations), 1)
            }
        }
        
        return insights
    
    def validate_final_output(self, transcript: str, context: Dict) -> Dict:
        """Final validation of the processed transcript"""
        
        validation_result = {
            'is_valid': True,
            'confidence': 0.8,
            'issues': [],
            'suggestions': []
        }
        
        try:
            # Check for remaining odd words
            if 'odd_words_detector' in self.agents:
                odd_check = self.agents['odd_words_detector'].detect_odd_words(transcript)
                if odd_check:
                    validation_result['issues'].append(f"Still contains {len(odd_check)} potentially odd words")
                    validation_result['confidence'] *= 0.9
            
            # Check medical coherence
            medical_terms = re.findall(r'\b\w+(?:ol|pril|sartan|statin|dipine|ide)\b', transcript.lower())
            if medical_terms:
                validation_result['suggestions'].append(f"Identified {len(medical_terms)} potential drug names")
            
            # Check for incomplete sentences
            sentences = transcript.split('.')
            incomplete_sentences = [s.strip() for s in sentences if s.strip() and len(s.strip().split()) < 3]
            if incomplete_sentences:
                validation_result['issues'].append(f"{len(incomplete_sentences)} potentially incomplete sentences")
                validation_result['confidence'] *= 0.95
            
            # Overall validation
            if validation_result['issues']:
                validation_result['is_valid'] = len(validation_result['issues']) <= 2  # Allow minor issues
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Final validation error: {e}")
            return {
                'is_valid': False,
                'confidence': 0.3,
                'issues': [f"Validation error: {str(e)}"],
                'suggestions': []
            }
    
    def get_agent_status(self) -> Dict:
        """Get status of all agents"""
        
        status = {
            'agents_available': len(self.agents),
            'agents_initialized': AGENTS_AVAILABLE,
            'agent_details': {}
        }
        
        for agent_name, agent in self.agents.items():
            try:
                # Try to get agent-specific status
                if hasattr(agent, 'get_stats'):
                    agent_stats = agent.get_stats()
                elif hasattr(agent, 'get_detection_stats'):
                    agent_stats = agent.get_detection_stats()
                elif hasattr(agent, 'get_pronunciation_stats'):
                    agent_stats = agent.get_pronunciation_stats()
                else:
                    agent_stats = {'status': 'active'}
                
                status['agent_details'][agent_name] = {
                    'status': 'active',
                    'stats': agent_stats
                }
                
            except Exception as e:
                status['agent_details'][agent_name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return status
    
    def process_with_feedback_loop(self, 
                                 transcript: str, 
                                 patient_context: DrugContext,
                                 target_confidence: float = 0.9) -> Dict:
        """Process with explicit feedback loop between agents"""
        
        feedback_loop_result = {
            'transcript': transcript,
            'confidence': 0.5,
            'feedback_rounds': 0,
            'agent_communications': []
        }
        
        try:
            current_transcript = transcript
            
            for round_num in range(3):  # Max 3 feedback rounds
                round_communications = []
                
                # Agent 1: Detect odd words
                if 'odd_words_detector' in self.agents:
                    odd_result = self.agents['odd_words_detector'].process_transcript_for_odd_words(current_transcript)
                    
                    if odd_result.get('corrections_made'):
                        round_communications.append({
                            'from_agent': 'Odd Words Detector',
                            'to_agent': 'Pronunciation System',
                            'message': f"Found {len(odd_result['corrections_made'])} odd words, please verify pronunciations",
                            'data': odd_result['corrections_made']
                        })
                        current_transcript = odd_result['corrected_transcript']
                
                # Agent 2: Verify pronunciations
                if 'pronunciation_system' in self.agents and round_communications:
                    pronunciation_result = self.agents['pronunciation_system'].enhance_drug_recognition(current_transcript)
                    
                    if pronunciation_result.get('enhancement_applied'):
                        round_communications.append({
                            'from_agent': 'Pronunciation System',
                            'to_agent': 'Drug Selector',
                            'message': f"Enhanced {len(pronunciation_result['drug_corrections'])} drug pronunciations",
                            'data': pronunciation_result['drug_corrections']
                        })
                        current_transcript = pronunciation_result['enhanced_transcript']
                
                # Agent 3: Contextual validation
                if 'drug_selector' in self.agents and round_communications:
                    # Extract potential drugs from communications
                    potential_drugs = []
                    for comm in round_communications:
                        if 'data' in comm:
                            for item in comm['data']:
                                if 'corrected' in item:
                                    potential_drugs.append(item['corrected'])
                    
                    if potential_drugs:
                        recommendations = self.agents['drug_selector'].select_optimal_drug(
                            patient_context.medical_condition,
                            patient_context,
                            potential_drugs
                        )
                        
                        round_communications.append({
                            'from_agent': 'Drug Selector',
                            'to_agent': 'Claude Validator',
                            'message': f"Validated {len(recommendations)} drug recommendations",
                            'data': [rec.generic_name for rec in recommendations]
                        })
                
                feedback_loop_result['agent_communications'].append({
                    'round': round_num + 1,
                    'communications': round_communications
                })
                
                # Check if we should continue
                if not round_communications:
                    break
            
            feedback_loop_result.update({
                'transcript': current_transcript,
                'confidence': 0.9 if feedback_loop_result['agent_communications'] else 0.7,
                'feedback_rounds': len(feedback_loop_result['agent_communications'])
            })
            
            return feedback_loop_result
            
        except Exception as e:
            logger.error(f"Feedback loop error: {e}")
            feedback_loop_result['error'] = str(e)
            return feedback_loop_result

def get_multi_agent_orchestrator(db_path: str) -> MultiAgentOrchestrator:
    """Get or create the multi-agent orchestrator"""
    return MultiAgentOrchestrator(db_path)

