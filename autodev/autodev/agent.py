"""
Core agent functionality for AutoDev
"""

import os
import dspy
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class DevResponse(dspy.Signature):
    """Generate a helpful response for a software development task."""
    
    query = dspy.InputField(desc="The development-related query or task")
    context = dspy.InputField(desc="Optional context or background information", default=None)
    
    response = dspy.OutputField(desc="A helpful response addressing the query")
    code = dspy.OutputField(desc="Code snippet that solves the task, if applicable")
    explanation = dspy.OutputField(desc="Explanation of the solution or approach")

class AutoDevAgent:
    """An agent that aids in software development using LLMs."""
    
    def __init__(self, model_name="openrouter/google/gemini-2.0-flash-001"):
        """
        Initialize the AutoDev agent.
        
        Args:
            model_name: The model to use for generation
        """
        self.model_name = model_name
        self.setup_model()
        self.generate_response = dspy.ChainOfThought(DevResponse)
    
    def setup_model(self):
        """Configure DSPy to use the specified model."""
        # Use the API key from .env file (loaded by dotenv)
        api_key = os.environ.get("OPENROUTER_API_KEY")
        
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set. Make sure you have a .env file with this key.")
        
        # Configure LM using the recommended approach in DSPy
        lm = dspy.LM(
            provider="openai",
            model=self.model_name,
        )
        
        # Configure DSPy to use this language model
        dspy.settings.configure(lm=lm)
    
    def run(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a development query and return a helpful response.
        
        Args:
            query: The development-related query or task
            context: Optional context or background information
            
        Returns:
            Dictionary containing the response, code, and explanation
        """
        result = self.generate_response(query=query, context=context)
        
        return {
            "response": result.response, 
            "code": result.code, 
            "explanation": result.explanation
        }
    
    def explain_code(self, code: str) -> str:
        """
        Generate an explanation for a code snippet.
        
        Args:
            code: The code to explain
            
        Returns:
            String explanation of the provided code
        """
        result = self.run(f"Explain the following code:\n\n{code}", context=code)
        return result["explanation"]
    
    def refactor_code(self, code: str, instructions: Optional[str] = None) -> Dict[str, Any]:
        """
        Refactor a code snippet according to the provided instructions.
        
        Args:
            code: The code to refactor
            instructions: Optional specific refactoring instructions
            
        Returns:
            Dictionary containing the refactored code and explanation
        """
        query = "Refactor the following code"
        if instructions:
            query += f" according to these instructions: {instructions}"
        
        result = self.run(query, context=code)
        return result
    
    def generate_tests(self, code: str) -> Dict[str, Any]:
        """
        Generate tests for the provided code.
        
        Args:
            code: The code to generate tests for
            
        Returns:
            Dictionary containing the generated test code and explanation
        """
        result = self.run("Generate comprehensive tests for the following code", context=code)
        return result
    
    def document_code(self, code: str) -> Dict[str, Any]:
        """
        Add documentation to the provided code.
        
        Args:
            code: The code to document
            
        Returns:
            Dictionary containing the documented code and explanation
        """
        result = self.run("Add detailed documentation to the following code", context=code)
        return result
