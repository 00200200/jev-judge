"""Demonstration of using jev-judge as a Python library."""

from jev_judge import Judge

# Initialize Judge (automatically reads TYPESAFE_API_KEY or runs in zero-friction mock mode)
judge = Judge()

print("Evaluating RAG Answer...")
result = judge.evaluate(
    name="Customer Support Query",
    input="Can I return an item after 14 days?",
    context="Our store allows returns within 30 days of purchase with proof of receipt.",
    output="Yes, you have 30 days to return your purchase as long as you provide a receipt.",
    assertions={
        "faithfulness": "pass",
        "relevance": 5,
        "hallucination": False,
    }
)

print(f"Overall Passed: {result.passed}")
print(f"Execution Time: {result.duration_ms}ms")
print(f"Total Cost: ${result.total_cost_usd:.6f}")
for name, decision in result.decisions.items():
    print(f"  • {name}: passed={decision.passed}, probability={decision.probability:.2f}")
