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
