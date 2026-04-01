"""
job_store.py — In-memory + JSON file store for pipeline jobs.
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4


JOBS_FILE = Path(__file__).resolve().parent.parent.parent / "output" / "jobs.json"


class JobStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._jobs: dict[str, dict] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self):
        if JOBS_FILE.exists():
            try:
                data = json.loads(JOBS_FILE.read_text())
                if isinstance(data, list):
                    for j in data:
                        self._jobs[j["id"]] = j
                elif isinstance(data, dict):
                    self._jobs = data
            except Exception:
                self._jobs = {}

    def _save(self):
        JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
        JOBS_FILE.write_text(json.dumps(list(self._jobs.values()), indent=2, default=str))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_job(
        self,
        filename: str,
        title: str = "",
        language: str = "en",
        model: str = "small",
        diarize: bool = False,
        num_speakers: Optional[int] = None,
    ) -> dict:
        job_id = uuid4().hex[:8]
        job = {
            "id": job_id,
            "title": title or Path(filename).stem,
            "filename": filename,
            "status": "queued",
            "progress": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": None,
            "language": language,
            "model": model,
            "num_speakers": num_speakers,
            "diarize": diarize,
            "log": [],
            "transcript": [],
            "diar_segments": [],
            "result_path": None,
            "error": None,
        }
        with self._lock:
            self._jobs[job_id] = job
            self._save()
        return job

    def update_job(self, job_id: str, **kwargs) -> Optional[dict]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            for k, v in kwargs.items():
                if k in job:
                    job[k] = v
            self._save()
            return dict(job)

    def append_log(self, job_id: str, line: str):
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job["log"].append(line)
                # Don't save on every log line for performance

    def append_transcript(self, job_id: str, text: str):
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                if "transcript" not in job:
                    job["transcript"] = []
                job["transcript"].append(text)

    def append_diar_segment(self, job_id: str, json_text: str):
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                if "diar_segments" not in job:
                    job["diar_segments"] = []
                job["diar_segments"].append(json_text)

    def get_diar_segments(self, job_id: str, after: int = 0) -> list[str]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return []
            return list(job.get("diar_segments", [])[after:])

    def get_transcript_chunks(self, job_id: str, after: int = 0) -> list[str]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return []
            return list(job.get("transcript", [])[after:])

    def get_job(self, job_id: str) -> Optional[dict]:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def list_jobs(self) -> list[dict]:
        with self._lock:
            jobs = sorted(
                self._jobs.values(),
                key=lambda j: j.get("created_at", ""),
                reverse=True,
            )
            return [dict(j) for j in jobs]

    def delete_job(self, job_id: str) -> bool:
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                self._save()
                return True
            return False

    def get_log_lines(self, job_id: str, after: int = 0) -> list[str]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return []
            return list(job["log"][after:])
