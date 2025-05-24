from fastapi import Depends
from typing import Annotated

from app.database import get_database
from app.services import DependencyManager

# Create a singleton instance of the dependency manager
_dependency_manager = DependencyManager()

async def get_dependency_manager():
    """
    Get the dependency manager instance.
    """
    return _dependency_manager

# Create a type annotation for dependency injection
DependencyManagerDep = Annotated[DependencyManager, Depends(get_dependency_manager)] 