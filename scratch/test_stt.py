from pathlib import Path
from src.services.audio.stt.faster_whisper_stt import FasterWhisperSTT
from src.services.audio.manager import AudioManager

def main():
    print("Testing FasterWhisperSTT Engine...")
    
    # Use the lightweight "tiny" model to save time and bandwidth
    stt = FasterWhisperSTT(model_size="tiny", device="cpu", compute_type="int8")
    
    # We pass None for tts since we only test STT here
    manager = AudioManager(stt_engine=stt, tts_engine=None)
    
    input_audio_path = Path("data/audio/test_feedback.mp3")
    
    if not input_audio_path.exists():
        print(f"Error: {input_audio_path} does not exist. Please run the TTS test script first to generate it.")
        return
        
    print(f"Transcribing audio file: {input_audio_path}")
    transcribed_text = manager.process_user_audio(input_audio_path)
    
    print("\n--- Transcription Result ---")
    print(transcribed_text)
    print("----------------------------\n")
    
    # Quick sanity check
    if len(transcribed_text) > 0:
        print("Success! Transcription completed.")
    else:
        print("Warning: Transcription is empty.")

if __name__ == "__main__":
    main()
