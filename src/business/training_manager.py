import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session as DBSession

from src.services.audio.manager import AudioManager
from src.services.audio.tts.edge_tts_engine import EdgeTTS
from src.services.audio.stt.faster_whisper_stt import FasterWhisperSTT
from src.services.ai.analyzer import analyze_single_answer
from src.database.repository import create_answer_history, create_ai_answer_evaluation

class TrainingManager:
    """
    Orchestrator class that decouples the UI from the database sessions,
    audio engines (TTS/STT), and AI evaluation logic.
    """
    def __init__(self, tts_voice: Optional[str] = None, stt_model_size: str = "small"):
        self.tts_engine = EdgeTTS(voice=tts_voice)
        self.stt_engine = FasterWhisperSTT(model_size=stt_model_size)
        self.audio_manager = AudioManager(stt_engine=self.stt_engine, tts_engine=self.tts_engine)

    def get_question_audio(self, question_id: int, question_text: str) -> Path:
        """
        Synthesizes the question text to a cached MP3 file.
        Returns the Path to the synthesized file.
        """
        cache_dir = Path("data/tts_cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        audio_path = cache_dir / f"q_{question_id}.mp3"
        
        if not audio_path.exists():
            # Run the asynchronous speech synthesis in a synchronous context
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            loop.run_until_complete(self.audio_manager.generate_ai_voice(question_text, audio_path))
            
        return audio_path

    def process_and_evaluate_answer(
        self,
        db_session: DBSession,
        session_id: int,
        question_id: int,
        question_text: str,
        expected_answer: str,
        audio_bytes: bytes
    ) -> Dict[str, Any]:
        """
        Main end-to-end training pipeline for voice response processing:
        1. Saves the audio bytes into a temporary WAV file.
        2. Transcribes the audio file to text using FasterWhisper STT.
        3. Invokes the Vertex AI Answer Analyzer to evaluate the answer against the reference answer.
        4. Saves the results to SQLite (AnswerHistory and AIAnswerEvaluation tables).
        5. Returns the structured evaluation details for display.
        """
        # Step 1: Save audio bytes to a temp file
        temp_dir = Path("data/audio")
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_audio_path = temp_dir / f"session_{session_id}_q_{question_id}_temp.wav"
        
        with open(temp_audio_path, "wb") as f:
            f.write(audio_bytes)
            
        # Step 2: Transcribe the audio
        transcribed_text = self.audio_manager.process_user_audio(temp_audio_path)
        if not transcribed_text:
            transcribed_text = "(Тишина или неразборчивая речь)"
            
        # Step 3: AI Answer Evaluation
        eval_result = analyze_single_answer(
            question=question_text,
            expected_answer=expected_answer,
            user_answer=transcribed_text
        )
        
        # Step 4: Save to SQLite
        # 4.1 Save to answer_histories
        db_history_record = create_answer_history(
            db=db_session,
            session_id=session_id,
            question_id=question_id,
            confidence_score=eval_result.score,
            transcribed_text=transcribed_text,
            evaluation_status="Great" if eval_result.score >= 8 else "Good" if eval_result.score >= 5 else "Bad"
        )
        
        # 4.2 Serialize criteria list as JSON for storage
        criteria_list_dict = [c.model_dump() for c in eval_result.criteria]
        criteria_json_str = json.dumps(criteria_list_dict, ensure_ascii=False)
        
        # 4.3 Save to ai_answer_evaluations
        create_ai_answer_evaluation(
            db=db_session,
            answer_history_id=db_history_record.id,
            score=eval_result.score,
            what_was_good=eval_result.what_was_good,
            what_was_bad_or_missing=eval_result.what_was_bad_or_missing,
            verdict=eval_result.verdict,
            summary=eval_result.summary,
            criteria_json=criteria_json_str
        )
        
        # Step 5: Return structured response for UI
        return {
            "transcribed_text": transcribed_text,
            "score": eval_result.score,
            "what_was_good": eval_result.what_was_good,
            "what_was_bad_or_missing": eval_result.what_was_bad_or_missing,
            "verdict": eval_result.verdict,
            "summary": eval_result.summary,
            "criteria": criteria_list_dict,
            "record_id": db_history_record.id
        }
