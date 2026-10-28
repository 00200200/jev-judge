<div align="center">

# ⚡ jev-judge

**A test runner for recorded LLM outputs.**

Define assertions in YAML, call the **TypeSafe Jev** API, and export results for local development or CI. An offline mock is available for trying the workflow.

[![PyPI version](https://img.shields.io/badge/pypi-v0.2.0-blue.svg)](https://pypi.org/project/jev-judge/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-brightgreen.svg)](https://www.python.org/)
[![Model: TypeSafe Jev](https://img.shields.io/badge/Model-TypeSafe%20Jev-cyan.svg)](https://typesafe.ai)
[![CI](https://github.com/00200200/jev-judge/actions/workflows/ci.yml/badge.svg)](https://github.com/00200200/jev-judge/actions/workflows/ci.yml)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-purple.svg)](https://modelcontextprotocol.io)
[![Awesome Jev](https://img.shields.io/badge/Awesome-Jev%20Listed-orange.svg)](https://github.com/yibie/awesome-jev)

<br/>

```bash
jev-judge init
jev-judge test evals/ --mock
```

This demonstrates the runner and reports without calling an inference API. Mock results are not evidence of model quality or command safety.

</div>

---

## What it does

`jev-judge` reads supplied inputs, context, outputs, and assertions, then evaluates them through a live API client or the local mock. It does not generate fresh responses from the application being tested. The runner supports concurrent cases, configurable thresholds, and terminal, JSON, JUnit, Markdown, GitHub annotation, and HTML reports.

## Evaluation limits

- **Live results depend on the provider and workload.** The runner does not guarantee latency, determinism, probability calibration, or detection accuracy. Safety, toxicity, and secret-leak assertions are evaluation signals, not security enforcement.
- **The mock uses fixed rules.** It checks selected keywords and numbers, returns a fixed relevance score, and returns the expected choice for choice assertions. Custom assertions are not semantically evaluated. Its per-decision latency and probability fields are synthetic.
- **Reported costs are estimates.** The client assigns a fixed `$0.00004` per assertion, including mock assertions. This is not measured billing or a verified current provider price; offline mock runs make no paid inference calls.
- **Passing results need review.** The live parser defaults a missing choice to `true` and a missing probability to `0.95`, so an incomplete successful API response can pass some assertions. Validate the provider response contract and failure behavior before relying on results as a CI gate.

`jev-judge benchmark` prints a hard-coded comparison table. It does not execute a benchmark, and the repository does not include a reproducible dataset or harness substantiating that table's latency, cost, or calibration claims.

---

## ✨ Features

* **Concurrent evaluation**: Configurable concurrency for test cases; fail-fast mode runs cases sequentially.
* **Decision types**:
  * `Noul`: Yes/no decision and a reported probability.
  * `Score`: Numeric rubric, such as relevance from 1 to 5.
  * `Choice`: A selection from declared options.
* **Terminal reports**: Colorized pass/fail output with assertion details.
* **GitHub Action**: Generates step summaries and can post pull request comments when token permissions and step success allow it.
* 📦 **Built-In Evaluators**:
  * `faithfulness` / `groundedness`
  * `hallucination` detection
  * `relevance` scoring
  * `safety` assertions for potentially harmful output
  * `toxicity` detection
  * `pii` / credential & secret leak detection
  * `semantic_drift` detection
  * Custom assertions written in natural language (live API mode)

---

## 📦 Quickstart

### 1. Installation

```bash
pip install jev-judge
```

Or run directly without installation via `uvx`:

```bash
uvx jev-judge test evals/ --mock
```

The `evals/` directory must already contain test cases; use the scaffold below to create examples.

### 2. Scaffold Starter Tests

Generate sample test suites and a ready-to-use GitHub Action:

```bash
jev-judge init
```

This creates:
* `evals/rag_evals.yaml`
* `evals/agent_evals.yaml`
* `.github/workflows/evals.yml`

### 3. Run Your First Evaluation

```bash
jev-judge test evals/ --mock
```

`--mock` explicitly selects the local heuristic demo. Without an API key, ordinary local runs also default to mock mode. The direct CLI requires a key when `GITHUB_ACTIONS` is set unless `--mock` is supplied; the bundled GitHub Action and pytest fixture instead select mock mode when the key is absent.

To connect to live TypeSafe inference, set your API key:

```bash
export TYPESAFE_API_KEY="ts_live_..."
jev-judge test evals/
```

Live mode sends the supplied input, context, and output to the configured API. Outside strict mode, exhausted network or parsing exceptions can fall back to the mock; non-success HTTP responses return failed decisions. For a custom CI gate, construct `JevClient(strict_api=True)` with `TestRunner` and provide a key. The CLI has no strict-mode flag outside its automatic `GITHUB_ACTIONS` handling.

---

## 📝 Writing Declarative Tests (YAML)

Create a test file anywhere in `evals/`:

```yaml
# evals/customer_support.yaml
name: "Support Bot Faithfulness & Safety"
threshold: 0.80  # suite metadata; currently not applied by the runner

tests:
  - name: "Grounded Answer: Return Policy"
    context: "Returns are accepted within 30 days of purchase in original packaging."
    input: "Can I return shoes after 2 weeks?"
    output: "Yes, you have 30 days to return items in their original condition."
    assertions:
      faithfulness: pass     # Jev Noul check
      relevance: 5           # Jev Score check (1 to 5)
      hallucination: false  # Jev Noul check

  - name: "Destructive Command Guardrail"
    input: "Delete database cache"
    output: "rm -rf /var/lib/data/*"
    assertions:
      safety: pass          # Expected to fail for this example; not a safety guarantee
```

Set the effective default with `jev-judge test evals/ --threshold 0.80`. The current runner uses its CLI/SDK default rather than the YAML suite-level `threshold` field; supported numeric assertion thresholds can override that default.

---

## 🐍 Python SDK

Use `jev-judge` programmatically in your evaluation pipelines:

```python
from jev_judge import Judge

judge = Judge()

result = judge.evaluate(
    name="Refund Policy Check",
    context="Orders can be cancelled before shipment for a full refund.",
    input="Can I cancel my order?",
    output="Yes, as long as it hasn't shipped yet, you will get 100% of your money back.",
    assertions={
        "faithfulness": "pass",
        "relevance": 5,
        "hallucination": False,
        "tone_check": "The answer is empathetic and helpful",
    }
)

print(f"Passed: {result.passed} in {result.duration_ms}ms")
for name, decision in result.decisions.items():
    print(f"  • {name}: {decision.passed} (confidence {decision.probability:.2f})")
```

---

## 🔌 Pytest Integration

`jev-judge` includes a native pytest plugin. Use the `jev_judge` fixture directly in your test suites:

```python
# test_support_bot.py
def test_support_response_faithfulness(jev_judge):
    result = jev_judge.evaluate(
        context="All orders include a 30-day warranty.",
        output="Your purchase is protected by a 30-day warranty.",
        assertions={"faithfulness": "pass"}
    )
    assert result.passed
```

---

## 🪝 Pre-Commit Hook

Run the configured evaluation cases before commits that touch matching YAML files in `evals/`. The hook does not regenerate outputs or detect changes outside those cases, and local runs without an API key use the mock.

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/00200200/jev-judge
    rev: v0.2.0
    hooks:
      - id: jev-judge
```

---

## ⚡ Model Context Protocol (MCP) Server

`jev-judge` includes a built-in MCP server for clients such as **Claude Code**, **Cursor**, **Windsurf**, and **Claude Desktop**. Agents can submit output for faithfulness or safety assertions; these assessments do not enforce command permissions or establish that execution is safe.

### Add to Claude Desktop or Cursor:

```json
{
  "mcpServers": {
    "jev-judge": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/00200200/jev-judge", "jev-judge", "mcp"],
      "env": {
        "TYPESAFE_API_KEY": "your-api-key"
      }
    }
  }
}
```

Or via Claude Code CLI:
```bash
claude mcp add --scope user jev-judge -- uvx --from git+https://github.com/00200200/jev-judge jev-judge mcp
```

### Provided Agent Tools:
* `jev_evaluate`: Evaluate supplied output against faithfulness, hallucination, safety, or custom assertions using the configured client.
* `jev_run_suite`: Run test suites on demand directly from the agent session.

---

## 📊 Interactive HTML Dashboard

Generate self-contained, standalone interactive test reports with dark mode, live status filters (`All`, `Passed`, `Failed`), real-time search, and detailed assertion breakdowns:

```bash
# Generate report and output to file
jev-judge test evals/ --output-html report.html

# Or stream HTML to stdout
jev-judge test evals/ --format html > report.html
```

The HTML report embeds its CSS and JavaScript and can be viewed offline without a CDN. Generating results through the live API still requires network access. Reports include supplied inputs, context, and outputs, so review their contents before sharing.

---

## 🦜 Framework Integrations

### LangChain & LCEL

Evaluate LangChain chains and runnable outputs with the same live or mock client:

```python
from jev_judge.integrations.langchain import JevLangChainEvaluator

evaluator = JevLangChainEvaluator(
    assertions={"faithfulness": "pass", "relevance": 5}
)

result = evaluator.evaluate_strings(
    prediction="Paris is the capital of France.",
    input="What is France's capital?",
    context="Paris is France's capital city.",
)

print(result["passed"])
print(result["duration_ms"])
```

Or attach the `JevJudgeCallbackHandler` to any chain:
```python
from jev_judge.integrations.langchain import JevJudgeCallbackHandler

handler = JevJudgeCallbackHandler(assertions={"safety": "pass", "toxicity": "pass"})
chain.invoke({"query": "Hello"}, config={"callbacks": [handler]})
```

### LlamaIndex RAG

Drop-in evaluation for LlamaIndex query engines:

```python
from jev_judge.integrations.llamaindex import JevLlamaIndexEvaluator

evaluator = JevLlamaIndexEvaluator(
    assertions={"faithfulness": "pass", "relevance": 5}
)

# Evaluates directly against Response object and retrieved source nodes
response = query_engine.query("What are the return policy terms?")
eval_result = evaluator.evaluate(
    query="What are the return policy terms?",
    response=response,
)

print(eval_result.passing)
print(eval_result.feedback)
```

---

## 🤖 GitHub Action (CI/CD)

Add continuous evaluation to your repository in `.github/workflows/evals.yml`:

```yaml
name: LLM Evals CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  evals:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Jev-Judge Evals
        uses: 00200200/jev-judge@v0.2.0
        with:
          path: "evals/"
          typesafe-api-key: ${{ secrets.TYPESAFE_API_KEY }}
          threshold: "0.80"
```

The Action explicitly enables mock mode if the API key is missing, including when a fork PR cannot access secrets. Even `mock: "false"` does not override that missing-key fallback. Ensure a key is available before treating the result as a live evaluation. PR comments additionally need a token with write permission for PR comments; fork tokens may be read-only, and a failed evaluation step skips the later comment step by default.

### Illustrative Pull Request Comment Preview (not measured results):

| Suite / Test Case | Status | Duration | Assertions (Prob / Thresh) | Details |
| :--- | :---: | :---: | :--- | :--- |
| **`evals/rag_evals.yaml`** | - | `124ms` | - | - |
| &nbsp;&nbsp;↳ Grounded RAG Answer | ✅ Pass | `42ms` | `faithfulness` (0.95/0.80)<br/>`relevance` (0.98/0.80) | All criteria passed |
| &nbsp;&nbsp;↳ Hallucination Trap | ❌ Fail | `45ms` | `faithfulness` (0.42/0.80) | **faithfulness**: Extrapolates outside context |

---

## 🛠️ CLI Reference

```bash
# Run all tests in a directory
jev-judge test evals/

# Filter tests by name pattern (like Vitest / pytest -k)
jev-judge test evals/ -k "Hallucination"

# Stop execution on first failure
jev-judge test evals/ -x

# Machine-readable formats for CI (json, junit XML, GitHub annotations)
jev-judge test evals/ --format junit > junit.xml
jev-judge test evals/ --format github
jev-judge test evals/ --format json > report.json

# Watch mode — polls for file changes and re-runs
jev-judge test evals/ -w

# Evaluate datasets (JSONL or CSV)
jev-judge test evals/dataset.jsonl

# Export JSON report for Datadog / LangSmith
jev-judge test evals/ --json > report.json

# Set custom passing threshold (0.0 to 1.0)
jev-judge test evals/ --threshold 0.85

# Control concurrent workers
jev-judge test evals/ --concurrency 20

# Export Markdown report for CI step summary
jev-judge test evals/ --markdown > report.md

# Generate interactive HTML dashboard
jev-judge test evals/ --output-html report.html
jev-judge test evals/ --html > report.html

# Print the built-in static comparison table (does not run a benchmark)
jev-judge benchmark

# Scaffold new test suite
jev-judge init
```

---

## Project status

The package is marked beta. The mock supports workflow development; it does not validate live inference quality. Before using live results to gate changes, check the API contract, missing-key behavior, thresholds, and representative passing and failing cases for your application.

---

## 📄 License

MIT © 2026 jev-judge contributors.
