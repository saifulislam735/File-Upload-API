from pymongo import MongoClient
from gridfs import GridFS # GridFS (a way to store files in chunks).
from app.config import MONGODB_URI

# Connect to MongoDB AtlaI
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client["file_upload_db"]  # Our database name
gridfs = GridFS(db)  # For storing big files