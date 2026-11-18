# =============================================================================
# OsdagBridge Report — Charts
# =============================================================================
#
# Programmatically generated figures for the design report:
#
#   * Section 5.5  — Utilization Ratio (UR = Demand / Capacity) charts
#   * Chapter 7    — Material quantity charts (steel tonnage, concrete vs rebar)
#
# Design notes
# ------------
# * matplotlib's object API (``Figure`` + ``FigureCanvasAgg``) is used instead of
#   ``pyplot``: no global state, no GUI backend, safe to call from the report
#   worker thread of the desktop application.
# * Plots are saved to a temporary asset directory supplied by the caller
#   (``report_generator.generate_report`` creates it inside its temp folder, so
#   nothing is left behind) and embedded with a PyLaTeX ``Figure``.
# * Every colour, size and font comes from ``styles.CHART`` / ``styles.COLORS``.
# * The chart module never raises into the report pipeline: a failure is logged
#   and the corresponding figure is simply omitted.
# =============================================================================

from __future__ import annotations

import logging
import os
import re
import textwrap
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .styles import CHART, COLORS, FIGURE, UR_ELEMENTS, hex_color

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Data containers
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class URRecord:
    """One utilization-ratio value taken from the design-check summary."""
    element: str      # one of styles.UR_ELEMENTS
    check: str        # e.g. "Girder --- Moment"
    ur: float


@dataclass(frozen=True)
class ChartAsset:
    """A rendered chart: where it is, how to refer to it from LaTeX, caption."""
    key: str
    path: str          # absolute file path
    tex_path: str      # path as seen by pdflatex (relative to the compile dir)
    caption: str


# ─────────────────────────────────────────────────────────────────────────────
# UR record extraction helpers
# ─────────────────────────────────────────────────────────────────────────────
_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def parse_ur(cell: str) -> Optional[float]:
    """Extract a UR number from a (possibly LaTeX-decorated) table cell."""
    if cell is None:
        return None
    s = str(cell)
    if s.strip() in ("", "---", "N/A"):
        return None
    m = _NUM.search(s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def element_for_label(label: str) -> Optional[str]:
    """Map a Table 5.22 row label to its primary structural element."""
    t = label.strip().lower()
    if t.startswith("girder"):
        return "Steel Plate Girders"
    if t.startswith("deck") or "(slab)" in t:
        return "Concrete Deck Slab"
    if t.startswith("cross bracing"):
        return "Cross Bracing"
    if t.startswith("end diaphragm"):
        return "End Diaphragms"
    return None


def make_record(label: str, ur_cell: str) -> Optional[URRecord]:
    ur = parse_ur(ur_cell)
    element = element_for_label(label)
    if ur is None or element is None:
        return None
    # strip LaTeX dashes ("Girder --- Moment" -> "Girder - Moment")
    return URRecord(element=element, check=label.replace("---", "-").strip(), ur=ur)


def summarise_by_element(records: Sequence[URRecord]) -> Dict[str, Optional[Tuple[float, str]]]:
    """``element -> (governing UR, check label)`` or ``None`` when no data."""
    out: Dict[str, Optional[Tuple[float, str]]] = {name: None for name, _ in UR_ELEMENTS}
    for r in records:
        cur = out.get(r.element)
        if cur is None or r.ur > cur[0]:
            out[r.element] = (r.ur, r.check)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# matplotlib helpers
# ─────────────────────────────────────────────────────────────────────────────
def _new_figure(figsize: Tuple[float, float]):
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    fig = Figure(figsize=figsize, dpi=CHART.dpi, facecolor="white")
    FigureCanvasAgg(fig)
    return fig


def _style_axes(ax, ylabel: str, title: str) -> None:
    txt = hex_color(CHART.text_color)
    ax.set_ylabel(ylabel, fontsize=CHART.label_size, color=txt)
    ax.set_title(title, fontsize=CHART.title_size, fontweight="bold", pad=10)
    ax.set_axisbelow(True)
    ax.grid(axis="y", color=hex_color(CHART.grid_color), linewidth=0.7)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(hex_color(CHART.grid_color))
    ax.tick_params(colors=txt, labelsize=CHART.font_size)


def _rc():
    import matplotlib

    return matplotlib.rc_context({
        "font.family": CHART.font_family,
        "font.size": CHART.font_size,
        "axes.unicode_minus": False,
    })


def _save(fig, out_dir: str, name: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    fig.savefig(path, dpi=CHART.dpi, bbox_inches="tight", facecolor="white")
    return path


def _asset(key: str, path: str, caption: str) -> ChartAsset:
    folder = os.path.basename(os.path.dirname(path))
    return ChartAsset(key=key, path=path,
                      tex_path=f"{folder}/{os.path.basename(path)}".replace("\\", "/"),
                      caption=caption)


def _na_bar(ax, x: float, ymax: float) -> None:
    ax.text(x, ymax * 0.04, CHART.unavailable_text, ha="center", va="bottom",
            fontsize=CHART.font_size, color=hex_color(CHART.text_color), style="italic")


def _threshold(ax) -> None:
    ax.axhline(CHART.threshold_value, color=hex_color(CHART.threshold_color),
               linestyle="--", linewidth=CHART.threshold_width, zorder=4,
               label=CHART.threshold_label)


# ─────────────────────────────────────────────────────────────────────────────
# Section 5.5 — Utilization Ratio charts
# ─────────────────────────────────────────────────────────────────────────────
def build_ur_charts(records: Sequence[URRecord], out_dir: str) -> List[ChartAsset]:
    """Create the overall (governing UR per element) and detailed (per check) charts."""
    if not records:
        return []
    assets: List[ChartAsset] = []
    try:
        with _rc():
            assets.append(_ur_overall(records, out_dir))
            detail = _ur_detail(records, out_dir)
            if detail:
                assets.append(detail)
    except Exception as exc:                                  # pragma: no cover
        logger.warning("Utilization-ratio chart generation failed: %s", exc, exc_info=True)
    return assets


def _ur_overall(records: Sequence[URRecord], out_dir: str) -> ChartAsset:
    summary = summarise_by_element(records)
    names = [n for n, _ in UR_ELEMENTS]
    values = [summary[n][0] if summary[n] else None for n in names]
    top = max([v for v in values if v is not None] + [CHART.threshold_value])
    ymax = top * CHART.y_headroom

    fig = _new_figure(CHART.figsize_overall)
    ax = fig.add_subplot(111)
    for i, (name, v) in enumerate(zip(names, values)):
        if v is None:
            _na_bar(ax, i, ymax)
            continue
        colour = hex_color(CHART.pass_color if v <= CHART.threshold_value else CHART.fail_color)
        ax.bar(i, v, width=CHART.bar_width, color=colour,
               edgecolor=hex_color("osdagGreenDark"), linewidth=CHART.bar_edge_width, zorder=3)
        ax.text(i, v + ymax * 0.015, CHART.value_label_fmt.format(v), ha="center", va="bottom",
                fontsize=CHART.font_size, fontweight="bold", zorder=5,
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.2})
    _threshold(ax)
    ax.set_ylim(0, ymax)
    ax.set_xlim(-0.6, len(names) - 0.4)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, fontsize=CHART.font_size - 0.5)
    # governing check of each element, wrapped, under the tick label
    for i, n in enumerate(names):
        if summary[n]:
            ax.text(i, -0.13, textwrap.fill(summary[n][1].replace(" - ", ": "), 18),
                    transform=ax.get_xaxis_transform(), ha="center", va="top",
                    fontsize=CHART.font_size - 2, color=hex_color(CHART.text_color), style="italic")
    _style_axes(ax, "Utilization Ratio, UR = Demand / Capacity",
                "Overall Utilization Ratio of Primary Elements (governing check)")
    ax.legend(loc="upper right", frameon=False, fontsize=CHART.font_size)
    path = _save(fig, out_dir, "ur_overall.png")
    return _asset("ur_overall", path,
                  "Overall utilization ratio (UR = Demand / Capacity) of the primary elements. "
                  "Bars show the governing check of each element; the red dashed line marks UR = 1.0 "
                  "(UR $\\leq$ 1.0 passes, UR $>$ 1.0 fails).")


def _short(check: str) -> str:
    for prefix in ("Girder - ", "Deck - ", "Cross Bracing - ", "End Diaphragm - "):
        if check.startswith(prefix):
            return check[len(prefix):]
    return check


def _ur_detail(records: Sequence[URRecord], out_dir: str) -> Optional[ChartAsset]:
    colour_of = dict(UR_ELEMENTS)
    ordered: List[URRecord] = []
    for name, _ in UR_ELEMENTS:
        ordered.extend(r for r in records if r.element == name)
    if not ordered:
        return None
    top = max([r.ur for r in ordered] + [CHART.threshold_value])
    ymax = top * CHART.y_headroom

    fig = _new_figure(CHART.figsize_detail)
    ax = fig.add_subplot(111)
    for i, r in enumerate(ordered):
        fail = r.ur > CHART.threshold_value
        colour = hex_color(CHART.fail_color if fail else colour_of[r.element])
        ax.bar(i, r.ur, width=CHART.bar_width + 0.15, color=colour,
               edgecolor=hex_color("osdagGreenDark"), linewidth=CHART.bar_edge_width, zorder=3)
        ax.text(i, r.ur + ymax * 0.012, CHART.value_label_fmt.format(r.ur), ha="center",
                va="bottom", fontsize=CHART.font_size - 1.5, zorder=5,
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.8})
    _threshold(ax)
    ax.set_ylim(0, ymax)
    ax.set_xlim(-0.7, len(ordered) - 0.3)
    ax.set_xticks(range(len(ordered)))
    ax.set_xticklabels([_short(r.check) for r in ordered], rotation=35, ha="right",
                       fontsize=CHART.font_size - 1.5)
    _style_axes(ax, "Utilization Ratio, UR = Demand / Capacity",
                "Utilization Ratio by Design Check")

    from matplotlib.patches import Patch
    handles = [Patch(facecolor=hex_color(c), edgecolor=hex_color("osdagGreenDark"), label=n)
               for n, c in UR_ELEMENTS if any(r.element == n for r in ordered)]
    handles.append(ax.get_lines()[0])
    ax.legend(handles=handles, loc="upper right", ncol=2, frameon=False,
              fontsize=CHART.font_size - 1)
    path = _save(fig, out_dir, "ur_detail.png")
    return _asset("ur_detail", path,
                  "Utilization ratio of every design check in the Overall Design Check Summary table, "
                  "grouped by element. Failing checks (UR $>$ 1.0) are drawn in red.")


# ─────────────────────────────────────────────────────────────────────────────
# Chapter 7 — material quantity charts
# ─────────────────────────────────────────────────────────────────────────────
def _num(quantities: dict, key: str) -> Optional[float]:
    v = quantities.get(key)
    if v in (None, "", "N.A.", "N.A"):
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


def _sum_or_none(values: Iterable[Optional[float]]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return sum(vals) if vals else None


def collect_quantities(quantities: dict) -> dict:
    """Pull the chartable numbers out of the Chapter 7 quantity dictionary."""
    steel = {
        "Girders": _num(quantities, "steel_girders_wt_total"),
        "Cross Bracing": _sum_or_none(_num(quantities, k) for k in
                                      ("bracing_top_wt_total", "bracing_bot_wt_total",
                                       "bracing_diag_wt_total")),
        "End Diaphragms": _num(quantities, "end_diaphragm_wt_total"),
    }
    return {
        "steel": steel,
        "concrete_m3": _num(quantities, "concrete_deck_vol_total"),
        "rebar_mt": _num(quantities, "rebar_deck_wt_total"),
    }


def build_quantity_charts(quantities: dict, out_dir: str) -> List[ChartAsset]:
    """Create the structural-steel tonnage chart and the concrete-vs-rebar chart."""
    data = collect_quantities(quantities)
    assets: List[ChartAsset] = []
    try:
        with _rc():
            if any(v is not None for v in data["steel"].values()):
                assets.append(_steel_chart(data["steel"], out_dir))
            if data["concrete_m3"] is not None or data["rebar_mt"] is not None:
                assets.append(_concrete_rebar_chart(data["concrete_m3"], data["rebar_mt"], out_dir))
    except Exception as exc:                                  # pragma: no cover
        logger.warning("Quantity chart generation failed: %s", exc, exc_info=True)
    return assets


def _steel_chart(steel: Dict[str, Optional[float]], out_dir: str) -> ChartAsset:
    names = list(steel)
    palette = [hex_color("osdagSteel"), hex_color("osdagBrace"), hex_color("osdagGreenDark")]
    top = max([v for v in steel.values() if v is not None] + [1.0])
    ymax = top * CHART.y_headroom

    fig = _new_figure(CHART.figsize_quantity)
    ax = fig.add_subplot(111)
    for i, name in enumerate(names):
        v = steel[name]
        if v is None:
            _na_bar(ax, i, ymax)
            continue
        ax.bar(i, v, width=CHART.bar_width, color=palette[i % len(palette)],
               edgecolor=hex_color("osdagGreenDark"), linewidth=CHART.bar_edge_width, zorder=3)
        ax.text(i, v + ymax * 0.015, f"{v:.2f}", ha="center", va="bottom",
                fontsize=CHART.font_size, fontweight="bold", zorder=5)
    total = _sum_or_none(steel.values())
    ax.set_ylim(0, ymax)
    ax.set_xlim(-0.6, len(names) - 0.4)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, fontsize=CHART.font_size)
    title = "Structural Steel Quantity"
    if total is not None:
        title += f"  (total quantified: {total:.2f} MT)"
    _style_axes(ax, "Weight (MT)", title)
    path = _save(fig, out_dir, "qty_steel.png")
    return _asset("qty_steel", path,
                  "Structural steel tonnage by member group (girders, cross bracing, end diaphragms). "
                  "``N/A'' marks groups with no quantity in the bill of materials.")


def _concrete_rebar_chart(concrete: Optional[float], rebar: Optional[float], out_dir: str) -> ChartAsset:
    fig = _new_figure(CHART.figsize_quantity)
    ax1 = fig.add_subplot(121)
    ax2 = fig.add_subplot(122)
    for ax, value, label, unit, colour in (
        (ax1, concrete, "Concrete (deck slab)", "Volume (m$^3$)", hex_color("osdagConcrete")),
        (ax2, rebar, "Reinforcement steel", "Weight (MT)", hex_color("osdagRebar")),
    ):
        ymax = (value or 1.0) * CHART.y_headroom
        if value is None:
            _na_bar(ax, 0, ymax)
        else:
            ax.bar(0, value, width=CHART.bar_width + 0.15, color=colour,
                   edgecolor=hex_color("osdagGreenDark"), linewidth=CHART.bar_edge_width, zorder=3)
            ax.text(0, value + ymax * 0.015, f"{value:.2f}", ha="center", va="bottom",
                    fontsize=CHART.font_size, fontweight="bold", zorder=5)
        ax.set_ylim(0, ymax)
        ax.set_xlim(-0.7, 0.7)
        ax.set_xticks([0])
        ax.set_xticklabels([label], fontsize=CHART.font_size)
        _style_axes(ax, unit, "")
    fig.suptitle("Concrete Volume vs. Reinforcement Steel Weight",
                 fontsize=CHART.title_size, fontweight="bold")
    if concrete and rebar:
        fig.text(0.5, 0.005, f"Reinforcement intensity: {rebar * 1000.0 / concrete:.0f} kg per m$^3$ of concrete",
                 ha="center", va="bottom", fontsize=CHART.font_size - 0.5,
                 color=hex_color(CHART.text_color))
    fig.subplots_adjust(wspace=0.45, top=0.86, bottom=0.2)
    path = _save(fig, out_dir, "qty_concrete_rebar.png")
    return _asset("qty_concrete_rebar", path,
                  "Concrete volume (m$^3$) of the deck slab compared with the reinforcement steel "
                  "weight (MT).")


# ─────────────────────────────────────────────────────────────────────────────
# LaTeX embedding (PyLaTeX Figure)
# ─────────────────────────────────────────────────────────────────────────────
def figure_tex(asset: ChartAsset) -> str:
    """Return the LaTeX for *asset* built with a PyLaTeX ``Figure``."""
    from pylatex import Figure
    from pylatex.utils import NoEscape

    fig = Figure(position=FIGURE.placement)
    fig.add_image(asset.tex_path, width=NoEscape(FIGURE.chart_width),
                  placement=NoEscape(r"\centering"))
    fig.add_caption(NoEscape(asset.caption))
    return fig.dumps()


def figures_tex(assets: Iterable[ChartAsset]) -> str:
    return "\n\n".join(figure_tex(a) for a in assets)
