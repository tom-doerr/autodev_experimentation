"""
Agent module for AutoDev.
"""

from autodev.agent.base import BaseAgent
from autodev.agent.model import (
    setup_openrouter_model, 
    setup_openai_model, 
    get_api_key, 
    save_api_key
)
