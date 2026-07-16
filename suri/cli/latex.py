"""LaTeX in the transcript: math blocks become Unicode — drawn in 2D or flattened to one line."""

import re
from typing import Any, cast

import flatlatex  # pyright: ignore[reportMissingTypeStubs]
import sympy  # pyright: ignore[reportMissingTypeStubs]
from sympy.parsing.latex import parse_latex  # pyright: ignore[reportMissingTypeStubs, reportUnknownVariableType]

_DISPLAY_MATH_BLOCK = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
_INLINE_MATH = re.compile(r"(?<!\$)\$([^$\n]+?)\$(?!\$)")
_BOXED = re.compile(r"\\boxed\{([^{}]*)\}")  # pure decoration: keep its content, drop the box

# Layout commands, not mathematics: sympy's parser silently mangles them (e.g. \text{or}
# becomes the product t*e*x*t*o*r), so 2D drawing is never attempted on them.
_UNSUPPORTED_2D_LATEX = re.compile(r"\\(text|quad|begin)\b|&|\\\\")

_flat_converter = flatlatex.converter()


def typeset_math(text: str) -> str:
    """Replace LaTeX math in the text with Unicode; whatever can't be rendered faithfully stays as it came.

    A $$...$$ block alone on its line becomes a 2D drawing; one inside a sentence, or
    inline $...$ math, becomes a single line (a drawing would split the sentence).
    """
    pieces: list[str] = []
    cursor = 0
    for block in _DISPLAY_MATH_BLOCK.finditer(text):
        pieces.append(text[cursor : block.start()])
        pieces.append(_render_display_block(text, block))
        cursor = block.end()
    pieces.append(text[cursor:])
    return _INLINE_MATH.sub(_render_inline_match, "".join(pieces))


def _render_display_block(text: str, block: re.Match[str]) -> str:
    latex_source = _BOXED.sub(r"\1", block.group(1).strip())
    if _is_alone_on_its_line(text, block):
        drawing = _draw_2d(latex_source)
        if drawing is not None:
            return f"\n{drawing}\n"
    flat = _render_flat(latex_source)
    if flat is not None:
        return flat
    return block.group(0)


def _render_inline_match(match: re.Match[str]) -> str:
    flat = _render_flat(_BOXED.sub(r"\1", match.group(1)))
    return flat if flat is not None else match.group(0)


def _is_alone_on_its_line(text: str, block: re.Match[str]) -> bool:
    line_start = text.rfind("\n", 0, block.start()) + 1
    line_end = text.find("\n", block.end())
    if line_end == -1:
        line_end = len(text)
    before = text[line_start : block.start()]
    after = text[block.end() : line_end]
    return not before.strip() and not after.strip()


def _draw_2d(latex_source: str) -> str | None:
    """A faithful multi-line drawing of the formula, or None when that can't be guaranteed."""
    if _UNSUPPORTED_2D_LATEX.search(latex_source):
        return None
    try:
        formula: Any = parse_latex(latex_source, strict=True)  # pyright: ignore[reportUnknownVariableType]
    except Exception:
        return None
    if isinstance(formula, bool) or formula is sympy.true or formula is sympy.false:
        # The parse collapsed the formula to True/False (e.g. an evaluated equality): drawing it would lie.
        return None
    return cast(str, sympy.pretty(formula, use_unicode=True))  # pyright: ignore[reportUnknownMemberType]


def _render_flat(latex_source: str) -> str | None:
    """The formula as a single Unicode line, or None when that can't be guaranteed."""
    try:
        flat: str = _flat_converter.convert(latex_source)  # pyright: ignore[reportUnknownMemberType]
    except Exception:
        return None
    # A leftover backslash means some command wasn't understood (e.g. "\textor").
    return None if "\\" in flat else flat
