from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from bson import ObjectId

from app.database import get_database
from app.models import TaskResponse, TaskInDB
from app.services import TaskScheduler

router = APIRouter()

@router.post("/generate", response_model=List[TaskResponse])
async def generate_schedule(
    date: str = Body(...),
    start_time: Optional[str] = Body(None),
    end_time: Optional[str] = Body(None),
    user_id: Optional[str] = Body("default_user"),
    db = Depends(get_database)
):
    """
    Generate a daily schedule for the specified date using the Round Robin algorithm.
    """
    try:
        # Parse date
        schedule_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Set default start and end times if not provided
        if not start_time:
            start_time = "09:00"
        if not end_time:
            end_time = "17:00"
            
        # Parse times
        try:
            start_hour, start_minute = map(int, start_time.split(":"))
            end_hour, end_minute = map(int, end_time.split(":"))
            
            schedule_start = datetime.combine(schedule_date, datetime.min.time().replace(hour=start_hour, minute=start_minute))
            schedule_end = datetime.combine(schedule_date, datetime.min.time().replace(hour=end_hour, minute=end_minute))
            
            if schedule_end <= schedule_start:
                raise HTTPException(status_code=400, detail="End time must be after start time")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM")
        
        # Build query
        query = {
            "status": {"$in": ["pending", "in_progress"]},
            "$or": [
                {"scheduled_start_time": None},
                {"scheduled_start_time": {"$exists": False}}
            ]
        }
        
        # Add user_id filter if provided
        if user_id:
            query["user_id"] = user_id
        
        # Get all tasks that are not yet scheduled or completed
        cursor = db["tasks"].find(query)
        tasks = await cursor.to_list(length=100)
        
        if not tasks:
            return []
        
        # Convert to TaskInDB objects
        task_objects = [TaskInDB(**task) for task in tasks]
        
        # Initialize scheduler
        scheduler = TaskScheduler(task_objects, schedule_start, schedule_end)
        
        # Generate schedule
        scheduled_tasks = scheduler.schedule()
        
        # Update tasks in database with scheduled times
        for task in scheduled_tasks:
            await db["tasks"].update_one(
                {"_id": task.id},
                {"$set": {
                    "scheduled_start_time": task.scheduled_start_time,
                    "scheduled_end_time": task.scheduled_end_time,
                    "updated_at": datetime.utcnow()
                }}
            )
        
        # Return scheduled tasks
        return [TaskResponse(
            id=str(task.id),
            name=task.name,
            description=task.description,
            duration=task.duration,
            priority=task.priority,
            deadline=task.deadline,
            dependencies=task.dependencies,
            user_id=task.user_id,
            created_at=task.created_at,
            updated_at=task.updated_at,
            scheduled_start_time=task.scheduled_start_time,
            scheduled_end_time=task.scheduled_end_time,
            actual_start_time=task.actual_start_time,
            actual_end_time=task.actual_end_time,
            status=task.status
        ) for task in scheduled_tasks]
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

@router.get("/daily/{date}", response_model=List[TaskResponse])
async def get_daily_schedule(
    date: str,
    user_id: Optional[str] = None,
    db = Depends(get_database)
):
    """
    Get the schedule for a specific date.
    """
    try:
        # Parse date
        schedule_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Find start and end of day
        start_of_day = datetime.combine(schedule_date, datetime.min.time())
        end_of_day = datetime.combine(schedule_date, datetime.max.time())
        
        # Build query
        query = {
            "scheduled_start_time": {"$gte": start_of_day, "$lt": end_of_day}
        }
        
        # Add user_id filter if provided
        if user_id:
            query["user_id"] = user_id
        
        # Get all scheduled tasks for this date
        cursor = db["tasks"].find(query).sort("scheduled_start_time", 1)  # Sort by start time ascending
        
        tasks = await cursor.to_list(length=100)
        
        return [TaskResponse(id=str(task["_id"]), **task) for task in tasks]
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

@router.post("/reset/{date}", status_code=200)
async def reset_schedule(
    date: str,
    user_id: Optional[str] = Body("default_user"),
    db = Depends(get_database)
):
    """
    Reset the schedule for a specific date by clearing scheduled times.
    """
    try:
        # Parse date
        schedule_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Find start and end of day
        start_of_day = datetime.combine(schedule_date, datetime.min.time())
        end_of_day = datetime.combine(schedule_date, datetime.max.time())
        
        # Build query
        query = {
            "scheduled_start_time": {"$gte": start_of_day, "$lt": end_of_day}
        }
        
        # Add user_id filter if provided
        if user_id:
            query["user_id"] = user_id
        
        # Reset all scheduled tasks for this date
        result = await db["tasks"].update_many(
            query,
            {"$set": {
                "scheduled_start_time": None,
                "scheduled_end_time": None,
                "updated_at": datetime.utcnow()
            }}
        )
        
        return {"message": f"Reset {result.modified_count} tasks"}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD") 