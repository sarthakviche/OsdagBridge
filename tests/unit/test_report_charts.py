"""Tests for the utilization-ratio and material-quantity charts."""
import os

from osdagbridge.core.reports import charts
from osdagbridge.core.reports.charts import (
    URRecord, build_quantity_charts, build_ur_charts, collect_quantities,
    element_for_label, figure_tex, make_record, parse_ur, summarise_by_element,
)

BS = "\\"


def test_parse_ur_handles_latex_decoration_and_missing_values():
    assert parse_ur("0.85") == 0.85
    assert parse_ur(BS + "osdagFail{1.64}") == 1.64
    assert parse_ur(BS + "textcolor{red}{1.20}") == 1.20
    assert parse_ur("---") is None and parse_ur("") is None and parse_ur(None) is None


def test_rows_map_to_the_four_primary_elements():
    assert element_for_label("Girder --- Moment") == "Steel Plate Girders"
    assert element_for_label("Deck --- Punching Shear") == "Concrete Deck Slab"
    assert element_for_label("Crack Width (slab)") == "Concrete Deck Slab"
    assert element_for_label("Cross Bracing --- Tension") == "Cross Bracing"
    assert element_for_label("End Diaphragm --- Shear") == "End Diaphragms"
    assert element_for_label("Something else") is None
    assert make_record("Girder --- Moment", "---") is None


def test_governing_ur_is_the_maximum_per_element():
    recs = [URRecord("Steel Plate Girders", "Girder - Moment", 0.6),
            URRecord("Steel Plate Girders", "Girder - Shear", 0.9),
            URRecord("Concrete Deck Slab", "Deck - Flexure", 0.4)]
    s = summarise_by_element(recs)
    assert s["Steel Plate Girders"] == (0.9, "Girder - Shear")
    assert s["Cross Bracing"] is None and s["End Diaphragms"] is None


def test_ur_charts_are_written_as_png(tmp_path):
    recs = [URRecord("Steel Plate Girders", "Girder - Moment", 0.7),
            URRecord("Concrete Deck Slab", "Deck - Flexure", 1.3),     # failing
            URRecord("Cross Bracing", "Cross Bracing - Tension", 0.5)]
    assets = build_ur_charts(recs, str(tmp_path / "charts"))
    assert {a.key for a in assets} == {"ur_overall", "ur_detail"}
    for a in assets:
        assert os.path.getsize(a.path) > 2000
        assert a.tex_path == "charts/" + os.path.basename(a.path)


def test_no_records_means_no_chart(tmp_path):
    assert build_ur_charts([], str(tmp_path)) == []


def test_quantity_collection_treats_na_as_missing():
    q = {"steel_girders_wt_total": "41.12", "bracing_top_wt_total": "N.A.",
         "bracing_bot_wt_total": "N.A.", "bracing_diag_wt_total": "N.A.",
         "concrete_deck_vol_total": "77.06", "rebar_deck_wt_total": "9.25"}
    d = collect_quantities(q)
    assert d["steel"]["Girders"] == 41.12
    assert d["steel"]["Cross Bracing"] is None and d["steel"]["End Diaphragms"] is None
    assert d["concrete_m3"] == 77.06 and d["rebar_mt"] == 9.25


def test_cross_bracing_tonnage_sums_its_members():
    q = {"bracing_top_wt_total": "1.0", "bracing_bot_wt_total": "2.0", "bracing_diag_wt_total": "0.5"}
    assert collect_quantities(q)["steel"]["Cross Bracing"] == 3.5


def test_quantity_charts_are_written(tmp_path):
    q = {"steel_girders_wt_total": "41.12", "concrete_deck_vol_total": "77.06",
         "rebar_deck_wt_total": "9.25"}
    assets = build_quantity_charts(q, str(tmp_path / "charts"))
    assert {a.key for a in assets} == {"qty_steel", "qty_concrete_rebar"}
    assert all(os.path.getsize(a.path) > 2000 for a in assets)


def test_figure_is_embedded_through_a_pylatex_figure(tmp_path):
    recs = [URRecord("Steel Plate Girders", "Girder - Moment", 0.7)]
    asset = build_ur_charts(recs, str(tmp_path / "charts"))[0]
    tex = figure_tex(asset)
    assert BS + "begin{figure}[H]" in tex and BS + "includegraphics" in tex
    assert "charts/ur_overall.png" in tex and BS + "caption{" in tex
    assert charts.FIGURE.chart_width in tex
