"""
exporter.py — Markdown and optional PDF export for AI MOM meeting minutes.

Public interface:
    to_markdown(minutes: dict) -> str
    export_minutes(minutes: dict, output_path: Path, format: str = "md") -> Path
"""

from __future__ import annotations

import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Date / duration helpers
# ---------------------------------------------------------------------------

_MONTHS = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _format_date(date_str: Optional[str]) -> str:
    """Convert an ISO datetime string or plain date string to UK format.

    Examples::

        "2026-03-28T14:00:00+00:00" -> "28 March 2026"
        "2026-03-28T14:00:00Z"      -> "28 March 2026"
        "2026-03-28"                -> "28 March 2026"
        "2 April 2026"              -> "2 April 2026"  (returned unchanged)
    """
    if not date_str:
        return "Not recorded"

    date_str = str(date_str).strip()

    # Normalise the Z suffix — Python 3.9 fromisoformat does not accept it
    normalised = date_str.replace("Z", "+00:00")

    try:
        dt = datetime.fromisoformat(normalised)
        return f"{dt.day} {_MONTHS[dt.month]} {dt.year}"
    except (ValueError, TypeError):
        # Already a plain human-readable string like "2 April 2026" — keep it
        return date_str


def _format_duration(seconds: Optional[float]) -> str:
    """Convert a duration in seconds to a human-readable UK string.

    Examples::

        2820.0 -> "47 minutes"
        4980.0 -> "1 hour 23 minutes"
        3600.0 -> "1 hour"
        60.0   -> "1 minute"
        None   -> "Not recorded"
    """
    if not seconds:
        return "Not recorded"

    total_minutes = int(round(float(seconds) / 60))

    if total_minutes == 0:
        return "%d seconds" % int(seconds)

    hours, mins = divmod(total_minutes, 60)

    parts: list[str] = []
    if hours:
        parts.append(f"{hours} {'hour' if hours == 1 else 'hours'}")
    if mins:
        parts.append(f"{mins} {'minute' if mins == 1 else 'minutes'}")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

def to_markdown(minutes: dict) -> str:
    """Return the full UK-style meeting minutes as a Markdown string.

    All sections degrade gracefully: missing or empty lists produce a
    ``*No X recorded.*`` placeholder rather than crashing or rendering
    broken Markdown.
    """
    title = minutes.get("title") or "Meeting"
    date_str = _format_date(minutes.get("date"))
    duration_str = _format_duration(minutes.get("duration_seconds"))

    attendees_list = minutes.get("attendees") or []
    attendees_str = ", ".join(attendees_list) if attendees_list else "Not recorded"

    lines: list[str] = []

    # ── Header block ──────────────────────────────────────────────────────
    lines += [
        "# MEETING MINUTES",
        "",
        f"**Project:** {title}  ",
        f"**Date:** {date_str}  ",
        f"**Duration:** {duration_str}  ",
        f"**Attendees:** {attendees_str}  ",
        "**Prepared by:** AI MOM",
        "",
        "---",
        "",
    ]

    section_number = 1

    # ── Talk Time (optional — only when diarization was run) ─────────────
    speaker_times = minutes.get("speaker_times")
    if speaker_times:
        total_time = sum(speaker_times.values()) or 1.0

        lines.append("## Talk Time")
        lines.append("")
        lines.append("| Speaker | Time | Share |")
        lines.append("|---------|------|-------|")

        for speaker, seconds in speaker_times.items():
            pct = seconds / total_time * 100
            mins = int(seconds) // 60
            secs = int(seconds) % 60
            if mins > 0 and secs > 0:
                time_str = "%d min %d sec" % (mins, secs)
            elif mins > 0:
                time_str = "%d min" % mins
            else:
                time_str = "%d sec" % secs
            lines.append("| %s | %s | %.1f%% |" % (speaker, time_str, pct))

        lines.append("")

    # ── Attendance (optional — only when attendance data is present) ────
    attendance = minutes.get("attendance")
    if attendance:
        present = attendance.get("present", [])
        absent = attendance.get("absent", [])
        unknown = attendance.get("unknown", [])
        if present or absent or unknown:
            lines.append("## Attendance")
            lines.append("")
            if present:
                lines.append("**Present:** %s" % ", ".join(present))
            if absent:
                lines.append("**Absent:** %s" % ", ".join(absent))
            if unknown:
                lines.append("**Unknown:** %s" % ", ".join(unknown))
            lines.append("")

    # ── 1. Session Summary ───────────────────────────────────────────────
    summary = minutes.get("session_summary") or ""
    lines.append(f"## {section_number}. Session Summary")
    lines.append("")
    lines.append(summary if summary else "*No summary recorded.*")
    lines.append("")
    section_number += 1

    # ── 2. Key Decisions ─────────────────────────────────────────────────
    decisions = minutes.get("key_decisions") or []
    lines.append(f"## {section_number}. Key Decisions")
    lines.append("")
    if decisions:
        for i, decision in enumerate(decisions, start=1):
            lines.append(f"{i}. {decision}")
    else:
        lines.append("*No decisions recorded.*")
    lines.append("")
    section_number += 1

    # ── 3. Action Items ──────────────────────────────────────────────────
    action_items = minutes.get("action_items") or []
    lines.append(f"## {section_number}. Action Items")
    lines.append("")
    if action_items:
        lines.append("| Owner | Action | Due |")
        lines.append("|-------|--------|-----|")
        for item in action_items:
            owner = (item.get("owner") or "TBC").replace("|", r"\|")
            description = (item.get("description") or "").replace("|", r"\|")
            due = (item.get("due") or "TBC").replace("|", r"\|")
            lines.append(f"| {owner} | {description} | {due} |")
    else:
        lines.append("*No action items recorded.*")
    lines.append("")
    section_number += 1

    # ── 4. Deadlines ─────────────────────────────────────────────────────
    deadlines = minutes.get("deadlines") or []
    lines.append(f"## {section_number}. Deadlines")
    lines.append("")
    if deadlines:
        for deadline in deadlines:
            desc = deadline.get("description") or ""
            date = deadline.get("date") or "TBC"
            lines.append(f"- {desc} — {date}")
    else:
        lines.append("*No deadlines recorded.*")
    lines.append("")
    section_number += 1

    # ── 5. Next Steps ────────────────────────────────────────────────────
    next_steps = minutes.get("next_steps") or []
    lines.append(f"## {section_number}. Next Steps")
    lines.append("")
    if next_steps:
        for i, step in enumerate(next_steps, start=1):
            lines.append(f"{i}. {step}")
    else:
        lines.append("*No next steps recorded.*")
    lines.append("")
    section_number += 1

    # ── 6. Questions and Answers ─────────────────────────────────────────
    qa_pairs = minutes.get("qa_pairs") or []
    lines.append(f"## {section_number}. Questions and Answers")
    lines.append("")
    if qa_pairs:
        for pair in qa_pairs:
            questioner = pair.get("questioner") or ""
            question = pair.get("question") or ""
            answer = pair.get("answer") or ""
            q_label = f"Q ({questioner})" if questioner else "Q"
            lines.append(f"**{q_label}:** {question}  ")
            lines.append(f"**A:** {answer}")
            lines.append("")
    else:
        lines.append("*No questions and answers recorded.*")
        lines.append("")

    # ── Transcript ────────────────────────────────────────────────────────
    speaker_transcript = minutes.get("speaker_transcript")
    plain_transcript = minutes.get("transcript")

    if speaker_transcript:
        lines.append("## Transcript")
        lines.append("")
        lines.append("```")
        lines.append(speaker_transcript)
        lines.append("```")
        lines.append("")
    elif plain_transcript:
        lines.append("## Transcript")
        lines.append("")
        lines.append(plain_transcript)
        lines.append("")

    # ── Footer ────────────────────────────────────────────────────────────
    lines += [
        "---",
        "*Minutes prepared by AI MOM*",
        "",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# PDF generation (reportlab — optional dependency)
# ---------------------------------------------------------------------------

def _to_pdf(minutes: dict, output_path: Path) -> Optional[Path]:
    """Generate a PDF from *minutes* using reportlab.

    Returns the output path on success, or ``None`` if reportlab is not
    installed (the caller is responsible for issuing the warning).
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib.enums import TA_LEFT, TA_CENTER  # noqa: F401
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            HRFlowable,
            Table,
            TableStyle,
        )
    except ImportError:
        return None

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
    )

    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        "MinutesTitle",
        parent=styles["Title"],
        fontSize=18,
        spaceAfter=6,
        alignment=TA_CENTER,
    )
    style_meta = ParagraphStyle(
        "MinutesMeta",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=3,
    )
    style_h2 = ParagraphStyle(
        "MinutesH2",
        parent=styles["Heading2"],
        fontSize=12,
        spaceBefore=14,
        spaceAfter=4,
    )
    style_body = ParagraphStyle(
        "MinutesBody",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=4,
    )
    style_list = ParagraphStyle(
        "MinutesList",
        parent=styles["Normal"],
        fontSize=10,
        leftIndent=12,
        spaceAfter=3,
    )
    style_footer = ParagraphStyle(
        "MinutesFooter",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )

    story = []

    title = minutes.get("title") or "Meeting"
    story.append(Paragraph("MEETING MINUTES", style_title))
    story.append(Spacer(1, 0.2 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    story.append(Spacer(1, 0.3 * cm))

    date_str = _format_date(minutes.get("date"))
    duration_str = _format_duration(minutes.get("duration_seconds"))
    attendees_list = minutes.get("attendees") or []
    attendees_str = ", ".join(attendees_list) if attendees_list else "Not recorded"

    story.append(Paragraph(f"<b>Project:</b> {title}", style_meta))
    story.append(Paragraph(f"<b>Date:</b> {date_str}", style_meta))
    story.append(Paragraph(f"<b>Duration:</b> {duration_str}", style_meta))
    story.append(Paragraph(f"<b>Attendees:</b> {attendees_str}", style_meta))
    story.append(Paragraph("<b>Prepared by:</b> AI MOM", style_meta))
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))

    section_number = 1

    # Session Summary
    summary = minutes.get("session_summary") or ""
    story.append(Paragraph(f"{section_number}. Session Summary", style_h2))
    story.append(Paragraph(summary if summary else "No summary recorded.", style_body))
    section_number += 1

    # Key Decisions
    decisions = minutes.get("key_decisions") or []
    story.append(Paragraph(f"{section_number}. Key Decisions", style_h2))
    if decisions:
        for i, decision in enumerate(decisions, start=1):
            story.append(Paragraph(f"{i}. {decision}", style_list))
    else:
        story.append(Paragraph("No decisions recorded.", style_body))
    section_number += 1

    # Action Items
    action_items = minutes.get("action_items") or []
    story.append(Paragraph(f"{section_number}. Action Items", style_h2))
    if action_items:
        table_data = [["Owner", "Action", "Due"]]
        for item in action_items:
            table_data.append([
                item.get("owner") or "TBC",
                item.get("description") or "",
                item.get("due") or "TBC",
            ])
        tbl = Table(table_data, colWidths=[4 * cm, 9 * cm, 3.5 * cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#404040")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tbl)
    else:
        story.append(Paragraph("No action items recorded.", style_body))
    section_number += 1

    # Deadlines
    deadlines = minutes.get("deadlines") or []
    story.append(Paragraph(f"{section_number}. Deadlines", style_h2))
    if deadlines:
        for deadline in deadlines:
            desc = deadline.get("description") or ""
            date = deadline.get("date") or "TBC"
            story.append(Paragraph(f"- {desc} — {date}", style_list))
    else:
        story.append(Paragraph("No deadlines recorded.", style_body))
    section_number += 1

    # Next Steps
    next_steps = minutes.get("next_steps") or []
    story.append(Paragraph(f"{section_number}. Next Steps", style_h2))
    if next_steps:
        for i, step in enumerate(next_steps, start=1):
            story.append(Paragraph(f"{i}. {step}", style_list))
    else:
        story.append(Paragraph("No next steps recorded.", style_body))
    section_number += 1

    # Questions & Answers
    qa_pairs = minutes.get("qa_pairs") or []
    story.append(Paragraph(f"{section_number}. Questions and Answers", style_h2))
    if qa_pairs:
        for pair in qa_pairs:
            questioner = pair.get("questioner") or ""
            question = pair.get("question") or ""
            answer = pair.get("answer") or ""
            q_label = f"Q ({questioner})" if questioner else "Q"
            story.append(Paragraph(f"<b>{q_label}:</b> {question}", style_body))
            story.append(Paragraph(f"<b>A:</b> {answer}", style_body))
            story.append(Spacer(1, 0.2 * cm))
    else:
        story.append(Paragraph("No questions and answers recorded.", style_body))

    # Footer
    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Minutes prepared by AI MOM", style_footer))

    doc.build(story)
    return output_path


# ---------------------------------------------------------------------------
# Filename helper
# ---------------------------------------------------------------------------

def _make_stem(minutes: dict) -> str:
    """Derive a safe filename stem from the meeting title and date."""
    title = minutes.get("title") or "meeting"
    date = minutes.get("date") or ""
    # Use first 10 chars of date (the YYYY-MM-DD portion, works for ISO strings)
    date_part = str(date)[:10].replace(":", "-")
    safe_title = "".join(
        c if c.isalnum() or c in " -_" else "_" for c in title
    ).strip().replace(" ", "_")
    if date_part:
        return f"{date_part}_{safe_title}"
    return safe_title or "meeting"


# ---------------------------------------------------------------------------
# Main export function
# ---------------------------------------------------------------------------

def export_minutes(
    minutes: dict,
    output_path: Path,
    format: str = "md",
) -> Path:
    """Export meeting minutes to Markdown and/or PDF.

    Parameters
    ----------
    minutes:
        The MeetingMinutes dict.
    output_path:
        A full file path (with or without a recognised suffix) or a directory.
        When a directory is supplied, the filename is derived from the meeting
        title and date.
    format:
        ``"md"`` | ``"pdf"`` | ``"both"``

    Returns
    -------
    Path
        Path to the exported file.  When *format* is ``"both"``, returns the
        directory that contains both files.
    """
    output_path = Path(output_path)
    format = format.lower().strip()

    # ── Resolve base path (stem without extension) ────────────────────────
    if output_path.suffix.lower() in (".md", ".pdf"):
        base_path = output_path.with_suffix("")
    elif output_path.is_dir():
        base_path = output_path / _make_stem(minutes)
    elif output_path.suffix == "":
        # Treat as a stem (parent may not exist yet — that is fine)
        base_path = output_path
    else:
        base_path = output_path.with_suffix("")

    base_path.parent.mkdir(parents=True, exist_ok=True)

    md_path = base_path.with_suffix(".md")
    pdf_path = base_path.with_suffix(".pdf")

    # Markdown is always written — stdlib only, never fails
    md_content = to_markdown(minutes)
    md_path.write_text(md_content, encoding="utf-8")

    if format == "md":
        return md_path

    if format in ("pdf", "both"):
        pdf_result = _to_pdf(minutes, pdf_path)

        if pdf_result is None:
            warnings.warn(
                "reportlab is not installed — PDF export is unavailable. "
                "The Markdown file has been written instead.",
                RuntimeWarning,
                stacklevel=2,
            )
            # Regardless of "pdf" or "both", return something useful
            return md_path if format == "pdf" else base_path.parent

        # PDF succeeded
        if format == "both":
            return base_path.parent

        return pdf_path  # format == "pdf"

    # Unknown format — warn and default to md
    warnings.warn(
        f"Unknown format {format!r}. Defaulting to Markdown.",
        RuntimeWarning,
        stacklevel=2,
    )
    return md_path
