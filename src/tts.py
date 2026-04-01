"""
tts.py — Phase 8: Custom voice TTS synthesis stub.

TODO: Phase 8 — Coqui TTS custom voice synthesis
      Replace this stub with a real implementation that uses
      Coqui TTS (https://github.com/coqui-ai/TTS) with a custom
      voice model trained on LSD speech samples.

The synthesised audio should faithfully reproduce LSD pronunciation
as captured in the Roman transliteration produced by Phase 7.
"""


def synthesize_audio(roman_text, output_path, voice_model=None):
    """Synthesise speech from *roman_text* and write a WAV file.

    Parameters
    ----------
    roman_text : str
        Roman-script transliteration to be spoken (output of Phase 7).
    output_path : str or Path or None
        Destination path for the generated WAV file.
        None is accepted in the stub (no file is written).
    voice_model : str or None
        Path or identifier for the Coqui TTS voice model.
        When None the stub skips model loading entirely.

    Returns
    -------
    str or None
        Absolute path to the generated WAV file, or None if synthesis
        failed or was skipped.  Returns None in this stub implementation.
    """
    # TODO: Phase 8 — Coqui TTS custom voice synthesis
    #   1. Load the Coqui TTS model from voice_model path (or default).
    #   2. Run tts.tts_to_file(text=roman_text, file_path=output_path).
    #   3. Verify the output file was created and is non-empty.
    #   4. Return str(output_path).
    print(
        "WARNING: synthesize_audio() is a stub (Phase 8 not yet implemented). "
        "No audio file was generated."
    )
    return None
