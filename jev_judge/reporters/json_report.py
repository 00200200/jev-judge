"""JSON reporter for machine-readable CI artifacts."""

from typing import Any, Dict, List

from jev_judge.models import TestSuiteResult


def build_json_report(suite_results: List[TestSuiteResult]) -> Dict[str, Any]:
    """Build a JSON-serializable document with suites, cases, decisions, and totals."""
    suites = [s.model_dump(mode="json") for s in suite_results]
    cases: List[Dict[str, Any]] = []
    decisions: List[Dict[str, Any]] = []

    for suite in suite_results:
        for result in suite.results:
            case_dump = result.model_dump(mode="json")
            case_dump["suite_name"] = suite.suite_name
            case_dump["file_path"] = suite.file_path
            cases.append(case_dump)
            for decision in result.decisions.values():
                decision_dump = decision.model_dump(mode="json")
                decision_dump["suite_name"] = suite.suite_name
                decision_dump["case_name"] = result.test_case.name
                decision_dump["file_path"] = suite.file_path
                decisions.append(decision_dump)

    totals = {
        "suites": len(suite_results),
        "cases": sum(s.total_tests for s in suite_results),
        "passed": sum(s.passed_tests for s in suite_results),
        "failed": sum(s.failed_tests for s in suite_results),
        "duration_ms": sum(s.duration_ms for s in suite_results),
        "total_cost_usd": sum(s.total_cost_usd for s in suite_results),
    }
    return {
        "suites": suites,
        "cases": cases,
        "decisions": decisions,
        "totals": totals,
    }
