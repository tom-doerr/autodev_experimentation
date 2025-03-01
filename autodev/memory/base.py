"""
Base memory system for storing and retrieving information.
"""
from typing import Dict, Any, List, Optional
import json
import os
from pathlib import Path


class BaseMemory:
    """Base memory class for storing and retrieving data."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """Initialize the memory with a storage path.
        
        Args:
            storage_path: Path to the storage directory. If None, 
                          uses ~/.autodev/memory/
        """
        if storage_path is None:
            # Use default location in user's home directory
            storage_path = os.path.expanduser("~/.autodev/memory/")
        
        # Create directory if it doesn't exist
        os.makedirs(storage_path, exist_ok=True)
        
        self.storage_path = storage_path
    
    def save(self, key: str, data: Any) -> None:
        """
        Save data to memory.
        
        Args:
            key: Unique identifier for the data
            data: The data to save (must be JSON serializable)
        """
        file_path = self._get_file_path(key)
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self, key: str) -> Any:
        """
        Load data from memory.
        
        Args:
            key: Unique identifier for the data
            
        Returns:
            The loaded data, or None if not found
        """
        file_path = self._get_file_path(key)
        
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def delete(self, key: str) -> bool:
        """
        Delete data from memory.
        
        Args:
            key: Unique identifier for the data
            
        Returns:
            True if successfully deleted, False otherwise
        """
        file_path = self._get_file_path(key)
        
        if not os.path.exists(file_path):
            return False
        
        os.remove(file_path)
        return True
    
    def list_keys(self) -> List[str]:
        """
        List all keys in memory.
        
        Returns:
            List of keys
        """
        keys = []
        
        for file_name in os.listdir(self.storage_path):
            if file_name.endswith('.json'):
                keys.append(file_name[:-5])  # Remove .json extension
        
        return keys
    
    def _get_file_path(self, key: str) -> str:
        """
        Get the file path for a key.
        
        Args:
            key: Memory key
            
        Returns:
            File path
        """
        return os.path.join(self.storage_path, f"{key}.json")
