"""
Core pipeline: Audio -> Whisper transcription -> GPT correction -> JSON output.

Handles Lisan-ud-Dawat (LSD) audio recordings written in Urdu script.
Whisper uses language='ar' (Arabic script family) for best Urdu-script results.
"""

import gc
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"
CONFIG_DIR = PROJECT_ROOT / "config"

logger = logging.getLogger(__name__)


def _diar_cache_path(audio_path, output_dir, num_speakers):
    """Return the path for a diarization result cache file.

    Cache key = MD5 of first 64KB of audio + file size + num_speakers.
    This avoids re-running the slow pyannote pipeline on the same audio.
    """
    import hashlib
    audio_path = Path(audio_path)
    with open(audio_path, "rb") as fh:
        digest = hashlib.md5(fh.read(65536)).hexdigest()[:8]
    size_tag = audio_path.stat().st_size
    spk_tag = num_speakers if num_speakers is not None else "auto"
    cache_name = "%s_diar_%s_%s.json" % (audio_path.stem, digest, spk_tag)
    return Path(output_dir) / cache_name

# ---------------------------------------------------------------------------
# 1. load_config
# ---------------------------------------------------------------------------

def load_config(config_dir=None):
    """Load script_standard.json and correction_prompt.txt from *config_dir*.

    Returns a dict with keys:
        - "standard": parsed JSON dict from script_standard.json
        - "prompt_template": string contents of correction_prompt.txt
    """
    config_dir = Path(config_dir) if config_dir else CONFIG_DIR

    standard_path = config_dir / "script_standard.json"
    prompt_path = config_dir / "correction_prompt.txt"

    if not standard_path.exists():
        raise FileNotFoundError(
            "script_standard.json not found at %s" % standard_path
        )
    if not prompt_path.exists():
        raise FileNotFoundError(
            "correction_prompt.txt not found at %s" % prompt_path
        )

    with open(standard_path, "r", encoding="utf-8") as fh:
        standard = json.load(fh)

    with open(prompt_path, "r", encoding="utf-8") as fh:
        prompt_template = fh.read()

    return {"standard": standard, "prompt_template": prompt_template}


# ---------------------------------------------------------------------------
# 2. check_ffmpeg
# ---------------------------------------------------------------------------

def check_ffmpeg():
    """Verify that ffmpeg is available on PATH.

    Raises RuntimeError with install instructions when missing.
    """
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg is not installed or not on PATH.\n"
            "Whisper requires ffmpeg to decode audio files.\n\n"
            "Install it with:\n"
            "  macOS:   brew install ffmpeg\n"
            "  Ubuntu:  sudo apt install ffmpeg\n"
            "  Windows: choco install ffmpeg   (or download from https://ffmpeg.org)"
        )
    logger.info("ffmpeg found: %s", shutil.which("ffmpeg"))


# ---------------------------------------------------------------------------
# 3. transcribe_audio
# ---------------------------------------------------------------------------

# Try to import faster-whisper; fall back to openai-whisper if unavailable.
try:
    from faster_whisper import WhisperModel as _FasterWhisperModel
    _HAS_FASTER_WHISPER = True
except ImportError:
    _HAS_FASTER_WHISPER = False


def _transcribe_faster_whisper(audio_path, model_size, language, step_total, translate=False):
    """Transcribe using faster-whisper (CTranslate2 backend, 2-4x faster on CPU)."""
    from rich.progress import (
        Progress, BarColumn, TimeRemainingColumn, TimeElapsedColumn, TextColumn,
    )
    from rich.console import Console
    from src.ui import print_step, print_info

    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError("Audio file not found: %s" % audio_path)

    # Map model names for compatibility
    fw_model_size = "large-v2" if model_size == "large" else model_size

    print_step(1, step_total, "Loading faster-whisper model '%s' ..." % fw_model_size)
    model = _FasterWhisperModel(fw_model_size, device="cpu", compute_type="int8")

    task = "translate" if translate else "transcribe"
    lang_label = "auto-detect" if language is None else language
    task_label = "Translating to English" if translate else "Transcribing"
    print_step(2, step_total, "%s %s (language=%s) ..." % (task_label, audio_path.name, lang_label))
    segments_gen, info = model.transcribe(
        str(audio_path),
        language=language,
        task=task,
        beam_size=5,
        word_timestamps=True,
        condition_on_previous_text=False,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        no_speech_threshold=0.6,
        compression_ratio_threshold=1.8,   # was 2.4 — catches repetition hallucinations
        repetition_penalty=1.2,            # penalises repeated tokens
        temperature=0.0,
    )

    # info.duration is available BEFORE consuming the generator
    duration = info.duration

    # Consume generator with a real-time progress bar
    rich_console = Console()
    raw_segments = []
    full_text_parts = []

    with Progress(
        TextColumn("    [cyan]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TextColumn("·"),
        TimeRemainingColumn(),
        console=rich_console,
        transient=False,
        redirect_stdout=False,  # keep sys.stdout unredirected so [TRANSCRIPT] lines reach the pipe
    ) as progress:
        task = progress.add_task(
            "Transcribing (%.0fs audio)" % duration,
            total=duration,
        )
        for seg in segments_gen:
            raw_segments.append(seg)
            full_text_parts.append(seg.text)
            progress.update(task, completed=seg.end)
            sys.stdout.write("[TRANSCRIPT] %s\n" % seg.text.strip())
            sys.stdout.flush()

    # Convert faster-whisper segment objects to dicts matching openai-whisper format
    seg_dicts = []
    for i, seg in enumerate(raw_segments):
        seg_dict = {
            "id": i,
            "start": seg.start,
            "end": seg.end,
            "text": seg.text,
        }
        if seg.words:
            seg_dict["words"] = [
                {"word": w.word, "start": w.start, "end": w.end, "probability": w.probability}
                for w in seg.words
            ]
        seg_dicts.append(seg_dict)

    full_text = " ".join(full_text_parts).strip()

    # Explicitly release the CTranslate2 model before returning so its OpenMP
    # threads are torn down before pyannote/torch initialise theirs (segfault fix).
    del model
    gc.collect()

    print_info("Transcription complete (%.1f s of audio)." % duration)

    return {
        "text": full_text,
        "duration": round(duration, 2),
        "segments": seg_dicts,
        "model_size": model_size,
    }


def _transcribe_openai_whisper(audio_path, model_size, language, step_total, translate=False):
    """Transcribe using openai-whisper (fallback)."""
    import whisper

    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError("Audio file not found: %s" % audio_path)

    from src.ui import print_step, print_info

    task = "translate" if translate else "transcribe"
    print_step(1, step_total, "Loading Whisper model '%s' ..." % model_size)
    model = whisper.load_model(model_size)

    task_label = "Translating to English" if translate else "Transcribing"
    print_step(2, step_total, "%s %s (language=%s) ..." % (task_label, audio_path.name, language))
    result = model.transcribe(
        str(audio_path),
        language=language,
        task=task,
        fp16=False,
        word_timestamps=True,
        condition_on_previous_text=False,
        beam_size=5,
        temperature=0.0,
        no_speech_threshold=0.6,
        compression_ratio_threshold=2.4,
    )

    segments = result.get("segments", [])
    if segments:
        duration = segments[-1].get("end", 0.0)
    else:
        duration = 0.0

    print_info("Transcription complete (%.1f s of audio)." % duration)

    return {
        "text": result.get("text", "").strip(),
        "duration": round(duration, 2),
        "segments": segments,
        "model_size": model_size,
    }


def transcribe_audio(audio_path, model_size="base", language="en", step_total=3, translate=False):
    """Run Whisper on *audio_path*.

    Uses faster-whisper (CTranslate2) when available for 2-4x speedup on CPU,
    with a real-time progress bar. Falls back to openai-whisper otherwise.

    Parameters
    ----------
    audio_path : str or Path
        Path to an audio file (wav, mp3, m4a, etc.).
    model_size : str
        Whisper model size: tiny | base | small | medium | large.
    language : str
        BCP-47 language code passed to Whisper.
        Use "en" for English, "ar" for LSD/Urdu script (Arabic-script family).
    step_total : int
        Total number of pipeline steps (for step numbering display).
    translate : bool
        When True, translate to English instead of transcribing in the source language.

    Returns
    -------
    dict with keys:
        - text: full transcription string
        - duration: audio duration in seconds (float)
        - segments: list of segment dicts from whisper
        - model_size: the model size that was used
    """
    if _HAS_FASTER_WHISPER:
        return _transcribe_faster_whisper(audio_path, model_size, language, step_total, translate=translate)
    else:
        logger.info("faster-whisper not available, falling back to openai-whisper")
        return _transcribe_openai_whisper(audio_path, model_size, language, step_total, translate=translate)


# ---------------------------------------------------------------------------
# 4. correct_transcript
# ---------------------------------------------------------------------------

def correct_transcript(whisper_text, prompt_template, openai_client, step_num=3, step_total=3):
    """Send whisper_text through Ollama for LSD nasal-rule correction.

    Parameters
    ----------
    whisper_text : str
        Raw text from Whisper.
    prompt_template : str
        Template string containing ``{whisper_output}`` placeholder.
    openai_client : openai.OpenAI
        An Ollama-compatible client (base_url=http://localhost:11434/v1).

    Returns
    -------
    str  -- corrected text from Ollama.
    """
    prompt = prompt_template.format(whisper_output=whisper_text)
    model_name = getattr(openai_client, "_ollama_model", "gemma3:4b")

    from src.ui import print_step, print_info

    print_step(step_num, step_total, "Sending to Ollama (%s) for LSD correction ..." % model_name)
    response = openai_client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    corrected = response.choices[0].message.content.strip()

    # Strip preamble lines that are not part of the actual corrected text.
    # The model sometimes prepends English explanation lines.
    _PREAMBLE_PATTERNS = re.compile(
        r"^(Here is|Sure,|The corrected|Corrected:|Below is|I have)",
        re.IGNORECASE,
    )
    lines = corrected.split("\n")
    while lines and _PREAMBLE_PATTERNS.match(lines[0].strip()):
        lines.pop(0)
    corrected = "\n".join(lines).strip()

    print_info("Correction complete.")
    return corrected


# ---------------------------------------------------------------------------
# Step counting helper
# ---------------------------------------------------------------------------

def _count_steps(language, diarize):
    """Compute the total number of pipeline steps based on flags.

    Steps: 1=load model, 2=transcribe, (3=correct if LSD), (N=diarize if enabled).
    """
    total = 2  # load + transcribe
    if language == "lsd":
        total += 1  # correct
    if diarize:
        total += 1  # diarize
    return total


# ---------------------------------------------------------------------------
# 5. process_audio  (full pipeline)
# ---------------------------------------------------------------------------

def process_audio(audio_path, model_size="base", output_dir=None, language="en", diarize=False, num_speakers=None, translate=False, engine="whisper"):
    """Run the full pipeline: transcribe -> correct -> save JSON.

    Parameters
    ----------
    audio_path : str or Path
        Path to the audio file.
    model_size : str
        Whisper model size (default ``"base"``).
    output_dir : str or Path or None
        Where to write the output JSON.  Defaults to ``<project>/output/``.
    language : str
        Meeting language code: "en" for English, "ar" for LSD/Urdu script.
        Passed directly to Whisper. (default ``"en"``)
    diarize : bool
        When True, run pyannote speaker diarization after transcription.
        Requires ``HF_TOKEN`` in environment. (default ``False``)

    Returns
    -------
    dict -- the output record (also saved as JSON).
    """
    # -- environment --------------------------------------------------------
    load_dotenv(PROJECT_ROOT / ".env")

    # -- pre-flight ---------------------------------------------------------
    check_ffmpeg()

    audio_path = Path(audio_path).resolve()
    output_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # -- config -------------------------------------------------------------
    config = load_config()
    prompt_template = config["prompt_template"]

    # -- compute step total -------------------------------------------------
    step_total = _count_steps(language, diarize)

    # -- transcribe ---------------------------------------------------------
    soniox_diar_segments = None  # populated when engine=soniox + diarize

    if engine == "soniox":
        from src.soniox_transcriber import transcribe_soniox
        soniox_lang = None if language in ("auto", "lsd") else language
        whisper_result = transcribe_soniox(
            audio_path,
            language=soniox_lang,
            diarize=diarize,
            translate=translate,
            step_total=step_total,
        )
        # Soniox returns diar_segments directly — skip pyannote diarization
        if diarize and whisper_result.get("diar_segments"):
            soniox_diar_segments = whisper_result["diar_segments"]
    else:
        # Map language codes to Whisper language hints:
        #   "lsd"  → "ar"  (Lisan-ud-Dawat uses Arabic script)
        #   "auto" → None  (Whisper auto-detects per segment)
        #   "en"   → "en"
        if language == "lsd":
            whisper_lang = "ar"
        elif language == "auto":
            whisper_lang = None
        else:
            whisper_lang = language
        whisper_result = transcribe_audio(audio_path, model_size=model_size, language=whisper_lang, step_total=step_total, translate=translate)

    whisper_text = whisper_result["text"]

    # Force release of faster-whisper / CTranslate2 resources before diarization.
    gc.collect()

    # -- correct via Ollama (LSD only — skip for English) --------------------
    correction_applied = False
    corrected_text = whisper_text  # fallback: raw whisper output
    current_step = 3  # next step after load + transcribe

    if language == "lsd":
        try:
            from openai import OpenAI
            ollama_model = os.environ.get("OLLAMA_MODEL", "gemma3:4b").strip()
            client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
            client._ollama_model = ollama_model
            corrected_text = correct_transcript(
                whisper_text, prompt_template, client,
                step_num=current_step, step_total=step_total,
            )
            correction_applied = True
        except Exception as exc:
            from src.ui import print_warning
            logger.warning("Ollama correction failed, using raw Whisper output: %s", exc)
            print_warning("Ollama correction failed (%s). Using raw Whisper output." % exc)
        current_step += 1
    else:
        from src.ui import print_info
        print_info("Skipping LSD correction (language=%s)." % language)

    # -- diarization (optional) ---------------------------------------------
    speaker_times = None
    speaker_map_path = None
    speaker_transcript = ""

    # If Soniox already provided diarization, use it directly
    if soniox_diar_segments:
        from src.diarization import compute_talk_time, build_speaker_transcript
        diar_segments = soniox_diar_segments

        # Soniox segments already have speaker + text — attach to whisper segments
        for seg in whisper_result["segments"]:
            seg["speaker_label"] = seg.get("speaker", "Unknown")

        # Auto-match Soniox speaker IDs to enrolled profiles
        try:
            from src.speaker_profiles import load_all_profiles
            if load_all_profiles():
                worker = Path(__file__).resolve().parent / "_embed_worker.py"
                env = os.environ.copy()
                env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
                inp = json.dumps({
                    "audio_path": str(audio_path),
                    "segments": diar_segments,
                    "hf_token": os.environ.get("HF_TOKEN", ""),
                })
                proc2 = subprocess.run(
                    [sys.executable, str(worker), "match"],
                    input=inp, capture_output=True, text=True, env=env,
                    cwd=str(PROJECT_ROOT),
                )
                if proc2.returncode == 0 and proc2.stdout.strip():
                    matches = json.loads(proc2.stdout).get("matches", {})
                    for seg in diar_segments:
                        matched = matches.get(seg["speaker"])
                        if matched:
                            seg["speaker"] = matched
                    for seg in whisper_result["segments"]:
                        old = seg.get("speaker_label", "")
                        matched = matches.get(old)
                        if matched:
                            seg["speaker_label"] = matched
                    for label, name in matches.items():
                        if name:
                            from src.ui import print_info as _pi
                            _pi("Auto-matched %s → %s" % (label, name))
        except Exception:
            pass

        speaker_times = compute_talk_time(diar_segments)
        speaker_transcript = build_speaker_transcript(whisper_result["segments"])
        from src.ui import print_info
        print_info("Detected %d speakers (via Soniox): %s" % (
            len(speaker_times), ", ".join(speaker_times.keys())
        ))
        # Skip pyannote diarization
        diarize = False

    if diarize:
        try:
            from src.diarization import (
                diarize_audio,
                align_transcript_speakers,
                build_speaker_transcript,
                compute_talk_time,
                load_speaker_map,
                apply_speaker_map,
                save_speaker_map,
            )
        except ImportError as exc:
            logger.warning("Diarization module unavailable (%s) — skipping.", exc)
            diarize = False

    if diarize:
        from src.ui import print_step, print_info, print_warning
        print_step(step_total, step_total, "Diarizing speakers ...")

        # Check diarization cache first — skip the slow subprocess on re-runs.
        cache_path = _diar_cache_path(audio_path, output_dir, num_speakers)
        if cache_path.exists():
            print_info("Using cached diarization (%s)." % cache_path.name)
            try:
                with open(cache_path, "r", encoding="utf-8") as _cf:
                    diar_segments = json.load(_cf)
            except (json.JSONDecodeError, OSError):
                diar_segments = []
                cache_path.unlink(missing_ok=True)  # corrupt cache — delete it
        else:
            # Run diarization in a subprocess to avoid OpenMP segfault:
            # CTranslate2 (faster-whisper) leaves OpenMP threads alive in the
            # current process; pyannote/torch segfaults when it tries to init
            # its own OpenMP context. A fresh subprocess has a clean slate.
            worker = Path(__file__).resolve().parent / "_diarize_worker.py"
            env = os.environ.copy()
            env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
            proc = subprocess.run(
                [sys.executable, str(worker), str(audio_path), str(num_speakers)],
                capture_output=True,
                text=True,
                env=env,
                cwd=str(PROJECT_ROOT),
            )

            # C4: Check subprocess returncode before processing output
            if proc.returncode != 0:
                print_warning("Diarization failed — skipping speaker detection.")
                if proc.stderr:
                    for line in proc.stderr.strip().splitlines():
                        if line.strip():
                            logger.warning("diarize_worker: %s", line)
                diar_segments = []
            else:
                # Forward any warnings/info from the subprocess to the terminal
                if proc.stderr:
                    _ERROR_PATTERNS = re.compile(
                        r"(Error|Traceback|Exception|FAILED)", re.IGNORECASE
                    )
                    for line in proc.stderr.strip().splitlines():
                        if line.strip():
                            if _ERROR_PATTERNS.search(line):
                                print_warning(line)
                            else:
                                print_info(line)

                try:
                    diar_segments = json.loads(proc.stdout) if proc.stdout.strip() else []
                except json.JSONDecodeError:
                    print_warning("Diarization subprocess returned unexpected output — skipping.")
                    diar_segments = []

            # Save to cache so re-runs are instant.
            if diar_segments:
                try:
                    with open(cache_path, "w", encoding="utf-8") as _cf:
                        json.dump(diar_segments, _cf)
                except OSError as exc:
                    logger.warning("Could not write diarization cache: %s", exc)

        # Phase 2: Auto-match speakers to known profiles via subprocess.
        # Runs in a subprocess to avoid OpenMP conflicts between CTranslate2
        # (faster-whisper) and pyannote/embedding.
        if diar_segments:
            try:
                from src.speaker_profiles import load_all_profiles
                if load_all_profiles():  # only launch subprocess if profiles exist
                    worker = Path(__file__).resolve().parent / "_embed_worker.py"
                    inp = json.dumps({
                        "audio_path": str(audio_path),
                        "segments": diar_segments,
                        "hf_token": os.environ.get("HF_TOKEN", ""),
                    })
                    proc2 = subprocess.run(
                        [sys.executable, str(worker), "match"],
                        input=inp, capture_output=True, text=True, env=env,
                        cwd=str(PROJECT_ROOT),
                    )
                    if proc2.returncode == 0 and proc2.stdout.strip():
                        result = json.loads(proc2.stdout)
                        matches = result.get("matches", {})
                        for seg in diar_segments:
                            matched = matches.get(seg["speaker"])
                            if matched:
                                seg["speaker"] = matched
                        for label, name in matches.items():
                            if name:
                                print_info("Auto-matched %s → %s" % (label, name))
            except Exception as exc:
                logger.debug("Phase 2 auto-matching failed (non-fatal): %s", exc)

        if diar_segments:
            # Align whisper segments with diarization
            align_transcript_speakers(whisper_result["segments"], diar_segments)

            # Stream merged segments to the web API for live display
            for _seg in whisper_result["segments"]:
                _sp = _seg.get("speaker_label", _seg.get("speaker", "Unknown"))
                _txt = _seg.get("text", "").strip()
                if _txt:
                    sys.stdout.write("[DIAR_SEGMENT] %s\n" % json.dumps({
                        "speaker": _sp,
                        "text": _txt,
                        "start": round(_seg.get("start", 0), 2),
                        "end": round(_seg.get("end", 0), 2),
                    }))
            sys.stdout.flush()

            # Compute talk time
            speaker_times = compute_talk_time(diar_segments)
            speaker_labels = list(speaker_times.keys())

            print_info("Detected %d speakers: %s" % (
                len(speaker_labels), ", ".join(speaker_labels)
            ))

            # Speaker map file
            stem = audio_path.stem
            speaker_map_path = output_dir / ("%s_speakers.json" % stem)

            existing_map = load_speaker_map(speaker_map_path)
            if existing_map:
                apply_speaker_map(whisper_result["segments"], existing_map)
                # Also rename keys in speaker_times
                renamed_times = {}
                for label, seconds in speaker_times.items():
                    mapped = existing_map.get(label, label)
                    if mapped and mapped != label:
                        renamed_times[mapped] = seconds
                    else:
                        renamed_times[label] = seconds
                speaker_times = renamed_times

                # Phase 2: Silent speaker learning via subprocess — store
                # voice profiles for speakers that the user has assigned
                # real names to.
                try:
                    worker = Path(__file__).resolve().parent / "_embed_worker.py"
                    inp = json.dumps({
                        "audio_path": str(audio_path),
                        "segments": diar_segments,
                        "speaker_map": existing_map,
                        "hf_token": os.environ.get("HF_TOKEN", ""),
                    })
                    proc3 = subprocess.run(
                        [sys.executable, str(worker), "learn"],
                        input=inp, capture_output=True, text=True, env=env,
                        cwd=str(PROJECT_ROOT),
                    )
                    # M10: verify returncode before trusting learned list
                    if proc3.returncode != 0:
                        print_warning("Speaker profile learning subprocess failed.")
                    elif proc3.stdout.strip():
                        result = json.loads(proc3.stdout)
                        for name in result.get("learned", []):
                            print_info("Learned voice profile: %s" % name)
                except Exception as exc:
                    logger.debug("Speaker profile learning failed (non-fatal): %s", exc)
            else:
                save_speaker_map(speaker_map_path, speaker_labels)
                # M3: Tell user what to do next
                print_info("Edit the speaker map, then re-run this command to learn speaker voices.")

            # Build speaker-attributed transcript string (after speaker map
            # has been applied so labels reflect real names when available).
            speaker_transcript = build_speaker_transcript(whisper_result["segments"])
        else:
            print_info("No diarization segments produced.")

    # -- build output record ------------------------------------------------
    timestamp = datetime.now(timezone.utc).isoformat()
    record = {
        "audio": audio_path.name,
        "whisper_output": whisper_text,
        "correct_text": corrected_text,
        "timestamp": timestamp,
        "duration_seconds": whisper_result["duration"],
        "model_used": "whisper-%s" % model_size,
        "correction_applied": correction_applied,
    }

    if speaker_times is not None:
        record["speaker_times"] = speaker_times
    if speaker_map_path is not None:
        record["speaker_map_path"] = str(speaker_map_path)
    if speaker_transcript:
        record["speaker_transcript"] = speaker_transcript

    # -- save JSON ----------------------------------------------------------
    stem = audio_path.stem
    ts_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_file = output_dir / ("%s_%s.json" % (stem, ts_slug))

    with open(out_file, "w", encoding="utf-8") as fh:
        json.dump(record, fh, ensure_ascii=False, indent=2)

    from src.ui import print_success
    print_success("Output saved to: %s" % out_file)
    return record


# ---------------------------------------------------------------------------
# Quick CLI for testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python -m src.pipeline <audio_file> [model_size]")
        sys.exit(1)

    _audio = sys.argv[1]
    _model = sys.argv[2] if len(sys.argv) > 2 else "base"
    process_audio(_audio, model_size=_model)
