"""Single-source-of-truth guard for the report generator.

Chapter / section generator files must not hard-code formatting: every layout
or visual attribute is defined in ``osdagbridge.core.reports.styles`` and
reached through semantic macros (``\\osdagGap``, ``\\osdagNote{..}``, ...).
"""
import re
from pathlib import Path

import pytest

from osdagbridge.core.reports import styles

REPORTS = Path(styles.__file__).parent
CHAPTER_FILES = sorted(
    [*REPORTS.glob("chap*.py"), REPORTS / "executive_summary.py",
     REPORTS / "report_utils.py", REPORTS / "load_tables.py"]
)

BS = "\\"
# LaTeX formatting commands that may only be written in styles.py / tables.py.
FORBIDDEN = {
    "raw vertical space": re.escape(BS + "vspace"),
    "raw colour": re.escape(BS + "textcolor") + "|" + re.escape(BS + "color{") + "|"
                  + re.escape(BS + "definecolor") + "|" + re.escape(BS + "rowcolor")
                  + "|" + re.escape(BS + "cellcolor"),
    "raw length setting": re.escape(BS + "setlength"),
    "raw array stretch": "arraystretch",
    "raw font size": re.escape(BS) + r"(?:tiny|scriptsize|small|footnotesize|large|Large|LARGE|huge|Huge)\b",
    "raw page geometry": re.escape(BS + "geometry") + "|" + re.escape(BS + "newgeometry") + "|margin=",
    "raw package": re.escape(BS + "usepackage"),
    "literal row gap": re.escape(BS * 2) + r"\[\d+(?:\.\d+)?(?:pt|em|cm|mm)\]",
}


@pytest.mark.parametrize("path", CHAPTER_FILES, ids=lambda p: p.name)
def test_chapter_files_have_no_hardcoded_formatting(path):
    source = path.read_text(encoding="utf-8")
    offences = []
    for what, pattern in FORBIDDEN.items():
        for m in re.finditer(pattern, source):
            line = source.count("\n", 0, m.start()) + 1
            offences.append(f"{path.name}:{line}: {what}: {m.group(0)!r}")
    assert not offences, "hard-coded formatting found:\n" + "\n".join(offences)


def test_every_macro_used_by_chapters_is_defined_in_preamble():
    preamble = styles.build_preamble("P", "J", "D", "R")
    used = set()
    for path in CHAPTER_FILES:
        used |= set(re.findall(re.escape(BS) + r"(osdag[A-Za-z]+)", path.read_text(encoding="utf-8")))
    # macros that only appear as helper identifiers (python names) are filtered by
    # requiring a definition for each LaTeX use
    missing = sorted(m for m in used
                     if (BS + "newcommand{" + BS + m + "}") not in preamble
                     and (BS + "newlength{" + BS + m + "}") not in preamble)
    assert not missing, f"macros used but not defined by styles.build_preamble: {missing}"


def test_preamble_defines_palette_and_geometry():
    pre = styles.build_preamble("Proj", "J-1", "2026-01-01", "Rev 0")
    for name in styles.COLORS:
        assert BS + "definecolor{" + name + "}" in pre
    assert "geometry" in pre and "footskip=" in pre
    assert BS + "begin{document}" in pre


def test_changing_a_style_value_restyles_the_preamble(monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(styles, "TABLE", replace(styles.TABLE, row_gap="9pt"))
    assert "9pt" in styles.build_preamble("P", "J", "D", "R")
