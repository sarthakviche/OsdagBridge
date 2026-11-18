"""Chapter 3 live-load tables follow the vehicles selected in the UI."""
from osdagbridge.core.reports.load_tables import (
    footpath_live_load_table, live_load_tables, selected_vehicle_rows, vehicular_live_load_table,
)
from osdagbridge.core.utils.common import (
    KEY_LL_ECCENTRICITY, KEY_LL_FOOTPATH_PRESSURE_MODE, KEY_LL_FOOTPATH_PRESSURE_VALUE,
    KEY_LL_IRC_70R_WHEELED, KEY_LL_IRC_CLASS_A, KEY_LL_IRC_CLASS_SV, KEY_SPAN,
    KEY_TS_FOOTPATH_WIDTH, KEY_TS_NO_OF_FOOTPATHS,
)

BS = "\\"


def _inputs(**flags):
    d = {KEY_SPAN: 30.0, KEY_LL_ECCENTRICITY: 1.2, KEY_TS_NO_OF_FOOTPATHS: 0}
    d.update(flags)
    return d


def test_only_vehicles_selected_in_the_ui_are_listed():
    rows = selected_vehicle_rows(_inputs(**{KEY_LL_IRC_CLASS_A: True, KEY_LL_IRC_CLASS_SV: True}))
    assert [r.label for r in rows] == ["Class A", "Class SV"]


def test_braking_rules_per_vehicle():
    rows = {r.label: r for r in selected_vehicle_rows(
        _inputs(**{KEY_LL_IRC_CLASS_A: True, KEY_LL_IRC_CLASS_SV: True}))}
    a, sv = rows["Class A"], rows["Class SV"]
    assert a.braking_considered
    assert abs(a.braking_kN - 0.2 * a.total_kN) < 1e-9 and a.eccentricity_m == 1.2
    assert not sv.braking_considered and sv.braking_kN is None and sv.eccentricity_m is None


def test_vehicle_totals_come_from_the_irc_definitions():
    rows = {r.label: r for r in selected_vehicle_rows(
        _inputs(**{KEY_LL_IRC_CLASS_A: True, KEY_LL_IRC_70R_WHEELED: True}))}
    assert abs(rows["Class A"].total_kN - 543.474) < 1e-3
    assert abs(rows["Class 70R (Wheeled)"].total_kN - 981.0) < 1e-3
    assert rows["Class A"].impact_factor > 1.0


def test_vehicular_table_has_grouped_braking_header_and_units():
    tex = vehicular_live_load_table(_inputs(**{KEY_LL_IRC_CLASS_A: True}))
    assert "Total Load (kN)" in tex and "Impact Factor" in tex
    assert BS + "multicolumn{3}{c|}{" + BS + "textbf{Braking Load}}" in tex
    assert "Value (kN)" in tex and "Eccentricity (m)" in tex and "Considered?" in tex
    assert BS + "endhead" in tex                       # header repeats across pages


def test_empty_selection_still_produces_a_valid_table():
    tex = vehicular_live_load_table(_inputs())
    assert "None selected" in tex


def test_footpath_table_is_separate_and_has_unit_column():
    d = _inputs(**{KEY_TS_NO_OF_FOOTPATHS: 1, KEY_TS_FOOTPATH_WIDTH: 1.5,
                   KEY_LL_FOOTPATH_PRESSURE_MODE: "User-defined",
                   KEY_LL_FOOTPATH_PRESSURE_VALUE: 4.0})
    tex = footpath_live_load_table(d)
    assert "Footpath" in tex and "Unit" in tex and "kN/m" in tex
    assert "6.000" in tex                              # 4.0 kN/m^2 x 1.5 m x 1 footpath


def test_no_footpath_means_a_note_not_a_table():
    tex = footpath_live_load_table(_inputs())
    assert "longtable" not in tex and "not applicable" in tex


def test_both_tables_are_emitted_together():
    tex = live_load_tables(_inputs(**{KEY_LL_IRC_CLASS_A: True}))
    assert "Vehicular" in tex
