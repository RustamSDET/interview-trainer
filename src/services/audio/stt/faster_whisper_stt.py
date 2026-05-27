from pathlib import Path
from .base import BaseSTT
from src.config import STT_LANGUAGE

class FasterWhisperSTT(BaseSTT):
    def __init__(self, model_size="small", device="cpu", compute_type="int8", language=None):
        self.language = language or STT_LANGUAGE
        # Load model once into memory upon initialization
        # Note: We import WhisperModel here or inside init so that it is only required
        # when FasterWhisperSTT is actually instantiated.
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        except ImportError:
            self.model = None
            print("Warning: faster-whisper is not installed. FasterWhisperSTT will not work.")

    def transcribe(self, audio_path: str | Path) -> str:
        if self.model is None:
            raise ImportError("faster-whisper is not installed or failed to load. Please install faster-whisper.")
        
        segments, _ = self.model.transcribe(str(audio_path), beam_size=5, language=self.language)
        return " ".join([segment.text for segment in segments]).strip()
