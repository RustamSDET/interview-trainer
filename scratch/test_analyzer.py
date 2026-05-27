import json
from src.services.ai.analyzer import analyze_answers_batch

def main():
    print("Testing AI Answer Analyzer Batch Evaluation...")
    
    test_items = [
        {
            "question": "How do you manage flaky tests in pytest?",
            "expected_answer": "Use retries via pytest-rerunfailures, isolate test state, mock external APIs, and run tests in clean containers.",
            "user_answer": "We usually rerun flaky tests using pytest rerunfailures plugin. Also, we try to isolate our test databases and mock our external HTTP calls to keep them stable."
        },
        {
            "question": "What is the purpose of fixtures in pytest?",
            "expected_answer": "Fixtures provide a fixed baseline so tests can run reliably. They allow setup/teardown code and dependency injection.",
            "user_answer": "Fixtures are just some random variables that you can use to output logs when tests fail. They don't do anything else."
        },
        {
            "question": "What does the -s flag do in pytest?",
            "expected_answer": "It disables stdout/stderr capturing, allowing standard output to be displayed immediately in the terminal during execution.",
            "user_answer": "It shows print statements in the console."
        }
    ]
    
    print(f"Sending a batch of {len(test_items)} test answers to AI...")
    try:
        result = analyze_answers_batch(test_items)
        print("\n=== Evaluation Succeeded! ===")
        for eval_item in result.evaluations:
            print(f"\n[Answer #{eval_item.index}]")
            print(f"  Score: {eval_item.score}/10")
            print(f"  Summary: {eval_item.summary}")
            print(f"  What was GOOD: {eval_item.what_was_good}")
            print(f"  What was BAD/MISSING: {eval_item.what_was_bad_or_missing}")
            print(f"  Verdict: {eval_item.verdict}")
            print("  Criteria scores:")
            for crit in eval_item.criteria:
                print(f"    - {crit.criterion}: {crit.score}/10 -> {crit.explanation}")
    except Exception as e:
        print(f"\n❌ Evaluation Failed: {e}")

if __name__ == "__main__":
    main()
