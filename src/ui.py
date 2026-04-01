"""
ui.py — Rich terminal output for ai-mom.

Provides styled console output using the ``rich`` library.
All functions degrade gracefully if rich is not installed.
"""
from __future__ import annotations

import contextlib
from typing import Any, Dict, Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.columns import Columns
    from rich.style import Style
    from rich.progress import SpinnerColumn, TextColumn, Progress
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

# ---------------------------------------------------------------------------
# Console singleton
# ---------------------------------------------------------------------------

if HAS_RICH:
    console = Console(highlight=False)
else:
    console = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _duration_label(seconds: float) -> str:
    """Convert seconds to a human-readable duration string."""
    minutes = round(seconds / 60)
    if minutes < 1:
        return "%d sec" % int(seconds)
    return "%d min" % minutes


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def print_header() -> None:
    """Print a dramatic startup header."""
    if not HAS_RICH:
        print("\n  AI MOM  —  Meeting Minutes, Automated.\n")
        return

    title_art = Text()
    title_art.append("  A I ", style="bold bright_white on blue")
    title_art.append(" ", style="default")
    title_art.append(" M O M ", style="bold bright_white on dark_red")

    tagline = Text("Meeting Minutes, Automated.", style="dim italic")

    inner = Text.assemble(
        "\n",
        title_art,
        "\n\n",
        "  ",
        tagline,
        "\n",
    )

    panel = Panel(
        inner,
        border_style="bright_blue",
        box=box.DOUBLE_EDGE,
        padding=(0, 2),
    )
    console.print()
    console.print(panel)
    console.print()


def print_step(n: int, total: int, description: str) -> None:
    """Print a numbered step indicator."""
    if not HAS_RICH:
        print("[%d/%d] %s" % (n, total, description))
        return

    step_text = Text()
    step_text.append(" [%d/%d] " % (n, total), style="bold cyan")
    step_text.append("\u25c6 ", style="cyan")
    step_text.append(description, style="bold white")
    console.print(step_text)


def print_success(msg: str) -> None:
    """Print a green success message."""
    if not HAS_RICH:
        print("  \u2714 %s" % msg)
        return

    text = Text()
    text.append("  \u2714 ", style="bold green")
    text.append(msg, style="green")
    console.print(text)


def print_warning(msg: str) -> None:
    """Print a yellow warning message."""
    if not HAS_RICH:
        print("  WARNING: %s" % msg)
        return

    text = Text()
    text.append("  \u26a0 WARNING: ", style="bold yellow")
    text.append(msg, style="yellow")
    console.print(text)


def print_error(msg: str) -> None:
    """Print a red error message."""
    if not HAS_RICH:
        print("  ERROR: %s" % msg)
        return

    text = Text()
    text.append("  \u2718 ERROR: ", style="bold red")
    text.append(msg, style="red")
    console.print(text)


def print_info(msg: str) -> None:
    """Print a dim/muted informational message."""
    if not HAS_RICH:
        print("    %s" % msg)
        return

    console.print("    %s" % msg, style="dim")


def print_banner(
    audio_name: str,
    duration_seconds: float,
    language: str,
    attendees: list,
    fmt: str,
    exported_path: str,
    speaker_times: Optional[Dict[str, float]] = None,
) -> None:
    """Print the final rich summary panel — the showpiece."""
    _LANGUAGE_LABELS = {"en": "English", "gu": "Gujarati", "hi": "Hindi", "lsd": "Lisan-ud-Dawat"}
    _FMT_LABELS = {"md": "Markdown", "pdf": "PDF", "both": "Markdown + PDF"}

    lang_label = _LANGUAGE_LABELS.get(language, language)
    fmt_label = _FMT_LABELS.get(fmt, fmt)
    duration_str = _duration_label(duration_seconds)
    speakers_line = ", ".join(attendees) if attendees else "(none listed)"

    import sys as _sys
    if not HAS_RICH or not _sys.stdout.isatty():
        width = 50
        sep = "=" * width
        print("")
        print(sep)
        print(" AI MOM  --  Meeting Minutes Generated")
        print(sep)
        print(" Audio:     %s (%s)" % (audio_name, duration_str))
        print(" Language:  %s" % lang_label)
        print(" Speakers:  %s" % speakers_line)
        print(" Format:    %s" % fmt_label)
        print(" Exported:  %s" % exported_path)
        if speaker_times:
            print("")
            print(" Speaker Talk Times:")
            total = sum(speaker_times.values()) or 1
            for name, secs in speaker_times.items():
                pct = secs / total * 100
                print("   %-20s %5.1fs  (%4.1f%%)" % (name, secs, pct))
        print(sep)
        return

    # -- Rich version -------------------------------------------------------

    # Details table
    details = Table(
        show_header=False,
        show_edge=False,
        box=None,
        padding=(0, 2),
        expand=True,
    )
    details.add_column("key", style="bold bright_cyan", no_wrap=True)
    details.add_column("value", style="white")

    details.add_row("Audio", "%s  (%s)" % (audio_name, duration_str))
    details.add_row("Language", lang_label)
    details.add_row("Speakers", speakers_line)
    details.add_row("Format", fmt_label)
    details.add_row("Exported", str(exported_path))

    # Speaker talk-time table (if available)
    speaker_table = None
    if speaker_times:
        total_talk = sum(speaker_times.values()) or 1.0
        speaker_table = Table(
            title="Speaker Talk Times",
            title_style="bold bright_cyan",
            box=box.SIMPLE_HEAVY,
            show_edge=False,
            padding=(0, 1),
            expand=True,
        )
        speaker_table.add_column("Speaker", style="white", no_wrap=True)
        speaker_table.add_column("Time", style="dim", justify="right")
        speaker_table.add_column("Share", justify="right")
        speaker_table.add_column("", min_width=20)

        for name, secs in speaker_times.items():
            pct = secs / total_talk * 100
            bar_len = int(pct / 100 * 20)
            bar = "\u2588" * bar_len + "\u2591" * (20 - bar_len)
            speaker_table.add_row(
                name,
                "%.1fs" % secs,
                "[bold cyan]%.1f%%[/]" % pct,
                "[cyan]%s[/]" % bar,
            )

    # Compose the panel content
    from rich.console import Group

    parts = [details]
    if speaker_table:
        parts.append(Text(""))
        parts.append(speaker_table)

    panel_title = Text()
    panel_title.append(" AI MOM ", style="bold bright_white on blue")
    panel_title.append(" Meeting Minutes Generated ", style="bold bright_white")

    panel = Panel(
        Group(*parts),
        title=panel_title,
        border_style="bright_green",
        box=box.DOUBLE_EDGE,
        padding=(1, 2),
    )

    console.print()
    console.print(panel)
    console.print()


@contextlib.contextmanager
def live_spinner(description: str):
    """Context manager that shows a spinner while work is happening.

    Yields a status object (rich) or None (fallback).
    """
    if not HAS_RICH:
        print("  %s ..." % description)
        yield None
        return

    with console.status(
        "[bold cyan]%s[/bold cyan]" % description,
        spinner="dots",
        spinner_style="cyan",
    ) as status:
        yield status
