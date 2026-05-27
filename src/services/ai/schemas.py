from typing import List
from pydantic import BaseModel, Field

# ==========================================
# --- Schemas for Question Generation ---
# ==========================================

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


# ==========================================
# --- Schemas for Answer Evaluation ---
# ==========================================

class CriterionEvaluation(BaseModel):
    """Оценка по конкретному критерию"""
    criterion: str = Field(
        ...,
        description="Название критерия (например, 'Корректность', 'Полнота', 'Ясность', 'Техническая точность')"
    )
    score: int = Field(
        ...,
        description="Оценка по этому критерию от 1 до 10"
    )
    explanation: str = Field(
        ...,
        description="Лаконичное объяснение оценки на русском языке (1-2 предложения)"
    )


class SingleAnswerEvaluation(BaseModel):
    """Схема оценки одного ответа кандидата"""
    index: int = Field(
        ...,
        description="Индекс ответа в исходном списке (0-indexed)"
    )
    score: int = Field(
        ...,
        description="Общая оценка ответа от 1 до 10"
    )
    criteria: List[CriterionEvaluation] = Field(
        ...,
        description="Оценки по различным критериям (Корректность, Полнота, Ясность, Техническая точность)"
    )
    what_was_good: str = Field(
        ...,
        description="Что было хорошо в ответе (сильные стороны, верные технические факты)"
    )
    what_was_bad_or_missing: str = Field(
        ...,
        description="Что было плохо или чего не хватило (ошибки, неточности, упущенные ключевые моменты)"
    )
    verdict: str = Field(
        ...,
        description="Общий конструктивный вердикт и рекомендации по улучшению на русском языке"
    )
    summary: str = Field(
        ...,
        description="Краткое лаконичное резюме ответа (одно предложение)"
    )


class BatchAnswerEvaluation(BaseModel):
    """Схема списка оценок ответов для пакетного анализа"""
    evaluations: List[SingleAnswerEvaluation] = Field(
        ...,
        description="Список результатов оценки для каждого переданного ответа"
    )
