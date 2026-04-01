"""
routers/jobs.py — Job management endpoints.
"""

import asyncio
import shutil
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from web.api.job_store import JobStore
from web.api.pipeline_runner import start_pipeline_thread

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
UPLOAD_DIR = PROJECT_ROOT / "output" / "uploads"

# Shared job store — singleton
_store: JobStore | None = None


def get_store() -> JobStore:
    global _store
    if _store is None:
        _store = JobStore()
    return _store


@router.post("")
async def create_job(
    audio: UploadFile = File(...),
    title: str = Form(""),
    language: str = Form("en"),
    model: str = Form("small"),
    engine: str = Form("whisper"),
    diarize: bool = Form(False),
    translate: bool = Form(False),
    num_speakers: int | None = Form(None),
):
    store = get_store()

    # Save uploaded file
    job_temp_id = __import__("uuid").uuid4().hex[:8]
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = audio.filename.replace("/", "_").replace("\\", "_")
    dest = UPLOAD_DIR / ("%s_%s" % (job_temp_id, safe_name))

    with open(dest, "wb") as f:
        shutil.copyfileobj(audio.file, f)

    # Create job
    job = store.create_job(
        filename=safe_name,
        title=title,
        language=language,
        model=model,
        diarize=diarize,
        num_speakers=num_speakers,
    )

    # Start pipeline in background
    start_pipeline_thread(
        job_id=job["id"],
        audio_path=str(dest),
        job_store=store,
        model=model,
        language=language,
        engine=engine,
        diarize=diarize,
        translate=translate,
        num_speakers=num_speakers,
        title=title or None,
    )

    return job


@router.get("")
async def list_jobs():
    return get_store().list_jobs()


@router.get("/{job_id}")
async def get_job(job_id: str):
    job = get_store().get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    if not get_store().delete_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True}


@router.get("/{job_id}/events")
async def job_events(job_id: str):
    """SSE endpoint — streams log lines as they arrive."""
    store = get_store()
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        log_cursor        = 0
        transcript_cursor = 0
        diar_cursor       = 0
        while True:
            lines = store.get_log_lines(job_id, after=log_cursor)
            for line in lines:
                yield "data: %s\n\n" % line
                log_cursor += 1

            chunks = store.get_transcript_chunks(job_id, after=transcript_cursor)
            for text in chunks:
                yield "event: transcript\ndata: %s\n\n" % text
                transcript_cursor += 1

            diar_segs = store.get_diar_segments(job_id, after=diar_cursor)
            for seg_json in diar_segs:
                yield "event: diar\ndata: %s\n\n" % seg_json
                diar_cursor += 1

            current = store.get_job(job_id)
            if not current:
                yield "data: [DONE]\n\n"
                break
            if current["status"] in ("complete", "failed"):
                # Flush remaining
                for line in store.get_log_lines(job_id, after=log_cursor):
                    yield "data: %s\n\n" % line
                    log_cursor += 1
                for text in store.get_transcript_chunks(job_id, after=transcript_cursor):
                    yield "event: transcript\ndata: %s\n\n" % text
                    transcript_cursor += 1
                for seg_json in store.get_diar_segments(job_id, after=diar_cursor):
                    yield "event: diar\ndata: %s\n\n" % seg_json
                    diar_cursor += 1
                if current["status"] == "failed" and current.get("error"):
                    yield "data: ERROR: %s\n\n" % current["error"]
                yield "data: [DONE]\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
