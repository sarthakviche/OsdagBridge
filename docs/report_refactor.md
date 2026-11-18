# OsdagBridge LaTeX Report Generator — Refactoring & Enhancements

Technical changes document. Scope: `src/osdagbridge/core/reports/`.

## 1. Summary

| Task item | What changed | Where |
|---|---|---|
| 1. Repeated table headers | Every `longtable` gets `\endfirsthead` / `\endhead`, a "(continued)" caption and a closing rule at page breaks. New tables are built with PyLaTeX `LongTable`; the 49 existing raw-LaTeX tables are normalised by a brace-aware post-processor. | `tables.py`, `report_generator.py` |
| 2. Footer overlap / spacing | Footer band is reserved by the page geometry; the "* Software default value" note moved out of negative vertical space into that band; `\multirow` groups can no longer split across pages; longtable `\needspace` hook removed (it made longtable re-print its first head). | `styles.py`, `tables.py` |
| 3. Load tables | Vehicular and footpath live loads are separate PyLaTeX tables. Rows follow the vehicles selected in the UI; columns: total load (kN), impact factor, braking *considered / value (kN) / eccentricity (m)*. | `load_tables.py`, `chap3.py` |
| 4. UR charts | Overall (governing UR per element) and per-check bar charts with a red dashed UR = 1.0 line; embedded in Section 5.5. | `charts.py`, `chap5.py` |
| 5. Quantity charts | Structural steel tonnage (girders / cross bracing / end diaphragms) and concrete volume vs. reinforcement weight; saved to a temp asset dir and embedded via PyLaTeX `Figure`. | `charts.py`, `chap7.py` |
| 6. Central style system | `styles.py` is the single source of truth. Chapter files contain **no** hard-coded formatting; a unit test enforces this. | `styles.py`, `tests/unit/test_report_styles.py` |

Measured on the same design (30 m span, 5 girders, single footpath):

| | Before | After |
|---|---|---|
| longtables with a repeating header | 2 / 49 | 50 / 50 |
| hard-coded `\\[6pt]` row gaps in chapters | 561 | 0 |
| hard-coded `\vspace` / `\textcolor` in chapters | 81 / 19 | 0 / 0 |
| `\multirow` groups split across pages | yes (e.g. Table 5.7, girder G2) | no |
| charts | none | 4 (2 UR, 2 quantity) |

## 2. Files altered under the report generator

New:

* `styles.py` — central style module (see §3)
* `tables.py` — PyLaTeX `LongTable` builder + longtable normaliser
* `charts.py` — matplotlib charts + PyLaTeX `Figure` embedding
* `load_tables.py` — Chapter 3 live-load data + tables

Modified:

* `report_generator.py` — preamble / title page / TOC now delegate to `styles.py`; `normalize_longtables()` applied to the assembled document; creates the temporary `charts/` directory and passes it to chapters 5 and 7.
* `chap1.py … chap9.py`, `executive_summary.py`, `report_utils.py` — raw formatting literals replaced by semantic macros; `chap3.py` uses `load_tables`; `chap5.py` records UR values and embeds the charts; `chap7.py` embeds the quantity charts.
* `environment.yml`, `requirements.txt`, `pyproject.toml` — add the `pylatex` dependency.

Tests added: `tests/unit/test_report_styles.py`, `test_report_tables.py`, `test_report_charts.py`, `test_report_load_tables.py` (+ `conftest.py`).

## 3. Structure of the centralised style module (`styles.py`)

```
COLORS            palette: osdagGreen, osdagPass, osdagFail, osdagHeaderFill, chart colours ...
PAGE              document class, geometry (margins, head height, footskip, bottom reserve)
TYPOGRAPHY        line stretch, note / small / title sizes, chapter-title format
CAPTION           caption font, justification, skips
TABLE             tabcolsep, arraystretch, rule width, row gap, LTpre/LTpost, header fill,
                  standard column widths, gap tiers (XS / S / M / base / L), keep-row-groups
HEADER_FOOTER     header / footer texts and rule width, "software default" note
TITLE_PAGE        title-page spacing, logo widths, info-table column spec
FIGURE            placement, default / chart widths, caption size
TOC               depth, title, per-level indents
CHART             dpi, figure sizes, fonts, bar width, UR threshold (value, width, label,
                  colour), pass / fail colours
UR_ELEMENTS       the four primary elements and their colours

build_preamble(...)       whole LaTeX preamble generated from the settings above
build_toc_formatting()    chapter-title + TOC formatting
build_title_page(...)     title page
```

`build_preamble` also defines the **semantic macros** that chapter files use instead of raw LaTeX:

| Macro | Meaning |
|---|---|
| `\osdagGap`, `\osdagGapXS/S/M/L` | vertical gaps between blocks |
| `\osdagNote{..}` | table/figure footnote |
| `\osdagPass{..}`, `\osdagFail{..}` | status text colours |
| `\osdagLogWarn/Error/Info{..}` | design-log level colours |
| `\\[\osdagRowGap]`, `\osdagCellGap` | row / in-cell line gaps |
| `\osdagColKey`, `\osdagColVal`, `\osdagColValNarrow` | standard column widths |
| `\osdagTabcolsepCompact`, `\osdagArrayRoomy`, `\osdagTableLeft`, `\osdagTightCaptions` | table density / alignment presets |
| `\osdagFootnoteSize`, `\osdagCaptionSize`, `\osdagChapterHead`, `\osdagRestoreChapterFormat` | type styles |

Changing a value in `styles.py` restyles the whole report — a test (`test_changing_a_style_value_restyles_the_preamble`) proves it.

## 4. Key code and LaTeX changes

### 4.1 Repeating headers (`tables.py`)

* `build_longtable(...)` builds a PyLaTeX `LongTable`: terminated `\caption`, header rows (optionally grouped, with `\cline` mid-rules), `\endfirsthead`, a `\caption[]{… (continued)}` head, `\endhead`, `\endfoot` (closing rule), then rows.
* `normalize_longtables(tex)` rewrites the legacy raw tables. 47 of 49 shared one pattern (`\caption` *without* `\\`, `\hline`, header row, `\hline`, body); that missing `\\` also produced a `Misplaced \noalign` LaTeX error. The normaliser is brace-aware (a row ends at `\\` at brace depth 0, so `\makecell{a\\b}` is untouched), is idempotent, and skips tables that are already hand-built.
* Header rows get a light tint (`osdagHeaderFill`) for readability.

### 4.2 Footer / page-bottom fixes (`styles.py`, `tables.py`)

* Geometry reserves the footer band explicitly (`bottom`, `footskip`, `headheight`) — the fancyhdr "headheight too small" warnings are gone.
* The "* Software default value" note used `\vspace{-20pt}` to pull itself *up* into the body area, which is how rows such as "G4" ended up touching the footer. It now lives inside the footer band above the footer text.
* `\\*` alone does not stop a break after `\cline` (the zero-height cline row followed by `\vskip-\arrayrulewidth` is itself a legal break point). `_cline_nobreak_tex()` patches `\@cline` with `\nobreak`; combined with `\\*` on the rows of each `\multirow` group, groups stay in one piece (verified on a 39-group stress test: 0 split groups vs 6 without the patch).
* The previous `\BeforeBeginEnvironment{longtable}{\needspace{5\baselineskip}}` hook was removed: with it, longtable printed its first head *and* the continuation head at the top of a fresh page. Float `table`s keep their `\needspace`.

### 4.3 Chapter 3 live loads (`load_tables.py`)

* Vehicles are exactly those selected in Additional Inputs → Loading (`KEY_LL_IRC_*` flags + custom vehicles).
* Total loads come from the project's `IRC6_2017` definitions (Class A 543.47 kN, 70R wheeled 981 kN, 70R tracked 686.8 kN, SV 3776.85 kN, fatigue 392.4 kN). Class AA and 70R bogie have no geometry in `irc6_2017.py`, so nominal IRC 6 Cl. 204.1 tonnages are used and clearly labelled in the code.
* Impact factor `1 + IM`: Cl. 208.2 for Class A, Cl. 208.3 for the others (same functions the old table used).
* Braking: considered for Class A / 70R / AA / bogie, not for SV or fatigue; value = 20 % of the vehicle load (Cl. 211.2); eccentricity = the "eccentricity" input of the Loading tab.
* Footpath table: footpath count and width, pressure basis (IRC 6 Cl. 206.1 or user-defined), intensity (kN/m²), and the resulting line load (kN/m); a short note replaces the table when there is no footpath.

### 4.4 Charts (`charts.py`)

* matplotlib's object API (`Figure` + `FigureCanvasAgg`) — no pyplot, no GUI backend, safe in the report worker thread.
* UR values are taken from the **same rows that fill Table 5.22** (`_row522` records them), so a chart can never disagree with the table. Elements without data (e.g. an end diaphragm that is a rolled section with no design yet) are shown as "N/A" rather than silently dropped.
* Bars are green (UR ≤ 1.0) or red (> 1.0); a red dashed line marks UR = 1.0; the governing check is annotated under each bar.
* Images are written to `<tmp>/charts/` created inside `generate_report`'s temporary directory (deleted with it) and embedded through `pylatex.Figure`.
* The chart module never raises into the report pipeline — a failure is logged and the figure omitted.

## 5. Rationale

* **Post-processor + builder instead of rewriting 49 tables by hand.** The legacy tables are string templates interleaved with data lookups; rewriting each would risk regressions in numbers. A normaliser gives uniform behaviour immediately, and `build_longtable` is the path for all new tables.
* **Semantic macros instead of f-string substitution.** The chapters are `r"""` templates; injecting style values by string formatting would be noisy and brittle. Macros keep templates readable and let LaTeX resolve the values once.
* **One preamble generator.** `report_generator.py` lost ~230 lines of inline LaTeX.
* **Guard test.** `test_chapter_files_have_no_hardcoded_formatting` fails the build if `\vspace`, `\textcolor`, `\setlength`, literal row gaps, font-size commands, geometry or packages creep back into a chapter file.

## 6. Visual enhancements beyond the brief

* Tinted header rows; green PASS / bold red FAIL status text; small italic notes.
* Footer: software-default note placed in a reserved band; consistent header/footer rules.
* Per-check UR chart in addition to the per-element chart; reinforcement-intensity (kg/m³) annotation on the concrete/rebar chart.
* Row groups (per-girder blocks) never split across pages.

## 7. Known upstream observations (not changed — outside `reports/`)

* `IRC6_2017.cl_211_2_braking_force` raises `UnboundLocalError` for fewer than 3 design lanes (the old Chapter 3 swallowed it and printed "N/A").
* `IRC6_2017.cl_208_3_impact_factor` tests `KEY_VEHICLE[1]` (a non-empty string, always truthy), so it always takes the tracked-vehicle branch (IM = 0.10 for 9–45 m spans) and the analysis applies that dynamic allowance to every vehicle, including wheeled and Class A vehicles.

## 8. Running the tests

```
python -m pytest tests/unit -q
```

(42 tests; `tests/unit/conftest.py` adds `src/` to `sys.path` if the package is not installed.)
