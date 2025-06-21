from pymongo import AsyncMongoClient
from functools import lru_cache
from app.core.config import settings

@lru_cache()
def get_client():
    return AsyncMongoClient(settings.MONGO_URI)

db = get_client()[settings.MONGO_DB_NAME]

def get_db():
    return get_client()[settings.MONGO_DB_NAME]

def get_collection(collection_name: str):
    return get_db()[collection_name]