from fastapi import FastAPI, UploadFile, File, HTTPException
from app.db import gridfs
from app.config import MAX_FILE_SIZE, ALLOWED_TYPES

app = FastAPI(title="My File Upload API")

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    # Check file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="File type not allowed")
    # Check file size
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too big (max 5MB)")

    # Read the file
    content = await file.read()

    # Save to MongoDB
    file_id = gridfs.put(content, filename=file.filename, content_type=file.content_type)

    return {"filename": file.filename, "file_id": str(file_id), "message": "File uploaded!"}

@app.get("/file/{file_id}")
async def get_file(file_id: str):
    try:
        file_data = gridfs.get(file_id)
        return {"filename": file_data.filename, "content_type": file_data.content_type}
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")