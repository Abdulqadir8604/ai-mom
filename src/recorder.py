"""
recorder.py — Record audio from the microphone to a WAV file.

Uses ``sounddevice`` for capture and ``soundfile`` (or ``scipy``) for writing.
"""

import sys
import threading
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ui import print_info, print_warning, print_error


def record_audio(output_path, sample_rate=16000):
    """Record from the default microphone until the user presses Enter.

    Parameters
    ----------
    output_path : str or Path
        Destination WAV file.
    sample_rate : int
        Sample rate in Hz (default 16 000).

    Returns
    -------
    Path
        The path to the saved WAV file.
    """
    try:
        import sounddevice as sd
    except ImportError:
        print_warning(
            "sounddevice not installed. Run: .venv/bin/pip install sounddevice soundfile"
        )
        sys.exit(1)

    # Prefer soundfile; fall back to scipy.io.wavfile
    try:
        import soundfile as sf
        _writer = "soundfile"
    except ImportError:
        try:
            import scipy.io.wavfile as _scipy_wav  # noqa: F401
            _writer = "scipy"
        except ImportError:
            print_warning(
                "Neither soundfile nor scipy is installed. "
                "Run: .venv/bin/pip install soundfile"
            )
            sys.exit(1)

    import numpy as np

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    chunks = []

    def _callback(indata, frames, time_info, status):
        if status:
            print_warning("sounddevice status: %s" % status)
        chunks.append(indata.copy())

    # Start the recording stream in a background thread
    stream = sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        callback=_callback,
    )
    stream.start()

    print_info("Recording... press Enter to stop.")

    # Block until the user presses Enter
    try:
        input()
    except EOFError:
        pass

    stream.stop()
    stream.close()

    if not chunks:
        print_error("No audio captured.")
        sys.exit(1)

    audio_data = np.concatenate(chunks, axis=0)

    # Write WAV
    if _writer == "soundfile":
        import soundfile as sf
        sf.write(str(output_path), audio_data, sample_rate)
    else:
        import scipy.io.wavfile as scipy_wav
        # scipy expects int16
        int_data = (audio_data * 32767).astype(np.int16)
        scipy_wav.write(str(output_path), sample_rate, int_data)

    print_info("Saved recording to %s" % output_path)
    return output_path
