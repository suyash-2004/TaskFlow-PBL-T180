from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path
from fastapi.responses import JSONResponse
from bson import ObjectId

from app.database import get_database
from app.models import TaskCreate, TaskUpdate, TaskResponse, TaskInDB

router = APIRouter()

@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(
    task: TaskCreate,
    db = Depends(get_database)
):
    """
    Create a new task.
    """
    # Create new task
    task_dict = task.dict()
    task_dict["created_at"] = datetime.utcnow()
    task_dict["updated_at"] = task_dict["created_at"]
    task_dict["status"] = "pending"
    
    # Insert into database
    result = await db["tasks"].insert_one(task_dict)
    
    # Get the created task
    created_task = await db["tasks"].find_one({"_id": result.inserted_id})
    
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
    
    return [TaskResponse(id=str(task["_id"]), **task) for task in tasks]

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
    
    return TaskResponse(id=str(task["_id"]), **task)

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_update: TaskUpdate,
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
    
    # Update task
    update_data = {k: v for k, v in task_update.dict(exclude_unset=True).items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    # Update in database
    await db["tasks"].update_one(
        {"_id": ObjectId(task_id)},
        {"$set": update_data}
    )
    
    # Get updated task
    updated_task = await db["tasks"].find_one({"_id": ObjectId(task_id)})
    
    return TaskResponse(id=str(updated_task["_id"]), **updated_task)

@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
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
    
    # Delete from database
    await db["tasks"].delete_one({"_id": ObjectId(task_id)})
    
    return JSONResponse(status_code=204, content=None)

@router.patch("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: str,
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
    
    # Update task status and times
    update_data = {"status": status, "updated_at": datetime.utcnow()}
    
    # If status is changing to in_progress, record start time
    if status == "in_progress" and task["status"] != "in_progress":
        update_data["actual_start_time"] = datetime.utcnow()
    
    # If status is changing to completed, record end time
    if status == "completed" and task["status"] != "completed":
        update_data["actual_end_time"] = datetime.utcnow()
    
    # Update in database
    await db["tasks"].update_one(
        {"_id": ObjectId(task_id)},
        {"$set": update_data}
    )
    
    # Get updated task
    updated_task = await db["tasks"].find_one({"_id": ObjectId(task_id)})
    
    return TaskResponse(id=str(updated_task["_id"]), **updated_task) 