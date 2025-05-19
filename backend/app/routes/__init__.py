from .tasks import router as tasks_router
from .calendar import router as calendar_router
from .scheduler import router as scheduler_router
from .reports import router as reports_router

# Export routers
tasks = tasks_router
calendar = calendar_router
scheduler = scheduler_router
reports = reports_router

__all__ = ["tasks", "calendar", "scheduler", "reports"] 