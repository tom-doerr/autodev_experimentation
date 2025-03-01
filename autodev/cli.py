"""
Command-line interface for AutoDev.
"""
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

import dspy

from autodev.agent.base import BaseAgent
from autodev.agent.model import setup_openrouter_model, setup_openai_model, get_api_key


def setup_argparse() -> argparse.ArgumentParser:
    """
    Set up argument parser.
    
    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="AutoDev - AI-powered software development assistant"
    )
    
    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Configure AutoDev")
    config_parser.add_argument(
        "--api-key", 
        help="Set OpenRouter API key"
    )
    config_parser.add_argument(
        "--model", 
        choices=["openrouter", "openai"],
        default="openrouter",
        help="Model provider to use"
    )
    config_parser.add_argument(
        "--model-name", 
        help="Specific model name to use"
    )
    
    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate code")
    generate_parser.add_argument(
        "task", 
        help="Code generation task description"
    )
    generate_parser.add_argument(
        "--constraints", 
        help="Constraints or requirements for the generated code"
    )
    generate_parser.add_argument(
        "--context-file", 
        help="File containing additional context for code generation"
    )
    generate_parser.add_argument(
        "--output-file", 
        help="File to write the generated code to"
    )
    
    # Explain command
    explain_parser = subparsers.add_parser("explain", help="Explain code")
    explain_parser.add_argument(
        "file", 
        help="File containing code to explain"
    )
    explain_parser.add_argument(
        "--context-file", 
        help="File containing additional context for explanation"
    )
    explain_parser.add_argument(
        "--output-file", 
        help="File to write the explanation to"
    )
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Generate tests")
    test_parser.add_argument(
        "file", 
        help="File containing code to generate tests for"
    )
    test_parser.add_argument(
        "--context-file", 
        help="File containing additional context for test generation"
    )
    test_parser.add_argument(
        "--output-file", 
        help="File to write the generated tests to"
    )
    
    # Document command
    doc_parser = subparsers.add_parser("document", help="Generate documentation")
    doc_parser.add_argument(
        "file", 
        help="File containing code to document"
    )
    doc_parser.add_argument(
        "--context-file", 
        help="File containing additional context for documentation"
    )
    doc_parser.add_argument(
        "--output-file", 
        help="File to write the generated documentation to"
    )
    
    # Query command
    query_parser = subparsers.add_parser("query", help="Answer a code-related query")
    query_parser.add_argument(
        "query", 
        help="Query to answer"
    )
    query_parser.add_argument(
        "--context-file", 
        help="File containing additional context for the query"
    )
    query_parser.add_argument(
        "--output-file", 
        help="File to write the response to"
    )
    
    return parser


def setup_model(args: argparse.Namespace) -> dspy.LM:
    """
    Set up language model based on arguments.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Configured language model
    """
    api_key = None
    model_name = None
    
    # Get API key
    if hasattr(args, "api_key") and args.api_key:
        api_key = args.api_key
    
    # Get model name
    if hasattr(args, "model_name") and args.model_name:
        model_name = args.model_name
    
    # Set up model based on provider
    if not hasattr(args, "model") or args.model == "openrouter":
        if api_key is None:
            api_key = get_api_key("OPENROUTER_API_KEY")
        
        if model_name is None:
            model_name = "anthropic/claude-3-haiku-20240307"
        
        return setup_openrouter_model(api_key=api_key, model_name=model_name)
    else:  # openai
        if api_key is None:
            api_key = get_api_key("OPENAI_API_KEY")
        
        if model_name is None:
            model_name = "gpt-4"
        
        return setup_openai_model(api_key=api_key, model_name=model_name)


def read_file(file_path: str) -> str:
    """
    Read contents of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File contents
    """
    with open(file_path, 'r') as f:
        return f.read()


def write_file(file_path: str, content: str) -> None:
    """
    Write content to a file.
    
    Args:
        file_path: Path to the file
        content: Content to write
    """
    with open(file_path, 'w') as f:
        f.write(content)


def handle_config(args: argparse.Namespace) -> None:
    """
    Handle the config command.
    
    Args:
        args: Command-line arguments
    """
    try:
        # This will validate the API key and save it
        lm = setup_model(args)
        print("Configuration successful!")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


def handle_generate(args: argparse.Namespace, agent: BaseAgent) -> None:
    """
    Handle the generate command.
    
    Args:
        args: Command-line arguments
        agent: BaseAgent instance
    """
    # Get context if provided
    context = None
    if args.context_file:
        context = read_file(args.context_file)
    
    # Generate code
    result = agent.generate_code(
        task=args.task,
        constraints=args.constraints,
        context=context
    )
    
    # Output code
    if args.output_file:
        write_file(args.output_file, result["code"])
        print(f"Code written to {args.output_file}")
    else:
        print("Generated code:")
        print("-" * 40)
        print(result["code"])
        print("-" * 40)
    
    # Output explanation
    print("\nExplanation:")
    print(result["explanation"])


def handle_explain(args: argparse.Namespace, agent: BaseAgent) -> None:
    """
    Handle the explain command.
    
    Args:
        args: Command-line arguments
        agent: BaseAgent instance
    """
    # Read code from file
    code = read_file(args.file)
    
    # Get context if provided
    context = None
    if args.context_file:
        context = read_file(args.context_file)
    
    # Explain code
    explanation = agent.explain_code(code=code, context=context)
    
    # Output explanation
    if args.output_file:
        write_file(args.output_file, explanation)
        print(f"Explanation written to {args.output_file}")
    else:
        print("Explanation:")
        print("-" * 40)
        print(explanation)
        print("-" * 40)


def handle_test(args: argparse.Namespace, agent: BaseAgent) -> None:
    """
    Handle the test command.
    
    Args:
        args: Command-line arguments
        agent: BaseAgent instance
    """
    # Read code from file
    code = read_file(args.file)
    
    # Get context if provided
    context = None
    if args.context_file:
        context = read_file(args.context_file)
    
    # Generate tests
    result = agent.generate_tests(code=code, context=context)
    
    # Output tests
    if args.output_file:
        write_file(args.output_file, result["tests"])
        print(f"Tests written to {args.output_file}")
    else:
        print("Generated tests:")
        print("-" * 40)
        print(result["tests"])
        print("-" * 40)
    
    # Output explanation
    print("\nExplanation:")
    print(result["explanation"])


def handle_document(args: argparse.Namespace, agent: BaseAgent) -> None:
    """
    Handle the document command.
    
    Args:
        args: Command-line arguments
        agent: BaseAgent instance
    """
    # Read code from file
    code = read_file(args.file)
    
    # Get context if provided
    context = None
    if args.context_file:
        context = read_file(args.context_file)
    
    # Generate documentation
    documentation = agent.generate_documentation(code=code, context=context)
    
    # Output documentation
    if args.output_file:
        write_file(args.output_file, documentation)
        print(f"Documentation written to {args.output_file}")
    else:
        print("Generated documentation:")
        print("-" * 40)
        print(documentation)
        print("-" * 40)


def handle_query(args: argparse.Namespace, agent: BaseAgent) -> None:
    """
    Handle the query command.
    
    Args:
        args: Command-line arguments
        agent: BaseAgent instance
    """
    # Get context if provided
    context = None
    if args.context_file:
        context = read_file(args.context_file)
    
    # Answer query
    response = agent.answer_query(query=args.query, context=context)
    
    # Output response
    if args.output_file:
        write_file(args.output_file, response)
        print(f"Response written to {args.output_file}")
    else:
        print("Response:")
        print("-" * 40)
        print(response)
        print("-" * 40)


def process_agent_command(args: argparse.Namespace) -> None:
    """
    Process commands that require an agent.
    
    Args:
        args: Command-line arguments
    """
    # Set up language model
    lm = setup_model(args)
    
    # Set up agent
    agent = BaseAgent(lm=lm)
    
    # Command handler mapping
    command_handlers = {
        "generate": handle_generate,
        "explain": handle_explain,
        "test": handle_test,
        "document": handle_document,
        "query": handle_query
    }
    
    # Get the appropriate handler and execute it
    handler = command_handlers.get(args.command)
    if handler:
        handler(args, agent)
    else:
        # This shouldn't happen if argparse is configured correctly,
        # but handle it just in case
        raise ValueError(f"Unknown command: {args.command}")


def main() -> None:
    """Main entry point for the CLI."""
    parser = setup_argparse()
    args = parser.parse_args()
    
    # If no command provided, show help
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Config command doesn't need an agent
    if args.command == "config":
        handle_config(args)
        sys.exit(0)
    
    try:
        # Process commands that require an agent
        process_agent_command(args)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
