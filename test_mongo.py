from pymongo import MongoClient
from app.config import MONGODB_URI

try:
    client = MongoClient(MONGODB_URI)
    client.server_info()  # This checks if the connection works
    print("Connected to MongoDB Atlas successfully!")
except Exception as e:
    print(f"Error: {e}")