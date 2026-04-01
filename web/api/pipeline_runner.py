"""
pipeline_runner.py — Run the ai-mom CLI pipeline as a subprocess.
"""

import os
import re
import subprocess
import sys
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # ai-mom root


def run_pipeline(job_id: str, audio_path: str, job_store, **kwargs):
    """Run run.py as a subprocess, capturing output lines into job_store log."""
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "run.py"),
        "--audio", str(audio_path),
        "--model", kwargs.get("model", "small"),
        "--language", kwargs.get("language", "en"),
        "--engine", kwargs.get("engine", "whisper"),
        "--output-dir", str(PROJECT_ROOT / "output"),
    ]
    if kwargs.get("diarize"):
        cmd.append("--diarize")
    if kwargs.get("translate"):
        cmd.append("--translate")
    if kwargs.get("num_speakers"):
        cmd.extend(["--num-speakers", str(kwargs["num_speakers"])])
    if kwargs.get("title"):
        cmd.extend(["--title", kwargs["title"]])

    env = os.environ.copy()
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"

    # Load .env variables
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()

    job_store.update_job(job_id, status="loading", progress=5)

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            cwd=str(PROJECT_ROOT),
        )

        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            if "[TRANSCRIPT] " in line:
                job_store.append_transcript(job_id, line[line.index("[TRANSCRIPT] ") + len("[TRANSCRIPT] "):])
                continue
            if "[DIAR_SEGMENT] " in line:
                job_store.append_diar_segment(job_id, line[line.index("[DIAR_SEGMENT] ") + len("[DIAR_SEGMENT] "):])
                continue
            job_store.append_log(job_id, line)

            # Parse progress from known output patterns
            if "Loading faster-whisper" in line or "Loading" in line:
                job_store.update_job(job_id, status="loading", progress=10)
            elif "Transcribing" in line:
                job_store.update_job(job_id, status="transcribing", progress=30)
            elif "%" in line and "Transcrib" in line:
                m = re.search(r"(\d+)%", line)
                if m:
                    pct = int(m.group(1))
                    job_store.update_job(job_id, progress=30 + int(pct * 0.3))
            elif "Diarizing" in line:
                job_store.update_job(job_id, status="diarizing", progress=65)
            elif "cached diarization" in line.lower():
                job_store.update_job(job_id, status="diarizing", progress=70)
            elif "Gemini" in line or "summariz" in line.lower():
                job_store.update_job(job_id, status="summarizing", progress=90)
            elif "Output saved" in line or "Exported" in line:
                job_store.update_job(job_id, progress=95)

        proc.wait()

        if proc.returncode == 0:
            output_dir = PROJECT_ROOT / "output"
            stem = Path(audio_path).stem
            jsons = sorted(
                output_dir.glob("%s*.json" % stem),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            # Filter out jobs.json
            jsons = [j for j in jsons if j.name != "jobs.json"]
            result_path = str(jsons[0]) if jsons else None
            job_store.update_job(job_id, status="complete", progress=100, result_path=result_path)
        else:
            job_store.update_job(
                job_id,
                status="failed",
                error="Pipeline exited with code %d" % proc.returncode,
            )
    except Exception as exc:
        job_store.update_job(job_id, status="failed", error=str(exc))


def start_pipeline_thread(job_id: str, audio_path: str, job_store, **kwargs):
    """Launch the pipeline in a background thread."""
    t = threading.Thread(
        target=run_pipeline,
        args=(job_id, audio_path, job_store),
        kwargs=kwargs,
        daemon=True,
    )
    t.start()
    return t
