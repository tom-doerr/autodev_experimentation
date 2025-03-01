"""
Model configuration for AutoDev agents.
"""
import os
from typing import Optional, Dict, Any
import dspy
from pathlib import Path
from dotenv import load_dotenv


def get_api_key(key_name: str) -> Optional[str]:
    """
    Get API key from environment variables.
    
    Args:
        key_name: Name of the API key environment variable
        
    Returns:
        API key or None if not found
    """
    # Load environment variables from .env file if it exists
    env_file = Path.home() / ".autodev" / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    
    # Try to get key from environment
    return os.environ.get(key_name)


def save_api_key(key_name: str, api_key: str) -> None:
    """
    Save API key to the .env file.
    
    Args:
        key_name: Name of the API key environment variable
        api_key: API key to save
    """
    # Create directory if it doesn't exist
    env_dir = Path.home() / ".autodev"
    env_dir.mkdir(exist_ok=True)
    
    # Create or update .env file
    env_file = env_dir / ".env"
    
    # Read existing content
    content = {}
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    content[key] = value
    
    # Update key
    content[key_name] = api_key
    
    # Write back
    with open(env_file, 'w') as f:
        for key, value in content.items():
            f.write(f"{key}={value}\n")


def setup_openrouter_model(api_key: Optional[str] = None, 
                           model_name: str = "mistral-large-latest") -> dspy.LM:
    """
    Set up an OpenRouter-based language model.
    
    Args:
        api_key: OpenRouter API key (optional, will try to get from environment)
        model_name: Model name to use
        
    Returns:
        Configured DSPy LM
    """
    # Get API key if not provided
    if api_key is None:
        api_key = get_api_key("OPENROUTER_API_KEY")
        
        if api_key is None:
            raise ValueError(
                "OpenRouter API key not provided and not found in environment. "
                "Please provide an API key or set the OPENROUTER_API_KEY environment variable."
            )
    
    # Save API key for future use
    save_api_key("OPENROUTER_API_KEY", api_key)
    
    # Configure Mistral
    mistral_config = {
        "model": model_name,
        "api_key": api_key
    }
    
    # Create Mistral LM
    lm = dspy.Mistral(**mistral_config)
    
    return lm


def setup_openai_model(api_key: Optional[str] = None,
                       model_name: str = "gpt-4") -> dspy.LM:
    """
    Set up an OpenAI-based language model.
    
    Args:
        api_key: OpenAI API key (optional, will try to get from environment)
        model_name: Model name to use
        
    Returns:
        Configured DSPy LM
    """
    # Get API key if not provided
    if api_key is None:
        api_key = get_api_key("OPENAI_API_KEY")
        
        if api_key is None:
            raise ValueError(
                "OpenAI API key not provided and not found in environment. "
                "Please provide an API key or set the OPENAI_API_KEY environment variable."
            )
    
    # Save API key for future use
    save_api_key("OPENAI_API_KEY", api_key)
    
    # Configure OpenAI
    openai_config = {
        "model": model_name,
        "api_key": api_key
    }
    
    # Create OpenAI LM
    lm = dspy.OpenAI(**openai_config)
    
    return lm
