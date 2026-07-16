"""Shared expression parsing for the math tools."""

from typing import Any

import sympy  # pyright: ignore[reportMissingTypeStubs]
from sympy.core.function import AppliedUndef  # pyright: ignore[reportMissingTypeStubs]


def parse_expression(expression: str, variable_values: dict[str, str] | None = None) -> object:
    """Parse a SymPy expression string, optionally plugging in values for its variables."""

    expr: Any = sympy.sympify(expression)  # pyright: ignore[reportUnknownMemberType]
    # If the expression calls a function SymPy doesn't know, fail here instead of returning it unevaluated.
    if isinstance(expr, sympy.Basic):
        unknown_calls = expr.atoms(AppliedUndef)  # every call to a function SymPy didn't recognize
        if unknown_calls:
            function_names = ", ".join(sorted(str(call.func) for call in unknown_calls))  # e.g. "subs"
            raise ValueError(f"unknown function(s): {function_names}")

    if variable_values:
        substitutions: Any = {
            sympy.Symbol(name): sympy.sympify(value)  # pyright: ignore[reportUnknownMemberType]
            for name, value in variable_values.items()
        }
        expr = expr.subs(substitutions)
    return expr
