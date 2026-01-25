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
    # Add this import at the top with other imports
from pydantic import BaseModel

# Add this class after your imports (before the endpoints)
class ChatRequest(BaseModel):
    question: str

# Add this endpoint after your other endpoints
@app.post("/papers/{paper_id}/chat")
async def chat_with_paper(
    paper_id: str,
    chat_request: ChatRequest,
    user_id: str = "default-user",
   
):
    """Chat with AI about a specific paper"""
    try:
        # 1. Get paper from database
        paper = supabase.table("papers").select("*").eq("id", paper_id).eq("user_id", user_id).single().execute()
        
        if not paper.data:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        # 2. Get paper content from storage
        file_path = paper.data["file_path"]
        file_bytes = supabase.storage.from_("research-papers").download(file_path)
        
        # 3. Extract text from PDF
        pdf_text = extract_text_from_pdf(file_bytes)
        
        # 4. Create AI prompt with paper context
        prompt = f"""You are an AI assistant helping someone understand a research paper.

Paper Title: {paper.data['title']}
Paper Abstract: {paper.data['abstract']}

Full Paper Text (first 8000 chars):
{pdf_text[:8000]}

User Question: {chat_request.question}

Please provide a clear, helpful answer based on the paper content above. If the question cannot be answered from the paper, say so politely."""

        # 5. Get AI response
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        response = model.generate_content(prompt)
        ai_answer = response.text.strip()
        
        # 6. Return response
        return {
            "question": chat_request.question,
            "answer": ai_answer,
            "paper_title": paper.data['title']
        }
        
    except Exception as e:
        print(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
# Add this import at the top with other imports
from pydantic import BaseModel

# Add this class after your imports (before the endpoints)
class ChatRequest(BaseModel):
    question: str

# Add this endpoint after your other endpoints
@app.post("/papers/{paper_id}/chat")
async def chat_with_paper(
    paper_id: str,
    chat_request: ChatRequest,
    user_id: str = "default-user",
   
):
    """Chat with AI about a specific paper"""
    try:
        # 1. Get paper from database
        paper = supabase.table("papers").select("*").eq("id", paper_id).eq("user_id", user_id).single().execute()
        
        if not paper.data:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        # 2. Get paper content from storage
        file_path = paper.data["file_path"]
        file_bytes = supabase.storage.from_("research-papers").download(file_path)
        
        # 3. Extract text from PDF
        pdf_text = extract_text_from_pdf(file_bytes)
        
        # 4. Create AI prompt with paper context
        prompt = f"""You are an AI assistant helping someone understand a research paper.

Paper Title: {paper.data['title']}
Paper Abstract: {paper.data['abstract']}

Full Paper Text (first 8000 chars):
{pdf_text[:8000]}

User Question: {chat_request.question}

Please provide a clear, helpful answer based on the paper content above. If the question cannot be answered from the paper, say so politely."""

        # 5. Get AI response
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        response = model.generate_content(prompt)
        ai_answer = response.text.strip()
        
        # 6. Return response
        return {
            "question": chat_request.question,
            "answer": ai_answer,
            "paper_title": paper.data['title']
        }
        
    except Exception as e:
        print(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/")
async def root():
    return {"message": "FastAPI File Upload Service is running"}

