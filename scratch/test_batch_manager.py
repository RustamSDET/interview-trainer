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

def test_manager_batch():
    print("Testing TrainingManager batch evaluation for MULTIPLE questions with DB...")
    manager = TrainingManager(stt_model_size="tiny") # tiny to be fast
    
    with get_db_session() as session:
        # Find multiple existing questions to satisfy foreign key constraints
        q_records = session.scalars(select(Question).limit(3)).all()
        if not q_records:
            print("No questions found in the database. Please seed the database first.")
            return
            
        print(f"Found {len(q_records)} questions in DB. Using them for batch evaluation test.")
        
        # Create a mock training session
        training_sess = create_training_session(session, session_mode="Sandbox", total_questions=len(q_records))
        session.flush()
        
        # Prepare multiple inputs with "id" matching our real questions
        voice_answers = []
        for i, q in enumerate(q_records):
            voice_answers.append({
                "id": q.id,
                "question_text": q.question_text,
                "expected_answer": q.expected_answer,
                "transcribed_text": f"Это мой тестовый устный ответ на вопрос номер {i+1}.",
                "is_voice": True
            })
        
        try:
            print(f"Invoking evaluate_transcribed_answers_batch with {len(voice_answers)} items...")
            results = manager.evaluate_transcribed_answers_batch(
                db_session=session,
                session_id=training_sess.id,
                answers_data=voice_answers
            )
            print("\n🎉 Manager Batch SUCCESS!")
            print(f"Evaluated results count: {len(results)}")
            for idx, res in enumerate(results):
                print(f"--- Question {idx+1} (ID: {res['id']}) ---")
                print(f"Score: {res['score']} / 10")
                print(f"Summary: {res['summary']}")
                print(f"Verdict: {res['verdict']}")
        except Exception as e:
            print(f"Manager Batch FAILED with exception: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_manager_batch()
