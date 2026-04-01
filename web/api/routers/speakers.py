"""
routers/speakers.py — Speaker profile management endpoints.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

router = APIRouter(prefix="/api/speakers", tags=["speakers"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PROFILES_DIR = PROJECT_ROOT / "profiles"


def _get_env():
    env = os.environ.copy()
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


@router.get("")
async def list_speakers():
    """List all enrolled speaker profiles."""
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    profiles = []
    for f in sorted(PROFILES_DIR.glob("*.npy")):
        profiles.append({
            "name": f.stem,
            "file": f.name,
        })
    return profiles


def _to_wav(src: Path, dst: Path) -> None:
    """Convert any audio format to 16kHz mono WAV using ffmpeg."""
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(src), "-ar", "16000", "-ac", "1", str(dst)],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError("ffmpeg conversion failed: %s" % result.stderr.decode())


@router.post("/enroll")
async def enroll_speaker(
    name: str = Form(...),
    audio: UploadFile = File(...),
):
    """Enroll a new speaker from an audio file."""
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    name_slug = name.lower().replace(" ", "_")

    # Save the raw upload (may be webm, ogg, mp3, etc.)
    raw_path = PROFILES_DIR / ("enroll_%s_raw_%s" % (name_slug, audio.filename or "audio"))
    with open(raw_path, "wb") as f:
        shutil.copyfileobj(audio.file, f)

    # Always convert to 16kHz mono WAV — pyannote requires it
    wav_path = PROFILES_DIR / ("enroll_%s.wav" % name_slug)
    try:
        _to_wav(raw_path, wav_path)
    except RuntimeError as exc:
        raw_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        raw_path.unlink(missing_ok=True)

    # Run the embed worker in learn mode
    worker = PROJECT_ROOT / "src" / "_embed_worker.py"
    env = _get_env()

    inp = json.dumps({
        "audio_path": str(wav_path),
        "segments": [{"speaker": "SPEAKER_00", "start": 0.0, "end": 9999.0}],
        "speaker_map": {"SPEAKER_00": name},
        "hf_token": env.get("HF_TOKEN", ""),
    })

    proc = subprocess.run(
        [sys.executable, str(worker), "learn"],
        input=inp,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(PROJECT_ROOT),
    )

    wav_path.unlink(missing_ok=True)

    if proc.returncode == 0 and proc.stdout.strip():
        try:
            result = json.loads(proc.stdout)
            if result.get("learned"):
                return {"ok": True, "name": name, "learned": result["learned"]}
        except json.JSONDecodeError:
            pass

    error_msg = proc.stderr.strip() if proc.stderr else "Enrollment failed"
    raise HTTPException(status_code=500, detail=error_msg)


@router.post("/identify")
async def identify_speaker(
    audio: UploadFile = File(...),
):
    """Identify who is speaking from a short audio clip (~3s).
    Returns {"speaker": "Name" | null, "confidence": 0.0-1.0}.
    """
    from web.api.speaker_identifier import identify_speaker as _identify

    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = PROFILES_DIR / ("_identify_%s" % (audio.filename or "clip"))
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(audio.file, f)

    try:
        result = _identify(str(temp_path))
    finally:
        temp_path.unlink(missing_ok=True)

    return result


@router.delete("/{name}")
async def delete_speaker(name: str):
    """Delete a speaker profile."""
    profile = PROFILES_DIR / ("%s.npy" % name)
    if not profile.exists():
        raise HTTPException(status_code=404, detail="Profile not found")
    profile.unlink()
    return {"ok": True}
