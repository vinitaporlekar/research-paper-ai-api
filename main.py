from fastapi import FastAPI

app = FastAPI(title="FastAPI File Upload Service")

@app.get("/")
async def root():
    return {"message": "FastAPI File Upload Service is running"}