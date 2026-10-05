"""Unit tests for jev-judge core logic and CLI."""

import os
import tempfile
import pytest
from jev_judge import Judge, TestCase
from jev_judge.evaluators import get_evaluator_spec, evaluate_decision_verdict
from jev_judge.models import DecisionType, AssertionType
from jev_judge.runner import TestRunner


def test_evaluator_spec_mapping():
    # Faithfulness
    spec = get_evaluator_spec("faithfulness", "pass", default_threshold=0.8)
    assert spec.assertion_type == AssertionType.FAITHFULNESS
    assert spec.decision_type == DecisionType.NOUL
    assert spec.threshold == 0.8
    assert spec.expected is True

    # Hallucination
    h_spec = get_evaluator_spec("hallucination", False)
    assert h_spec.assertion_type == AssertionType.HALLUCINATION
    assert h_spec.expected is False

    # Relevance Score
    r_spec = get_evaluator_spec("relevance", 4)
    assert r_spec.assertion_type == AssertionType.RELEVANCE
    assert r_spec.decision_type == DecisionType.SCORE
    assert r_spec.expected == 4


def test_decision_verdict_noul():
    spec = get_evaluator_spec("faithfulness", "pass", default_threshold=0.75)
    passed, reason = evaluate_decision_verdict(spec, True, 0.92)
    assert passed is True
    assert reason is None

    # Below threshold
    passed, reason = evaluate_decision_verdict(spec, True, 0.60)
    assert passed is False
    assert "fell below required threshold" in reason


def test_programmatic_judge():
    judge = Judge(force_mock=True)
    res = judge.evaluate(
        name="Unit Test Case",
        input="Hello",
        context="Context fact",
        output="Hello fact",
        assertions={"faithfulness": "pass", "relevance": 5},
    )
    assert res.passed is True
    assert len(res.decisions) == 2
    assert res.duration_ms > 0
    assert res.total_cost_usd > 0


def test_jsonl_suite_loading():
    runner = TestRunner()
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
        f.write('{"name": "Row 1", "output": "Sample output", "assertions": {"faithfulness": "pass"}}\n')
        f.write('{"name": "Row 2", "output": "Another output", "assertions": {"safety": "pass"}}\n')
        tmp_name = f.name

    try:
        suite = runner.load_suite_from_file(tmp_name)
        assert len(suite.tests) == 2
        assert suite.tests[0].name == "Row 1"
        assert suite.tests[1].name == "Row 2"
    finally:
        os.remove(tmp_name)


def test_csv_suite_loading():
    runner = TestRunner()
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
        f.write("name,input,context,output\n")
        f.write("Test CSV,Question,Context,Answer\n")
        tmp_name = f.name

    try:
        suite = runner.load_suite_from_file(tmp_name)
        assert len(suite.tests) == 1
        assert suite.tests[0].name == "Test CSV"
        assert suite.tests[0].output == "Answer"
    finally:
        os.remove(tmp_name)


def test_pytest_fixture(jev_judge):
    assert isinstance(jev_judge, Judge)
    res = jev_judge.evaluate(
        output="Grounded fact",
        context="Grounded fact",
        assertions={"faithfulness": "pass"},
    )
    assert res.passed is True
