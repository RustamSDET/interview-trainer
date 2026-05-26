from datetime import datetime
import enum
from typing import List, Optional
from sqlalchemy import ForeignKey, String, Text, Integer, DateTime, Enum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class QuestionType(enum.Enum):
    THEORY = "Theory"
    ALGORITHMS = "Algorithms"
    BUG_HUNTING = "BugHunting"
    TEST_ARCH = "TestArch"
    TEST_DESIGN = "TestDesign"
    BEHAVIORAL = "Behavioral"

class GlobalTopic(Base):
    __tablename__ = "global_topics"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    
    # Cascades deletions to local topics
    local_topics: Mapped[List["LocalTopic"]] = relationship(
        back_populates="global_topic", cascade="all, delete-orphan"
    )

class LocalTopic(Base):
    __tablename__ = "local_topics"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    global_topic_id: Mapped[int] = mapped_column(ForeignKey("global_topics.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    allowed_question_types: Mapped[str] = mapped_column(Text, nullable=False, default="Theory")
    
    global_topic: Mapped["GlobalTopic"] = relationship(back_populates="local_topics")
    # Cascades deletions to questions
    questions: Mapped[List["Question"]] = relationship(
        back_populates="local_topic", cascade="all, delete-orphan"
    )

class Question(Base):
    __tablename__ = "questions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    local_topic_id: Mapped[int] = mapped_column(ForeignKey("local_topics.id", ondelete="CASCADE"), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(Enum(QuestionType), nullable=False)
    keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Comma-separated keywords
    code_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bad_question: Mapped[bool] = mapped_column(default=False, nullable=False)
    
    local_topic: Mapped["LocalTopic"] = relationship(back_populates="questions")
    # Cascades deletions to answers
    answers: Mapped[List["AnswerHistory"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )

class Session(Base):
    __tablename__ = "sessions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    session_mode: Mapped[str] = mapped_column(String(50), nullable=False)  # "Interview" or "Sandbox"
    total_questions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Cascades deletions to answers
    answers: Mapped[List["AnswerHistory"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )

class AnswerHistory(Base):
    __tablename__ = "answer_histories"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    audio_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    transcribed_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    evaluation_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "Great", "Good", "Bad"
    ai_feedback_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Detailed JSON payload
    answered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    session: Mapped["Session"] = relationship(back_populates="answers")
    question: Mapped["Question"] = relationship(back_populates="answers")
