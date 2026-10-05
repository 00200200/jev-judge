"""GitHub Actions workflow-command annotations for failed cases."""

from typing import List

from jev_judge.models import TestSuiteResult


def _escape_data(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_property(value: str) -> str:
    return (
        _escape_data(value)
        .replace(":", "%3A")
        .replace(",", "%2C")
    )


def generate_github_annotations(suite_results: List[TestSuiteResult]) -> str:
    """Emit ::error title=...:: lines for failed cases (file= YAML path)."""
    lines: List[str] = []
    for suite in suite_results:
        file_path = suite.file_path or suite.suite_name
        for result in suite.results:
            if result.passed:
                continue
            details = []
            for name, decision in result.decisions.items():
                if decision.passed:
                    continue
                detail = decision.error or decision.reason or "Assertion threshold not met"
                details.append(f"{name}: {detail}")
            message = "; ".join(details) if details else "Test case failed"
            title = _escape_property(result.test_case.name)
            file_prop = _escape_property(file_path)
            lines.append(
                f"::error file={file_prop},line=1,title={title}::{_escape_data(message)}"
            )
    return "\n".join(lines)
