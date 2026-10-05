"""Rich terminal reporter with Vitest/Jest style output."""

import os
from typing import List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from jev_judge.models import TestSuiteResult


def print_banner(console: Console, is_mock: bool):
    title_text = Text()
    title_text.append("⚡ Jev-Judge", style="bold cyan")
    title_text.append(" v0.1.0 — Fast CI/CD Evaluator for LLM & RAG", style="dim")
    if is_mock:
        title_text.append(" [MOCK MODE / ZERO CONFIG]", style="bold yellow")
    else:
        title_text.append(" [TypeSafe Jev Engine]", style="bold green")

    console.print(Panel(title_text, border_style="cyan", padding=(0, 1)))


def print_suite_results(console: Console, suite_results: List[TestSuiteResult]):
    total_suites = len(suite_results)
    passed_suites = sum(1 for s in suite_results if s.is_success)
    failed_suites = total_suites - passed_suites

    total_tests = sum(s.total_tests for s in suite_results)
    passed_tests = sum(s.passed_tests for s in suite_results)
    failed_tests = sum(s.failed_tests for s in suite_results)

    total_duration_ms = sum(s.duration_ms for s in suite_results)
    total_cost_usd = sum(s.total_cost_usd for s in suite_results)

    # Estimate traditional GPT-4o cost for equivalent judgments (~$0.025 per test)
    traditional_cost_usd = total_tests * 0.025
    savings_pct = (
        ((traditional_cost_usd - total_cost_usd) / traditional_cost_usd) * 100
        if traditional_cost_usd > 0
        else 0
    )

    console.print()
    for suite in suite_results:
        # File header
        badge = "[bold white on green] PASS [/]" if suite.is_success else "[bold white on red] FAIL [/]"
        rel_path = suite.file_path or suite.suite_name
        console.print(f"{badge} [bold]{rel_path}[/] [dim]({suite.total_tests} tests in {suite.duration_ms:.0f}ms)[/]")

        # Tests details
        for tr in suite.results:
            tc = tr.test_case
            status_symbol = "[bold green]✓[/]" if tr.passed else "[bold red]✕[/]"
            console.print(f"  {status_symbol} [white]{tc.name}[/] [dim]({tr.duration_ms:.0f}ms, ${tr.total_cost_usd:.5f})[/]")

            # If failed or user wants details, show assertions
            if not tr.passed:
                for a_name, dec in tr.decisions.items():
                    if not dec.passed:
                        err_text = dec.error or dec.reason or "Assertion threshold not met"
                        console.print(
                            f"    [red]Assertion failed:[/] [bold]{a_name}[/] "
                            f"[dim](prob: {dec.probability:.2f}, thresh: {dec.threshold:.2f})[/] → {err_text}"
                        )
        console.print()

    # Summary Table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Label", style="bold dim", justify="right")
    table.add_column("Value")

    # Suites status
    suite_status = []
    if failed_suites > 0:
        suite_status.append(f"[bold red]{failed_suites} failed[/]")
    if passed_suites > 0:
        suite_status.append(f"[bold green]{passed_suites} passed[/]")
    table.add_row("Test Files", f"{' | '.join(suite_status)} ({total_suites})")

    # Tests status
    test_status = []
    if failed_tests > 0:
        test_status.append(f"[bold red]{failed_tests} failed[/]")
    if passed_tests > 0:
        test_status.append(f"[bold green]{passed_tests} passed[/]")
    table.add_row("Tests", f"{' | '.join(test_status)} ({total_tests})")

    # Timing
    table.add_row("Duration", f"[bold cyan]{total_duration_ms / 1000.0:.2f}s[/] [dim]({total_duration_ms:.0f}ms total)[/]")

    # Cost comparison
    cost_str = (
        f"[bold green]${total_cost_usd:.5f}[/] "
        f"[dim](vs ~${traditional_cost_usd:.3f} with GPT-4o-judge — saved [/]"
        f"[bold green]{savings_pct:.1f}%[/][dim])[/]"
    )
    table.add_row("Estimated Cost", cost_str)

    console.print(Panel(table, border_style="dim", title="[bold]Execution Summary[/]", title_align="left"))
