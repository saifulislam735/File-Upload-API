from fastapi import FastAPI, UploadFile, File, HTTPException 
from fastapi.responses import StreamingResponse, JSONResponse 
from fastapi.middleware.cors import CORSMiddleware
from app.db import db, pdf_gridfs, image_gridfs, json_gridfs, other_gridfs, word_gridfs, text_gridfs, csv_gridfs  # Import all buckets
from app.config import MAX_FILE_SIZE, ALLOWED_TYPES
from bson.objectid import ObjectId   
import io
import logging
import json
from io import BytesIO
import PyPDF2 
from docx import Document 
from motor.motor_asyncio import AsyncIOMotorClient  
import pandas as pd
import chardet 


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="My File Upload API")

@app.get("/")
async def root():
    return {"message": "I am alive"}

origins = ["https://cheerful-froyo-4df5ef.netlify.app"]
# origins = ["*"]

#Bucket and Gridfs Dictionary
bucket_gridfs_dict = {"pdf": pdf_gridfs, "image": image_gridfs, "json": json_gridfs, "other": other_gridfs, "word": word_gridfs, "text": text_gridfs, "csv": csv_gridfs}


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
    elif content_type in {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"}:
        return word_gridfs, "word"
    elif content_type in {"text/plain"}:
        return text_gridfs, "text"
    elif content_type in {"text/csv"}:
        return csv_gridfs, "csv"
    else:
        return other_gridfs, "other"

# Function to extract text from PDF
def extract_text_from_pdf(file_bytes):
    reader = PyPDF2.PdfReader(BytesIO(file_bytes))
    text = " ".join([page.extract_text() for page in reader.pages if page.extract_text()])
    return text.strip()

# Extract text from a .docx file.
def extract_text_from_docx(file_data: bytes) -> str:
    doc = Document(io.BytesIO(file_data))
    return "\n".join([para.text for para in doc.paragraphs])

#Detects encoding of a file using chardet.
def detect_encoding(file_bytes):
    result = chardet.detect(file_bytes)
    return result["encoding"]


# Upload a file
@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    try:
        # logger.info(f"File content type: {file.content_type}")
        # if file.content_type not in ALLOWED_TYPES:
        #     logger.error(f"Invalid file type: {file.content_type}")
        #     raise HTTPException(status_code=400, detail="File type not allowed")
        if file.size > MAX_FILE_SIZE:
            logger.error(f"File too large: {file.size} bytes")
            raise HTTPException(status_code=400, detail="File too big (max 5MB)")
        
        
        content = await file.read()
        gridfs_bucket, bucket_name = get_gridfs_bucket(file.content_type)

        file_id = gridfs_bucket.put(content, filename=file.filename, content_type=file.content_type)
        logger.info(f"Uploaded file: {file.filename}, ID: {file_id}, Bucket: {bucket_name}")

        #Store pdf content
        if bucket_name == "pdf":
            extracted_text = extract_text_from_pdf(content)
            db.pdfContent.insert_one({
                "filename": file.filename,
                "content": extracted_text,
                "file_id": file_id
            })

        #Store word content
        if bucket_name == "word":
            text = extract_text_from_docx(content)
            db.wordContent.insert_one({
                "filename": file.filename, 
                "content": text,
                "file_id": file_id
            })

        #Store txt content
        if bucket_name == "text":
            text_data = content.decode("utf-8")
            db.txtContent.insert_one({
                "filename": file.filename, 
                "content": text_data,
                "file_id": file_id
            })

        #Store JSON as JSON and content
        if bucket_name == "json":
            json_data = json.load(BytesIO(content))
            db.jsonContent.insert_one({
                "filename": file.filename,
                "json_object": json_data,
                "content": content.decode("utf-8"),
                "file_id": file_id
            })
        
        #Store CSV content
        if bucket_name == "csv":
            encoding = detect_encoding(content)
            df = pd.read_csv(io.BytesIO(content), dtype=str, encoding=encoding, header=None)
            text_content = "\n".join(df.astype(str).apply(lambda x: ", ".join(x), axis=1))
            db.csvContent.insert_one({
                "filename": file.filename,
                "content": text_content,
                "file_id": file_id
            })

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
        json_files = [{"file_id": str(f._id), "filename": f.filename, "content_type": f.content_type, "bucket": "json"} for f in json_gridfs.find()]
        other_files = [{"file_id": str(f._id), "filename": f.filename, "content_type": f.content_type, "bucket": "other"} for f in other_gridfs.find()]
        word_files = [{"file_id": str(f._id), "filename": f.filename, "content_type": f.content_type, "bucket": "word"} for f in word_gridfs.find()]
        text_files = [{"file_id": str(f._id), "filename": f.filename, "content_type": f.content_type, "bucket": "text"} for f in text_gridfs.find()]
        csv_files = [{"file_id": str(f._id), "filename": f.filename, "content_type": f.content_type, "bucket": "csv"} for f in csv_gridfs.find()]
        
        file_list = pdf_files + image_files + json_files + other_files + word_files + text_files + csv_files
        logger.info(f"Listed {len(file_list)} files")
        return {"files": file_list}
    except Exception as e:
        logger.error(f"List files error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Get file for specific file type
@app.get("/file/{bucket}")
async def get_files_in_type(bucket: str):
    try:
        gridfs_bucket = bucket_gridfs_dict[bucket]
        files = [{"file_id": str(f._id), "filename": f.filename, "content_type": f.content_type, "bucket": bucket} for f in gridfs_bucket.find()]
        # file_data = gridfs_bucket.get(ObjectId(file_id))
        logger.info(f"Listed {len(files)} files")
        return {"files": files}
    except Exception as e:
        logger.error(f"List files error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Endpoint to search word
@app.get("/search/")
async def search_pdf_by_word(word: str):
    resultsPDF = db.pdfContent.find({"content": {"$regex": word, "$options": "i"}})
    resultsWord = db.wordContent.find({"content": {"$regex": word, "$options": "i"}})
    resultsTxt = db.txtContent.find({"content": {"$regex": word, "$options": "i"}})
    resultsJSON = db.jsonContent.find({"content": {"$regex": word, "$options": "i"}})
    resultsCSV = db.csvContent.find({"content": {"$regex": word, "$options": "i"}})
    
    matched_file_PDF = [{"filename": doc["filename"], "pdf_id": str(doc["file_id"])} for doc in resultsPDF]
    matched_file_Word = [{"filename": doc["filename"], "pdf_id": str(doc["file_id"])} for doc in resultsWord]
    matched_file_Txt = [{"filename": doc["filename"], "pdf_id": str(doc["file_id"])} for doc in resultsTxt]
    matched_file_JSON = [{"filename": doc["filename"], "pdf_id": str(doc["file_id"])} for doc in resultsJSON]
    matched_file_CSV = [{"filename": doc["filename"], "pdf_id": str(doc["file_id"])} for doc in resultsCSV]
    
    matched_files = matched_file_PDF + matched_file_Word + matched_file_Txt + matched_file_JSON + matched_file_CSV
    
    if not matched_files:
        raise HTTPException(status_code=404, detail="No matching PDFs found")
    
    return {"matched_pdfs": matched_files}

# Get a file (download/stream or view inline)
@app.get("/file/{file_id}/{bucket}")
async def get_file(file_id: str, bucket: str, inline: bool = False):
    try:
        logger.info(f"Request received - File ID: {file_id}, Bucket: {bucket}, Inline: {inline}")
        gridfs_bucket = bucket_gridfs_dict[bucket]
        file_data = gridfs_bucket.get(ObjectId(file_id))
        logger.info(f"Streaming file: {file_data.filename}, ID: {file_id}, Bucket: {bucket}")

        # If inline=True and bucket is "word", return extracted text
        if inline and bucket == "word":
            logger.info(f"Attempting to fetch word content for file_id: {file_id}")
            content_doc = db.wordContent.find_one({"file_id": ObjectId(file_id)})
            if not content_doc:
                logger.error(f"No word content found for file_id: {file_id}")
                raise HTTPException(status_code=404, detail="Word content not found")
            logger.info(f"Word content retrieved: {content_doc['filename']}")
            return {"filename": content_doc["filename"], "content": content_doc["content"]}

        # Otherwise, stream the raw file
        disposition = "inline" if inline else "attachment"
        logger.info(f"Streaming raw file with disposition: {disposition}")
        return StreamingResponse(
            io.BytesIO(file_data.read()),
            media_type=file_data.content_type,
            headers={"Content-Disposition": f"{disposition}; filename={file_data.filename}"}
        )
    except HTTPException as e:
        raise e  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}, File ID: {file_id}, Bucket: {bucket}")
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
        
        gridfs_bucket = bucket_gridfs_dict[bucket]
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
        gridfs_bucket = bucket_gridfs_dict[bucket]
        gridfs_bucket.delete(ObjectId(file_id))
        logger.info(f"Deleted file ID: {file_id}, Bucket: {bucket}")
        return {"message": "File deleted!"}
    except Exception:
        logger.error(f"Delete error: {file_id} in bucket {bucket}")
        raise HTTPException(status_code=404, detail="File not found")