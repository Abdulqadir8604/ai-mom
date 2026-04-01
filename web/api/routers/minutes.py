"""
routers/minutes.py — Serve processed meeting minutes.
"""

import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from web.api.routers.jobs import get_store

router = APIRouter(prefix="/api/minutes", tags=["minutes"])


def _find_md_file(json_path):
    """Find the most recent markdown file matching the same stem prefix."""
    json_path = Path(json_path)
    parent = json_path.parent
    # Strip timestamp suffix to get base stem (e.g. b1d20181_harvard)
    # Pattern: stem ends with _YYYYMMDD_HHMMSS
    base = re.sub(r"_\d{8}_\d{6}$", "", json_path.stem)
    candidates = sorted(
        parent.glob("%s*_minutes_*.md" % base),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        # fallback: any matching md
        candidates = sorted(
            parent.glob("%s*.md" % base),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    return candidates[0] if candidates else None


def _parse_markdown(md_text):
    """Extract structured fields from the minutes markdown file."""
    result = {
        "session_summary": "",
        "key_decisions": [],
        "action_items": [],
        "deadlines": [],
        "next_steps": [],
        "qa_pairs": [],
        "transcript_text": "",
    }

    # Session Summary
    m = re.search(r"## \d+\.\s+Session Summary\s*\n+(.*?)(?=\n## |\Z)", md_text, re.DOTALL)
    if m:
        text = m.group(1).strip()
        if text and text != "*No summary recorded.*":
            result["session_summary"] = text

    # Key Decisions — numbered list
    m = re.search(r"## \d+\.\s+Key Decisions\s*\n+(.*?)(?=\n## |\Z)", md_text, re.DOTALL)
    if m:
        block = m.group(1).strip()
        if block and "*No" not in block:
            items = re.findall(r"^\d+\.\s+(.+)$", block, re.MULTILINE)
            if not items:
                items = re.findall(r"^[-*]\s+(.+)$", block, re.MULTILINE)
            result["key_decisions"] = items

    # Action Items — markdown table
    m = re.search(r"## \d+\.\s+Action Items\s*\n+(.*?)(?=\n## |\Z)", md_text, re.DOTALL)
    if m:
        block = m.group(1).strip()
        rows = re.findall(r"^\|([^|]+)\|([^|]+)\|([^|]+)\|", block, re.MULTILINE)
        for row in rows:
            owner, action, due = [c.strip() for c in row]
            if owner.lower() in ("owner", "---", ""):
                continue
            result["action_items"].append({"owner": owner, "action": action, "due": due})

    # Next Steps
    m = re.search(r"## \d+\.\s+Next Steps\s*\n+(.*?)(?=\n## |\Z)", md_text, re.DOTALL)
    if m:
        block = m.group(1).strip()
        if block and "*No" not in block:
            items = re.findall(r"^\d+\.\s+(.+)$", block, re.MULTILINE)
            result["next_steps"] = items

    # Q&A
    m = re.search(r"## \d+\.\s+Questions.*?\n+(.*?)(?=\n## |\Z)", md_text, re.DOTALL)
    if m:
        block = m.group(1).strip()
        if block and "*No" not in block:
            pairs = re.findall(r"\*\*Q.*?\*\*:\s*(.+?)\s*\n\s*\*\*A.*?\*\*:\s*(.+?)(?=\n\*\*Q|\Z)", block, re.DOTALL)
            result["qa_pairs"] = [{"question": q.strip(), "answer": a.strip()} for q, a in pairs]

    # Transcript (raw block)
    m = re.search(r"## Transcript\s*\n+```\s*\n(.*?)```", md_text, re.DOTALL)
    if m:
        result["transcript_text"] = m.group(1).strip()

    return result


def _parse_transcript_segments(speaker_transcript):
    """Parse the speaker_transcript string into a list of segment dicts."""
    if not speaker_transcript:
        return []

    segments = []
    current_speaker = None
    current_lines = []

    for line in speaker_transcript.splitlines():
        # Speaker header: [SPEAKER_00]    text...
        header_match = re.match(r"^\[([^\]]+)\]\s*(.*)", line)
        if header_match:
            if current_speaker is not None:
                segments.append({
                    "speaker_label": current_speaker,
                    "text": " ".join(current_lines).strip(),
                })
            current_speaker = header_match.group(1)
            first_text = header_match.group(2).strip()
            current_lines = [first_text] if first_text else []
        elif line.strip() and current_speaker is not None:
            current_lines.append(line.strip())

    if current_speaker is not None and current_lines:
        segments.append({
            "speaker_label": current_speaker,
            "text": " ".join(current_lines).strip(),
        })

    return segments


@router.get("/{job_id}")
async def get_minutes(job_id: str):
    """Return unified minutes data for a completed job."""
    store = get_store()
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "complete":
        raise HTTPException(status_code=400, detail="Job not complete yet")

    result_path = job.get("result_path")
    if not result_path or not Path(result_path).exists():
        raise HTTPException(status_code=404, detail="Result file not found")

    # Load raw pipeline JSON
    raw = json.loads(Path(result_path).read_text())

    # Parse speaker_transcript into segments
    segments = _parse_transcript_segments(raw.get("speaker_transcript", ""))

    # Build unified response
    response = {
        "title": job.get("title", raw.get("audio", "")),
        "date": raw.get("timestamp", ""),
        "duration_seconds": raw.get("duration_seconds"),
        "language": job.get("language", "en"),
        "model": raw.get("model_used", ""),
        "speaker_times": raw.get("speaker_times", {}),
        "attendance": raw.get("attendance", {}),
        "segments": segments,
        "transcript": raw.get("correct_text") or raw.get("whisper_output", ""),
        # defaults — overridden by markdown below
        "session_summary": "",
        "key_decisions": [],
        "action_items": [],
        "deadlines": [],
        "next_steps": [],
        "qa_pairs": [],
    }

    # Enrich with parsed markdown (has Gemini-generated summary/decisions/etc.)
    md_path = _find_md_file(result_path)
    if md_path and md_path.exists():
        parsed = _parse_markdown(md_path.read_text())
        response.update({k: v for k, v in parsed.items() if v})
        # Use transcript segments from markdown if pipeline didn't produce any
        if not segments and parsed.get("transcript_text"):
            response["segments"] = _parse_transcript_segments(parsed["transcript_text"])

    return response


@router.get("/{job_id}/markdown")
async def get_minutes_markdown(job_id: str):
    """Return the .md file content for a completed job."""
    store = get_store()
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "complete":
        raise HTTPException(status_code=400, detail="Job not complete yet")

    result_path = job.get("result_path")
    if not result_path:
        raise HTTPException(status_code=404, detail="Result file not found")

    md_path = _find_md_file(result_path)
    if not md_path or not md_path.exists():
        raise HTTPException(status_code=404, detail="Markdown file not found")

    return PlainTextResponse(md_path.read_text(), media_type="text/markdown")
