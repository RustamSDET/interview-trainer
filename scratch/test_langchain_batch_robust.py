import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.services.ai.analyzer import analyze_answers_individually_batch

def test_langchain_batch_evaluation():
    print("🚀 Running robust test for LangChain .batch() evaluation...")
    
    # 5 realistic question-answer pairs for SDET interview
    test_items = [
        {
            "question": "Как устроен жизненный цикл бина (Bean Lifecycle) в Spring?",
            "expected_answer": "Инстанцирование, заполнение свойств, вызов BeanNameAware, BeanFactoryAware, предобработка BeanPostProcessor, @PostConstruct, AfterPropertiesSet, custom init, постобработка BeanPostProcessor. При уничтожении: @PreDestroy, DisposableBean, custom destroy.",
            "user_answer": "Ну сначала спринг создает объект бина, потом внедряет зависимости через конструкторы или сеттеры. Потом вызываются всякие методы жизненного цикла типа PostConstruct, а в конце бин уничтожается через PreDestroy."
        },
        {
            "question": "В чем разница между @Component, @Service, @Repository в Spring?",
            "expected_answer": "@Component — общая аннотация для управляемых бинов. @Service обозначает бизнес-логику. @Repository — для уровня доступа к данным, автоматически включает перевод исключений БД в Spring DataAccessException.",
            "user_answer": "Все эти аннотации создают бины. Но Service мы пишем над классами с бизнес-логикой, а Repository — над дао-классами для работы с базой данных."
        },
        {
            "question": "Что такое транзакционность в Spring и как работает @Transactional?",
            "expected_answer": "@Transactional управляет транзакциями через AOP-прокси. Он перехватывает вызов, открывает транзакцию в начале и фиксирует (commit) в конце или откатывает (rollback) в случае RuntimeException.",
            "user_answer": "Она открывает транзакцию в базе данных перед началом метода и закрывает ее в конце, чтобы все изменения применились вместе."
        },
        {
            "question": "Как работает механизм кэширования в Spring Cache?",
            "expected_answer": "Использует прокси для перехвата вызовов методов, проверяет наличие результата в кеше по ключу. Если есть — возвращает, если нет — выполняет метод и сохраняет результат в кеш.",
            "user_answer": "Ну мы ставим аннотацию Cacheable над методом, и спринг сохраняет возвращаемый результат в памяти, чтобы в следующий раз не вычислять заново."
        },
        {
            "question": "Как настроить глобальный обработчик исключений в Spring Boot?",
            "expected_answer": "Создать класс с аннотацией @ControllerAdvice или @RestControllerAdvice и объявить в нем методы с аннотацией @ExceptionHandler для обработки конкретных классов исключений.",
            "user_answer": "Мы делаем специальный класс, вешаем над ним ControllerAdvice, и пишем методы с ExceptionHandler для нужных ошибок."
        }
    ]

    print(f"📦 Prepared {len(test_items)} SDET-themed questions and answers for parallel batch analysis.")
    print("⏳ Invoking analyze_answers_individually_batch (parallel execution)...")
    
    start_time = time.time()
    try:
        results = analyze_answers_individually_batch(test_items)
        elapsed = time.time() - start_time
        
        print(f"\n🎉 Test completed successfully in {elapsed:.2f} seconds!")
        print(f"Received {len(results)} individual evaluations:")
        
        for idx, r in enumerate(results):
            print(f"\n📝 Question {idx+1}: {test_items[idx]['question'][:50]}...")
            print(f"   ⭐ Score: {r.score}/10")
            print(f"   🔍 What was good: {r.what_was_good}")
            print(f"   ⚠️ What was bad or missing: {r.what_was_bad_or_missing}")
            print(f"   💡 Verdict: {r.verdict}")
            print(f"   📄 Summary: {r.summary}")
            
        assert len(results) == len(test_items), "Number of results should match number of input items"
        assert all(1 <= r.score <= 10 for r in results), "All scores should be between 1 and 10"
        print("\n✅ All assertions passed perfectly!")
        
    except Exception as e:
        print(f"\n❌ Test FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_langchain_batch_evaluation()
