from pymongo import MongoClient
from gridfs import GridFS
from app.config import MONGODB_URI

# Connect to MongoDB Atlas
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client["file_upload_db"] #Atlas

# Define separate GridFS buckets
pdf_gridfs = GridFS(db, collection="pdf")      # For PDFs
image_gridfs = GridFS(db, collection="image")  # For images
json_gridfs = GridFS(db, collection="json")  # For json file
word_gridfs = GridFS(db, collection="word")  # For word file
text_gridfs = GridFS(db, collection="text")  # For text file
csv_gridfs = GridFS(db, collection="csv")  # For csv file
audio_gridfs = GridFS(db, collection="audio") #For audio file
video_gridfs = GridFS(db, collection="video") #For video file
other_gridfs = GridFS(db, collection="other")  # For other files
