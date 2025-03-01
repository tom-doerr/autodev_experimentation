import os
import dspy
import sys
from typing import List, Optional
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

class AutoDevAgent(dspy.Module):
    """An agent that aids in software development using LLMs."""
    
    def __init__(self):
        super().__init__()
        # Define the signature using ChainOfThought for reasoning
        self.generate_response = dspy.ChainOfThought(DevResponse)
    
    def forward(self, query: str, context: Optional[str] = None) -> dict:
        """Process a development query and return a helpful response."""
        return self.generate_response(query=query, context=context)

    def __call__(self, query: str, context: Optional[str] = None) -> dict:
        return self.forward(query, context)

def setup_openrouter_model():
    """Configure DSPy to use OpenRouter's Gemini model."""
    # Use the API key from .env file (loaded by dotenv)
    api_key = os.environ.get("OPENROUTER_API_KEY")
    
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable not set. Make sure you have a .env file with this key.")
    
    # Configure LM using the recommended approach in DSPy
    lm = dspy.LM(
        provider="openai",
        model="openrouter/google/gemini-2.0-flash-001",
    )
    
    # Configure DSPy to use this language model
    dspy.settings.configure(lm=lm)
    
    return lm

def main():
    try:
        # Set up the model
        lm = setup_openrouter_model()
        
        # Initialize the agent
        agent = AutoDevAgent()
        
        # Example usage
        query = "Create a function that calculates the Fibonacci sequence in Python"
        print("\n=== QUERY ===")
        print(query)
        
        print("\n=== CONNECTING TO OPENROUTER API ===")
        result = agent(query)
        
        print("\n=== RESPONSE ===")
        print(result.response)
        
        if result.code:
            print("\n=== CODE ===")
            print(result.code)
        
        if result.explanation:
            print("\n=== EXPLANATION ===")
            print(result.explanation)
            
    except ValueError as e:
        print(f"\n=== ERROR: API KEY NOT FOUND ===")
        print(f"{e}")
        print("\nPlease run the setup_env.py script to extract your API key from zshrc:")
        print("python setup_env.py")
        
    except Exception as e:
        print(f"\n=== API CONNECTION ERROR ===")
        print(f"Failed to connect to the API: {e}")
        print("\nPossible solutions:")
        print("1. Make sure you have run the setup_env.py script")
        print("2. Check your internet connection")
        print("3. Verify your API key is correct in the .env file")

if __name__ == "__main__":
    main()
