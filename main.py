from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
import shutil
from pathlib import Path
from supabase import create_client, Client

from utils.pdf_extractor import extract_text_from_pdf
from utils.ai_extractor import extract_paper_info
from dotenv import load_dotenv

load_dotenv()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="FastAPI File Upload Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc)
    allow_headers=["*"],  # Allows all headers
)

# Initialize Supabase
supabase : Client =  create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

@app.post("/upload")
async def upload_single_file(file: UploadFile = File(...), user_id: str = "default-user"):
    """Upload a single file with basic validation"""
    if file.filename == "":
        raise HTTPException(status_code=400, detail="No file selected")
    
    file_path = UPLOAD_DIR / file.filename
    
    try:
        # 1. Read file bytes
        file_bytes = await file.read()

        # 3. Extract text from PDF
        pdf_text = extract_text_from_pdf(file_bytes)
        
        # 4. Use AI to extract structured information
        paper_info = extract_paper_info(pdf_text)

        print("Extracted Paper Info using AI: ", paper_info )
        
        # 5. Save to database
        db_response = supabase.table("papers").insert({
            "user_id": user_id,
            "title": paper_info["title"],
            "authors": paper_info["authors"],
            "abstract": paper_info["abstract"],
            "tags": paper_info["tags"],
            "file_url": paper_info["file_url"],
            "paper_id" : paper_info["paper_id"],
        }).execute()
        
        return {
            "message": "Paper uploaded and processed successfully",
            "paper": db_response.data[0]
        }
        
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
    
@app.delete("/papers/{title}")
async def delete_paper(
    title : str,
    user_id: str = "default-user"
    ):
    """Delete a paper"""
    try:
        # Get paper
        paper = supabase.table("papers").select("*").eq("title", title).eq("user_id", user_id).single().execute()
        if not paper.data:
            raise HTTPException(status_code=404, detail="Paper not found")
        
    
        
        # Delete from database
        supabase.table("papers").delete().eq("title", title).execute()
        
        return {"message": "Paper deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "FastAPI File Upload Service is running"}

