from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.database.models import GlobalTopic, LocalTopic, Question, QuestionType

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
    code_snippet: Optional[str] = None
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
        code_snippet=code_snippet
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
