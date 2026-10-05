"""Asynchronous test suite runner with parallel execution."""

import asyncio
import os
import glob
import time
from typing import List, Optional
import yaml

from jev_judge.client import JevClient
from jev_judge.evaluators import get_evaluator_spec
from jev_judge.models import TestCase, TestCaseResult, TestSuite, TestSuiteResult, DecisionResult


class TestRunner:
    def __init__(
        self,
        client: Optional[JevClient] = None,
        concurrency: int = 10,
        default_threshold: float = 0.75,
    ):
        self.client = client or JevClient()
        self.concurrency = concurrency
        self.default_threshold = default_threshold
        self.semaphore = asyncio.Semaphore(concurrency)

    async def run_test_case(self, tc: TestCase) -> TestCaseResult:
        """Run all assertions for a single test case in one Jev decision batch."""
        async with self.semaphore:
            start = time.perf_counter()

            assertion_defs = [
                get_evaluator_spec(name, val, default_threshold=self.default_threshold)
                for name, val in tc.assertions.items()
            ]

            state = {
                "input": tc.input,
                "context": tc.context,
                "output": tc.output,
            }

            decisions_list: List[DecisionResult] = await self.client.decide_batch(state, assertion_defs)
            duration_ms = (time.perf_counter() - start) * 1000.0

            decisions_dict = {d.assertion_name: d for d in decisions_list}
            passed = all(d.passed for d in decisions_list)
            total_cost = sum(d.cost_usd for d in decisions_list)

            return TestCaseResult(
                test_case=tc,
                passed=passed,
                decisions=decisions_dict,
                duration_ms=round(duration_ms, 2),
                total_cost_usd=round(total_cost, 6),
            )

    async def run_suite(self, suite: TestSuite, file_path: Optional[str] = None) -> TestSuiteResult:
        """Run all test cases in a test suite concurrently."""
        start = time.perf_counter()

        tasks = [self.run_test_case(tc) for tc in suite.tests]
        results: List[TestCaseResult] = await asyncio.gather(*tasks)

        duration_ms = (time.perf_counter() - start) * 1000.0
        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count
        total_cost = sum(r.total_cost_usd for r in results)

        return TestSuiteResult(
            suite_name=suite.name,
            file_path=file_path,
            total_tests=len(results),
            passed_tests=passed_count,
            failed_tests=failed_count,
            duration_ms=round(duration_ms, 2),
            total_cost_usd=round(total_cost, 6),
            results=results,
        )

    def load_suite_from_file(self, file_path: str) -> TestSuite:
        """Parse a YAML or JSON test suite file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if isinstance(data, list):
            # Simple list of test cases
            test_cases = [TestCase(**item) for item in data]
            base_name = os.path.basename(file_path)
            return TestSuite(name=base_name, tests=test_cases)
        elif isinstance(data, dict):
            if "tests" in data:
                return TestSuite(**data)
            # Single test case dictionary
            return TestSuite(name=os.path.basename(file_path), tests=[TestCase(**data)])
        else:
            raise ValueError(f"Unrecognized format in test file: {file_path}")

    async def run_path(self, target_path: str) -> List[TestSuiteResult]:
        """Discover and execute all test files in a directory or single file."""
        files_to_run: List[str] = []

        if os.path.isfile(target_path):
            files_to_run.append(target_path)
        elif os.path.isdir(target_path):
            for ext in ("*.yaml", "*.yml", "*.json"):
                files_to_run.extend(glob.glob(os.path.join(target_path, "**", ext), recursive=True))
        else:
            # Pattern matching
            matched = glob.glob(target_path)
            if matched:
                files_to_run.extend(matched)
            else:
                raise FileNotFoundError(f"Path not found: {target_path}")

        suite_results = []
        for fp in sorted(files_to_run):
            suite = self.load_suite_from_file(fp)
            res = await self.run_suite(suite, file_path=fp)
            suite_results.append(res)

        return suite_results
