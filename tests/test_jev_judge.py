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


import asyncio
import json
import xml.etree.ElementTree as ET
from jev_judge.client import JevClient
from jev_judge.models import DecisionResult, TestCaseResult, TestSuiteResult
from jev_judge.reporters.formats import resolve_output_format
from jev_judge.reporters.github import generate_github_annotations
from jev_judge.reporters.json_report import build_json_report
from jev_judge.reporters.junit import generate_junit_xml


def _tiny_suite_results():
    passing = TestCase(name="grounded answer", output="Warsaw", assertions={"faithfulness": "pass"})
    failing = TestCase(name="hallucinated plan", output="$5 student plan", assertions={"faithfulness": "pass"})
    ok = DecisionResult(
        assertion_name="faithfulness",
        passed=True,
        decision_type=DecisionType.NOUL,
        value=True,
        probability=0.96,
        threshold=0.80,
        latency_ms=12.0,
        cost_usd=0.00004,
    )
    bad = DecisionResult(
        assertion_name="faithfulness",
        passed=False,
        decision_type=DecisionType.NOUL,
        value=False,
        probability=0.21,
        threshold=0.80,
        latency_ms=11.0,
        cost_usd=0.00004,
        reason="Output is not grounded in context",
    )
    return [
        TestSuiteResult(
            suite_name="tiny",
            file_path="evals/tiny.yaml",
            total_tests=2,
            passed_tests=1,
            failed_tests=1,
            duration_ms=40.0,
            total_cost_usd=0.00008,
            results=[
                TestCaseResult(
                    test_case=passing,
                    passed=True,
                    decisions={"faithfulness": ok},
                    duration_ms=20.0,
                    total_cost_usd=0.00004,
                ),
                TestCaseResult(
                    test_case=failing,
                    passed=False,
                    decisions={"faithfulness": bad},
                    duration_ms=20.0,
                    total_cost_usd=0.00004,
                ),
            ],
        )
    ]


def test_json_format_is_json_loads_parseable():
    payload = json.loads(json.dumps(build_json_report(_tiny_suite_results())))
    assert payload["totals"]["suites"] == 1
    assert payload["totals"]["cases"] == 2
    assert payload["totals"]["failed"] == 1
    assert payload["totals"]["passed"] == 1
    assert len(payload["suites"]) == 1
    assert len(payload["cases"]) == 2
    assert len(payload["decisions"]) == 2
    assert payload["suites"][0]["file_path"] == "evals/tiny.yaml"
    assert payload["cases"][1]["passed"] is False
    assert payload["decisions"][1]["assertion_name"] == "faithfulness"


def test_junit_format_parses_and_marks_failures():
    xml_text = generate_junit_xml(_tiny_suite_results())
    root = ET.fromstring(xml_text)
    assert root.tag == "testsuites"
    assert root.attrib["tests"] == "2"
    assert root.attrib["failures"] == "1"
    cases = list(root.iter("testcase"))
    assert len(cases) == 2
    failures = list(root.iter("failure"))
    assert len(failures) == 1
    assert "faithfulness" in failures[0].attrib["message"]
    assert failures[0].attrib["message"] == failures[0].text


def test_github_format_emits_error_for_failed_case():
    text = generate_github_annotations(_tiny_suite_results())
    assert "::error file=evals/tiny.yaml,line=1,title=hallucinated plan::" in text
    assert "grounded answer" not in text


def test_format_flag_wins_over_markdown_and_github_actions():
    assert resolve_output_format("json", markdown_alias=True, github_actions="true") == "json"
    assert resolve_output_format(None, markdown_alias=True, github_actions="true") == "markdown"
    assert resolve_output_format(None, markdown_alias=False, github_actions="true") == "markdown"
    assert resolve_output_format(None, markdown_alias=False, github_actions="") == "pretty"


def test_runner_filter_pattern():
    from jev_judge.models import TestSuite
    suite = TestSuite(
        name="filter_suite",
        tests=[
            TestCase(name="Grounded Answer: Return Policy", output="policy", assertions={"faithfulness": "pass"}),
            TestCase(name="Detected Hallucination: Free Shipping", output="free", assertions={"faithfulness": "pass"}),
            TestCase(name="Technical Spec Query", output="spec", assertions={"faithfulness": "pass"}),
        ],
    )
    runner = TestRunner(client=JevClient(force_mock=True), filter_pattern="Hallucination")
    res = asyncio.run(runner.run_suite(suite))
    assert res.total_tests == 1
    assert res.results[0].test_case.name == "Detected Hallucination: Free Shipping"
