# =============================================================================
# OsdagBridge Report — Chapter 3 live-load tables
# =============================================================================
#
# Builds two separate, clearly structured tables:
#
#   * Table "Live Loads (LL) — Vehicular"  : one row per vehicle SELECTED in the
#     UI (Additional Inputs > Loading tab): total load, impact factor and the
#     braking-load parameters (considered?, value, eccentricity).
#   * Table "Live Loads (LL) — Footpath"   : footway pressure, width and the
#     resulting line load, with a unit column.
#
# Values are derived from the project's own IRC 6:2017 definitions
# (``IRC6_2017``) wherever those exist; nothing is hard-coded per vehicle except
# the nominal IRC train loads of classes the code module has no geometry for
# (see ``_NOMINAL_TONNES``).
# =============================================================================

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, List, Optional

from osdagbridge.core.reports.report_utils import _tex
from osdagbridge.core.reports.tables import build_longtable
from osdagbridge.core.utils.common import (
    KEY_LL_CUSTOM_VEHICLES,
    KEY_LL_ECCENTRICITY,
    KEY_LL_FOOTPATH_PRESSURE_MODE,
    KEY_LL_FOOTPATH_PRESSURE_VALUE,
    KEY_LL_IRC_70R_BOGIE,
    KEY_LL_IRC_70R_TRACKED,
    KEY_LL_IRC_70R_WHEELED,
    KEY_LL_IRC_AA_TRACKED,
    KEY_LL_IRC_AA_WHEELED,
    KEY_LL_IRC_CLASS_A,
    KEY_LL_IRC_CLASS_FATIGUE,
    KEY_LL_IRC_CLASS_SV,
    KEY_SPAN,
    KEY_TS_FOOTPATH_WIDTH,
    KEY_TS_NO_OF_FOOTPATHS,
)

logger = logging.getLogger(__name__)

G = 9.81                      # kN per tonne-force (same g as irc6_2017.py)
BRAKING_FRACTION = 0.20       # IRC 6:2017 Cl. 211.2 — 20 % of the (first) train load
NOT_AVAILABLE = "---"

# Nominal IRC 6:2017 Cl. 204.1 train loads (tonnes) for classes that
# irc6_2017.py does not model geometrically.
_NOMINAL_TONNES = {
    "aa_wheeled": 40.0,
    "aa_tracked": 70.0,
    "70r_bogie": 40.0,
}


# ─────────────────────────────────────────────────────────────────────────────
# Vehicle catalogue
# ─────────────────────────────────────────────────────────────────────────────
def _irc():
    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
    return IRC6_2017


def _total_class_a() -> float:
    return sum(_irc().cl_204_1_ClassA_vehicle()["wheel_loads"]) / 1000.0


def _total_70r_wheeled() -> float:
    return sum(_irc().cl_204_1_Class70R_vehicle_wheel()["wheel_loads"]) / 1000.0


def _total_70r_tracked() -> float:
    v = _irc().cl_204_1_Class70R_vehicle_track()
    length = abs(v["x"][1] - v["x"][0])
    return v["wheel_loads_udl"] * length * len(v["z"]) / 1000.0


def _total_sv() -> float:
    return float(_irc().cl_204_5_1_special_vehicle()["total_load_kN"])


def _total_fatigue() -> float:
    return sum(_irc().cl_204_6_fatigue_load()["wheel_loads"]) / 1000.0


def _nominal(name: str) -> Callable[[], float]:
    return lambda: _NOMINAL_TONNES[name] * G


@dataclass(frozen=True)
class VehicleSpec:
    key: str                         # UI input key (boolean flag)
    label: str
    total_kN: Callable[[], float]
    impact_clause: str               # "208.2" (Class A) or "208.3" (others)
    braking: bool                    # braking force considered (IRC 6 Cl. 211)


VEHICLES: List[VehicleSpec] = [
    VehicleSpec(KEY_LL_IRC_CLASS_A,       "Class A",               _total_class_a,     "208.2", True),
    VehicleSpec(KEY_LL_IRC_70R_WHEELED,   "Class 70R (Wheeled)",   _total_70r_wheeled, "208.3", True),
    VehicleSpec(KEY_LL_IRC_70R_TRACKED,   "Class 70R (Tracked)",   _total_70r_tracked, "208.3", True),
    VehicleSpec(KEY_LL_IRC_AA_WHEELED,    "Class AA (Wheeled)",    _nominal("aa_wheeled"), "208.3", True),
    VehicleSpec(KEY_LL_IRC_AA_TRACKED,    "Class AA (Tracked)",    _nominal("aa_tracked"), "208.3", True),
    VehicleSpec(KEY_LL_IRC_70R_BOGIE,     "Class 70R (Bogie)",     _nominal("70r_bogie"),  "208.3", True),
    VehicleSpec(KEY_LL_IRC_CLASS_SV,      "Class SV",              _total_sv,          "208.3", False),
    VehicleSpec(KEY_LL_IRC_CLASS_FATIGUE, "Class Fatigue",         _total_fatigue,     "208.3", False),
]


@dataclass(frozen=True)
class VehicleRow:
    label: str
    total_kN: Optional[float]
    impact_factor: Optional[float]
    braking_considered: bool
    braking_kN: Optional[float]
    eccentricity_m: Optional[float]


def _to_float(v) -> Optional[float]:
    try:
        if v in (None, ""):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _impact_factor(clause: str, span_m: Optional[float]) -> Optional[float]:
    """1 + IM (IRC 6:2017 Cl. 208.2 / 208.3), or None if the span is unknown."""
    if span_m is None:
        return None
    try:
        irc = _irc()
        im = irc.cl_208_2_impact_factor(span_m) if clause == "208.2" else irc.cl_208_3_impact_factor(span_m)
        return 1.0 + float(im)
    except Exception as exc:                                    # pragma: no cover
        logger.warning("Impact factor (Cl. %s) unavailable: %s", clause, exc)
        return None


def selected_vehicle_rows(input_dict: dict) -> List[VehicleRow]:
    """One row per vehicle selected in the UI (plus user-defined vehicles)."""
    span = _to_float(input_dict.get(KEY_SPAN))
    ecc = _to_float(input_dict.get(KEY_LL_ECCENTRICITY))
    rows: List[VehicleRow] = []
    for spec in VEHICLES:
        if not input_dict.get(spec.key):
            continue
        try:
            total = float(spec.total_kN())
        except Exception as exc:                                # pragma: no cover
            logger.warning("Total load of %s unavailable: %s", spec.label, exc)
            total = None
        rows.append(VehicleRow(
            label=spec.label,
            total_kN=total,
            impact_factor=_impact_factor(spec.impact_clause, span),
            braking_considered=spec.braking,
            braking_kN=(BRAKING_FRACTION * total) if (spec.braking and total is not None) else None,
            eccentricity_m=ecc if spec.braking else None,
        ))
    custom = input_dict.get(KEY_LL_CUSTOM_VEHICLES)
    if isinstance(custom, list):
        for c in custom:
            name = c.get("name") if isinstance(c, dict) else (c if isinstance(c, str) else None)
            if name:
                total = _to_float(c.get("total_load")) if isinstance(c, dict) else None
                rows.append(VehicleRow(
                    label=str(name), total_kN=total, impact_factor=_impact_factor("208.3", span),
                    braking_considered=False, braking_kN=None, eccentricity_m=None))
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Table builders
# ─────────────────────────────────────────────────────────────────────────────
def _fmt(v: Optional[float], nd: int = 2) -> str:
    return f"{v:.{nd}f}" if v is not None else NOT_AVAILABLE


def vehicular_live_load_table(input_dict: dict) -> str:
    rows = selected_vehicle_rows(input_dict)
    # Two header rows: a group row ("Braking Load" spans three columns) above the
    # column labels.  Labels sit in the lower row so p-columns wrap them.
    header_rows = [
        ["", "", "", r"\multicolumn{3}{c|}{\textbf{Braking Load}}"],
        [r"\textbf{Vehicle}", r"\textbf{Total Load (kN)}", r"\textbf{Impact Factor}",
         r"\textbf{Considered?}", r"\textbf{Value (kN)}", r"\textbf{Eccentricity (m)}"],
    ]
    body = []
    for r in rows:
        body.append([
            _tex(r.label),
            _fmt(r.total_kN),
            _fmt(r.impact_factor, 3),
            "Yes" if r.braking_considered else "No",
            _fmt(r.braking_kN) if r.braking_considered else NOT_AVAILABLE,
            _fmt(r.eccentricity_m) if r.braking_considered else NOT_AVAILABLE,
        ])
    if not body:
        body.append(["None selected", NOT_AVAILABLE, NOT_AVAILABLE, NOT_AVAILABLE, NOT_AVAILABLE, NOT_AVAILABLE])
    note = (
        "Vehicles: as selected in Additional Inputs (Loading tab). "
        "Impact factor $= 1 + IM$ (IRC 6:2017 Cl.~208). "
        "Braking force $= 20\\%$ of the vehicle load, acting at the eccentricity shown "
        "(Cl.~211.2--211.3); not considered for the special and fatigue vehicles."
    )
    return build_longtable(
        caption="Live Loads (LL) --- Vehicular",
        colspec=r"|L{3.0cm}|C{2.1cm}|C{1.8cm}|C{2.7cm}|C{1.8cm}|C{2.5cm}|",
        header=[], header_rows=header_rows, header_midrules=[r"\cline{4-6}"],
        rows=body, note=note, compact=True,
    )


def footpath_live_load_table(input_dict: dict) -> str:
    n_fp = int(_to_float(input_dict.get(KEY_TS_NO_OF_FOOTPATHS)) or 0)
    if n_fp == 0:
        return (r"\osdagGap" + "\n"
                r"\osdagNote{Footpath live load: not applicable --- no footpath is provided on this bridge.}"
                + "\n")
    width = _to_float(input_dict.get(KEY_TS_FOOTPATH_WIDTH))
    mode = str(input_dict.get(KEY_LL_FOOTPATH_PRESSURE_MODE, "") or "")
    auto = mode.strip().lower() in ("as per irc 6", "as per irc6", "automatic")
    pressure: Optional[float]
    if auto:
        try:
            pressure = float(_irc().cl_206_1_footway_load())
        except Exception:                                       # pragma: no cover
            pressure = None
        basis = "As per IRC 6:2017 Cl.~206.1"
    else:
        pressure = _to_float(input_dict.get(KEY_LL_FOOTPATH_PRESSURE_VALUE))
        basis = "User-defined"
    line_load = (pressure * width * n_fp) if (pressure is not None and width is not None) else None

    rows = [
        ["Number of footpaths", str(n_fp), "---"],
        ["Footpath width", _fmt(width), "m"],
        ["Pressure basis", basis, "---"],
        ["Footway live load intensity", _fmt(pressure, 3), r"kN/m\textsuperscript{2}"],
        ["Total footway line load (all footpaths)", _fmt(line_load, 3), "kN/m"],
    ]
    return build_longtable(
        caption="Live Loads (LL) --- Footpath",
        colspec=r"|L{7.5cm}|C{4.5cm}|C{2.5cm}|",
        header=[r"\textbf{Parameter}", r"\textbf{Value}", r"\textbf{Unit}"],
        rows=rows,
        note="Line load = intensity $\\times$ footpath width $\\times$ number of footpaths.",
    )


def live_load_tables(input_dict: dict) -> str:
    """Both live-load tables, separated by the standard block gap."""
    return (vehicular_live_load_table(input_dict) + "\n" + r"\osdagGap" + "\n"
            + footpath_live_load_table(input_dict))
