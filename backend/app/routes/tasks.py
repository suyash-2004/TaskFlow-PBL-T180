from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path, Response
from fastapi.responses import JSONResponse
from bson import ObjectId
import logging

from app.database import get_database
from app.models import TaskCreate, TaskUpdate, TaskResponse, TaskInDB
from app.dependencies import DependencyManagerDep

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    dependency_manager: DependencyManagerDep,
    db = Depends(get_database)
):
    """
    Create a new task.
    """
    # Validate dependencies
    if task.dependencies:
        # Check if all dependencies exist
        for dep_id in task.dependencies:
            if not ObjectId.is_valid(dep_id):
                raise HTTPException(status_code=400, detail=f"Invalid dependency ID: {dep_id}")
            
            dep_task = await db["tasks"].find_one({"_id": ObjectId(dep_id)})
            if not dep_task:
                raise HTTPException(status_code=404, detail=f"Dependency task not found: {dep_id}")
        
        # Create a temporary TaskInDB with a placeholder ID to check for cycles
        temp_id = str(ObjectId())
        temp_task = TaskInDB(
            id=temp_id,
            **task.dict()
        )
        
        # Register with dependency manager temporarily to check for cycles
        dependency_manager.register_task(temp_task)
        
        # Check for circular dependencies
        if dependency_manager.check_circular_dependency(temp_id, task.dependencies):
            # Clean up the temporary task
            if temp_id in dependency_manager.dependency_graph:
                del dependency_manager.dependency_graph[temp_id]
            if temp_id in dependency_manager.task_semaphores:
                del dependency_manager.task_semaphores[temp_id]
            
            raise HTTPException(
                status_code=400, 
                detail="Circular dependency detected. Task cannot depend on itself directly or indirectly."
            )
    
    # Create task in database
    task_dict = task.dict()
    task_dict["created_at"] = datetime.utcnow()
    task_dict["updated_at"] = task_dict["created_at"]
    task_dict["status"] = "pending"  # Set default status
    
    result = await db["tasks"].insert_one(task_dict)
    created_task = await db["tasks"].find_one({"_id": result.inserted_id})
    
    # Register the task with the dependency manager
    task_obj = TaskInDB(**created_task)
    dependency_manager.register_task(task_obj)
    
    return TaskResponse(id=str(created_task["_id"]), **created_task)

@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    date: Optional[str] = None,
    user_id: Optional[str] = None,
    db = Depends(get_database)
):
    """
    Get all tasks, with optional filtering.
    """
    # Build query
    query = {}
    
    # Add user_id filter if provided
    if user_id:
        query["user_id"] = user_id
    
    # Add status filter if provided
    if status:
        query["status"] = status
    
    # Add date filter if provided
    if date:
        try:
            filter_date = datetime.strptime(date, "%Y-%m-%d").date()
            # Find tasks scheduled for this date
            start_of_day = datetime.combine(filter_date, datetime.min.time())
            end_of_day = datetime.combine(filter_date, datetime.max.time())
            
            query["$or"] = [
                {"scheduled_start_time": {"$gte": start_of_day, "$lte": end_of_day}},
                {"scheduled_end_time": {"$gte": start_of_day, "$lte": end_of_day}}
            ]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Get tasks from database
    cursor = db["tasks"].find(query).skip(skip).limit(limit)
    tasks = await cursor.to_list(length=limit)
    
    # Add default status for tasks that don't have it
    result_tasks = []
    for task in tasks:
        if "status" not in task:
            task["status"] = "pending"
            # Also update the task in the database to fix it permanently
            await db["tasks"].update_one(
                {"_id": task["_id"]},
                {"$set": {"status": "pending"}}
            )
            logger.info(f"Added missing status field to task {task['_id']}")
        result_tasks.append(TaskResponse(id=str(task["_id"]), **task))
    
    return result_tasks

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db = Depends(get_database)
):
    """
    Get a specific task by ID.
    """
    # Validate ObjectId
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=400, detail="Invalid task ID")
    
    # Get task from database
    task = await db["tasks"].find_one({"_id": ObjectId(task_id)})
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Add default status if missing
    if "status" not in task:
        task["status"] = "pending"
        # Also update the task in the database to fix it permanently
        await db["tasks"].update_one(
            {"_id": task["_id"]},
            {"$set": {"status": "pending"}}
        )
        logger.info(f"Added missing status field to task {task['_id']}")
    
    return TaskResponse(id=str(task["_id"]), **task)

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_update: TaskUpdate,
    dependency_manager: DependencyManagerDep,
    db = Depends(get_database)
):
    """
    Update a task.
    """
    # Validate ObjectId
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=400, detail="Invalid task ID")
    
    # Check if task exists
    task = await db["tasks"].find_one({"_id": ObjectId(task_id)})
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Validate dependencies if they're being updated
    if task_update.dependencies is not None:
        # Check if all dependencies exist
        for dep_id in task_update.dependencies:
            if not ObjectId.is_valid(dep_id):
                raise HTTPException(status_code=400, detail=f"Invalid dependency ID: {dep_id}")
            
            if dep_id == task_id:
                raise HTTPException(status_code=400, detail="Task cannot depend on itself")
            
            dep_task = await db["tasks"].find_one({"_id": ObjectId(dep_id)})
            if not dep_task:
                raise HTTPException(status_code=404, detail=f"Dependency task not found: {dep_id}")
        
        # Check for circular dependencies
        if dependency_manager.check_circular_dependency(task_id, task_update.dependencies):
            raise HTTPException(
                status_code=400, 
                detail="Circular dependency detected. Task cannot depend on itself directly or indirectly."
            )
    
    # Log incoming update data for debugging
    update_data = {k: v for k, v in task_update.dict(exclude_unset=True).items() if v is not None}
    if "deadline" in update_data:
        logger.info(f"Updating task {task_id} with deadline: {update_data['deadline']}")
        # Log in a more readable format too
        try:
            deadline_dt = datetime.fromisoformat(update_data['deadline'].replace('Z', '+00:00'))
            logger.info(f"Parsed update deadline as: {deadline_dt} (UTC)")
        except Exception as e:
            logger.error(f"Error parsing update deadline: {e}")
    
    # Add update timestamp
    update_data["updated_at"] = datetime.utcnow()
    
    # Update in database
    await db["tasks"].update_one(
        {"_id": ObjectId(task_id)},
        {"$set": update_data}
    )
    
    # Get updated task
    updated_task = await db["tasks"].find_one({"_id": ObjectId(task_id)})
    
    # Update the task in the dependency manager
    task_obj = TaskInDB(**updated_task)
    dependency_manager.register_task(task_obj)
    
    # Check for deadlocks after update
    deadlocks = dependency_manager.detect_deadlocks()
    if deadlocks:
        logger.warning(f"Deadlocks detected after updating task {task_id}: {deadlocks}")
        # Resolve deadlocks
        for cycle in deadlocks:
            resolved_task = dependency_manager.resolve_deadlock(cycle)
            if resolved_task:
                logger.info(f"Resolved deadlock by modifying task {resolved_task}")
    
    # Log stored deadline for debugging
    if updated_task.get("deadline"):
        logger.info(f"Updated deadline in database: {updated_task['deadline']}")
    
    return TaskResponse(id=str(updated_task["_id"]), **updated_task)

@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    dependency_manager: DependencyManagerDep,
    db = Depends(get_database)
):
    """
    Delete a task.
    """
    # Validate ObjectId
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=400, detail="Invalid task ID")
    
    # Check if task exists
    task = await db["tasks"].find_one({"_id": ObjectId(task_id)})
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if any other tasks depend on this one
    dependent_tasks = dependency_manager.dependent_tasks.get(task_id, [])
    if dependent_tasks:
        # Remove this dependency from all dependent tasks
        for dep_task_id in dependent_tasks:
            if dep_task_id in dependency_manager.dependency_graph:
                if task_id in dependency_manager.dependency_graph[dep_task_id]:
                    dependency_manager.dependency_graph[dep_task_id].remove(task_id)
            
            # Update the database
            await db["tasks"].update_one(
                {"_id": ObjectId(dep_task_id)},
                {"$pull": {"dependencies": task_id}}
            )
    
    # Delete from database
    await db["tasks"].delete_one({"_id": ObjectId(task_id)})
    
    # Clean up from dependency manager
    if task_id in dependency_manager.dependency_graph:
        del dependency_manager.dependency_graph[task_id]
    if task_id in dependency_manager.task_semaphores:
        del dependency_manager.task_semaphores[task_id]
    if task_id in dependency_manager.waiting_for:
        del dependency_manager.waiting_for[task_id]
    if task_id in dependency_manager.completed_tasks:
        dependency_manager.completed_tasks.remove(task_id)
    
    return JSONResponse(status_code=204, content=None)

@router.patch("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: str,
    dependency_manager: DependencyManagerDep,
    status: str = Body(..., embed=True),
    db = Depends(get_database)
):
    """
    Update a task's status and record actual start/end times.
    """
    # Validate ObjectId
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=400, detail="Invalid task ID")
    
    # Check valid status
    valid_statuses = ["pending", "in_progress", "completed", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    # Check if task exists
    task = await db["tasks"].find_one({"_id": ObjectId(task_id)})
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if dependencies are satisfied for in_progress or completed
    if status in ["in_progress", "completed"]:
        task_obj = TaskInDB(**task)
        dependency_status = dependency_manager.get_task_dependency_status(task_id)
        unsatisfied_deps = [dep_id for dep_id, completed in dependency_status.items() if not completed]
        
        if unsatisfied_deps:
            # Get task names for better error messages
            dep_tasks = []
            for dep_id in unsatisfied_deps:
                dep_task = await db["tasks"].find_one({"_id": ObjectId(dep_id)})
                if dep_task:
                    dep_tasks.append(f"{dep_task['name']} (ID: {dep_id})")
                else:
                    dep_tasks.append(f"Unknown task (ID: {dep_id})")
            
            # Return warning but allow the update (soft enforcement)
            logger.warning(f"Task {task_id} status changed to {status} with unsatisfied dependencies: {unsatisfied_deps}")
    
    # Update task status and times
    update_data = {"status": status, "updated_at": datetime.utcnow()}
    
    # If status is changing to in_progress, record start time
    if status == "in_progress" and task["status"] != "in_progress":
        update_data["actual_start_time"] = datetime.utcnow()
    
    # If status is changing to completed, record end time
    if status == "completed" and task["status"] != "completed":
        update_data["actual_end_time"] = datetime.utcnow()
        
        # Mark completed in dependency manager and get unblocked tasks
        unblocked_tasks = dependency_manager.mark_task_completed(task_id)
        if unblocked_tasks:
            logger.info(f"Completing task {task_id} unblocked tasks: {unblocked_tasks}")
    
    # Update in database
    await db["tasks"].update_one(
        {"_id": ObjectId(task_id)},
        {"$set": update_data}
    )
    
    # Get updated task
    updated_task = await db["tasks"].find_one({"_id": ObjectId(task_id)})
    
    return TaskResponse(id=str(updated_task["_id"]), **updated_task)

@router.get("/dependencies/status", response_model=Dict[str, Any])
async def get_dependency_status(
    dependency_manager: DependencyManagerDep,
):
    """
    Get the current dependency status including deadlocks.
    """
    return dependency_manager.get_dependency_summary()

@router.post("/dependencies/check-circular", response_model=Dict[str, Any])
async def check_circular_dependency(
    dependency_manager: DependencyManagerDep,
    task_id: str = Body(...),
    dependencies: List[str] = Body(...),
):
    """
    Check if a set of dependencies would create a circular dependency.
    """
    has_circular = dependency_manager.check_circular_dependency(task_id, dependencies)
    return {
        "has_circular_dependency": has_circular,
        "task_id": task_id,
        "dependencies": dependencies
    }

@router.post("/dependencies/resolve-deadlocks", response_model=Dict[str, Any])
async def resolve_deadlocks(
    dependency_manager: DependencyManagerDep,
    db = Depends(get_database)
):
    """
    Detect and resolve all deadlocks in the task dependency graph.
    """
    deadlocks = dependency_manager.detect_deadlocks()
    resolved = []
    
    if deadlocks:
        for cycle in deadlocks:
            resolved_task = dependency_manager.resolve_deadlock(cycle)
            if resolved_task:
                resolved.append({
                    "task_id": resolved_task,
                    "cycle": cycle
                })
                
                # Update the database to reflect the resolved deadlock
                if resolved_task in dependency_manager.dependency_graph:
                    await db["tasks"].update_one(
                        {"_id": ObjectId(resolved_task)},
                        {"$set": {
                            "dependencies": dependency_manager.dependency_graph[resolved_task],
                            "updated_at": datetime.utcnow()
                        }}
                    )
    
    return {
        "deadlocks_detected": len(deadlocks),
        "deadlocks_resolved": len(resolved),
        "details": resolved
    }

@router.get("/{task_id}/dependencies", response_model=Dict[str, Any])
async def get_task_dependencies(
    task_id: str,
    dependency_manager: DependencyManagerDep,
    db = Depends(get_database)
):
    """
    Get detailed dependency information for a specific task.
    """
    # Validate ObjectId
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=400, detail="Invalid task ID")
    
    # Check if task exists
    task = await db["tasks"].find_one({"_id": ObjectId(task_id)})
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Get dependency status
    dependency_status = dependency_manager.get_task_dependency_status(task_id)
    
    # Get dependent tasks (tasks that depend on this one)
    dependent_tasks = dependency_manager.dependent_tasks.get(task_id, [])
    
    # Get task details for dependencies and dependents
    dependency_details = []
    for dep_id, completed in dependency_status.items():
        dep_task = await db["tasks"].find_one({"_id": ObjectId(dep_id)})
        if dep_task:
            dependency_details.append({
                "id": dep_id,
                "name": dep_task["name"],
                "status": dep_task["status"],
                "completed": completed
            })
    
    dependent_details = []
    for dep_id in dependent_tasks:
        dep_task = await db["tasks"].find_one({"_id": ObjectId(dep_id)})
        if dep_task:
            dependent_details.append({
                "id": dep_id,
                "name": dep_task["name"],
                "status": dep_task["status"]
            })
    
    # Check if this task is part of any deadlocks
    deadlocks = dependency_manager.detect_deadlocks()
    in_deadlock = any(task_id in cycle for cycle in deadlocks)
    deadlock_details = [cycle for cycle in deadlocks if task_id in cycle]
    
    can_start = dependency_manager.can_start(task_id)
    
    return {
        "task_id": task_id,
        "task_name": task["name"],
        "task_status": task["status"],
        "dependencies": dependency_details,
        "dependents": dependent_details,
        "can_start": can_start,
        "in_deadlock": in_deadlock,
        "deadlock_details": deadlock_details
    } 