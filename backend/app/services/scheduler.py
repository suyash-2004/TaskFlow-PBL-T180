import logging
from datetime import datetime, timedelta
from typing import List, Dict, Set
from app.models import TaskInDB

logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(self, tasks: List[TaskInDB], start_time: datetime, end_time: datetime):
        """
        Initialize the TaskScheduler.
        
        Args:
            tasks: List of tasks to schedule
            start_time: Start time of the scheduling window
            end_time: End time of the scheduling window
        """
        self.tasks = tasks
        self.start_time = start_time
        self.end_time = end_time
        self.scheduled_tasks: List[TaskInDB] = []
        
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
        
        logger.info(f"Initialized TaskScheduler with {len(tasks)} tasks")
    
    def is_schedulable(self, task: TaskInDB, current_time: datetime) -> bool:
        """Check if a task is schedulable at the current time."""
        # Check if all dependencies are completed
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
                
                logger.info(f"Scheduled task '{scheduled_task.name}' from {scheduled_task.scheduled_start_time} to {scheduled_task.scheduled_end_time}")
            else:
                # If no task can be scheduled, move time forward by 15 minutes
                current_time += timedelta(minutes=15)
                logger.info(f"No schedulable tasks found, moving time to {current_time}")
        
        if unscheduled_tasks:
            logger.warning(f"Could not schedule {len(unscheduled_tasks)} tasks")
            for task in unscheduled_tasks:
                logger.warning(f"Unscheduled task: {task.name}")
        
        return self.scheduled_tasks 