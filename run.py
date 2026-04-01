import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"  # fix macOS OpenMP conflict (torch + CTranslate2)

"""
run.py — CLI entry point for the ai-mom pipeline.

Usage:
    python run.py --audio path/to/recording.wav
    python run.py --record
    python run.py --audio path/to/recording.wav --model small --output-dir /tmp/out
    python run.py --audio path/to/recording.wav --all-phases
    python run.py --audio path/to/recording.wav --title "Board Meeting" \
                  --attendees "Sarah Chen, James Obi" --format md --language en
    python run.py --audio path/to/recording.wav --skip-summary
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Ensure the project root is on sys.path when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.pipeline import process_audio
from src.summarizer import generate_minutes
from src.exporter import export_minutes, to_markdown
from src.ui import (
    print_header,
    print_step,
    print_success,
    print_warning,
    print_error,
    print_info,
    print_banner as ui_print_banner,
    live_spinner,
)

# ---------------------------------------------------------------------------
# Language display map
# ---------------------------------------------------------------------------

_LANGUAGE_LABELS = {
    "en": "English",
    "gu": "Gujarati",
    "hi": "Hindi",
    "lsd": "Lisan-ud-Dawat",
}


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="ai-mom: Transcribe and generate meeting minutes from audio.",
    )
    parser.add_argument(
        "--audio",
        required=False,
        default=None,
        help="Path to the audio file (wav, mp3, m4a, etc.)",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="Record from microphone first, then process the recording.",
    )
    parser.add_argument(
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: base)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        dest="output_dir",
        help="Override output directory (default: <project>/output/)",
    )
    parser.add_argument(
        "--all-phases",
        action="store_true",
        dest="all_phases",
        help="Run legacy stub phases (roman conversion, TTS synthesis). Core diarization uses --diarize instead.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Meeting title (default: audio filename stem)",
    )
    parser.add_argument(
        "--attendees",
        default="",
        help="Comma-separated list of attendee names (default: empty)",
    )
    parser.add_argument(
        "--format",
        default="md",
        choices=["md", "pdf", "both"],
        dest="fmt",
        help="Export format: md, pdf, or both (default: md)",
    )
    parser.add_argument(
        "--language",
        default="en",
        choices=["en", "gu", "hi", "lsd", "auto"],
        help="Meeting language: en=English, gu=Gujarati, hi=Hindi, lsd=Lisan-ud-Dawat, auto=multilingual/code-switching (default: en)",
    )
    parser.add_argument(
        "--translate",
        action="store_true",
        help="Translate to English instead of transcribing in the source language",
    )
    parser.add_argument(
        "--engine",
        default="whisper",
        choices=["whisper", "soniox"],
        help="Transcription engine: whisper (local) or soniox (cloud API, requires SONIOX_API_KEY)",
    )
    parser.add_argument(
        "--skip-summary",
        action="store_true",
        dest="skip_summary",
        help="Skip LLM summarisation — transcribe only, then export raw transcript",
    )
    parser.add_argument(
        "--diarize",
        action="store_true",
        help="Enable speaker diarization (requires HF_TOKEN in .env)",
    )
    parser.add_argument(
        "--num-speakers",
        type=int,
        default=None,
        dest="num_speakers",
        help="Exact number of speakers (overrides auto-detection, e.g. --num-speakers 8)",
    )
    parser.add_argument(
        "--attendance",
        action="store_true",
        help="Check attendance against enrolled voice profiles",
    )
    parser.add_argument(
        "--enroll",
        type=str,
        default=None,
        metavar="NAME",
        help="Enroll a new speaker by recording their voice",
    )
    parser.add_argument(
        "--register",
        type=str,
        default=None,
        metavar="NAMES",
        help='Comma-separated names to enroll before processing (e.g. --register "Ali, Sara, John")',
    )
    return parser


# ---------------------------------------------------------------------------
# Stub phases (--all-phases)
# ---------------------------------------------------------------------------

def run_stub_phases(result):
    """Invoke stub phases 5-8 after the core pipeline.

    Each stub prints a TODO warning and returns an empty/None value.
    Results are attached to the output dict under 'stub_phases'.
    """
    from src.diarization import diarize_audio
    from src.summarizer import generate_minutes
    from src.roman_converter import convert_to_roman
    from src.tts import synthesize_audio

    audio_name = result.get("audio", "")

    print_info("Running stub phases (--all-phases) ...")

    diarization = diarize_audio(audio_name)
    summary = generate_minutes(result.get("correct_text", ""), {}, None)
    roman = convert_to_roman(result.get("correct_text", ""), openai_client=None)
    tts_path = synthesize_audio(roman, output_path=None)

    result["stub_phases"] = {
        "diarization": diarization,
        "summary": summary,
        "roman_text": roman,
        "tts_output": tts_path,
    }
    return result


# ---------------------------------------------------------------------------
# Summary banner
# ---------------------------------------------------------------------------

def print_banner_legacy(audio_name, duration_seconds, language, attendees, fmt, exported_path,
                        speaker_times=None):
    """Print the final summary banner (delegates to ui module)."""
    ui_print_banner(
        audio_name=audio_name,
        duration_seconds=duration_seconds,
        language=language,
        attendees=attendees,
        fmt=fmt,
        exported_path=exported_path,
        speaker_times=speaker_times,
    )


# ---------------------------------------------------------------------------
# Enrollment helper
# ---------------------------------------------------------------------------

def _enroll_one(name, output_dir, env):
    """Record a voice sample for *name* and save an embedding profile.

    Returns True on success, False on failure.
    """
    from src.recorder import record_audio

    name_slug = name.lower().replace(" ", "_")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_wav = output_dir / ("enroll_%s.wav" % name_slug)

    print_info("Recording voice for %s — speak naturally for 15-20 seconds, then press Enter." % name)
    record_audio(temp_wav)

    worker = Path(__file__).resolve().parent / "src" / "_embed_worker.py"
    inp = json.dumps({
        "audio_path": str(temp_wav),
        "segments": [{"speaker": "SPEAKER_00", "start": 0.0, "end": 9999.0}],
        "speaker_map": {"SPEAKER_00": name},
        "hf_token": env.get("HF_TOKEN", ""),
    })
    proc = subprocess.run(
        [sys.executable, str(worker), "learn"],
        input=inp, capture_output=True, text=True, env=env,
        cwd=str(Path(__file__).resolve().parent),
    )
    if proc.returncode == 0 and proc.stdout.strip():
        result = json.loads(proc.stdout)
        if result.get("learned"):
            print_success("Voice profile saved for %s." % name)
            return True
    print_warning("Enrollment failed for %s — ensure HF_TOKEN is set." % name)
    if proc.stderr:
        print_warning(proc.stderr.strip())
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # 0. Print header — only when running interactively (skip in subprocess/pipe)
    if sys.stdout.isatty():
        print_header()

    # 1. Parse args + load .env
    from dotenv import load_dotenv

    parser = build_parser()
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    load_dotenv(project_root / ".env")

    _env = os.environ.copy()
    _env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    _output_dir = Path(args.output_dir) if args.output_dir else project_root / "output"

    # Handle --enroll: record one voice sample and exit
    if args.enroll:
        _enroll_one(args.enroll, _output_dir, _env)
        sys.exit(0)

    # Handle --register: enroll multiple speakers, then continue into the pipeline
    if args.register:
        names = [n.strip() for n in args.register.split(",") if n.strip()]
        print_info("Registering %d speaker(s): %s" % (len(names), ", ".join(names)))
        for name in names:
            _enroll_one(name, _output_dir, _env)
        print_info("Registration complete. Starting meeting processing...")
        # Automatically enable diarize so matching runs right after
        args.diarize = True

    # Validate: at least one of --audio or --record is required
    if not args.audio and not args.record:
        print_error("Either --audio or --record is required.")
        sys.exit(1)

    # Handle --record: capture from microphone first
    if args.record:
        from src.recorder import record_audio

        project_root_rec = Path(__file__).resolve().parent
        rec_output_dir = Path(args.output_dir) if args.output_dir else project_root_rec / "output"
        rec_output_dir.mkdir(parents=True, exist_ok=True)
        rec_path = rec_output_dir / ("recording_%s.wav" % datetime.now().strftime("%Y%m%d_%H%M%S"))
        audio_path = record_audio(rec_path)
        args.audio = str(audio_path)

    # Build Ollama client (no API key needed — runs fully locally)
    ollama_model = os.environ.get("OLLAMA_MODEL", "gemma3:4b").strip()
    openai_client = None
    try:
        from openai import OpenAI
        openai_client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",  # Ollama ignores this but the SDK requires a non-empty string
        )
        # Attach the model name so summarizer can read it
        openai_client._ollama_model = ollama_model
    except Exception as exc:
        print_warning("Could not create Ollama client: %s" % exc)

    # Resolve output directory
    output_dir = _output_dir

    try:
        # 2. process_audio → pipeline_result
        pipeline_result = process_audio(
            audio_path=args.audio,
            model_size=args.model,
            output_dir=output_dir,
            language=args.language,
            diarize=args.diarize,
            num_speakers=args.num_speakers,
            translate=args.translate,
            engine=args.engine,
        )

        # --all-phases: run legacy stubs (existing behaviour preserved)
        if args.all_phases:
            pipeline_result = run_stub_phases(pipeline_result)

        audio_path = Path(args.audio)
        audio_stem = audio_path.stem
        duration_seconds = pipeline_result.get("duration_seconds", 0.0)
        transcript = pipeline_result.get("correct_text", "")

        # 3. Build meeting_info from args + pipeline_result
        title = args.title if args.title else audio_stem
        attendees = (
            [a.strip() for a in args.attendees.split(",") if a.strip()]
            if args.attendees
            else []
        )
        meeting_info = {
            "title": title,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "language": _LANGUAGE_LABELS.get(args.language, args.language),
            "attendees": attendees,
            "duration_seconds": duration_seconds,
        }

        # Attach diarization data if available
        speaker_times = pipeline_result.get("speaker_times")
        if speaker_times:
            meeting_info["speaker_times"] = speaker_times

        speaker_transcript = pipeline_result.get("speaker_transcript", "")
        if speaker_transcript:
            meeting_info["speaker_transcript"] = speaker_transcript

        # Attendance check — runs automatically when diarizing if profiles exist
        # (or when --attendance is explicitly set). Skipped silently if no profiles enrolled yet.
        if args.diarize or args.attendance:
            from src.attendance import build_attendance, format_attendance_report, get_enrolled_names

            enrolled = get_enrolled_names()
            expected = (
                [a.strip() for a in args.attendees.split(",") if a.strip()]
                if args.attendees
                else None
            )
            # Only run if there's something to compare against
            if enrolled or expected:
                # Use speaker_times keys (already auto-matched to real names)
                speaker_times_dict = pipeline_result.get("speaker_times", {})
                unique_labels = set(speaker_times_dict.keys()) if speaker_times_dict else set()
                attendance = build_attendance(list(unique_labels), expected)
                print_info(format_attendance_report(attendance))
                meeting_info["attendance"] = attendance

        # 4. Generate minutes (unless --skip-summary)
        if args.skip_summary:
            minutes_dict = dict(meeting_info)
            minutes_dict["transcript"] = transcript
            minutes_dict["key_decisions"] = []
            minutes_dict["action_items"] = []
            minutes_dict["deadlines"] = []
            minutes_dict["next_steps"] = []
            minutes_dict["qa_pairs"] = []
            minutes_dict["session_summary"] = ""
        else:
            minutes_dict = generate_minutes(transcript, meeting_info, openai_client)

        # 5. Merge meeting metadata into minutes_dict (ensure consistency)
        for key, value in meeting_info.items():
            if key not in minutes_dict:
                minutes_dict[key] = value

        # 6. Determine output path for minutes
        ts_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
        minutes_filename = "%s_minutes_%s" % (audio_stem, ts_slug)
        output_path = output_dir / minutes_filename

        # 7. Export minutes
        exported_path = export_minutes(minutes_dict, output_path, format=args.fmt)

        # 8. Print speaker map path if diarization was run
        speaker_map_path = pipeline_result.get("speaker_map_path")
        if speaker_map_path:
            print_info("Speaker map: %s" % speaker_map_path)
            print_info("Edit this file to assign real names, then re-run to apply.")

        # 9. Print banner
        print_banner_legacy(
            audio_name=audio_path.name,
            duration_seconds=duration_seconds,
            language=args.language,
            attendees=attendees,
            fmt=args.fmt,
            exported_path=exported_path,
            speaker_times=speaker_times,
        )

    except FileNotFoundError as exc:
        print_error(str(exc))
        sys.exit(1)
    except RuntimeError as exc:
        print_error(str(exc))
        sys.exit(2)
    except Exception as exc:
        print_error(str(exc))
        sys.exit(3)


if __name__ == "__main__":
    main()
