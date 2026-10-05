"""JUnit XML reporter (stdlib xml.etree, no extra deps)."""

import xml.etree.ElementTree as ET
from typing import List

from jev_judge.models import TestCaseResult, TestSuiteResult


def _failure_message(result: TestCaseResult) -> str:
    parts = []
    for name, decision in result.decisions.items():
        if decision.passed:
            continue
        detail = decision.error or decision.reason or "Assertion threshold not met"
        parts.append(f"{name}: {detail}")
    return "; ".join(parts) if parts else "Test case failed"


def generate_junit_xml(suite_results: List[TestSuiteResult]) -> str:
    """Serialize suite results as JUnit XML with failures as <failure message=>."""
    total_tests = sum(s.total_tests for s in suite_results)
    total_failures = sum(s.failed_tests for s in suite_results)
    total_time = sum(s.duration_ms for s in suite_results) / 1000.0

    root = ET.Element("testsuites")
    root.set("tests", str(total_tests))
    root.set("failures", str(total_failures))
    root.set("time", f"{total_time:.3f}")

    for suite in suite_results:
        suite_el = ET.SubElement(root, "testsuite")
        suite_el.set("name", suite.suite_name)
        suite_el.set("tests", str(suite.total_tests))
        suite_el.set("failures", str(suite.failed_tests))
        suite_el.set("time", f"{suite.duration_ms / 1000.0:.3f}")
        if suite.file_path:
            suite_el.set("file", suite.file_path)

        for result in suite.results:
            case_el = ET.SubElement(suite_el, "testcase")
            case_el.set("name", result.test_case.name)
            case_el.set("classname", suite.suite_name)
            case_el.set("time", f"{result.duration_ms / 1000.0:.3f}")
            if not result.passed:
                failure_el = ET.SubElement(case_el, "failure")
                message = _failure_message(result)
                failure_el.set("message", message)
                failure_el.text = message

    return ET.tostring(root, encoding="unicode")
