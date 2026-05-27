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
