from typing import List, Dict, Optional
from src.services.ai.base import get_vertex_llm
from src.services.ai.prompt_answer_analyzer import SYSTEM_PROMPT, USER_PROMPT_SINGLE, USER_PROMPT_BATCH
from langchain_core.prompts import ChatPromptTemplate
from src.services.ai.schemas import CriterionEvaluation, SingleAnswerEvaluation, BatchAnswerEvaluation


# --- Helper to flatten schemas ---

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
                return resolve_refs(defs[def_name])
            return {k: resolve_refs(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [resolve_refs(item) for item in obj]
        return obj

    return resolve_refs(schema)


# --- Core Analyzer Service Functions ---

def analyze_answers_batch(items: List[Dict[str, str]]) -> BatchAnswerEvaluation:
    """
    Принимает список из 1-5 ответов для оценки за один промпт.
    Каждый элемент списка должен быть словарем с ключами:
    - "question"
    - "expected_answer"
    - "user_answer"
    
    Возвращает объект BatchAnswerEvaluation.
    """
    if not items:
        return BatchAnswerEvaluation(evaluations=[])
        
    if len(items) > 5:
        raise ValueError("Максимальный размер пачки для анализа - 5 вопросов.")

    # Строим текстовый блок из вопросов
    questions_block_parts = []
    for idx, item in enumerate(items):
        part = (
            f"=== Question {idx} ===\n"
            f"[Question]: {item['question']}\n"
            f"[Expected Answer]: {item['expected_answer']}\n"
            f"[Candidate's Transcribed Answer]: {item['user_answer']}\n"
        )
        questions_block_parts.append(part)
        
    questions_block = "\n".join(questions_block_parts)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", USER_PROMPT_BATCH)
    ])
    
    prompt_messages = prompt.format_messages(
        questions_block=questions_block
    )

    llm = get_vertex_llm()
    
    # Быстрый прогрев сессии
    try:
        llm.invoke("warmup")
    except Exception as warmup_err:
        print(f"DEBUG: Warmup warning: {warmup_err}")

    raw_schema = BatchAnswerEvaluation.model_json_schema()
    flat_json_schema = make_schema_flat(raw_schema)
    
    structured_llm = llm.with_structured_output(flat_json_schema, include_raw=True)
    
    print(f"DEBUG: Invoking AI Analyzer with {len(items)} items...")
    response_dict = structured_llm.invoke(prompt_messages)
    
    if not response_dict:
        raise ValueError("Модель вернула пустой результат.")
        
    ai_response = response_dict.get('parsed')
    if ai_response is None:
        raise ValueError(f"Ошибка парсинга ответа модели. Подробности: {response_dict.get('parsing_error')}")
        
    return BatchAnswerEvaluation.model_validate(ai_response)


def analyze_single_answer(question: str, expected_answer: str, user_answer: str) -> SingleAnswerEvaluation:
    """
    Оценка одного ответа. Обертка над batch методом.
    """
    item = {
        "question": question,
        "expected_answer": expected_answer,
        "user_answer": user_answer
    }
    batch_res = analyze_answers_batch([item])
    if batch_res.evaluations:
        return batch_res.evaluations[0]
    raise ValueError("Не удалось получить оценку для ответа.")


def analyze_answers_individually_batch(items: List[Dict[str, str]]) -> List[SingleAnswerEvaluation]:
    """
    Принимает список ответов. Каждый элемент списка должен быть словарем с ключами:
    - "question"
    - "expected_answer"
    - "user_answer"
    
    Использует встроенный в langchain метод batch() для параллельной отправки
    индивидуальных запросов (1 запрос на 1 ответ) к Vertex AI.
    
    Возвращает список объектов SingleAnswerEvaluation.
    """
    if not items:
        return []
        
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", USER_PROMPT_SINGLE)
    ])
    
    llm = get_vertex_llm()
    
    # Принудительный прогрев для авторизации на главном потоке.
    # Это предотвращает гонку за получением OAuth-токена в параллельных потоках,
    # которая часто приводит к ошибкам DNS-резолвинга oauth2.googleapis.com.
    try:
        print("DEBUG: [Warmup] Synchronous warmup on main thread to securely cache OAuth credentials...")
        llm.invoke("warmup")
    except Exception as warmup_err:
        print(f"DEBUG: [Warmup Warning] Warmup failed (ignored): {warmup_err}")

    raw_schema = SingleAnswerEvaluation.model_json_schema()
    flat_json_schema = make_schema_flat(raw_schema)
    
    structured_llm = llm.with_structured_output(flat_json_schema, include_raw=True)
    
    # Готовим список сообщений (inputs) для batch()
    batch_messages = []
    for item in items:
        formatted_messages = prompt.format_messages(
            question=item["question"],
            expected_answer=item["expected_answer"],
            user_answer=item["user_answer"]
        )
        batch_messages.append(formatted_messages)
        
    print(f"DEBUG: Invoking AI Analyzer individually with langchain batch() for {len(items)} items...")
    # langchain's batch() runs these in parallel with safe max_concurrency
    responses = structured_llm.batch(batch_messages, config={"max_concurrency": 5})
    
    evaluations = []
    for idx, response_dict in enumerate(responses):
        if not response_dict:
            raise ValueError(f"Модель вернула пустой результат для элемента {idx}.")
            
        ai_response = response_dict.get('parsed')
        if ai_response is None:
            raise ValueError(f"Ошибка парсинга ответа модели для элемента {idx}. Подробности: {response_dict.get('parsing_error')}")
            
        if isinstance(ai_response, dict):
            ai_response["index"] = idx
            
        eval_item = SingleAnswerEvaluation.model_validate(ai_response)
        evaluations.append(eval_item)
        
    return evaluations

