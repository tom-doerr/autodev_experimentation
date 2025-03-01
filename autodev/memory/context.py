"""
Context memory for storing short-term information about the current task.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base import Memory


class ContextMemory(Memory):
    """Memory for storing short-term context about the current task."""
    
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
