"""
speaker_profiles.py — Phase 2: Silent Speaker Learning.

Extracts voice embeddings from diarized audio, stores them under real names,
and auto-matches voices to known profiles on future meetings.
"""

import json
import logging
import re
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = PROJECT_ROOT / "profiles"

MIN_TALK_SECONDS = 2.0  # ignore speakers with < 2s total talk time


# ---------------------------------------------------------------------------
# 1. extract_speaker_embeddings
# ---------------------------------------------------------------------------

def extract_speaker_embeddings(audio_path, diarization_segments, hf_token=None):
    """Extract mean embedding per speaker from audio.

    For each unique speaker label in *diarization_segments*, collect all their
    segments, extract embeddings for each, and average them.

    Returns
    -------
    dict
        speaker_label -> mean_embedding (numpy array, 512-dim).
        Skips speakers with < 2 seconds total talk time.
        Returns {} if pyannote embedding model is unavailable.
    """
    if not diarization_segments:
        return {}

    try:
        from pyannote.audio import Inference
        from pyannote.core import Segment
    except ImportError:
        logger.warning("pyannote.audio not available — cannot extract embeddings.")
        return {}

    import os
    token = hf_token or os.environ.get("HF_TOKEN")
    if not token:
        logger.warning("HF_TOKEN not set — cannot load embedding model.")
        return {}

    try:
        embedding_model = Inference(
            "pyannote/embedding", window="whole", use_auth_token=token
        )
    except Exception as exc:
        logger.warning("Failed to load pyannote/embedding model: %s", exc)
        return {}

    # Group segments by speaker and compute total talk time
    speaker_segs = {}  # speaker_label -> list of (start, end)
    for seg in diarization_segments:
        label = seg["speaker"]
        speaker_segs.setdefault(label, []).append((seg["start"], seg["end"]))

    results = {}
    audio_str = str(audio_path)

    for label, segs in speaker_segs.items():
        total_time = sum(end - start for start, end in segs)
        if total_time < MIN_TALK_SECONDS:
            logger.info(
                "Skipping speaker %s — only %.1fs of talk time.", label, total_time
            )
            continue

        embeddings = []
        for start, end in segs:
            duration = end - start
            if duration < 0.5:
                continue  # skip very short segments (noisy)
            try:
                emb = embedding_model(
                    {"uri": "meeting", "audio": audio_str},
                    Segment(start, end),
                )
                embeddings.append(emb)
            except Exception as exc:
                logger.debug("Embedding extraction failed for %s [%.1f-%.1f]: %s",
                             label, start, end, exc)

        if embeddings:
            mean_emb = np.mean(embeddings, axis=0)
            # Normalize to unit vector for consistent cosine similarity
            norm = np.linalg.norm(mean_emb)
            if norm > 0:
                mean_emb = mean_emb / norm
            results[label] = mean_emb

    return results


# ---------------------------------------------------------------------------
# 2. save_speaker_profile
# ---------------------------------------------------------------------------

def save_speaker_profile(name, embedding, profiles_dir=None):
    """Save or update a speaker profile on disk.

    If the profile already exists, blend the new embedding with the stored one
    using a running average (0.7 * existing + 0.3 * new) to improve over time.

    Files:
        profiles/<safe_name>.npy  — the embedding vector
        profiles/index.json       — maps name -> filename
    """
    pdir = Path(profiles_dir) if profiles_dir else PROFILES_DIR
    pdir.mkdir(parents=True, exist_ok=True)

    index_path = pdir / "index.json"
    index = {}
    if index_path.exists():
        try:
            with open(index_path, "r", encoding="utf-8") as fh:
                index = json.load(fh)
        except (json.JSONDecodeError, OSError):
            index = {}

    # Determine filename (reuse existing or create new)
    if name in index:
        filename = index[name]
    else:
        # Sanitize name for filesystem
        safe = re.sub(r"[^\w\-]", "_", name).strip("_")
        if not safe:
            safe = "speaker"
        filename = safe + ".npy"
        # Avoid collisions
        counter = 1
        while (pdir / filename).exists() and filename not in index.values():
            filename = "%s_%d.npy" % (safe, counter)
            counter += 1

    npy_path = pdir / filename

    # Blend with existing profile if present
    if npy_path.exists():
        try:
            existing = np.load(npy_path)
            blended = 0.7 * existing + 0.3 * embedding
            # Re-normalize
            norm = np.linalg.norm(blended)
            if norm > 0:
                blended = blended / norm
            embedding = blended
        except Exception as exc:
            logger.warning("Could not load existing profile %s: %s", npy_path, exc)

    np.save(npy_path, embedding)

    # Update index
    index[name] = filename
    with open(index_path, "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    logger.info("Saved speaker profile: %s -> %s", name, filename)


# ---------------------------------------------------------------------------
# 3. load_all_profiles
# ---------------------------------------------------------------------------

def load_all_profiles(profiles_dir=None):
    """Load all stored speaker profiles from disk.

    Returns
    -------
    dict
        name -> embedding (numpy array).
        Returns {} if profiles dir is empty or missing.
    """
    pdir = Path(profiles_dir) if profiles_dir else PROFILES_DIR

    index_path = pdir / "index.json"
    if not index_path.exists():
        return {}

    try:
        with open(index_path, "r", encoding="utf-8") as fh:
            index = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}

    profiles = {}
    for name, filename in index.items():
        npy_path = pdir / filename
        if npy_path.exists():
            try:
                profiles[name] = np.load(npy_path)
            except Exception as exc:
                logger.warning("Could not load profile %s: %s", npy_path, exc)

    return profiles


# ---------------------------------------------------------------------------
# 4. match_speakers
# ---------------------------------------------------------------------------

def match_speakers(speaker_embeddings, profiles, threshold=0.55):
    """Match detected speaker labels to known profiles using cosine similarity.

    Parameters
    ----------
    speaker_embeddings : dict
        speaker_label -> embedding (numpy array) from current meeting.
    profiles : dict
        name -> embedding (numpy array) from stored profiles.
    threshold : float
        Minimum cosine similarity to accept a match (default 0.85).

    Returns
    -------
    dict
        speaker_label -> matched_name (str or None if no match above threshold).
    """
    if not speaker_embeddings or not profiles:
        return {}

    matches = {}
    used_names = set()  # prevent two speakers matching the same profile

    # Build list of (label, embedding) and (name, embedding) for matching
    label_list = list(speaker_embeddings.items())
    name_list = list(profiles.items())

    # Compute all similarities, then greedily assign best matches
    all_scores = []
    for label, emb_a in label_list:
        for name, emb_b in name_list:
            norm_a = np.linalg.norm(emb_a)
            norm_b = np.linalg.norm(emb_b)
            if norm_a == 0 or norm_b == 0:
                sim = 0.0
            else:
                sim = float(np.dot(emb_a, emb_b) / (norm_a * norm_b))
            all_scores.append((sim, label, name))

    # Sort descending by similarity — greedy best-first assignment
    all_scores.sort(key=lambda x: x[0], reverse=True)

    assigned_labels = set()
    for sim, label, name in all_scores:
        if sim < threshold:
            break  # remaining scores are all below threshold
        if label in assigned_labels or name in used_names:
            continue
        matches[label] = name
        assigned_labels.add(label)
        used_names.add(name)

    # Fill unmatched labels with None
    for label in speaker_embeddings:
        if label not in matches:
            matches[label] = None

    return matches


# ---------------------------------------------------------------------------
# 5. learn_from_speaker_map
# ---------------------------------------------------------------------------

def learn_from_speaker_map(audio_path, diarization_segments, speaker_map, hf_token=None):
    """Called after user edits speaker_map.json.

    For each entry in *speaker_map* where the value differs from the key
    (i.e. user has assigned a real name), extract embeddings for that speaker
    and save their profile.

    This is the "silent learning" step -- called automatically when a speaker
    map with real names is applied.
    """
    if not speaker_map or not diarization_segments:
        return

    # Identify speakers that have been given real names
    renamed = {
        label: name
        for label, name in speaker_map.items()
        if name and name != label
    }
    if not renamed:
        return

    logger.info("Learning speaker profiles for: %s", list(renamed.values()))

    embeddings = extract_speaker_embeddings(
        audio_path, diarization_segments, hf_token=hf_token
    )
    if not embeddings:
        logger.info("No embeddings extracted — skipping profile learning.")
        return

    for label, real_name in renamed.items():
        if label in embeddings:
            save_speaker_profile(real_name, embeddings[label])
            logger.info("Learned profile for '%s' from %s.", real_name, label)
        else:
            logger.info(
                "No embedding for %s (too little talk time?) — skipping '%s'.",
                label, real_name,
            )
