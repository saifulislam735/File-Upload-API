from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.db import pdf_gridfs, image_gridfs, json_gridfs, other_gridfs  # Import all buckets
from app.config import MAX_FILE_SIZE, ALLOWED_TYPES
from bson.objectid import ObjectId
import io
import logging
import json
from io import BytesIO

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="My File Upload API")

@app.get("/")
async def root():
    return {"message": "I am alive"}

origins = ["https://cheerful-froyo-4df5ef.netlify.app"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Only allow requests from this frontend
    allow_credentials=True,  # Allow cookies for authentication
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Allowed HTTP methods
    allow_headers=["Authorization", "Content-Type"],  # Allowed headers
)

# Helper function to choose the GridFS bucket based on content_type
def get_gridfs_bucket(content_type):
    if content_type == "application/pdf":
        return pdf_gridfs, "pdf"
    elif content_type in {"image/jpeg", "image/png"}:
        return image_gridfs, "image"
    elif content_type in {"application/json"}:
        return json_gridfs, "json"
    else:
        return other_gridfs, "other"

# Upload a file
@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    try:
        logger.info(f"File content type: {file.content_type}")
        if file.content_type not in ALLOWED_TYPES:
            logger.error(f"Invalid file type: {file.content_type}")
            raise HTTPException(status_code=400, detail="File type not allowed")
        if file.size > MAX_FILE_SIZE:
            logger.error(f"File too large: {file.size} bytes")
            raise HTTPException(status_code=400, detail="File too big (max 5MB)")
        
        
        content = await file.read()
        gridfs_bucket, bucket_name = get_gridfs_bucket(file.content_type)

        # if file.content_type == "application/json":
        #     try:
        #         #         # Parse the content to JSON
        #         # json_data = json.load(BytesIO(content))
                
        #         # # Insert the JSON data into MongoDB
        #         # result = gridfs_bucket.insert_one(json_data)
        #         file_id = gridfs_bucket.put(file_content, filename=file.filename)
        #         # Return a response with the inserted record's id
        #         return JSONResponse(content={"message": "File uploaded and data saved", "id": str(result.inserted_id)}, status_code=200)
            
        #     except Exception as e:
        #         return JSONResponse(content={"error": str(e)}, status_code=400)

        file_id = gridfs_bucket.put(content, filename=file.filename, content_type=file.content_type)
        logger.info(f"Uploaded file: {file.filename}, ID: {file_id}, Bucket: {bucket_name}")
        
        return {"filename": file.filename, "file_id": str(file_id), "bucket": bucket_name, "message": "File uploaded!"}
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Get all files (list)
@app.get("/files/")
async def list_files():
    try:
        # Collect files from all buckets
        pdf_files = [{"file_id": str(f._id), "filename": f.filename, "content_type": f.content_type, "bucket": "pdf"} for f in pdf_gridfs.find()]
        image_files = [{"file_id": str(f._id), "filename": f.filename, "content_type": f.content_type, "bucket": "image"} for f in image_gridfs.find()]
        other_files = [{"file_id": str(f._id), "filename": f.filename, "content_type": f.content_type, "bucket": "other"} for f in other_gridfs.find()]
        
        file_list = pdf_files + image_files + other_files
        logger.info(f"Listed {len(file_list)} files")
        return {"files": file_list}
    except Exception as e:
        logger.error(f"List files error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Get file for specific file type
@app.get("/file/{bucket}")
async def get_files_in_type(bucket: str):
    try:
        gridfs_bucket = {"pdf": pdf_gridfs, "image": image_gridfs, "other": other_gridfs}[bucket]
        files = [{"file_id": str(f._id), "filename": f.filename, "content_type": f.content_type, "bucket": bucket} for f in gridfs_bucket.find()]
        # file_data = gridfs_bucket.get(ObjectId(file_id))
        logger.info(f"Listed {len(files)} files")
        return {"files": files}
    except Exception as e:
        logger.error(f"List files error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Get a file (download/stream)
@app.get("/file/{file_id}/{bucket}")
async def get_file(file_id: str, bucket: str):
    try:
        gridfs_bucket = {"pdf": pdf_gridfs, "image": image_gridfs, "other": other_gridfs}[bucket]
        file_data = gridfs_bucket.get(ObjectId(file_id))
        logger.info(f"Streaming file: {file_data.filename}, ID: {file_id}, Bucket: {bucket}")
        return StreamingResponse(
            io.BytesIO(file_data.read()),
            media_type=file_data.content_type,
            headers={"Content-Disposition": f"attachment; filename={file_data.filename}"}
        )
    except Exception:
        logger.error(f"File not found: {file_id} in bucket {bucket}")
        raise HTTPException(status_code=404, detail="File not found")

# Update a file
@app.put("/file/{file_id}/{bucket}")
async def update_file(file_id: str, bucket: str, file: UploadFile = File(...)):
    try:
        if file.content_type not in ALLOWED_TYPES:
            logger.error(f"Invalid file type for update: {file.content_type}")
            raise HTTPException(status_code=400, detail="File type not allowed")
        if file.size > MAX_FILE_SIZE:
            logger.error(f"File too large for update: {file.size} bytes")
            raise HTTPException(status_code=400, detail="File too big (max 5MB)")
        
        gridfs_bucket = {"pdf": pdf_gridfs, "image": image_gridfs, "other": other_gridfs}[bucket]
        gridfs_bucket.delete(ObjectId(file_id))
        content = await file.read()
        new_file_id = gridfs_bucket.put(content, filename=file.filename, content_type=file.content_type, _id=ObjectId(file_id))
        logger.info(f"Updated file: {file.filename}, ID: {new_file_id}, Bucket: {bucket}")
        
        return {"filename": file.filename, "file_id": str(new_file_id), "bucket": bucket, "message": "File updated!"}
    except Exception as e:
        logger.error(f"Update error: {str(e)}")
        raise HTTPException(status_code=404, detail="File not found")

# Delete a file
@app.delete("/file/{file_id}/{bucket}")
async def delete_file(file_id: str, bucket: str):
    try:
        gridfs_bucket = {"pdf": pdf_gridfs, "image": image_gridfs, "other": other_gridfs}[bucket]
        gridfs_bucket.delete(ObjectId(file_id))
        logger.info(f"Deleted file ID: {file_id}, Bucket: {bucket}")
        return {"message": "File deleted!"}
    except Exception:
        logger.error(f"Delete error: {file_id} in bucket {bucket}")
        raise HTTPException(status_code=404, detail="File not found")