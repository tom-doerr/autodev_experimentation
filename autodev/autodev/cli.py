"""
Command line interface for AutoDev
"""

import argparse
import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any

from .agent import AutoDevAgent

def read_file(file_path: str) -> str:
    """Read content from a file."""
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        sys.exit(1)

def write_file(file_path: str, content: str) -> None:
    """Write content to a file."""
    try:
        with open(file_path, 'w') as f:
            f.write(content)
    except Exception as e:
        print(f"Error writing to file {file_path}: {e}")
        sys.exit(1)

def format_output(result: Dict[str, Any], format_type: str = "readable") -> str:
    """Format the output according to the specified format."""
    if format_type == "json":
        return json.dumps(result, indent=2)
    
    # Default readable format
    output = []
    
    if result.get("response"):
        output.append("\n=== RESPONSE ===")
        output.append(result["response"])
    
    if result.get("code"):
        output.append("\n=== CODE ===")
        output.append(f"```\n{result['code']}\n```")
    
    if result.get("explanation"):
        output.append("\n=== EXPLANATION ===")
        output.append(result["explanation"])
    
    return "\n".join(output)

def setup_api_key() -> None:
    """Prompt user for API key if not set."""
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("OpenRouter API key not found.")
        key = input("Please enter your OpenRouter API key: ")
        
        if not key.strip():
            print("No API key provided. Exiting.")
            sys.exit(1)
        
        # Save to .env file in current directory
        env_path = Path.home() / ".autodev.env"
        with open(env_path, 'w') as f:
            f.write(f"OPENROUTER_API_KEY={key}")
        
        print(f"API key saved to {env_path}")
        os.environ["OPENROUTER_API_KEY"] = key

def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="AutoDev - AI-powered software development assistant")
    
    # Main command options
    parser.add_argument("--model", type=str, default="openrouter/google/gemini-2.0-flash-001",
                        help="Model to use for generation")
    parser.add_argument("--format", type=str, choices=["readable", "json"], default="readable",
                        help="Output format")
    parser.add_argument("--setup", action="store_true", help="Setup API key")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate code from a description")
    generate_parser.add_argument("prompt", type=str, help="Description of code to generate")
    generate_parser.add_argument("--output", "-o", type=str, help="Output file for generated code")
    
    # Explain command
    explain_parser = subparsers.add_parser("explain", help="Explain code")
    explain_parser.add_argument("file", type=str, help="File containing code to explain")
    
    # Refactor command
    refactor_parser = subparsers.add_parser("refactor", help="Refactor code")
    refactor_parser.add_argument("file", type=str, help="File containing code to refactor")
    refactor_parser.add_argument("--instructions", "-i", type=str, help="Refactoring instructions")
    refactor_parser.add_argument("--output", "-o", type=str, help="Output file for refactored code")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Generate tests for code")
    test_parser.add_argument("file", type=str, help="File containing code to generate tests for")
    test_parser.add_argument("--output", "-o", type=str, help="Output file for generated tests")
    
    # Document command
    doc_parser = subparsers.add_parser("document", help="Document code")
    doc_parser.add_argument("file", type=str, help="File containing code to document")
    doc_parser.add_argument("--output", "-o", type=str, help="Output file for documented code")
    
    args = parser.parse_args()
    
    # If setup flag is given or no command is specified, run setup
    if args.setup or args.command is None:
        setup_api_key()
        if args.command is None:
            print("Use --help to see available commands")
            sys.exit(0)
    
    # Initialize the agent
    try:
        agent = AutoDevAgent(model_name=args.model)
    except ValueError as e:
        print(f"Error initializing agent: {e}")
        setup_api_key()
        agent = AutoDevAgent(model_name=args.model)
    
    result = None
    
    # Execute the appropriate command
    if args.command == "generate":
        result = agent.run(args.prompt)
        
        if args.output and result.get("code"):
            write_file(args.output, result["code"])
            print(f"Generated code saved to {args.output}")
    
    elif args.command == "explain":
        code = read_file(args.file)
        result = agent.explain_code(code)
        # Format result as dictionary for consistent output handling
        result = {"explanation": result}
    
    elif args.command == "refactor":
        code = read_file(args.file)
        result = agent.refactor_code(code, args.instructions)
        
        if args.output and result.get("code"):
            write_file(args.output, result["code"])
            print(f"Refactored code saved to {args.output}")
    
    elif args.command == "test":
        code = read_file(args.file)
        result = agent.generate_tests(code)
        
        if args.output and result.get("code"):
            write_file(args.output, result["code"])
            print(f"Generated tests saved to {args.output}")
    
    elif args.command == "document":
        code = read_file(args.file)
        result = agent.document_code(code)
        
        if args.output and result.get("code"):
            write_file(args.output, result["code"])
            print(f"Documented code saved to {args.output}")
    
    # Print the result
    if result:
        print(format_output(result, args.format))

if __name__ == "__main__":
    main()
