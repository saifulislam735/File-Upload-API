from dotenv import load_dotenv
import os

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE"))
ALLOWED_TYPES = set(os.getenv("ALLOWED_TYPES").split(","))