import logging
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime
from bson import ObjectId
from app.models import TaskInDB, TaskResponse

logger = logging.getLogger(__name__)

class Semaphore:
    """
    A counting semaphore implementation for managing task dependencies.    
    """
    def __init__(self, count: int = 0):
        self.count = count
        self.waiting_tasks: List[str] = []
    
    def acquire(self, task_id: str) -> bool:
        """
        Try to acquire the semaphore.
        
        Args:
            task_id: ID of the task trying to acquire
            
        Returns:
            True if acquired, False if must wait
        """
        if self.count > 0:
            self.count -= 1
            return True
        else:
            if task_id not in self.waiting_tasks:
                self.waiting_tasks.append(task_id)
            return False
    
    def release(self) -> Optional[str]:
        """
        Release the semaphore and return the next waiting task if any.
        
        Returns:
            ID of the next task that can now proceed, or None
        """
        if self.waiting_tasks:
            next_task = self.waiting_tasks.pop(0)
            return next_task
        else:
            self.count += 1
            return None




class DependencyManager:
    """
    Manages task dependencies using semaphores and provides deadlock detection.
    """
    def __init__(self):
        self.dependency_graph: Dict[str, List[str]] = {}  # task_id -> list of dependencies
        self.dependent_tasks: Dict[str, List[str]] = {}   # task_id -> list of tasks that depend on it
        self.task_semaphores: Dict[str, Semaphore] = {}   # task_id -> semaphore
        self.waiting_for: Dict[str, str] = {}             # task_id -> id of task it's waiting for
        self.completed_tasks: Set[str] = set()            # Set of completed task IDs
        
    def register_task(self, task: TaskInDB) -> None:
        """
        Register a task with the dependency manager.
        
        Args:
            task: The task to register
        """
        task_id = str(task.id)
        
        # Initialize or update dependency graph
        self.dependency_graph[task_id] = task.dependencies or []
        
        # Update reverse dependency map
        for dep_id in task.dependencies or []:
            if dep_id not in self.dependent_tasks:
                self.dependent_tasks[dep_id] = []
            if task_id not in self.dependent_tasks[dep_id]:
                self.dependent_tasks[dep_id].append(task_id)
        
        # Initialize semaphore
        if task_id not in self.task_semaphores:
            # If task has no dependencies or all deps are completed, init with 1 (ready)
            # Otherwise init with 0 (must wait)
            deps_completed = all(
                dep_id in self.completed_tasks 
                for dep_id in (task.dependencies or [])
            )
            
            initial_count = 1 if not task.dependencies or deps_completed else 0
            self.task_semaphores[task_id] = Semaphore(initial_count)
        
        # If task is already completed, mark it as such
        if task.status == "completed":
            self.mark_task_completed(task_id)
    
    def load_tasks(self, tasks: List[TaskInDB]) -> None:
        """
        Load multiple tasks into the dependency manager.
        
        Args:
            tasks: List of tasks to load
        """
        for task in tasks:
            self.register_task(task)
    
    def mark_task_completed(self, task_id: str) -> List[str]:
        """
        Mark a task as completed and release dependent tasks.
        
        Args:
            task_id: ID of the completed task
            
        Returns:
            List of task IDs that are now unblocked
        """
        unblocked_tasks = []
        
        # Add to completed set
        self.completed_tasks.add(task_id)
        
        # Release dependencies
        dependent_ids = self.dependent_tasks.get(task_id, [])
        for dep_task_id in dependent_ids:
            # Remove this task from the dependency graph of dependent tasks
            if dep_task_id in self.dependency_graph:
                if task_id in self.dependency_graph[dep_task_id]:
                    self.dependency_graph[dep_task_id].remove(task_id)
            
            # If all dependencies are complete, release the semaphore
            all_deps_completed = all(
                dep_id in self.completed_tasks 
                for dep_id in self.dependency_graph.get(dep_task_id, [])
            )
            
            if all_deps_completed:
                # Remove from waiting_for if it was waiting
                if dep_task_id in self.waiting_for:
                    del self.waiting_for[dep_task_id]
                
                # Release semaphore for this task
                if dep_task_id in self.task_semaphores:
                    next_task = self.task_semaphores[dep_task_id].release()
                    if next_task:
                        unblocked_tasks.append(next_task)
                    else:
                        unblocked_tasks.append(dep_task_id)
        
        return unblocked_tasks
    
    def can_start(self, task_id: str) -> bool:
        """
        Check if a task can start (all dependencies satisfied).
        
        Args:
            task_id: ID of the task to check
            
        Returns:
            True if the task can start, False otherwise
        """
        # If task has no semaphore, it's not registered
        if task_id not in self.task_semaphores:
            return False
        
        # Try to acquire the semaphore
        return self.task_semaphores[task_id].acquire(task_id)
    
    def detect_deadlocks(self) -> List[List[str]]:
        """
        Detect deadlock cycles in the task dependency graph.
        
        Returns:
            List of cycles in the dependency graph (each cycle is a list of task IDs)
        """
        deadlock_cycles = []
        visited = set()
        path = []
        path_set = set()
        
        def dfs(node):
            if node in path_set:
                # Found a cycle
                cycle_start = path.index(node)
                deadlock_cycles.append(path[cycle_start:] + [node])
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            path_set.add(node)
            
            # Check all dependencies
            for dep in self.dependency_graph.get(node, []):
                dfs(dep)
            
            path.pop()
            path_set.remove(node)
        
        # Run DFS from each node
        for node in self.dependency_graph:
            if node not in visited:
                dfs(node)
        
        return deadlock_cycles
    
    def resolve_deadlock(self, cycle: List[str]) -> str:
        """
        Resolve a deadlock by breaking a dependency.
        
        Args:
            cycle: A cycle in the dependency graph
            
        Returns:
            ID of the task whose dependency was broken
        """
        if not cycle:
            return ""
        
        # Choose the lowest priority task to break
        # For simplicity, we'll choose the first task in the cycle
        task_to_break = cycle[0]
        
        # Remove one dependency to break the cycle
        if task_to_break in self.dependency_graph and self.dependency_graph[task_to_break]:
            # Remove the last dependency
            dep_to_remove = self.dependency_graph[task_to_break][-1]
            self.dependency_graph[task_to_break].remove(dep_to_remove)
            
            # Update reverse dependency map
            if dep_to_remove in self.dependent_tasks and task_to_break in self.dependent_tasks[dep_to_remove]:
                self.dependent_tasks[dep_to_remove].remove(task_to_break)
            
            logger.warning(f"Breaking dependency from {task_to_break} to {dep_to_remove} to resolve deadlock")
            
            # Release semaphore if all remaining dependencies are satisfied
            all_deps_completed = all(
                dep_id in self.completed_tasks 
                for dep_id in self.dependency_graph.get(task_to_break, [])
            )
            
            if all_deps_completed:
                if task_to_break in self.waiting_for:
                    del self.waiting_for[task_to_break]
                
                if task_to_break in self.task_semaphores:
                    self.task_semaphores[task_to_break].release()
            
            return task_to_break
        
        return ""
    
    def check_circular_dependency(self, task_id: str, dependencies: List[str]) -> bool:
        """
        Check if adding these dependencies would create a circular dependency.
        
        Args:
            task_id: ID of the task
            dependencies: List of dependency IDs to check
            
        Returns:
            True if circular dependency would be created, False otherwise
        """
        # Create a temporary dependency graph for checking
        temp_graph = self.dependency_graph.copy()
        temp_graph[task_id] = dependencies
        
        # Run DFS to check for cycles
        visited = set()
        rec_stack = set()
        
        def is_cyclic(node):
            visited.add(node)
            rec_stack.add(node)
            
            # Check all neighbors
            for dep in temp_graph.get(node, []):
                if dep not in visited:
                    if is_cyclic(dep):
                        return True
                elif dep in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        return is_cyclic(task_id)
    
    def get_task_dependency_status(self, task_id: str) -> Dict[str, bool]:
        """
        Get the status of each dependency for a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Dictionary mapping dependency IDs to their completion status
        """
        result = {}
        if task_id in self.dependency_graph:
            for dep_id in self.dependency_graph[task_id]:
                result[dep_id] = dep_id in self.completed_tasks
        return result
    
    def get_waiting_tasks(self) -> Dict[str, List[str]]:
        """
        Get tasks that are waiting on dependencies.
        
        Returns:
            Dictionary mapping task IDs to lists of dependency IDs they're waiting on
        """
        waiting_tasks = {}
        
        for task_id, deps in self.dependency_graph.items():
            waiting_deps = [dep for dep in deps if dep not in self.completed_tasks]
            if waiting_deps:
                waiting_tasks[task_id] = waiting_deps
        
        return waiting_tasks
    
    def get_dependency_summary(self) -> Dict:
        """
        Get a summary of the dependency state.
        
        Returns:
            Dictionary with dependency statistics
        """
        total_tasks = len(self.dependency_graph)
        completed = len(self.completed_tasks)
        waiting = len(self.get_waiting_tasks())
        
        deadlocks = self.detect_deadlocks()
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed,
            "waiting_tasks": waiting,
            "deadlocks": len(deadlocks),
            "deadlock_details": deadlocks
        } 
