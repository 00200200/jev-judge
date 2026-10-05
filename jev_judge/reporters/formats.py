"""Resolve CLI output format, honoring --format over aliases and env defaults."""

import os
from typing import Optional

OUTPUT_FORMATS = ("pretty", "markdown", "json", "junit", "github")


def resolve_output_format(
    output_format: Optional[str],
    markdown_alias: bool = False,
    github_actions: Optional[str] = None,
) -> str:
    """Pick a reporter. Explicit --format always wins; --markdown aliases markdown."""
    if output_format:
        return output_format.lower()
    if markdown_alias:
        return "markdown"
    env_val = github_actions if github_actions is not None else os.environ.get("GITHUB_ACTIONS")
    if env_val:
        return "markdown"
    return "pretty"
