"""
Tests for the base memory module.
"""
import os
import tempfile
import json
import shutil
import pytest
from pathlib import Path

# Add parent directory to path for importing
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from autodev.memory.base import BaseMemory


class TestMemory:
    """Test suite for the base Memory class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def memory(self, temp_dir):
        """Create a Memory instance for testing."""
        return BaseMemory(storage_path=temp_dir)
    
    def test_initialization(self, temp_dir):
        """Test that Memory initializes correctly."""
        memory = BaseMemory(storage_path=temp_dir)
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


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
