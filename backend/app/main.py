import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.routes import tasks, calendar, scheduler, reports
from app.database import get_database
from app.dependencies import get_dependency_manager
from app.models import TaskInDB

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="TaskFlow API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(tasks, prefix="/api/tasks", tags=["tasks"])
app.include_router(calendar, prefix="/api/calendar", tags=["calendar"])
app.include_router(scheduler, prefix="/api/scheduler", tags=["scheduler"])
app.include_router(reports, prefix="/api/reports", tags=["reports"])

@app.on_event("startup")
async def startup_event():
    # Initialize the dependency manager with existing tasks
    logger.info("Initializing dependency manager")
    dependency_manager = await get_dependency_manager()
    db = await get_database()
    
    # Load all tasks
    cursor = db["tasks"].find({})
    tasks = await cursor.to_list(length=1000)
    
    if tasks:
        task_objects = [TaskInDB(**task) for task in tasks]
        dependency_manager.load_tasks(task_objects)
        logger.info(f"Loaded {len(tasks)} tasks into dependency manager")
        
        # Check for deadlocks
        deadlocks = dependency_manager.detect_deadlocks()
        if deadlocks:
            logger.warning(f"Detected {len(deadlocks)} deadlocks on startup")
    else:
        logger.info("No tasks found to load into dependency manager")

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"} 