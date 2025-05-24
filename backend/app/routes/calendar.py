from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId

from app.database import get_database
from app.models import TaskResponse

router = APIRouter()

@router.get("/month/{year}/{month}", response_model=List[TaskResponse])
async def get_month_tasks(
    year: int,
    month: int,
    user_id: Optional[str] = None,
    db = Depends(get_database)
):
    """
    Get all tasks for a specific month.
    """
    try:
        # Validate month
        if month < 1 or month > 12:
            raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
        
        # Calculate start and end dates for the month
        start_date = datetime(year, month, 1)
        
        # Calculate end date (first day of next month)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        # Build query
        query = {}
        
        # Add user_id filter if provided
        if user_id:
            query["user_id"] = user_id
            
        query["$or"] = [
            # Tasks scheduled during this month
            {
                "$and": [
                    {"scheduled_start_time": {"$lt": end_date}},
                    {"scheduled_end_time": {"$gte": start_date}}
                ]
            },
            # Tasks with deadlines in this month
            {"deadline": {"$gte": start_date, "$lt": end_date}}
        ]
        
        # Get all tasks for this month
        cursor = db["tasks"].find(query)
        
        tasks = await cursor.to_list(length=500)  # Increased limit for month view
        
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
                logger.warning(f"Added missing status field to task {task['_id']}")
            result_tasks.append(TaskResponse(id=str(task["_id"]), **task))
        
        return result_tasks
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/week/{year}/{week}", response_model=List[TaskResponse])
async def get_week_tasks(
    year: int,
    week: int,
    user_id: Optional[str] = None,
    db = Depends(get_database)
):
    """
    Get all tasks for a specific week.
    """
    try:
        # Validate week number
        if week < 1 or week > 53:
            raise HTTPException(status_code=400, detail="Week must be between 1 and 53")
        
        # Calculate start date (Monday of the week)
        start_date = datetime.strptime(f"{year}-{week}-1", "%Y-%W-%w")
        
        # Calculate end date (Monday of next week)
        end_date = start_date + timedelta(days=7)
        
        # Build query
        query = {}
        
        # Add user_id filter if provided
        if user_id:
            query["user_id"] = user_id
            
        query["$or"] = [
            # Tasks scheduled during this week
            {
                "$and": [
                    {"scheduled_start_time": {"$lt": end_date}},
                    {"scheduled_end_time": {"$gte": start_date}}
                ]
            },
            # Tasks with deadlines in this week
            {"deadline": {"$gte": start_date, "$lt": end_date}}
        ]
        
        # Get all tasks for this week
        cursor = db["tasks"].find(query)
        
        tasks = await cursor.to_list(length=200)  # Increased limit for week view
        
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
                logger.warning(f"Added missing status field to task {task['_id']}")
            result_tasks.append(TaskResponse(id=str(task["_id"]), **task))
        
        return result_tasks
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/day/{date}", response_model=List[TaskResponse])
async def get_day_tasks(
    date: str,
    user_id: Optional[str] = None,
    db = Depends(get_database)
):
    """
    Get all tasks for a specific day.
    """
    try:
        # Parse date
        day_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Find start and end of day
        start_of_day = datetime.combine(day_date, datetime.min.time())
        end_of_day = datetime.combine(day_date, datetime.max.time())
        
        # Build query
        query = {}
        
        # Add user_id filter if provided
        if user_id:
            query["user_id"] = user_id
            
        query["$or"] = [
            # Tasks scheduled during this day
            {
                "$and": [
                    {"scheduled_start_time": {"$lt": end_of_day}},
                    {"scheduled_end_time": {"$gte": start_of_day}}
                ]
            },
            # Tasks with deadlines on this day
            {"deadline": {"$gte": start_of_day, "$lt": end_of_day}}
        ]
        
        # Get all tasks for this day
        cursor = db["tasks"].find(query).sort("scheduled_start_time", 1)  # Sort by start time ascending
        
        tasks = await cursor.to_list(length=100)
        
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
                logger.warning(f"Added missing status field to task {task['_id']}")
            result_tasks.append(TaskResponse(id=str(task["_id"]), **task))
        
        return result_tasks
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD") 