import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.database.connection import get_db_session
from src.services.ai.analyzer import analyze_answers_batch

def test_batch():
    print("Testing batch AI analyzer...")
    items = [
        {
            "question": "Что такое инкапсуляция в ООП?",
            "expected_answer": "Инкапсуляция — это сокрытие внутреннего состояния и реализации объекта и предоставление доступа через публичный интерфейс.",
            "user_answer": "Ну это типа когда мы скрываем данные внутри класса и делаем методы геттеры и сеттеры."
        },
        {
            "question": "Зачем нужен полиморфизм?",
            "expected_answer": "Полиморфизм позволяет использовать единый интерфейс для работы с объектами разных типов, что повышает гибкость кода.",
            "user_answer": "Чтобы вызывать один и тот же метод у разных наследников."
        }
    ]
    
    try:
        res = analyze_answers_batch(items)
        print("Success!")
        print(f"Evaluations count: {len(res.evaluations)}")
        for ev in res.evaluations:
            print(f"Index: {ev.index}, Score: {ev.score}, Summary: {ev.summary}")
    except Exception as e:
        print(f"FAILED with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_batch()
