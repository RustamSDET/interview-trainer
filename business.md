# 🏛️ Архитектура слоев: Бизнес-логика, STT/TTS Сервисы и Чистый UI

Этот документ описывает чистый архитектурный паттерн для расширения тренажера функциями воспроизведения вопросов (TTS), распознавания ответов (STT) и автоматической ИИ-оценки (LLM). Архитектура построена на принципах разделения ответственности (**Separation of Concerns**) и слабой связанности (**Loose Coupling**).

---

## 🗺️ Структура каталогов и назначение файлов

Чтобы избежать "толстых" файлов-монолитов и лапшичного кода, все внешние интеграции выносятся в сервисный слой, а логика координации процессов — в бизнес-слой. Слой представления (Streamlit UI) остается тонким и отвечает только за отрисовку интерфейса.

```
src/
├── services/
│   ├── __init__.py
│   ├── tts/                  # Модуль озвучки (Text-to-Speech)
│   │   ├── __init__.py
│   │   ├── base.py           # Абстрактный интерфейс TTS
│   │   ├── gtts_service.py   # Реализация через gTTS (Google)
│   │   └── factory.py        # Фабрика для выбора провайдера TTS
│   ├── stt/                  # Модуль распознавания (Speech-to-Text)
│   │   ├── __init__.py
│   │   ├── base.py           # Абстрактный интерфейс STT
│   │   ├── whisper_service.py# Локальный faster-whisper (с Singleton)
│   │   └── factory.py        # Фабрика для выбора провайдера STT
│   └── ai/                   # Модуль AI-оценки (LLM Evaluator)
│       ├── __init__.py
│       ├── evaluator.py      # Структурированная оценка ответов (Gemini)
│       └── prompts.py        # Хранилище промптов
└── business/
    ├── __init__.py
    ├── randomizer.py         # Выбор случайных вопросов (уже готов)
    └── training_manager.py   # Оркестратор: Связующее звено между UI, STT, TTS и LLM
```

---

## 🛠️ Детальное проектирование компонентов

### 1. Модуль TTS (Озвучка вопросов)
Определяет абстрактный интерфейс для синтеза речи, чтобы при желании можно было легко переключиться с облачного Google TTS на офлайновый `pyttsx3` или премиальный `ElevenLabs`.

#### **`src/services/tts/base.py`**
```python
from abc import ABC, abstractmethod
from pathlib import Path

class BaseTTSService(ABC):
    @abstractmethod
    def synthesize(self, text: str, output_path: Path) -> Path:
        """
        Синтезирует текст в аудиофайл (WAV/MP3) и возвращает путь к нему.
        """
        pass
```

#### **`src/services/tts/gtts_service.py`**
```python
from pathlib import Path
from gtts import gTTS
from src.services.tts.base import BaseTTSService

class GoogleTTSService(BaseTTSService):
    def synthesize(self, text: str, output_path: Path) -> Path:
        """Реализация с использованием библиотеки gTTS (Google TTS)"""
        tts = gTTS(text=text, lang="ru")
        tts.save(str(output_path))
        return output_path
```

---

### 2. Модуль STT (Распознавание речи)
Инициализация локальных нейросетей (таких как `faster-whisper`) требует больших ресурсов и времени. Для предотвращения повторной загрузки весов модели при каждом обновлении страницы Streamlit, используется паттерн **Singleton**.

#### **`src/services/stt/base.py`**
```python
from abc import ABC, abstractmethod

class BaseSTTService(ABC):
    @abstractmethod
    def transcribe(self, audio_bytes: bytes) -> str:
        """
        Преобразует бинарный поток аудиоданных в очищенный текст.
        """
        pass
```

#### **`src/services/stt/whisper_service.py`**
```python
import io
from faster_whisper import WhisperModel
from src.services.stt.base import BaseSTTService

class LocalWhisperService(BaseSTTService):
    _model_instance = None  # Кэшируемый инстанс нейросети (Singleton)

    def __init__(self, model_size: str = "base"):
        if LocalWhisperService._model_instance is None:
            # Инициализация тяжелой модели происходит строго ОДИН раз
            LocalWhisperService._model_instance = WhisperModel(
                model_size, 
                device="cpu",  # Или "cuda" при наличии GPU
                compute_type="int8"
            )
        self.model = LocalWhisperService._model_instance

    def transcribe(self, audio_bytes: bytes) -> str:
        audio_file = io.BytesIO(audio_bytes)
        segments, info = self.model.transcribe(audio_file, beam_size=5)
        return " ".join([segment.text for segment in segments])
```

---

### 3. Модуль AI-оценки (LLM-анализ)
Для получения предсказуемой оценки от Gemini API используется механизм **Structured Outputs**. Описание структуры ответа задается через Pydantic-модели, гарантируя, что ИИ вернет строго валидный JSON.

#### **`src/services/ai/evaluator.py`**
```python
from pydantic import BaseModel, Field
from google.cloud import aiplatform # Или vertexai
from src.services.ai.prompts import EVALUATION_SYSTEM_PROMPT

class EvaluationSchema(BaseModel):
    score: int = Field(description="Оценка устного ответа кандидата от 1 до 10")
    strengths: list[str] = Field(description="Сильные стороны ответа, ключевые упомянутые термины")
    weaknesses: list[str] = Field(description="Слабые стороны, фактические ошибки или упущенные важные концепты")
    recommendations: str = Field(description="Советы по улучшению ответа и полезные ссылки")

class AIEvaluator:
    def __init__(self):
        # Настройка и инициализация клиента Vertex AI/Gemini
        pass

    def evaluate_user_response(self, question: str, expected_answer: str, transcribed_text: str) -> EvaluationSchema:
        """Отправляет структурированный запрос к Gemini для оценки ответа"""
        # Логика сборки промпта и вызова LLM
        # return evaluation_pydantic_object
        pass
```

---

### 4. Бизнес-слой (Оркестратор процессов)
**`TrainingManager`** объединяет разрозненные сервисы озвучки, распознавания и оценки в один сквозной пайплайн. Это ключевой файл бизнес-логики, который полностью изолирует UI от баз данных, нейросетей и внешних API.

#### **`src/business/training_manager.py`**
```python
from pathlib import Path
from src.database.repository import create_answer_history
from src.services.stt.whisper_service import LocalWhisperService
from src.services.ai.evaluator import AIEvaluator

class TrainingManager:
    def __init__(self):
        self.stt_service = LocalWhisperService()
        self.ai_evaluator = AIEvaluator()

    def process_and_evaluate_answer(
        self, 
        db_session, 
        session_id: int, 
        question_id: int, 
        question_text: str, 
        expected_answer: str, 
        audio_bytes: bytes
    ) -> dict:
        """
        Координирует сквозной процесс обработки ответа:
        1. Распознает аудио-поток в текст (STT)
        2. Запрашивает ИИ-оценку на основе ожидаемого ответа (LLM)
        3. Записывает детальные результаты в базу данных SQLite (DB)
        """
        # Шаг 1: Распознавание аудиозаписи
        transcribed_text = self.stt_service.transcribe(audio_bytes)
        
        # Шаг 2: Получение ИИ-анализа и оценки
        eval_result = self.ai_evaluator.evaluate_user_response(
            question=question_text,
            expected_answer=expected_answer,
            transcribed_text=transcribed_text
        )
        
        # Шаг 3: Сохранение результатов в историю (SQLite)
        db_history_record = create_answer_history(
            db=db_session,
            session_id=session_id,
            question_id=question_id,
            confidence_score=eval_result.score,
            transcribed_text=transcribed_text,
            evaluation_status="Great" if eval_result.score >= 8 else "Good" if eval_result.score >= 5 else "Bad"
        )
        
        # Возвращаем форматированный результат для мгновенного рендеринга в UI
        return {
            "transcribed_text": transcribed_text,
            "score": eval_result.score,
            "strengths": eval_result.strengths,
            "weaknesses": eval_result.weaknesses,
            "recommendations": eval_result.recommendations,
            "record_id": db_history_record.id
        }
```

---

## 🎨 Тонкий UI слой (Чистый рендеринг)

Благодаря внедрению оркестратора, код представления в файле `training.py` остается невероятно лаконичным и легким для чтения. Он не содержит тяжелых импортов или логики сохранения, а лишь рендерит Streamlit-виджеты.

#### **`src/web/views/training.py` (Пример чистой интеграции)**
```python
import streamlit as st
from st_custom_audio_recorder import audio_recorder  # Кастомный веб-компонент записи аудио
from src.business.training_manager import TrainingManager
from src.database.connection import get_db_session

# Инициализируем оркестратор в сессии Streamlit один раз
if "training_manager" not in st.session_state:
    st.session_state.training_manager = TrainingManager()

def render_training():
    st.markdown("### 🥋 Тренировочный лагерь")
    
    # 1. Получение текущего активного вопроса
    q = st.session_state.sandbox_questions[st.session_state.sandbox_current_index]
    st.info(q['question_text'])
    
    # 2. Озвучка вопроса через TTS
    audio_cache_path = Path(f"data/tts_cache/q_{q['id']}.wav")
    if not audio_cache_path.exists():
        # Синтезируем один раз и сохраняем в кэш на диске
        tts_service.synthesize(q['question_text'], audio_cache_path)
    
    st.audio(str(audio_cache_path), format="audio/wav")
    
    # 3. Кнопка записи устного ответа в браузере
    st.write("🎙️ Запишите ваш устный ответ:")
    audio_bytes = audio_recorder()
    
    if audio_bytes:
        if st.button("🚀 Отправить ответ на проверку AI"):
            with st.spinner("Локальная транскрибация голоса и оценка AI..."):
                with get_db_session() as db_session:
                    # Всего ОДИН вызов бизнес-логики делает всё!
                    result = st.session_state.training_manager.process_and_evaluate_answer(
                        db_session=db_session,
                        session_id=st.session_state.sandbox_session_id,
                        question_id=q["id"],
                        question_text=q["question_text"],
                        expected_answer=q["expected_answer"],
                        audio_bytes=audio_bytes
                    )
                
                # Рендерим результаты проверки
                st.success("✅ Ответ успешно проанализирован!")
                st.metric("ИИ Оценка", f"{result['score']} / 10")
                st.write(f"**Ваш распознанный ответ:** {result['transcribed_text']}")
                
                with st.expander("📊 Подробный разбор"):
                    st.write("**Сильные стороны:**")
                    for s in result["strengths"]:
                        st.write(f"- {s}")
                    st.write("**Что нужно доработать:**")
                    for w in result["weaknesses"]:
                        st.write(f"- {w}")
                    st.write(f"**Рекомендации:** {result['recommendations']}")
```

---

## 💎 Преимущества такого подхода
1. **Отсутствие монолитов**: Ни один файл не превышает 100-150 строк кода. Код легко дебажить и поддерживать.
2. **Простота тестирования**: Все функции модулей `tts`, `stt` и `ai_evaluator` можно покрыть unit-тестами (например, через `pytest`) в консоли без запуска Streamlit и браузера.
3. **Безопасность транзакций**: Работа с SQLite вынесена на уровень оркестратора, гарантируя сохранение оценок и истории ответов перед ререндерингом интерфейса.
