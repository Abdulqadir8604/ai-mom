"""
summarizer.py — Phase 6: Ollama UK-style meeting minutes generation.

Public API
----------
generate_minutes(transcript, meeting_info, openai_client) -> dict
    Main entry point.  Returns a MeetingMinutes-compatible dict.

generate_summary(transcript, openai_client) -> dict   [DEPRECATED]
    Backward-compatible alias for generate_minutes().  Accepts the old
    two-argument signature and delegates to generate_minutes().  The
    return shape is the new MeetingMinutes shape, not the old stub shape.
"""
from __future__ import annotations

import functools
import json
import logging
import os
import re
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
_PROMPT_PATH: Path = _PROJECT_ROOT / "config" / "uk_minutes_prompt.txt"

# Keys the caller expects in a valid MeetingMinutes dict, mapped to safe defaults.
_REQUIRED_KEYS: Dict[str, Any] = {
    "title": "",
    "session_summary": "",
    "key_decisions": [],
    "action_items": [],
    "deadlines": [],
    "next_steps": [],
    "qa_pairs": [],
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=1)
def _load_prompt_template() -> str:
    """Load and cache the UK minutes prompt template from config/.

    Returns
    -------
    str
        The raw prompt text with a ``{transcript}`` placeholder.

    Raises
    ------
    FileNotFoundError
        If the prompt file is missing from the expected location.
    """
    if not _PROMPT_PATH.exists():
        raise FileNotFoundError(
            f"UK minutes prompt not found at: {_PROMPT_PATH}"
        )
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _safe_fallback(
    transcript: str,
    meeting_info: Dict[str, Any],
    raw_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a minimal valid MeetingMinutes-compatible dict.

    Used when the OpenAI client is unavailable or when the API response
    cannot be parsed as valid JSON.

    Parameters
    ----------
    transcript:
        The original transcript text (stored for reference).
    meeting_info:
        Caller-supplied meeting metadata dict.
    raw_text:
        If provided (e.g. a malformed GPT response), stored verbatim in
        ``session_summary`` so no information is lost.
    """
    summary = raw_text if raw_text is not None else transcript[:500] if transcript else ""
    return {
        "title": meeting_info.get("title", ""),
        "session_summary": summary,
        "key_decisions": [],
        "action_items": [],
        "deadlines": [],
        "next_steps": [],
        "qa_pairs": [],
    }


def _extract_json(text: str) -> str:
    """Strip markdown code fences and extract the JSON object from *text*.

    Handles all common Ollama response shapes:
    - Fenced: ```json { ... } ```
    - Bare object: { ... }
    - Fields without braces: "title": "...", ...  → wrapped in { }
    """
    text = text.strip()

    # 1. Strip ```json ... ``` or ``` ... ``` fences
    fenced = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if fenced:
        text = fenced.group(1).strip()

    # 2. If it already parses, return as-is
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    # 3. Find outermost { ... }
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        candidate = text[brace_start : brace_end + 1]
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    # 4. Model returned bare fields without braces — wrap them
    if text.lstrip().startswith('"'):
        wrapped = "{" + text.rstrip().rstrip(",") + "}"
        try:
            json.loads(wrapped)
            return wrapped
        except json.JSONDecodeError:
            pass

    return text


def _call_gemini(user_message: str, system_message: str) -> Optional[str]:
    """Try Gemini 2.5 Flash via the OpenAI-compatible endpoint.

    Returns the raw response string, or None if the call fails or
    GEMINI_API_KEY is not set.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from openai import OpenAI as _OpenAI
        client = _OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        response = client.chat.completions.create(
            model="gemini-2.5-flash",
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        logger.warning("summarizer: Gemini fallback failed (%s).", exc)
        return None


def _validate_and_fill(data: Dict[str, Any], meeting_info: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure all required keys are present and carry sensible types.

    Missing keys are filled with empty-list / empty-string defaults.
    The ``title`` is always taken from *meeting_info* to guarantee
    consistency with the caller's metadata.
    """
    result: Dict[str, Any] = {}
    for key, default in _REQUIRED_KEYS.items():
        value = data.get(key, default)
        # Type-safety: coerce to the expected container type.
        if isinstance(default, list) and not isinstance(value, list):
            logger.warning("summarizer: GPT returned non-list for '%s'; using [].", key)
            value = []
        elif isinstance(default, str) and not isinstance(value, str):
            value = str(value)
        result[key] = value

    # Authoritative title always comes from meeting_info, not GPT.
    result["title"] = meeting_info.get("title", result.get("title", ""))
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_minutes(
    transcript: str,
    meeting_info: Dict[str, Any],
    openai_client: Any,
) -> Dict[str, Any]:
    """Generate UK-style structured meeting minutes via GPT-4o-mini.

    Parameters
    ----------
    transcript:
        Full (corrected) transcript text of the meeting.
    meeting_info:
        Dict with meeting metadata.  Recognised keys:
        ``title`` (str), ``date`` (str), ``attendees`` (list[str]),
        ``duration_seconds`` (float).
    openai_client:
        An initialised ``openai.OpenAI`` client.  Pass ``None`` to receive
        an immediate safe fallback without raising an exception.

    Returns
    -------
    dict
        MeetingMinutes-compatible dict with keys:
        title, session_summary, key_decisions, action_items,
        deadlines, next_steps, qa_pairs.
    """
    if openai_client is None:
        logger.warning(
            "summarizer: openai_client is None — returning safe fallback."
        )
        return _safe_fallback(transcript, meeting_info)

    # Build meeting context for the system message.
    title = meeting_info.get("title", "Untitled Meeting")
    date = meeting_info.get("date", "Date not specified")
    attendees: List[str] = meeting_info.get("attendees", [])
    attendees_str = ", ".join(attendees) if attendees else "Not recorded"

    system_message = (
        "You are a professional meeting secretary producing formal UK-style "
        "meeting minutes in JSON format.\n\n"
        f"Meeting title: {title}\n"
        f"Date: {date}\n"
        f"Attendees: {attendees_str}"
    )

    try:
        prompt_template = _load_prompt_template()
    except FileNotFoundError as exc:
        logger.warning("summarizer: %s — returning safe fallback.", exc)
        return _safe_fallback(transcript, meeting_info)

    # Prefer speaker-attributed transcript when available — gives the model
    # better context about who said what.
    effective_transcript = meeting_info.get("speaker_transcript") or transcript
    user_message = prompt_template.replace("{transcript}", effective_transcript)

    # If GEMINI_API_KEY is set, use Gemini directly — skip Ollama entirely.
    if os.environ.get("GEMINI_API_KEY", "").strip():
        from src.ui import print_info
        print_info("Using Gemini for summarization...")
        gemini_raw = _call_gemini(user_message, system_message)
        if gemini_raw:
            try:
                data = json.loads(_extract_json(gemini_raw))
                if isinstance(data, dict):
                    return _validate_and_fill(data, meeting_info)
            except json.JSONDecodeError:
                logger.warning("summarizer: Gemini returned malformed JSON.")
        return _safe_fallback(transcript, meeting_info)

    # Ollama path (fallback when no Gemini key)
    model_name: str = getattr(openai_client, "_ollama_model", "gemma3:4b")

    try:
        response = openai_client.chat.completions.create(
            model=model_name,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
        )
        raw_content: str = response.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "summarizer: Ollama call failed (%s) — returning safe fallback.",
            exc,
        )
        return _safe_fallback(transcript, meeting_info)

    try:
        data = json.loads(_extract_json(raw_content))
    except json.JSONDecodeError as exc:
        logger.warning("summarizer: Ollama returned malformed JSON (%s).", exc)
        from src.ui import print_warning
        print_warning("Ollama returned malformed JSON. Using raw summary.")
        return _safe_fallback(transcript, meeting_info, raw_text=raw_content)

    if not isinstance(data, dict):
        logger.warning(
            "summarizer: GPT response was valid JSON but not an object (got %s) "
            "— returning safe fallback.",
            type(data).__name__,
        )
        return _safe_fallback(transcript, meeting_info, raw_text=raw_content)

    return _validate_and_fill(data, meeting_info)


# ---------------------------------------------------------------------------
# Deprecated alias
# ---------------------------------------------------------------------------


def generate_summary(transcript: str, openai_client: Any) -> Dict[str, Any]:
    """Generate meeting minutes (DEPRECATED — use generate_minutes instead).

    This function preserves backward compatibility with the Phase 6 stub
    signature ``(transcript, openai_client)``.  It delegates to
    :func:`generate_minutes` with an empty *meeting_info* dict.

    .. deprecated::
        Use ``generate_minutes(transcript, meeting_info, openai_client)``
        instead.  The return shape is the full MeetingMinutes dict, not
        the old stub keys (key_points, decisions, action_items, qa_pairs).
    """
    warnings.warn(
        "generate_summary() is deprecated and will be removed in a future release. "
        "Use generate_minutes(transcript, meeting_info, openai_client) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return generate_minutes(transcript, {}, openai_client)
