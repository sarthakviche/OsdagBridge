# =============================================================================
# OsdagBridge Report — Table utilities
# =============================================================================
#
# 1. ``build_longtable``     — builds a PyLaTeX ``LongTable`` (caption, repeating
#                              header via \endfirsthead / \endhead, closing rule
#                              via \endfoot).  Used for every NEW table.
# 2. ``normalize_longtables`` — post-processes the assembled document and gives
#                              every legacy raw-LaTeX ``longtable`` the same
#                              treatment: terminated caption, repeated column
#                              header on each page, "(continued)" caption,
#                              closing rule at page breaks, and no page break
#                              inside a \multirow row group.
#
# All look-and-feel values come from ``styles.TABLE``.
# =============================================================================

from __future__ import annotations

import re
from typing import Iterable, List, Optional, Sequence, Tuple

from pylatex import Command, LongTable
from pylatex.utils import NoEscape

from .styles import TABLE

_BEGIN = r"\begin{longtable}"
_END = r"\end{longtable}"
_ROW_GAP_MACRO = r"\osdagRowGap"
HLINE = r"\hline"


# ─────────────────────────────────────────────────────────────────────────────
# Low-level scanning helpers
# ─────────────────────────────────────────────────────────────────────────────
def _match_brace(s: str, i: int) -> int:
    """``s[i] == '{'`` -> index just after the matching ``}`` (escape-aware)."""
    assert s[i] == "{"
    depth = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unbalanced braces in LaTeX table block")


def _skip_ws(s: str, i: int) -> int:
    while i < len(s) and s[i] in " \t\r\n":
        i += 1
    return i


def _split_rows(body: str) -> List[Tuple[str, str]]:
    """Split a table body into ``(row_text, terminator)`` pairs.

    A terminator is a ``\\\\`` at brace depth 0, optionally followed by ``*``
    and/or ``[len]``.  Row text keeps any leading rules (``\\hline`` etc.).
    The last pair may have an empty terminator (trailing text).
    """
    rows: List[Tuple[str, str]] = []
    depth = 0
    start = 0
    i = 0
    n = len(body)
    while i < n:
        c = body[i]
        if c == "\\":
            if i + 1 < n and body[i + 1] == "\\" and depth == 0:
                j = i + 2
                if j < n and body[j] == "*":
                    j += 1
                if j < n and body[j] == "[":
                    k = body.find("]", j)
                    if k != -1:
                        j = k + 1
                rows.append((body[start:i], body[i:j]))
                start = j
                i = j
                continue
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    if start < n:
        rows.append((body[start:], ""))
    return rows


_LEADING_RULES = re.compile(r"^(\s*(\\hline|\\cline\{[^}]*\})\s*)*")
_MULTIROW = re.compile(r"^\\multirow\{(\d+)\}")


def _keep_row_groups_together(body: str) -> str:
    """Forbid page breaks inside \\multirow groups by using ``\\\\*``."""
    rows = _split_rows(body)
    remaining = 0
    out: List[str] = []
    for text, term in rows:
        stripped = _LEADING_RULES.sub("", text, count=1).lstrip()
        m = _MULTIROW.match(stripped)
        if m:
            remaining = max(remaining, int(m.group(1)) - 1)
        if remaining > 0 and term.startswith("\\\\") and not term.startswith("\\\\*"):
            term = "\\\\*" + term[2:]
            remaining -= 1
        elif remaining > 0 and term:
            remaining -= 1
        out.append(text + term)
    return "".join(out)


def _is_header_row(row_text: str) -> bool:
    t = row_text.lstrip()
    return t.startswith("\\textbf") or t.startswith("\\multicolumn") or t.startswith("\\rowcolor")


# ─────────────────────────────────────────────────────────────────────────────
# Legacy longtable normaliser
# ─────────────────────────────────────────────────────────────────────────────
def _caption_parts(rest: str) -> Tuple[Optional[str], Optional[str], str]:
    """Return ``(caption_cmd, caption_text, remainder)`` if *rest* starts with \\caption."""
    rest = rest.lstrip()
    if not rest.startswith("\\caption"):
        return None, None, rest
    i = len("\\caption")
    if i < len(rest) and rest[i] == "[":
        i = rest.index("]", i) + 1
    i = _skip_ws(rest, i)
    j = _match_brace(rest, i)
    caption_cmd = rest[:j]
    caption_text = rest[i + 1:j - 1]
    k = _skip_ws(rest, j)
    # swallow an existing explicit line end so we never emit it twice
    if rest.startswith("\\\\", k):
        k += 2
    elif rest.startswith("\\tabularnewline", k):
        k += len("\\tabularnewline")
    return caption_cmd, caption_text, rest[k:]


def _normalize_block(block: str) -> str:
    spec_start = len(_BEGIN)
    if block[spec_start] == "[":                       # optional alignment arg
        spec_start = block.index("]", spec_start) + 1
    spec_start = _skip_ws(block, spec_start)
    spec_end = _match_brace(block, spec_start)
    head = block[:spec_end]
    inner = block[spec_end:-len(_END)]

    if "\\endfirsthead" in inner or "\\endhead" in inner:
        return block                                    # already hand-built

    caption_cmd, caption_text, rest = _caption_parts(inner)

    # ── optional header block: \hline <header rows> \hline <body> ────────────
    rest_l = rest.lstrip()
    header_rows: List[str] = []
    body = rest_l
    if rest_l.startswith(HLINE):
        after = rest_l[len(HLINE):]
        body = after                                   # top rule is re-emitted below
        rows = _split_rows(after)
        k = 0
        hdr: List[str] = []
        while k < len(rows) and rows[k][1] and _is_header_row(rows[k][0]):
            hdr.append(rows[k][0].strip() + rows[k][1])
            k += 1
        if hdr and k < len(rows) and rows[k][0].lstrip().startswith(HLINE):
            first_text, first_term = rows[k]
            first_text = first_text.lstrip()[len(HLINE):]
            body = first_text + first_term + "".join(t + e for t, e in rows[k + 1:])
            header_rows = hdr

    if caption_cmd is None and not header_rows:
        # nothing to repeat — only apply row-group protection
        if TABLE.keep_row_groups:
            return head + _keep_row_groups_together(inner) + _END
        return block

    if TABLE.keep_row_groups:
        body = _keep_row_groups_together(body)

    fill = (r"\rowcolor{" + TABLE.header_fill + "}") if TABLE.header_fill else ""
    hdr_tex = ("\n".join(fill + r if i == 0 else r for i, r in enumerate(header_rows))
               if header_rows else "")
    out: List[str] = [head]
    cont_caption = None
    if caption_cmd is not None:
        out.append(caption_cmd + r"\\")
        cont_caption = (r"\caption[]{" + caption_text + TABLE.continued_suffix + r"}\\")
    out.append(r"\hline")
    if hdr_tex:
        out.append(hdr_tex)
        out.append(r"\hline")
    if TABLE.repeat_header and (header_rows or cont_caption):
        out.append(r"\endfirsthead")
        if cont_caption:
            out.append(cont_caption)
        out.append(r"\hline")
        if hdr_tex:
            out.append(hdr_tex)
            out.append(r"\hline")
        out.append(r"\endhead")
        out.append(r"\hline")
        out.append(r"\endfoot")
    out.append(body.lstrip("\n"))
    out.append(_END)
    return "\n".join(out)


def normalize_longtables(tex: str) -> str:
    """Give every raw ``longtable`` in *tex* repeating headers, see module doc."""
    out: List[str] = []
    pos = 0
    while True:
        b = tex.find(_BEGIN, pos)
        if b < 0:
            out.append(tex[pos:])
            break
        e = tex.find(_END, b)
        if e < 0:
            out.append(tex[pos:])
            break
        out.append(tex[pos:b])
        e_end = e + len(_END)
        out.append(_normalize_block(tex[b:e_end]))
        pos = e_end
    return "".join(out)


# ─────────────────────────────────────────────────────────────────────────────
# PyLaTeX builder for new tables
# ─────────────────────────────────────────────────────────────────────────────
def _apply_row_gap(tex: str) -> str:
    """Append the standard inter-row gap to rows that end with a bare ``\\\\``."""
    # PyLaTeX terminates rows with "\\" + "%" (comment) + newline; accept both forms.
    return re.sub(r"\\\\(?=%?[ \t]*(?:\r?\n|$))", lambda m: "\\\\[" + _ROW_GAP_MACRO + "]", tex)


def build_longtable(
    caption: str,
    colspec: str,
    header: Sequence[str],
    rows: Iterable[Sequence[str]],
    *,
    header_rows: Optional[Sequence[Sequence[str]]] = None,
    header_midrules: Optional[Sequence[str]] = None,
    note: Optional[str] = None,
    bold_caption: bool = True,
    compact: bool = False,
) -> str:
    """Build a PyLaTeX ``LongTable`` as a LaTeX string.

    Parameters
    ----------
    caption, colspec : caption text and LaTeX column spec (``|C{2cm}|L{4cm}|``).
    header           : header cells (already LaTeX).  Ignored if *header_rows* is set.
    rows             : iterable of rows; each row is a sequence of LaTeX cell strings.
    header_rows      : several header rows (e.g. a grouped ``\\multicolumn`` header).
    header_midrules  : rule commands (``\\cline{4-6}``) drawn after each header row
                       except the last, one per gap between header rows.
    note             : optional footnote placed under the table via ``\\osdagNote``.
    compact          : wrap the table in the compact cell-padding group.
    """
    hdr_rows = [list(r) for r in header_rows] if header_rows else [list(header)]
    ncols = max(len(r) for r in hdr_rows)

    def _header(lt: LongTable) -> None:
        lt.add_hline()
        for k, r in enumerate(hdr_rows):
            lt.add_row(
                *r, escape=False, strict=False,
                color=TABLE.header_fill or None,
            )
            if header_midrules and k < len(hdr_rows) - 1 and k < len(header_midrules):
                lt.append(NoEscape(header_midrules[k]))
        lt.add_hline()

    lt = LongTable(NoEscape(colspec), width=ncols, pos=None)
    cap = r"\textbf{" + caption + "}" if bold_caption else caption
    lt.append(NoEscape(r"\caption{" + cap + r"}\\"))
    _header(lt)
    lt.append(Command("endfirsthead"))
    lt.append(NoEscape(r"\caption[]{" + cap + TABLE.continued_suffix + r"}\\"))
    _header(lt)
    lt.append(Command("endhead"))
    lt.add_hline()
    lt.append(Command("endfoot"))
    for r in rows:
        lt.add_row(*r, escape=False, strict=False)
        lt.add_hline()

    tex = _apply_row_gap(lt.dumps())
    if TABLE.keep_row_groups:
        # (new tables never use \multirow groups spanning pages, kept for symmetry)
        pass
    if compact:                       # tighter cell padding for wide tables
        tex = "\\begingroup\\osdagTabcolsepCompact\n" + tex + "\n\\endgroup"
    if note:
        tex += "\n" + r"\nopagebreak" + "\n" + r"\osdagNote{" + note + "}\n"
    return tex + "\n"
