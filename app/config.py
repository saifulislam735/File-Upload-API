from dotenv import load_dotenv
import os
load_dotenv()

# print(f"MONGODB_URI: {os.getenv('MONGODB_URI')}")
# print(f"MAX_FILE_SIZE: {os.getenv('MAX_FILE_SIZE')}")
# print(f"ALLOWED_TYPES: {os.getenv('ALLOWED_TYPES')}")

MONGODB_URI = os.getenv("MONGODB_URI")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE"))


ALLOWED_TYPES = {
    "image/jpeg", 
    "image/png", 
    "application/pdf", 
    "text/plain", 
    "application/json",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
    "application/msword",  
    "text/csv"
        # Audio types
    "audio/mpeg",           # .mp3
    "audio/wav",            # .wav
    "audio/x-wav",          # .wav (alternative)
    "audio/ogg",            # .ogg
    "audio/webm",           # .webm audio

    # Video types
    "video/mp4",            # .mp4
    "video/x-msvideo",      # .avi
    "video/x-matroska",     # .mkv
    "video/webm",           # .webm video
    "video/ogg"             # .ogv
}
# print(ALLOWED_TYPES)