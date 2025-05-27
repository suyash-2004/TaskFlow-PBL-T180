import logging
from datetime import datetime, timedelta
from typing import List, Dict, Set, Literal, Optional
from app.models import TaskInDB
from app.services.dependency_manager import DependencyManager

logger = logging.getLogger(__name__)

# Define supported scheduling algorithms
SchedulingAlgorithm = Literal["round_robin", "fcfs", "sjf", "ljf", "priority"]

class TaskScheduler:
    def __init__(self, 
                 tasks: List[TaskInDB], 
                 start_time: datetime, 
                 end_time: datetime, 
                 dependency_manager: Optional[DependencyManager] = None,
                 algorithm: SchedulingAlgorithm = "round_robin"):
        """
        Initialize the TaskScheduler.
        
        Args:
            tasks: List of tasks to schedule
            start_time: Start time of the scheduling window
            end_time: End time of the scheduling window
            dependency_manager: Optional dependency manager to use for dependency checks
            algorithm: Scheduling algorithm to use (round_robin, fcfs, sjf, ljf, priority)
        """
        self.tasks = tasks
        self.start_time = start_time
        self.end_time = end_time
        self.scheduled_tasks: List[TaskInDB] = []
        self.dependency_manager = dependency_manager
        self.algorithm = algorithm
        
        # Create task dependency graph
        self.dependency_graph: Dict[str, List[str]] = {}
        self.dependent_tasks: Dict[str, List[str]] = {}
        
        for task in tasks:
            task_id = str(task.id)
            self.dependency_graph[task_id] = task.dependencies or []
            
            # Build reverse dependency map
            for dep_id in task.dependencies or []:
                if dep_id not in self.dependent_tasks:
                    self.dependent_tasks[dep_id] = []
                self.dependent_tasks[dep_id].append(task_id)
        
        # If a dependency manager was provided, use it to check for and resolve deadlocks
        if self.dependency_manager:
            # Register all tasks with the dependency manager
            self.dependency_manager.load_tasks(tasks)
            
            # Check for deadlocks before scheduling
            deadlocks = self.dependency_manager.detect_deadlocks()
            if deadlocks:
                logger.warning(f"Deadlocks detected before scheduling: {deadlocks}")
                # Resolve deadlocks
                for cycle in deadlocks:
                    resolved_task = self.dependency_manager.resolve_deadlock(cycle)
                    if resolved_task:
                        logger.info(f"Resolved deadlock by modifying task {resolved_task}")
                        
                        # Update our local dependency graph
                        if resolved_task in self.dependency_graph and resolved_task in self.dependency_manager.dependency_graph:
                            self.dependency_graph[resolved_task] = self.dependency_manager.dependency_graph[resolved_task].copy()
        
        logger.info(f"Initialized TaskScheduler with {len(tasks)} tasks using {algorithm} algorithm")
    
    def is_schedulable(self, task: TaskInDB, current_time: datetime) -> bool:
        """Check if a task is schedulable at the current time."""
        task_id = str(task.id)
        
        # If we have a dependency manager, use it to check if the task can start
        if self.dependency_manager:
            # Check if all dependencies are completed in the dependency manager
            dep_status = self.dependency_manager.get_task_dependency_status(task_id)
            if not all(status for _, status in dep_status.items()):
                return False
        else:
            # Fall back to the original implementation
            for dep_id in task.dependencies or []:
                dep_completed = False
                for scheduled_task in self.scheduled_tasks:
                    if str(scheduled_task.id) == dep_id and scheduled_task.scheduled_end_time <= current_time:
                        dep_completed = True
                        break
                if not dep_completed:
                    return False
        
        # Check if deadline is reachable
        if task.deadline:
            task_end_time = current_time + timedelta(minutes=task.duration)
            if task_end_time > task.deadline:
                return False
        
        return True
    
    def schedule(self) -> List[TaskInDB]:
        """
        Schedule tasks using the selected algorithm.
        
        Returns:
            List of scheduled tasks with updated scheduled_start_time and scheduled_end_time.
        """
        if self.algorithm == "round_robin":
            return self._schedule_round_robin()
        elif self.algorithm == "fcfs":
            return self._schedule_fcfs()
        elif self.algorithm == "sjf":
            return self._schedule_sjf()
        elif self.algorithm == "ljf":
            return self._schedule_ljf()
        elif self.algorithm == "priority":
            return self._schedule_priority()
        else:
            logger.warning(f"Unknown algorithm {self.algorithm}, falling back to round robin")
            return self._schedule_round_robin()

    def _schedule_round_robin(self) -> List[TaskInDB]:
        """
        Schedule tasks using a priority-based Round Robin algorithm with dependency resolution.
        
        Returns:
            List of scheduled tasks with updated scheduled_start_time and scheduled_end_time.
        """
        # Sort tasks by priority (highest first) and then by deadline (earliest first)
        sorted_tasks = sorted(
            self.tasks,
            key=lambda t: (-t.priority, t.deadline or datetime.max)
        )
        
        # Track unscheduled tasks
        unscheduled_tasks = sorted_tasks.copy()
        
        # Track completed dependencies
        completed_deps: Set[str] = set()
        
        # Current time pointer
        current_time = self.start_time
        
        # Continue until all tasks are scheduled or we've tried all tasks
        while unscheduled_tasks and current_time < self.end_time:
            # Find the next task that can be scheduled
            scheduled_task = None
            
            for i, task in enumerate(unscheduled_tasks):
                if self.is_schedulable(task, current_time):
                    scheduled_task = task
                    del unscheduled_tasks[i]
                    break
            
            if scheduled_task:
                # Schedule the task
                task_duration = timedelta(minutes=scheduled_task.duration)
                scheduled_task.scheduled_start_time = current_time
                scheduled_task.scheduled_end_time = current_time + task_duration
                
                # Update current time
                current_time = scheduled_task.scheduled_end_time
                
                # Add to scheduled tasks
                self.scheduled_tasks.append(scheduled_task)
                
                # Mark this task as completed for dependency tracking
                completed_deps.add(str(scheduled_task.id))
                
                # If we have a dependency manager, mark the task as "completed" for scheduling purposes
                if self.dependency_manager:
                    self.dependency_manager.mark_task_completed(str(scheduled_task.id))
                
                logger.info(f"Scheduled task '{scheduled_task.name}' from {scheduled_task.scheduled_start_time} to {scheduled_task.scheduled_end_time}")
            else:
                # If no task can be scheduled, move time forward by 15 minutes
                current_time += timedelta(minutes=15)
                logger.info(f"No schedulable tasks found, moving time to {current_time}")
        
        self._log_unscheduled_tasks(unscheduled_tasks)
        return self.scheduled_tasks
    
    def _schedule_fcfs(self) -> List[TaskInDB]:
        """
        Schedule tasks using First Come First Served algorithm (based on creation time).
        
        Returns:
            List of scheduled tasks with updated scheduled_start_time and scheduled_end_time.
        """
        # Sort tasks by creation time (earliest first)
        sorted_tasks = sorted(
            self.tasks,
            key=lambda t: t.created_at
        )
        
        # Track unscheduled tasks
        unscheduled_tasks = sorted_tasks.copy()
        
        # Current time pointer
        current_time = self.start_time
        
        # Continue until all tasks are scheduled or we've tried all tasks
        while unscheduled_tasks and current_time < self.end_time:
            # Find the next task that can be scheduled
            scheduled_task = None
            
            for i, task in enumerate(unscheduled_tasks):
                if self.is_schedulable(task, current_time):
                    scheduled_task = task
                    del unscheduled_tasks[i]
                    break
            
            if scheduled_task:
                # Schedule the task
                self._schedule_task(scheduled_task, current_time)
                # Update current time
                current_time = scheduled_task.scheduled_end_time
            else:
                # If no task can be scheduled, move time forward by 15 minutes
                current_time += timedelta(minutes=15)
                logger.info(f"No schedulable tasks found, moving time to {current_time}")
        
        self._log_unscheduled_tasks(unscheduled_tasks)
        return self.scheduled_tasks
    
    def _schedule_sjf(self) -> List[TaskInDB]:
        """
        Schedule tasks using Shortest Job First algorithm.
        
        Returns:
            List of scheduled tasks with updated scheduled_start_time and scheduled_end_time.
        """
        # Track unscheduled tasks
        unscheduled_tasks = self.tasks.copy()
        
        # Current time pointer
        current_time = self.start_time
        
        # Continue until all tasks are scheduled or we've tried all tasks
        while unscheduled_tasks and current_time < self.end_time:
            # Find schedulable tasks
            schedulable_tasks = []
            for task in unscheduled_tasks:
                if self.is_schedulable(task, current_time):
                    schedulable_tasks.append(task)
            
            if schedulable_tasks:
                # Find the shortest task
                shortest_task = min(schedulable_tasks, key=lambda t: t.duration)
                
                # Schedule the task
                self._schedule_task(shortest_task, current_time)
                
                # Update current time
                current_time = shortest_task.scheduled_end_time
                
                # Remove from unscheduled tasks
                unscheduled_tasks.remove(shortest_task)
            else:
                # If no task can be scheduled, move time forward by 15 minutes
                current_time += timedelta(minutes=15)
                logger.info(f"No schedulable tasks found, moving time to {current_time}")
        
        self._log_unscheduled_tasks(unscheduled_tasks)
        return self.scheduled_tasks
    
    def _schedule_ljf(self) -> List[TaskInDB]:
        """
        Schedule tasks using Longest Job First algorithm.
        
        Returns:
            List of scheduled tasks with updated scheduled_start_time and scheduled_end_time.
        """
        # Track unscheduled tasks
        unscheduled_tasks = self.tasks.copy()
        
        # Current time pointer
        current_time = self.start_time
        
        # Continue until all tasks are scheduled or we've tried all tasks
        while unscheduled_tasks and current_time < self.end_time:
            # Find schedulable tasks
            schedulable_tasks = []
            for task in unscheduled_tasks:
                if self.is_schedulable(task, current_time):
                    schedulable_tasks.append(task)
            
            if schedulable_tasks:
                # Find the longest task
                longest_task = max(schedulable_tasks, key=lambda t: t.duration)
                
                # Schedule the task
                self._schedule_task(longest_task, current_time)
                
                # Update current time
                current_time = longest_task.scheduled_end_time
                
                # Remove from unscheduled tasks
                unscheduled_tasks.remove(longest_task)
            else:
                # If no task can be scheduled, move time forward by 15 minutes
                current_time += timedelta(minutes=15)
                logger.info(f"No schedulable tasks found, moving time to {current_time}")
        
        self._log_unscheduled_tasks(unscheduled_tasks)
        return self.scheduled_tasks
    
    def _schedule_priority(self) -> List[TaskInDB]:
        """
        Schedule tasks purely based on priority (highest priority first).
        
        Returns:
            List of scheduled tasks with updated scheduled_start_time and scheduled_end_time.
        """
        # Sort tasks by priority (highest first)
        sorted_tasks = sorted(
            self.tasks,
            key=lambda t: -t.priority
        )
        
        # Track unscheduled tasks
        unscheduled_tasks = sorted_tasks.copy()
        
        # Current time pointer
        current_time = self.start_time
        
        # Continue until all tasks are scheduled or we've tried all tasks
        while unscheduled_tasks and current_time < self.end_time:
            # Find the next task that can be scheduled
            scheduled_task = None
            
            for i, task in enumerate(unscheduled_tasks):
                if self.is_schedulable(task, current_time):
                    scheduled_task = task
                    del unscheduled_tasks[i]
                    break
            
            if scheduled_task:
                # Schedule the task
                self._schedule_task(scheduled_task, current_time)
                
                # Update current time
                current_time = scheduled_task.scheduled_end_time
            else:
                # If no task can be scheduled, move time forward by 15 minutes
                current_time += timedelta(minutes=15)
                logger.info(f"No schedulable tasks found, moving time to {current_time}")
        
        self._log_unscheduled_tasks(unscheduled_tasks)
        return self.scheduled_tasks
    
    def _schedule_task(self, task: TaskInDB, current_time: datetime) -> None:
        """
        Helper method to schedule a single task and handle dependency management.
        
        Args:
            task: The task to schedule
            current_time: The current time to schedule from
        """
        # Calculate task duration
        task_duration = timedelta(minutes=task.duration)
        
        # Set scheduled times
        task.scheduled_start_time = current_time
        task.scheduled_end_time = current_time + task_duration
        
        # Add to scheduled tasks
        self.scheduled_tasks.append(task)
        
        # If we have a dependency manager, mark the task as "completed" for scheduling purposes
        if self.dependency_manager:
            self.dependency_manager.mark_task_completed(str(task.id))
        
        logger.info(f"Scheduled task '{task.name}' from {task.scheduled_start_time} to {task.scheduled_end_time}")
    
    def _log_unscheduled_tasks(self, unscheduled_tasks: List[TaskInDB]) -> None:
        """
        Log unscheduled tasks and check for deadlocks.
        
        Args:
            unscheduled_tasks: List of tasks that couldn't be scheduled
        """
        if unscheduled_tasks:
            logger.warning(f"Could not schedule {len(unscheduled_tasks)} tasks")
            for task in unscheduled_tasks:
                logger.warning(f"Unscheduled task: {task.name}")
            
            # Check for deadlocks if we have a dependency manager
            if self.dependency_manager and unscheduled_tasks:
                deadlocks = self.dependency_manager.detect_deadlocks()
                if deadlocks:
                    logger.warning(f"Deadlocks may have prevented scheduling: {deadlocks}") 
