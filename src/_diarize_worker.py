"""
_diarize_worker.py — Subprocess entry point for speaker diarization.

Run in an isolated process to avoid OpenMP conflicts between CTranslate2
(faster-whisper) and pyannote/torch when both are loaded in the same process.

Called by pipeline.py via subprocess. Reads args from CLI, writes JSON to stdout.
Token is read from HF_TOKEN env var (never passed as CLI arg).

Usage (internal):
    python -m src._diarize_worker <audio_path> [<num_speakers>]
"""
import os
import warnings
warnings.filterwarnings("ignore", message="Found keys that are not in the model state dict")
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import json
import sys
import tempfile
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from src.diarization import diarize_audio

    audio_path = sys.argv[1]
    num_speakers = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] != "None" else None
    hf_token = os.environ.get("HF_TOKEN")

    # Pre-downsample to 16kHz mono before passing to pyannote.
    # pyannote internally resamples to 16kHz mono anyway — doing it upfront
    # with pydub means pyannote processes a much smaller file, cutting first-run
    # diarization time by 20-40% on stereo or high-sample-rate recordings.
    tmp_path = None
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(audio_path)
        audio = audio.set_channels(1).set_frame_rate(16000)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        audio.export(tmp_path, format="wav")
        diar_input = tmp_path
    except Exception:
        # pydub unavailable or conversion failed — use original file
        diar_input = audio_path

    try:
        segments = diarize_audio(diar_input, hf_token=hf_token, num_speakers=num_speakers)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    print(json.dumps(segments))

except Exception as exc:
    sys.stderr.write("_diarize_worker error: %s\n" % exc)
    sys.exit(1)
