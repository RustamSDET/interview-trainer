import os
from pathlib import Path
from dotenv import load_dotenv

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "db.sqlite"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database Connection URI
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Load environment variables from .env
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Audio Configuration
AUDIO_LANGUAGE = os.getenv("AUDIO_LANGUAGE", "en").lower()

# Map language to defaults
DEFAULT_VOICES = {
    "en": "en-US-AndrewNeural",
    "ru": "ru-RU-DmitryNeural"
}

# Resolve actual configurations
TTS_VOICE = os.getenv("TTS_VOICE", DEFAULT_VOICES.get(AUDIO_LANGUAGE, "en-US-AndrewNeural"))
STT_LANGUAGE = os.getenv("STT_LANGUAGE", AUDIO_LANGUAGE if AUDIO_LANGUAGE in ["en", "ru"] else "en")
