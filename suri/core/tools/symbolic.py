"""Symbolic mathematics tools backed by SymPy."""

from collections.abc import Callable
from typing import cast

import sympy  # pyright: ignore[reportMissingTypeStubs]
from langchain_core.tools import tool

# SymPy's own type information is too partial for strict checking; pin each function we
# use to a plain object -> object callable at this boundary.
_OPERATIONS: dict[str, Callable[[object], object]] = {
    "simplify": cast(Callable[[object], object], sympy.simplify),  # pyright: ignore[reportUnknownMemberType]
    "solve": cast(Callable[[object], object], sympy.solve),  # pyright: ignore[reportUnknownMemberType]
    "diff": cast(Callable[[object], object], sympy.diff),  # pyright: ignore[reportUnknownMemberType]
    "integrate": cast(Callable[[object], object], sympy.integrate),  # pyright: ignore[reportUnknownMemberType]
}


@tool
def sympy_eval(expression: str, operation: str = "evaluate") -> str:
    """Compute an exact symbolic result, e.g. "sqrt(3)/2" — for decimals use `numeric_eval`.

    `expression`: a SymPy expression string, e.g. "x**2 - 1".
    `operation`: "evaluate", "simplify", "solve", "diff" or "integrate".
    On error you get the message back: fix the expression and retry.
    """
    try:
        expr: object = sympy.sympify(expression)  # pyright: ignore[reportUnknownMemberType]
        if operation == "evaluate":
            return str(expr)
        if operation not in _OPERATIONS:
            return f"Error: unknown operation {operation!r}"
        return str(_OPERATIONS[operation](expr))
    # Any failure goes back to the model as text so it can correct itself and retry.
    except Exception as error:
        return f"Error: {error}"
