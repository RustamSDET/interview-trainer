import sys
from pathlib import Path

# Add project root to sys.path to resolve 'src' imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.config import DB_PATH
from src.database.connection import init_db, get_db_session
from src.database.repository import create_global_topic, create_local_topic

TOPICS_DATA = [
    {
        "name": "Python Core & Computer Science",
        "priority": 9,
        "description": "Базовый фундамент языка, на котором пишется весь фреймворк и проходяться секции кодинга.",
        "local_topics": [
            {"name": "Data Structures & Complexity", "priority": 10, "description": "Списки, словари, множества, мутабельность, сложность операций O(n)", "allowed_question_types": "Theory,Algorithms,BugHunting"},
            {"name": "Advanced Python", "priority": 10, "description": "Декораторы, генераторы, итераторы, контекстные менеджеры — это фундамент для понимания Pytest под капотом", "allowed_question_types": "Theory,BugHunting"},
            {"name": "Asyncio & Concurrency", "priority": 9, "description": "GIL, разница между threading/multiprocessing, асинхронность под капотом", "allowed_question_types": "Theory,BugHunting"},
            {"name": "OOP & MRO", "priority": 7, "description": "Наследование, инкапсуляция, полиморфизм, миксины, магические методы, порядок разрешения методов", "allowed_question_types": "Theory,BugHunting"},
            {"name": "Basic Algorithms", "priority": 6, "description": "Задачи уровня LeetCode Easy/Medium на строки и массивы", "allowed_question_types": "Theory,Algorithms"},
        ]
    },
    {
        "name": "Pytest Framework",
        "priority": 10,
        "description": "Твой главный инструмент-раннер, разобранный до молекул.",
        "local_topics": [
            {"name": "Fixtures & Scopes", "priority": 10, "description": "Управление фикстурами, yield, автоюз, области видимости session/module/class/function", "allowed_question_types": "Theory,BugHunting"},
            {"name": "Execution & Parallelism", "priority": 10, "description": "Параллельный запуск через pytest-xdist, изоляция состояния воркеров — самая частая тема на сеньорских собесах", "allowed_question_types": "Theory,TestArch"},
            {"name": "Conftest & Configuration", "priority": 9, "description": "Каскады conftest.py, кастомные CLI-флаги, инициализация окружения", "allowed_question_types": "Theory,BugHunting,TestArch"},
            {"name": "Parametrization", "priority": 9, "description": "Data-driven тестирование, динамическое создание тест-кейсов", "allowed_question_types": "Theory,BugHunting,TestDesign"},
            {"name": "Plugins & Hooks", "priority": 8, "description": "Кастомные плагины, хуки жизненного цикла тестов, например pytest_runtest_makereport", "allowed_question_types": "Theory,BugHunting,TestArch"},
        ]
    },
    {
        "name": "Playwright UI Automation",
        "priority": 9,
        "description": "Современный стандарт веб-автоматизации и фронтенд-магии.",
        "local_topics": [
            {"name": "Network Interception", "priority": 10, "description": "Перехват, мокирование и подмена API-ответов прямо внутри контекста браузера, роутинг — киллер-фича Playwright", "allowed_question_types": "Theory,BugHunting,TestDesign"},
            {"name": "Contexts & Auth", "priority": 9, "description": "Изоляция через BrowserContext, сохранение кук/стейта авторизации, многостраничные сценарии", "allowed_question_types": "Theory,BugHunting,TestArch,TestDesign"},
            {"name": "Locators & Assertions", "priority": 8, "description": "Селекторы, Strict mode, механизмы Auto-waiting, веб-фермы", "allowed_question_types": "Theory,BugHunting,TestDesign"},
            {"name": "Advanced UI Handling", "priority": 7, "description": "Работа с iframes, Shadow DOM, скачивание файлов, хендлинг алертов", "allowed_question_types": "Theory,BugHunting,TestDesign"},
        ]
    },
    {
        "name": "Backend & API Automation",
        "priority": 10,
        "description": "Инструменты и подходы для тестирования логики без участия UI.",
        "local_topics": [
            {"name": "Data Validation (Pydantic)", "priority": 10, "description": "Контрактные тесты, строгая типизация JSON-ответов, кастомные валидаторы", "allowed_question_types": "Theory,BugHunting,TestDesign"},
            {"name": "Smart Mocking (FastAPI)", "priority": 9, "description": "Создание умных stateful-заглушек вместо статического WireMock", "allowed_question_types": "Theory,BugHunting,TestArch,TestDesign"},
            {"name": "Advanced Protocols", "priority": 8, "description": "Тестирование очередей сообщений Kafka/RabbitMQ, работа с gRPC и Protobuf", "allowed_question_types": "Theory,BugHunting,TestArch,TestDesign"},
            {"name": "HTTPx & Async Clients", "priority": 8, "description": "Асинхронные HTTP-клиенты, пулы соединений, таймауты, сессии", "allowed_question_types": "Theory,BugHunting,TestArch,TestDesign"},
        ]
    },
    {
        "name": "Test Architecture & System Design",
        "priority": 10,
        "description": "Умение собирать отдельные скрипты в поддерживаемую корпоративную систему.",
        "local_topics": [
            {"name": "Test Data Management", "priority": 10, "description": "Стратегии генерации данных, использование Faker, фабрики данных, очистка БД", "allowed_question_types": "Theory,BugHunting,TestArch,TestDesign"},
            {"name": "Design Patterns", "priority": 8, "description": "Page Object Pattern, Fluent Interface, Screenplay, Factory, Singleton в контексте QA", "allowed_question_types": "Theory,BugHunting,TestArch,TestDesign"},
            {"name": "Reporting & Observability", "priority": 7, "description": "Интеграция с Allure, кастомное логирование шагов, сбор метрик", "allowed_question_types": "Theory,BugHunting,TestArch"},
        ]
    },
    {
        "name": "Infrastructure & CI/CD",
        "priority": 9,
        "description": "Окружение, контейнеризация и доставка тестов в продакшн-пайплайн.",
        "local_topics": [
            {"name": "Docker Basics", "priority": 9, "description": "Написание оптимальных Dockerfile, слои кэширования, запуск тестов в контейнере", "allowed_question_types": "Theory,BugHunting,TestArch"},
            {"name": "CI/CD Pipelines", "priority": 9, "description": "GitLab CI / GitHub Actions, триггеры, запуск по расписанию, артефакты", "allowed_question_types": "Theory,TestArch"},
            {"name": "Docker Compose", "priority": 8, "description": "Поднятие локального окружения: приложение + база + зависимые сервисы", "allowed_question_types": "Theory,BugHunting,TestArch"},
            {"name": "Distributed Execution", "priority": 8, "description": "Playwright Sharding, масштабирование через Selenoid/Kubernetes", "allowed_question_types": "Theory,BugHunting,TestArch"},
        ]
    },
    {
        "name": "Databases & Networks",
        "priority": 9,
        "description": "Инженерный бэкграунд: как устроены системы под капотом.",
        "local_topics": [
            {"name": "SQL & Database Internals", "priority": 9, "description": "Сложные запросы, JOIN, агрегации, индексы, ACID, транзакции", "allowed_question_types": "Theory,BugHunting,TestDesign"},
            {"name": "Web & Network Basics", "priority": 9, "description": "Устройство HTTP/HTTPS, заголовки, куки, CORS, сессии, REST vs GraphQL", "allowed_question_types": "Theory,BugHunting,TestDesign"},
            {"name": "ORM (SQLAlchemy)", "priority": 7, "description": "Интеграция ORM в тестовые фикстуры, сессии БД", "allowed_question_types": "Theory,BugHunting,TestArch,TestDesign"},
        ]
    },
    {
        "name": "QA Mindset & Methodology",
        "priority": 7,
        "description": "Продуктовое мышление, софт-скиллы и процессы.",
        "local_topics": [
            {"name": "Flaky Tests Management", "priority": 10, "description": "Стратегии борьбы с мигающими тестами, поиск инфраструктурных проблем", "allowed_question_types": "Theory,BugHunting,TestArch,TestDesign"},
            {"name": "Shift-Left & Test Strategy", "priority": 8, "description": "Пирамида тестирования, включение QA на этапе требований, метрики покрытия", "allowed_question_types": "Theory,TestArch,TestDesign"},
            {"name": "Behavioral & HR (STAR)", "priority": 7, "description": "Рассказы о факапах, достижениях, перформанс-ревью, софт-скиллах", "allowed_question_types": "Theory,Behavioral"},
            {"name": "Test Design Techniques", "priority": 6, "description": "Применение Pairwise, эквивалентных классов и граничных значений в автотестах", "allowed_question_types": "Theory,BugHunting,TestDesign"},
        ]
    }
]

def seed_database(fresh: bool = False):
    print("🌱 Database seeding has started...")
    
    if fresh and DB_PATH.exists():
        print(f"🧹 Option '--fresh' received: Deleting old database at {DB_PATH}")
        DB_PATH.unlink()
        
    print("📦 Initializing database schema...")
    init_db()
    
    with get_db_session() as session:
        for g_topic_data in TOPICS_DATA:
            # Create or get global topic (will update its priority if it exists)
            g_topic = create_global_topic(
                session,
                name=g_topic_data["name"],
                description=g_topic_data["description"],
                priority=g_topic_data["priority"]
            )
            print(f"🌍 Global Topic: '{g_topic.name}' [Priority: {g_topic.priority}/10]")
            
            # Fetch existing local topics for this global topic to prevent duplicate inserts
            from sqlalchemy import select
            from src.database.models import LocalTopic
            stmt = select(LocalTopic).where(LocalTopic.global_topic_id == g_topic.id)
            existing_locals = {lt.name: lt for lt in session.scalars(stmt).all()}
            
            for l_topic_data in g_topic_data["local_topics"]:
                if l_topic_data["name"] in existing_locals:
                    # Update priority and allowed_question_types of existing local topic if different
                    lt = existing_locals[l_topic_data["name"]]
                    updated = False
                    if lt.priority != l_topic_data["priority"]:
                        lt.priority = l_topic_data["priority"]
                        updated = True
                    if lt.allowed_question_types != l_topic_data["allowed_question_types"]:
                        lt.allowed_question_types = l_topic_data["allowed_question_types"]
                        updated = True
                    if updated:
                        session.flush()
                        print(f"   ↳ 🔄 Local Topic '{lt.name}' already exists (Updated Priority: {lt.priority}/10, Types: {lt.allowed_question_types})")
                    else:
                        print(f"   ↳ 🔄 Local Topic '{lt.name}' already exists (No changes)")
                else:
                    lt = create_local_topic(
                        session,
                        global_topic_id=g_topic.id,
                        name=l_topic_data["name"],
                        description=l_topic_data["description"],
                        priority=l_topic_data["priority"],
                        allowed_question_types=l_topic_data["allowed_question_types"]
                    )
                    print(f"   ↳ 🆕 Local Topic: '{lt.name}' [Priority: {lt.priority}/10, Types: {lt.allowed_question_types}]")
                    
    print("\n🎉 Seeding completed successfully!")

if __name__ == "__main__":
    fresh_run = "--fresh" in sys.argv
    seed_database(fresh=fresh_run)
