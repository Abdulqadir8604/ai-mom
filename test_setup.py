#!/usr/bin/env python3
"""
test_setup.py — Setup verification script for ai-mom project.

Checks that the project is correctly structured without requiring:
  - Real audio files
  - OpenAI API keys
  - Whisper model downloads
  - External dependencies beyond stdlib

Run as:  python test_setup.py

Exit code: 0 if all checks pass, 1 if any fail.
"""

import json
import py_compile
import sys
from pathlib import Path

# Project structure
PROJECT_ROOT = Path(__file__).resolve().parent
CHECKS_PASSED = 0
CHECKS_TOTAL = 9
RESULTS = []


def print_check(check_name, passed, message=""):
    """Print a single check result."""
    global CHECKS_PASSED
    status = "PASS" if passed else "FAIL"
    msg = f"[{status}] {check_name}"
    if message:
        msg += f" — {message}"
    print(msg)
    RESULTS.append((check_name, passed, message))
    if passed:
        CHECKS_PASSED += 1


# =============================================================================
# Check 1: Directory structure
# =============================================================================

def check_directory_structure():
    """Verify all required directories exist."""
    required_dirs = ["src", "config", "output", "audio"]
    missing = []

    for dirname in required_dirs:
        dir_path = PROJECT_ROOT / dirname
        if not dir_path.is_dir():
            missing.append(dirname)

    if missing:
        print_check(
            "Directory structure",
            False,
            f"Missing: {', '.join(missing)}"
        )
    else:
        print_check("Directory structure", True)


# =============================================================================
# Check 2: Config files exist
# =============================================================================

def check_config_files():
    """Verify config files exist (script_standard.json, correction_prompt.txt)."""
    config_dir = PROJECT_ROOT / "config"
    json_path = config_dir / "script_standard.json"
    prompt_path = config_dir / "correction_prompt.txt"

    missing = []
    if not json_path.exists():
        missing.append("script_standard.json")
    if not prompt_path.exists():
        missing.append("correction_prompt.txt")

    if missing:
        print_check(
            "Config files exist",
            False,
            f"Missing: {', '.join(missing)}"
        )
    else:
        print_check("Config files exist", True)


# =============================================================================
# Check 3: script_standard.json is valid JSON with 6 groups
# =============================================================================

def check_script_standard_json():
    """Verify script_standard.json is valid and contains required structure."""
    json_path = PROJECT_ROOT / "config" / "script_standard.json"

    try:
        with open(json_path, "r", encoding="utf-8") as fh:
            standard = json.load(fh)

        # Check for required top-level keys
        required_keys = ["language", "script", "groups"]
        missing_keys = [k for k in required_keys if k not in standard]

        if missing_keys:
            print_check(
                "script_standard.json structure",
                False,
                f"Missing keys: {', '.join(missing_keys)}"
            )
            return

        # Check groups
        groups = standard.get("groups", [])
        if len(groups) != 6:
            print_check(
                "script_standard.json groups",
                False,
                f"Expected 6 groups, got {len(groups)}"
            )
            return

        # Check group IDs
        expected_ids = {"A", "B", "C", "D", "E", "F"}
        actual_ids = {g.get("id") for g in groups}

        if actual_ids != expected_ids:
            print_check(
                "script_standard.json nasal groups",
                False,
                f"Expected {expected_ids}, got {actual_ids}"
            )
            return

        # Check nasal values
        nasal_checks = {
            "A": False,  # maa preposition — no nasal
            "B": True,   # maa mother — with nasal
            "C": False,  # hard noon — pronouns
            "D": False,  # hard noon — verbs
            "E": False,  # hard noon — nouns
            "F": True,   # noon ghunna — locatives
        }

        group_by_id = {g["id"]: g for g in groups}
        nasal_mismatch = []

        for gid, expected_nasal in nasal_checks.items():
            actual_nasal = group_by_id[gid].get("nasal")
            if actual_nasal != expected_nasal:
                nasal_mismatch.append(f"{gid}(expected {expected_nasal}, got {actual_nasal})")

        if nasal_mismatch:
            print_check(
                "script_standard.json nasal values",
                False,
                f"Mismatch: {', '.join(nasal_mismatch)}"
            )
            return

        print_check("script_standard.json structure and content", True)

    except json.JSONDecodeError as e:
        print_check(
            "script_standard.json JSON validity",
            False,
            f"Invalid JSON: {e}"
        )
    except Exception as e:
        print_check(
            "script_standard.json parse",
            False,
            f"Error: {e}"
        )


# =============================================================================
# Check 4: correction_prompt.txt contains {whisper_output}
# =============================================================================

def check_correction_prompt():
    """Verify correction_prompt.txt exists and contains placeholder."""
    prompt_path = PROJECT_ROOT / "config" / "correction_prompt.txt"

    try:
        with open(prompt_path, "r", encoding="utf-8") as fh:
            content = fh.read()

        if "{whisper_output}" not in content:
            print_check(
                "correction_prompt.txt placeholder",
                False,
                "Missing {whisper_output} placeholder"
            )
        else:
            print_check("correction_prompt.txt content", True)

    except Exception as e:
        print_check(
            "correction_prompt.txt read",
            False,
            f"Error: {e}"
        )


# =============================================================================
# Check 5: Source modules exist
# =============================================================================

def check_source_modules():
    """Verify all src/*.py modules exist."""
    src_dir = PROJECT_ROOT / "src"
    required_modules = [
        "pipeline.py",
        "diarization.py",
        "summarizer.py",
        "roman_converter.py",
        "tts.py"
    ]

    missing = []
    for module in required_modules:
        module_path = src_dir / module
        if not module_path.exists():
            missing.append(module)

    if missing:
        print_check(
            "Source modules exist",
            False,
            f"Missing: {', '.join(missing)}"
        )
    else:
        print_check("Source modules exist", True)


# =============================================================================
# Check 6: run.py exists
# =============================================================================

def check_run_py():
    """Verify run.py exists and is readable."""
    run_path = PROJECT_ROOT / "run.py"

    if not run_path.exists():
        print_check("run.py exists", False)
    elif not run_path.is_file():
        print_check("run.py is file", False)
    else:
        try:
            with open(run_path, "r", encoding="utf-8") as fh:
                _ = fh.read()
            print_check("run.py exists and readable", True)
        except Exception as e:
            print_check("run.py readable", False, f"Error: {e}")


# =============================================================================
# Check 7: .env.example exists with OPENAI_API_KEY
# =============================================================================

def check_env_template():
    """Verify .env.example exists and contains OPENAI_API_KEY."""
    env_path = PROJECT_ROOT / ".env.example"

    if not env_path.exists():
        print_check(".env.example exists", False)
        return

    try:
        with open(env_path, "r", encoding="utf-8") as fh:
            content = fh.read()

        if "OPENAI_API_KEY" not in content:
            print_check(
                ".env.example content",
                False,
                "Missing OPENAI_API_KEY"
            )
        else:
            print_check(".env.example exists and configured", True)

    except Exception as e:
        print_check(".env.example read", False, f"Error: {e}")


# =============================================================================
# Check 8: Python syntax — compile all .py files
# =============================================================================

def check_python_syntax():
    """Compile all Python files to check for syntax errors."""
    py_files = list(PROJECT_ROOT.glob("src/**/*.py")) + [
        PROJECT_ROOT / "run.py"
    ]

    syntax_errors = []

    for py_file in py_files:
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as e:
            syntax_errors.append(f"{py_file.name}: {e}")

    if syntax_errors:
        print_check(
            "Python syntax validity",
            False,
            f"{len(syntax_errors)} file(s) have syntax errors"
        )
        for err in syntax_errors:
            print(f"    {err}")
    else:
        print_check("Python syntax validity", True)


# =============================================================================
# Check 9 (bonus): Stub functions are callable
# =============================================================================

def check_stub_functions():
    """Import stub functions and verify they're callable."""
    stub_checks = []

    try:
        from src.diarization import diarize_audio
        if callable(diarize_audio):
            stub_checks.append(("diarize_audio", True))
        else:
            stub_checks.append(("diarize_audio", False, "not callable"))
    except Exception as e:
        stub_checks.append(("diarize_audio", False, str(e)))

    try:
        from src.summarizer import generate_summary
        if callable(generate_summary):
            stub_checks.append(("generate_summary", True))
        else:
            stub_checks.append(("generate_summary", False, "not callable"))
    except Exception as e:
        stub_checks.append(("generate_summary", False, str(e)))

    try:
        from src.roman_converter import convert_to_roman
        if callable(convert_to_roman):
            stub_checks.append(("convert_to_roman", True))
        else:
            stub_checks.append(("convert_to_roman", False, "not callable"))
    except Exception as e:
        stub_checks.append(("convert_to_roman", False, str(e)))

    try:
        from src.tts import synthesize_audio
        if callable(synthesize_audio):
            stub_checks.append(("synthesize_audio", True))
        else:
            stub_checks.append(("synthesize_audio", False, "not callable"))
    except Exception as e:
        stub_checks.append(("synthesize_audio", False, str(e)))

    # Try calling stub functions without arguments (they should handle gracefully)
    try:
        from src.diarization import diarize_audio
        result = diarize_audio(str(PROJECT_ROOT / "audio" / "test.wav"))
        if isinstance(result, list):
            stub_checks.append(("diarize_audio() call", True))
        else:
            stub_checks.append(("diarize_audio() call", False, "unexpected return type"))
    except TypeError:
        # Expected: requires arguments, but import works
        stub_checks.append(("diarize_audio() callable", True))
    except Exception as e:
        stub_checks.append(("diarize_audio() call", False, str(e)))

    try:
        from src.summarizer import generate_summary
        result = generate_summary("test", None)
        if isinstance(result, dict):
            stub_checks.append(("generate_summary() call", True))
        else:
            stub_checks.append(("generate_summary() call", False, "unexpected return type"))
    except TypeError:
        stub_checks.append(("generate_summary() callable", True))
    except Exception as e:
        stub_checks.append(("generate_summary() call", False, str(e)))

    try:
        from src.roman_converter import convert_to_roman
        result = convert_to_roman("test", None)
        if isinstance(result, str):
            stub_checks.append(("convert_to_roman() call", True))
        else:
            stub_checks.append(("convert_to_roman() call", False, "unexpected return type"))
    except TypeError:
        stub_checks.append(("convert_to_roman() callable", True))
    except Exception as e:
        stub_checks.append(("convert_to_roman() call", False, str(e)))

    try:
        from src.tts import synthesize_audio
        result = synthesize_audio("test", None)
        if result is None or isinstance(result, str):
            stub_checks.append(("synthesize_audio() call", True))
        else:
            stub_checks.append(("synthesize_audio() call", False, "unexpected return type"))
    except TypeError:
        stub_checks.append(("synthesize_audio() callable", True))
    except Exception as e:
        stub_checks.append(("synthesize_audio() call", False, str(e)))

    all_passed = all(check[1] for check in stub_checks)

    if all_passed:
        print_check("Stub functions callable and importable", True)
    else:
        failures = [c[0] for c in stub_checks if not c[1]]
        print_check(
            "Stub functions callable and importable",
            False,
            f"Issues with: {', '.join(failures)}"
        )


# =============================================================================
# Main
# =============================================================================

def main():
    """Run all checks and report results."""
    global CHECKS_TOTAL

    print("=" * 70)
    print("ai-mom Setup Verification Script")
    print("=" * 70)
    print()

    check_directory_structure()
    check_config_files()
    check_script_standard_json()
    check_correction_prompt()
    check_source_modules()
    check_run_py()
    check_env_template()
    check_python_syntax()
    check_stub_functions()

    print()
    print("=" * 70)
    print(f"SUMMARY: {CHECKS_PASSED}/{CHECKS_TOTAL} checks passed")
    print("=" * 70)

    if CHECKS_PASSED == CHECKS_TOTAL:
        print("\nAll checks passed! Project is correctly set up.")
        print("\nContext for Next Steps:")
        print("=" * 70)
        print("""
WHAT THIS TEST COVERS (9 checks):
  1. Directory structure (src/, config/, output/, audio/)
  2. Config file existence (script_standard.json, correction_prompt.txt)
  3. JSON validity and structure (6 nasal groups A-F with correct properties)
  4. Correction prompt template (contains {whisper_output} placeholder)
  5. Source module existence (all phase stubs)
  6. Entry point (run.py)
  7. Environment template (.env.example with OPENAI_API_KEY)
  8. Python syntax validity (py_compile check)
  9. Stub function imports and callability (diarize, summarize, roman_convert, tts)

WHAT THIS TEST DOES NOT COVER (manual steps):
  1. Audio file handling — requires actual audio files
  2. Whisper functionality — requires ffmpeg and openai-whisper package
  3. OpenAI API integration — requires valid OPENAI_API_KEY and internet
  4. Full pipeline execution — requires whisper, openai, and other deps
  5. Speaker diarization (Phase 5) — requires pyannote.audio
  6. GPT summary generation (Phase 6) — requires OpenAI API
  7. Roman transliteration (Phase 7) — requires OpenAI API
  8. TTS synthesis (Phase 8) — requires Coqui TTS

NEXT STEPS:
  1. Install dependencies: pip install -r requirements.txt
  2. Set up .env: cp .env.example .env && edit with your OpenAI API key
  3. Test with a sample audio file:
       python run.py --audio sample.wav --model base
  4. For full pipeline test: python run.py --audio sample.wav --all-phases

NOTES:
  - Phases 5-8 are stubs and will print TODO warnings
  - The script does NOT require any external packages beyond Python stdlib
  - All checks use pathlib, json, py_compile (stdlib only)
        """)
        return 0
    else:
        print("\nSome checks failed. Review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
