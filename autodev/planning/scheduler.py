"""
Task scheduler module for prioritizing tasks based on dependencies and other factors.
"""

import logging
from typing import Dict, List, Set, Optional, Tuple, Callable, Any
from datetime import datetime, timedelta
import heapq

from autodev.planning.task import Task, TaskStatus, Priority
from autodev.planning.graph import TaskGraph

logger = logging.getLogger(__name__)


class TaskScheduler:
    """
    Scheduler for prioritizing tasks based on dependencies and other factors.
    
    This class is responsible for:
    - Calculating effective priorities for tasks based on dependencies
    - Generating optimized task schedules
    - Identifying bottlenecks in the task graph
    - Providing insights for better task management
    """
    
    def __init__(self, task_graph: TaskGraph):
        """
        Initialize the task scheduler.
        
        Args:
            task_graph: The task graph to schedule
        """
        self.task_graph = task_graph
        
        # Default weights for priority calculation
        self.priority_weights = {
            "base_priority": 1.0,  # Weight for the task's intrinsic priority
            "dependency_count": 0.5,  # Weight for the number of dependencies
            "dependent_count": 1.5,  # Weight for the number of dependents
            "path_depth": 2.0,  # Weight for the task's position on critical paths
            "effort": 0.8,  # Weight for the estimated effort
            "urgency": 1.2,  # Weight for time-based urgency factors
        }
    
    def calculate_effective_priorities(
        self,
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Calculate effective priorities for all tasks based on dependencies and other factors.
        
        Args:
            weights: Optional custom weights for the priority calculation
            
        Returns:
            Dictionary mapping task IDs to their effective priority values
        """
        if weights:
            # Update weights but keep defaults for missing keys
            for key, value in weights.items():
                if key in self.priority_weights:
                    self.priority_weights[key] = value
        
        effective_priorities = {}
        
        # Calculate critical path to identify key tasks
        try:
            critical_path_tasks = {task.id for task in self.task_graph.calculate_critical_path()}
        except Exception as e:
            logger.warning(f"Failed to calculate critical path: {e}")
            critical_path_tasks = set()
        
        # Calculate the maximum path depth for each task
        path_depths = self._calculate_path_depths()
        
        # Calculate effective priority for each task
        for task_id, task in self.task_graph.tasks.items():
            # Skip completed or cancelled tasks
            if task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
                effective_priorities[task_id] = 0.0
                continue
            
            # Base priority from task's intrinsic priority
            priority = task.priority.value * self.priority_weights["base_priority"]
            
            # Factor in the number of dependencies
            deps = self.task_graph.get_dependencies(task_id)
            if deps:
                priority += len(deps) * self.priority_weights["dependency_count"]
            
            # Factor in the number of dependents (more dependents = higher priority)
            dependents = self.task_graph.get_all_dependents(task_id)
            if dependents:
                priority += len(dependents) * self.priority_weights["dependent_count"]
            
            # Factor in path depth (longer path = higher priority)
            if task_id in path_depths:
                priority += path_depths[task_id] * self.priority_weights["path_depth"]
            
            # Bonus for critical path tasks
            if task_id in critical_path_tasks:
                priority *= 1.5
            
            # Factor in effort (higher effort might need earlier start)
            priority += task.estimated_effort * self.priority_weights["effort"]
            
            # Factor in urgency based on metadata if available
            if "deadline" in task.metadata:
                try:
                    deadline = datetime.fromisoformat(task.metadata["deadline"])
                    now = datetime.now()
                    days_until_deadline = (deadline - now).days
                    
                    # More urgent as deadline approaches
                    if days_until_deadline <= 0:
                        # Past deadline - highest urgency
                        urgency_factor = 5.0
                    elif days_until_deadline <= 1:
                        # Due today or tomorrow
                        urgency_factor = 3.0
                    elif days_until_deadline <= 3:
                        # Due within 3 days
                        urgency_factor = 2.0
                    elif days_until_deadline <= 7:
                        # Due within a week
                        urgency_factor = 1.5
                    else:
                        # Due later
                        urgency_factor = 1.0
                        
                    priority += urgency_factor * self.priority_weights["urgency"]
                except (ValueError, TypeError):
                    # Invalid deadline format - ignore
                    pass
            
            # Store the calculated priority
            effective_priorities[task_id] = priority
            
            # Update the task object
            task.set_effective_priority(priority)
        
        return effective_priorities
    
    def get_prioritized_tasks(self) -> List[Task]:
        """
        Get tasks sorted by their effective priority (highest first).
        
        Returns:
            List of tasks sorted by priority
        """
        # Make sure priorities are calculated
        self.calculate_effective_priorities()
        
        # Get all non-completed, non-cancelled tasks
        active_tasks = [
            task for task in self.task_graph.tasks.values()
            if task.status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)
        ]
        
        # Sort by effective priority (descending)
        return sorted(
            active_tasks,
            key=lambda t: t.effective_priority,
            reverse=True
        )
    
    def get_next_tasks(self, limit: int = 5) -> List[Task]:
        """
        Get the next tasks that should be worked on.
        
        This considers dependencies and only returns tasks that are not blocked.
        
        Args:
            limit: Maximum number of tasks to return
            
        Returns:
            List of next tasks to work on, sorted by priority
        """
        # Make sure priorities are calculated
        self.calculate_effective_priorities()
        
        # Get only tasks that are ready to work on (not blocked, not completed, not cancelled)
        ready_tasks = [
            task for task in self.task_graph.tasks.values()
            if task.status not in (TaskStatus.BLOCKED, TaskStatus.COMPLETED, TaskStatus.CANCELLED)
        ]
        
        # Sort by effective priority (descending)
        sorted_tasks = sorted(
            ready_tasks,
            key=lambda t: t.effective_priority,
            reverse=True
        )
        
        return sorted_tasks[:limit]
    
    def _calculate_path_depths(self) -> Dict[str, int]:
        """
        Calculate the maximum path depth for each task.
        
        A task's path depth is the length of the longest path from any root task to this task.
        Tasks on longer paths get higher priority because they have more potential for delays.
        
        Returns:
            Dictionary mapping task IDs to their maximum path depths
        """
        path_depths = {}
        
        # Get all root tasks (those with no dependencies)
        root_tasks = self.task_graph.get_root_tasks()
        
        # For each root task, calculate path depths for all tasks reachable from it
        for root_task in root_tasks:
            self._dfs_path_depth(root_task.id, 0, path_depths)
            
        return path_depths
    
    def _dfs_path_depth(
        self,
        task_id: str,
        current_depth: int,
        path_depths: Dict[str, int]
    ) -> None:
        """
        Recursively calculate path depths using depth-first search.
        
        Args:
            task_id: Current task ID
            current_depth: Current path depth
            path_depths: Dictionary to store maximum path depths
        """
        # Update maximum path depth for this task
        path_depths[task_id] = max(path_depths.get(task_id, 0), current_depth)
        
        # Process all dependent tasks
        for dependent_id in self.task_graph.get_dependents(task_id):
            self._dfs_path_depth(dependent_id, current_depth + 1, path_depths)
    
    def identify_bottlenecks(self, threshold: int = 3) -> List[Dict[str, Any]]:
        """
        Identify bottleneck tasks that may delay the project.
        
        Bottlenecks are tasks with many dependents and/or on the critical path.
        
        Args:
            threshold: Minimum number of dependents to consider a task a bottleneck
            
        Returns:
            List of bottleneck tasks with details about why they're bottlenecks
        """
        bottlenecks = []
        
        # Try to calculate the critical path
        try:
            critical_path = self.task_graph.calculate_critical_path()
            critical_path_ids = {task.id for task in critical_path}
        except Exception as e:
            logger.warning(f"Failed to calculate critical path: {e}")
            critical_path_ids = set()
        
        for task_id, task in self.task_graph.tasks.items():
            # Skip completed tasks
            if task.status == TaskStatus.COMPLETED:
                continue
                
            dependents = self.task_graph.get_all_dependents(task_id)
            
            is_bottleneck = False
            reasons = []
            
            # Criterion 1: Task has many dependents
            if len(dependents) >= threshold:
                is_bottleneck = True
                reasons.append(f"Blocks {len(dependents)} other tasks")
            
            # Criterion 2: Task is on the critical path
            if task_id in critical_path_ids:
                is_bottleneck = True
                reasons.append("On the critical path")
            
            # Criterion 3: Task is blocked and has dependents
            if task.status == TaskStatus.BLOCKED and dependents:
                is_bottleneck = True
                reasons.append(f"Currently blocked and has {len(dependents)} dependent tasks")
            
            if is_bottleneck:
                bottlenecks.append({
                    "task": task,
                    "dependents_count": len(dependents),
                    "reasons": reasons
                })
        
        # Sort bottlenecks by number of dependents (descending)
        bottlenecks.sort(key=lambda x: x["dependents_count"], reverse=True)
        
        return bottlenecks
    
    def generate_schedule(
        self,
        start_date: datetime = None,
        resources: int = 1
    ) -> Dict[str, Any]:
        """
        Generate a schedule for tasks based on dependencies and priorities.
        
        Args:
            start_date: Start date for the schedule (defaults to today)
            resources: Number of parallel resources available
            
        Returns:
            Dictionary with schedule details
        """
        if start_date is None:
            start_date = datetime.now()
        
        # Calculate effective priorities
        self.calculate_effective_priorities()
        
        # Track unscheduled tasks
        unscheduled = set(self.task_graph.tasks.keys())
        
        # Track when each resource becomes available
        resource_available = [start_date] * resources
        
        # Store task schedules
        schedule = {}
        
        # Track tasks that are ready to be scheduled
        ready_tasks = []
        
        # Initial ready tasks are those with no dependencies
        for task in self.task_graph.get_root_tasks():
            if task.status != TaskStatus.COMPLETED:
                # Use negative priority for min-heap (highest priority first)
                heapq.heappush(ready_tasks, (-task.effective_priority, task.id))
                
        # Schedule tasks until all are scheduled
        while unscheduled:
            # If no tasks are ready, there might be a dependency cycle
            if not ready_tasks:
                remaining = [self.task_graph.tasks[tid] for tid in unscheduled]
                logger.warning(f"Unable to schedule {len(remaining)} tasks due to dependencies")
                break
            
            # Get highest priority ready task
            _, task_id = heapq.heappop(ready_tasks)
            
            # Skip if already scheduled
            if task_id not in unscheduled:
                continue
                
            task = self.task_graph.tasks[task_id]
            
            # Find earliest available resource
            resource_idx = resource_available.index(min(resource_available))
            start_time = resource_available[resource_idx]
            
            # Adjust start time based on dependencies
            for dep_id in task.dependencies:
                if dep_id in schedule:
                    dep_end = schedule[dep_id]["end_time"]
                    if dep_end > start_time:
                        start_time = dep_end
            
            # Calculate end time
            hours_needed = task.estimated_effort  # Assuming effort is in hours
            end_time = start_time + timedelta(hours=hours_needed)
            
            # Update resource availability
            resource_available[resource_idx] = end_time
            
            # Add to schedule
            schedule[task_id] = {
                "task": task,
                "start_time": start_time,
                "end_time": end_time,
                "resource": resource_idx
            }
            
            # Mark as scheduled
            unscheduled.remove(task_id)
            
            # Add dependent tasks to ready list if all their dependencies are scheduled
            for dependent_id in self.task_graph.get_dependents(task_id):
                if dependent_id in unscheduled:
                    dependent_task = self.task_graph.tasks[dependent_id]
                    
                    # Check if all dependencies are scheduled
                    all_deps_scheduled = True
                    for dep_id in dependent_task.dependencies:
                        if dep_id in unscheduled:
                            all_deps_scheduled = False
                            break
                            
                    if all_deps_scheduled:
                        heapq.heappush(
                            ready_tasks,
                            (-dependent_task.effective_priority, dependent_id)
                        )
        
        # Calculate project metrics
        if schedule:
            project_start = min(item["start_time"] for item in schedule.values())
            project_end = max(item["end_time"] for item in schedule.values())
            project_duration = (project_end - project_start).total_seconds() / 3600  # in hours
        else:
            project_start = start_date
            project_end = start_date
            project_duration = 0
        
        return {
            "schedule": schedule,
            "project_start": project_start,
            "project_end": project_end,
            "project_duration": project_duration,
            "resources_used": resources,
            "unscheduled_tasks": len(unscheduled)
        }
    
    def get_paths_to_completion(self, task_id: str) -> List[List[str]]:
        """
        Get all paths from dependencies to the specified task.
        
        Args:
            task_id: Target task ID
            
        Returns:
            List of paths (each path is a list of task IDs)
        """
        if task_id not in self.task_graph.tasks:
            return []
            
        paths = []
        self._find_paths_to_task(task_id, [], set(), paths)
        return paths
    
    def _find_paths_to_task(
        self,
        target_id: str,
        current_path: List[str],
        visited: Set[str],
        all_paths: List[List[str]]
    ) -> None:
        """
        Recursively find all paths to a target task.
        
        Args:
            target_id: Target task ID
            current_path: Current path being built
            visited: Set of visited task IDs (to avoid cycles)
            all_paths: List to collect all found paths
        """
        if target_id in visited:
            return
            
        current_path.append(target_id)
        visited.add(target_id)
        
        # If this is a root task (no dependencies), we've found a path
        deps = self.task_graph.get_dependencies(target_id)
        if not deps:
            # Reverse the path to get it in order from root to target
            all_paths.append(list(reversed(current_path)))
        else:
            # Continue searching through dependencies
            for dep_id in deps:
                self._find_paths_to_task(dep_id, current_path.copy(), visited.copy(), all_paths)
    
    def estimate_completion_date(self, task_id: str) -> Optional[datetime]:
        """
        Estimate the completion date for a specific task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Estimated completion date or None if not estimable
        """
        # Generate a schedule starting from now
        schedule = self.generate_schedule()
        
        # Return the end time for this task if scheduled
        if task_id in schedule["schedule"]:
            return schedule["schedule"][task_id]["end_time"]
            
        return None
    
    def calculate_slack_time(self, task_id: str) -> Optional[float]:
        """
        Calculate slack time (float) for a task.
        
        Slack time is the amount of time a task can be delayed without
        delaying the overall project completion.
        
        Args:
            task_id: Task ID
            
        Returns:
            Slack time in hours or None if not calculable
        """
        if task_id not in self.task_graph.tasks:
            return None
            
        try:
            # We need to calculate earliest and latest start times
            earliest_start = self.task_graph._calculate_earliest_start_times()
            latest_start = self.task_graph._calculate_latest_start_times(earliest_start)
            
            # Slack is the difference between latest and earliest start times
            if task_id in earliest_start and task_id in latest_start:
                return latest_start[task_id] - earliest_start[task_id]
        except Exception as e:
            logger.warning(f"Failed to calculate slack time for task {task_id}: {e}")
            
        return None
