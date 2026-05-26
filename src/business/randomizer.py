from typing import List
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from src.database.models import Question

def get_random_questions(db: Session, limit: int) -> List[Question]:
    """
    Selects N random questions from the database that are not marked as bad (bad_question == False).
    Uses SQLite/PostgreSQL random() function to perform the selection on the database side.
    """
    stmt = (
        select(Question)
        .where(Question.bad_question == False)
        .order_by(func.random())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())
