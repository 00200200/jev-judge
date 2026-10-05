"""Markdown reporter for GitHub Actions and pull request summaries."""

from typing import List

from jev_judge.models import TestSuiteResult


def generate_markdown_report(suite_results: List[TestSuiteResult]) -> str:
    """Generate GitHub-compatible Markdown summary."""
    total_tests = sum(s.total_tests for s in suite_results)
    passed_tests = sum(s.passed_tests for s in suite_results)
    failed_tests = sum(s.failed_tests for s in suite_results)
    total_duration_ms = sum(s.duration_ms for s in suite_results)
    total_cost_usd = sum(s.total_cost_usd for s in suite_results)
    traditional_cost_usd = total_tests * 0.025

    status_badge = "✅ **PASSED**" if failed_tests == 0 else "❌ **FAILED**"

    lines = [
        f"## ⚡ Jev-Judge Evaluation Report: {status_badge}",
        "",
        f"- **Results**: `{passed_tests}/{total_tests}` tests passed (`{failed_tests}` failed)",
        f"- **Latency**: `{total_duration_ms:.0f}ms` total execution time",
        f"- **Cost**: `${total_cost_usd:.5f}` (vs ~`${traditional_cost_usd:.3f}` with traditional LLM judge)",
        "",
        "| Suite / Test Case | Status | Duration | Assertions (Prob / Thresh) | Details |",
        "| :--- | :---: | :---: | :--- | :--- |",
    ]

    for suite in suite_results:
        suite_title = suite.file_path or suite.suite_name
        lines.append(f"| **`{suite_title}`** | - | `{suite.duration_ms:.0f}ms` | - | - |")

        for tr in suite.results:
            tc = tr.test_case
            status_icon = "✅ Pass" if tr.passed else "❌ Fail"

            assertions_summary = []
            details_list = []
            for a_name, dec in tr.decisions.items():
                assertions_summary.append(f"`{a_name}` ({dec.probability:.2f}/{dec.threshold:.2f})")
                if not dec.passed:
                    err = dec.error or dec.reason or "Failed"
                    details_list.append(f"**{a_name}**: {err}")

            details_str = "<br>".join(details_list) if details_list else "All criteria passed"
            assertions_str = "<br>".join(assertions_summary)

            lines.append(
                f"| &nbsp;&nbsp;↳ {tc.name} | {status_icon} | `{tr.duration_ms:.0f}ms` | {assertions_str} | {details_str} |"
            )

    lines.append("")
    lines.append(
        "> *Powered by [TypeSafe Jev](https://typesafe.ai) via [jev-judge](https://github.com/your-org/jev-judge)*"
    )
    return "\n".join(lines)
