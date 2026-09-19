"""
app/config.py
--------------
Responsible for loading environment variables, system instructions, 
and application settings. Keeps sensitive secrets outside source code.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Find project root directory (one level up from app/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file into os.environ
ENV_FILE = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_FILE)

# Level 3: Storage Directory for SQLite database & memory persistence
DATA_DIR = BASE_DIR / "data"

# System Prompt defines the AI's persona, identity, and behavior limits.
DEFAULT_SYSTEM_PROMPT = (
    "You are Maverick, an autonomous personal AI assistant equipped with Voice (STT/TTS), "
    "Persistent Long-Term Memory, Real-Time Web Research Tools, and Local Desktop/OS Control "
    "(File Management, Terminal Commands, App Launcher, Desktop Screenshots, System Metrics). "
    "You are helpful, concise, smart, and friendly. "
    "Answer questions accurately and directly. "
    "When producing visual output (ASCII art, diagrams, code, tables), output it immediately "
    "without any introductory preamble like 'Here is ...' or 'Sure, here you go:'. "
    "Also skip unnecessary closing remarks like 'Hope you like it!' or "
    "'Let me know if you need anything else.' — only add follow-up if it is genuinely useful."
)


class Config:
    """Central configuration class for Maverick."""

    @classmethod
    def reload(cls) -> None:
        """Reload .env variables directly from disk."""
        load_dotenv(dotenv_path=ENV_FILE, override=True)

    @classmethod
    def get_api_key(cls) -> str:
        """Returns the GEMINI_API_KEY from environment variables."""
        cls.reload()
        return os.getenv("GEMINI_API_KEY", "").strip()

    @classmethod
    def get_model_name(cls) -> str:
        """Returns the configured model name or default."""
        cls.reload()
        return os.getenv("MODEL_NAME", "gemini-3.6-flash").strip()

    @classmethod
    def get_groq_api_key(cls) -> str:
        """Returns the GROQ_API_KEY from environment variables."""
        cls.reload()
        return os.getenv("GROQ_API_KEY", "").strip()

    @classmethod
    def get_groq_model_name(cls) -> str:
        """Returns the GROQ_MODEL_NAME from environment variables."""
        cls.reload()
        return os.getenv("GROQ_MODEL_NAME", "auto").strip()

    @classmethod
    def get_system_prompt(cls) -> str:
        """Returns the configured system prompt or default."""
        cls.reload()
        return os.getenv("SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT).strip()

    @classmethod
    def is_voice_enabled(cls) -> bool:
        """Returns whether voice mode is enabled by default from env."""
        cls.reload()
        return os.getenv("ENABLE_VOICE", "false").strip().lower() in ["true", "1", "yes"]

    @classmethod
    def is_tools_enabled(cls) -> bool:
        """Returns whether external tools are enabled from env."""
        cls.reload()
        return os.getenv("ENABLE_TOOLS", "true").strip().lower() in ["true", "1", "yes"]

    @classmethod
    def get_voice_rate(cls) -> int:
        """Returns speech rate WPM (words per minute). Default 180."""
        cls.reload()
        try:
            return int(os.getenv("VOICE_SPEED", "180"))
        except ValueError:
            return 180

    @classmethod
    def get_data_dir(cls) -> Path:
        """Returns the Path object for the local data storage directory."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return DATA_DIR

    @classmethod
    def get_memory_db_path(cls) -> Path:
        """Returns the Path to the SQLite memory database file."""
        return cls.get_data_dir() / "memory.db"

    @classmethod
    def validate(cls) -> None:
        """
        Verify that required credentials are present.
        Raises ValueError with a helpful message if GEMINI_API_KEY is missing.
        """
        api_key = cls.get_api_key()
        if not api_key:
            raise ValueError(
                "\n[CONFIG ERROR] GEMINI_API_KEY is missing!\n"
                "Please add your API key to the '.env' file in the project root.\n"
                "Example in .env:\n"
                "  GEMINI_API_KEY=AIzaSyYourActualKeyHere\n"
                "Get a free API key at: https://aistudio.google.com/\n"
            )
