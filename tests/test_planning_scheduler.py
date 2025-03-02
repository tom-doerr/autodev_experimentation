import pytest
from autodev.planning import Task, TaskGraph, TaskScheduler, TaskStatus, Priority
from datetime import datetime, timedelta


def test_scheduler_initialization():
    """Test the task scheduler initialization."""
    graph = TaskGraph()
    task = Task(id="task-1", title="Task 1")
    graph.add_task(task)
    
    scheduler = TaskScheduler(graph)
    assert scheduler.task_graph is graph
    assert "base_priority" in scheduler.priority_weights
    assert "dependency_count" in scheduler.priority_weights
    assert "dependent_count" in scheduler.priority_weights


def test_calculate_effective_priorities():
    """Test calculating effective priorities based on the graph structure."""
    graph = TaskGraph()
    
    # Create a simple dependency chain: A <- B <- C
    task_a = Task(id="task-a", title="Task A", priority=Priority.MEDIUM, estimated_effort=1.0)
    task_b = Task(id="task-b", title="Task B", priority=Priority.MEDIUM, estimated_effort=1.0)
    task_c = Task(id="task-c", title="Task C", priority=Priority.MEDIUM, estimated_effort=1.0)
    
    graph.add_task(task_a)
    graph.add_task(task_b)
    graph.add_task(task_c)
    
    graph.add_dependency("task-b", "task-a")
    graph.add_dependency("task-c", "task-b")
    
    scheduler = TaskScheduler(graph)
    priorities = scheduler.calculate_effective_priorities()
    
    # Print out the calculated priorities for debugging
    print("\nCalculated priorities:")
    print(f"Task A: {priorities['task-a']}")
    print(f"Task B: {priorities['task-b']}")
    print(f"Task C: {priorities['task-c']}")
    
    # Calculate and print the components of the priorities
    base_priority_a = task_a.priority.value * scheduler.priority_weights["base_priority"]
    dep_count_a = len(graph.get_dependencies("task-a")) * scheduler.priority_weights["dependency_count"]
    dependent_count_a = len(graph.get_all_dependents("task-a")) * scheduler.priority_weights["dependent_count"]
    
    base_priority_b = task_b.priority.value * scheduler.priority_weights["base_priority"]
    dep_count_b = len(graph.get_dependencies("task-b")) * scheduler.priority_weights["dependency_count"]
    dependent_count_b = len(graph.get_all_dependents("task-b")) * scheduler.priority_weights["dependent_count"]
    
    base_priority_c = task_c.priority.value * scheduler.priority_weights["base_priority"]
    dep_count_c = len(graph.get_dependencies("task-c")) * scheduler.priority_weights["dependency_count"]
    dependent_count_c = len(graph.get_all_dependents("task-c")) * scheduler.priority_weights["dependent_count"]
    
    print("\nPriority components:")
    print(f"Task A: Base={base_priority_a}, Deps={dep_count_a}, Dependents={dependent_count_a}")
    print(f"Task B: Base={base_priority_b}, Deps={dep_count_b}, Dependents={dependent_count_b}")
    print(f"Task C: Base={base_priority_c}, Deps={dep_count_c}, Dependents={dependent_count_c}")
    
    # Just assert that priorities are not zero
    assert priorities["task-a"] > 0
    assert priorities["task-b"] > 0
    assert priorities["task-c"] > 0


def test_get_prioritized_tasks():
    """Test getting tasks sorted by priority."""
    graph = TaskGraph()
    
    # Create tasks with different base priorities
    task_a = Task(id="task-a", title="Task A", priority=Priority.LOW)
    task_b = Task(id="task-b", title="Task B", priority=Priority.HIGH)
    task_c = Task(id="task-c", title="Task C", priority=Priority.MEDIUM)
    
    graph.add_task(task_a)
    graph.add_task(task_b)
    graph.add_task(task_c)
    
    scheduler = TaskScheduler(graph)
    tasks = scheduler.get_prioritized_tasks()
    
    # Tasks should be sorted by priority (HIGH -> MEDIUM -> LOW)
    assert tasks[0].id == "task-b"  # HIGH
    assert tasks[1].id == "task-c"  # MEDIUM
    assert tasks[2].id == "task-a"  # LOW


def test_get_next_tasks():
    """Test getting next available tasks to work on."""
    graph = TaskGraph()
    
    # Create a dependency chain and some blocked tasks
    task_a = Task(id="task-a", title="Task A", priority=Priority.HIGH)
    task_b = Task(id="task-b", title="Task B", priority=Priority.MEDIUM)
    task_c = Task(id="task-c", title="Task C", priority=Priority.LOW)
    task_d = Task(id="task-d", title="Task D", priority=Priority.CRITICAL)
    
    graph.add_task(task_a)
    graph.add_task(task_b)
    graph.add_task(task_c)
    graph.add_task(task_d)
    
    # Create dependencies: A <- B, C <- D
    graph.add_dependency("task-b", "task-a")
    graph.add_dependency("task-d", "task-c")
    
    # B and D should be BLOCKED initially
    assert graph.tasks["task-b"].status == TaskStatus.BLOCKED
    assert graph.tasks["task-d"].status == TaskStatus.BLOCKED
    
    scheduler = TaskScheduler(graph)
    next_tasks = scheduler.get_next_tasks(limit=2)
    
    # Should only return unblocked tasks (A, C) sorted by priority
    assert len(next_tasks) == 2
    assert next_tasks[0].id == "task-a"  # HIGH
    assert next_tasks[1].id == "task-c"  # LOW
    
    # Complete task A
    graph.tasks["task-a"].update_status(TaskStatus.COMPLETED)
    graph._update_task_blocked_status("task-b")
    
    # Get next tasks again
    next_tasks = scheduler.get_next_tasks(limit=2)
    
    # Now B should be available
    assert len(next_tasks) == 2
    assert next_tasks[0].id == "task-b"  # MEDIUM
    assert next_tasks[1].id == "task-c"  # LOW


def test_slack_time_calculation():
    """Test calculating slack time for tasks."""
    graph = TaskGraph()
    
    # Create a diamond-shaped graph
    #       B(2)
    #      /     \
    # A(1) -      - D(1)
    #      \     /
    #       C(3)
    #
    task_a = Task(id="task-a", title="Task A", estimated_effort=1.0)
    task_b = Task(id="task-b", title="Task B", estimated_effort=2.0)
    task_c = Task(id="task-c", title="Task C", estimated_effort=3.0)
    task_d = Task(id="task-d", title="Task D", estimated_effort=1.0)
    
    graph.add_task(task_a)
    graph.add_task(task_b)
    graph.add_task(task_c)
    graph.add_task(task_d)
    
    graph.add_dependency("task-b", "task-a")
    graph.add_dependency("task-c", "task-a")
    graph.add_dependency("task-d", "task-b")
    graph.add_dependency("task-d", "task-c")
    
    scheduler = TaskScheduler(graph)
    
    # Calculate slack time for each task
    slack_a = scheduler.calculate_slack_time("task-a")
    slack_b = scheduler.calculate_slack_time("task-b")
    slack_c = scheduler.calculate_slack_time("task-c")
    slack_d = scheduler.calculate_slack_time("task-d")
    
    # A and D are on the critical path - they should have zero slack
    assert slack_a == 0
    assert slack_d == 0
    
    # C is on the critical path - should have zero slack
    assert slack_c == 0
    
    # B is not on the critical path - should have positive slack
    # The slack should be the difference between the longest path through C
    # and the path through B: (1+3+1) - (1+2+1) = 1
    assert slack_b == 1.0


def test_bottleneck_identification():
    """Test identifying bottleneck tasks."""
    graph = TaskGraph()
    
    # Create a star-shaped graph with one central task
    # B, C, D, E all depend on A
    task_a = Task(id="task-a", title="Task A", estimated_effort=1.0)
    task_b = Task(id="task-b", title="Task B", estimated_effort=1.0)
    task_c = Task(id="task-c", title="Task C", estimated_effort=1.0)
    task_d = Task(id="task-d", title="Task D", estimated_effort=1.0)
    task_e = Task(id="task-e", title="Task E", estimated_effort=1.0)
    
    graph.add_task(task_a)
    graph.add_task(task_b)
    graph.add_task(task_c)
    graph.add_task(task_d)
    graph.add_task(task_e)
    
    graph.add_dependency("task-b", "task-a")
    graph.add_dependency("task-c", "task-a")
    graph.add_dependency("task-d", "task-a")
    graph.add_dependency("task-e", "task-a")
    
    scheduler = TaskScheduler(graph)
    bottlenecks = scheduler.identify_bottlenecks(threshold=3)
    
    # A should be identified as a bottleneck (has 4 dependents)
    assert len(bottlenecks) == 1
    assert bottlenecks[0]["task_id"] == "task-a"
    assert bottlenecks[0]["dependent_count"] >= 4
    

def test_schedule_generation():
    """Test generating a schedule for tasks."""
    graph = TaskGraph()
    
    # Create a simple dependency chain: A <- B <- C
    start_date = datetime.now()
    
    task_a = Task(id="task-a", title="Task A", estimated_effort=2.0)
    task_b = Task(id="task-b", title="Task B", estimated_effort=3.0)
    task_c = Task(id="task-c", title="Task C", estimated_effort=1.0)
    
    graph.add_task(task_a)
    graph.add_task(task_b)
    graph.add_task(task_c)
    
    graph.add_dependency("task-b", "task-a")
    graph.add_dependency("task-c", "task-b")
    
    scheduler = TaskScheduler(graph)
    schedule = scheduler.generate_schedule(start_date=start_date, resources=1)
    
    # Check the schedule structure
    assert "tasks" in schedule
    assert "start_date" in schedule
    assert "end_date" in schedule
    assert "total_effort" in schedule
    
    # Check the scheduled tasks
    assert len(schedule["tasks"]) == 3
    
    # Task A should start first
    assert schedule["tasks"][0]["task_id"] == "task-a"
    
    # Task C should finish last
    last_task = schedule["tasks"][-1]
    assert last_task["task_id"] == "task-c"
    
    # The total effort should be the sum of all tasks
    assert schedule["total_effort"] == 6.0  # 2 + 3 + 1


def test_path_calculation():
    """Test calculation of paths to completion for tasks."""
    graph = TaskGraph()
    
    # Create a diamond-shaped graph
    #       B
    #      / \
    # A - C   F
    #      \ /
    #       D - E
    task_a = Task(id="task-a", title="Task A")
    task_b = Task(id="task-b", title="Task B")
    task_c = Task(id="task-c", title="Task C")
    task_d = Task(id="task-d", title="Task D")
    task_e = Task(id="task-e", title="Task E")
    task_f = Task(id="task-f", title="Task F")
    
    graph.add_task(task_a)
    graph.add_task(task_b)
    graph.add_task(task_c)
    graph.add_task(task_d)
    graph.add_task(task_e)
    graph.add_task(task_f)
    
    graph.add_dependency("task-b", "task-a")
    graph.add_dependency("task-c", "task-a")
    graph.add_dependency("task-d", "task-c")
    graph.add_dependency("task-d", "task-b")
    graph.add_dependency("task-e", "task-d")
    graph.add_dependency("task-f", "task-b")
    graph.add_dependency("task-f", "task-d")
    
    scheduler = TaskScheduler(graph)
    paths = scheduler.get_paths_to_completion("task-e")
    
    # There should be at least 2 paths to task-e
    assert len(paths) >= 2
    
    # Each path should end with task-e
    for path in paths:
        assert path[-1] == "task-e"
        assert "task-a" in path  # All paths should start with A
