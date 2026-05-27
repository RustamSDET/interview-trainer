import json
from src.database.connection import init_db, get_db_session
from src.database.models import GlobalTopic, LocalTopic, Question, QuestionType, QuestionGrade, AnswerHistory
from src.database.repository import create_training_session, create_answer_history, create_ai_answer_evaluation
from src.services.ai.analyzer import analyze_single_answer

def main():
    print("Initializing Database...")
    init_db()
    
    with get_db_session() as db:
        # Ensure we have a dummy GlobalTopic, LocalTopic and Question to link against
        topic = db.query(GlobalTopic).first()
        if not topic:
            print("Creating dummy Global Topic...")
            topic = GlobalTopic(name="Testing Basics", description="General QA Concepts")
            db.add(topic)
            db.flush()
            
        local_topic = db.query(LocalTopic).where(LocalTopic.global_topic_id == topic.id).first()
        if not local_topic:
            print("Creating dummy Local Topic...")
            local_topic = LocalTopic(global_topic_id=topic.id, name="Pytest Fixtures", description="Pytest advanced concepts")
            db.add(local_topic)
            db.flush()
            
        question = db.query(Question).where(Question.local_topic_id == local_topic.id).first()
        if not question:
            print("Creating dummy Question...")
            question = Question(
                local_topic_id=local_topic.id,
                question_text="What is the purpose of fixtures in pytest?",
                expected_answer="Fixtures provide a fixed baseline so tests can run reliably. They allow setup/teardown code and dependency injection.",
                question_type=QuestionType.THEORY,
                grade=QuestionGrade.MIDDLE
            )
            db.add(question)
            db.flush()
            
        # 1. Create a dummy training session
        print("Creating dummy Session...")
        session_obj = create_training_session(db, session_mode="Sandbox", total_questions=1)
        
        # 2. Analyze a dummy answer
        user_answer = "Fixtures are just some random variables that you can use to output logs when tests fail. They don't do anything else."
        print(f"Analyzing user answer via AI Answer Analyzer: '{user_answer}'")
        
        evaluation_result = analyze_single_answer(
            question=question.question_text,
            expected_answer=question.expected_answer,
            user_answer=user_answer
        )
        
        # 3. Create AnswerHistory record
        print("Creating AnswerHistory record...")
        ans_history = create_answer_history(
            db=db,
            session_id=session_obj.id,
            question_id=question.id,
            confidence_score=100,
            transcribed_text=user_answer,
            evaluation_status="Bad" if evaluation_result.score < 5 else "Great"
        )
        
        # 4. Serialize criteria evaluations list to JSON
        criteria_list = [crit.model_dump() for crit in evaluation_result.criteria]
        criteria_json = json.dumps(criteria_list, ensure_ascii=False)
        
        # 5. Create AIAnswerEvaluation record
        print("Saving structured AI Evaluation to new database table...")
        ai_eval = create_ai_answer_evaluation(
            db=db,
            answer_history_id=ans_history.id,
            score=evaluation_result.score,
            what_was_good=evaluation_result.what_was_good,
            what_was_bad_or_missing=evaluation_result.what_was_bad_or_missing,
            verdict=evaluation_result.verdict,
            summary=evaluation_result.summary,
            criteria_json=criteria_json
        )
        
        # Flush to confirm insert
        db.flush()
        print(f"Success! AI Evaluation inserted with ID: {ai_eval.id}")
        
        # 6. Retrieve back and verify relationship
        print("\n--- Verifying Database Relationship Mapping ---")
        retrieved_answer = db.get(AnswerHistory, ans_history.id)
        
        assert retrieved_answer is not None
        assert retrieved_answer.evaluation is not None
        
        print(f"Retrieved Answer ID: {retrieved_answer.id}")
        print(f"Linked Evaluation Score: {retrieved_answer.evaluation.score}/10")
        print(f"Summary: {retrieved_answer.evaluation.summary}")
        print(f"What was GOOD: {retrieved_answer.evaluation.what_was_good}")
        print(f"What was BAD: {retrieved_answer.evaluation.what_was_bad_or_missing}")
        print(f"Verdict: {retrieved_answer.evaluation.verdict}")
        
        # Parse JSON
        parsed_criteria = json.loads(retrieved_answer.evaluation.criteria_json)
        print("Criteria Breakdown from DB JSON column:")
        for c in parsed_criteria:
            print(f"  - {c['criterion']}: {c['score']}/10 ({c['explanation']})")

if __name__ == "__main__":
    main()
