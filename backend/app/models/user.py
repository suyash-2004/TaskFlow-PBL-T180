from datetime import datetime
from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, Field, EmailStr

from .task import PyObjectId

class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None

class UserInDB(UserBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    is_superuser: bool = False
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat(),
        },
        "json_schema_extra": {
            "example": {
                "_id": "60d5ec9af682dbd134b216c7",
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "hashed_password": "hashed_password_string",
                "created_at": "2023-11-01T12:00:00",
                "updated_at": "2023-11-01T12:00:00",
                "is_active": True,
                "is_superuser": False
            }
        }
    }

class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: Optional[str] = None
    created_at: datetime
    is_active: bool
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "60d5ec9af682dbd134b216c7",
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "created_at": "2023-11-01T12:00:00",
                "is_active": True
            }
        }
    }

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None 