"""Jev-Judge: Vitest for LLM outputs. Fast, deterministic CI/CD evaluations powered by TypeSafe Jev."""

import asyncio
from typing import Any, Dict, List, Optional, Union

from jev_judge.client import JevClient
from jev_judge.models import DecisionResult, TestCase, TestCaseResult, TestSuite, TestSuiteResult
from jev_judge.runner import TestRunner

__version__ = "0.1.0"


class Judge:
    """Programmatic interface for evaluating model outputs with TypeSafe Jev."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        force_mock: bool = False,
        default_threshold: float = 0.75,
    ):
        self.client = JevClient(api_key=api_key, force_mock=force_mock)
        self.runner = TestRunner(client=self.client, default_threshold=default_threshold)

    def evaluate(
        self,
        output: str,
        assertions: Dict[str, Any],
        input: Optional[str] = None,
        context: Optional[Union[str, Dict[str, Any], List[Any]]] = None,
        name: str = "Evaluation Case",
    ) -> TestCaseResult:
        """Synchronously evaluate a single model output."""
        tc = TestCase(
            name=name,
            input=input,
            context=context,
            output=output,
            assertions=assertions,
        )
        return asyncio.run(self.runner.run_test_case(tc))

    async def aevaluate(
        self,
        output: str,
        assertions: Dict[str, Any],
        input: Optional[str] = None,
        context: Optional[Union[str, Dict[str, Any], List[Any]]] = None,
        name: str = "Evaluation Case",
    ) -> TestCaseResult:
        """Asynchronously evaluate a single model output."""
        tc = TestCase(
            name=name,
            input=input,
            context=context,
            output=output,
            assertions=assertions,
        )
        return await self.runner.run_test_case(tc)


__all__ = [
    "Judge",
    "JevClient",
    "TestRunner",
    "TestCase",
    "TestCaseResult",
    "TestSuite",
    "TestSuiteResult",
    "DecisionResult",
    "__version__",
]
