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
