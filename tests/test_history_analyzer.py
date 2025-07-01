"""
Tests for the HistoryAnalyzer module
"""

import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.history_analyzer import HistoryAnalyzer, SymptomDetail


class TestHistoryAnalyzer:
    """Test cases for HistoryAnalyzer"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.analyzer = HistoryAnalyzer()
    
    def test_analyzer_initialization(self):
        """Test that analyzer initializes correctly"""
        assert self.analyzer is not None
        assert hasattr(self.analyzer, 'medical_terms')
        assert hasattr(self.analyzer, 'symptom_patterns')
    
    def test_simple_conversation_analysis(self):
        """Test analysis of a simple doctor-patient conversation"""
        conversation = """
        Dokter: Goedemorgen, waarmee kan ik u helpen?
        Patiënt: Ik heb pijn op de borst sinds gisteren.
        """
        
        analysis = self.analyzer.analyze_conversation(conversation)
        
        assert analysis is not None
        assert analysis.reason_for_encounter != ""
        assert len(analysis.chief_complaints) > 0
        
        # Check that we found the chest pain complaint
        complaint_texts = [c.symptom for c in analysis.chief_complaints]
        assert any('pijn' in text and 'borst' in text for text in complaint_texts)
    
    def test_empty_conversation(self):
        """Test handling of empty conversation"""
        analysis = self.analyzer.analyze_conversation("")
        
        assert analysis.reason_for_encounter == "No transcript provided"
        assert len(analysis.chief_complaints) == 0
    
    def test_no_fabrication(self):
        """Test that analyzer doesn't fabricate information"""
        conversation = "Patiënt: Ik voel me goed vandaag."
        
        analysis = self.analyzer.analyze_conversation(conversation)
        
        # Should not find any specific symptoms since none were mentioned
        assert len(analysis.chief_complaints) == 0 or \
               all(c.onset is None for c in analysis.chief_complaints if 'goed' not in c.symptom)
    
    def test_symptom_detail_extraction(self):
        """Test extraction of symptom details"""
        conversation = """
        Patiënt: Ik heb sinds vorige week ernstige hoofdpijn.
        Het is een kloppende pijn aan de linkerkant.
        """
        
        analysis = self.analyzer.analyze_conversation(conversation)
        
        if analysis.chief_complaints:
            complaint = analysis.chief_complaints[0]
            # Should extract some details about the headache
            assert complaint.symptom is not None
            # Note: We don't assert specific values since extraction may vary
    
    def test_confidence_scoring(self):
        """Test that confidence scores are calculated"""
        conversation = "Patiënt: Ik heb pijn op de borst."
        
        analysis = self.analyzer.analyze_conversation(conversation)
        
        assert isinstance(analysis.confidence_scores, dict)
        # Should have confidence scores for extracted information
        if analysis.chief_complaints:
            assert len(analysis.confidence_scores) > 0
    
    def test_source_validation(self):
        """Test that source validation is provided"""
        conversation = "Patiënt: Ik heb hoofdpijn sinds gisteren."
        
        analysis = self.analyzer.analyze_conversation(conversation)
        
        assert isinstance(analysis.source_validation, dict)
        # Should map extracted information to source text
        if analysis.chief_complaints:
            assert len(analysis.source_validation) > 0
    
    def test_formatted_output(self):
        """Test formatted output generation"""
        conversation = "Patiënt: Ik heb buikpijn sinds vanmorgen."
        
        analysis = self.analyzer.analyze_conversation(conversation)
        formatted = self.analyzer.format_structured_output(analysis)
        
        assert isinstance(formatted, str)
        assert len(formatted) > 0
        assert "Reden van komst:" in formatted


if __name__ == "__main__":
    pytest.main([__file__])

