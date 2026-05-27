from typing import List, Optional, Dict, TypedDict
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END

from src.services.ai.base import get_vertex_llm
from src.services.ai.prompts import SYSTEM_PROMPT, USER_PROMPT, TYPE_REQUIREMENTS
from src.database.models import GlobalTopic, LocalTopic, Question, QuestionType, QuestionGrade
from src.database.repository import create_question


# --- Pydantic Schemas for Structured Output ---

class GeneratedQuestion(BaseModel):
    """Схема одного сгенерированного вопроса для интервью"""
    text: str = Field(
        ...,
        description="Текст вопроса. Должен быть глубоким, конкретным, соответствующим заданной теме и типу вопроса."
    )
    expected_answer: str = Field(
        ...,
        description="Подробный, развернутый эталонный ответ со всеми техническими деталями и обоснованием."
    )
    keywords: str = Field(
        ...,
        description="Ключевые слова и технические термины через запятую. Если ключевых слов нет, пустая строка."
    )
    code_snippet: str = Field(
        ...,
        description="Опциональный кусок кода (обязателен для BugHunting с багом и для Algorithms с шаблоном). Если код не требуется, пустая строка."
    )
    grade: str = Field(
        ...,
        description="Уровень сложности вопроса. Должен быть строго один из: junior, middle, senior."
    )


class GeneratedQuestions(BaseModel):
    """Схема списка сгенерированных вопросов"""
    questions: List[GeneratedQuestion] = Field(
        ...,
        description="Список из ровно 6 уникальных высококачественных вопросов (3 уровня junior, 2 уровня middle, 1 уровня senior)."
    )


# --- Helper to flatten nested JSON schemas (resolving $defs/$ref) for Vertex AI ---

def make_schema_flat(schema: dict) -> dict:
    """
    Рекурсивно раскрывает ссылки $ref, подставляя определения из $defs,
    делая JSON-схему плоской и совместимой с Vertex AI.
    """
    if "$defs" not in schema:
        return schema
    
    defs = schema.pop("$defs")
    
    def resolve_refs(obj):
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref_path = obj["$ref"]
                def_name = ref_path.split("/")[-1]
                # Рекурсивно подставляем реальную схему вместо ссылки
                return resolve_refs(defs[def_name])
            return {k: resolve_refs(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [resolve_refs(item) for item in obj]
        return obj

    return resolve_refs(schema)


# --- LangGraph Workflow Structure ---

class GeneratorState(TypedDict):
    """Состояние графа генерации вопросов"""
    global_topic_name: str
    global_topic_desc: str
    local_topic_name: str
    local_topic_desc: str
    question_type_name: str
    type_requirements: str
    result: Optional[GeneratedQuestions]


def generate_questions_node(state: GeneratorState) -> dict:
    """
    Узел графа, который вызывает LLM со структурированным Pydantic-выводом
    для генерации списка вопросов.
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", USER_PROMPT)
    ])
    
    prompt_messages = prompt.format_messages(
        question_type_name=state["question_type_name"],
        type_requirements=state["type_requirements"],
        global_topic_name=state["global_topic_name"],
        global_topic_desc=state["global_topic_desc"],
        local_topic_name=state["local_topic_name"],
        local_topic_desc=state["local_topic_desc"]
    )
    
    # Инициализируем LLM
    llm = get_vertex_llm()
    
    # Выполняем быстрый прогрев сессии для надежной работы структурированного вывода в окружении GCP
    try:
        print("DEBUG: Выполнение быстрого прогревочного запроса...")
        llm.invoke("warmup")
    except Exception as warmup_err:
        print(f"DEBUG: Предупреждение во время прогрева (игнорируется): {warmup_err}")
    
    # 1. Извлекаем сырую JSON-схему из Pydantic-модели
    raw_schema = GeneratedQuestions.model_json_schema()
    
    # 2. Делаем схему плоской, удаляя $defs и $ref для совместимости с Vertex AI
    flat_json_schema = make_schema_flat(raw_schema)
    
    # 3. Настраиваем структурированный вывод по плоской схеме с include_raw=True
    structured_llm = llm.with_structured_output(flat_json_schema, include_raw=True)
    
    # 4. Вызываем модель и парсим словарь обратно в Pydantic-модель
    print(f"DEBUG: Invoking model with structured output (include_raw=True).")
    try:
        response_dict = structured_llm.invoke(prompt_messages)
        if response_dict:
            print(f"DEBUG: response_dict keys: {list(response_dict.keys())}")
            print(f"DEBUG: parsing_error: {response_dict.get('parsing_error')}")
            print(f"DEBUG: raw response: {response_dict.get('raw')}")
            ai_response = response_dict.get('parsed')
        else:
            print("DEBUG: response_dict is None!")
            ai_response = None
        print(f"DEBUG: parsed response: {ai_response}")
    except Exception as exc:
        print(f"DEBUG: Invoke exception: {exc}")
        raise exc
    
    # Валидируем сырой словарь обратно в наш Pydantic-класс
    if ai_response is None:
        raise ValueError(f"Модель вернула пустой результат или произошла ошибка парсинга. Подробности в логах.")
        
    parsed_result = GeneratedQuestions.model_validate(ai_response)
    
    return {"result": parsed_result}


# Сборка графа генератора
workflow = StateGraph(GeneratorState)
workflow.add_node("generate_questions", generate_questions_node)
workflow.add_edge(START, "generate_questions")
workflow.add_edge("generate_questions", END)

generator_app = workflow.compile()


# --- Core Generator Functions ---

def generate_questions_for_topic_and_type(
    db: Session,
    local_topic_id: int,
    question_type: QuestionType,
    overwrite: bool = True
) -> int:
    """
    Генерирует ровно 6 вопросов конкретного типа для указанной подтемы с помощью LangGraph.
    При `overwrite=True` удаляет старые вопросы этого типа по этой теме перед сохранением.
    
    Args:
        db (Session): Сессия подключения к БД.
        local_topic_id (int): ID подтемы.
        question_type (QuestionType): Конкретный тип вопросов для генерации.
        overwrite (bool): Флаг перезаписи существующих вопросов этого же типа.
        
    Returns:
        int: Количество успешно созданных и сохраненных вопросов.
    """
    # 1. Извлекаем локальную и глобальную тему из БД
    local_topic = db.get(LocalTopic, local_topic_id)
    if not local_topic:
        raise ValueError(f"LocalTopic с ID {local_topic_id} не найден.")
        
    global_topic = local_topic.global_topic
    if not global_topic:
        raise ValueError(f"Глобальная тема для LocalTopic ID {local_topic_id} не найдена.")
    
    type_val = question_type.value
    if type_val not in TYPE_REQUIREMENTS:
        raise ValueError(f"Требования для типа вопросов '{type_val}' не описаны в TYPE_REQUIREMENTS.")
        
    # 2. Подготавливаем входные данные для LangGraph
    inputs = {
        "global_topic_name": global_topic.name,
        "global_topic_desc": global_topic.description or "",
        "local_topic_name": local_topic.name,
        "local_topic_desc": local_topic.description or "",
        "question_type_name": type_val,
        "type_requirements": TYPE_REQUIREMENTS[type_val],
        "result": None
    }
    
    # 3. Запуск генерации напрямую (обход накладных расходов LangGraph для стабильности)
    print(f"🤖 Запуск генерации вопросов | Подтема: '{local_topic.name}' | Тип вопроса: '{type_val}'...")
    final_state = generate_questions_node(inputs)
    response: Optional[GeneratedQuestions] = final_state.get("result")
    
    # 4. Если включена перезапись, удаляем старые вопросы этого типа для этой подтемы
    if overwrite:
        stmt = delete(Question).where(
            Question.local_topic_id == local_topic_id,
            Question.question_type == question_type
        )
        db.execute(stmt)
        db.flush()
        print(f"🧹 Удалены старые вопросы типа '{type_val}' для подтемы '{local_topic.name}'.")
    
    # 5. Сохраняем сгенерированные вопросы в БД
    created_count = 0
    if response and response.questions:
        for q in response.questions:
            q_text = q.text.strip()
            q_ans = q.expected_answer.strip()
            q_key = q.keywords.strip()
            
            # Программная защита: для типа Theory принудительно обнуляем code_snippet
            if question_type == QuestionType.THEORY:
                q_code = ""
            else:
                q_code = q.code_snippet.strip() if q.code_snippet else ""
            
            # Пропускаем, если по какой-то причине текст пустой
            if not q_text:
                continue
                
            # Safely map grade to QuestionGrade enum
            try:
                grade_enum = QuestionGrade(q.grade.lower().strip())
            except Exception:
                grade_enum = QuestionGrade.MIDDLE
                
            create_question(
                db=db,
                local_topic_id=local_topic_id,
                question_text=q_text,
                expected_answer=q_ans,
                question_type=question_type,
                keywords=q_key,
                code_snippet=q_code,
                grade=grade_enum
            )
            created_count += 1
        
    db.commit()
    print(f"✅ Успешно сгенерировано и сохранено {created_count} вопросов типа '{type_val}' для '{local_topic.name}'.")
    return created_count


def generate_questions_batch(
    db: Session,
    targets: List[tuple[int, QuestionType]],
    overwrite: bool = True
) -> int:
    """
    Генерирует вопросы для списка целей (ID подтемы, тип вопроса) в параллельном режиме
    с использованием встроенного метода .batch() в LangChain/LangGraph.
    Гарантирует атомарность и потокобезопасность транзакций БД, выполняя операции с базой
    последовательно на главном потоке.
    """
    if not targets:
        return 0

    inputs_list = []
    valid_targets = []

    # 1. Сбор и подготовка входных данных для всех батч-запросов (чтение из БД)
    for local_topic_id, question_type in targets:
        local_topic = db.get(LocalTopic, local_topic_id)
        if not local_topic:
            print(f"WARN: LocalTopic ID {local_topic_id} не найден. Пропуск.")
            continue
            
        global_topic = local_topic.global_topic
        if not global_topic:
            print(f"WARN: GlobalTopic для LocalTopic ID {local_topic_id} не найден. Пропуск.")
            continue

        type_val = question_type.value
        if type_val not in TYPE_REQUIREMENTS:
            print(f"WARN: Требования для типа вопросов '{type_val}' не найдены. Пропуск.")
            continue

        inputs = {
            "global_topic_name": global_topic.name,
            "global_topic_desc": global_topic.description or "",
            "local_topic_name": local_topic.name,
            "local_topic_desc": local_topic.description or "",
            "question_type_name": type_val,
            "type_requirements": TYPE_REQUIREMENTS[type_val],
            "result": None
        }
        inputs_list.append(inputs)
        valid_targets.append((local_topic_id, question_type, local_topic.name))

    if not inputs_list:
        return 0

    print(f"🤖 Запуск параллельной генерации для {len(inputs_list)} запросов (max_concurrency=10)...")
    
    # 2. Выполнение батч-запроса через LangGraph
    # Метод .batch() сам управляет параллельными сетевыми вызовами к API Vertex AI
    batch_results = generator_app.batch(inputs_list, config={"max_concurrency": 10})

    # 3. Сохранение сгенерированных вопросов в базу данных (последовательно на главном потоке)
    created_count = 0
    for (local_topic_id, qtype, lt_name), final_state in zip(valid_targets, batch_results):
        response: Optional[GeneratedQuestions] = final_state.get("result")
        type_val = qtype.value
        
        # Если включена перезапись, удаляем старые вопросы этого типа для этой подтемы
        if overwrite:
            stmt = delete(Question).where(
                Question.local_topic_id == local_topic_id,
                Question.question_type == qtype
            )
            db.execute(stmt)
            db.flush()
            print(f"🧹 Удалены старые вопросы типа '{type_val}' для подтемы '{lt_name}'.")

        # Сохраняем сгенерированные вопросы в БД
        if response and response.questions:
            for q in response.questions:
                q_text = q.text.strip()
                q_ans = q.expected_answer.strip()
                q_key = q.keywords.strip()
                
                # Программная защита: для типа Theory принудительно обнуляем code_snippet
                if qtype == QuestionType.THEORY:
                    q_code = ""
                else:
                    q_code = q.code_snippet.strip() if q.code_snippet else ""

                if not q_text:
                    continue

                # Safely map grade to QuestionGrade enum
                try:
                    grade_enum = QuestionGrade(q.grade.lower().strip())
                except Exception:
                    grade_enum = QuestionGrade.MIDDLE

                create_question(
                    db=db,
                    local_topic_id=local_topic_id,
                    question_text=q_text,
                    expected_answer=q_ans,
                    question_type=qtype,
                    keywords=q_key,
                    code_snippet=q_code,
                    grade=grade_enum
                )
                created_count += 1

    db.commit()
    print(f"✅ Батч-генерация завершена. Успешно сохранено {created_count} вопросов!")
    return created_count


def generate_questions_for_topic_all_types(
    db: Session,
    local_topic_id: int,
    overwrite: bool = True
) -> Dict[str, Dict]:
    """
    Генерирует вопросы всех разрешенных типов для одной указанной подтемы.
    """
    local_topic = db.get(LocalTopic, local_topic_id)
    if not local_topic:
        raise ValueError(f"LocalTopic с ID {local_topic_id} не найден.")
        
    allowed_types_str = local_topic.allowed_question_types
    allowed_types = [t.strip() for t in allowed_types_str.split(",") if t.strip()]
    
    print(f"\n⚡ Запуск генерации всех типов для темы: '{local_topic.name}'")
    print(f"Разрешенные типы: {allowed_types}")
    
    results = {}
    for type_str in allowed_types:
        try:
            q_type = QuestionType(type_str)
            count = generate_questions_for_topic_and_type(
                db=db,
                local_topic_id=local_topic_id,
                question_type=q_type,
                overwrite=overwrite
            )
            results[type_str] = {"status": "success", "count": count}
        except Exception as e:
            results[type_str] = {"status": "error", "error": str(e)}
            
    return results


def generate_all_questions(db: Session, overwrite: bool = True) -> Dict[int, Dict]:
    """
    Базовый режим работы для UI / Админ-панели:
    Полная генерация банка вопросов. Проходит по ВСЕМ глобальным и локальным темам в БД
    и генерирует по 6 вопросов под каждый разрешенный тип.
    
    Returns:
        Dict[int, Dict]: Отчет о результатах генерации по каждому local_topic_id.
    """
    stmt = select(LocalTopic)
    local_topics = db.scalars(stmt).all()
    
    print(f"📊 Начинается полная генерация банка вопросов для {len(local_topics)} тем...")
    
    bulk_results = {}
    for lt in local_topics:
        try:
            topic_results = generate_questions_for_topic_all_types(
                db=db,
                local_topic_id=lt.id,
                overwrite=overwrite
            )
            bulk_results[lt.id] = {
                "name": lt.name,
                "status": "completed",
                "results": topic_results
            }
        except Exception as e:
            bulk_results[lt.id] = {
                "name": lt.name,
                "status": "failed",
                "error": str(e)
            }
            
    print("\n🏁 Полная генерация банка вопросов завершена!")
    return bulk_results
