"""
CBFT door and window panel cutting list rules.

Door panels  : bamboo studs at ends, timber jambs + head.
Window panels: bamboo studs at ends, timber jambs + head + sill.

Neither door nor window panels use a flat-bar X-brace (no AR-Flatbar layer
appears in the reference door_window.dxf).  Connection hardware (J-bolts,
straight rods, nuts, washers) matches the T1-stud rules from cutting_rules.py.
"""

import math
from .cutting_rules import (
    CuttingRow,
    PLATE_THICKNESS,
    PLATE_WIDTH,
    STUD_DIAMETER,
    WALL_HEIGHT_TOTAL,
    TADTAD_STRIP_W,
    T1_JBOLT_EA,
    T1_STROD_EA,
    T1_NUTS12_EA,
    T1_WASH12_EA,
)

# Door/window panels always have exactly 2 T1 bamboo studs (one at each end).
_T1_COUNT = 2

# Stud height = panel height minus two timber plate thicknesses.
def _stud_height(panel_height: float) -> float:
    return panel_height - 2 * PLATE_THICKNESS


def _hardware_rows(t1: int = _T1_COUNT) -> list:
    """Return the T1-stud connection hardware rows (J-bolt + straight rod + nuts/washers)."""
    return [
        CuttingRow("THREADED J-BOLT",   "12MM ∅",             "-", t1 * T1_JBOLT_EA),
        CuttingRow("STR. THREADED ROD", "12MM ∅",             "-", t1 * T1_STROD_EA),
        CuttingRow("NUTS",              "12MM ∅",             "-", t1 * T1_NUTS12_EA),
        CuttingRow("WASHER",            "2.8MM THK. X 35MM∅", "-", t1 * T1_WASH12_EA),
    ]


def _cladding_row(cladding: str, panel_width: float, panel_height: float) -> CuttingRow:
    """Return one TADTAD or RIBLATH row."""
    if cladding == "double":
        return CuttingRow("RIBLATH", f"600 X {panel_width:.0f} MM", "-", 5)
    tadtad_count = math.ceil(panel_height / TADTAD_STRIP_W)
    return CuttingRow("TADTAD", f"300 X {panel_width:.0f} MM", "-", tadtad_count)


# ─────────────────────────────────────────────────────────────────────────────
# Public entry points
# ─────────────────────────────────────────────────────────────────────────────

def compute_door_cutting_list(panel_width:   float,
                              opening_width: float,
                              cladding:      str   = "single",
                              panel_height:  float = WALL_HEIGHT_TOTAL) -> list:
    """
    Compute the cutting list for a CBFT door panel.

    Parameters
    ----------
    panel_width   : total panel length (mm)
    opening_width : clear door opening width (mm)
    cladding      : "single" (TADTAD) or "double" (RIBLATH)
    panel_height  : total panel height incl. plates (default 2100 mm)
    """
    sh = _stud_height(panel_height)
    rows = [
        CuttingRow("TOP TIMBER PLATE",  "38X88 MM", f"{panel_width:.0f} MM",   1),
        CuttingRow("BOT. TIMBER PLATE", "38X88 MM", f"{panel_width:.0f} MM",   1),
        CuttingRow("DOOR HEAD",         "38X88 MM", f"{opening_width:.0f} MM", 1),
        CuttingRow("SIDE JAMB",         "38X88 MM", f"{panel_height:.0f} MM",  2),
        CuttingRow("T1 BAMBOO STUD",    "100MM ∅",  f"{sh:.0f} MM",            _T1_COUNT),
    ]
    rows += _hardware_rows()
    rows.append(_cladding_row(cladding, panel_width, panel_height))
    return rows


def compute_window_cutting_list(panel_width:    float,
                                opening_width:  float,
                                opening_height: float,
                                cladding:       str   = "single",
                                panel_height:   float = WALL_HEIGHT_TOTAL) -> list:
    """
    Compute the cutting list for a CBFT window panel.

    Parameters
    ----------
    panel_width    : total panel length (mm)
    opening_width  : clear window opening width (mm)
    opening_height : clear window opening height (mm)
    cladding       : "single" (TADTAD) or "double" (RIBLATH)
    panel_height   : total panel height incl. plates (default 2100 mm)
    """
    sh = _stud_height(panel_height)
    rows = [
        CuttingRow("TOP TIMBER PLATE",  "38X88 MM", f"{panel_width:.0f} MM",    1),
        CuttingRow("BOT. TIMBER PLATE", "38X88 MM", f"{panel_width:.0f} MM",    1),
        CuttingRow("WINDOW HEAD",       "38X88 MM", f"{opening_width:.0f} MM",  1),
        CuttingRow("WINDOW SILL",       "38X88 MM", f"{opening_width:.0f} MM",  1),
        CuttingRow("SIDE JAMB",         "38X88 MM", f"{panel_height:.0f} MM",   2),
        CuttingRow("T1 BAMBOO STUD",    "100MM ∅",  f"{sh:.0f} MM",             _T1_COUNT),
    ]
    rows += _hardware_rows()
    rows.append(_cladding_row(cladding, panel_width, panel_height))
    return rows
