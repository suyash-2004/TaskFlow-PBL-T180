from datetime import datetime, date
from typing import List, Optional, Dict, Any
from bson import ObjectId
from pydantic import BaseModel, Field, field_validator

from .task import PyObjectId

class TaskSummary(BaseModel):
    task_id: str
    name: str
    scheduled_duration: int  # in minutes
    actual_duration: Optional[int] = None  # in minutes
    scheduled_start_time: datetime
    scheduled_end_time: datetime
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    status: str
    priority: int
    delay: Optional[int] = None  # in minutes (positive if late, negative if early)

class ProductivityMetrics(BaseModel):
    completion_rate: float  # percentage of completed tasks
    on_time_rate: float  # percentage of tasks completed on time
    avg_delay: float  # average delay in minutes
    productivity_score: float  # custom score (0-100)
    total_scheduled_time: int  # in minutes
    total_actual_time: int  # in minutes
    time_efficiency: float  # ratio of scheduled to actual time

class ReportBase(BaseModel):
    date: datetime  # Changed from date to datetime for MongoDB compatibility
    user_id: str
    tasks: List[TaskSummary]
    metrics: ProductivityMetrics
    ai_summary: Optional[str] = None
    
    @field_validator('date', mode='before')
    @classmethod
    def validate_date(cls, v):
        # Convert date to datetime if needed
        if isinstance(v, date) and not isinstance(v, datetime):
            return datetime.combine(v, datetime.min.time())
        return v

class ReportCreate(ReportBase):
    pass

class ReportInDB(ReportBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat(),
            date: lambda d: d.isoformat(),
        }
    }

class ReportResponse(BaseModel):
    id: str
    date: datetime  # Changed from date to datetime for consistency
    user_id: str
    tasks: List[TaskSummary]
    metrics: ProductivityMetrics
    ai_summary: Optional[str] = None
    created_at: datetime
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "60d5ec9af682dbd134b216c9",
                "date": "2023-11-01T00:00:00",
                "user_id": "60d5ec9af682dbd134b216c7",
                "tasks": [
                    {
                        "task_id": "60d5ec9af682dbd134b216c8",
                        "name": "Write project proposal",
                        "scheduled_duration": 120,
                        "actual_duration": 135,
                        "scheduled_start_time": "2023-11-01T09:00:00",
                        "scheduled_end_time": "2023-11-01T11:00:00",
                        "actual_start_time": "2023-11-01T09:15:00",
                        "actual_end_time": "2023-11-01T11:30:00",
                        "status": "completed",
                        "priority": 4,
                        "delay": 15
                    }
                ],
                "metrics": {
                    "completion_rate": 100.0,
                    "on_time_rate": 0.0,
                    "avg_delay": 15.0,
                    "productivity_score": 85.0,
                    "total_scheduled_time": 120,
                    "total_actual_time": 135,
                    "time_efficiency": 0.89
                },
                "ai_summary": "You had a productive day, completing all scheduled tasks. However, you started 15 minutes late on your project proposal task, which caused you to finish later than planned. Overall, your time management was good with a productivity score of 85/100.",
                "created_at": "2023-11-01T23:59:59"
            }
        }
    } 