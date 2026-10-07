"""LangChain integration for jev-judge fast evaluations."""

import asyncio
from typing import Any, Dict, List, Optional, Union
from jev_judge import Judge
from jev_judge.models import TestCaseResult


class JevLangChainEvaluator:
    """Evaluates LangChain / LCEL outputs using TypeSafe Jev (sub-100ms).

    Compatible with LangChain's evaluation pattern (evaluate_strings).
    """

    def __init__(
        self,
        assertions: Optional[Dict[str, Any]] = None,
        judge: Optional[Judge] = None,
        force_mock: bool = False,
    ):
        self.assertions = assertions or {"faithfulness": "pass", "relevance": 5}
        self.judge = judge or Judge(force_mock=force_mock)

    def evaluate_strings(
        self,
        prediction: str,
        input: Optional[str] = None,
        reference: Optional[str] = None,
        context: Optional[Union[str, List[str]]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Synchronously evaluate prediction against input and context/reference."""
        ctx = context if context is not None else reference
        if isinstance(ctx, list):
            ctx = "\n\n".join(ctx)

        result: TestCaseResult = self.judge.evaluate(
            output=prediction,
            input=input,
            context=ctx,
            assertions=self.assertions,
            name=kwargs.get("name", "LangChain Eval"),
        )

        scores = {}
        for name, dec in result.decisions.items():
            scores[name] = dec.probability if dec.probability is not None else (1.0 if dec.passed else 0.0)

        return {
            "passed": result.passed,
            "score": 1.0 if result.passed else 0.0,
            "scores": scores,
            "duration_ms": result.duration_ms,
            "cost_usd": result.total_cost_usd,
            "decisions": {k: v.model_dump() for k, v in result.decisions.items()},
        }

    async def aevaluate_strings(
        self,
        prediction: str,
        input: Optional[str] = None,
        reference: Optional[str] = None,
        context: Optional[Union[str, List[str]]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Asynchronously evaluate prediction against input and context/reference."""
        ctx = context if context is not None else reference
        if isinstance(ctx, list):
            ctx = "\n\n".join(ctx)

        result: TestCaseResult = await self.judge.aevaluate(
            output=prediction,
            input=input,
            context=ctx,
            assertions=self.assertions,
            name=kwargs.get("name", "LangChain Eval"),
        )

        scores = {}
        for name, dec in result.decisions.items():
            scores[name] = dec.probability if dec.probability is not None else (1.0 if dec.passed else 0.0)

        return {
            "passed": result.passed,
            "score": 1.0 if result.passed else 0.0,
            "scores": scores,
            "duration_ms": result.duration_ms,
            "cost_usd": result.total_cost_usd,
            "decisions": {k: v.model_dump() for k, v in result.decisions.items()},
        }


# Optional LangChain Callback Handler
try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:
    class BaseCallbackHandler:  # type: ignore
        """Fallback stub when langchain_core is not installed."""
        pass


class JevJudgeCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler that records and evaluates LLM generations in real-time."""

    def __init__(
        self,
        assertions: Optional[Dict[str, Any]] = None,
        judge: Optional[Judge] = None,
        force_mock: bool = False,
    ):
        super().__init__()
        self.assertions = assertions or {"safety": "pass", "toxicity": "pass"}
        self.judge = judge or Judge(force_mock=force_mock)
        self.evaluation_results: List[TestCaseResult] = []

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Called when LLM generation finishes."""
        for generations in getattr(response, "generations", []):
            for gen in generations:
                text = getattr(gen, "text", "")
                if text:
                    res = self.judge.evaluate(
                        output=text,
                        assertions=self.assertions,
                        name="LangChain Generation",
                    )
                    self.evaluation_results.append(res)
