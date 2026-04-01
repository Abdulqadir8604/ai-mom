"""
soniox_transcriber.py — Soniox Speech-to-Text integration.

Uses the Soniox async API for high-quality transcription with built-in
speaker diarization. Requires SONIOX_API_KEY in environment.
"""

import json
import os
import sys
import time
from pathlib import Path

from src.ui import print_step, print_info, print_warning


def transcribe_soniox(audio_path, language="en", diarize=False, translate=False, step_total=3):
    """Transcribe audio using Soniox async API.

    Returns dict matching the Whisper pipeline format:
        text, duration, segments (with speaker_label), model_size, diar_segments
    """
    from soniox import SonioxClient
    from soniox.types import CreateTranscriptionConfig

    api_key = os.environ.get("SONIOX_API_KEY")
    if not api_key:
        raise RuntimeError("SONIOX_API_KEY not set. Get one at https://console.soniox.com")

    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError("Audio file not found: %s" % audio_path)

    client = SonioxClient(api_key=api_key)

    # Build config
    config_kwargs = {"model": "stt-async-v4"}

    if language and language not in ("auto", None):
        config_kwargs["language_hints"] = [language]
    else:
        config_kwargs["enable_language_identification"] = True

    if diarize:
        config_kwargs["enable_speaker_diarization"] = True

    config = CreateTranscriptionConfig(**config_kwargs)

    # Upload
    print_step(1, step_total, "Uploading to Soniox ...")
    uploaded = client.files.upload(str(audio_path))

    # Create transcription
    print_step(2, step_total, "Transcribing via Soniox (model=stt-async-v4) ...")
    transcription = client.stt.create(config=config, file_id=uploaded.id)

    # Poll
    while True:
        status = client.stt.get(transcription.id)
        if status.status == "completed":
            break
        if status.status == "error":
            try:
                client.stt.delete(transcription.id)
                client.files.delete(uploaded.id)
            except Exception:
                pass
            raise RuntimeError("Soniox transcription failed")
        time.sleep(1)

    # Get transcript
    transcript = client.stt.get_transcript(transcription.id)
    tokens = transcript.tokens

    # -- Build segments by splitting on speaker changes AND sentence boundaries --
    # Each segment = a sentence-ish chunk within a single speaker turn
    segments = []
    diar_segments = []
    full_text_parts = []

    current_speaker = None
    current_words = []
    current_start_ms = None
    current_end_ms = None

    def flush_segment():
        """Flush current words into a segment."""
        nonlocal current_words, current_start_ms, current_end_ms, current_speaker
        if not current_words:
            return
        text = "".join(current_words).strip()
        if not text:
            current_words = []
            return

        start_s = (current_start_ms or 0) / 1000.0
        end_s = (current_end_ms or 0) / 1000.0
        spk_label = "SPEAKER_%s" % str(int(current_speaker) - 1).zfill(2) if current_speaker else "Unknown"

        seg = {
            "id": len(segments),
            "text": text,
            "start": round(start_s, 2),
            "end": round(end_s, 2),
            "speaker_label": spk_label,
        }
        segments.append(seg)

        if diarize and current_speaker:
            diar_segments.append({
                "speaker": spk_label,
                "start": round(start_s, 2),
                "end": round(end_s, 2),
            })

        # Stream for web UI
        sys.stdout.write("[TRANSCRIPT] %s\n" % text)
        sys.stdout.flush()
        if diarize and current_speaker:
            sys.stdout.write("[DIAR_SEGMENT] %s\n" % json.dumps({
                "speaker": spk_label,
                "text": text,
                "start": round(start_s, 2),
                "end": round(end_s, 2),
            }))
            sys.stdout.flush()

        current_words = []
        current_start_ms = None
        current_end_ms = None

    for tok in tokens:
        text = tok.text
        speaker = getattr(tok, "speaker", None)
        start_ms = getattr(tok, "start_ms", None) or 0
        end_ms = getattr(tok, "end_ms", None) or 0

        full_text_parts.append(text)

        # Speaker change → flush
        if speaker != current_speaker and current_words:
            flush_segment()

        current_speaker = speaker

        if current_start_ms is None:
            current_start_ms = start_ms
        current_end_ms = end_ms
        current_words.append(text)

        # Sentence boundary → flush (split long monologues into readable chunks)
        stripped = text.strip()
        if stripped and stripped[-1] in ".!?,;:":
            # Only flush if we have at least ~5 words worth of text
            joined = "".join(current_words).strip()
            if len(joined) > 40:
                flush_segment()

    # Flush remaining
    flush_segment()

    full_text = "".join(full_text_parts).strip()

    # Duration from last token
    duration = 0.0
    if segments:
        duration = max(s["end"] for s in segments)

    # Cleanup
    try:
        client.stt.delete(transcription.id)
        client.files.delete(uploaded.id)
    except Exception:
        pass

    print_info("Soniox transcription complete (%.1f s, %d segments, %d speakers)." % (
        duration, len(segments),
        len(set(s.get("speaker", "") for s in diar_segments)) if diar_segments else 0,
    ))

    result = {
        "text": full_text,
        "duration": round(duration, 2),
        "segments": segments,
        "model_size": "soniox",
    }
    if diar_segments:
        result["diar_segments"] = diar_segments

    return result
