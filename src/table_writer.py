"""
Write a CBFT cutting list as a DXF table, matching the reference drawing geometry.
All coordinates derived from measurement of panel_1200A_detail.dxf.
"""

from __future__ import annotations
from ezdxf.layouts import Modelspace
from typing import List

from .cutting_rules import CuttingRow

# ── Table geometry (mm) — reference-exact ─────────────────────────────────────
TABLE_LEFT_X    = 26.5
TABLE_RIGHT_X   = 4245.1
ROW_HEIGHT      = 225.0   # every row (header + data) is 225 mm

# The table HEADER separator sits at 3161.4 in the reference.
# The outer-border TOP  = HEADER_SEP_Y + ROW_HEIGHT = 3386.4.
HEADER_SEP_Y    = 3161.4
TABLE_TOP_Y     = HEADER_SEP_Y + ROW_HEIGHT          # 3386.4

# Text Y offset above each row's BOTTOM border line
TEXT_LABEL_OFF  = 161   # component / row label
TEXT_VALUE_OFF  = 61    # size / length / qty values

# ── Column divider X positions ────────────────────────────────────────────────
COL_DIV_1  = 1717.9   # COMPONENT | SIZE
COL_DIV_2  = 2789.1   # SIZE      | LENGTH
COL_DIV_3  = 3672.4   # LENGTH    | QTY

# ── Text anchor X positions (left edge of each value) ────────────────────────
COL_COMP_X    = 103.6   # component label
COL_SIZE_X    = 1895.1  # size value
COL_LEN_X     = 2909.3  # length value (non-dash)
COL_DASH_X    = 3187.9  # length "-" dash (centred in length col)
COL_QTY_X     = 3772.2  # qty value

# ── Title block (separate box above the main table) ──────────────────────────
TITLE_TOP_Y   = 3988.6
TITLE_BOT_Y   = 3538.6
TITLE_MID_Y   = 3763.6   # horizontal divider inside title block
TITLE_V_DIV   = 776.5    # vertical divider (label | value)

TEXT_H        = 100       # default text height for all entities

LAYER_TEXT    = "A-Main Text"
LAYER_BORDER  = "0-S2"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _text(msp: Modelspace, s: str, x: float, y: float,
          layer: str = LAYER_TEXT, height: float = TEXT_H) -> None:
    """Plain DXF TEXT entity — baseline at (x, y)."""
    msp.add_text(s, dxfattribs={"layer": layer, "height": height,
                                "insert": (x, y)})


def _mtext(msp: Modelspace, s: str, x: float, y: float,
           width: float = 1600.0, layer: str = LAYER_TEXT,
           height: float = TEXT_H) -> None:
    """
    MTEXT entity with BOTTOM-LEFT attachment so the baseline sits at y.
    Used for component names so long labels wrap within the column.
    """
    msp.add_mtext(s, dxfattribs={
        "layer":            layer,
        "char_height":      height,
        "insert":           (x, y),
        "attachment_point": 7,    # BOTTOM_LEFT — baseline at insert y
        "width":            width,
    })


def _hline(msp: Modelspace, x0: float, x1: float, y: float) -> None:
    msp.add_line((x0, y), (x1, y), dxfattribs={"layer": LAYER_BORDER})


def _vline(msp: Modelspace, x: float, y0: float, y1: float) -> None:
    msp.add_line((x, y0), (x, y1), dxfattribs={"layer": LAYER_BORDER})


def _lwpoly(msp: Modelspace, pts: list, closed: bool = True) -> None:
    msp.add_lwpolyline(pts, close=closed,
                       dxfattribs={"layer": LAYER_BORDER})


# ─────────────────────────────────────────────────────────────────────────────
# Public function
# ─────────────────────────────────────────────────────────────────────────────

def write_cutting_table(msp: Modelspace,
                        rows: List[CuttingRow],
                        origin_x: float = 0.0,
                        origin_y: float = 0.0,
                        panel_id: str = "") -> None:
    """
    Draw a CBFT cutting-list table into model-space at the given origin.

    Geometry matches the reference panel detail DXF files (R2018 format).

    Parameters
    ----------
    msp       : ezdxf model-space layout
    rows      : cutting list rows from compute_cutting_list()
    origin_x  : X translation for the whole table
    origin_y  : Y translation for the whole table
    panel_id  : panel identifier shown in the title block (e.g. "PANEL 1200A")
    """
    ox, oy = origin_x, origin_y

    def tx(x: float) -> float: return x + ox
    def ty(y: float) -> float: return y + oy

    n = len(rows)

    # outer-border bottom: one extra empty row below the last data row
    table_bot = HEADER_SEP_Y - (n + 1) * ROW_HEIGHT

    # ── Title block (above the outer border) ─────────────────────────────────
    _lwpoly(msp, [
        (tx(TABLE_LEFT_X), ty(TITLE_BOT_Y)),
        (tx(TABLE_RIGHT_X), ty(TITLE_BOT_Y)),
        (tx(TABLE_RIGHT_X), ty(TITLE_TOP_Y)),
        (tx(TABLE_LEFT_X), ty(TITLE_TOP_Y)),
    ])
    _hline(msp, tx(TABLE_LEFT_X), tx(TABLE_RIGHT_X), ty(TITLE_MID_Y))
    _vline(msp, tx(TITLE_V_DIV), ty(TITLE_BOT_Y), ty(TITLE_TOP_Y))

    # Title block row labels
    _text(msp, "NAME", tx(77.2), ty(TITLE_BOT_Y + TEXT_VALUE_OFF + ROW_HEIGHT))
    _text(msp, "QTY",  tx(77.2), ty(TITLE_BOT_Y + TEXT_VALUE_OFF))

    # Title block value cell — panel identifier in the NAME row
    if panel_id:
        _text(msp, panel_id, tx(TITLE_V_DIV + 50), ty(TITLE_BOT_Y + TEXT_VALUE_OFF + ROW_HEIGHT))

    # ── Main outer border ─────────────────────────────────────────────────────
    _lwpoly(msp, [
        (tx(TABLE_LEFT_X), ty(table_bot)),
        (tx(TABLE_RIGHT_X), ty(table_bot)),
        (tx(TABLE_RIGHT_X), ty(TABLE_TOP_Y)),
        (tx(TABLE_LEFT_X), ty(TABLE_TOP_Y)),
    ])

    # ── Header row ────────────────────────────────────────────────────────────
    _hline(msp, tx(TABLE_LEFT_X), tx(TABLE_RIGHT_X), ty(HEADER_SEP_Y))
    header_y = ty(HEADER_SEP_Y + TEXT_VALUE_OFF)
    _text(msp, "COMPONENT", tx(COL_COMP_X), header_y)
    _text(msp, "SIZE",      tx(COL_SIZE_X), header_y)
    _text(msp, "LENGTH",    tx(COL_LEN_X),  header_y)
    _text(msp, "QTY",       tx(COL_QTY_X),  header_y)

    # ── Vertical column dividers (full table height) ──────────────────────────
    for col_x in (COL_DIV_1, COL_DIV_2, COL_DIV_3):
        _vline(msp, tx(col_x), ty(table_bot), ty(TABLE_TOP_Y))

    # ── Data rows ─────────────────────────────────────────────────────────────
    row_bot = HEADER_SEP_Y   # bottom of the current row starts at header sep

    for row in rows:
        row_bot -= ROW_HEIGHT

        y_label = ty(row_bot + TEXT_LABEL_OFF)
        y_value = ty(row_bot + TEXT_VALUE_OFF)

        # Component label — MTEXT so long names wrap inside the column
        _mtext(msp, row.component, tx(COL_COMP_X), y_label,
               width=COL_DIV_1 - COL_COMP_X - 20)

        # Size — use MTEXT if the string contains special chars (e.g. washers)
        if len(row.size) > 12:
            _mtext(msp, row.size, tx(COL_SIZE_X), y_value,
                   width=COL_DIV_2 - COL_SIZE_X - 20)
        else:
            _text(msp, row.size, tx(COL_SIZE_X), y_value)

        # Length — dash uses centred position, real values are left-aligned
        if row.length == "-":
            _text(msp, "-", tx(COL_DASH_X), y_value)
        else:
            _text(msp, row.length, tx(COL_LEN_X), y_value)

        # Qty
        _text(msp, f"{row.qty} {row.unit}", tx(COL_QTY_X), y_value)

        # Bottom border of this row
        _hline(msp, tx(TABLE_LEFT_X), tx(TABLE_RIGHT_X), ty(row_bot))
