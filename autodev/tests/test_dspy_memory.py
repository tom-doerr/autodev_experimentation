"""
Tests for the DSPy memory module.
"""
import os
import tempfile
import json
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path for importing
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import dspy
from autodev.memory.dspy_memory import MemoryModule, ContextMemory, ProjectMemory, MemoryManager


class TestMemoryModule:
    """Tests for the MemoryModule class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def memory(self, temp_dir):
        """Create a MemoryModule instance for testing."""
        return MemoryModule(storage_path=temp_dir)
    
    def test_initialization(self, temp_dir):
        """Test that MemoryModule initializes correctly."""
        memory = MemoryModule(storage_path=temp_dir)
        assert os.path.exists(temp_dir)
        assert memory.storage_path == temp_dir
    
    def test_save_and_load(self, memory):
        """Test saving and loading data."""
        test_data = {"test": "data", "nested": {"value": 123}}
        memory.save("test_key", test_data)
        
        # Check that file exists
        file_path = os.path.join(memory.storage_path, "test_key.json")
        assert os.path.exists(file_path)
        
        # Check file contents
        with open(file_path, 'r') as f:
            saved_data = json.load(f)
        assert saved_data == test_data
        
        # Test loading
        loaded_data = memory.load("test_key")
        assert loaded_data == test_data
    
    def test_load_nonexistent(self, memory):
        """Test loading a nonexistent key."""
        assert memory.load("nonexistent") is None
    
    def test_delete(self, memory):
        """Test deleting data."""
        test_data = {"test": "data"}
        memory.save("test_key", test_data)
        
        # Check file exists before deletion
        file_path = os.path.join(memory.storage_path, "test_key.json")
        assert os.path.exists(file_path)
        
        # Test deletion
        assert memory.delete("test_key") is True
        assert not os.path.exists(file_path)
        
        # Test deleting nonexistent key
        assert memory.delete("nonexistent") is False
    
    def test_list_keys(self, memory):
        """Test listing all keys."""
        # Save multiple keys
        memory.save("key1", {"data": 1})
        memory.save("key2", {"data": 2})
        memory.save("key3", {"data": 3})
        
        # List keys
        keys = memory.list_keys()
        assert len(keys) == 3
        assert set(keys) == {"key1", "key2", "key3"}


class TestContextMemoryModule:
    """Test suite for the ContextMemoryModule class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def context_memory(self, temp_dir):
        """Create a ContextMemoryModule instance for testing."""
        return ContextMemory(storage_path=temp_dir)
    
    def test_initialization(self, temp_dir):
        """Test that ContextMemoryModule initializes correctly."""
        memory = ContextMemory(storage_path=temp_dir)
        assert os.path.exists(temp_dir)
        
        # Check that current context is initialized
        context = memory.load("current_context")
        assert context is not None
        assert "entries" in context
        assert isinstance(context["entries"], list)
        assert "last_updated" in context
    
    def test_add_and_get_entries(self, context_memory):
        """Test adding and retrieving entries."""
        # Add entries of different types
        context_memory.add_entry("code", "def hello(): print('Hello')")
        context_memory.add_entry("query", "How to define a function?")
        context_memory.add_entry("response", "Here's how to define a function...")
        
        # Get all entries
        all_entries = context_memory.get_entries()
        assert len(all_entries) == 3
        
        # Get entries by type
        code_entries = context_memory.get_entries("code")
        assert len(code_entries) == 1
        assert code_entries[0]["type"] == "code"
        assert code_entries[0]["content"] == "def hello(): print('Hello')"
        
        query_entries = context_memory.get_entries("query")
        assert len(query_entries) == 1
        assert query_entries[0]["type"] == "query"
        
        # Check nonexistent type
        nonexistent = context_memory.get_entries("nonexistent")
        assert len(nonexistent) == 0
    
    def test_clear(self, context_memory):
        """Test clearing entries."""
        # Add some entries
        context_memory.add_entry("code", "test code")
        context_memory.add_entry("query", "test query")
        
        # Verify entries exist
        entries = context_memory.get_entries()
        assert len(entries) == 2
        
        # Clear entries
        context_memory.clear()
        
        # Verify entries are cleared
        entries = context_memory.get_entries()
        assert len(entries) == 0
    
    def test_max_entries(self, temp_dir):
        """Test that max entries is respected."""
        # Create memory with small max_entries
        memory = ContextMemory(storage_path=temp_dir, max_entries=3)
        
        # Add more than max entries
        for i in range(5):
            memory.add_entry("test", f"entry {i}")
        
        # Verify only max_entries are kept
        entries = memory.get_entries()
        assert len(entries) == 3
        
        # Verify the oldest entries are removed
        contents = [entry["content"] for entry in entries]
        assert "entry 0" not in contents
        assert "entry 1" not in contents
        assert "entry 2" in contents
        assert "entry 3" in contents
        assert "entry 4" in contents


class TestProjectMemoryModule:
    """Test suite for the ProjectMemoryModule class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def project_memory(self, temp_dir):
        """Create a ProjectMemoryModule instance for testing."""
        return ProjectMemory(project_id="test_project", storage_path=temp_dir)
    
    def test_initialization(self, temp_dir):
        """Test that ProjectMemoryModule initializes correctly."""
        memory = ProjectMemory(project_id="test_project", storage_path=temp_dir)
        assert os.path.exists(temp_dir)
        
        # Check that project is initialized
        project = memory.load("project_test_project")
        assert project is not None
        assert project["id"] == "test_project"
        assert "files" in project
        assert "components" in project
        assert "created_at" in project
        assert "last_updated" in project
    
    def test_update_file_info(self, project_memory):
        """Test updating file information."""
        # Update file info without content
        project_memory.update_file_info("test.py")
        
        # Check that file info exists
        file_info = project_memory.get_file_info("test.py")
        assert file_info is not None
        assert "last_updated" in file_info
        
        # Update file info with content
        python_content = "def hello():\n    print('Hello world')\n\nclass Test:\n    pass"
        project_memory.update_file_info("test.py", python_content)
        
        # Check that file info is updated
        file_info = project_memory.get_file_info("test.py")
        assert file_info["language"] == "python"
        assert file_info["size"] == len(python_content)
        assert file_info["line_count"] == 5
        assert len(file_info["functions"]) == 1
        assert file_info["functions"][0] == "hello"
        assert len(file_info["classes"]) == 1
        assert file_info["classes"][0] == "Test"
    
    def test_remove_file(self, project_memory):
        """Test removing a file."""
        # Add a file
        project_memory.update_file_info("test.py", "# Test file")
        
        # Verify file exists
        assert project_memory.get_file_info("test.py") != {}
        
        # Remove the file
        project_memory.remove_file("test.py")
        
        # Verify file is removed
        assert project_memory.get_file_info("test.py") == {}
    
    def test_add_component(self, project_memory):
        """Test adding a component."""
        # Add a component
        project_memory.add_component(
            name="Test Component",
            description="A test component",
            file_paths=["test.py", "test2.py"]
        )
        
        # Get components
        components = project_memory.get_components()
        
        # Verify component exists
        assert len(components) == 1
        assert components[0]["name"] == "Test Component"
        assert components[0]["description"] == "A test component"
        assert components[0]["file_paths"] == ["test.py", "test2.py"]
        assert "created_at" in components[0]


class TestMemoryManager:
    """Test suite for the MemoryManager class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        context_dir = os.path.join(temp_dir, "context")
        project_dir = os.path.join(temp_dir, "project")
        os.makedirs(context_dir)
        os.makedirs(project_dir)
        yield {
            "base": temp_dir,
            "context": context_dir,
            "project": project_dir
        }
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def memory_manager(self, temp_dir):
        """Create a MemoryManager instance for testing."""
        return MemoryManager(
            project_id="test_project",
            context_storage_path=temp_dir["context"],
            project_storage_path=temp_dir["project"]
        )
    
    def test_initialization(self, temp_dir):
        """Test that MemoryManager initializes correctly."""
        manager = MemoryManager(
            project_id="test_project",
            context_storage_path=temp_dir["context"],
            project_storage_path=temp_dir["project"]
        )
        
        assert manager.context_memory is not None
        assert manager.project_memory is not None
        assert manager.project_memory.project_id == "test_project"
    
    def test_set_project(self, memory_manager, temp_dir):
        """Test setting the project."""
        # Change the project
        memory_manager.set_project("new_project")
        
        # Verify project is changed
        assert memory_manager.project_memory.project_id == "new_project"
        
        # Verify project is initialized in storage
        project_path = os.path.join(temp_dir["project"], "project_new_project.json")
        assert os.path.exists(project_path)
    
    def test_add_and_get_context(self, memory_manager):
        """Test adding and retrieving context."""
        # Add context entries
        memory_manager.add_context("code", "test code")
        memory_manager.add_context("query", "test query")
        
        # Get all context
        all_context = memory_manager.get_context()
        assert len(all_context) == 2
        
        # Get context by type
        code_context = memory_manager.get_context("code")
        assert len(code_context) == 1
        assert code_context[0]["type"] == "code"
        assert code_context[0]["content"] == "test code"
    
    def test_update_and_get_file_info(self, memory_manager):
        """Test updating and retrieving file info."""
        # Update file info
        memory_manager.update_file("test.py", "def test(): pass")
        
        # Get file info
        file_info = memory_manager.get_file_info("test.py")
        
        # Verify file info
        assert file_info is not None
        assert file_info["language"] == "python"
        assert "functions" in file_info
        assert file_info["functions"] == ["test"]


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
