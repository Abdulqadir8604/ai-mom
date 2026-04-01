# NOTE: These dataclasses are not yet used by the runtime pipeline.
# They represent a planned data model for a future SQLite persistence layer.

"""Data model foundations for the AI Meeting of Minutes (MOM) system.

Classes:
    MeetingSession  -- Represents one meeting recording session with metadata,
                       language config, and audio path.
    TranscriptSegment -- One Whisper-produced segment with optional speaker label
                         and text correction.
    SpeakerProfile  -- An enrolled speaker's voice profile for diarization.
    MeetingMinutes  -- Final structured output (summary, decisions, actions)
                       ready for export to JSON / PDF.

Constants:
    SQLITE_SCHEMA   -- CREATE TABLE statements for all four entities.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional


def _new_id() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------------
# MeetingSession
# ---------------------------------------------------------------------------

@dataclass
class MeetingSession:
    """Represents one meeting recording session."""

    meeting_id: str = field(default_factory=_new_id)
    title: str = ""
    attendees: List[str] = field(default_factory=list)
    date: str = field(default_factory=_now_iso)
    language: str = "en"
    whisper_language_hint: str = "en"
    correction_pipeline: str = "none"
    duration_seconds: float = 0.0
    audio_path: str = ""

    @classmethod
    def for_english(
        cls,
        audio_path: str,
        title: str = "",
        attendees: Optional[List[str]] = None,
    ) -> MeetingSession:
        """Create a session pre-configured for English meetings."""
        return cls(
            audio_path=audio_path,
            title=title,
            attendees=attendees or [],
            language="en",
            whisper_language_hint="en",
            correction_pipeline="none",
        )

    @classmethod
    def for_lsd(
        cls,
        audio_path: str,
        title: str = "",
        attendees: Optional[List[str]] = None,
    ) -> MeetingSession:
        """Create a session pre-configured for Lisan-ud-Dawat meetings."""
        return cls(
            audio_path=audio_path,
            title=title,
            attendees=attendees or [],
            language="lsd",
            whisper_language_hint="ar",
            correction_pipeline="lsd_nasal",
        )


# ---------------------------------------------------------------------------
# TranscriptSegment
# ---------------------------------------------------------------------------

@dataclass
class TranscriptSegment:
    """One Whisper segment with speaker label and optional correction."""

    segment_id: str = field(default_factory=_new_id)
    meeting_id: str = ""
    speaker_label: str = "UNKNOWN"
    start: float = 0.0
    end: float = 0.0
    text_raw: str = ""
    text_corrected: Optional[str] = None
    language: str = "en"
    confidence: float = 0.0


# ---------------------------------------------------------------------------
# SpeakerProfile
# ---------------------------------------------------------------------------

@dataclass
class SpeakerProfile:
    """Enrolled speaker voice profile for diarization."""

    speaker_id: str = field(default_factory=_new_id)
    name: str = ""
    embedding: Optional[bytes] = None
    embedding_model: str = "ecapa_tdnn"
    enrolled_at: Optional[str] = None
    sample_audio_path: str = ""


# ---------------------------------------------------------------------------
# MeetingMinutes
# ---------------------------------------------------------------------------

@dataclass
class MeetingMinutes:
    """Final structured output for export (JSON / PDF)."""

    meeting_id: str = ""
    title: str = ""
    date: str = ""
    duration_seconds: float = 0.0
    attendees: List[str] = field(default_factory=list)
    session_summary: str = ""
    key_decisions: List[str] = field(default_factory=list)
    action_items: List[Dict[str, str]] = field(default_factory=list)
    deadlines: List[Dict[str, str]] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    qa_pairs: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Return a plain dict suitable for JSON serialization."""
        return asdict(self)


# ---------------------------------------------------------------------------
# SQLite Schema
# ---------------------------------------------------------------------------

SQLITE_SCHEMA = """\
CREATE TABLE IF NOT EXISTS meeting_session (
    meeting_id          TEXT PRIMARY KEY,
    title               TEXT NOT NULL DEFAULT '',
    attendees           TEXT NOT NULL DEFAULT '[]',   -- JSON array of strings
    date                TEXT NOT NULL,
    language            TEXT NOT NULL DEFAULT 'en',
    whisper_language_hint TEXT NOT NULL DEFAULT 'en',
    correction_pipeline TEXT NOT NULL DEFAULT 'none',
    duration_seconds    REAL NOT NULL DEFAULT 0.0,
    audio_path          TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS transcript_segment (
    segment_id          TEXT PRIMARY KEY,
    meeting_id          TEXT NOT NULL REFERENCES meeting_session(meeting_id),
    speaker_label       TEXT NOT NULL DEFAULT 'UNKNOWN',
    start               REAL NOT NULL DEFAULT 0.0,
    end                 REAL NOT NULL DEFAULT 0.0,
    text_raw            TEXT NOT NULL DEFAULT '',
    text_corrected      TEXT,
    language            TEXT NOT NULL DEFAULT 'en',
    confidence          REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS speaker_profile (
    speaker_id          TEXT PRIMARY KEY,
    name                TEXT NOT NULL DEFAULT '',
    embedding           BLOB,
    embedding_model     TEXT NOT NULL DEFAULT 'ecapa_tdnn',
    enrolled_at         TEXT,
    sample_audio_path   TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS meeting_minutes (
    meeting_id          TEXT PRIMARY KEY REFERENCES meeting_session(meeting_id),
    title               TEXT NOT NULL DEFAULT '',
    date                TEXT NOT NULL DEFAULT '',
    duration_seconds    REAL NOT NULL DEFAULT 0.0,
    attendees           TEXT NOT NULL DEFAULT '[]',       -- JSON array
    session_summary     TEXT NOT NULL DEFAULT '',
    key_decisions       TEXT NOT NULL DEFAULT '[]',       -- JSON array
    action_items        TEXT NOT NULL DEFAULT '[]',       -- JSON array of objects
    deadlines           TEXT NOT NULL DEFAULT '[]',       -- JSON array of objects
    next_steps          TEXT NOT NULL DEFAULT '[]',       -- JSON array
    qa_pairs            TEXT NOT NULL DEFAULT '[]'        -- JSON array of objects
);
"""
