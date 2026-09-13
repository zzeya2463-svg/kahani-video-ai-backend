import os
import uuid
import shutil
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pipeline import run_video_pipeline

app = FastAPI(title="Kahani Video AI Backend")

# Allow CORS for potential web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated videos statically
os.makedirs("output_videos", exist_ok=True)
os.makedirs("temp_uploads", exist_ok=True)
app.mount("/videos", StaticFiles(directory="output_videos"), name="videos")

# In-memory job store (for production, use Redis or Postgres)
jobs = {}

@app.post("/api/v1/generate")
async def start_generation(
    request: Request,
    background_tasks: BackgroundTasks,
    story: str = Form(...),
    photos: List[UploadFile] = File(...)
):
    job_id = str(uuid.uuid4())
    base_url = str(request.base_url)
    
    # Save uploaded photos securely
    job_dir = os.path.join("temp_uploads", job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    saved_photo_paths = []
    for i, photo in enumerate(photos):
        file_extension = os.path.splitext(photo.filename)[1] if photo.filename else ".jpg"
        safe_filename = f"scene_{i}{file_extension}"
        file_path = os.path.join(job_dir, safe_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)
        saved_photo_paths.append(file_path)

    # Initialize job state
    jobs[job_id] = {
        "job_id": job_id,
        "status": "PROCESSING",
        "progress": 0.0,
        "status_message": "वीडियो बनाने की प्रक्रिया शुरू हो रही है...",
        "video_url": None,
        "error": None
    }

    # Kick off background pipeline
    background_tasks.add_task(run_video_pipeline, job_id, story, saved_photo_paths, jobs, base_url)

    return {"job_id": job_id, "message": "Generation started successfully"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/v1/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    return jobs[job_id]

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
