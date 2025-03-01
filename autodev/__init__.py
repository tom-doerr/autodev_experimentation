"""
AutoDev - AI-powered development assistant.
"""

__version__ = "0.1.0"

# Import main components
from autodev.agent.base import BaseAgent
from autodev.agent.model import setup_openrouter_model, setup_openai_model
from autodev.memory.dspy_memory import MemoryManager, ContextMemory, ProjectMemory
