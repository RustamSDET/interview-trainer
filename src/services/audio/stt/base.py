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
