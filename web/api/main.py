"""
main.py — FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from web.api.routers import jobs, speakers, minutes

app = FastAPI(
    title="AI MOM — Meeting Minutes Generator",
    version="1.0.0",
    description="Web API for AI-powered meeting transcription and minute generation.",
)

# CORS — allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(jobs.router)
app.include_router(speakers.router)
app.include_router(minutes.router)

# Serve uploaded files
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "output" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
