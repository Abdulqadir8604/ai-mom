"""
_embed_worker.py — Subprocess entry point for speaker embedding work.

Run in an isolated process to avoid OpenMP conflicts between CTranslate2
(faster-whisper) and pyannote/torch when both are loaded in the same process.

Called by pipeline.py via subprocess. Reads JSON from stdin, writes JSON to stdout.
Token is read from input JSON or HF_TOKEN env var.

Modes:
    match  — auto-match detected speakers to known voice profiles
    learn  — learn new speaker profiles from a corrected speaker map

Usage (internal):
    echo '{"audio_path": "...", "segments": [...]}' | python -m src._embed_worker match
    echo '{"audio_path": "...", "segments": [...], "speaker_map": {...}}' | python -m src._embed_worker learn
"""
import os
import warnings
warnings.filterwarnings("ignore", message="Found keys that are not in the model state dict")
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def _ensure_wav(audio_path):
    """Convert any audio to 16kHz mono WAV via ffmpeg if it isn't already WAV.
    Returns (path_str, is_tmp) — caller must delete the file if is_tmp=True.
    """
    if Path(audio_path).suffix.lower() == ".wav":
        return audio_path, False
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", audio_path, "-ar", "16000", "-ac", "1", tmp.name],
        capture_output=True,
    )
    if r.returncode != 0:
        os.unlink(tmp.name)
        return audio_path, False   # fall back; let pyannote try
    return tmp.name, True

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: _embed_worker.py <match|learn>\n")
        sys.exit(1)

    mode = sys.argv[1]  # "match" or "learn"
    data = json.loads(sys.stdin.read())

    if mode == "match":
        from src.speaker_profiles import load_all_profiles, extract_speaker_embeddings, match_speakers

        profiles = load_all_profiles()
        if not profiles:
            print(json.dumps({"matches": {}}))
            sys.exit(0)

        segments = data["segments"]
        hf_token = data.get("hf_token") or os.environ.get("HF_TOKEN")

        wav_path, is_tmp = _ensure_wav(data["audio_path"])
        try:
            speaker_embs = extract_speaker_embeddings(wav_path, segments, hf_token=hf_token)
            matches = match_speakers(speaker_embs, profiles) if speaker_embs else {}
        finally:
            if is_tmp:
                os.unlink(wav_path)
        print(json.dumps({"matches": matches}))

    elif mode == "learn":
        from src.speaker_profiles import learn_from_speaker_map

        profiles_dir = Path(__file__).resolve().parent.parent / "profiles"

        # Snapshot .npy files before learning
        before = {}
        if profiles_dir.exists():
            for f in profiles_dir.glob("*.npy"):
                before[f.name] = f.stat().st_mtime

        wav_path, is_tmp = _ensure_wav(data["audio_path"])
        try:
            learn_from_speaker_map(
                wav_path,
                data["segments"],
                data["speaker_map"],
                hf_token=data.get("hf_token") or os.environ.get("HF_TOKEN"),
            )
        finally:
            if is_tmp:
                os.unlink(wav_path)

        # Check which .npy files were actually created or updated
        learned = []
        if profiles_dir.exists():
            for label, name in data["speaker_map"].items():
                if name and name != label:
                    safe_name = name.replace(" ", "_")
                    npy_file = profiles_dir / ("%s.npy" % safe_name)
                    if npy_file.exists():
                        mtime = npy_file.stat().st_mtime
                        old_mtime = before.get(npy_file.name)
                        if old_mtime is None or mtime > old_mtime:
                            learned.append(name)

        print(json.dumps({"learned": learned}))

    else:
        print(json.dumps({"error": "Unknown mode: %s" % mode}), file=sys.stderr)
        sys.exit(1)

except Exception as exc:
    sys.stderr.write("_embed_worker error: %s\n" % exc)
    sys.exit(1)
