import os
from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import FileResponse, JSONResponse
from bson import ObjectId
import tempfile

from app.database import get_database
from app.models import ReportResponse, ReportCreate, TaskInDB
from app.services import ReportGenerator

router = APIRouter()

@router.post("/generate/{date}", response_model=ReportResponse)
async def generate_report(
    date: str,
    user_id: Optional[str] = "default_user",
    db = Depends(get_database)
):
    """
    Generate a productivity report for the specified date.
    """
    try:
        # Parse date
        report_date = datetime.strptime(date, "%Y-%m-%d").date()
        # Convert date to datetime for MongoDB storage
        report_datetime = datetime.combine(report_date, datetime.min.time())
        
        # Check if report already exists
        existing_report = await db["reports"].find_one({
            "user_id": user_id,
            "date": report_datetime
        })
        
        if existing_report:
            return ReportResponse(id=str(existing_report["_id"]), **existing_report)
        
        # Find start and end of day
        start_of_day = datetime.combine(report_date, datetime.min.time())
        end_of_day = datetime.combine(report_date, datetime.max.time())
        
        # Get all tasks for this date with more flexible criteria
        # Include tasks with either scheduled time OR deadline on this date
        cursor = db["tasks"].find({
            "user_id": user_id,
            "$or": [
                {"scheduled_start_time": {"$gte": start_of_day, "$lt": end_of_day}},
                {"scheduled_end_time": {"$gte": start_of_day, "$lt": end_of_day}},
                {"deadline": {"$gte": start_of_day, "$lt": end_of_day}}
            ]
        })
        
        tasks = await cursor.to_list(length=100)
        
        if not tasks:
            # If no scheduled tasks, try to get any tasks for this user
            cursor = db["tasks"].find({"user_id": user_id}).limit(5)
            tasks = await cursor.to_list(length=5)
            
            if not tasks:
                raise HTTPException(status_code=404, detail="No tasks found for this user")
            
            # Add mock scheduling data for report generation
            for task in tasks:
                if not task.get("scheduled_start_time"):
                    task["scheduled_start_time"] = start_of_day + timedelta(hours=9)  # 9 AM
                if not task.get("scheduled_end_time"):
                    duration_minutes = task.get("duration", 60)
                    task["scheduled_end_time"] = task["scheduled_start_time"] + timedelta(minutes=duration_minutes)
        
        # Convert to TaskInDB objects
        task_objects = [TaskInDB(**task) for task in tasks]
        
        # Initialize report generator
        report_generator = ReportGenerator()
        
        # Generate report
        report = await report_generator.generate_daily_report(
            tasks=task_objects,
            report_date=report_date,
            user_id=user_id
        )
        
        # Save report to database
        report_dict = report.dict()
        # Convert date to datetime for MongoDB storage
        if isinstance(report_dict.get("date"), date):
            report_dict["date"] = datetime.combine(report_dict["date"], datetime.min.time())
            
        result = await db["reports"].insert_one(report_dict)
        
        # Get the created report
        created_report = await db["reports"].find_one({"_id": result.inserted_id})
        
        return ReportResponse(id=str(created_report["_id"]), **created_report)
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        # Log the actual error for debugging
        import traceback
        print(f"Error generating report: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

@router.post("/simple/{date}", response_model=ReportResponse)
async def generate_simple_report(
    date: str,
    user_id: Optional[str] = "default_user",
    db = Depends(get_database)
):
    """
    Generate a simple productivity report for the specified date.
    This is a fallback endpoint that doesn't use the complex Report Generator.
    """
    try:
        # Parse date
        report_date = datetime.strptime(date, "%Y-%m-%d").date()
        report_datetime = datetime.combine(report_date, datetime.min.time())
        
        # Check if report already exists
        existing_report = await db["reports"].find_one({
            "user_id": user_id,
            "date": report_datetime
        })
        
        if existing_report:
            return ReportResponse(id=str(existing_report["_id"]), **existing_report)
        
        # Find start and end of day
        start_of_day = datetime.combine(report_date, datetime.min.time())
        end_of_day = datetime.combine(report_date, datetime.max.time())
        
        # Get all tasks for this date
        cursor = db["tasks"].find({
            "user_id": user_id,
            "$or": [
                {"scheduled_start_time": {"$gte": start_of_day, "$lt": end_of_day}},
                {"scheduled_end_time": {"$gte": start_of_day, "$lt": end_of_day}},
                {"deadline": {"$gte": start_of_day, "$lt": end_of_day}}
            ]
        })
        
        tasks = await cursor.to_list(length=100)
        
        if not tasks:
            # If no tasks for this date, get any tasks for this user
            cursor = db["tasks"].find({"user_id": user_id}).limit(5)
            tasks = await cursor.to_list(length=5)
            
            if not tasks:
                raise HTTPException(status_code=404, detail="No tasks found for this user")
        
        # Create task summaries directly
        task_summaries = []
        for task in tasks:
            # Make sure we have scheduled times - add defaults if missing
            scheduled_start = task.get("scheduled_start_time")
            scheduled_end = task.get("scheduled_end_time")
            
            if not scheduled_start or not scheduled_end:
                scheduled_start = start_of_day + timedelta(hours=9)  # 9 AM
                scheduled_end = scheduled_start + timedelta(minutes=task.get("duration", 60))
            
            actual_start = task.get("actual_start_time")
            actual_end = task.get("actual_end_time")
            actual_duration = None
            delay = None
            
            if actual_start and actual_end:
                actual_duration = int((actual_end - actual_start).total_seconds() // 60)
                delay = int((actual_start - scheduled_start).total_seconds() // 60)
            
            task_summaries.append({
                "task_id": str(task["_id"]),
                "name": task["name"],
                "scheduled_duration": task.get("duration", 60),
                "actual_duration": actual_duration,
                "scheduled_start_time": scheduled_start,
                "scheduled_end_time": scheduled_end,
                "actual_start_time": actual_start,
                "actual_end_time": actual_end,
                "status": task.get("status", "pending"),
                "priority": task.get("priority", 3),
                "delay": delay
            })
        
        # Calculate basic metrics
        total_tasks = len(task_summaries)
        completed_tasks = len([t for t in task_summaries if t["status"] == "completed"])
        completion_rate = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
        
        on_time_tasks = len([t for t in task_summaries if t["status"] == "completed" and (t["delay"] is None or t["delay"] <= 0)])
        on_time_rate = (on_time_tasks / completed_tasks) * 100 if completed_tasks > 0 else 0
        
        delays = [t["delay"] for t in task_summaries if t["status"] == "completed" and t["delay"] is not None]
        avg_delay = sum(delays) / len(delays) if delays else 0
        
        total_scheduled_time = sum(t["scheduled_duration"] for t in task_summaries)
        total_actual_time = sum(t["actual_duration"] for t in task_summaries if t["actual_duration"] is not None)
        
        time_efficiency = total_scheduled_time / total_actual_time if total_actual_time > 0 else 0
        
        # Create simple productivity score
        productivity_score = (completion_rate * 0.5) + (on_time_rate * 0.3) + (min(time_efficiency, 1) * 100 * 0.2)
        
        # Create simple report
        report = {
            "date": report_datetime,
            "user_id": user_id,
            "tasks": task_summaries,
            "metrics": {
                "completion_rate": round(completion_rate, 1),
                "on_time_rate": round(on_time_rate, 1),
                "avg_delay": round(avg_delay, 1),
                "productivity_score": round(productivity_score, 1),
                "total_scheduled_time": total_scheduled_time,
                "total_actual_time": total_actual_time,
                "time_efficiency": round(time_efficiency, 2)
            },
            "ai_summary": f"You completed {completed_tasks} out of {total_tasks} tasks ({completion_rate:.1f}%). Your productivity score is {productivity_score:.1f}/100.",
            "created_at": datetime.utcnow()
        }
        
        # Insert into database
        result = await db["reports"].insert_one(report)
        
        # Get the created report
        created_report = await db["reports"].find_one({"_id": result.inserted_id})
        
        return ReportResponse(id=str(created_report["_id"]), **created_report)
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        import traceback
        print(f"Error generating simple report: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error generating simple report: {str(e)}")

@router.get("/", response_model=List[ReportResponse])
async def get_reports(
    skip: int = 0,
    limit: int = 10,
    user_id: Optional[str] = None,
    db = Depends(get_database)
):
    """
    Get all reports.
    """
    # Build query
    query = {}
    
    # Add user_id filter if provided
    if user_id:
        query["user_id"] = user_id
        
    cursor = db["reports"].find(query).sort("date", -1).skip(skip).limit(limit)
    reports = await cursor.to_list(length=limit)
    
    return [ReportResponse(id=str(report["_id"]), **report) for report in reports]

@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    db = Depends(get_database)
):
    """
    Get a specific report by ID.
    """
    # Validate ObjectId
    if not ObjectId.is_valid(report_id):
        raise HTTPException(status_code=400, detail="Invalid report ID")
    
    # Get report from database
    report = await db["reports"].find_one({"_id": ObjectId(report_id)})
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return ReportResponse(id=str(report["_id"]), **report)

@router.get("/{report_id}/pdf")
async def get_report_pdf(
    report_id: str,
    db = Depends(get_database)
):
    """
    Get a PDF version of a specific report.
    """
    # Validate ObjectId
    if not ObjectId.is_valid(report_id):
        raise HTTPException(status_code=400, detail="Invalid report ID")
    
    # Get report from database
    report = await db["reports"].find_one({"_id": ObjectId(report_id)})
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Create report object
    report_obj = ReportCreate(**report)
    
    # Initialize report generator
    report_generator = ReportGenerator()
    
    # Create temporary file for PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        pdf_path = temp_file.name
    
    # Generate PDF
    try:
        report_generator.generate_pdf_report(report_obj, pdf_path)
        
        # Return PDF file
        return FileResponse(
            path=pdf_path,
            filename=f"productivity_report_{report['date']}.pdf",
            media_type="application/pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")
    finally:
        # Clean up temp file (after response is sent)
        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except:
                pass 