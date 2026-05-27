import edge_tts
from pathlib import Path
from .base import BaseTTS
from src.config import TTS_VOICE

class EdgeTTS(BaseTTS):
    def __init__(self, voice=None):
        self.voice = voice or TTS_VOICE

    async def synthesize(self, text: str, output_path: str | Path) -> str:
        # Create parent directories if they don't exist
        path_obj = Path(output_path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(str(output_path))
        return str(output_path)
