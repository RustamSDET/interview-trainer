import os
import sys
from pathlib import Path

# Automatically add the project root to sys.path so we can import 'src'
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# Override the database path to use a test-specific database so we don't affect main seeded database
from src import config
TEST_DB_PATH = config.DATA_DIR / "test_ai_db.sqlite"
config.DB_PATH = TEST_DB_PATH
config.DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

from src.database.connection import init_db, get_db_session
from src.database.models import QuestionType
from src.database.repository import create_global_topic, create_local_topic, get_questions_by_local_topic
from src.services.ai.generator import generate_questions_for_topic_and_type

def run_ai_generator_test():
    print("🚀 Starting AI Question Generator Targeted Verification Test...")
    
    # 1. Clean up old test database if it exists
    if config.DB_PATH.exists():
        print(f"🧹 Removing old test database at {config.DB_PATH}")
        config.DB_PATH.unlink()
        
    # 2. Initialize database
    print("📦 Initializing test database tables...")
    init_db()
    
    # 3. Seed a single Global & Local Topic to generate questions for
    with get_db_session() as session:
        print("🌱 Seeding a test topic 'Advanced Python' with allowed types 'Theory,BugHunting'...")
        g_topic = create_global_topic(
            session, 
            name="Python Core & Computer Science", 
            description="Базовый фундамент языка, на котором пишется весь фреймворк и проходяться секции кодинга.",
            priority=9
        )
        l_topic = create_local_topic(
            session,
            global_topic_id=g_topic.id,
            name="Advanced Python",
            description="Декораторы, генераторы, итераторы, контекстные менеджеры — это фундамент для понимания Pytest под капотом",
            priority=10,
            allowed_question_types="Theory,BugHunting"
        )
        l_topic_id = l_topic.id
        print(f"Test Local Topic created: ID={l_topic_id}, Name='{l_topic.name}'")
        
    # 4. Trigger Targeted Live AI Question Generation (Theory and BugHunting in batch!)
    print(f"\n🔮 Triggering targeted live AI generation via Vertex AI batch for Theory and BugHunting...")
    try:
        from src.services.ai.generator import generate_questions_batch
        with get_db_session() as session:
            targets = [
                (l_topic_id, QuestionType.THEORY),
                (l_topic_id, QuestionType.BUG_HUNTING)
            ]
            count = generate_questions_batch(
                db=session,
                targets=targets,
                overwrite=True
            )
            print(f"✅ Success! Generated and stored {count} questions in the database.")
            assert count == 12, f"Expected 12 questions, but got {count}"
            
        # 5. Query and Print the Generated Questions
        with get_db_session() as session:
            print("\n📥 Retrieving generated questions from the database:")
            questions = get_questions_by_local_topic(session, l_topic_id)
            
            # Verify that Theory questions have no code snippets
            theory_questions = [q for q in questions if q.question_type == QuestionType.THEORY]
            bug_hunting_questions = [q for q in questions if q.question_type == QuestionType.BUG_HUNTING]
            
            assert len(theory_questions) == 6, f"Expected 6 Theory questions, got {len(theory_questions)}"
            assert len(bug_hunting_questions) == 6, f"Expected 6 BugHunting questions, got {len(bug_hunting_questions)}"
            
            for q in theory_questions:
                assert not q.code_snippet, f"Theory question ID {q.id} has code snippet: '{q.code_snippet}'"
                
            print("🚀 Verified: All Theory questions have absolutely NO code snippets.")
            
            # Verify grade distribution for each type (3 junior, 2 middle, 1 senior)
            for q_type, q_list in [("Theory", theory_questions), ("BugHunting", bug_hunting_questions)]:
                juniors = [q for q in q_list if q.grade.value == "junior"]
                middles = [q for q in q_list if q.grade.value == "middle"]
                seniors = [q for q in q_list if q.grade.value == "senior"]
                print(f"Verified {q_type} Grade Distribution: {len(juniors)} Junior, {len(middles)} Middle, {len(seniors)} Senior.")
                assert len(juniors) == 3, f"Expected 3 Junior questions for {q_type}, got {len(juniors)}"
                assert len(middles) == 2, f"Expected 2 Middle questions for {q_type}, got {len(middles)}"
                assert len(seniors) == 1, f"Expected 1 Senior question for {q_type}, got {len(seniors)}"
            
            for i, q in enumerate(questions, 1):
                print("\n" + "=" * 80)
                print(f"❓ Question {i} | ID: {q.id} | Type: {q.question_type.value}")
                print("=" * 80)
                print(f"Text:\n{q.question_text}")
                if q.code_snippet:
                    print(f"\nCode Snippet:\n{q.code_snippet}")
                print(f"\nKeywords: {q.keywords}")
                print(f"\nExpected Answer:\n{q.expected_answer}")
                print("=" * 80)
                
            print("\n🎉 TARGETED LIVE AI GENERATION BATCH TEST COMPLETED SUCCESSFULLY! 🎉")
            
    except Exception as e:
        print(f"\n❌ Error during AI generation test: {e}")
        print("\n💡 Hint: Make sure you are authenticated with Google Cloud:")
        print("  gcloud auth application-default login")
        sys.exit(1)

if __name__ == "__main__":
    run_ai_generator_test()
