# from dotenv import load_dotenv
# import os

# load_dotenv()

<<<<<<< HEAD
# MONGODB_URI = os.getenv("MONGODB_URI")
# MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE"))
# ALLOWED_TYPES = set(os.getenv("ALLOWED_TYPES").split(","))

# MONGODB_URI="mongodb+srv://shahin:12267655@cluster0.gjsqa.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# MONGODB_URI="mongodb+srv://sss:BonFF6j0paMT7VBq@cluster0.gjsqa.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
MONGODB_URI="localhost:27017"



# Max file size (5MB in bytes)
MAX_FILE_SIZE = 5 * 1024 * 1024

# Allowed file types
ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf", "text/plain", "application/json"}
=======
# Print values to debug
# print(f"MONGODB_URI: {os.getenv('MONGODB_URI')}")
# print(f"MAX_FILE_SIZE: {os.getenv('MAX_FILE_SIZE')}")
# print(f"ALLOWED_TYPES: {os.getenv('ALLOWED_TYPES')}")

MONGODB_URI = os.getenv("MONGODB_URI")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE"))
ALLOWED_TYPES = set(os.getenv("ALLOWED_TYPES").split(","))
>>>>>>> ec55a1f3ba91bfba686d9cca1abe00684feb4fa6
