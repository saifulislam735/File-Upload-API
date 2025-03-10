from fastapi import FastAPI, UploadFile, File, HTTPException, Query 
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
from typing import Literal


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="My File Upload API")

@app.get("/")
async def root():
    return {"message": "I am alive"}

# origins = ["https://cheerful-froyo-4df5ef.netlify.app"]
origins = ["*"]

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
        return pdf_gridfs, "pdf", db.pdfContent
    elif content_type in {"image/jpeg", "image/png"}:
        return image_gridfs, "image", None
    elif content_type in {"application/json"}:
        return json_gridfs, "json", db.jsonContent
    elif content_type in {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"}:
        return word_gridfs, "word", db.wordContent
    elif content_type in {"text/plain"}:
        return text_gridfs, "text", db.textContent
    elif content_type in {"text/csv"}:
        return csv_gridfs, "csv", db.csvContent
    else:
        return other_gridfs, "other", None

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

def get_gridfs_files_collection(section_name: str):
    """Returns the GridFS files collection dynamically based on section name."""
    return db[f"{section_name}.files"]

def get_gridfs_files_and_contrnt_collection(section_name: str):
    """Returns the GridFS files collection dynamically based on section name."""
    return db[f"{section_name}.files"], db[f"{section_name}Content"]

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
        gridfs_bucket, bucket_name, content_collection = get_gridfs_bucket(file.content_type)

        # Check if a file with the same name already exists in the bucket
        existing_file = gridfs_bucket.find_one({"filename": file.filename})
        if existing_file:
            logger.error(f"File already exists: {file.filename}")
            # return {"Message":"File with the same name already exists"}
            raise HTTPException(status_code=400, detail="File with the same name already exists")
            

        file_id = gridfs_bucket.put(content, filename=file.filename, content_type=file.content_type, downloadsCount= 0, viewsCount=0)
        logger.info(f"Uploaded file: {file.filename}, ID: {file_id}, Bucket: {bucket_name}")

        # Extract Text
        if bucket_name == "pdf" or bucket_name == "word" or bucket_name == "csv" or bucket_name == "text":
            #Store pdf content
            if bucket_name == "pdf":
                extracted_text = extract_text_from_pdf(content)

            #Store word content
            if bucket_name == "word":
                extracted_text = extract_text_from_docx(content)

            #Store txt content
            if bucket_name == "text":
                extracted_text = content.decode("utf-8")
            
            #Store CSV content
            if bucket_name == "csv":
                encoding = detect_encoding(content)
                df = pd.read_csv(io.BytesIO(content), dtype=str, encoding=encoding, header=None)
                extracted_text = "\n".join(df.astype(str).apply(lambda x: ", ".join(x), axis=1))

            contentID = content_collection.insert_one({
                    "filename": file.filename,
                    "content": extracted_text,
                    "file_id": file_id
                }).inserted_id
            files_collection = get_gridfs_files_collection(bucket_name)
            files_collection.update_one(
                    {"_id": ObjectId(file_id)}, # Filter condition
                    {"$set": {"content_id": ObjectId(contentID)}}  # Correct use of $set
                )
            return {"filename": file.filename, "file_id": str(file_id), "content_id": str(contentID), "bucket": bucket_name, "message": "File and Content uploaded!"}
        
        elif bucket_name == "json":
            json_data = json.load(BytesIO(content))
            extracted_text = content.decode("utf-8")
            contentID = content_collection.insert_one({
                "filename": file.filename,
                "json_object": json_data,
                "content": extracted_text,
                "file_id": file_id
            }).inserted_id

            files_collection = get_gridfs_files_collection(bucket_name)
            files_collection.update_one(
                    {"_id": ObjectId(file_id)}, # Filter condition
                    {"$set": {"content_id": ObjectId(contentID)}}  # Correct use of $set
                )
            return {"filename": file.filename, "file_id": str(file_id), "content_id": str(contentID), "bucket": bucket_name, "message": "File and Content uploaded!"}
        
        else:
            return {"filename": file.filename, "file_id": str(file_id), "bucket": bucket_name, "message": "File uploaded!"}
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error from upload")

# Get all files (list)
@app.get("/files/")
async def list_files(sort_by: Literal["upload_time", "filename"] = Query("upload_time"), order: Literal["asc", "desc"] = Query("desc")):
    try:
        # Collect files from all buckets
        pdf_files = [{"file_id": str(f._id), "filename": f.filename, "content_type": f.content_type, "bucket": "pdf", "upload_time": f.uploadDate} for f in pdf_gridfs.find()]
        image_files = [{"file_id": str(f._id), "filename": f.filename, "content_type": f.content_type, "bucket": "image", "upload_time": f.uploadDate} for f in image_gridfs.find()]
        json_files = [{"file_id": str(f._id), "filename": f.filename, "content_type": f.content_type, "bucket": "json", "upload_time": f.uploadDate} for f in json_gridfs.find()]
        other_files = [{"file_id": str(f._id), "filename": f.filename, "content_type": f.content_type, "bucket": "other", "upload_time": f.uploadDate} for f in other_gridfs.find()]
        word_files = [{"file_id": str(f._id), "filename": f.filename, "content_type": f.content_type, "bucket": "word", "upload_time": f.uploadDate} for f in word_gridfs.find()]
        text_files = [{"file_id": str(f._id), "filename": f.filename, "content_type": f.content_type, "bucket": "text", "upload_time": f.uploadDate} for f in text_gridfs.find()]
        csv_files = [{"file_id": str(f._id), "filename": f.filename, "content_type": f.content_type, "bucket": "csv", "upload_time": f.uploadDate} for f in csv_gridfs.find()]
        
        file_list = pdf_files + image_files + json_files + other_files + word_files + text_files + csv_files

        sort_reverse = order == "desc"
        if sort_by == "filename":
            file_list.sort(key=lambda x: x["filename"].lower(), reverse=sort_reverse)
        else:
            file_list.sort(key=lambda x: x["upload_time"], reverse=sort_reverse)
        # file_list.sort(key=lambda x: x[sort_by], reverse= sort_reverse)

        logger.info(f"Listed {len(file_list)} files")
        return {"files": file_list}
    except Exception as e:
        logger.error(f"List files error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Get file for specific file type
@app.get("/file/{bucket}")
async def get_files_in_type(bucket: str, sort_by: Literal["upload_time", "filename"] = Query("upload_time"), order: Literal["asc", "desc"] = Query("desc")):
    try:
        gridfs_bucket = bucket_gridfs_dict[bucket]
        sort_direction = 1 if order == "asc" else -1
        files = [{"file_id": str(f._id), "filename": f.filename, "content_type": f.content_type, "bucket": bucket, "upload_time": f.uploadDate} for f in gridfs_bucket.find()]
        # file_data = gridfs_bucket.get(ObjectId(file_id))

        sort_reverse = order == "desc"
        if sort_by == "filename":
            files.sort(key=lambda x: x["filename"].lower(), reverse=sort_reverse)
        else:
            files.sort(key=lambda x: x["upload_time"], reverse=sort_reverse)

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
    matched_file_Word = [{"filename": doc["filename"], "word_id": str(doc["file_id"])} for doc in resultsWord]
    matched_file_Txt = [{"filename": doc["filename"], "text_id": str(doc["file_id"])} for doc in resultsTxt]
    matched_file_JSON = [{"filename": doc["filename"], "json_id": str(doc["file_id"])} for doc in resultsJSON]
    matched_file_CSV = [{"filename": doc["filename"], "csv_id": str(doc["file_id"])} for doc in resultsCSV]
    
    matched_files = matched_file_PDF + matched_file_Word + matched_file_Txt + matched_file_JSON + matched_file_CSV
    
    if not matched_files:
        # matched_files = []
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
            # return {"filename": content_doc["filename"], "content": content_doc["content"]}
        
        if inline and bucket == "pdf":
            logger.info(f"Attempting to fetch pdf content for file_id: {file_id}")
            content_doc = db.pdfContent.find_one({"file_id": ObjectId(file_id)})
            if not content_doc:
                logger.error(f"No Pdf content found for file_id: {file_id}")
                raise HTTPException(status_code=404, detail="Word content not found")
            logger.info(f"Pdf content retrieved: {content_doc['filename']}")
            # return {"filename": content_doc["filename"], "content": content_doc["content"]}
        
        if inline and bucket == "csv":
            logger.info(f"Attempting to fetch word content for file_id: {file_id}")
            content_doc = db.csvContent.find_one({"file_id": ObjectId(file_id)})
            if not content_doc:
                logger.error(f"No CSV content found for file_id: {file_id}")
                raise HTTPException(status_code=404, detail="Word content not found")
            logger.info(f"CSV content retrieved: {content_doc['filename']}")
            # return {"filename": content_doc["filename"], "content": content_doc["content"]}
        
        # Increment the download count for the file
        if inline == False:
            db[f"{bucket}.files"].update_one(
                {"_id": ObjectId(file_id)},
                {"$inc": {"downloadsCount": 1}},
                upsert=True
            )
            logger.info(f"Download count for file_id {file_id} incremented.")
        else:
            db[f"{bucket}.files"].update_one(
                {"_id": ObjectId(file_id)},
                {"$inc": {"viewsCount": 1}},
                upsert=True
            )
            logger.info(f"View count for file_id {file_id} incremented.")


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
        
        
        gridfs_bucket1, bucket_name, content_collection = get_gridfs_bucket(file.content_type)

        gridfs_bucket = bucket_gridfs_dict[bucket]
        if bucket_name == bucket:
            file_object_id = ObjectId(file_id)
            if bucket == "pdf" or bucket == "word" or  bucket == "json" or bucket == "csv" or bucket == "text":
                files_collection, content_collection = get_gridfs_files_and_contrnt_collection(bucket)
                file_data = files_collection.find_one({"_id": file_object_id})
                if not file_data:
                    logger.info("File not found in GridFS")
                    raise HTTPException(status_code=404, detail="File not found in GridFS")       
                document = content_collection.find_one({"file_id": file_object_id})
                if not document:
                    logger.info("Document not fount")
                    raise HTTPException(status_code=404, detail="Document referencing file not found")
                gridfs_bucket.delete(file_object_id)
                content_collection.delete_one({"_id": document["_id"]})
                logger.info("File and related document deleted successfully")
                # return {"message": "File and related document deleted successfully"}
            else:
                gridfs_bucket.delete(ObjectId(file_id))
                logger.info(f"Deleted file ID: {file_id}, Bucket: {bucket}")
                logger.info("File deleted!")
                # return {"message": "File deleted!"}

            # gridfs_bucket.delete(ObjectId(file_id))
            # content = await file.read()
            content = await file.read()
            new_file_id = gridfs_bucket.put(content, filename=file.filename, content_type=file.content_type, _id=ObjectId(file_id), downloadsCount= 0, viewsCount=0)
            logger.info(f"Updated file: {file.filename}, ID: {new_file_id}, Bucket: {bucket}")


            # Extract Text
            if bucket_name == "pdf" or bucket_name == "word" or bucket_name == "csv" or bucket_name == "text":
                #Store pdf content
                if bucket_name == "pdf":
                    extracted_text = extract_text_from_pdf(content)

                #Store word content
                if bucket_name == "word":
                    extracted_text = extract_text_from_docx(content)

                #Store txt content
                if bucket_name == "text":
                    extracted_text = content.decode("utf-8")
                
                #Store CSV content
                if bucket_name == "csv":
                    encoding = detect_encoding(content)
                    df = pd.read_csv(io.BytesIO(content), dtype=str, encoding=encoding, header=None)
                    extracted_text = "\n".join(df.astype(str).apply(lambda x: ", ".join(x), axis=1))

                new_contentID = content_collection.insert_one({
                        "filename": file.filename,
                        "content": extracted_text,
                        "file_id": ObjectId(file_id),
                        "_id": ObjectId(document["_id"])
                    }).inserted_id
                files_collection = get_gridfs_files_collection(bucket_name)
                files_collection.update_one(
                        {"_id": ObjectId(file_id)}, # Filter condition
                        {"$set": {"content_id": ObjectId(new_contentID)}}  # Correct use of $set
                    )
                logger.info("File and Content updated!")
                return {"filename": file.filename, "file_id": str(file_id), "content_id": str(new_contentID), "bucket": bucket_name, "message": "File and Content updated!"}
            
            elif bucket_name == "json":
                json_data = json.load(BytesIO(content))
                extracted_text = content.decode("utf-8")
                new_contentID = content_collection.insert_one({
                    "filename": file.filename,
                    "json_object": json_data,
                    "content": extracted_text,
                    "file_id": ObjectId(file_id),
                    "_id": ObjectId(document["_id"])
                }).inserted_id

                files_collection = get_gridfs_files_collection(bucket_name)
                files_collection.update_one(
                        {"_id": ObjectId(file_id)}, # Filter condition
                        {"$set": {"content_id": ObjectId(new_contentID)}}  # Correct use of $set
                    )
                return {"filename": file.filename, "file_id": str(file_id), "content_id": str(new_contentID), "bucket": bucket_name, "message": "File and Content updated!"}
            
            else:
                return {"filename": file.filename, "file_id": str(new_file_id), "bucket": bucket_name, "message": "File updated!"}
        else:
            return {"Message": "Please upload same file type!!"}
        
        # return {"filename": file.filename, "file_id": str(new_file_id), "bucket": bucket, "message": "File updated!"}
    except Exception as e:
        logger.error(f"Update error: {str(e)}")
        raise HTTPException(status_code=404, detail="File not found")

# Delete a file
@app.delete("/file/{file_id}/{bucket}")
async def delete_file(file_id: str, bucket: str):
    try:
        gridfs_bucket = bucket_gridfs_dict[bucket]
        file_object_id = ObjectId(file_id)
        if bucket == "pdf" or bucket == "word" or  bucket == "json" or bucket == "csv" or bucket == "text":
            # if bucket == "pdf":
            #     files_collection = db.pdf.files
            #     content_collection = db.pdfContent
            # elif bucket == "word":
            #     files_collection = db.word.files
            #     content_collection = db.wordContent
            # elif bucket == "json":
            #     files_collection = db.json.files
            #     content_collection = db.jsonContent
            # elif bucket == "csv":
            #     files_collection = db.csv.files
            #     content_collection = db.csvContent
            # elif bucket == "text":
            #     files_collection = db.text.files
            #     content_collection = db.textContent
            # else:
            #     raise HTTPException(status_code=400, detail="Invalid bucket")

            files_collection, content_collection = get_gridfs_files_and_contrnt_collection(bucket)
            # Find the file in the GridFS files collection
            file_data = files_collection.find_one({"_id": file_object_id})
            if not file_data:
                logger.info("File not found in GridFS")
                raise HTTPException(status_code=404, detail="File not found in GridFS")       
            # Find the related document in the other collection that references this file
            document = content_collection.find_one({"file_id": file_object_id})
            if not document:
                logger.info("Document not fount")
                raise HTTPException(status_code=404, detail="Document referencing file not found")
            # Delete the file from GridFS
            gridfs_bucket.delete(file_object_id)
            # Delete the document from the other collection
            content_collection.delete_one({"_id": document["_id"]})

            return {"message": "File and related document deleted successfully"}
        else:
            gridfs_bucket.delete(ObjectId(file_id))
            logger.info(f"Deleted file ID: {file_id}, Bucket: {bucket}")
            return {"message": "File deleted!"}
        # grid_out = gridfs_bucket.get(ObjectId(file_id))
        # content_ID = grid_out.content_id
        
        # logger.info(f"content id: {content_ID}")
        
        # if bucket == "pdf":
        #     db.pdfContent.delete(ObjectId(content_ID))
        #     logger.info(f"Deleted Content ID: {content_ID}, Bucket: {bucket}")

        # logger.info(f"Deleted file ID: {file_id}, Bucket: {bucket}")
        # return {"message": "File deleted!"}
    except Exception:
        logger.error(f"Delete error: {file_id} in bucket {bucket}")
        raise HTTPException(status_code=404, detail="File not found")