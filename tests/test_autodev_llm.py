import pytest
import os
import sys
from unittest.mock import patch, MagicMock
import dspy

# Add parent directory to path to import from main package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from autodev_llm import AutoDevAgent, setup_openrouter_model, DevResponse

class TestAutoDevLLM:
    """Test suite for the AutoDev LLM agent."""
    
    def test_agent_initialization(self):
        """Test that the agent initializes properly."""
        agent = AutoDevAgent()
        assert hasattr(agent, 'generate_response')
    
    @patch('dspy.LM')
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock-api-key"})
    def test_openrouter_model_setup(self, mock_lm):
        """Test that the OpenRouter model is configured correctly."""
        mock_instance = MagicMock()
        mock_lm.return_value = mock_instance
        
        lm = setup_openrouter_model()
        
        # Check that LM was called with the correct parameters
        mock_lm.assert_called_once()
        call_args = mock_lm.call_args[1]
        assert call_args['provider'] == "openai"
        assert call_args['model'] == "openrouter/google/gemini-2.0-flash-001"
        assert call_args['api_key'] == "mock-api-key"
        assert call_args['api_base'] == "https://openrouter.ai/api/v1"
        assert 'HTTP-Referer' in call_args['extra_headers']
        assert 'X-Title' in call_args['extra_headers']
    
    @patch('dspy.ChainOfThought.__call__')
    def test_agent_forward(self, mock_chain_of_thought):
        """Test that the agent's forward method calls generate_response correctly."""
        # Setup mock return value
        mock_result = MagicMock()
        mock_result.response = "Test response"
        mock_result.code = "def test(): pass"
        mock_result.explanation = "This is a test"
        mock_chain_of_thought.return_value = mock_result
        
        # Create agent and call forward
        agent = AutoDevAgent()
        result = agent("Test query", "Test context")
        
        # Verify generate_response was called with correct args
        mock_chain_of_thought.assert_called_once_with(query="Test query", context="Test context")
        
        # Verify result matches mock
        assert result == mock_result

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
