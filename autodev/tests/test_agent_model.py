"""
Tests for the model configuration module.
"""
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add parent directory to path for importing
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import dspy
from autodev.agent.model import (
    get_api_key,
    save_api_key,
    setup_openrouter_model,
    setup_openai_model
)


class TestModelConfiguration:
    """Test suite for the model configuration module."""
    
    @pytest.fixture
    def mock_env(self):
        """Set up mock environment variables."""
        original_environ = os.environ.copy()
        # Clear API keys from environment
        if "OPENROUTER_API_KEY" in os.environ:
            del os.environ["OPENROUTER_API_KEY"]
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        yield
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_environ)
    
    def test_get_api_key_from_env(self, mock_env):
        """Test getting API key from environment."""
        # Set key in environment
        os.environ["TEST_API_KEY"] = "test_key_value"
        
        # Get key
        key = get_api_key("TEST_API_KEY")
        
        assert key == "test_key_value"
    
    def test_get_api_key_not_found(self, mock_env):
        """Test getting a non-existent API key."""
        key = get_api_key("NONEXISTENT_KEY")
        
        assert key is None
    
    def test_save_and_get_api_key(self, mock_env):
        """Test saving and then getting an API key."""
        with patch('pathlib.Path.home') as mock_home:
            # Set up temporary directory
            temp_dir = tempfile.mkdtemp()
            mock_home.return_value = Path(temp_dir)
            
            # Ensure .autodev directory exists
            autodev_dir = Path(temp_dir) / ".autodev"
            autodev_dir.mkdir(exist_ok=True)
            
            # Save API key
            save_api_key("TEST_API_KEY", "test_key_value")
            
            # Check that file exists
            env_file = autodev_dir / ".env"
            assert env_file.exists()
            
            # Check file contents
            with open(env_file, 'r') as f:
                content = f.read()
                assert "TEST_API_KEY=test_key_value" in content
            
            # Get key and verify it matches
            with patch('dotenv.load_dotenv'):
                os.environ["TEST_API_KEY"] = "test_key_value"  # Mock what load_dotenv would do
                key = get_api_key("TEST_API_KEY")
                assert key == "test_key_value"
    
    def test_setup_openrouter_model(self, mock_env):
        """Test setting up an OpenRouter model."""
        with patch('dspy.Mistral') as mock_mistral:
            mock_lm = MagicMock(spec=dspy.LM)
            mock_mistral.return_value = mock_lm
            
            # Test with explicit API key
            lm = setup_openrouter_model(api_key="test_key")
            
            mock_mistral.assert_called_once()
            assert lm is mock_lm
            
            # Check API key was saved
            with patch('pathlib.Path.home') as mock_home:
                temp_dir = tempfile.mkdtemp()
                mock_home.return_value = Path(temp_dir)
                
                # Create directory
                autodev_dir = Path(temp_dir) / ".autodev"
                autodev_dir.mkdir(exist_ok=True)
                
                # Call function again
                setup_openrouter_model(api_key="test_key")
                
                # Check that file exists
                env_file = autodev_dir / ".env"
                assert env_file.exists()
    
    def test_setup_openrouter_model_no_key(self, mock_env):
        """Test setting up an OpenRouter model without an API key."""
        # Mock get_api_key to return None
        with patch('autodev.agent.model.get_api_key', return_value=None):
            # No key provided or in environment
            with pytest.raises(ValueError, match="OpenRouter API key not provided"):
                setup_openrouter_model()
    
    def test_setup_openai_model(self, mock_env):
        """Test setting up an OpenAI model."""
        with patch('dspy.OpenAI') as mock_openai:
            mock_lm = MagicMock(spec=dspy.LM)
            mock_openai.return_value = mock_lm
            
            # Test with explicit API key
            lm = setup_openai_model(api_key="test_key")
            
            mock_openai.assert_called_once()
            assert lm is mock_lm
            
            # Check API key was saved
            with patch('pathlib.Path.home') as mock_home:
                temp_dir = tempfile.mkdtemp()
                mock_home.return_value = Path(temp_dir)
                
                # Create directory
                autodev_dir = Path(temp_dir) / ".autodev"
                autodev_dir.mkdir(exist_ok=True)
                
                # Call function again
                setup_openai_model(api_key="test_key")
                
                # Check that file exists
                env_file = autodev_dir / ".env"
                assert env_file.exists()
    
    def test_setup_openai_model_no_key(self, mock_env):
        """Test setting up an OpenAI model without an API key."""
        # Mock get_api_key to return None
        with patch('autodev.agent.model.get_api_key', return_value=None):
            # No key provided or in environment
            with pytest.raises(ValueError, match="OpenAI API key not provided"):
                setup_openai_model()
