from pymongo import MongoClient
from gridfs import GridFS
from app.config import MONGODB_URI

# Connect to MongoDB Atlas
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client["file_upload_db"]

# Define separate GridFS buckets
pdf_gridfs = GridFS(db, collection="pdf")    
image_gridfs = GridFS(db, collection="image")  
other_gridfs = GridFS(db, collection="other")  