"""
Project memory for storing long-term information about code projects.
"""
from typing import Dict, Any, List, Optional, Set
import os
from pathlib import Path
from datetime import datetime
from .base import Memory


class ProjectMemory(Memory):
    """Memory for storing long-term information about code projects."""
    
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
                "structure": {},
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
            # Basic content analysis
            file_info["language"] = self._detect_language(file_path)
            file_info["size"] = len(content)
            file_info["line_count"] = content.count("\n") + 1
            
            # Extract imports, functions, classes, etc. (basic version)
            if file_info["language"] == "python":
                file_info["imports"] = self._extract_python_imports(content)
                file_info["functions"] = self._extract_python_functions(content)
                file_info["classes"] = self._extract_python_classes(content)
        
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
    
    def _detect_language(self, file_path: str) -> str:
        """
        Detect the programming language of a file based on extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Detected language or 'unknown'
        """
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
        
        return lang_map.get(ext, 'unknown')
    
    def _extract_python_imports(self, content: str) -> List[str]:
        """
        Extract Python imports from content.
        
        Args:
            content: File content
            
        Returns:
            List of imports
        """
        imports = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                imports.append(line)
        
        return imports
    
    def _extract_python_functions(self, content: str) -> List[str]:
        """
        Extract Python function names from content (basic version).
        
        Args:
            content: File content
            
        Returns:
            List of function names
        """
        functions = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('def '):
                func_name = line[4:].split('(')[0].strip()
                functions.append(func_name)
        
        return functions
    
    def _extract_python_classes(self, content: str) -> List[str]:
        """
        Extract Python class names from content (basic version).
        
        Args:
            content: File content
            
        Returns:
            List of class names
        """
        classes = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('class '):
                class_name = line[6:].split('(')[0].split(':')[0].strip()
                classes.append(class_name)
        
        return classes
