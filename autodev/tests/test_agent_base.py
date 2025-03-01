"""
Tests for the base agent.
"""
import os
import tempfile
import shutil
import pytest
from unittest.mock import MagicMock, patch

# Add parent directory to path for importing
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import dspy
from autodev.agent.base import BaseAgent


class TestBaseAgent:
    """Test suite for the BaseAgent class."""
    
    @pytest.fixture
    def mock_lm(self):
        """Create a mock language model."""
        mock_lm = MagicMock()
        
        # Configure mock to return predictable responses
        def mock_generate(prompt, **kwargs):
            if "code" in prompt.lower():
                return "def hello(): return 'Hello, world!'"
            elif "explain" in prompt.lower():
                return "This function returns a greeting."
            elif "test" in prompt.lower():
                return "def test_hello(): assert hello() == 'Hello, world!'"
            elif "document" in prompt.lower():
                return "# Hello Function\nReturns a greeting."
            else:
                return "I'm a helpful assistant."
        
        mock_lm.generate.side_effect = mock_generate
        
        return mock_lm
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def agent(self, mock_lm):
        """Create a BaseAgent instance with mock LM for testing."""
        with patch('dspy.Predict') as mock_predict:
            # Configure the mock Predict to return predictable responses
            mock_predict.return_value.side_effect = lambda **kwargs: MagicMock(
                response="Mock response",
                code="def mock(): pass",
                explanation="Mock explanation",
                tests="def test_mock(): pass",
                documentation="Mock documentation"
            )
            
            agent = BaseAgent(lm=mock_lm, project_id="test_project")
            
            return agent
    
    def test_initialization(self, mock_lm):
        """Test that BaseAgent initializes correctly."""
        with patch('dspy.Predict') as mock_predict:
            agent = BaseAgent(lm=mock_lm, project_id="test_project")
            
            assert agent.lm is mock_lm
            assert agent.memory_manager is not None
            assert mock_predict.call_count == 5  # One for each module
    
    def test_set_language_model(self, agent, mock_lm):
        """Test setting the language model."""
        new_mock_lm = MagicMock()
        
        with patch('dspy.Predict') as mock_predict:
            agent.set_language_model(new_mock_lm)
            
            assert agent.lm is new_mock_lm
            assert mock_predict.call_count == 5  # One for each module
    
    def test_set_project(self, agent):
        """Test setting the project."""
        with patch.object(agent.memory_manager, 'set_project') as mock_set_project:
            agent.set_project("new_project")
            
            mock_set_project.assert_called_once_with("new_project")
    
    def test_answer_query(self, agent):
        """Test answering a query."""
        with patch.object(agent.memory_manager, 'add_context') as mock_add_context:
            response = agent.answer_query("How do I define a function?", context="Python code")
            
            assert response == "Mock response"
            assert mock_add_context.call_count == 3  # query, context, response
    
    def test_generate_code(self, agent):
        """Test generating code."""
        with patch.object(agent.memory_manager, 'add_context') as mock_add_context:
            result = agent.generate_code(
                task="Write a function to say hello",
                constraints="Must return a string",
                context="Python code"
            )
            
            assert result["code"] == "def mock(): pass"
            assert result["explanation"] == "Mock explanation"
            assert mock_add_context.call_count == 5  # task, constraints, context, code, explanation
    
    def test_explain_code(self, agent):
        """Test explaining code."""
        with patch.object(agent.memory_manager, 'add_context') as mock_add_context:
            explanation = agent.explain_code("def hello(): return 'Hello, world!'")
            
            assert explanation == "Mock explanation"
            assert mock_add_context.call_count == 2  # code, explanation
    
    def test_generate_tests(self, agent):
        """Test generating tests."""
        with patch.object(agent.memory_manager, 'add_context') as mock_add_context:
            result = agent.generate_tests("def hello(): return 'Hello, world!'")
            
            assert result["tests"] == "def test_mock(): pass"
            assert result["explanation"] == "Mock explanation"
            assert mock_add_context.call_count == 3  # code, tests, explanation
    
    def test_generate_documentation(self, agent):
        """Test generating documentation."""
        with patch.object(agent.memory_manager, 'add_context') as mock_add_context:
            documentation = agent.generate_documentation("def hello(): return 'Hello, world!'")
            
            assert documentation == "Mock documentation"
            assert mock_add_context.call_count == 2  # code, documentation
    
    def test_error_when_lm_not_set(self):
        """Test that methods raise errors when LM is not set."""
        agent = BaseAgent()  # No LM provided
        
        with pytest.raises(ValueError, match="Language model not set"):
            agent.answer_query("How do I define a function?")
        
        with pytest.raises(ValueError, match="Language model not set"):
            agent.generate_code("Write a function")
        
        with pytest.raises(ValueError, match="Language model not set"):
            agent.explain_code("def hello(): pass")
        
        with pytest.raises(ValueError, match="Language model not set"):
            agent.generate_tests("def hello(): pass")
        
        with pytest.raises(ValueError, match="Language model not set"):
            agent.generate_documentation("def hello(): pass")
