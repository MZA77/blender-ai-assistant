"""Voice-to-text input.

Captures a short phrase from the microphone and transcribes it, so the user can
speak a command instead of typing. Uses the `SpeechRecognition` library with the
free Google Web Speech backend (no API key needed).

Dependencies (install into Blender's bundled Python):
    <blender>/python/bin/python -m pip install SpeechRecognition pyaudio

Privacy note: the Google backend uploads the recorded audio to Google's servers
for transcription.
"""


def _err(message):
    return {"ok": False, "text": "", "error": message}


def transcribe(timeout=6, phrase_time_limit=12):
    """Record a phrase from the default mic and return a result dict.

    Returns: {ok (bool), text (str), error (str | None)}.
    This call BLOCKS while listening, so Blender's UI will freeze briefly.
    """
    try:
        import speech_recognition as sr
    except ImportError:
        return _err(
            "The 'SpeechRecognition' package isn't installed in Blender's Python. "
            "Install it with: <blender>/python/bin/python -m pip install "
            "SpeechRecognition pyaudio"
        )

    recognizer = sr.Recognizer()

    try:
        microphone = sr.Microphone()
    except (OSError, AttributeError) as exc:
        # AttributeError: PyAudio missing; OSError: no input device.
        return _err(
            "No microphone available (or PyAudio isn't installed). Install it "
            "with: <blender>/python/bin/python -m pip install pyaudio  "
            f"[{exc}]"
        )

    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio = recognizer.listen(
                source, timeout=timeout, phrase_time_limit=phrase_time_limit
            )
    except sr.WaitTimeoutError:
        return _err("Didn't hear anything — try again.")
    except Exception as exc:  # device errors, etc.
        return _err(f"Recording failed: {exc}")

    try:
        text = recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return _err("Couldn't understand the audio — try again.")
    except sr.RequestError as exc:
        return _err(f"Speech service error: {exc}")

    return {"ok": True, "text": text, "error": None}
