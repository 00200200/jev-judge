"""Data models for Jev-Judge test cases, assertions, and results."""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class AssertionType(str, Enum):
    FAITHFULNESS = "faithfulness"
    HALLUCINATION = "hallucination"
    RELEVANCE = "relevance"
    SAFETY = "safety"
    SEMANTIC_DRIFT = "semantic_drift"
    CUSTOM = "custom"


class DecisionType(str, Enum):
    NOUL = "noul"
    CHOICE = "choice"
    SCORE = "score"


class AssertionDef(BaseModel):
    name: str
    assertion_type: AssertionType
    decision_type: DecisionType = DecisionType.NOUL
    instructions: str
    threshold: float = 0.75
    expected: Any = True
    options: Optional[Dict[str, str]] = None


class TestCase(BaseModel):
    __test__ = False
    id: str = Field(default_factory=lambda: "tc_")
    name: str
    description: Optional[str] = None
    input: Optional[str] = None
    context: Optional[Union[str, Dict[str, Any], List[Any]]] = None
    output: str
    assertions: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value mapping of assertions, e.g. faithfulness: pass, relevance: 4, custom: 'Tone is polite'",
    )


class TestSuite(BaseModel):
    __test__ = False
    name: str = "Test Suite"
    description: Optional[str] = None
    threshold: float = 0.75
    tests: List[TestCase] = Field(default_factory=list)


class DecisionResult(BaseModel):
    assertion_name: str
    passed: bool
    decision_type: DecisionType
    value: Any
    probability: float
    threshold: float
    latency_ms: float
    cost_usd: float
    reason: Optional[str] = None
    error: Optional[str] = None


class TestCaseResult(BaseModel):
    __test__ = False
    test_case: TestCase
    passed: bool
    decisions: Dict[str, DecisionResult]
    duration_ms: float
    total_cost_usd: float


class TestSuiteResult(BaseModel):
    __test__ = False
    suite_name: str
    file_path: Optional[str] = None
    total_tests: int
    passed_tests: int
    failed_tests: int
    duration_ms: float
    total_cost_usd: float
    results: List[TestCaseResult]

    @property
    def is_success(self) -> bool:
        return self.failed_tests == 0
