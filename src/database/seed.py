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
        "name": "BACKEND & API AUTOMATION",
        "priority": 10,
        "description": "Практическое тестирование серверной логики, межсервисного взаимодействия и API. Раздел охватывает методы валидации контрактов, стратегии изоляции тестов с помощью моков и стабов, а также работу с протоколами и брокерами сообщений в контексте проверки бизнес-логики.",
        "local_topics": [
            {
                "name": "REST API Testing",
                "priority": 9,
                "description": "Практическое тестирование через HTTPx/Requests, работа с XML (SOAP) и JSON (REST), обработка сессий и таймаутов.",
                "allowed_question_types": "Theory,BugHunting,TestDesign"
            },
            {
                "name": "Kafka Integration Testing",
                "priority": 8,
                "description": "Тестирование интеграций через Kafka. Валидация отправки и чтения (producer/consumer), изоляция тестовых данных, консьюмер-группы.",
                "allowed_question_types": "Theory,TestArch,TestDesign"
            },
            {
                "name": "Data Validation (Pydantic)",
                "priority": 9,
                "description": "Контрактные тесты, строгая типизация ответов, валидация JSON-схем, написание кастомных валидаторов.",
                "allowed_question_types": "Theory,BugHunting"
            },
            {
                "name": "Mocking & Stubbing",
                "priority": 9,
                "description": "Создание заглушек, мокирование ответов микросервисов для изоляции E2E тестов.",
                "allowed_question_types": "Theory,BugHunting,TestArch"
            }
        ]
    },
    {
        "name": "DATABASES, LINUX & NETWORKS",
        "priority": 8,
        "description": "Базовая инфраструктурная грамотность инженера по тестированию. Включает навыки работы с базами данных для подготовки тестовых данных, использование консоли Linux для траблшутинга и чтения логов, а также понимание фундаментальных принципов работы сетей.",
        "local_topics": [
            {
                "name": "PostgreSQL & SQL Basics",
                "priority": 9,
                "description": "Практический SQL (JOIN, агрегации, базовые индексы), подготовка, валидация и очистка тестовых данных в БД.",
                "allowed_question_types": "Theory,Algorithms,BugHunting,TestDesign"
            },
            {
                "name": "ORM (SQLAlchemy) in Testing",
                "priority": 8,
                "description": "Использование ORM как фабрики данных для фикстур. Тестирование транзакций, сброс состояния БД после теста (teardown).",
                "allowed_question_types": "Theory,BugHunting,TestArch"
            },
            {
                "name": "Linux CLI & Troubleshooting",
                "priority": 8,
                "description": "Базовые команды (grep, tail, awk), чтение логов, работа с сетью (curl, ping) для дебага падающих тестов.",
                "allowed_question_types": "Theory,BugHunting"
            },
            {
                "name": "Web & Network Basics",
                "priority": 9,
                "description": "Устройство HTTP/HTTPS, заголовки, куки, CORS, статус-коды.",
                "allowed_question_types": "Theory,BugHunting"
            }
        ]
    },
    {
        "name": "INFRASTRUCTURE & CI/CD",
        "priority": 8,
        "description": "Инструменты и процессы непрерывной интеграции и доставки автотестов. Раздел посвящен контейнеризации тестовых сред, настройке пайплайнов для регулярного запуска, а также выполнению тестов в распределенных средах и кластерах.",
        "local_topics": [
            {
                "name": "CI/CD Pipelines (GitLab/GitHub/Bamboo)",
                "priority": 9,
                "description": "Настройка джоб, триггеры, передача секретов и переменных окружения, кэширование зависимостей.",
                "allowed_question_types": "Theory,BugHunting,TestArch"
            },
            {
                "name": "Docker Ecosystem & Playwright CI",
                "priority": 8,
                "description": "Написание Dockerfile для автотестов, docker-compose для локального окружения. Запуск браузеров в контейнерах, проброс видео и артефактов в CI.",
                "allowed_question_types": "Theory,BugHunting,TestArch"
            },
            {
                "name": "Kubernetes for SDET",
                "priority": 7,
                "description": "Запуск тест-ранов внутри K8s, базовые команды kubectl, траблшутинг падающих подов с тестами, доступ к логам.",
                "allowed_question_types": "Theory,TestArch"
            }
        ]
    },
    {
        "name": "PLAYWRIGHT UI AUTOMATION",
        "priority": 9,
        "description": "Современный стандарт автоматизации веб-интерфейсов. Фокус на архитектуре Playwright, его механизмах встроенных ожиданий (auto-waiting), изоляции браузерных контекстов и продвинутых техниках перехвата сетевого трафика.",
        "local_topics": [
            {
                "name": "Locators & Assertions",
                "priority": 9,
                "description": "Селекторы, Strict mode, встроенные веб-ассерты (expect), механизмы Auto-waiting.",
                "allowed_question_types": "Theory,BugHunting,TestDesign"
            },
            {
                "name": "Network Interception",
                "priority": 10,
                "description": "Перехват запросов, подмена API-ответов прямо внутри браузера, блокировка тяжелых ресурсов для ускорения тестов.",
                "allowed_question_types": "Theory,BugHunting,TestDesign"
            },
            {
                "name": "Contexts & Auth",
                "priority": 9,
                "description": "Изоляция через BrowserContext, сохранение стейта авторизации (сохранение кук в файл), многостраничные сценарии.",
                "allowed_question_types": "Theory,BugHunting,TestArch"
            },
            {
                "name": "Advanced UI & Pytest Integration",
                "priority": 8,
                "description": "Работа с iframes, загрузка файлов, использование встроенных фикстур pytest-playwright (page, context).",
                "allowed_question_types": "Theory,BugHunting,TestDesign"
            }
        ]
    },
    {
        "name": "PYTEST FRAMEWORK",
        "priority": 10,
        "description": "Глубокое погружение в устройство тест-раннера. Раздел оценивает умение проектировать модульные наборы тестов, управлять жизненным циклом фикстур, параметризировать проверки и безопасно запускать тесты в параллельном режиме.",
        "local_topics": [
            {
                "name": "Fixtures & Scopes",
                "priority": 10,
                "description": "Управление фикстурами, yield (teardown), области видимости (session/module/function), conftest.py.",
                "allowed_question_types": "Theory,BugHunting,TestArch"
            },
            {
                "name": "Pytest-Asyncio",
                "priority": 8,
                "description": "Написание и запуск асинхронных тестов, работа с асинхронными фикстурами, управление event loop.",
                "allowed_question_types": "Theory,BugHunting"
            },
            {
                "name": "Parametrization",
                "priority": 9,
                "description": "Data-driven тестирование, динамическая генерация кейсов, переопределение фикстур через indirect=True.",
                "allowed_question_types": "Theory,BugHunting,TestDesign"
            },
            {
                "name": "Execution & Parallelism",
                "priority": 9,
                "description": "Запуск через pytest-xdist, потокобезопасность тестов, изоляция стейта между воркерами БД при параллельном запуске.",
                "allowed_question_types": "Theory,BugHunting,TestArch"
            }
        ]
    },
    {
        "name": "PYTHON CORE & TYPING",
        "priority": 9,
        "description": "Фундаментальные знания языка Python, необходимые для написания чистого и поддерживаемого кода автотестов. Включает строгую типизацию, объектно-ориентированное программирование для проектирования фреймворка и основы асинхронности.",
        "local_topics": [
            {
                "name": "Type Hinting (PEP 484)",
                "priority": 8,
                "description": "Строгая типизация, использование Optional, Union, Callable, Any, TypeVar, настройка Mypy.",
                "allowed_question_types": "Theory,BugHunting"
            },
            {
                "name": "Data Structures & Memory",
                "priority": 9,
                "description": "Списки, словари, множества, мутабельность дефолтных аргументов.",
                "allowed_question_types": "Theory,Algorithms,BugHunting"
            },
            {
                "name": "Advanced Python",
                "priority": 10,
                "description": "Декораторы, генераторы, итераторы, контекстные менеджеры (with).",
                "allowed_question_types": "Theory,BugHunting"
            },
            {
                "name": "OOP in QA",
                "priority": 9,
                "description": "Применение ООП для написания Page Objects, API-клиентов. Наследование, миксины, *args, kwargs.",
                "allowed_question_types": "Theory,BugHunting,TestArch"
            },
            {
                "name": "Asyncio Basics",
                "priority": 8,
                "description": "Понимание корутин, задач (asyncio.create_task), отличия I/O-bound (сеть/ожидания) от CPU-bound задач.",
                "allowed_question_types": "Theory,BugHunting"
            }
        ]
    },
    {
        "name": "TEST AUTOMATION ARCHITECTURE",
        "priority": 10,
        "description": "Проектирование масштабируемой архитектуры тестовых фреймворков. Раздел описывает применение паттернов проектирования в тестировании, стратегии управления тестовыми данными и интеграцию систем отчетности.",
        "local_topics": [
            {
                "name": "Framework Design Patterns",
                "priority": 9,
                "description": "Page Object Pattern, Fluent Interface, Singleton, Data Builder / Factory.",
                "allowed_question_types": "Theory,BugHunting,TestArch"
            },
            {
                "name": "Test Data Management",
                "priority": 9,
                "description": "Стратегии генерации независимых данных, использование библиотек типа Faker, подходы к изоляции (каждый тест создает свои данные).",
                "allowed_question_types": "Theory,BugHunting,TestArch,TestDesign"
            },
            {
                "name": "Observability & Reporting",
                "priority": 8,
                "description": "Интеграция Allure-отчетов, сбор логов выполнения через Kibana, базовое понимание дашбордов Grafana для анализа времени выполнения тестов.",
                "allowed_question_types": "Theory,BugHunting,TestArch"
            }
        ]
    },
    {
        "name": "QA MINDSET & METHODOLOGY",
        "priority": 7,
        "description": "Продуктовое мышление, процессы обеспечения качества и навыки коммуникации. Охватывает стратегии борьбы с нестабильными тестами, подходы к тест-дизайну, метрики эффективности тестирования и поведенческие сценарии.",
        "local_topics": [
            {
                "name": "Flaky Tests Management",
                "priority": 10,
                "description": "Стратегии поиска плавающих тестов, анализ причин (сеть, моргающий UI, конкуррентность в БД), авторетраи.",
                "allowed_question_types": "Theory,BugHunting,TestArch,TestDesign"
            },
            {
                "name": "Test Design & Strategy",
                "priority": 8,
                "description": "Пирамида тестирования, Shift-Left, оценка тестового покрытия, выбор приоритетов для автоматизации.",
                "allowed_question_types": "Theory,TestDesign"
            },
            {
                "name": "QA Metrics",
                "priority": 7,
                "description": "Метрики автотестов (Pass rate, Time to Resolve, Test Execution Time), интеграция QA-gate в процесс релиза.",
                "allowed_question_types": "Theory,TestArch"
            },
            {
                "name": "Behavioral (STAR)",
                "priority": 9,
                "description": "Разрешение конфликтов с разработчиками, аргументация выбора инструментов, онбординг коллег в автоматизацию.",
                "allowed_question_types": "Behavioral"
            }
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
