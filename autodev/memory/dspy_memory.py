"""
Memory management module using DSPy for optimizations.
"""
from typing import Dict, Any, List, Optional, Union
import os
import json
from pathlib import Path
from datetime import datetime
import dspy

from autodev.memory.base import BaseMemory as LegacyBaseMemory


class MemoryModule(LegacyBaseMemory):
    """Base DSPy module for memory management."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the memory module.
        
        Args:
            storage_path: Path to store the memory. If None, uses a default path.
        """
        super().__init__(storage_path)
        
        if storage_path is None:
            storage_path = str(Path.home() / ".autodev" / "memory")
        
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
    
    def _get_file_path(self, key: str) -> str:
        """Get the file path for a memory key."""
        return os.path.join(self.storage_path, f"{key}.json")
    
    def save(self, key: str, data: Any) -> None:
        """Save data to memory."""
        file_path = self._get_file_path(key)
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self, key: str) -> Any:
        """Load data from memory."""
        file_path = self._get_file_path(key)
        
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def delete(self, key: str) -> bool:
        """Delete data from memory."""
        file_path = self._get_file_path(key)
        
        if not os.path.exists(file_path):
            return False
        
        os.remove(file_path)
        return True
    
    def list_keys(self) -> List[str]:
        """List all keys in memory."""
        keys = []
        
        for file_name in os.listdir(self.storage_path):
            if file_name.endswith('.json'):
                keys.append(file_name[:-5])  # Remove .json extension
        
        return keys


class ContextMemory(MemoryModule):
    """DSPy module for handling context memory."""
    
    def __init__(self, storage_path: Optional[str] = None, max_entries: int = 20):
        """
        Initialize the context memory.
        
        Args:
            storage_path: Path to store the memory. If None, uses a default path.
            max_entries: Maximum number of context entries to keep
        """
        super().__init__(storage_path)
        self.max_entries = max_entries
        self.current_context_key = "current_context"
        
        # Initialize current context if it doesn't exist
        if not self.load(self.current_context_key):
            self.save(self.current_context_key, {
                "entries": [],
                "last_updated": datetime.now().isoformat()
            })
    
    def add_entry(self, entry_type: str, content: Any) -> None:
        """
        Add a new entry to the context memory.
        
        Args:
            entry_type: Type of entry (e.g., 'code', 'query', 'response')
            content: The content to add
        """
        context = self.load(self.current_context_key)
        
        # Create new entry
        new_entry = {
            "type": entry_type,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to entries and maintain max size
        context["entries"].append(new_entry)
        if len(context["entries"]) > self.max_entries:
            context["entries"] = context["entries"][-self.max_entries:]
        
        context["last_updated"] = datetime.now().isoformat()
        
        # Save updated context
        self.save(self.current_context_key, context)
    
    def get_entries(self, entry_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get entries from the context memory.
        
        Args:
            entry_type: Optional filter by entry type
            
        Returns:
            List of matching entries
        """
        context = self.load(self.current_context_key)
        
        if not context or "entries" not in context:
            return []
        
        if entry_type is None:
            return context["entries"]
        
        return [entry for entry in context["entries"] if entry["type"] == entry_type]
    
    def clear(self) -> None:
        """Clear the current context."""
        self.save(self.current_context_key, {
            "entries": [],
            "last_updated": datetime.now().isoformat()
        })
    
    def forward(self, entry_type: str, content: Any) -> Dict[str, Any]:
        """
        DSPy forward method to retrieve relevant context.
        
        Args:
            entry_type: Type of entry
            content: Content to find relevant context for
            
        Returns:
            Dict containing relevant context
        """
        entries = self.get_entries()
        
        # For now, just return the most recent entries
        # In a real implementation, this would use DSPy's retrieval capabilities
        recent_entries = entries[-5:] if entries else []
        
        return {"retrieval": recent_entries}


class ProjectMemory(MemoryModule):
    """DSPy module for handling project memory."""
    
    def __init__(self, project_id: str, storage_path: Optional[str] = None):
        """
        Initialize the project memory.
        
        Args:
            project_id: Unique identifier for the project
            storage_path: Path to store the memory. If None, uses a default path.
        """
        if storage_path is None:
            storage_path = str(Path.home() / ".autodev" / "memory" / "projects")
        
        super().__init__(storage_path)
        self.project_id = project_id
        self.project_key = f"project_{project_id}"
        
        # Initialize project if it doesn't exist
        if not self.load(self.project_key):
            self.save(self.project_key, {
                "id": project_id,
                "files": {},
                "components": [],
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            })
    
    def update_file_info(self, file_path: str, content: Optional[str] = None) -> None:
        """
        Update information about a file in the project.
        
        Args:
            file_path: Path to the file relative to project root
            content: Optional file content to analyze
        """
        project = self.load(self.project_key)
        
        if file_path not in project["files"]:
            project["files"][file_path] = {}
        
        file_info = project["files"][file_path]
        file_info["last_updated"] = datetime.now().isoformat()
        
        if content:
            # Use the forward method to extract metadata
            metadata = self.forward(self.project_id, file_path, content)
            
            # Update file info with extracted metadata
            for key, value in metadata["metadata"].items():
                file_info[key] = value
        
        project["last_updated"] = datetime.now().isoformat()
        self.save(self.project_key, project)
    
    def remove_file(self, file_path: str) -> None:
        """
        Remove a file from the project memory.
        
        Args:
            file_path: Path to the file relative to project root
        """
        project = self.load(self.project_key)
        
        if file_path in project["files"]:
            del project["files"][file_path]
            project["last_updated"] = datetime.now().isoformat()
            self.save(self.project_key, project)
    
    def add_component(self, name: str, description: str, file_paths: List[str]) -> None:
        """
        Add a component to the project memory.
        
        Args:
            name: Component name
            description: Component description
            file_paths: List of file paths that make up the component
        """
        project = self.load(self.project_key)
        
        component = {
            "name": name,
            "description": description,
            "file_paths": file_paths,
            "created_at": datetime.now().isoformat()
        }
        
        project["components"].append(component)
        project["last_updated"] = datetime.now().isoformat()
        self.save(self.project_key, project)
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get information about a file in the project.
        
        Args:
            file_path: Path to the file relative to project root
            
        Returns:
            File information or empty dict if not found
        """
        project = self.load(self.project_key)
        return project["files"].get(file_path, {})
    
    def get_all_files(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all files in the project.
        
        Returns:
            Dictionary of file paths to file information
        """
        project = self.load(self.project_key)
        return project["files"]
    
    def get_components(self) -> List[Dict[str, Any]]:
        """
        Get all components in the project.
        
        Returns:
            List of components
        """
        project = self.load(self.project_key)
        return project["components"]
    
    def forward(self, project_id: str, file_path: str, content: str) -> Dict[str, Any]:
        """
        DSPy forward method to extract metadata from file content.
        
        Args:
            project_id: Project identifier
            file_path: Path to the file
            content: File content
            
        Returns:
            Dict containing extracted metadata
        """
        # Basic metadata extraction (will be enhanced with DSPy)
        metadata = {}
        
        # Language detection
        ext = os.path.splitext(file_path)[1].lower()
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.html': 'html',
            '.css': 'css',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php'
        }
        metadata["language"] = lang_map.get(ext, 'unknown')
        metadata["size"] = len(content)
        metadata["line_count"] = content.count("\n") + 1
        
        # For Python files, extract simple metrics
        if metadata["language"] == "python":
            metadata["imports"] = self._extract_python_imports(content)
            metadata["functions"] = self._extract_python_functions(content)
            metadata["classes"] = self._extract_python_classes(content)
        
        return {"metadata": metadata}
    
    def _extract_python_imports(self, content: str) -> List[str]:
        """Extract Python imports from content."""
        imports = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                imports.append(line)
        
        return imports
    
    def _extract_python_functions(self, content: str) -> List[str]:
        """Extract Python function names from content (basic version)."""
        functions = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('def '):
                func_name = line[4:].split('(')[0].strip()
                functions.append(func_name)
        
        return functions
    
    def _extract_python_classes(self, content: str) -> List[str]:
        """Extract Python class names from content (basic version)."""
        classes = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('class '):
                class_name = line[6:].split('(')[0].split(':')[0].strip()
                classes.append(class_name)
        
        return classes


class MemoryManager:
    """Manager class to coordinate different memory modules."""
    
    def __init__(self, 
                 project_id: Optional[str] = None,
                 context_storage_path: Optional[str] = None,
                 project_storage_path: Optional[str] = None):
        """
        Initialize the memory manager.
        
        Args:
            project_id: Optional project ID
            context_storage_path: Optional path for context memory
            project_storage_path: Optional path for project memory
        """
        self.context_memory = ContextMemory(storage_path=context_storage_path)
        self.project_storage_path = project_storage_path
        
        if project_id:
            self.project_memory = ProjectMemory(
                project_id=project_id,
                storage_path=project_storage_path
            )
        else:
            self.project_memory = None
    
    def set_project(self, project_id: str) -> None:
        """
        Set or change the current project.
        
        Args:
            project_id: Project ID
        """
        if self.project_memory is None or self.project_memory.project_id != project_id:
            self.project_memory = ProjectMemory(
                project_id=project_id,
                storage_path=self.project_storage_path
            )
    
    def add_context(self, entry_type: str, content: Any) -> None:
        """
        Add an entry to context memory.
        
        Args:
            entry_type: Type of entry
            content: Entry content
        """
        self.context_memory.add_entry(entry_type, content)
    
    def get_context(self, entry_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get context entries.
        
        Args:
            entry_type: Optional type filter
            
        Returns:
            List of context entries
        """
        return self.context_memory.get_entries(entry_type)
    
    def update_file(self, file_path: str, content: Optional[str] = None) -> None:
        """
        Update file information in project memory.
        
        Args:
            file_path: File path
            content: Optional file content
        """
        if self.project_memory:
            self.project_memory.update_file_info(file_path, content)
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get file information from project memory.
        
        Args:
            file_path: File path
            
        Returns:
            File information
        """
        if self.project_memory:
            return self.project_memory.get_file_info(file_path)
        return {}
