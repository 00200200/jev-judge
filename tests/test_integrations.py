"""Tests for LangChain and LlamaIndex integrations."""

import asyncio
import pytest
from jev_judge.integrations.langchain import JevLangChainEvaluator, JevJudgeCallbackHandler
from jev_judge.integrations.llamaindex import JevLlamaIndexEvaluator, JevEvaluationResult


def test_langchain_evaluator_sync():
    evaluator = JevLangChainEvaluator(force_mock=True)
    res = evaluator.evaluate_strings(
        prediction="Paris is the capital of France.",
        input="What is France's capital?",
        context="Paris is France's capital city.",
    )
    assert res["passed"] is True
    assert res["score"] == 1.0
    assert "faithfulness" in res["scores"]
    assert res["duration_ms"] > 0


def test_langchain_evaluator_async():
    evaluator = JevLangChainEvaluator(force_mock=True)
    res = asyncio.run(
        evaluator.aevaluate_strings(
            prediction="Paris is the capital of France.",
            input="What is France's capital?",
            context="Paris is France's capital city.",
        )
    )
    assert res["passed"] is True
    assert res["score"] == 1.0


def test_langchain_callback_handler():
    handler = JevJudgeCallbackHandler(force_mock=True)

    class MockGeneration:
        text = "Hello, I am a friendly assistant."

    class MockResponse:
        generations = [[MockGeneration()]]

    handler.on_llm_end(MockResponse())
    assert len(handler.evaluation_results) == 1
    assert handler.evaluation_results[0].passed is True


def test_llamaindex_evaluator_sync():
    evaluator = JevLlamaIndexEvaluator(force_mock=True)
    res: JevEvaluationResult = evaluator.evaluate(
        query="What is France's capital?",
        response="Paris is the capital of France.",
        contexts=["Paris is France's capital city."],
    )
    assert res.passing is True
    assert res.score == 1.0
    assert "faithfulness: PASS" in res.feedback


def test_llamaindex_evaluator_async():
    evaluator = JevLlamaIndexEvaluator(force_mock=True)
    res: JevEvaluationResult = asyncio.run(
        evaluator.aevaluate(
            query="What is France's capital?",
            response="Paris is the capital of France.",
            contexts=["Paris is France's capital city."],
        )
    )
    assert res.passing is True
    assert res.score == 1.0


def test_llamaindex_evaluator_with_mock_response_object():
    class MockNode:
        def get_content(self):
            return "Paris is France's capital city."

    class MockSourceNode:
        node = MockNode()

    class MockQueryResponse:
        response = "Paris is the capital of France."
        source_nodes = [MockSourceNode()]

    evaluator = JevLlamaIndexEvaluator(force_mock=True)
    res = evaluator.evaluate(
        query="What is France's capital?",
        response=MockQueryResponse(),
    )
    assert res.passing is True
    assert "Paris" in res.response
