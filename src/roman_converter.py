"""
roman_converter.py — Phase 7: Roman transliteration stub.

TODO: Phase 7 — GPT Roman transliteration for TTS input
      Replace this stub with a real implementation that converts
      the corrected Urdu-script (LSD) text into Roman-script
      transliteration suitable as input for the TTS engine.

The Roman form must accurately reflect LSD pronunciation rules
(nasal groups A-F as defined in config/script_standard.json).
"""


def convert_to_roman(lsd_text, openai_client):
    """Transliterate LSD Urdu-script text into Roman script.

    Parameters
    ----------
    lsd_text : str
        Corrected Urdu-script transcript text (output of Phase 4/6).
    openai_client : openai.OpenAI or None
        An initialised OpenAI client.  None is accepted in the stub.

    Returns
    -------
    str
        Roman-script transliteration of *lsd_text*.
        Returns an empty string in this stub implementation.
    """
    # TODO: Phase 7 — GPT Roman transliteration for TTS input
    #   1. Build a prompt that instructs GPT to transliterate Urdu-script
    #      LSD text to Roman script, respecting nasal pronunciation rules
    #      from config/script_standard.json.
    #   2. Send to GPT-4o-mini and retrieve the transliterated string.
    #   3. Post-process to normalise spacing and punctuation for TTS.
    #   4. Return the Roman-script string.
    print(
        "WARNING: convert_to_roman() is a stub (Phase 7 not yet implemented). "
        "Returning empty string."
    )
    return ""
