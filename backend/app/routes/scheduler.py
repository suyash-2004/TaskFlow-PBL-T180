from datetime import datetime, timedelta
from typing import List, Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from bson import ObjectId
import logging

from app.database import get_database
from app.models import TaskResponse, TaskInDB
from app.services import TaskScheduler
from app.dependencies import DependencyManagerDep

router = APIRouter()
logger = logging.getLogger(__name__)

# Define the available scheduling algorithms for documentation
SchedulingAlgorithm = Literal["round_robin", "fcfs", "sjf", "ljf", "priority"]

@router.post("/generate", response_model=List[TaskResponse])
async def generate_schedule(
    dependency_manager: DependencyManagerDep,
    db = Depends(get_database),
    date: str = Body(...),
    start_time: Optional[str] = Body(None),
    end_time: Optional[str] = Body(None),
    user_id: Optional[str] = Body("default_user"),
    algorithm: SchedulingAlgorithm = Body("round_robin", description="Scheduling algorithm to use")
):
    """
    Generate a daily schedule for the specified date using the selected algorithm.
    
    Available algorithms:
    - round_robin: Priority-based Round Robin (considers both priority and deadlines)
    - fcfs: First Come First Served (schedules tasks in the order they were created)
    - sjf: Shortest Job First (schedules shortest duration tasks first)
    - ljf: Longest Job First (schedules longest duration tasks first)
    - priority: Priority only (schedules based solely on task priority)
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
        
        # First, clear any existing schedule for this date to avoid showing old schedules
        start_of_day = datetime.combine(schedule_date, datetime.min.time())
        end_of_day = datetime.combine(schedule_date, datetime.max.time())
        
        # Find all tasks scheduled for this date and reset them
        reset_query = {
            "scheduled_start_time": {"$gte": start_of_day, "$lt": end_of_day},
            "user_id": user_id
        }
        
        reset_result = await db["tasks"].update_many(
            reset_query,
            {"$set": {
                "scheduled_start_time": None,
                "scheduled_end_time": None,
                "updated_at": datetime.utcnow()
            }}
        )
        
        logger.info(f"Reset {reset_result.modified_count} previously scheduled tasks for {date}")
        
        # Build query to find unscheduled tasks
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
        
        # Initialize scheduler with dependency manager and selected algorithm
        scheduler = TaskScheduler(
            task_objects, 
            schedule_start, 
            schedule_end, 
            dependency_manager,
            algorithm=algorithm
        )
        
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
        
        # Find tasks scheduled for this date
        start_of_day = datetime.combine(schedule_date, datetime.min.time())
        end_of_day = datetime.combine(schedule_date, datetime.max.time())
        
        # Build query
        query = {
            "$or": [
                {"scheduled_start_time": {"$gte": start_of_day, "$lte": end_of_day}},
                {"scheduled_end_time": {"$gte": start_of_day, "$lte": end_of_day}}
            ]
        }
        
        # Add user_id filter if provided
        if user_id:
            query["user_id"] = user_id
        
        # Get tasks from database
        cursor = db["tasks"].find(query)
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