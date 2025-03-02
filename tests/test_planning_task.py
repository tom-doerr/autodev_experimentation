"""
Tests for the Task class in the planning module.
"""

import pytest
from datetime import datetime, timedelta

from autodev.planning.task import Task, TaskStatus, Priority


def test_task_initialization():
    """Test that a task initializes with correct values."""
    task = Task(
        id="task-1",
        title="Test Task",
        description="This is a test task",
        status=TaskStatus.NOT_STARTED,
        priority=Priority.MEDIUM,
        estimated_effort=2.5,
        dependencies={"task-2", "task-3"},
        tags=["test", "planning"],
        metadata={"owner": "test-user"}
    )
    
    assert task.id == "task-1"
    assert task.title == "Test Task"
    assert task.description == "This is a test task"
    assert task.status == TaskStatus.NOT_STARTED
    assert task.priority == Priority.MEDIUM
    assert task.estimated_effort == 2.5
    assert task.dependencies == {"task-2", "task-3"}
    assert task.dependents == set()
    assert task.tags == ["test", "planning"]
    assert task.metadata == {"owner": "test-user"}
    assert isinstance(task.created_at, datetime)
    assert isinstance(task.updated_at, datetime)
    assert task.effective_priority == Priority.MEDIUM.value


def test_task_default_values():
    """Test that a task uses correct default values."""
    task = Task(id="task-1", title="Test Task")
    
    assert task.description == ""
    assert task.status == TaskStatus.NOT_STARTED
    assert task.priority == Priority.MEDIUM
    assert task.estimated_effort == 1.0
    assert task.dependencies == set()
    assert task.tags == []
    assert task.metadata == {}


def test_task_update_status():
    """Test updating a task's status."""
    task = Task(id="task-1", title="Test Task")
    original_updated_at = task.updated_at
    
    # Wait a moment to ensure timestamps differ
    import time
    time.sleep(0.01)
    
    task.update_status(TaskStatus.IN_PROGRESS)
    
    assert task.status == TaskStatus.IN_PROGRESS
    assert task.updated_at > original_updated_at


def test_task_dependencies_management():
    """Test adding and removing dependencies."""
    task = Task(id="task-1", title="Test Task")
    
    task.add_dependency("task-2")
    assert "task-2" in task.dependencies
    
    task.add_dependency("task-3")
    assert "task-3" in task.dependencies
    
    task.remove_dependency("task-2")
    assert "task-2" not in task.dependencies
    assert "task-3" in task.dependencies
    
    # Test that we can't add self as dependency
    task.add_dependency("task-1")
    assert "task-1" not in task.dependencies


def test_task_effective_priority():
    """Test effective priority calculation."""
    task = Task(id="task-1", title="Test Task", priority=Priority.MEDIUM)
    
    # Default is base priority
    assert task.effective_priority == Priority.MEDIUM.value
    
    # Set a different effective priority
    task.set_effective_priority(8.5)
    assert task.effective_priority == 8.5


def test_task_to_dict():
    """Test converting a task to a dictionary."""
    task = Task(
        id="task-1",
        title="Test Task",
        description="Description",
        status=TaskStatus.IN_PROGRESS,
        priority=Priority.HIGH,
        estimated_effort=3.0,
        dependencies={"task-2"},
        tags=["test"],
        metadata={"key": "value"}
    )
    
    # Add a dependent
    task.add_dependent("task-3")
    
    # Set effective priority
    task.set_effective_priority(7.5)
    
    task_dict = task.to_dict()
    
    assert task_dict["id"] == "task-1"
    assert task_dict["title"] == "Test Task"
    assert task_dict["description"] == "Description"
    assert task_dict["status"] == "IN_PROGRESS"
    assert task_dict["priority"] == "HIGH"
    assert task_dict["effective_priority"] == 7.5
    assert task_dict["estimated_effort"] == 3.0
    assert task_dict["dependencies"] == ["task-2"]
    assert task_dict["dependents"] == ["task-3"]
    assert task_dict["tags"] == ["test"]
    assert task_dict["metadata"] == {"key": "value"}
    assert "created_at" in task_dict
    assert "updated_at" in task_dict


def test_task_from_dict():
    """Test creating a task from a dictionary."""
    now = datetime.now()
    now_str = now.isoformat()
    
    task_dict = {
        "id": "task-1",
        "title": "Test Task",
        "description": "Description",
        "status": "IN_PROGRESS",
        "priority": "HIGH",
        "effective_priority": 7.5,
        "estimated_effort": 3.0,
        "dependencies": ["task-2"],
        "dependents": ["task-3"],
        "created_at": now_str,
        "updated_at": now_str,
        "tags": ["test"],
        "metadata": {"key": "value"}
    }
    
    task = Task.from_dict(task_dict)
    
    assert task.id == "task-1"
    assert task.title == "Test Task"
    assert task.description == "Description"
    assert task.status == TaskStatus.IN_PROGRESS
    assert task.priority == Priority.HIGH
    assert task.effective_priority == 7.5
    assert task.estimated_effort == 3.0
    assert task.dependencies == {"task-2"}
    assert task.dependents == {"task-3"}
    assert task.tags == ["test"]
    assert task.metadata == {"key": "value"}
    
    # Check that datetime parsing worked
    assert isinstance(task.created_at, datetime)
    assert isinstance(task.updated_at, datetime)
    assert task.created_at.isoformat() == now_str
    assert task.updated_at.isoformat() == now_str
