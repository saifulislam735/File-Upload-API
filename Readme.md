Here’s a short and sweet `README.md` for your `File-Upload-API` project, tailored for quick setup and sharing with your friend on the same Wi-Fi. It’s concise yet covers the essentials for a beginner like you.

---

# File Upload API

A simple FastAPI app to upload files, JSON, and text to MongoDB Atlas GridFS, with a basic HTML frontend.

## Features

- Upload: PDFs, images (`.jpg`, `.png`), JSON, text.
- Storage: Separate GridFS buckets (`pdf`, `image`, `other`).
- Frontend: Upload, list, download, update, delete via UI.

## Setup

1. **Clone** (if using Git):
   ```bash
   git clone https://github.com/yourusername/File-Upload-API.git
   cd File-Upload-API
   ```
2. **Virtual Env**:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```
3. **Install**:
   ```bash
   pip install fastapi uvicorn pymongo python-dotenv python-multipart
   ```
4. **MongoDB**:
   - Get URI from [mongodb.com](https://www.mongodb.com/).
   - Add to `.env`:
     ```
     MONGODB_URI=mongodb+srv://myuser:mypassword@cluster0.xyz123.mongodb.net/?retryWrites=true&w=majority
     ```
5. **Run API**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   - URL: `http://172.16.225.76:8000/docs`
6. **Run Frontend**:
   ```bash
   cd E:\Frontend
   python -m http.server 8001
   ```

   - URL: `http://172.16.225.76:8001`

## Usage

- **API**: `http://172.16.225.76:8000`
  - `POST /upload/`: File, JSON, or text.
  - `GET /files/`: List all.
  - `GET /file/{file_id}/{bucket}`: Download.
  - `PUT /file/{file_id}/{bucket}`: Update.
  - `DELETE /file/{file_id}/{bucket}`: Delete.
- **Frontend**: Upload and manage via UI.

## Share

- Tell your friend on the same Wi-Fi:
  - API: `http://172.16.225.76:8000/docs`
  - UI: `http://172.16.225.76:8001`

## Troubleshooting

- **No Access**: Check Wi-Fi, allow port 8000 in firewall.
- **Errors**: Verify `.env` URI, ensure server’s running.

---

### How to Add

1. Create `README.md` in `E:\File-Upload-API\File-Upload-API`.
2. Copy-paste this text.
3. Save.

### Share

- “Hey friend, open `http://172.16.225.76:8000/docs` or `http://172.16.225.76:8001`—use my Wi-Fi!”
