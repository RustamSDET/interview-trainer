import asyncio
from pathlib import Path
from src.services.audio.tts.edge_tts_engine import EdgeTTS
from src.services.audio.manager import AudioManager

async def main():
    print("Testing EdgeTTS Engine...")
    tts = EdgeTTS(voice="ru-RU-DmitryNeural")
    
    # We pass None for stt since we only test TTS here
    manager = AudioManager(stt_engine=None, tts_engine=tts)
    
    output_path = Path("data/audio/test_feedback.mp3")
    test_text = "Привет! Это проверка работы синтезатора речи в новом аудио модуле."
    
    print(f"Synthesizing text: '{test_text}'")
    await manager.generate_ai_voice(test_text, output_path)
    
    if output_path.exists():
        print(f"Success! Audio file saved to {output_path}")
        print(f"File size: {output_path.stat().st_size} bytes")
    else:
        print("Failure: Audio file was not created.")

if __name__ == "__main__":
    asyncio.run(main())
