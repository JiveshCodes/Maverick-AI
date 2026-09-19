"""
app/voice.py
------------
Level 2 Voice Interface engine for Maverick.
Manages Text-to-Speech (TTS) response playback and Speech-to-Text (STT) microphone input.
"""

import sys
import re
import subprocess
from typing import Optional
from app.config import Config

# Safe dynamic import for SpeechRecognition (STT)
try:
    import speech_recognition as sr
    STT_AVAILABLE = True
except ImportError:
    STT_AVAILABLE = False


def _clean_text(text: str) -> str:
    """
    Prepare text for speech synthesis:
    1. Remove entire fenced code blocks (``` ... ```) — ASCII art, code, etc. should NOT be spoken.
    2. Strip remaining Markdown formatting characters from prose text.
    """
    # Remove fenced code blocks (```...```) including optional language tag
    text = re.sub(r"```[\s\S]*?```", "", text)
    # Strip inline code spans
    text = re.sub(r"`[^`]*`", "", text)
    # Strip remaining Markdown formatting
    text = (
        text.replace("**", "")
            .replace("*", "")
            .replace("#", "")
            .replace("- ", "")
    )
    return text.strip()


def _speak_windows(text: str, rate: int) -> None:
    """
    TTS via Windows PowerShell System.Speech — guaranteed to work on Windows.
    Runs as a blocking subprocess so it never hangs the main process thread.
    No pyttsx3 / COM threading issues possible.

    PowerShell Rate scale: -10 (slowest) to 10 (fastest), default 0 (~150 WPM).
    pyttsx3 default rate 180 WPM  maps to PowerShell rate ~2.
    """
    # Map pyttsx3-style WPM rate to PowerShell -10..10 scale
    ps_rate = max(-10, min(10, round((rate - 150) / 15)))

    # Escape single quotes inside text for PowerShell string safety
    safe_text = text.replace("'", "''")

    ps_command = (
        f"Add-Type -AssemblyName System.Speech; "
        f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.Rate = {ps_rate}; "
        f"$s.Speak('{safe_text}')"
    )

    # Try 'powershell' first; fall back to absolute path in case it's not on PATH
    ps_executables = [
        "powershell",
        r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    ]
    for ps_exe in ps_executables:
        try:
            subprocess.run(
                [ps_exe, "-NoProfile", "-NonInteractive", "-Command", ps_command],
                check=False,
                capture_output=True,
            )
            return  # success — stop trying
        except FileNotFoundError:
            continue  # try the next path
        except Exception as e:
            print(f"\n[Voice Output Error] TTS subprocess failed — {type(e).__name__}: {e}")
            return
    print("\n[Voice Output Error] PowerShell not found — cannot speak on this system.")


def _speak_pyttsx3(text: str, rate: int) -> None:
    """
    TTS via pyttsx3 for non-Windows platforms (Linux/macOS).
    Called directly on the main thread where the COM event loop is available.
    """
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', rate)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    except ImportError:
        print("[Voice Output Error] pyttsx3 is not installed. Run: pip install pyttsx3")
    except Exception as e:
        print(f"\n[Voice Output Error] TTS failed — {type(e).__name__}: {e}")


class VoiceEngine:
    """
    VoiceEngine provides audio input (STT) and voice output (TTS) capabilities.
    Fails gracefully if audio libraries or microphone hardware are unavailable.

    On Windows: TTS uses PowerShell System.Speech (no extra packages, no COM hangs).
    On Linux/macOS: TTS uses pyttsx3.
    """

    def __init__(self):
        """Initialize STT recognizer. TTS is stateless (no persistent engine)."""
        self.enabled = Config.is_voice_enabled()
        self.recognizer = None

        # Initialize STT (SpeechRecognition)
        if STT_AVAILABLE:
            try:
                self.recognizer = sr.Recognizer()
                # Auto-adjust energy threshold for background noise
                self.recognizer.dynamic_energy_threshold = True
            except Exception as e:
                print(f"[System Warning] STT initialization failed: {e}")
                self.recognizer = None

    def toggle_mode(self) -> bool:
        """Toggles voice output ON or OFF dynamically and returns the new state."""
        self.enabled = not self.enabled
        return self.enabled

    def speak(self, text: str) -> None:
        """
        Converts text to spoken audio output.
        Does nothing if voice is toggled OFF.

        On Windows: uses PowerShell System.Speech (no COM locking, works every time).
        On other OS: uses pyttsx3.
        """
        if not self.enabled:
            return

        clean = _clean_text(text)
        if not clean:
            return

        print("[🔊 Speaking response...]", end="\r")
        rate = Config.get_voice_rate()

        if sys.platform == "win32":
            _speak_windows(clean, rate)
        else:
            _speak_pyttsx3(clean, rate)

        print(" " * 30, end="\r")

    def listen(self, timeout: int = 5, phrase_time_limit: int = 10) -> Optional[str]:
        """
        Listens to microphone input and converts speech to text.

        Parameters:
            timeout (int): Seconds to wait for speech to start.
            phrase_time_limit (int): Max duration in seconds for spoken phrase.

        Returns:
            Optional[str]: Transcribed user text prompt, or None if failed/timed out.
        """
        if not STT_AVAILABLE or not self.recognizer:
            print("[Voice Input Error] SpeechRecognition library is missing or unavailable.")
            print("Tip: Install dependencies via `pip install SpeechRecognition PyAudio`")
            return None

        try:
            with sr.Microphone() as source:
                print("\n[🎙️ Listening...] Speak into your microphone now...")
                # Adjust for ambient background noise briefly
                self.recognizer.adjust_for_ambient_noise(source, duration=0.8)
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )

                print("[🧠 Processing speech...]", end="\r")
                transcribed_text = self.recognizer.recognize_google(audio)
                print(" " * 30, end="\r")
                return transcribed_text.strip()

        except sr.WaitTimeoutError:
            print("\n[Voice Input] Listening timed out (no speech detected).")
            return None
        except sr.UnknownValueError:
            print("\n[Voice Input] Could not understand the audio. Please try speaking clearer.")
            return None
        except sr.RequestError as req_err:
            print(f"\n[Voice Input Error] Speech Recognition service error: {req_err}")
            return None
        except Exception as err:
            print(f"\n[Voice Input Error] Microphone hardware error or missing PyAudio: {err}")
            return None
