"""
Tests for the CLI module.
"""
import os
import sys
import tempfile
import pytest
from unittest.mock import patch, MagicMock, mock_open

# Add parent directory to path for importing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from autodev.cli import (
    setup_argparse,
    setup_model,
    read_file,
    write_file,
    handle_config,
    handle_generate,
    handle_explain,
    handle_test,
    handle_document,
    handle_query,
    main
)


class TestCLI:
    """Test suite for the CLI module."""
    
    def test_setup_argparse(self):
        """Test setting up the argument parser."""
        parser = setup_argparse()
        
        # Test that parser has expected commands
        commands = [
            "config",
            "generate",
            "explain",
            "test",
            "document",
            "query"
        ]
        
        # Parse each command with --help to ensure they're defined
        for command in commands:
            with pytest.raises(SystemExit):
                parser.parse_args([command, "--help"])
    
    def test_setup_model_openrouter(self):
        """Test setting up an OpenRouter model."""
        with patch('autodev.cli.setup_openrouter_model') as mock_setup:
            mock_lm = MagicMock()
            mock_setup.return_value = mock_lm
            
            # Create args
            args = MagicMock()
            args.model = "openrouter"
            args.api_key = "test_key"
            args.model_name = "test_model"
            
            # Call function
            lm = setup_model(args)
            
            # Check that setup_openrouter_model was called with correct args
            mock_setup.assert_called_once_with(
                api_key="test_key",
                model_name="test_model"
            )
            
            assert lm is mock_lm
    
    def test_setup_model_openai(self):
        """Test setting up an OpenAI model."""
        with patch('autodev.cli.setup_openai_model') as mock_setup:
            mock_lm = MagicMock()
            mock_setup.return_value = mock_lm
            
            # Create args
            args = MagicMock()
            args.model = "openai"
            args.api_key = "test_key"
            args.model_name = "test_model"
            
            # Call function
            lm = setup_model(args)
            
            # Check that setup_openai_model was called with correct args
            mock_setup.assert_called_once_with(
                api_key="test_key",
                model_name="test_model"
            )
            
            assert lm is mock_lm
    
    def test_read_file(self):
        """Test reading a file."""
        test_content = "Test content"
        
        # Mock open
        with patch('builtins.open', mock_open(read_data=test_content)):
            content = read_file("test_file.txt")
            
            assert content == test_content
    
    def test_write_file(self):
        """Test writing to a file."""
        test_content = "Test content"
        
        # Mock open
        mock_file = mock_open()
        with patch('builtins.open', mock_file):
            write_file("test_file.txt", test_content)
            
            # Check that file was written to
            mock_file.assert_called_once_with("test_file.txt", 'w')
            mock_file().write.assert_called_once_with(test_content)
    
    def test_handle_config(self):
        """Test handling the config command."""
        with patch('autodev.cli.setup_model') as mock_setup:
            # Test successful config
            args = MagicMock()
            handle_config(args)
            
            mock_setup.assert_called_once_with(args)
            
            # Test failed config
            mock_setup.side_effect = ValueError("Test error")
            
            with pytest.raises(SystemExit):
                handle_config(args)
    
    def test_handle_generate(self):
        """Test handling the generate command."""
        # Mock agent
        mock_agent = MagicMock()
        mock_agent.generate_code.return_value = {
            "code": "def test(): pass",
            "explanation": "This is a test function."
        }
        
        # Args without output file
        args = MagicMock()
        args.task = "Write a test function"
        args.constraints = "Must be simple"
        args.context_file = None
        args.output_file = None
        
        # Test without output file
        with patch('builtins.print') as mock_print:
            handle_generate(args, mock_agent)
            
            mock_agent.generate_code.assert_called_once_with(
                task="Write a test function",
                constraints="Must be simple",
                context=None
            )
            
            # Check that output was printed
            assert mock_print.call_count > 0
        
        # Args with output file
        args.output_file = "test_output.py"
        
        # Test with output file
        with patch('autodev.cli.write_file') as mock_write:
            handle_generate(args, mock_agent)
            
            mock_write.assert_called_once_with("test_output.py", "def test(): pass")
    
    def test_handle_explain(self):
        """Test handling the explain command."""
        # Mock agent
        mock_agent = MagicMock()
        mock_agent.explain_code.return_value = "This is a test function."
        
        # Args without output file
        args = MagicMock()
        args.file = "test_file.py"
        args.context_file = None
        args.output_file = None
        
        # Test without output file
        with patch('autodev.cli.read_file') as mock_read:
            mock_read.return_value = "def test(): pass"
            
            with patch('builtins.print') as mock_print:
                handle_explain(args, mock_agent)
                
                mock_read.assert_called_once_with("test_file.py")
                mock_agent.explain_code.assert_called_once_with(
                    code="def test(): pass",
                    context=None
                )
                
                # Check that output was printed
                assert mock_print.call_count > 0
        
        # Args with output file
        args.output_file = "test_output.md"
        
        # Test with output file
        with patch('autodev.cli.read_file') as mock_read:
            mock_read.return_value = "def test(): pass"
            
            with patch('autodev.cli.write_file') as mock_write:
                handle_explain(args, mock_agent)
                
                mock_write.assert_called_once_with("test_output.md", "This is a test function.")
    
    def test_handle_test(self):
        """Test handling the test command."""
        # Mock agent
        mock_agent = MagicMock()
        mock_agent.generate_tests.return_value = {
            "tests": "def test_function(): assert test() is None",
            "explanation": "This test verifies that the function returns None."
        }
        
        # Args without output file
        args = MagicMock()
        args.file = "test_file.py"
        args.context_file = None
        args.output_file = None
        
        # Test without output file
        with patch('autodev.cli.read_file') as mock_read:
            mock_read.return_value = "def test(): pass"
            
            with patch('builtins.print') as mock_print:
                handle_test(args, mock_agent)
                
                mock_read.assert_called_once_with("test_file.py")
                mock_agent.generate_tests.assert_called_once_with(
                    code="def test(): pass",
                    context=None
                )
                
                # Check that output was printed
                assert mock_print.call_count > 0
        
        # Args with output file
        args.output_file = "test_output.py"
        
        # Test with output file
        with patch('autodev.cli.read_file') as mock_read:
            mock_read.return_value = "def test(): pass"
            
            with patch('autodev.cli.write_file') as mock_write:
                handle_test(args, mock_agent)
                
                mock_write.assert_called_once_with(
                    "test_output.py", 
                    "def test_function(): assert test() is None"
                )
    
    def test_handle_document(self):
        """Test handling the document command."""
        # Mock agent
        mock_agent = MagicMock()
        mock_agent.generate_documentation.return_value = "# Test Function\nA simple test function."
        
        # Args without output file
        args = MagicMock()
        args.file = "test_file.py"
        args.context_file = None
        args.output_file = None
        
        # Test without output file
        with patch('autodev.cli.read_file') as mock_read:
            mock_read.return_value = "def test(): pass"
            
            with patch('builtins.print') as mock_print:
                handle_document(args, mock_agent)
                
                mock_read.assert_called_once_with("test_file.py")
                mock_agent.generate_documentation.assert_called_once_with(
                    code="def test(): pass",
                    context=None
                )
                
                # Check that output was printed
                assert mock_print.call_count > 0
        
        # Args with output file
        args.output_file = "test_output.md"
        
        # Test with output file
        with patch('autodev.cli.read_file') as mock_read:
            mock_read.return_value = "def test(): pass"
            
            with patch('autodev.cli.write_file') as mock_write:
                handle_document(args, mock_agent)
                
                mock_write.assert_called_once_with(
                    "test_output.md", 
                    "# Test Function\nA simple test function."
                )
    
    def test_handle_query(self):
        """Test handling the query command."""
        # Mock agent
        mock_agent = MagicMock()
        mock_agent.answer_query.return_value = "To define a function in Python, use the def keyword."
        
        # Args without output file
        args = MagicMock()
        args.query = "How do I define a function in Python?"
        args.context_file = None
        args.output_file = None
        
        # Test without output file
        with patch('builtins.print') as mock_print:
            handle_query(args, mock_agent)
            
            mock_agent.answer_query.assert_called_once_with(
                query="How do I define a function in Python?",
                context=None
            )
            
            # Check that output was printed
            assert mock_print.call_count > 0
        
        # Args with output file
        args.output_file = "test_output.md"
        
        # Test with output file
        with patch('autodev.cli.write_file') as mock_write:
            handle_query(args, mock_agent)
            
            mock_write.assert_called_once_with(
                "test_output.md", 
                "To define a function in Python, use the def keyword."
            )
    
    def test_main_no_command(self):
        """Test main with no command."""
        with patch('autodev.cli.setup_argparse') as mock_setup:
            mock_parser = MagicMock()
            mock_setup.return_value = mock_parser
            
            # Create args with no command
            mock_args = MagicMock()
            mock_args.command = None
            mock_parser.parse_args.return_value = mock_args
            
            # Call main and check that help is printed
            with pytest.raises(SystemExit):
                with patch.object(sys, 'argv', ['autodev']):
                    main()
            
            mock_parser.print_help.assert_called_once()
    
    def test_main_config(self):
        """Test main with config command."""
        with patch('autodev.cli.setup_argparse') as mock_setup:
            mock_parser = MagicMock()
            mock_setup.return_value = mock_parser
            
            # Create args with config command
            mock_args = MagicMock()
            mock_args.command = "config"
            mock_parser.parse_args.return_value = mock_args
            
            # Call main and check that handle_config is called
            with pytest.raises(SystemExit):
                with patch('autodev.cli.handle_config') as mock_handle:
                    with patch.object(sys, 'argv', ['autodev', 'config']):
                        main()
                    
                    mock_handle.assert_called_once_with(mock_args)
    
    def test_main_generate(self):
        """Test main with generate command."""
        with patch('autodev.cli.setup_argparse') as mock_setup:
            mock_parser = MagicMock()
            mock_setup.return_value = mock_parser
            
            # Create args with generate command
            mock_args = MagicMock()
            mock_args.command = "generate"
            mock_parser.parse_args.return_value = mock_args
            
            # Mock setup_model
            with patch('autodev.cli.setup_model') as mock_model:
                mock_lm = MagicMock()
                mock_model.return_value = mock_lm
                
                # Mock BaseAgent
                with patch('autodev.cli.BaseAgent') as mock_agent_class:
                    mock_agent = MagicMock()
                    mock_agent_class.return_value = mock_agent
                    
                    # Call main and check that handle_generate is called
                    with patch('autodev.cli.handle_generate') as mock_handle:
                        with patch.object(sys, 'argv', ['autodev', 'generate', 'test task']):
                            main()
                        
                        mock_model.assert_called_once_with(mock_args)
                        mock_agent_class.assert_called_once_with(lm=mock_lm)
                        mock_handle.assert_called_once_with(mock_args, mock_agent)
