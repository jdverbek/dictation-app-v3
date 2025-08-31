"""
Core analysis modules for the Medical Dictation App
"""

# Import only existing modules
try:
    from .medical_knowledge_system import get_knowledge_system, MedicalKnowledgeSystem
    __all__ = ['get_knowledge_system', 'MedicalKnowledgeSystem']
except ImportError:
    __all__ = []

__version__ = '3.0.0'

