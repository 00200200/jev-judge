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


def test_pytest_fixture_env_handling(monkeypatch):
    from jev_judge.fixtures import get_default_judge
    # Without key, fixture defaults to mock
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.delenv("JEV_MOCK", raising=False)
    j = get_default_judge()
    assert j.client.is_mock is True

    # With JEV_MOCK=1, fixture forces mock
    monkeypatch.setenv("JEV_MOCK", "1")
    monkeypatch.setenv("TYPESAFE_API_KEY", "real-key")
    j2 = get_default_judge()
    assert j2.client.is_mock is True




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


def test_toxicity_and_pii_assertions():
    judge = Judge(force_mock=True)

    # Clean text should pass
    clean_res = judge.evaluate(
        output="Hello! I would be glad to help you with your account.",
        assertions={"toxicity": "pass", "pii": "pass"},
    )
    assert clean_res.passed is True

    # PII leak (email / api key) should fail
    pii_res = judge.evaluate(
        output="Your reset key is sk-123456 and email is user@example.com",
        assertions={"pii": "pass"},
    )
    assert pii_res.passed is False

    # Toxic output should fail
    toxic_res = judge.evaluate(
        output="You are an idiot and I hate this system",
        assertions={"toxicity": "pass"},
    )
    assert toxic_res.passed is False


def test_client_strict_ci_no_key(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)

    client = JevClient(api_key=None, force_mock=False)
    assert client.strict_api is True
    assert client.is_mock is False

    res = asyncio.run(client.decide_batch(
        state={"output": "test"},
        assertions=[get_evaluator_spec("faithfulness", "pass")],
    ))
    assert len(res) == 1
    assert res[0].passed is False
    assert "refusing silent mock fallback" in (res[0].error or "")


def test_numeric_hallucination_detection():
    judge = Judge(force_mock=True)

    # Output introduces $99 which is not in context
    res = judge.evaluate(
        context="Standard shipping is $4.99 on domestic orders.",
        input="How much is shipping?",
        output="Shipping costs $99 for all orders.",
        assertions={"faithfulness": "pass"},
    )
    assert res.passed is False


def test_mcp_server_tools_and_call():
    from jev_judge.mcp_server import McpServer
    server = McpServer(force_mock=True)
    tools = server.get_tool_definitions()
    tool_names = [t["name"] for t in tools]
    assert "jev_evaluate" in tool_names
    assert "jev_run_suite" in tool_names

    # Test evaluating via MCP tool call
    res = asyncio.run(
        server.handle_tool_call(
            "jev_evaluate",
            {
                "output": "Paris is the capital of France.",
                "context": "Paris is France's capital city.",
                "assertions": {"faithfulness": "pass"}
            }
        )
    )
    assert "content" in res
    assert len(res["content"]) > 0
    payload = json.loads(res["content"][0]["text"])
    assert payload["passed"] is True
    assert "faithfulness" in payload["decisions"]


def test_html_report_generation():
    from jev_judge.reporters.html import generate_html_report
    html_content = generate_html_report(_tiny_suite_results())
    assert "<!DOCTYPE html>" in html_content
    assert "Jev-Judge Test Report" in html_content
    assert "grounded answer" in html_content
    assert "hallucinated plan" in html_content
    assert "badge-pass" in html_content
    assert "badge-fail" in html_content


