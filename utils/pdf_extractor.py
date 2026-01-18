import PyPDF2
from io import BytesIO  

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file given its byte content."""
    try:
        pdf_file = BytesIO(file_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        text = ""
        #Extract text from first 10 pages
        max_pages = min(10, len(pdf_reader.pages))
    
        for page_num in range(max_pages):
            page = pdf_reader.pages[page_num]
            text += page.extract_text()
        
        
        return text
    except Exception as e:
        raise ValueError(f"Error extracting text from PDF: {str(e)}")