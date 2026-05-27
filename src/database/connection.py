from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from src.config import DATABASE_URL

# Create database engine
# SQLite requires check_same_thread=False for multi-threaded frameworks like Streamlit
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Enable foreign key support for SQLite (not enabled by default)
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db_session():
    """
    Context manager that provides a database session.
    Automatically commits transactions on success or rolls back on exception.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def init_db():
    """
    Initializes the database, creating all tables if they do not exist.
    """
    from src.database.models import Base
    Base.metadata.create_all(bind=engine)
    
    # Safe database column migration for existing databases
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if "questions" in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('questions')]
        if 'bad_question' not in columns:
            print("🔧 Schema Migration: Adding 'bad_question' column to 'questions' table...")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE questions ADD COLUMN bad_question BOOLEAN DEFAULT 0 NOT NULL"))
            print("✅ Migration completed successfully!")
            
        if 'grade' not in columns:
            print("🔧 Schema Migration: Adding 'grade' column to 'questions' table...")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE questions ADD COLUMN grade VARCHAR(50) DEFAULT 'middle' NOT NULL"))
            print("✅ Migration completed successfully!")
