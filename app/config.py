from dotenv import load_dotenv
import os

load_dotenv()

# # Print values to debug
# print(f"MONGODB_URI: {os.getenv('MONGODB_URI')}")
# print(f"MAX_FILE_SIZE: {os.getenv('MAX_FILE_SIZE')}")
# print(f"ALLOWED_TYPES: {os.getenv('ALLOWED_TYPES')}")

MONGODB_URI = os.getenv("MONGODB_URI")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE"))
ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf", "text/plain", "application/json"}
# print(ALLOWED_TYPES)