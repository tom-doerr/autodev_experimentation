"""
Base agent for AutoDev.
"""
from typing import Dict, Any, List, Optional, Union
import os
import dspy
from pathlib import Path

# Import our memory manager
from autodev.memory.dspy_memory import MemoryManager


class CodeQuery(dspy.Signature):
    """DSPy Signature for code-related queries."""
    
    query = dspy.InputField(desc="The user's query about code")
    context = dspy.InputField(desc="Relevant code context", default=None)
    response = dspy.OutputField(desc="Detailed response to the query")


class CodeGenerator(dspy.Signature):
    """DSPy Signature for code generation."""
    
    task = dspy.InputField(desc="The code generation task")
    constraints = dspy.InputField(desc="Any constraints or requirements", default=None)
    context = dspy.InputField(desc="Relevant code context", default=None)
    code = dspy.OutputField(desc="Generated code")
    explanation = dspy.OutputField(desc="Explanation of the generated code")


class CodeExplanation(dspy.Signature):
    """DSPy Signature for code explanation."""
    
    code = dspy.InputField(desc="Code to explain")
    context = dspy.InputField(desc="Additional context", default=None)
    explanation = dspy.OutputField(desc="Step-by-step explanation of the code")


class TestGenerator(dspy.Signature):
    """DSPy Signature for test generation."""
    
    code = dspy.InputField(desc="Code to generate tests for")
    context = dspy.InputField(desc="Additional context", default=None)
    tests = dspy.OutputField(desc="Generated test code")
    explanation = dspy.OutputField(desc="Explanation of the test coverage")


class DocumentationGenerator(dspy.Signature):
    """DSPy Signature for documentation generation."""
    
    code = dspy.InputField(desc="Code to document")
    context = dspy.InputField(desc="Additional context", default=None)
    documentation = dspy.OutputField(desc="Generated documentation")


class BaseAgent(dspy.Module):
    """Base agent for code-related tasks using DSPy."""
    
    def __init__(self, 
                 lm: Optional[dspy.LM] = None, 
                 project_id: Optional[str] = None):
        """
        Initialize the base agent.
        
        Args:
            lm: Language model to use
            project_id: Optional project ID
        """
        super().__init__()
        
        # Set up language model
        self.lm = lm
        
        # Set up memory manager
        self.memory_manager = MemoryManager(project_id=project_id)
        
        # Set up modules for different tasks
        if lm is not None:
            self.code_query = dspy.Predict(CodeQuery, lm=lm)
            self.code_generator = dspy.Predict(CodeGenerator, lm=lm)
            self.code_explainer = dspy.Predict(CodeExplanation, lm=lm)
            self.test_generator = dspy.Predict(TestGenerator, lm=lm)
            self.doc_generator = dspy.Predict(DocumentationGenerator, lm=lm)
    
    def set_language_model(self, lm: dspy.LM) -> None:
        """
        Set or update the language model.
        
        Args:
            lm: Language model to use
        """
        self.lm = lm
        self.code_query = dspy.Predict(CodeQuery, lm=lm)
        self.code_generator = dspy.Predict(CodeGenerator, lm=lm)
        self.code_explainer = dspy.Predict(CodeExplanation, lm=lm)
        self.test_generator = dspy.Predict(TestGenerator, lm=lm)
        self.doc_generator = dspy.Predict(DocumentationGenerator, lm=lm)
    
    def set_project(self, project_id: str) -> None:
        """
        Set or change the current project.
        
        Args:
            project_id: Project ID
        """
        self.memory_manager.set_project(project_id)
    
    def answer_query(self, query: str, context: Optional[str] = None) -> str:
        """
        Answer a code-related query.
        
        Args:
            query: The user's query
            context: Optional code context
            
        Returns:
            Response to the query
        """
        if self.lm is None:
            raise ValueError("Language model not set")
        
        # Add to context memory
        self.memory_manager.add_context("query", query)
        if context:
            self.memory_manager.add_context("context", context)
        
        # Get prediction from LM
        result = self.code_query(query=query, context=context)
        
        # Add to context memory
        self.memory_manager.add_context("response", result.response)
        
        return result.response
    
    def generate_code(self, 
                      task: str, 
                      constraints: Optional[str] = None, 
                      context: Optional[str] = None) -> Dict[str, str]:
        """
        Generate code based on a task description.
        
        Args:
            task: The code generation task
            constraints: Optional constraints or requirements
            context: Optional code context
            
        Returns:
            Dictionary with generated code and explanation
        """
        if self.lm is None:
            raise ValueError("Language model not set")
        
        # Add to context memory
        self.memory_manager.add_context("task", task)
        if constraints:
            self.memory_manager.add_context("constraints", constraints)
        if context:
            self.memory_manager.add_context("context", context)
        
        # Get prediction from LM
        result = self.code_generator(
            task=task,
            constraints=constraints,
            context=context
        )
        
        # Add to context memory
        self.memory_manager.add_context("code", result.code)
        self.memory_manager.add_context("explanation", result.explanation)
        
        return {
            "code": result.code,
            "explanation": result.explanation
        }
    
    def explain_code(self, code: str, context: Optional[str] = None) -> str:
        """
        Explain code.
        
        Args:
            code: Code to explain
            context: Optional additional context
            
        Returns:
            Explanation of the code
        """
        if self.lm is None:
            raise ValueError("Language model not set")
        
        # Add to context memory
        self.memory_manager.add_context("code", code)
        if context:
            self.memory_manager.add_context("context", context)
        
        # Get prediction from LM
        result = self.code_explainer(code=code, context=context)
        
        # Add to context memory
        self.memory_manager.add_context("explanation", result.explanation)
        
        return result.explanation
    
    def generate_tests(self, code: str, context: Optional[str] = None) -> Dict[str, str]:
        """
        Generate tests for code.
        
        Args:
            code: Code to generate tests for
            context: Optional additional context
            
        Returns:
            Dictionary with generated tests and explanation
        """
        if self.lm is None:
            raise ValueError("Language model not set")
        
        # Add to context memory
        self.memory_manager.add_context("code", code)
        if context:
            self.memory_manager.add_context("context", context)
        
        # Get prediction from LM
        result = self.test_generator(code=code, context=context)
        
        # Add to context memory
        self.memory_manager.add_context("tests", result.tests)
        self.memory_manager.add_context("explanation", result.explanation)
        
        return {
            "tests": result.tests,
            "explanation": result.explanation
        }
    
    def generate_documentation(self, code: str, context: Optional[str] = None) -> str:
        """
        Generate documentation for code.
        
        Args:
            code: Code to document
            context: Optional additional context
            
        Returns:
            Generated documentation
        """
        if self.lm is None:
            raise ValueError("Language model not set")
        
        # Add to context memory
        self.memory_manager.add_context("code", code)
        if context:
            self.memory_manager.add_context("context", context)
        
        # Get prediction from LM
        result = self.doc_generator(code=code, context=context)
        
        # Add to context memory
        self.memory_manager.add_context("documentation", result.documentation)
        
        return result.documentation
