import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def extract_paper_info(pdf_text: str) -> dict:
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""Analyze this research paper text and extract the following information in JSON format:

    1. title: The paper's title
    2. authors: List of author names
    3. abstract: The abstract or summary (2-3 sentences if no abstract found)
    4. tags: 3-5 relevant topic tags/keywords
    5. file_url: URL where the paper is hosted (if mentioned)
    6. paper_id: A unique identifier for the paper (e.g., DOI or arXiv ID; if not found, generate a random unique string)

    Paper text:
    {pdf_text[:8000]}

    Respond ONLY with valid JSON in this exact format:
    {{
    "title": "Paper Title Here",
    "authors": ["Author 1", "Author 2"],
    "abstract": "Abstract text here...",
    "tags": ["tag1", "tag2", "tag3"],
    "file_url": "URL here or empty string",
    "paper_id": "unique-paper-id-here"
    }}"""

    try:
        response = model.generate_content(prompt)
        # Clean response (remove markdown code blocks if present)
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith("```"):
            response_text = response_text[3:-3].strip()
            
        paper_info = json.loads(response_text)
        return paper_info
    except Exception as e:
        raise Exception(f"AI extraction error: {str(e)}")