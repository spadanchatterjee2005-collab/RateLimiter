
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import redis

# Load environment variables
load_dotenv()

# MongoDB connection
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://localhost:27017"
)

mongo_client = MongoClient(MONGO_URI)

db = mongo_client["rate_limiter_db"]

# MongoDB collections
clients_collection = db["clients"]
history_collection = db["request_history"]

# Redis connection
REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0"
)

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True
)

# Check database connections
def check_connections():
    mongo_client.admin.command("ping")
    redis_client.ping()
    return True
