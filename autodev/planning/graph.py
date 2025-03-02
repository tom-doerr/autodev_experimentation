"""
Task graph module for managing task dependencies and relationships.
"""

import logging
from typing import Dict, List, Set, Optional, Tuple, Iterator, Any
from collections import deque

from autodev.planning.task import Task, TaskStatus

logger = logging.getLogger(__name__)


class CyclicDependencyError(Exception):
    """Exception raised when a cyclic dependency is detected."""
    pass


class TaskGraph:
    """
    A graph representation of tasks and their dependencies.
    
    This class is responsible for:
    - Storing all tasks in the system
    - Maintaining dependency relationships between tasks
    - Detecting cycles in the dependency graph
    - Providing methods to traverse tasks in topological order
    - Calculating metrics like critical paths and bottlenecks
    """
    
    def __init__(self):
        """Initialize an empty task graph."""
        self.tasks: Dict[str, Task] = {}
        self._adjacency_list: Dict[str, Set[str]] = {}  # task_id -> set of dependent task_ids
        self._reverse_adjacency: Dict[str, Set[str]] = {}  # task_id -> set of dependency task_ids
    
    def add_task(self, task: Task) -> None:
        """
        Add a task to the graph.
        
        Args:
            task: The task to add
            
        Raises:
            ValueError: If a task with the same ID already exists
        """
        if task.id in self.tasks:
            raise ValueError(f"Task with ID '{task.id}' already exists")
        
        self.tasks[task.id] = task
        self._adjacency_list[task.id] = set()
        self._reverse_adjacency[task.id] = set()
        
        # Add existing dependencies
        for dep_id in task.dependencies:
            self.add_dependency(task.id, dep_id)
    
    def remove_task(self, task_id: str) -> Optional[Task]:
        """
        Remove a task from the graph.
        
        Args:
            task_id: ID of the task to remove
            
        Returns:
            The removed task, or None if not found
        """
        task = self.tasks.pop(task_id, None)
        if task is None:
            return None
        
        # Remove this task from all dependency relationships
        for dep_task_id in self._reverse_adjacency.get(task_id, set()):
            self._adjacency_list[dep_task_id].discard(task_id)
            if task_id in self.tasks.get(dep_task_id, Task(id="", title="")).dependencies:
                self.tasks[dep_task_id].remove_dependency(task_id)
        
        # Remove this task from all dependent relationships
        for dependent_id in self._adjacency_list.get(task_id, set()):
            self._reverse_adjacency[dependent_id].discard(task_id)
            if dependent_id in self.tasks:
                self.tasks[dependent_id].dependencies.discard(task_id)
        
        # Clean up adjacency lists
        self._adjacency_list.pop(task_id, None)
        self._reverse_adjacency.pop(task_id, None)
        
        return task
    
    def add_dependency(self, task_id: str, dependency_id: str) -> bool:
        """
        Add a dependency relationship between two tasks.
        
        Args:
            task_id: ID of the dependent task
            dependency_id: ID of the dependency task
            
        Returns:
            True if the dependency was added, False otherwise
            
        Raises:
            ValueError: If either task doesn't exist
            CyclicDependencyError: If adding this dependency would create a cycle
        """
        if task_id == dependency_id:
            logger.warning(f"Cannot add self-dependency for task {task_id}")
            return False
        
        if task_id not in self.tasks:
            raise ValueError(f"Task with ID '{task_id}' not found")
        
        if dependency_id not in self.tasks:
            raise ValueError(f"Dependency task with ID '{dependency_id}' not found")
        
        # Check if this would create a cycle
        if self._would_create_cycle(task_id, dependency_id):
            raise CyclicDependencyError(
                f"Adding dependency from {task_id} to {dependency_id} would create a cycle"
            )
        
        # Update adjacency lists
        self._adjacency_list[dependency_id].add(task_id)
        self._reverse_adjacency[task_id].add(dependency_id)
        
        # Update task objects
        self.tasks[task_id].add_dependency(dependency_id)
        self.tasks[dependency_id].add_dependent(task_id)
        
        # Update task status if needed
        self._update_task_blocked_status(task_id)
        
        return True
    
    def remove_dependency(self, task_id: str, dependency_id: str) -> bool:
        """
        Remove a dependency relationship between two tasks.
        
        Args:
            task_id: ID of the dependent task
            dependency_id: ID of the dependency task
            
        Returns:
            True if the dependency was removed, False otherwise
        """
        if task_id not in self.tasks or dependency_id not in self.tasks:
            return False
        
        # Check if the dependency exists
        if dependency_id not in self._reverse_adjacency.get(task_id, set()):
            return False
        
        # Update adjacency lists
        self._adjacency_list[dependency_id].discard(task_id)
        self._reverse_adjacency[task_id].discard(dependency_id)
        
        # Update task objects
        self.tasks[task_id].remove_dependency(dependency_id)
        self.tasks[dependency_id].dependents.discard(task_id)
        
        # Update task status if needed
        self._update_task_blocked_status(task_id)
        
        return True
    
    def get_dependencies(self, task_id: str) -> Set[str]:
        """
        Get IDs of all tasks that the specified task depends on.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Set of dependency task IDs
        """
        if task_id not in self.tasks:
            return set()
        return self._reverse_adjacency.get(task_id, set()).copy()
    
    def get_dependents(self, task_id: str) -> Set[str]:
        """
        Get IDs of all tasks that depend on the specified task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Set of dependent task IDs
        """
        if task_id not in self.tasks:
            return set()
        return self._adjacency_list.get(task_id, set()).copy()
    
    def get_all_dependencies(self, task_id: str) -> Set[str]:
        """
        Get IDs of all tasks that the specified task directly or indirectly depends on.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Set of all dependency task IDs (transitive closure)
        """
        if task_id not in self.tasks:
            return set()
        
        all_deps = set()
        queue = deque([task_id])
        visited = set()
        
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
                
            visited.add(current)
            deps = self._reverse_adjacency.get(current, set())
            all_deps.update(deps)
            
            for dep in deps:
                if dep not in visited:
                    queue.append(dep)
        
        return all_deps
    
    def get_all_dependents(self, task_id: str) -> Set[str]:
        """
        Get IDs of all tasks that directly or indirectly depend on the specified task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Set of all dependent task IDs (transitive closure)
        """
        if task_id not in self.tasks:
            return set()
        
        all_dependents = set()
        queue = deque([task_id])
        visited = set()
        
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
                
            visited.add(current)
            dependents = self._adjacency_list.get(current, set())
            all_dependents.update(dependents)
            
            for dep in dependents:
                if dep not in visited:
                    queue.append(dep)
        
        return all_dependents
    
    def _would_create_cycle(self, task_id: str, dependency_id: str) -> bool:
        """
        Check if adding a dependency would create a cycle.
        
        Args:
            task_id: ID of the dependent task
            dependency_id: ID of the dependency task
            
        Returns:
            True if adding this dependency would create a cycle, False otherwise
        """
        # If we're creating a self-dependency, that's a cycle
        if task_id == dependency_id:
            return True
        
        # Check for transitive dependency cycles
        all_deps_of_task = self.get_all_dependencies(task_id)
        if dependency_id in all_deps_of_task:
            # We already depend on this task (directly or indirectly)
            return False
        
        # Check if the dependency already depends on the task (directly or indirectly)
        # This would create a cycle like: task -> ... -> dependency -> task
        all_deps_of_dependency = self.get_all_dependencies(dependency_id)
        if task_id in all_deps_of_dependency:
            return True
            
        # Additional check for cycles through transitive dependents
        all_dependents_of_dependency = self.get_all_dependents(dependency_id)
        for dependent_id in all_dependents_of_dependency:
            # If any task that depends on the dependency also depends on the task,
            # this would create a cycle
            if dependent_id in all_deps_of_task:
                return True
                
        return False
    
    def _update_task_blocked_status(self, task_id: str) -> None:
        """
        Update a task's blocked status based on its dependencies.
        
        Args:
            task_id: ID of the task to update
        """
        if task_id not in self.tasks:
            return
            
        task = self.tasks[task_id]
        
        # Don't change status of completed or cancelled tasks
        if task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            return
            
        # Check if any dependencies are not completed
        for dep_id in task.dependencies:
            if dep_id in self.tasks and self.tasks[dep_id].status != TaskStatus.COMPLETED:
                task.update_status(TaskStatus.BLOCKED)
                return
                
        # If we got here, no blocking dependencies
        if task.status == TaskStatus.BLOCKED:
            task.update_status(TaskStatus.NOT_STARTED)
    
    def get_root_tasks(self) -> List[Task]:
        """
        Get all tasks that have no dependencies.
        
        Returns:
            List of tasks without dependencies
        """
        return [
            task for task_id, task in self.tasks.items() 
            if not self._reverse_adjacency.get(task_id, set())
        ]
    
    def get_leaf_tasks(self) -> List[Task]:
        """
        Get all tasks that have no dependents.
        
        Returns:
            List of tasks with no dependents
        """
        return [
            task for task_id, task in self.tasks.items() 
            if not self._adjacency_list.get(task_id, set())
        ]
    
    def topological_sort(self) -> List[Task]:
        """
        Sort tasks in topological order (dependencies first).
        
        Returns:
            List of tasks in topological order
            
        Raises:
            CyclicDependencyError: If the graph contains a cycle
        """
        # Use Kahn's algorithm for topological sorting
        result = []
        in_degree = {node: 0 for node in self.tasks}
        
        # Calculate in-degree for each node
        for node in self.tasks:
            for dependent in self._adjacency_list.get(node, set()):
                in_degree[dependent] += 1
        
        # Start with nodes that have no dependencies
        queue = deque([node for node, degree in in_degree.items() if degree == 0])
        
        while queue:
            node = queue.popleft()
            result.append(self.tasks[node])
            
            for dependent in self._adjacency_list.get(node, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # If we couldn't process all nodes, there's a cycle
        if len(result) != len(self.tasks):
            raise CyclicDependencyError("Task graph contains a cycle")
            
        return result
    
    def calculate_critical_path(self) -> List[Task]:
        """
        Calculate the critical path through the task graph.
        
        The critical path is the sequence of tasks with the longest total duration,
        which determines the minimum time needed to complete the entire project.
        
        Returns:
            List of tasks on the critical path, in order from start to end
        """
        if not self.tasks:
            return []
            
        # Get a topological ordering of tasks
        try:
            task_order = self.topological_sort()
        except CyclicDependencyError:
            logger.warning("Cannot calculate critical path for graph with cycles")
            return []
        
        # Calculate earliest start times for each task
        earliest_start = self._calculate_earliest_start_times()
        
        # Find the project completion time (maximum earliest finish time)
        max_completion_time = 0.0
        for task_id, task in self.tasks.items():
            finish_time = earliest_start[task_id] + task.estimated_effort
            max_completion_time = max(max_completion_time, finish_time)
        
        # Calculate latest start times
        latest_start = self._calculate_latest_start_times(max_completion_time)
        
        # Tasks on the critical path have zero slack (difference between latest and earliest start)
        critical_tasks = []
        task_order = self.topological_sort()
        for task in task_order:
            # Calculate slack for this task
            slack = latest_start[task.id] - earliest_start[task.id]
            # Tasks with zero (or nearly zero) slack are on the critical path
            if abs(slack) < 1e-6:  # Use a small epsilon for floating point comparison
                critical_tasks.append(task)
        
        return critical_tasks
    
    def _calculate_earliest_start_times(self) -> Dict[str, float]:
        """
        Calculate the earliest start time for each task.
        
        Returns:
            Dictionary mapping task IDs to their earliest possible start times
        """
        if not self.tasks:
            return {}
            
        # Get a topological ordering of tasks
        try:
            task_order = self.topological_sort()
        except CyclicDependencyError:
            logger.warning("Cannot calculate earliest start times for graph with cycles")
            return {}
        
        # Initialize earliest start times to 0
        earliest_start = {task_id: 0.0 for task_id in self.tasks}
        
        # Forward pass - Calculate earliest start times
        for task in task_order:
            # Task's earliest start is the max of all dependencies' earliest finish times
            for dep_id in self._reverse_adjacency.get(task.id, set()):
                dep_task = self.tasks[dep_id]
                earliest_start[task.id] = max(
                    earliest_start[task.id],
                    earliest_start[dep_id] + dep_task.estimated_effort
                )
                
        return earliest_start
        
    def _calculate_latest_start_times(self, max_completion_time: Optional[float] = None) -> Dict[str, float]:
        """
        Calculate the latest start time for each task that won't delay the project.
        
        Args:
            max_completion_time: The project completion time, if known. If None, 
                                it will be calculated from earliest start times.
                                
        Returns:
            Dictionary mapping task IDs to their latest possible start times
        """
        if not self.tasks:
            return {}
            
        # Get a topological ordering of tasks
        try:
            task_order = self.topological_sort()
        except CyclicDependencyError:
            logger.warning("Cannot calculate latest start times for graph with cycles")
            return {}
            
        # If max_completion_time is not provided, calculate it
        if max_completion_time is None:
            earliest_start = self._calculate_earliest_start_times()
            max_completion_time = 0.0
            for task_id, task in self.tasks.items():
                finish_time = earliest_start[task_id] + task.estimated_effort
                max_completion_time = max(max_completion_time, finish_time)
        
        # Initialize latest start times to project end time
        latest_start = {task_id: max_completion_time for task_id in self.tasks}
        
        # Backwards pass - Calculate latest start times
        for task in reversed(task_order):
            # For leaf tasks, latest start is project end minus task duration
            if not self._adjacency_list.get(task.id, set()):
                latest_start[task.id] = max_completion_time - task.estimated_effort
            
            # For other tasks, latest start is min of all dependents' latest starts minus task duration
            for dependent_id in self._adjacency_list.get(task.id, set()):
                latest_start[task.id] = min(
                    latest_start[task.id],
                    latest_start[dependent_id] - task.estimated_effort
                )
                
        return latest_start
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the task graph to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the task graph
        """
        return {
            "tasks": {task_id: task.to_dict() for task_id, task in self.tasks.items()},
            "dependencies": {
                task_id: list(deps) for task_id, deps in self._reverse_adjacency.items() if deps
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskGraph':
        """
        Create a task graph from a dictionary representation.
        
        Args:
            data: Dictionary representation of a task graph
            
        Returns:
            TaskGraph instance
        """
        graph = cls()
        
        # Add tasks first
        for task_id, task_data in data.get("tasks", {}).items():
            task = Task.from_dict(task_data)
            graph.add_task(task)
        
        # Then add dependencies
        for task_id, deps in data.get("dependencies", {}).items():
            for dep_id in deps:
                try:
                    graph.add_dependency(task_id, dep_id)
                except (ValueError, CyclicDependencyError) as e:
                    logger.warning(f"Failed to add dependency from {task_id} to {dep_id}: {e}")
        
        return graph
