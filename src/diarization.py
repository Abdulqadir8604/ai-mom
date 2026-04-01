"""
diarization.py — Phase 1: Unsupervised speaker diarization.

Uses pyannote/speaker-diarization-3.1 to detect who spoke when,
aligns diarization segments with Whisper word-level timestamps,
and provides talk-time analytics plus a speaker-map sidecar file.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from src.ui import print_warning

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. diarize_audio
# ---------------------------------------------------------------------------

def diarize_audio(audio_path, hf_token=None, num_speakers=None):
    """Run pyannote speaker diarization on *audio_path*.

    Parameters
    ----------
    audio_path : str or Path
        Path to the audio file.
    hf_token : str or None
        Hugging Face access token required by pyannote.audio models.
        When None, falls back to ``HF_TOKEN`` environment variable.
    num_speakers : int or None
        Exact number of speakers in the audio. When provided, overrides
        pyannote's automatic speaker count detection. Use this when you
        know how many people are in the meeting.

    Returns
    -------
    list of dict
        Each dict has keys: ``speaker`` (str), ``start`` (float), ``end`` (float).
        Returns an empty list if diarization is unavailable or fails.
    """
    token = hf_token or os.environ.get("HF_TOKEN")
    if not token:
        logger.warning("HF_TOKEN not set — skipping diarization.")
        print_warning("HF_TOKEN not set. Skipping diarization.")
        return []

    try:
        from pyannote.audio import Pipeline as PyannotePipeline  # deferred import

        # Patch the hf_hub_download reference inside pyannote's pipeline module
        # to convert the legacy use_auth_token kwarg → token (removed in hub ≥1.0).
        import pyannote.audio.core.pipeline as _pyannote_pipeline
        _orig_download = _pyannote_pipeline.hf_hub_download
        def _patched_download(*args, **kwargs):
            if "use_auth_token" in kwargs:
                kwargs["token"] = kwargs.pop("use_auth_token")
            return _orig_download(*args, **kwargs)
        _pyannote_pipeline.hf_hub_download = _patched_download
    except ImportError:
        logger.warning("pyannote.audio is not installed — skipping diarization.")
        print_warning(
            "pyannote.audio is not installed. "
            "Run: .venv/bin/pip install pyannote.audio"
        )
        return []

    try:
        pipeline = PyannotePipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=token,
        )
        diar_kwargs = {}
        if num_speakers is not None:
            diar_kwargs["num_speakers"] = num_speakers
        diarization = pipeline(str(audio_path), **diar_kwargs)
    except Exception as exc:
        logger.warning("Diarization failed: %s", exc)
        print_warning("Diarization failed (%s). Continuing without it." % exc)
        return []

    segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append({
            "speaker": speaker,
            "start": round(turn.start, 3),
            "end": round(turn.end, 3),
        })

    return segments


# ---------------------------------------------------------------------------
# 2. align_transcript_speakers  (word-level when available)
# ---------------------------------------------------------------------------

def _assign_word_to_speaker(word_mid, diarization_segments):
    """Find the speaker active at *word_mid*. Returns speaker label or None."""
    for d_seg in diarization_segments:
        if d_seg["start"] <= word_mid <= d_seg["end"]:
            return d_seg["speaker"]
    # Fallback: nearest diarization segment by midpoint distance
    best = min(
        diarization_segments,
        key=lambda s: abs((s["start"] + s["end"]) / 2 - word_mid),
    )
    return best["speaker"]


def align_transcript_speakers(whisper_segments, diarization_segments):
    """Attach a speaker label to each Whisper segment based on diarization.

    When word-level timestamps are available (``word_timestamps=True`` in
    Whisper), each word is individually matched to a diarization segment and
    the segment's speaker is determined by majority vote across its words.
    This is significantly more accurate than segment-midpoint matching,
    especially for segments that straddle a speaker change.

    Falls back to segment-midpoint matching when words are not available.

    Parameters
    ----------
    whisper_segments : list of dict
        Whisper segment dicts (must have ``start`` and ``end`` keys).
        May optionally contain a ``words`` list of word-level dicts.
    diarization_segments : list of dict
        Output of :func:`diarize_audio` — each has ``speaker``, ``start``, ``end``.

    Returns
    -------
    list of dict
        The same Whisper segments with an added ``speaker_label`` key.
    """
    if not diarization_segments:
        for seg in whisper_segments:
            seg.setdefault("speaker_label", "UNKNOWN")
        return whisper_segments

    for seg in whisper_segments:
        words = seg.get("words")

        if words:
            # --- Word-level majority vote ---
            votes = {}  # type: Dict[str, int]
            for w in words:
                w_start = w.get("start", 0.0)
                w_end = w.get("end", 0.0)
                word_mid = (w_start + w_end) / 2.0
                speaker = _assign_word_to_speaker(word_mid, diarization_segments)
                votes[speaker] = votes.get(speaker, 0) + 1

            # Majority wins
            seg["speaker_label"] = max(votes, key=votes.get)
        else:
            # --- Fallback: segment midpoint ---
            mid = (seg.get("start", 0.0) + seg.get("end", 0.0)) / 2.0

            matched_speaker = None
            for d_seg in diarization_segments:
                if d_seg["start"] <= mid <= d_seg["end"]:
                    matched_speaker = d_seg["speaker"]
                    break

            if matched_speaker is None:
                best_dist = float("inf")
                for d_seg in diarization_segments:
                    d_mid = (d_seg["start"] + d_seg["end"]) / 2.0
                    dist = abs(mid - d_mid)
                    if dist < best_dist:
                        best_dist = dist
                        matched_speaker = d_seg["speaker"]

            seg["speaker_label"] = matched_speaker or "UNKNOWN"

    return whisper_segments


# ---------------------------------------------------------------------------
# 2b. build_speaker_transcript
# ---------------------------------------------------------------------------

def build_speaker_transcript(whisper_segments):
    """Build a formatted speaker-attributed transcript string.

    Groups consecutive segments by the same speaker into blocks and
    formats them with aligned speaker tags.

    Parameters
    ----------
    whisper_segments : list of dict
        Whisper segments that have been annotated with ``speaker_label``.

    Returns
    -------
    str
        Formatted transcript with speaker tags, or empty string if no
        segments contain text.
    """
    speaker_blocks = []  # list of (speaker, [text_lines])
    for seg in whisper_segments:
        label = seg.get("speaker_label", "UNKNOWN")
        text = seg.get("text", "").strip()
        if not text:
            continue
        if speaker_blocks and speaker_blocks[-1][0] == label:
            speaker_blocks[-1][1].append(text)
        else:
            speaker_blocks.append((label, [text]))

    transcript_lines = []
    for speaker, texts in speaker_blocks:
        tag = "[%s]" % speaker
        for i, line in enumerate(texts):
            if i == 0:
                transcript_lines.append("%-16s%s" % (tag, line))
            else:
                transcript_lines.append("%-16s%s" % ("", line))
        transcript_lines.append("")  # blank line between blocks

    return "\n".join(transcript_lines).rstrip()


# ---------------------------------------------------------------------------
# 3. compute_talk_time
# ---------------------------------------------------------------------------

def compute_talk_time(diarization_segments):
    """Compute total talk time per speaker from diarization segments.

    Parameters
    ----------
    diarization_segments : list of dict
        Output of :func:`diarize_audio`.

    Returns
    -------
    dict
        Mapping ``speaker_label -> seconds`` (float), sorted by descending time.
    """
    times = {}  # type: Dict[str, float]
    for seg in diarization_segments:
        speaker = seg["speaker"]
        duration = seg["end"] - seg["start"]
        times[speaker] = times.get(speaker, 0.0) + duration

    # Sort descending by talk time
    sorted_times = dict(
        sorted(times.items(), key=lambda kv: kv[1], reverse=True)
    )
    return sorted_times


# ---------------------------------------------------------------------------
# 4. load_speaker_map
# ---------------------------------------------------------------------------

def load_speaker_map(speaker_map_path):
    """Load a speaker-map JSON sidecar file.

    Parameters
    ----------
    speaker_map_path : str or Path
        Path to the JSON file mapping ``SPEAKER_00`` -> real name.

    Returns
    -------
    dict
        The loaded map, or ``{}`` if the file does not exist or is invalid.
    """
    path = Path(speaker_map_path)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return data
        return {}
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load speaker map %s: %s", path, exc)
        return {}


# ---------------------------------------------------------------------------
# 5. apply_speaker_map
# ---------------------------------------------------------------------------

def apply_speaker_map(segments, speaker_map):
    """Replace generic speaker labels with real names from *speaker_map*.

    Parameters
    ----------
    segments : list of dict
        Whisper segments with ``speaker_label`` key.
    speaker_map : dict
        Mapping ``SPEAKER_00`` -> ``"Alice"`` etc.

    Returns
    -------
    list of dict
        The same segments with ``speaker_label`` updated in-place.
    """
    if not speaker_map:
        return segments

    for seg in segments:
        label = seg.get("speaker_label", "")
        if label in speaker_map:
            mapped = speaker_map[label]
            # Only replace if the mapped name is different from the key
            # (user has actually edited the file)
            if mapped and mapped != label:
                seg["speaker_label"] = mapped

    return segments


# ---------------------------------------------------------------------------
# 6. save_speaker_map
# ---------------------------------------------------------------------------

def save_speaker_map(speaker_map_path, speaker_labels):
    """Write an initial speaker-map JSON sidecar for the user to edit.

    Parameters
    ----------
    speaker_map_path : str or Path
        Destination path for the JSON file.
    speaker_labels : list of str
        Unique speaker labels detected (e.g. ``["SPEAKER_00", "SPEAKER_01"]``).
    """
    path = Path(speaker_map_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    mapping = {}
    for label in sorted(set(speaker_labels)):
        mapping[label] = label  # identity — user edits to set real names

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(mapping, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
