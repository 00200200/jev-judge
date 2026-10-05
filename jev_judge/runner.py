"""Asynchronous test suite runner with parallel execution and multi-format support."""

import asyncio
import os
import glob
import time
import json
import csv
from typing import List, Optional
import yaml

from jev_judge.client import JevClient
from jev_judge.evaluators import get_evaluator_spec
from jev_judge.models import TestCase, TestCaseResult, TestSuite, TestSuiteResult, DecisionResult


class TestRunner:
    __test__ = False

    def __init__(
        self,
        client: Optional[JevClient] = None,
        concurrency: int = 10,
        default_threshold: float = 0.75,
        fail_fast: bool = False,
    ):
        self.client = client or JevClient()
        self.concurrency = concurrency
        self.default_threshold = default_threshold
        self.fail_fast = fail_fast
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

        if self.fail_fast:
            results: List[TestCaseResult] = []
            for tc in suite.tests:
                res = await self.run_test_case(tc)
                results.append(res)
                if not res.passed:
                    break
        else:
            tasks = [self.run_test_case(tc) for tc in suite.tests]
            results = await asyncio.gather(*tasks)

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
        """Parse YAML, JSON, JSONL, or CSV test suite files."""
        base_name = os.path.basename(file_path)

        # 1. JSON Lines (.jsonl)
        if file_path.endswith(".jsonl"):
            test_cases = []
            with open(file_path, "r", encoding="utf-8") as f:
                for idx, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    item = json.loads(line)
                    if "name" not in item:
                        item["name"] = f"Row #{idx}"
                    test_cases.append(TestCase(**item))
            return TestSuite(name=base_name, tests=test_cases)

        # 2. CSV (.csv)
        if file_path.endswith(".csv"):
            test_cases = []
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader, 1):
                    assertions = {}
                    if "assertions" in row and row["assertions"]:
                        try:
                            assertions = json.loads(row["assertions"])
                        except Exception:
                            assertions = {"faithfulness": "pass"}
                    else:
                        assertions = {"faithfulness": "pass"}

                    test_cases.append(
                        TestCase(
                            name=row.get("name") or f"CSV Row #{idx}",
                            input=row.get("input"),
                            context=row.get("context"),
                            output=row.get("output", ""),
                            assertions=assertions,
                        )
                    )
            return TestSuite(name=base_name, tests=test_cases)

        # 3. YAML or JSON
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if isinstance(data, list):
            test_cases = [TestCase(**item) for item in data]
            return TestSuite(name=base_name, tests=test_cases)
        elif isinstance(data, dict):
            if "tests" in data:
                return TestSuite(**data)
            return TestSuite(name=base_name, tests=[TestCase(**data)])
        else:
            raise ValueError(f"Unrecognized format in test file: {file_path}")

    async def run_path(self, target_path: str) -> List[TestSuiteResult]:
        """Discover and execute all test files in a directory or single file."""
        files_to_run: List[str] = []

        if os.path.isfile(target_path):
            files_to_run.append(target_path)
        elif os.path.isdir(target_path):
            for ext in ("*.yaml", "*.yml", "*.json", "*.jsonl", "*.csv"):
                files_to_run.extend(glob.glob(os.path.join(target_path, "**", ext), recursive=True))
        else:
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
            if self.fail_fast and not res.is_success:
                break

        return suite_results
