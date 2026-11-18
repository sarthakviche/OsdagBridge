"""Tests for repeating table headers and row-group protection."""
from osdagbridge.core.reports.tables import build_longtable, normalize_longtables

BS = "\\"


def _legacy_table(extra_rows=""):
    return (
        BS + "begin{longtable}{|C{2cm}|C{3cm}|}\n"
        + BS + "caption{" + BS + "textbf{My Table}}\n"
        + BS + "hline\n"
        + BS + "textbf{A} & " + BS + "textbf{B} " + BS * 2 + "[6pt]\n"
        + BS + "hline\n"
        + "1 & 2 " + BS * 2 + "[6pt]\n" + BS + "hline\n"
        + extra_rows
        + BS + "end{longtable}"
    )


def test_header_repeats_on_every_page():
    out = normalize_longtables(_legacy_table())
    assert BS + "endfirsthead" in out and BS + "endhead" in out
    # header text appears in both the first head and the repeated head
    assert out.count(BS + "textbf{A}") == 2
    assert BS + "caption[]{" + BS + "textbf{My Table} (continued)}" in out
    # closing rule when the table breaks over a page
    assert BS + "endfoot" in out


def test_caption_is_terminated_with_a_line_end():
    out = normalize_longtables(_legacy_table())
    assert BS + "caption{" + BS + "textbf{My Table}}" + BS * 2 in out


def test_normalisation_is_idempotent():
    once = normalize_longtables(_legacy_table())
    assert normalize_longtables(once) == once


def test_multirow_groups_use_no_break_line_ends():
    group = (
        BS + "multirow{3}{*}{G1} & a " + BS * 2 + "[6pt]\n" + BS + "cline{2-2}\n"
        " & b " + BS * 2 + "[6pt]\n" + BS + "cline{2-2}\n"
        " & c " + BS * 2 + "[6pt]\n" + BS + "hline\n"
    )
    out = normalize_longtables(_legacy_table(group))
    assert out.count(BS * 2 + "*[6pt]") == 2        # first two rows of the 3-row group


def test_tables_without_caption_or_header_are_left_alone_except_groups():
    plain = BS + "begin{longtable}{|c|}\nx " + BS * 2 + "\n" + BS + "end{longtable}"
    assert normalize_longtables(plain) == plain


def test_cells_with_nested_line_breaks_are_not_split():
    cell = BS + "makecell{a" + BS * 2 + "b}"
    body = BS + "multirow{2}{*}{" + cell + "} & x " + BS * 2 + "[6pt]\n & y " + BS * 2 + "[6pt]\n"
    out = normalize_longtables(_legacy_table(body))
    assert cell in out                                # untouched
    assert out.count(BS * 2 + "*[6pt]") == 1


def test_build_longtable_uses_pylatex_with_repeating_header():
    tex = build_longtable("Demo", "|c|c|", [BS + "textbf{X}", BS + "textbf{Y}"],
                          [["1", "2"], ["3", "4"]], note="a note")
    assert BS + "begin{longtable}{|c|c|}" in tex
    assert BS + "endfirsthead" in tex and BS + "endhead" in tex and BS + "endfoot" in tex
    assert tex.count(BS + "textbf{X}") == 2
    assert BS + "osdagNote{a note}" in tex
    assert BS * 2 + "[" + BS + "osdagRowGap]" in tex          # standard inter-row gap applied
