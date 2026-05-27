import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.database.connection import get_db_session
from src.business.training_manager import TrainingManager
from src.database.repository import create_training_session
from sqlalchemy import select
from src.database.models import Question

def test_manager_modes():
    print("Testing TrainingManager with BOTH batch and single modes under realistic loads (5 questions)...")
    manager = TrainingManager(stt_model_size="tiny") # tiny to be fast
    
    with get_db_session() as session:
        # Fetch 5 questions from DB
        q_records = session.scalars(select(Question).limit(5)).all()
        if not q_records:
            print("No questions found in the database. Please seed the database first.")
            return
            
        print(f"Found {len(q_records)} questions in DB. Proceeding with tests...")
        
        # Test Mode 1: batch (chunks of 5 in 1 prompt)
        print("\n=== 1. Testing BATCH Mode (1 prompt per 5 items) ===")
        sess_batch = create_training_session(session, session_mode="Sandbox", total_questions=len(q_records))
        session.flush()
        
        answers_batch = []
        for i, q in enumerate(q_records):
            answers_batch.append({
                "id": q.id,
                "question_text": q.question_text,
                "expected_answer": q.expected_answer,
                "transcribed_text": f"Это мой тестовый ответ на вопрос {i+1} для батч-режима.",
                "is_voice": True
            })
            
        try:
            results = manager.evaluate_transcribed_answers_batch(
                db_session=session,
                session_id=sess_batch.id,
                answers_data=answers_batch,
                analysis_mode="batch"
            )
            print("🎉 Batch Mode Success!")
            print(f"Evaluated {len(results)} answers.")
            for r in results:
                print(f"  Q-ID: {r['id']}, Score: {r['score']}, Summary: {r['summary']}")
        except Exception as e:
            print(f"❌ Batch Mode Failed: {e}")
            import traceback
            traceback.print_exc()
            
        # Test Mode 2: single (1 prompt per 1 item, langchain batch)
        print("\n=== 2. Testing SINGLE Mode (Parallel langchain.batch with max_concurrency=5) ===")
        sess_single = create_training_session(session, session_mode="Sandbox", total_questions=len(q_records))
        session.flush()
        
        answers_single = []
        for i, q in enumerate(q_records):
            answers_single.append({
                "id": q.id,
                "question_text": q.question_text,
                "expected_answer": q.expected_answer,
                "transcribed_text": f"Это мой ответ на вопрос {i+1} для режима поочередного параллельного разбора.",
                "is_voice": True
            })
            
        try:
            results = manager.evaluate_transcribed_answers_batch(
                db_session=session,
                session_id=sess_single.id,
                answers_data=answers_single,
                analysis_mode="single"
            )
            print("🎉 Single Mode (LangChain batch) Success!")
            print(f"Evaluated {len(results)} answers.")
            for r in results:
                print(f"  Q-ID: {r['id']}, Score: {r['score']}, Summary: {r['summary']}")
        except Exception as e:
            print(f"❌ Single Mode Failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_manager_modes()
