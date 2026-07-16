"""Arbitrary-precision numeric evaluation backed by SymPy/mpmath."""

from typing import cast

import sympy  # pyright: ignore[reportMissingTypeStubs]
from langchain_core.tools import tool

DEFAULT_DIGITS = 50
MAX_DIGITS = 200  # beyond this, runtimes and result sizes stop paying for themselves


@tool
def numeric_eval(expression: str, digits: int = DEFAULT_DIGITS) -> str:
    """Evaluate an expression to a high-precision decimal — for exact formulas use `sympy_eval`.

    `expression`: a SymPy expression string with no free variables, e.g. "exp(pi*sqrt(163))".
    `digits`: decimal precision (default 50, max 200).
    On error you get the message back: fix the expression and retry.
    """
    try:
        digits = min(digits, MAX_DIGITS)
        expr: object = sympy.sympify(expression)  # pyright: ignore[reportUnknownMemberType]
        value = cast(object, sympy.N(expr, digits))  # pyright: ignore[reportUnknownMemberType]
        return str(value)
    # Any failure goes back to the model as text so it can correct itself and retry.
    except Exception as error:
        return f"Error: {error}"
