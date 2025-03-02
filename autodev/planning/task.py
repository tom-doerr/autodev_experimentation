"""
Task module for representing individual tasks with their properties and relationships.
"""

from enum import Enum, auto
from datetime import datetime
from typing import List, Dict, Any, Optional, Set


class TaskStatus(Enum):
    """Status of a task in its lifecycle."""
    NOT_STARTED = auto()
    IN_PROGRESS = auto()
    BLOCKED = auto()
    COMPLETED = auto()
    CANCELLED = auto()


class Priority(Enum):
    """Priority levels for tasks."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class Task:
    """
    Represents a task with dependencies and prioritization information.
    
    Attributes:
        id: Unique identifier for the task
        title: Short descriptive title
        description: Detailed description of the work required
        status: Current status of the task
        priority: Base priority level (independent of dependencies)
        estimated_effort: Estimated effort in hours
        dependencies: IDs of tasks that must be completed before this task
        dependents: IDs of tasks that depend on this task
        created_at: Creation timestamp
        updated_at: Last update timestamp
        tags: List of tags for categorization
        metadata: Additional task-specific data
    """
    
    def __init__(
        self,
        id: str,
        title: str,
        description: str = "",
        status: TaskStatus = TaskStatus.NOT_STARTED,
        priority: Priority = Priority.MEDIUM,
        estimated_effort: float = 1.0,
        dependencies: Optional[Set[str]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a new Task.
        
        Args:
            id: Unique identifier for the task
            title: Short descriptive title
            description: Detailed description of the work required
            status: Current status of the task
            priority: Base priority level
            estimated_effort: Estimated effort in hours
            dependencies: IDs of tasks that must be completed before this task
            tags: List of tags for categorization
            metadata: Additional task-specific data
        """
        self.id = id
        self.title = title
        self.description = description
        self.status = status
        self.priority = priority
        self.estimated_effort = estimated_effort
        self.dependencies = dependencies or set()
        self.dependents = set()  # Will be populated by the TaskGraph
        self.tags = tags or []
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.updated_at = self.created_at
        
        # Dynamic priority calculated based on dependencies
        self._effective_priority = None
        
    def update_status(self, status: TaskStatus) -> None:
        """
        Update the status of the task.
        
        Args:
            status: New status to set
        """
        self.status = status
        self.updated_at = datetime.now()
    
    def add_dependency(self, task_id: str) -> None:
        """
        Add a dependency to this task.
        
        Args:
            task_id: ID of the task this task depends on
        """
        if task_id != self.id:  # Prevent self-dependency
            self.dependencies.add(task_id)
            self.updated_at = datetime.now()
    
    def remove_dependency(self, task_id: str) -> None:
        """
        Remove a dependency from this task.
        
        Args:
            task_id: ID of the task to remove as a dependency
        """
        if task_id in self.dependencies:
            self.dependencies.remove(task_id)
            self.updated_at = datetime.now()
    
    def add_dependent(self, task_id: str) -> None:
        """
        Add a dependent task to this task.
        
        Args:
            task_id: ID of the task that depends on this task
        """
        if task_id != self.id:  # Prevent self-dependency
            self.dependents.add(task_id)
            self.updated_at = datetime.now()
    
    def is_blocked(self) -> bool:
        """
        Check if this task is blocked by dependencies.
        
        Returns:
            True if any dependencies are not completed, False otherwise
        """
        return self.status == TaskStatus.BLOCKED
    
    def set_effective_priority(self, priority_value: float) -> None:
        """
        Set the calculated effective priority.
        
        Args:
            priority_value: Calculated priority value
        """
        self._effective_priority = priority_value
    
    @property
    def effective_priority(self) -> float:
        """
        Get the effective priority, which is calculated based on dependencies.
        Returns the base priority if effective priority hasn't been calculated.
        
        Returns:
            Effective priority value
        """
        if self._effective_priority is not None:
            return self._effective_priority
        return self.priority.value
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the task to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the task
        """
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.name,
            "priority": self.priority.name,
            "effective_priority": self.effective_priority,
            "estimated_effort": self.estimated_effort,
            "dependencies": list(self.dependencies),
            "dependents": list(self.dependents),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """
        Create a task from a dictionary representation.
        
        Args:
            data: Dictionary representation of a task
            
        Returns:
            Task instance
        """
        task = cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            status=TaskStatus[data["status"]] if "status" in data else TaskStatus.NOT_STARTED,
            priority=Priority[data["priority"]] if "priority" in data else Priority.MEDIUM,
            estimated_effort=data.get("estimated_effort", 1.0),
            dependencies=set(data.get("dependencies", [])),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )
        
        # Set additional properties
        if "dependents" in data:
            task.dependents = set(data["dependents"])
        
        if "effective_priority" in data and isinstance(data["effective_priority"], (int, float)):
            task._effective_priority = data["effective_priority"]
            
        # Parse dates if available
        if "created_at" in data:
            try:
                task.created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                pass
                
        if "updated_at" in data:
            try:
                task.updated_at = datetime.fromisoformat(data["updated_at"])
            except (ValueError, TypeError):
                pass
                
        return task
