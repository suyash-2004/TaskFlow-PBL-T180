from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.database import get_database
from app.models import UserCreate, UserResponse, UserInDB, Token
from app.utils import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_active_user
)

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=201)
async def register_user(user: UserCreate, db = Depends(get_database)):
    """
    Register a new user.
    """
    # Check if username already exists
    existing_user = await db["users"].find_one({"username": user.username})
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = await db["users"].find_one({"email": user.email})
    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    user_dict = user.dict()
    user_dict.pop("password")
    user_dict["hashed_password"] = hashed_password
    user_dict["created_at"] = datetime.utcnow()
    user_dict["updated_at"] = user_dict["created_at"]
    user_dict["is_active"] = True
    user_dict["is_superuser"] = False
    
    # Insert into database
    result = await db["users"].insert_one(user_dict)
    
    # Get the created user
    created_user = await db["users"].find_one({"_id": result.inserted_id})
    
    return UserResponse(id=str(created_user["_id"]), **created_user)

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db = Depends(get_database)
):
    """
    Get an access token for authentication.
    """
    # Find user by username
    user = await db["users"].find_one({"username": form_data.username})
    
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=30)  # Token valid for 30 minutes
    access_token = create_access_token(
        data={"sub": user["username"], "user_id": str(user["_id"])},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: UserInDB = Depends(get_current_active_user)):
    """
    Get information about the current authenticated user.
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        created_at=current_user.created_at,
        is_active=current_user.is_active
    ) 