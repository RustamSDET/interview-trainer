import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    print("🤖 [TEST] Запуск экспресс-теста Vertex AI...")
    from src.services.ai.base import get_vertex_llm
    
    # Инициализируем модель по единому конфигу
    llm = get_vertex_llm()
    
    print("📡 [TEST] Отправка тестового запроса (пинг)...")
    response = llm.invoke("Привет! Ответь одним словом 'Работает', если ты меня слышишь.")
    
    print("\n🎉 === РЕЗУЛЬТАТ ТЕСТА ===")
    print(f"Ответ от Gemini Вертекса: {response.content}")
    print("==========================\n")

except Exception as e:
    print("\n❌ === ТЕСТ ПОВАЛЕН! ОШИБКА ПОДКЛЮЧЕНИЯ ===")
    print(f"Тип ошибки: {type(e).__name__}")
    print(f"Детали ошибки: {e}")
    print("==========================================\n")
