"""
attendance.py — Attendance tracking from voice-identified speakers.

Compares detected speaker labels (after Phase 2 auto-match) against
enrolled voice profiles to determine who was present, absent, or unknown.
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = PROJECT_ROOT / "profiles"

_SPEAKER_PATTERN = re.compile(r"^SPEAKER_\d+$")


def get_enrolled_names(profiles_dir=None):
    """Return sorted list of all enrolled names (stems of .npy files in profiles/).

    profiles_dir defaults to PROJECT_ROOT/profiles/.
    """
    pdir = Path(profiles_dir) if profiles_dir else PROFILES_DIR
    if not pdir.is_dir():
        return []
    return sorted(p.stem for p in pdir.glob("*.npy"))


def build_attendance(final_speaker_labels, expected_names=None):
    """Compare detected speakers against enrolled/expected names.

    Parameters
    ----------
    final_speaker_labels : list of str
        Unique labels from segments after Phase 2 (real names like "Ali"
        or "SPEAKER_00" if unmatched).
    expected_names : list of str or None
        If None, use all enrolled profiles.

    Returns
    -------
    dict with keys:
        "present"  -- detected AND known (in enrolled/expected)
        "absent"   -- expected/enrolled but NOT detected
        "unknown"  -- detected labels that look like SPEAKER_XX (not matched)
    """
    if expected_names is None:
        expected_names = get_enrolled_names()

    expected_set = set(expected_names)
    detected_set = set(final_speaker_labels)

    known = set()
    unknown = set()
    for label in detected_set:
        if _SPEAKER_PATTERN.match(label):
            unknown.add(label)
        elif label:
            known.add(label)

    present = sorted(known & expected_set) if expected_set else sorted(known)
    absent = sorted(expected_set - known) if expected_set else []
    unknown_sorted = sorted(unknown)

    return {
        "present": present,
        "absent": absent,
        "unknown": unknown_sorted,
    }


def format_attendance_report(attendance):
    """Return a multi-line formatted string for the attendance report."""
    lines = []
    lines.append("--- Attendance Report ---")

    present = attendance.get("present", [])
    absent = attendance.get("absent", [])
    unknown = attendance.get("unknown", [])

    lines.append("Present:  %s" % (", ".join(present) if present else "(none)"))
    lines.append("Absent:   %s" % (", ".join(absent) if absent else "(none)"))
    if unknown:
        lines.append("Unknown:  %s" % ", ".join(unknown))

    return "\n".join(lines)
