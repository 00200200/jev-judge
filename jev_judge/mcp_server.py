"""Model Context Protocol (MCP) server for jev-judge.

Enables AI agents (Cursor, Claude Code, Windsurf, Claude Desktop) to invoke Jev evaluations
as structured tools over stdio JSON-RPC.
"""

import sys
import json
import asyncio
from typing import Any, Dict, Optional

from jev_judge import Judge
from jev_judge.runner import TestRunner


class McpServer:
    def __init__(self, force_mock: bool = False):
        self.judge = Judge(force_mock=force_mock)
        self.runner = TestRunner(client=self.judge.client)

    def get_tool_definitions(self) -> list:
        return [
            {
                "name": "jev_evaluate",
                "description": (
                    "Evaluate an LLM or agent output using TypeSafe Jev (System One). "
                    "Performs sub-100ms deterministic checks for faithfulness (groundedness in context), "
                    "hallucination detection, safety guardrails (malicious commands, data leaks), "
                    "and answer relevance."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "output": {
                            "type": "string",
                            "description": "The model response, generated text, or command to evaluate."
                        },
                        "context": {
                            "type": "string",
                            "description": "Grounding facts or reference documentation against which to evaluate faithfulness."
                        },
                        "input": {
                            "type": "string",
                            "description": "The user query or prompt that produced the output."
                        },
                        "assertions": {
                            "type": "object",
                            "description": "Key-value assertions (e.g. {'faithfulness': 'pass', 'safety': 'pass', 'relevance': 5})."
                        }
                    },
                    "required": ["output", "assertions"]
                }
            },
            {
                "name": "jev_run_suite",
                "description": "Run an automated test suite file (YAML, JSON, JSONL, or CSV) using jev-judge.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to test suite file or directory."
                        },
                        "fail_fast": {
                            "type": "boolean",
                            "description": "Stop at the first failure."
                        }
                    },
                    "required": ["path"]
                }
            }
        ]

    async def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if name == "jev_evaluate":
            output = arguments.get("output", "")
            context = arguments.get("context")
            user_input = arguments.get("input")
            assertions = arguments.get("assertions", {"faithfulness": "pass"})

            result = await self.judge.aevaluate(
                output=output,
                context=context,
                input=user_input,
                assertions=assertions,
                name="MCP Evaluation",
            )

            summary = {
                "passed": result.passed,
                "duration_ms": result.duration_ms,
                "cost_usd": result.total_cost_usd,
                "decisions": {
                    k: {
                        "passed": v.passed,
                        "probability": v.probability,
                        "value": v.value,
                        "threshold": v.threshold,
                        "reason": v.reason or v.error,
                    }
                    for k, v in result.decisions.items()
                }
            }
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(summary, indent=2)
                    }
                ]
            }

        elif name == "jev_run_suite":
            path = arguments.get("path", "evals")
            fail_fast = arguments.get("fail_fast", False)
            self.runner.fail_fast = fail_fast

            suite_results = await self.runner.run_path(path)
            total_tests = sum(s.total_tests for s in suite_results)
            passed_tests = sum(s.passed_tests for s in suite_results)
            failed_tests = sum(s.failed_tests for s in suite_results)

            summary = {
                "all_passed": all(s.is_success for s in suite_results),
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "duration_ms": sum(s.duration_ms for s in suite_results),
                "suites": [
                    {
                        "suite": s.suite_name,
                        "passed": s.is_success,
                        "failed_count": s.failed_tests,
                    }
                    for s in suite_results
                ]
            }
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(summary, indent=2)
                    }
                ]
            }

        else:
            raise ValueError(f"Unknown tool: {name}")

    async def run_stdio(self):
        """Standard stdio JSON-RPC loop compatible with Anthropic Model Context Protocol."""
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            line = await reader.readline()
            if not line:
                break
            line_str = line.decode("utf-8").strip()
            if not line_str:
                continue

            try:
                request = json.loads(line_str)
                req_id = request.get("id")
                method = request.get("method")
                params = request.get("params", {})

                # MCP Handshake & Protocol
                if method == "initialize":
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {
                                "tools": {}
                            },
                            "serverInfo": {
                                "name": "jev-judge",
                                "version": "0.2.0"
                            }
                        }
                    }
                elif method == "notifications/initialized":
                    continue
                elif method == "tools/list":
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "tools": self.get_tool_definitions()
                        }
                    }
                elif method == "tools/call":
                    tool_name = params.get("name")
                    arguments = params.get("arguments", {})
                    try:
                        tool_result = await self.handle_tool_call(tool_name, arguments)
                        response = {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": tool_result
                        }
                    except Exception as e:
                        response = {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "error": {
                                "code": -32000,
                                "message": str(e)
                            }
                        }
                elif method == "ping":
                    response = {"jsonrpc": "2.0", "id": req_id, "result": {}}
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    }

                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            except Exception as e:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {e}"
                    }
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()
