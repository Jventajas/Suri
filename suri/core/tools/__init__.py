"""Verification tools the agent can call: the model proposes, these provide ground truth."""

from langchain_core.tools import BaseTool

from suri.core.tools.symbolic import sympy_eval

# Every tool the agent gets; new tool modules register here, agent.py never changes.
AGENT_TOOLS: tuple[BaseTool, ...] = (sympy_eval,)

__all__ = ["AGENT_TOOLS"]
