Excellent choice. Focusing on the MVP with st.audio_input, faster-whisper, and edge-tts is the fastest way to get a working, high-quality prototype while keeping costs at zero.

To ensure you can easily swap out faster-whisper for Google Cloud STT, or edge-tts for ElevenLabs/Google Cloud TTS later without breaking the app, we need to design this using the Strategy Pattern and Dependency Inversion Principle (SOLID).

Here is the architectural plan and folder structure.

1. Folder & File Structure
We will isolate the audio logic inside src/services/audio/. By separating stt (Speech-to-Text) and tts (Text-to-Speech) into their own sub-packages, you maintain the "Modular Monolith" philosophy outlined in your README.md.

Plaintext
interview-trainer/
├── data/
│   └── audio/               # Temporary storage for .wav/.mp3 files during session
├── src/
│   ├── web/
│   │   └── app.py           # UI layer (uses st.audio_input)
│   ├── services/
│   │   ├── ai/              # Existing Vertex AI logic
│   │   └── audio/           # ⬅️ NEW AUDIO MODULE
│   │       ├── __init__.py
│   │       ├── manager.py   # High-level Facade for the UI to interact with
│   │       ├── stt/
│   │       │   ├── __init__.py
│   │       │   ├── base.py                 # Abstract Base Class for Transcribers
│   │       │   ├── faster_whisper_stt.py   # MVP Implementation
│   │       │   └── gcp_stt.py              # (Future) Google Cloud implementation
│   │       └── tts/
│   │           ├── __init__.py
│   │           ├── base.py                 # Abstract Base Class for Synthesizers
│   │           ├── edge_tts_engine.py      # MVP Implementation
│   │           └── gcp_tts.py              # (Future) Google Cloud implementation
2. Architecture Document: Pluggable Audio Module
Goal: The UI (app.py) and the business logic (State Machine) should never know how audio is transcribed or synthesized. They should only know that they give audio and get text, or give text and get audio.

A. The Interfaces (Contracts)
In Python, we use the abc (Abstract Base Classes) module to enforce contracts. Any transcriber or synthesizer you write must implement these specific methods.

src/services/audio/stt/base.py

Python
from abc import ABC, abstractmethod
from pathlib import Path

class BaseSTT(ABC):
    """
    Abstract interface for all Speech-to-Text engines.
    """
    @abstractmethod
    def transcribe(self, audio_path: str | Path) -> str:
        """
        Takes a path to an audio file and returns the transcribed text.
        """
        pass
src/services/audio/tts/base.py

Python
from abc import ABC, abstractmethod
from pathlib import Path

class BaseTTS(ABC):
    """
    Abstract interface for all Text-to-Speech engines.
    """
    @abstractmethod
    async def synthesize(self, text: str, output_path: str | Path) -> str:
        """
        Takes text, converts it to speech, saves to output_path, and returns the path.
        """
        pass
B. The MVP Implementations
Now, we create concrete classes that inherit from these base classes. If you ever want to change providers, you just write a new class; you don't touch the UI or existing logic.

src/services/audio/stt/faster_whisper_stt.py

Python
from faster_whisper import WhisperModel
from pathlib import Path
from .base import BaseSTT

class FasterWhisperSTT(BaseSTT):
    def __init__(self, model_size="small", device="cpu", compute_type="int8"):
        # Load model once into memory upon initialization
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe(self, audio_path: str | Path) -> str:
        # Business logic for faster-whisper
        segments, _ = self.model.transcribe(str(audio_path), beam_size=5)
        return " ".join([segment.text for segment in segments]).strip()
src/services/audio/tts/edge_tts_engine.py

Python
import edge_tts
from pathlib import Path
from .base import BaseTTS

class EdgeTTS(BaseTTS):
    def __init__(self, voice="ru-RU-DmitryNeural"):
        self.voice = voice

    async def synthesize(self, text: str, output_path: str | Path) -> str:
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(str(output_path))
        return str(output_path)
C. The Manager (Facade Pattern)
This is the single entry point for your Streamlit app. By injecting the dependencies (the specific STT/TTS classes) into the manager, you can switch engines using a .env variable or a configuration file.

src/services/audio/manager.py

Python
from pathlib import Path
from .stt.base import BaseSTT
from .tts.base import BaseTTS

class AudioManager:
    """
    Facade handling all media operations. 
    It receives the configured STT and TTS engines via Dependency Injection.
    """
    def __init__(self, stt_engine: BaseSTT, tts_engine: BaseTTS):
        self.stt = stt_engine
        self.tts = tts_engine

    def process_user_audio(self, audio_path: str | Path) -> str:
        """Takes user voice, returns text."""
        return self.stt.transcribe(audio_path)

    async def generate_ai_voice(self, text: str, output_path: str | Path) -> str:
        """Takes AI text, saves audio file, returns path."""
        return await self.tts.synthesize(text, output_path)
3. How it looks in your UI (app.py)
Because of this architecture, your UI code remains incredibly clean and is entirely decoupled from faster-whisper or edge-tts.

Python
import streamlit as st
import asyncio
from src.services.audio.manager import AudioManager
from src.services.audio.stt.faster_whisper_stt import FasterWhisperSTT
from src.services.audio.tts.edge_tts_engine import EdgeTTS

# 1. Initialize once and cache it so the ML model isn't reloaded on every button click
@st.cache_resource
def get_audio_manager():
    # Here is where you "plug in" your MVP engines. 
    # To switch to GCP later, just change these two lines!
    stt = FasterWhisperSTT(model_size="small")
    tts = EdgeTTS(voice="ru-RU-DmitryNeural")
    return AudioManager(stt_engine=stt, tts_engine=tts)

audio_manager = get_audio_manager()

# 2. UI Implementation
st.markdown("### 🎙️ Simulator")

# Streamlit 1.50 Native Audio Input
user_audio = st.audio_input("Record your answer")

if user_audio is not None:
    # Save the bytes to a temp file
    temp_audio_path = "data/audio/temp_input.wav"
    with open(temp_audio_path, "wb") as f:
        f.write(user_audio.getbuffer())
    
    with st.spinner("Transcribing..."):
        # The UI doesn't know we are using faster-whisper. It just calls the manager.
        transcribed_text = audio_manager.process_user_audio(temp_audio_path)
        st.success(f"Recognized: {transcribed_text}")
        
        # --- (Send transcribed_text to Vertex AI here) ---

        # Generate voice for the AI's feedback
        feedback_text = "Отличный ответ! Вы правильно упомянули фикстуры."
        feedback_audio_path = "data/audio/temp_output.mp3"
        
        asyncio.run(audio_manager.generate_ai_voice(feedback_text, feedback_audio_path))
        
        st.audio(feedback_audio_path)