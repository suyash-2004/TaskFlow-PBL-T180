import os
import logging
import traceback
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    
    def __init__(self):
        self.db_name = os.getenv("MONGO_DB_NAME", "taskflow_db")
        self.db_url = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        logger.info(f"Database configuration: URL={self.db_url}, DB={self.db_name}")
    
    async def connect(self):
        """Connect to MongoDB database."""
        try:
            logger.info(f"Connecting to MongoDB at {self.db_url}...")
            self.client = AsyncIOMotorClient(self.db_url, serverSelectionTimeoutMS=5000)
            
            # Verify connection works
            await self.client.server_info()
            logger.info(f"Successfully connected to MongoDB - Database: {self.db_name}")
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            logger.error(traceback.format_exc())
            raise e
    
    async def close(self):
        """Close connection to MongoDB."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    def get_db(self):
        """Get database instance."""
        if not self.client:
            logger.warning("Database client not initialized. Attempting to create client...")
            self.client = AsyncIOMotorClient(self.db_url, serverSelectionTimeoutMS=5000)
        
        return self.client[self.db_name]

# Create database instance
database = Database()

# Convenience function to get database instance
async def get_database():
    return database.get_db() 