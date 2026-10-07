"""LlamaIndex integration for jev-judge fast evaluations."""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Union
from jev_judge import Judge
from jev_judge.models import TestCaseResult


@dataclass
class JevEvaluationResult:
    """Standard evaluation result compatible with LlamaIndex BaseEvaluator."""

    query: Optional[str] = None
    contexts: Optional[Sequence[str]] = None
    response: Optional[str] = None
    passing: bool = True
    score: Optional[float] = None
    feedback: Optional[str] = None
    pairwise_source: Optional[str] = None
    invalid_result: bool = False
    invalid_reason: Optional[str] = None
    extra_info: Dict[str, Any] = field(default_factory=dict)


class JevLlamaIndexEvaluator:
    """Evaluates LlamaIndex query responses against retrieved context using TypeSafe Jev (sub-100ms)."""

    def __init__(
        self,
        assertions: Optional[Dict[str, Any]] = None,
        judge: Optional[Judge] = None,
        force_mock: bool = False,
    ):
        self.assertions = assertions or {"faithfulness": "pass", "relevance": 5}
        self.judge = judge or Judge(force_mock=force_mock)

    def _extract_response_and_context(
        self,
        response: Any,
        contexts: Optional[Sequence[str]] = None,
    ) -> tuple[str, Optional[str]]:
        """Extract plain string output and joined context from response object or string."""
        if hasattr(response, "response"):
            resp_str = str(response.response)
        else:
            resp_str = str(response)

        extracted_contexts = list(contexts) if contexts else []
        if hasattr(response, "source_nodes") and not extracted_contexts:
            for node_with_score in getattr(response, "source_nodes", []):
                node = getattr(node_with_score, "node", node_with_score)
                content = getattr(node, "get_content", lambda: "")() or getattr(node, "text", "")
                if content:
                    extracted_contexts.append(str(content))

        ctx_str = "\n\n".join(extracted_contexts) if extracted_contexts else None
        return resp_str, ctx_str

    def evaluate(
        self,
        query: Optional[str] = None,
        response: Optional[Any] = None,
        contexts: Optional[Sequence[str]] = None,
        **kwargs: Any,
    ) -> JevEvaluationResult:
        """Synchronously evaluate a query and response."""
        resp_str, ctx_str = self._extract_response_and_context(response, contexts)

        tc_result: TestCaseResult = self.judge.evaluate(
            output=resp_str,
            input=query,
            context=ctx_str,
            assertions=self.assertions,
            name=kwargs.get("name", "LlamaIndex Eval"),
        )

        feedback_parts = []
        for name, dec in tc_result.decisions.items():
            status = "PASS" if dec.passed else "FAIL"
            prob = f" (prob: {dec.probability:.2f})" if dec.probability is not None else ""
            feedback_parts.append(f"{name}: {status}{prob}")

        return JevEvaluationResult(
            query=query,
            contexts=contexts,
            response=resp_str,
            passing=tc_result.passed,
            score=1.0 if tc_result.passed else 0.0,
            feedback="; ".join(feedback_parts),
            extra_info={
                "duration_ms": tc_result.duration_ms,
                "cost_usd": tc_result.total_cost_usd,
                "decisions": {k: v.model_dump() for k, v in tc_result.decisions.items()},
            },
        )

    async def aevaluate(
        self,
        query: Optional[str] = None,
        response: Optional[Any] = None,
        contexts: Optional[Sequence[str]] = None,
        **kwargs: Any,
    ) -> JevEvaluationResult:
        """Asynchronously evaluate a query and response."""
        resp_str, ctx_str = self._extract_response_and_context(response, contexts)

        tc_result: TestCaseResult = await self.judge.aevaluate(
            output=resp_str,
            input=query,
            context=ctx_str,
            assertions=self.assertions,
            name=kwargs.get("name", "LlamaIndex Eval"),
        )

        feedback_parts = []
        for name, dec in tc_result.decisions.items():
            status = "PASS" if dec.passed else "FAIL"
            prob = f" (prob: {dec.probability:.2f})" if dec.probability is not None else ""
            feedback_parts.append(f"{name}: {status}{prob}")

        return JevEvaluationResult(
            query=query,
            contexts=contexts,
            response=resp_str,
            passing=tc_result.passed,
            score=1.0 if tc_result.passed else 0.0,
            feedback="; ".join(feedback_parts),
            extra_info={
                "duration_ms": tc_result.duration_ms,
                "cost_usd": tc_result.total_cost_usd,
                "decisions": {k: v.model_dump() for k, v in tc_result.decisions.items()},
            },
        )
