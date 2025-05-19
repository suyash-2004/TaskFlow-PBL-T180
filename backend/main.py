import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

# Import routes
from app.routes import tasks, calendar, scheduler, reports
from app.database import get_database, database

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="TaskFlow API",
    description="API for TaskFlow - Smart Calendar-Based Task Scheduler",
    version="1.0.0",
)

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:3000",  # React frontend
    "http://localhost:5173",  # Vite development server
    "http://127.0.0.1:5173",  # Alternative localhost address
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection events
@app.on_event("startup")
async def startup_db_client():
    await database.connect()

@app.on_event("shutdown")
async def shutdown_db_client():
    await database.close()

# Include routers
app.include_router(tasks, prefix="/api/tasks", tags=["Tasks"])
app.include_router(calendar, prefix="/api/calendar", tags=["Calendar"])
app.include_router(scheduler, prefix="/api/scheduler", tags=["Scheduler"])
app.include_router(reports, prefix="/api/reports", tags=["Reports"])

# Root endpoint
@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to TaskFlow API - Smart Calendar-Based Task Scheduler"}

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # Using host="0.0.0.0" will make the server listen on all available IPv4 addresses
    # Setting reload=True enables automatic reloading when code changes
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
