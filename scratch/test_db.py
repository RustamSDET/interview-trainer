import os
import sys
from pathlib import Path

# Automatically add the project root to sys.path so we can import 'src'
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from src import config

# Override with a test-specific database so we don't wipe out the main seeded database
TEST_DB_PATH = config.DATA_DIR / "test_db.sqlite"
config.DB_PATH = TEST_DB_PATH
config.DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

from src.database.connection import init_db, get_db_session
from src.database.models import QuestionType
from src.database.repository import (
    create_global_topic,
    get_all_global_topics,
    delete_global_topic,
    create_local_topic,
    get_local_topics_by_global,
    create_question,
    get_questions_by_local_topic,
    delete_question,
    get_question_by_id,
)

def run_tests():
    print("🚀 Starting Isolated Database and CRUD Verification Tests...")
    
    # 1. Clean up old test DB if it exists so we start fresh
    if config.DB_PATH.exists():
        print(f"🧹 Removing old test database at {config.DB_PATH}")
        config.DB_PATH.unlink()
        
    # 2. Initialize Database Tables
    print("📦 Initializing database and creating tables...")
    init_db()
    assert config.DB_PATH.exists(), "❌ Error: Database file was not created!"
    print("✅ Database file initialized successfully.")
    
    # 3. Test CRUD Operations
    with get_db_session() as session:
        print("\n📝 Inserting Test Data...")
        
        # Create Global Topic
        db_topic = create_global_topic(session, "Базы данных", "Теория баз данных, транзакции, индексы")
        db_topic_id = db_topic.id
        print(f"Created Global Topic: ID={db_topic_id}, Name='{db_topic.name}'")
        assert db_topic_id is not None
        assert db_topic.name == "Базы данных"
        
        # Try creating duplicate (should return existing)
        duplicate_topic = create_global_topic(session, "Базы данных")
        assert duplicate_topic.id == db_topic_id, "❌ Error: Duplicate global topic was created instead of returning existing!"
        
        # Create Local Topic
        local_topic = create_local_topic(
            session, 
            global_topic_id=db_topic_id, 
            name="Изоляция транзакций", 
            description="Уровни изоляции транзакций, проблемы конкурентного доступа",
            allowed_question_types="Theory,BugHunting,TestDesign"
        )
        local_topic_id = local_topic.id
        print(f"Created Local Topic: ID={local_topic_id}, Name='{local_topic.name}', AllowedTypes='{local_topic.allowed_question_types}'")
        assert local_topic_id is not None
        assert local_topic.global_topic_id == db_topic_id
        assert local_topic.allowed_question_types == "Theory,BugHunting,TestDesign"
        
        # Create Question
        question = create_question(
            session,
            local_topic_id=local_topic_id,
            question_text="Что такое уровни изоляции транзакций в СУБД?",
            expected_answer="Уровни изоляции: Read Uncommitted, Read Committed, Repeatable Read, Serializable.",
            question_type=QuestionType.THEORY,
            keywords="ACID, Isolation, Read Committed, Repeatable Read, Serializable, Phantom Read, Dirty Read",
            code_snippet="-- Пример транзакции\nBEGIN TRANSACTION;\nSELECT * FROM accounts;\nCOMMIT;"
        )
        question_id = question.id
        print(f"Created Question: ID={question_id}, Type={question.question_type.value}")
        assert question_id is not None
        assert question.question_type == QuestionType.THEORY
        assert question.local_topic_id == local_topic_id
        
    # 4. Query and Verify Relationships (In a separate session to ensure persistence)
    with get_db_session() as session:
        print("\n🔍 Querying Database to Verify Persistent State...")
        
        # Verify Global Topics
        globals_list = get_all_global_topics(session)
        assert len(globals_list) == 1, f"Expected 1 global topic, found {len(globals_list)}"
        assert globals_list[0].name == "Базы данных"
        
        # Verify Local Topics
        locals_list = get_local_topics_by_global(session, globals_list[0].id)
        assert len(locals_list) == 1, f"Expected 1 local topic, found {len(locals_list)}"
        assert locals_list[0].name == "Изоляция транзакций"
        assert locals_list[0].allowed_question_types == "Theory,BugHunting,TestDesign"
        
        # Verify Questions
        questions_list = get_questions_by_local_topic(session, locals_list[0].id)
        assert len(questions_list) == 1, f"Expected 1 question, found {len(questions_list)}"
        assert questions_list[0].question_text.startswith("Что такое уровни")
        
        print("✅ Query and relationship assertions passed.")
        
    # 5. Test Question Deletion
    with get_db_session() as session:
        print("\n🗑️ Testing Question Deletion...")
        
        # Delete the question
        success = delete_question(session, question_id)
        assert success is True, "❌ Error: Failed to delete question!"
        
        # Verify it is gone
        deleted_q = get_question_by_id(session, question_id)
        assert deleted_q is None, "❌ Error: Question still exists after deletion!"
        
        # Re-create the question for cascade testing
        recreated_q = create_question(
            session,
            local_topic_id=local_topic_id,
            question_text="Что такое уровни изоляции транзакций в СУБД?",
            expected_answer="Уровни изоляции...",
            question_type=QuestionType.THEORY
        )
        recreated_q_id = recreated_q.id
        print(f"Re-created Question (ID={recreated_q_id}) for cascade testing.")
        
    # 6. Test Cascading Deletes (Deleting Global Topic should delete everything under it)
    with get_db_session() as session:
        print("\n💥 Testing Cascading Delete on Global Topic...")
        
        # Delete Global Topic
        success = delete_global_topic(session, db_topic_id)
        assert success is True, "❌ Error: Failed to delete global topic!"
        
    # Verify cascade in a separate session
    with get_db_session() as session:
        # Check global topics
        globals_list = get_all_global_topics(session)
        assert len(globals_list) == 0, f"Expected 0 global topics after cascade, found {len(globals_list)}"
        
        # Check local topics (should be empty because of CASCADE)
        # We try to search by the previous global ID
        locals_list = get_local_topics_by_global(session, db_topic_id)
        assert len(locals_list) == 0, f"Expected 0 local topics, found {len(locals_list)}"
        
        # Check questions
        q = get_question_by_id(session, recreated_q_id)
        assert q is None, "❌ Error: Question was NOT deleted via cascade!"
        
        print("✅ Cascading delete verified perfectly (SQLite PRAGMA foreign_keys=ON is working!).")
        
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY! Database module is 100% correct. 🎉")

if __name__ == "__main__":
    run_tests()
