from datetime import datetime, timedelta
from typing import List, Optional, Any, ClassVar
from bson import ObjectId
from pydantic import BaseModel, Field, validator, GetJsonSchemaHandler
from pydantic_core import core_schema

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: Any
    ) -> core_schema.CoreSchema:
        return core_schema.union_schema([
            core_schema.is_instance_schema(ObjectId),
            core_schema.chain_schema([
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(cls.validate),
            ]),
        ])

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)
    
    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: core_schema.CoreSchema, 
        handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler.resolve_ref_schema(handler.schema_generator.schema_for_type(str))
        json_schema["format"] = "object-id"
        return json_schema

class TaskBase(BaseModel):
    name: str
    description: Optional[str] = None
    duration: int  # Duration in minutes
    priority: int = Field(..., ge=1, le=5)  # Priority from 1 (lowest) to 5 (highest)
    deadline: Optional[datetime] = None
    dependencies: Optional[List[str]] = []  # List of task IDs this task depends on

class TaskCreate(TaskBase):
    user_id: str

class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    deadline: Optional[datetime] = None
    dependencies: Optional[List[str]] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    status: Optional[str] = None

class TaskInDB(TaskBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    scheduled_start_time: Optional[datetime] = None
    scheduled_end_time: Optional[datetime] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    status: str = "pending"  # pending, in_progress, completed, cancelled

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat(),
        },
        "json_schema_extra": {
            "example": {
                "_id": "60d5ec9af682dbd134b216c8",
                "name": "Write project proposal",
                "description": "Create a detailed project proposal for the client",
                "duration": 120,
                "priority": 4,
                "deadline": "2023-12-31T23:59:59",
                "dependencies": [],
                "user_id": "60d5ec9af682dbd134b216c7",
                "created_at": "2023-11-01T12:00:00",
                "updated_at": "2023-11-01T12:00:00",
                "scheduled_start_time": "2023-11-02T09:00:00",
                "scheduled_end_time": "2023-11-02T11:00:00",
                "actual_start_time": None,
                "actual_end_time": None,
                "status": "pending"
            }
        }
    }

class TaskResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    duration: int
    priority: int
    deadline: Optional[datetime] = None
    dependencies: List[str] = []
    user_id: str
    created_at: datetime
    updated_at: datetime
    scheduled_start_time: Optional[datetime] = None
    scheduled_end_time: Optional[datetime] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    status: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "60d5ec9af682dbd134b216c8",
                "name": "Write project proposal",
                "description": "Create a detailed project proposal for the client",
                "duration": 120,
                "priority": 4,
                "deadline": "2023-12-31T23:59:59",
                "dependencies": [],
                "user_id": "60d5ec9af682dbd134b216c7",
                "created_at": "2023-11-01T12:00:00",
                "updated_at": "2023-11-01T12:00:00",
                "scheduled_start_time": "2023-11-02T09:00:00",
                "scheduled_end_time": "2023-11-02T11:00:00",
                "actual_start_time": None,
                "actual_end_time": None,
                "status": "pending"
            }
        }
    } 