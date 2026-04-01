"""
speaker_identifier.py — In-process speaker identification for real-time diarization.

Keeps the pyannote embedding model warm in memory so identification calls
take ~0.3s instead of ~3s (cold-start model load).
"""

import json
import logging
import os
import subprocess
import tempfile
import warnings
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore", message="Found keys that are not in the model state dict")
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROFILES_DIR = PROJECT_ROOT / "profiles"

_embedding_model = None


def _get_model():
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    try:
        from pyannote.audio import Inference
    except ImportError:
        logger.warning("pyannote.audio not installed — speaker identification unavailable")
        return None

    token = os.environ.get("HF_TOKEN", "")
    if not token:
        # Try loading from .env
        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("HF_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                    break

    if not token:
        logger.warning("HF_TOKEN not set — cannot load embedding model")
        return None

    try:
        _embedding_model = Inference(
            "pyannote/embedding", window="whole", use_auth_token=token
        )
        logger.info("Loaded pyannote/embedding model (warm)")
    except Exception as exc:
        logger.warning("Failed to load embedding model: %s", exc)
        return None

    return _embedding_model


def _load_profiles():
    """Load all enrolled speaker profiles from disk."""
    index_path = PROFILES_DIR / "index.json"
    if not index_path.exists():
        return {}
    try:
        index = json.loads(index_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}

    profiles = {}
    for name, filename in index.items():
        npy_path = PROFILES_DIR / filename
        if npy_path.exists():
            try:
                emb = np.load(npy_path)
                norm = np.linalg.norm(emb)
                if norm > 0:
                    emb = emb / norm
                profiles[name] = emb
            except Exception:
                pass
    return profiles


def _to_wav(src_path):
    """Convert audio to 16kHz mono WAV. Returns (wav_path, is_temp)."""
    if src_path.suffix.lower() == ".wav":
        return src_path, False
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", str(src_path), "-ar", "16000", "-ac", "1", tmp.name],
        capture_output=True,
    )
    if r.returncode != 0:
        os.unlink(tmp.name)
        return src_path, False
    return Path(tmp.name), True


def identify_speaker(audio_path):
    """Identify the speaker in a short audio clip.

    Returns {"speaker": name_or_None, "confidence": float}.
    """
    model = _get_model()
    profiles = _load_profiles()

    if model is None or not profiles:
        return {"speaker": None, "confidence": 0.0}

    audio_path = Path(audio_path)
    wav_path, is_tmp = _to_wav(audio_path)

    try:
        emb = model({"uri": "identify", "audio": str(wav_path)})
    except Exception as exc:
        logger.debug("Embedding extraction failed: %s", exc)
        return {"speaker": None, "confidence": 0.0}
    finally:
        if is_tmp:
            os.unlink(wav_path)

    # Normalize
    norm = np.linalg.norm(emb)
    if norm > 0:
        emb = emb / norm

    # Find best match
    best_name = None
    best_sim = 0.0
    for name, profile_emb in profiles.items():
        sim = float(np.dot(emb, profile_emb))
        if sim > best_sim:
            best_sim = sim
            best_name = name

    # Log for debugging
    import logging
    logging.getLogger(__name__).info(
        "identify: best=%s sim=%.3f (threshold=0.40)", best_name, best_sim
    )

    if best_sim >= 0.40:
        return {"speaker": best_name, "confidence": round(best_sim, 3)}
    return {"speaker": None, "confidence": round(best_sim, 3)}
