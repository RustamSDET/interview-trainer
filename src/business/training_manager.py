import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
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

    def transcribe_audio(
        self,
        session_id: int,
        question_id: int,
        audio_bytes: bytes
    ) -> str:
        """
        Saves the user's recorded audio bytes to a WAV file and transcribes it using FasterWhisper.
        This is fast and does not use LLM.
        """
        temp_dir = Path("data/audio")
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_audio_path = temp_dir / f"session_{session_id}_q_{question_id}_temp.wav"
        
        with open(temp_audio_path, "wb") as f:
            f.write(audio_bytes)
            
        transcribed_text = self.audio_manager.process_user_audio(temp_audio_path)
        if not transcribed_text:
            transcribed_text = "(Тишина или неразборчивая речь)"
            
        return transcribed_text

    def evaluate_transcribed_answers_batch(
        self,
        db_session: DBSession,
        session_id: int,
        answers_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Evaluates a list of transcribed answers using Vertex AI batch analysis (max 5 per batch).
        Saves all results to SQLite (AnswerHistory and AIAnswerEvaluation) and returns the list
        of structured evaluation details.
        
        answers_data is a list of dicts:
        [
            {
                "question_id": int,
                "question_text": str,
                "expected_answer": str,
                "transcribed_text": str
            },
            ...
        ]
        """
        if not answers_data:
            return []
            
        from src.services.ai.analyzer import analyze_answers_batch
        from sqlalchemy import select
        from src.database.models import AnswerHistory, AIAnswerEvaluation
        
        # Split answers into chunks of max 5 items
        chunk_size = 5
        chunks = [answers_data[i:i + chunk_size] for i in range(0, len(answers_data), chunk_size)]
        
        evaluated_results = []
        
        for chunk in chunks:
            # Prepare items for the AI analyzer
            items = [
                {
                    "question": item["question_text"],
                    "expected_answer": item["expected_answer"],
                    "user_answer": item["transcribed_text"]
                }
                for item in chunk
            ]
            
            # Call the batch AI analyzer
            batch_eval = analyze_answers_batch(items)
            
            # Process the evaluations and match back by index
            for idx, item in enumerate(chunk):
                # Find matching evaluation by index
                eval_item = None
                for ev in batch_eval.evaluations:
                    if ev.index == idx:
                        eval_item = ev
                        break
                
                if not eval_item:
                    # Fallback if indices are mismatching (should not happen)
                    eval_item = batch_eval.evaluations[idx] if idx < len(batch_eval.evaluations) else batch_eval.evaluations[0]
                
                # Save to DB
                q_id = item.get("question_id") or item.get("id")
                
                stmt = select(AnswerHistory).where(
                    AnswerHistory.session_id == session_id,
                    AnswerHistory.question_id == q_id
                )
                db_history_record = db_session.scalar(stmt)
                
                if db_history_record:
                    db_history_record.transcribed_text = item["transcribed_text"]
                    db_history_record.confidence_score = eval_item.score
                    db_history_record.evaluation_status = "Great" if eval_item.score >= 8 else "Good" if eval_item.score >= 5 else "Bad"
                else:
                    db_history_record = create_answer_history(
                        db=db_session,
                        session_id=session_id,
                        question_id=q_id,
                        confidence_score=eval_item.score,
                        transcribed_text=item["transcribed_text"],
                        evaluation_status="Great" if eval_item.score >= 8 else "Good" if eval_item.score >= 5 else "Bad"
                    )
                
                # Serialize criteria
                criteria_list_dict = [c.model_dump() for c in eval_item.criteria]
                criteria_json_str = json.dumps(criteria_list_dict, ensure_ascii=False)
                
                # Clear existing evaluations
                stmt_eval = select(AIAnswerEvaluation).where(AIAnswerEvaluation.answer_history_id == db_history_record.id)
                existing_eval = db_session.scalar(stmt_eval)
                if existing_eval:
                    db_session.delete(existing_eval)
                    db_session.flush()
                
                create_ai_answer_evaluation(
                    db=db_session,
                    answer_history_id=db_history_record.id,
                    score=eval_item.score,
                    what_was_good=eval_item.what_was_good,
                    what_was_bad_or_missing=eval_item.what_was_bad_or_missing,
                    verdict=eval_item.verdict,
                    summary=eval_item.summary,
                    criteria_json=criteria_json_str
                )
                
                evaluated_results.append({
                    "id": q_id,
                    "question_text": item["question_text"],
                    "transcribed_text": item["transcribed_text"],
                    "score": eval_item.score,
                    "what_was_good": eval_item.what_was_good,
                    "what_was_bad_or_missing": eval_item.what_was_bad_or_missing,
                    "verdict": eval_item.verdict,
                    "summary": eval_item.summary,
                    "criteria": criteria_list_dict,
                    "record_id": db_history_record.id
                })
                
        return evaluated_results

    def evaluate_transcribed_answer(
        self,
        db_session: DBSession,
        session_id: int,
        question_id: int,
        question_text: str,
        expected_answer: str,
        transcribed_text: str
    ) -> Dict[str, Any]:
        """
        Evaluates an already transcribed user answer against the reference answer.
        Saves the results to SQLite (AnswerHistory and AIAnswerEvaluation tables).
        Returns the structured evaluation details for display.
        """
        # Step 1: AI Answer Evaluation
        eval_result = analyze_single_answer(
            question=question_text,
            expected_answer=expected_answer,
            user_answer=transcribed_text
        )
        
        # Step 2: Save to SQLite (create or update AnswerHistory)
        from sqlalchemy import select
        from src.database.models import AnswerHistory
        stmt = select(AnswerHistory).where(
            AnswerHistory.session_id == session_id,
            AnswerHistory.question_id == question_id
        )
        db_history_record = db_session.scalar(stmt)
        
        if db_history_record:
            # Update existing record
            db_history_record.transcribed_text = transcribed_text
            db_history_record.confidence_score = eval_result.score
            db_history_record.evaluation_status = "Great" if eval_result.score >= 8 else "Good" if eval_result.score >= 5 else "Bad"
        else:
            # Create a new record
            db_history_record = create_answer_history(
                db=db_session,
                session_id=session_id,
                question_id=question_id,
                confidence_score=eval_result.score,
                transcribed_text=transcribed_text,
                evaluation_status="Great" if eval_result.score >= 8 else "Good" if eval_result.score >= 5 else "Bad"
            )
            
        # Serialize criteria list as JSON for storage
        criteria_list_dict = [c.model_dump() for c in eval_result.criteria]
        criteria_json_str = json.dumps(criteria_list_dict, ensure_ascii=False)
        
        # Save to ai_answer_evaluations
        from src.database.models import AIAnswerEvaluation
        stmt_eval = select(AIAnswerEvaluation).where(AIAnswerEvaluation.answer_history_id == db_history_record.id)
        existing_eval = db_session.scalar(stmt_eval)
        if existing_eval:
            db_session.delete(existing_eval)
            db_session.flush()
            
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
        
        # Return structured response for UI
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

