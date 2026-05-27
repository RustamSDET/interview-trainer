from datetime import datetime
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.database.models import GlobalTopic, LocalTopic, Question, QuestionType, QuestionGrade, Session as DBSession, AnswerHistory, AIAnswerEvaluation

# --- Global Topic CRUD ---

def create_global_topic(db: Session, name: str, description: Optional[str] = None, priority: int = 5) -> GlobalTopic:
    """
    Creates a new GlobalTopic or returns an existing one if the name already matches.
    If the name matches, its priority will be updated to the new value.
    """
    stmt = select(GlobalTopic).where(GlobalTopic.name == name)
    existing = db.scalar(stmt)
    if existing:
        if existing.priority != priority:
            existing.priority = priority
            db.flush()
        return existing
    
    topic = GlobalTopic(name=name, description=description, priority=priority)
    db.add(topic)
    db.flush()  # Populates the id attribute on the object
    return topic

def get_all_global_topics(db: Session) -> List[GlobalTopic]:
    """
    Retrieves all global topics sorted alphabetically by name.
    """
    stmt = select(GlobalTopic).order_by(GlobalTopic.name)
    return list(db.scalars(stmt).all())

def get_global_topic_by_id(db: Session, topic_id: int) -> Optional[GlobalTopic]:
    """
    Retrieves a single global topic by its ID.
    """
    return db.get(GlobalTopic, topic_id)

def delete_global_topic(db: Session, topic_id: int) -> bool:
    """
    Deletes a global topic by ID. 
    Cascades deletion to child local topics, questions, and answers automatically.
    """
    topic = db.get(GlobalTopic, topic_id)
    if topic:
        db.delete(topic)
        db.flush()
        return True
    return False


# --- Local Topic CRUD ---

def create_local_topic(
    db: Session,
    global_topic_id: int,
    name: str,
    description: Optional[str] = None,
    priority: int = 5,
    allowed_question_types: str = "Theory"
) -> LocalTopic:
    """
    Creates a new LocalTopic under a specified GlobalTopic.
    """
    # Validation: Verify global topic exists
    if not db.get(GlobalTopic, global_topic_id):
        raise ValueError(f"GlobalTopic with ID {global_topic_id} does not exist.")
        
    topic = LocalTopic(
        global_topic_id=global_topic_id,
        name=name,
        description=description,
        priority=priority,
        allowed_question_types=allowed_question_types
    )
    db.add(topic)
    db.flush()
    return topic

def get_local_topics_by_global(db: Session, global_topic_id: int) -> List[LocalTopic]:
    """
    Retrieves all local topics belonging to a specific GlobalTopic, sorted by name.
    """
    stmt = select(LocalTopic).where(LocalTopic.global_topic_id == global_topic_id).order_by(LocalTopic.name)
    return list(db.scalars(stmt).all())

def get_local_topic_by_id(db: Session, topic_id: int) -> Optional[LocalTopic]:
    """
    Retrieves a single local topic by ID.
    """
    return db.get(LocalTopic, topic_id)

def delete_local_topic(db: Session, topic_id: int) -> bool:
    """
    Deletes a local topic by ID.
    Cascades deletion to child questions and answers automatically.
    """
    topic = db.get(LocalTopic, topic_id)
    if topic:
        db.delete(topic)
        db.flush()
        return True
    return False


# --- Question CRUD ---

def create_question(
    db: Session,
    local_topic_id: int,
    question_text: str,
    expected_answer: str,
    question_type: QuestionType,
    keywords: Optional[str] = None,
    code_snippet: Optional[str] = None,
    grade: QuestionGrade = QuestionGrade.MIDDLE
) -> Question:
    """
    Creates a new Question inside a specific LocalTopic.
    """
    # Validation: Verify local topic exists
    if not db.get(LocalTopic, local_topic_id):
        raise ValueError(f"LocalTopic with ID {local_topic_id} does not exist.")
        
    question = Question(
        local_topic_id=local_topic_id,
        question_text=question_text,
        expected_answer=expected_answer,
        question_type=question_type,
        keywords=keywords,
        code_snippet=code_snippet,
        grade=grade
    )
    db.add(question)
    db.flush()
    return question

def get_question_by_id(db: Session, question_id: int) -> Optional[Question]:
    """
    Retrieves a single question by ID.
    """
    return db.get(Question, question_id)

def get_questions_by_local_topic(db: Session, local_topic_id: int) -> List[Question]:
    """
    Retrieves all questions belonging to a specific LocalTopic.
    """
    stmt = select(Question).where(Question.local_topic_id == local_topic_id).order_by(Question.id)
    return list(db.scalars(stmt).all())

def delete_question(db: Session, question_id: int) -> bool:
    """
    Deletes a question by ID.
    Cascades deletion to associated answers automatically.
    """
    question = db.get(Question, question_id)
    if question:
        db.delete(question)
        db.flush()
        return True
    return False

def set_question_bad_status(db: Session, question_id: int, is_bad: bool = True) -> bool:
    """
    Sets the bad_question status of a question.
    """
    question = db.get(Question, question_id)
    if question:
        question.bad_question = is_bad
        db.flush()
        return True
    return False

def mark_question_as_bad(db: Session, question_id: int) -> bool:
    """
    Marks a question as bad (bad_question = True).
    """
    return set_question_bad_status(db, question_id, is_bad=True)


# --- Training Session & Answer History CRUD ---

def create_training_session(db: Session, session_mode: str, total_questions: int) -> DBSession:
    """
    Creates and records a new training session (e.g. 'Sandbox' or 'Interview').
    """
    session_obj = DBSession(
        session_mode=session_mode,
        total_questions=total_questions,
        started_at=datetime.utcnow()
    )
    db.add(session_obj)
    db.flush()
    return session_obj

def finish_training_session(db: Session, session_id: int) -> bool:
    """
    Marks a training session as completed by setting finished_at.
    """
    session_obj = db.get(DBSession, session_id)
    if session_obj:
        session_obj.finished_at = datetime.utcnow()
        db.flush()
        return True
    return False

def create_answer_history(
    db: Session,
    session_id: int,
    question_id: int,
    confidence_score: int,
    transcribed_text: Optional[str] = None,
    evaluation_status: Optional[str] = None
) -> AnswerHistory:
    """
    Saves an answer record under a given session.
    """
    answer_obj = AnswerHistory(
        session_id=session_id,
        question_id=question_id,
        confidence_score=confidence_score,
        transcribed_text=transcribed_text,
        evaluation_status=evaluation_status,
        answered_at=datetime.utcnow()
    )
    db.add(answer_obj)
    db.flush()
    return answer_obj

def create_ai_answer_evaluation(
    db: Session,
    answer_history_id: int,
    score: int,
    what_was_good: str,
    what_was_bad_or_missing: str,
    verdict: str,
    summary: str,
    criteria_json: str
) -> AIAnswerEvaluation:
    """
    Saves an AI evaluation report for a specific answer history entry.
    """
    eval_obj = AIAnswerEvaluation(
        answer_history_id=answer_history_id,
        score=score,
        what_was_good=what_was_good,
        what_was_bad_or_missing=what_was_bad_or_missing,
        verdict=verdict,
        summary=summary,
        criteria_json=criteria_json,
        created_at=datetime.utcnow()
    )
    db.add(eval_obj)
    db.flush()
    return eval_obj
