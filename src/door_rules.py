"""
CBFT door and window panel cutting list rules.

Reference: door_2400_detail.dxf (2350mm wide, 1000mm opening, T1=3, T2=2)

Door panel structure (top to bottom):
  TOP TIMBER PLATE (38x88mm)
  T1 BAMBOO STUD x3, T2 BAMBOO STUD x2  (full stud height)
  short BAMBOO STUD x1  (above door header)
  DOOR JAMB horizontal (= door head)
  DOOR JAMB vertical x2 (= side jambs, height = opening_height)
  BOT. TIMBER PLATE (38x88mm)
  FLAT BAR X-brace on solid section only
"""

import math
from .cutting_rules import (
    CuttingRow,
    PLATE_THICKNESS,
    TADTAD_STRIP_W,
    FLATBAR_W,
    FLATBAR_T,
    FLATBAR_H_TRIM,
    FLATBAR_V_TRIM,
    FLATBAR_EXTRA,
    ROD_10_LENGTH,
)

# Default total panel height for door/window panels (= 8 ft = 2440 mm)
DOOR_WALL_HEIGHT = 2440

# Default rough opening height for standard door (2000mm rough → 1962mm clear)
DOOR_ROUGH_OPENING_H = 2000
DOOR_OPENING_HEIGHT  = DOOR_ROUGH_OPENING_H - PLATE_THICKNESS  # 1962 mm


def _consolidate(rows: list) -> list:
    """Merge rows with identical (component, size, length) by summing qty."""
    seen: dict = {}
    order: list = []
    for row in rows:
        key = (row.component, row.size, row.length)
        if key in seen:
            r = seen[key]
            seen[key] = CuttingRow(r.component, r.size, r.length, r.qty + row.qty, r.unit)
        else:
            seen[key] = CuttingRow(row.component, row.size, row.length, row.qty, row.unit)
            order.append(key)
    return [seen[k] for k in order]


def _stud_height(panel_height: float) -> float:
    return panel_height - 2 * PLATE_THICKNESS


def _door_flatbar_length(panel_width: float,
                         opening_width: float,
                         panel_height: float) -> int:
    """
    Flat bar diagonal length for the SOLID SECTION of the door panel.

    The flat bar covers only panel_width - opening_width (solid side),
    using the same trim constants as wall panels.
    """
    solid = panel_width - opening_width
    h = solid - FLATBAR_H_TRIM
    v = panel_height - FLATBAR_V_TRIM
    return round(math.sqrt(h ** 2 + v ** 2) + FLATBAR_EXTRA)


# ─────────────────────────────────────────────────────────────────────────────
# Public entry points
# ─────────────────────────────────────────────────────────────────────────────

def compute_door_cutting_list(panel_width:    float,
                              opening_width:  float,
                              opening_height: float = DOOR_OPENING_HEIGHT,
                              t1_count:       int   = 3,
                              t2_count:       int   = 2,
                              cladding:       str   = "single",
                              panel_height:   float = DOOR_WALL_HEIGHT) -> list:
    """
    Compute the cutting list for a CBFT door panel.

    Parameters
    ----------
    panel_width    : total panel length (mm)
    opening_width  : clear door opening width (mm)
    opening_height : clear door opening height (mm); default 1962 mm
    t1_count       : end / structural bamboo studs (from plan DXF); default 3
    t2_count       : intermediate bamboo studs (from plan DXF); default 2
    cladding       : "single" (TADTAD) or "double" (RIBLATH)
    panel_height   : total panel height incl. plates (default 2440 mm)
    """
    stud_h = _stud_height(panel_height)
    # Short stud above door header fills the gap between door head and top plate
    short_stud = stud_h - opening_height - PLATE_THICKNESS

    fb = _door_flatbar_length(panel_width, opening_width, panel_height)

    # Hardware counts
    # hw12 = T1 studs + short stud above door (all need top & bottom plate connections)
    hw12 = t1_count + 1
    # rod10 = 2 rods per stud × (T1 + T2 + 1 short stud)
    rod10 = 2 * (t1_count + t2_count + 1)

    # ── Structural timber & bamboo ────────────────────────────────────────────
    rows = [
        CuttingRow("TOP TIMBER PLATE",  "38X88 MM", f"{panel_width:.0f} MM",    1),
        CuttingRow("BOT. TIMBER PLATE", "38X88 MM", f"{panel_width:.0f} MM",    1),
        CuttingRow("T1 BAMBOO STUD",    "100MM ∅",  f"{stud_h:.0f} MM",     t1_count),
    ]
    if t2_count > 0:
        rows.append(
            CuttingRow("T2 BAMBOO STUD", "100MM ∅",  f"{stud_h:.0f} MM",   t2_count)
        )
    rows += [
        CuttingRow("BAMBOO STUD",       "100MM ∅",  f"{short_stud:.0f} MM", 1),
        # Door jambs
        CuttingRow("DOOR JAMB",         "38X88 MM", f"{opening_width:.0f} MM",  1),  # head
        CuttingRow("DOOR JAMB",         "38X88 MM", f"{opening_height:.0f} MM", 2),  # sides
    ]

    # ── Flat-bar X-brace on solid section ────────────────────────────────────
    solid_width = panel_width - opening_width
    if solid_width > FLATBAR_H_TRIM and rod10 > 0:
        rows += [
            CuttingRow("FLAT BAR",  f"{FLATBAR_W}x{FLATBAR_T}MM THK.", f"{fb} MM", 2),
            CuttingRow("THREADED ROD",    "10MM ∅", f"{ROD_10_LENGTH} MM",    rod10),
            CuttingRow("NUTS",            "10MM ∅", "-",                       2 * rod10),
            CuttingRow("WASHER", "2.1MM THK. X 25MM∅", "-",                   2 * rod10),
        ]

    # ── 12 mm plate-connection hardware ──────────────────────────────────────
    # J-bolt bottom plate + straight rod top plate; 2 nuts + 2 washers per rod,
    # 1 nut + 1 washer per J-bolt → 3 × hw12 total each
    rows += [
        CuttingRow("THREADED J-BOLT",       "12MM ∅", "300 MM",             hw12),
        CuttingRow("STRAIGHT THREADED ROD", "12MM ∅", "150 MM",             hw12),
        CuttingRow("NUTS",                  "12MM ∅", "-",                  3 * hw12),
        CuttingRow("WASHER", "2.8MM THK. X 35MM∅",   "-",                  3 * hw12),
    ]

    # ── Infill cladding ───────────────────────────────────────────────────────
    if cladding == "double":
        rows.append(CuttingRow("RIBLATH", f"600 X {panel_width:.0f} MM", "-", 5))
    else:
        tadtad = math.ceil(panel_height / TADTAD_STRIP_W)
        rows.append(CuttingRow("TADTAD", f"300x{panel_width:.0f} MM", "-", tadtad))

    return _consolidate(rows)


def compute_window_cutting_list(panel_width:    float,
                                opening_width:  float,
                                opening_height: float,
                                t1_count:       int   = 3,
                                t2_count:       int   = 2,
                                cladding:       str   = "single",
                                panel_height:   float = DOOR_WALL_HEIGHT) -> list:
    """
    Compute the cutting list for a CBFT window panel.

    Similar structure to door panel but with a WINDOW SILL below the opening
    and studs flanking the window opening on both sides.
    """
    stud_h = _stud_height(panel_height)

    rows = [
        CuttingRow("TOP TIMBER PLATE",  "38X88 MM", f"{panel_width:.0f} MM",    1),
        CuttingRow("BOT. TIMBER PLATE", "38X88 MM", f"{panel_width:.0f} MM",    1),
        CuttingRow("T1 BAMBOO STUD",    "100MM ∅",  f"{stud_h:.0f} MM",     t1_count),
    ]
    if t2_count > 0:
        rows.append(
            CuttingRow("T2 BAMBOO STUD", "100MM ∅",  f"{stud_h:.0f} MM",   t2_count)
        )
    rows += [
        CuttingRow("WINDOW HEAD",  "38X88 MM", f"{opening_width:.0f} MM",  1),
        CuttingRow("WINDOW SILL",  "38X88 MM", f"{opening_width:.0f} MM",  1),
        CuttingRow("SIDE JAMB",    "38X88 MM", f"{opening_height:.0f} MM", 2),
    ]

    # Hardware (same pattern as door)
    hw12  = t1_count + 1
    rod10 = 2 * (t1_count + t2_count + 1)

    rows += [
        CuttingRow("FLAT BAR",
                   f"{FLATBAR_W}x{FLATBAR_T}MM THK.",
                   f"{_door_flatbar_length(panel_width, opening_width, panel_height)} MM",
                   2),
        CuttingRow("THREADED ROD",      "10MM ∅", f"{ROD_10_LENGTH} MM",    rod10),
        CuttingRow("NUTS",              "10MM ∅", "-",                       2 * rod10),
        CuttingRow("WASHER", "2.1MM THK. X 25MM∅",   "-",                   2 * rod10),
        CuttingRow("THREADED J-BOLT",       "12MM ∅", "300 MM",             hw12),
        CuttingRow("STRAIGHT THREADED ROD", "12MM ∅", "150 MM",             hw12),
        CuttingRow("NUTS",                  "12MM ∅", "-",                  3 * hw12),
        CuttingRow("WASHER", "2.8MM THK. X 35MM∅",   "-",                  3 * hw12),
    ]

    if cladding == "double":
        rows.append(CuttingRow("RIBLATH", f"600 X {panel_width:.0f} MM", "-", 5))
    else:
        tadtad = math.ceil(panel_height / TADTAD_STRIP_W)
        rows.append(CuttingRow("TADTAD", f"300x{panel_width:.0f} MM", "-", tadtad))

    return _consolidate(rows)
