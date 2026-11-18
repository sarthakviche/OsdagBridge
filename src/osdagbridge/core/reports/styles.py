# =============================================================================
# OsdagBridge Report — Centralised Style System (single source of truth)
# =============================================================================
#
# Every visual attribute of the generated design report lives in this module:
#
#   * page geometry & document class options          -> PAGE
#   * colour palette (LaTeX + matplotlib)             -> COLORS
#   * fonts / line spacing / caption look             -> TYPOGRAPHY, CAPTION
#   * table defaults (padding, rules, row gaps, ...)  -> TABLE
#   * running header / footer themes                  -> HEADER_FOOTER
#   * title page, figures, table of contents          -> TITLE_PAGE, FIGURE, TOC
#   * matplotlib chart theme (UR + quantity charts)   -> CHART
#
# Chapter / section generator files (chap*.py, executive_summary.py, ...) must
# NOT hard-code any of these values.  They only use the semantic LaTeX macros
# that ``build_preamble`` defines (``\osdagGap``, ``\osdagNote{..}``,
# ``\osdagPass{..}``, ``\osdagFail{..}``, ``\osdagRowGap`` ...) or the helpers in
# ``tables.py`` / ``charts.py``, which themselves read their settings from here.
# Changing a value below therefore restyles the entire report.
#
# A unit test (tests/unit/test_report_styles.py) fails the build if a chapter
# file re-introduces a hard-coded formatting literal.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Colour palette
# ─────────────────────────────────────────────────────────────────────────────
# HTML hex values (no leading '#').  ``latex_name -> hex``.
COLORS: Dict[str, str] = {
    "osdagGreen":      "91B014",   # brand colour: rules, header line, accents
    "osdagGreenDark":  "5E7A00",   # darker brand tone (chart edges, links)
    "osdagHeaderFill": "EEF3D8",   # table header row background tint
    "osdagStripe":     "F7F9EE",   # (optional) zebra stripe tint
    "osdagPass":       "1B7F3B",   # PASS status text / passing bars
    "osdagFail":       "D00000",   # FAIL status text / failing bars / UR = 1 line
    "osdagWarn":       "1F4E9B",   # design-log WARNING lines
    "osdagGrey":       "6B6B6B",   # secondary text, captions, axis text
    "osdagGridGrey":   "D9D9D9",   # light chart grid
    "osdagSteel":      "4C6A92",   # chart: structural steel
    "osdagConcrete":   "9AA0A6",   # chart: concrete
    "osdagRebar":      "C26A2E",   # chart: reinforcement
    "osdagBrace":      "7A5C9E",   # chart: bracing / diaphragms
}


def hex_color(name: str) -> str:
    """Return ``#RRGGBB`` for a palette entry (used by matplotlib)."""
    return "#" + COLORS[name]


# ─────────────────────────────────────────────────────────────────────────────
# Page / document
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class PageStyle:
    document_class: str = "report"
    class_options: str = "12pt,a4paper"
    # geometry package options
    paper: str = "a4paper"
    margin: str = "1in"
    head_height: str = "15pt"        # fancyhdr needs >= line height of header
    head_sep: str = "14pt"
    foot_skip: str = "38pt"          # room for footer rule + optional note + text
    include_head: bool = False
    # Reserve the footer band always, so body text can never creep into it
    # (fixes rows such as "G4" bleeding into the footer).
    bottom_margin: str = "1.05in"
    top_margin: str = "1in"
    line_stretch: float = 1.15


PAGE = PageStyle()


# ─────────────────────────────────────────────────────────────────────────────
# Typography / captions
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Typography:
    body_stretch: float = PAGE.line_stretch
    chapter_title: str = r"\normalfont\Large\bfseries\centering"
    note_size: str = r"\small"           # \osdagNote{..} text size
    small_size: str = r"\small"
    footnote_size: str = r"\footnotesize"
    title_main: str = r"\Huge\bfseries"
    title_sub: str = r"\large"
    title_doc: str = r"\Large"


TYPOGRAPHY = Typography()


@dataclass(frozen=True)
class CaptionStyle:
    label_font: str = "bf"
    justification: str = "raggedright"
    single_line_check: str = "false"
    fmt: str = "plain"
    skip: str = "6pt"                    # gap between caption and table/figure
    tight_skip: str = "2pt"              # \osdagTightCaptions (dense sub-sections)


CAPTION = CaptionStyle()


# ─────────────────────────────────────────────────────────────────────────────
# Tables
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class TableStyle:
    col_sep: str = "6pt"                 # \tabcolsep  (cell horizontal padding)
    col_sep_compact: str = "3.5pt"       # dense tables (BOM, wide result grids)
    array_stretch: float = 1.12          # row height multiplier
    array_stretch_roomy: float = 1.25    # tables that want extra air
    extra_row_height: str = "0.6pt"      # \extrarowheight (cell top padding)
    rule_width: str = "0.5pt"            # \arrayrulewidth
    row_gap: str = "6pt"                 # extra gap added after every body row
    lt_pre: str = "0pt"                  # \LTpre   (space above a longtable)
    lt_post: str = "6pt"                 # \LTpost  (space below a longtable)
    need_space_lines: int = 6            # float tables: start on a new page if fewer
                                         # than this many lines remain
    need_space_lines_longtable: int = 0  # longtables manage their own start; 0 = off
                                         # (a \needspace hook here made longtable
                                         # re-print its first head on a fresh page)
    # --- standard column widths -----------------------------------------
    col_key: str = "5.5cm"               # "parameter" column of key/value tables
    col_value: str = "10.0cm"            # "value" column
    # --- header / continuation behaviour --------------------------------
    header_fill: str = "osdagHeaderFill" # colour name from COLORS, or "" for none
    repeat_header: bool = True           # repeat header row on every page
    continued_suffix: str = r" (continued)"
    keep_row_groups: bool = True         # forbid page breaks inside \multirow groups
    # --- vertical gaps used between blocks (em-based tiers) --------------
    gap_xs: str = "0.3em"                # \osdagGapXS
    gap_small: str = "0.5em"             # \osdagGapS
    gap_medium: str = "0.8em"            # \osdagGapM
    gap: str = "1em"                     # \osdagGap   : after a table / block
    gap_large: str = "2em"               # \osdagGapL  : before big blocks
    cell_gap: str = "3pt"                # line gap inside a \makecell cell
    col_value_narrow: str = "8.5cm"      # value column of the summary tables


TABLE = TableStyle()


# ─────────────────────────────────────────────────────────────────────────────
# Header / footer
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class HeaderFooterStyle:
    footer_left: str = r"Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay"
    footer_right: str = r"Page \thepage\ of \pageref{LastPage}"
    header_left: str = r"{project} $|$ {job}"
    header_right: str = r"{date} $|$ {version}"
    rule_width: str = "1pt"
    software_default_note: str = r"* Software default value"


HEADER_FOOTER = HeaderFooterStyle()


# ─────────────────────────────────────────────────────────────────────────────
# Title page / figures / TOC
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class TitlePageStyle:
    top_space: str = "1.5cm"
    logo_left_width: str = "0.6"         # fraction of \textwidth
    logo_right_width: str = "0.35"
    org_logo_height: str = "2.2cm"
    after_logos: str = "1cm"
    after_title: str = "0.3cm"
    after_subtitle: str = "1.5cm"
    after_doc_title: str = "1.5cm"
    info_colspec: str = "|L{4cm}|L{10cm}|"


TITLE_PAGE = TitlePageStyle()


@dataclass(frozen=True)
class FigureStyle:
    placement: str = "H"
    default_width: str = r"0.9\textwidth"
    full_width: str = r"\textwidth"
    chart_width: str = r"0.82\textwidth"
    caption_size: str = r"\small"
    pre_gap: str = "-0.5em"
    post_gap: str = "0.5em"
    placeholder_width: str = r"0.97\textwidth"


FIGURE = FigureStyle()


@dataclass(frozen=True)
class TocStyle:
    depth: int = 2
    title: str = r"\centering\Large\bfseries Table of Contents"
    chapter_space_after_summary: str = "-30pt"   # \titlespacing before-skip once the
                                                  # un-numbered Executive Summary is done
    chapter: Tuple[str, str, str] = ("1.5em", "1.5em", "-1.5em")   # indent, label, hang
    section: Tuple[str, str, str] = ("3.8em", "2.3em", "-2.3em")
    subsection: Tuple[str, str, str] = ("7.0em", "3.2em", "-3.2em")


TOC = TocStyle()


# ─────────────────────────────────────────────────────────────────────────────
# matplotlib chart theme
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ChartStyle:
    dpi: int = 200
    figsize_overall: Tuple[float, float] = (7.2, 4.0)
    figsize_detail: Tuple[float, float] = (7.2, 4.6)
    figsize_quantity: Tuple[float, float] = (7.2, 3.8)
    font_family: str = "DejaVu Sans"
    font_size: float = 9.0
    title_size: float = 10.5
    label_size: float = 9.0
    bar_width: float = 0.55
    bar_edge_width: float = 0.8
    threshold_value: float = 1.0
    threshold_width: float = 1.4
    threshold_label: str = "UR = 1.0 (limit)"
    y_headroom: float = 1.18             # axis max = max(value, 1.0) * headroom
    value_label_fmt: str = "{:.2f}"
    unavailable_text: str = "N/A"
    pass_color: str = "osdagPass"
    fail_color: str = "osdagFail"
    threshold_color: str = "osdagFail"
    grid_color: str = "osdagGridGrey"
    text_color: str = "osdagGrey"


CHART = ChartStyle()

# Element -> (display name, bar colour name).  Order = left-to-right on charts.
UR_ELEMENTS: List[Tuple[str, str]] = [
    ("Steel Plate Girders", "osdagSteel"),
    ("Concrete Deck Slab", "osdagConcrete"),
    ("Cross Bracing", "osdagBrace"),
    ("End Diaphragms", "osdagGreenDark"),
]


# ─────────────────────────────────────────────────────────────────────────────
# LaTeX generation helpers
# ─────────────────────────────────────────────────────────────────────────────
# (package, options) — order matters for a few packages (hyperref late, etc.)
PACKAGES: List[Tuple[str, str]] = [
    ("graphicx", ""), ("amsmath", ""), ("amssymb", ""), ("booktabs", ""),
    ("array", ""), ("tabularx", ""), ("float", ""), ("fancyhdr", ""),
    ("hyperref", "hidelinks"), ("xcolor", "table"), ("setspace", ""),
    ("enumitem", ""), ("caption", ""), ("subcaption", ""), ("multirow", ""),
    ("longtable", ""), ("titlesec", ""), ("titletoc", ""), ("lastpage", ""),
    ("makecell", ""), ("etoolbox", ""), ("needspace", ""),
]


def _packages_tex() -> str:
    lines = []
    for name, opts in PACKAGES:
        if name == "caption":
            # configured right after loading (needs to precede subcaption)
            lines.append(r"\usepackage{caption}")
            lines.append(
                "\\captionsetup{\n"
                f"    labelfont={CAPTION.label_font},\n"
                f"    justification={CAPTION.justification},\n"
                f"    singlelinecheck={CAPTION.single_line_check},\n"
                f"    format={CAPTION.fmt},\n"
                f"    skip={CAPTION.skip}\n"
                "}"
            )
        elif opts:
            lines.append(r"\usepackage[" + opts + "]{" + name + "}")
        else:
            lines.append(r"\usepackage{" + name + "}")
    return "\n".join(lines)


def _geometry_tex() -> str:
    opts = [
        PAGE.paper,
        f"left={PAGE.margin}", f"right={PAGE.margin}",
        f"top={PAGE.top_margin}", f"bottom={PAGE.bottom_margin}",
        f"headheight={PAGE.head_height}", f"headsep={PAGE.head_sep}",
        f"footskip={PAGE.foot_skip}",
    ]
    if PAGE.include_head:
        opts.append("includehead")
    return r"\usepackage[" + ", ".join(opts) + "]{geometry}"


def _colors_tex() -> str:
    return "\n".join(
        r"\definecolor{" + n + "}{HTML}{" + h + "}" for n, h in COLORS.items()
    )


def _cline_nobreak_tex() -> str:
    r"""Make ``\\*`` effective for rows separated by ``\cline``.

    ``\cline`` typesets a zero-height row followed by a negative skip; that skip
    is a legal page-break point even after ``\\*``, so a ``\multirow`` group
    could still be split across pages.  Forbidding the break around the skip
    keeps each group in one piece.
    """
    old = r"\noalign{\vskip-\arrayrulewidth}"
    new = r"\noalign{\nobreak\vskip-\arrayrulewidth\nobreak}"
    return "\n".join([
        r"\makeatletter",
        r"\patchcmd{\@cline}{" + old + "}{" + new + r"}{}"
        r"{\PackageWarning{osdagbridge}{could not patch \string\cline}}",
        r"\makeatother",
    ])


def _table_settings_tex() -> str:
    t = TABLE
    keep_groups = _cline_nobreak_tex() if t.keep_row_groups else ""
    return "\n".join([
        r"\numberwithin{table}{chapter}",
        r"\numberwithin{figure}{chapter}",
        r"\setlength{\LTleft}{\fill}",
        r"\setlength{\LTright}{\fill}",
        r"\setlength{\tabcolsep}{" + t.col_sep + "}",
        r"\renewcommand{\arraystretch}{" + str(t.array_stretch) + "}",
        r"\setlength{\LTpre}{" + t.lt_pre + "}",
        r"\setlength{\LTpost}{" + t.lt_post + "}",
        r"\setlength{\arrayrulewidth}{" + t.rule_width + "}",
        r"\setlength{\extrarowheight}{" + t.extra_row_height + "}",
        r"\newlength{\osdagRowGap}\setlength{\osdagRowGap}{" + t.row_gap + "}",
        r"\newlength{\osdagColKey}\setlength{\osdagColKey}{" + t.col_key + "}",
        r"\newlength{\osdagColVal}\setlength{\osdagColVal}{" + t.col_value + "}",
        r"\newcommand{\osdagTabcolsepCompact}{\setlength{\tabcolsep}{" + t.col_sep_compact + "}}",
        r"\newcommand{\osdagArrayRoomy}{\renewcommand{\arraystretch}{" + str(t.array_stretch_roomy) + "}}",
        r"\newlength{\osdagCellGap}\setlength{\osdagCellGap}{" + t.cell_gap + "}",
        r"\newlength{\osdagColValNarrow}\setlength{\osdagColValNarrow}{" + t.col_value_narrow + "}",
        keep_groups,
        "% Never start a table in the last few lines of a page:",
        r"\BeforeBeginEnvironment{table}{\needspace{" + str(t.need_space_lines) + r"\baselineskip}}",
        (r"\BeforeBeginEnvironment{longtable}{\needspace{" + str(t.need_space_lines_longtable)
         + r"\baselineskip}}") if t.need_space_lines_longtable else "",
    ])


def _macros_tex() -> str:
    t = TABLE
    ty = TYPOGRAPHY
    f = FIGURE
    return "\n".join([
        "% ---- semantic macros consumed by the chapter generators ----",
        r"\newcommand{\osdagGap}{\vspace{" + t.gap + "}}",
        r"\newcommand{\osdagGapXS}{\vspace{" + t.gap_xs + "}}",
        r"\newcommand{\osdagGapS}{\vspace{" + t.gap_small + "}}",
        r"\newcommand{\osdagGapM}{\vspace{" + t.gap_medium + "}}",
        r"\newcommand{\osdagGapL}{\vspace{" + t.gap_large + "}}",
        r"\newcommand{\osdagChapterHead}{" + ty.chapter_title + "}",
        r"\newcommand{\osdagRestoreChapterFormat}{"
        r"\titleformat{\chapter}[block]{" + ty.chapter_title + r"}{\thechapter}{1em}{}"
        r"\titlespacing*{\chapter}{0pt}{" + TOC.chapter_space_after_summary + r"}{10pt}}",
        r"\newcommand{\osdagFigPre}{\vspace{" + f.pre_gap + "}}",
        r"\newcommand{\osdagFigPost}{\vspace{" + f.post_gap + "}}",
        r"\newcommand{\osdagNote}[1]{\noindent{" + ty.note_size + r"\textit{#1}}}",
        r"\newcommand{\osdagSmall}{" + ty.small_size + "}",
        r"\newcommand{\osdagFootnoteSize}{" + ty.footnote_size + "}",
        r"\newcommand{\osdagCaptionSize}{" + f.caption_size + "}",
        r"\newcommand{\osdagPass}[1]{\textcolor{osdagPass}{#1}}",
        r"\newcommand{\osdagFail}[1]{\textcolor{osdagFail}{\textbf{#1}}}",
        r"\newcommand{\osdagMuted}[1]{\textcolor{osdagGrey}{#1}}",
        r"\newcommand{\osdagLogWarn}[1]{\textcolor{osdagWarn}{#1}}",
        r"\newcommand{\osdagLogError}[1]{\textcolor{osdagFail}{#1}}",
        r"\newcommand{\osdagLogInfo}[1]{\textcolor{osdagGreen}{#1}}",
        r"\newcommand{\osdagTightCaptions}{\setlength{\abovecaptionskip}{" + CAPTION.tight_skip
        + r"}\setlength{\belowcaptionskip}{" + CAPTION.tight_skip + "}}",
        r"\newcommand{\osdagTableLeft}{\setlength{\LTleft}{0pt}\setlength{\LTright}{\fill}}",
        r"\newcommand{\placeholder}[1]{\textit{\textless #1\textgreater}}",
        r"\newcommand{\todo}[1]{\colorbox{yellow}{TODO: #1}}",
        r"\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}",
        r"\newcolumntype{C}[1]{>{\centering\arraybackslash}p{#1}}",
        r"\newcolumntype{R}[1]{>{\raggedleft\arraybackslash}p{#1}}",
        "",
        "% Software-default asterisk (page footer notes it when used on the page)",
        r"\newcommand{\sdstar}{\textsuperscript{*}}",
        r"\newbool{hasSDonPage}",
        r"\boolfalse{hasSDonPage}",
        r"\newcommand{\markSD}{\global\booltrue{hasSDonPage}}",
        r"\renewcommand{\sdstar}{\textsuperscript{*}\markSD{}}",
        r"\AddToHook{shipout/before}{\global\boolfalse{hasSDonPage}}",
    ])


def _page_styles_tex(project: str, job: str, date: str, version: str) -> str:
    hf = HEADER_FOOTER
    rw = hf.rule_width
    head_l = hf.header_left.format(project=project, job=job)
    head_r = hf.header_right.format(date=date, version=version)

    # The "software default" note sits INSIDE the reserved footer band, on its
    # own line above the footer text — it no longer uses negative vertical space
    # (which pulled content into the body area on some pages).
    foot_rule = (
        r"\renewcommand{\footrule}{\color{osdagGreen}\hrule width\headwidth height " + rw + r"}"
    )
    note = (
        r"\ifbool{hasSDonPage}{{\osdagFootnoteSize\textit{" + hf.software_default_note + r"}}\\[1pt]}{}"
    )
    main = "\n".join([
        r"\fancyhf{}",
        r"\fancyhead[L]{" + head_l + "}",
        r"\fancyhead[R]{" + head_r + "}",
        r"\fancyfoot[L]{\begin{tabular}[b]{@{}l@{}}" + note + hf.footer_left + r"\end{tabular}}",
        r"\fancyfoot[R]{" + hf.footer_right + "}",
        r"\renewcommand{\headrule}{\color{osdagGreen}\hrule width\headwidth height " + rw + r" \vspace{2pt}}",
        foot_rule,
    ])
    first = "\n".join([
        r"\fancyhf{}",
        r"\renewcommand{\headrulewidth}{0pt}",
        r"\fancyfoot[L]{" + hf.footer_left + "}",
        r"\fancyfoot[R]{" + hf.footer_right + "}",
        foot_rule,
    ])
    return (
        "\\fancypagestyle{main}{\n" + main + "\n}\n"
        "\\fancypagestyle{plain}{\n" + main + "\n}\n"
        "\\fancypagestyle{firstpage}{\n" + first + "\n}\n"
        r"\pagestyle{main}" + "\n"
        r"\setstretch{" + str(TYPOGRAPHY.body_stretch) + "}"
    )


def build_preamble(project: str, job: str, date: str, version: str = "Rev 0") -> str:
    """Return the complete LaTeX preamble (up to and including \\begin{document}).

    ``project``, ``job``, ``date`` and ``version`` must already be LaTeX-escaped.
    """
    title = (
        r"\title{\Large\textbf{OsdagBridge} \\ \normalsize Open Source Software for "
        r"Steel Girder Bridge Design \\ \vspace{2cm} \large Design Report}"
    )
    return "\n".join([
        r"\documentclass[" + PAGE.class_options + "]{" + PAGE.document_class + "}",
        "",
        "% Packages",
        _geometry_tex(),
        _packages_tex(),
        "",
        "% Colours",
        _colors_tex(),
        "",
        "% Table layout, spacing and rules",
        _table_settings_tex(),
        "",
        "% Header / footer",
        _page_styles_tex(project, job, date, version),
        "",
        _macros_tex(),
        "",
        title,
        r"\author{}",
        r"\date{}",
        "",
        r"\begin{document}",
        "",
    ])


def build_toc_formatting() -> str:
    """LaTeX that styles chapter titles / TOC entries and emits the TOC."""
    c, s, ss = TOC.chapter, TOC.section, TOC.subsection
    return "\n".join([
        "% Chapter / TOC Formatting",
        r"\titleformat{\chapter}[block]",
        r"  {" + TYPOGRAPHY.chapter_title + r"}{\thechapter}{1em}{}",
        r"\titlespacing*{\chapter}{0pt}{0pt}{10pt}",
        r"\setcounter{tocdepth}{" + str(TOC.depth) + "}",
        "",
        r"\titlecontents{chapter}[" + c[0] + "]",
        r"  {\normalfont\vspace{2pt}}",
        r"  {\contentslabel{" + c[1] + "}}",
        r"  {\hspace*{" + c[2] + "}}",
        r"  {\hfill\contentspage}",
        "",
        r"\titlecontents{section}[" + s[0] + "]",
        r"  {\normalfont}",
        r"  {\contentslabel{" + s[1] + "}}",
        r"  {\hspace*{" + s[2] + "}}",
        r"  {\hfill\contentspage}",
        "",
        r"\titlecontents{subsection}[" + ss[0] + "]",
        r"  {\normalfont}",
        r"  {\contentslabel{" + ss[1] + "}}",
        r"  {\hspace*{" + ss[2] + "}}",
        r"  {\hfill\contentspage}",
        "",
        r"\newpage",
        r"\renewcommand{\contentsname}{" + TOC.title + "}",
        r"\tableofcontents",
        "",
    ])


def build_title_page(project: str, location: str, designer: str, reviewer: str,
                     company: str, client: str, job: str, date: str, version: str,
                     osdag_logo: str | None, org_logo: str | None) -> str:
    """LaTeX for the title page. All text args must already be escaped."""
    tp = TITLE_PAGE
    lhs = (r"\includegraphics[width=\linewidth,keepaspectratio]{" + osdag_logo.replace("\\", "/") + "}"
           if osdag_logo else r"\textit{(Osdag Logo)}")
    rhs = (r"\includegraphics[width=\linewidth,height=" + tp.org_logo_height +
           r",keepaspectratio]{" + org_logo.replace("\\", "/") + "}" if org_logo else "")
    ty = TYPOGRAPHY
    rows = [
        ("Project Name", project), ("Project Location", location),
        ("Author / Designer", designer), ("Reviewer", reviewer),
        ("Organization", company), ("Client Name and Organization", client),
        ("Job Number", job), ("Date", date), ("Report Version", version),
    ]
    body = "\n".join(
        r"\textbf{" + k + "} & " + v + r" \\" + "\n" + r"\hline" for k, v in rows
    )
    return (
        "\\begin{titlepage}\n"
        "\\thispagestyle{firstpage}\n"
        "\\centering\n"
        "\\vspace*{" + tp.top_space + "}\n"
        "\\noindent\n"
        "\\begin{minipage}[c]{" + tp.logo_left_width + "\\textwidth}\n\\raggedright\n" + lhs + "\n\\end{minipage}%\n"
        "\\hfill\n"
        "\\begin{minipage}[c]{" + tp.logo_right_width + "\\textwidth}\n\\raggedleft\n" + rhs + "\n\\end{minipage}\n"
        "\\\\[" + tp.after_logos + "]\n"
        "{" + ty.title_main + r" OsdagBridge}\\[" + tp.after_title + "]\n"
        "{" + ty.title_sub + r" Open Source Software for Steel Girder Bridge Design}\\[" + tp.after_subtitle + "]\n"
        "{" + ty.title_doc + r" Design Report}\\[" + tp.after_doc_title + "]\n"
        "\\begin{tabular}{" + tp.info_colspec + "}\n"
        "\\hline\n" + body + "\n"
        "\\end{tabular}\n"
        "\\end{titlepage}\n"
    )
