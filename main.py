from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path
from supabase import create_client, Client

from utils.pdf_extractor import extract_text_from_pdf
from utils.ai_extractor import extract_paper_info
from middleware.auth import APIKeyMiddleware
from dotenv import load_dotenv

load_dotenv()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Research Paper AI API")

# Add API Key middleware
app.add_middleware(APIKeyMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Max file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024


@app.post("/upload")
async def upload_single_file(file: UploadFile = File(...), user_id: str = "default-user"):
    """Upload a single file with basic validation"""
    if file.filename == "":
        raise HTTPException(status_code=400, detail="No file selected")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        # 1. Read file bytes with size check
        file_bytes = await file.read()
        if len(file_bytes) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")

        # 2. Extract text from PDF
        pdf_text = extract_text_from_pdf(file_bytes)

        # 3. Use AI to extract structured information
        paper_info = extract_paper_info(pdf_text)

        print("Extracted Paper Info using AI:", paper_info)

        # 4. Save to database
        db_response = supabase.table("papers").insert({
            "user_id": user_id,
            "title": paper_info["title"],
            "authors": paper_info["authors"],
            "abstract": paper_info["abstract"],
            "tags": paper_info["tags"],
            "file_url": paper_info["file_url"],
            "paper_id": paper_info["paper_id"],
        }).execute()

        return {
            "message": "Paper uploaded and processed successfully",
            "paper": db_response.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/papers")
async def get_papers(user_id: str = "default-user"):
    """Get all papers for a user"""
    try:
        response = supabase.table("papers").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return {"papers": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/papers/{title}")
async def get_paper(title: str, user_id: str = "default-user"):
    """Get a single paper"""
    try:
        response = supabase.table("papers").select("*").eq("title", title).eq("user_id", user_id).single().execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Paper not found")
        return response.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/papers/{title}")
async def delete_paper(title: str, user_id: str = "default-user"):
    """Delete a paper"""
    try:
        # Check paper exists
        paper = supabase.table("papers").select("*").eq("title", title).eq("user_id", user_id).single().execute()
        if not paper.data:
            raise HTTPException(status_code=404, detail="Paper not found")

        # Delete from database
        supabase.table("papers").delete().eq("title", title).eq("user_id", user_id).execute()

        return {"message": "Paper deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {"message": "Research Paper AI API is running"}