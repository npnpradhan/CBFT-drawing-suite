"""
Write a CBFT cutting list as a DXF table, matching the reference drawing geometry.
All coordinates and text-placement conventions were extracted directly from
panel_1200A_detail.dxf.

Text-placement conventions (verified against the reference):
  • Component names : MTEXT, attachment=1 (TOP_LEFT), baseline-top at row_bot+161
  • Header labels   : TEXT, halign=CENTER, centred in each column at row_bot+61
  • SIZE / LENGTH / QTY values : TEXT, halign=CENTER, centred in each column
  • Long size strings (washers, infill) are centred across the merged SIZE+LENGTH
    region; the SIZE|LENGTH divider is broken on those rows and the length cell
    is left blank (no dash).
"""

from __future__ import annotations
from ezdxf.layouts import Modelspace
from ezdxf.enums import TextEntityAlignment
from typing import List

from .cutting_rules import CuttingRow

# ── Table geometry (mm) — reference-exact ─────────────────────────────────────
TABLE_LEFT_X    = 26.5
TABLE_RIGHT_X   = 4245.1
ROW_HEIGHT      = 225.0   # every row (header + data) is 225 mm

HEADER_SEP_Y    = 3161.4                       # line below the header row
TABLE_TOP_Y     = HEADER_SEP_Y + ROW_HEIGHT    # 3386.4 — outer-border top

# Text Y offsets above each row's BOTTOM border line
TEXT_VALUE_OFF  = 61    # baseline of centred value TEXT
TEXT_LABEL_OFF  = 161   # top of TOP_LEFT component MTEXT

# ── Column divider X positions ────────────────────────────────────────────────
COL_DIV_1  = 2100.0   # COMPONENT | SIZE
COL_DIV_2  = 2789.1   # SIZE      | LENGTH  (broken on merged rows)
COL_DIV_3  = 3672.4   # LENGTH    | QTY

# ── Text anchor X positions ───────────────────────────────────────────────────
COMP_LEFT_X    = 103.6                              # component MTEXT left edge
SIZE_CX        = (COL_DIV_1 + COL_DIV_2) / 2        # 2253.5  size column centre
LEN_CX         = (COL_DIV_2 + COL_DIV_3) / 2        # 3230.75 length column centre
QTY_CX         = (COL_DIV_3 + TABLE_RIGHT_X) / 2    # 3958.75 qty column centre
MERGED_CX      = (COL_DIV_1 + COL_DIV_3) / 2        # 2695.15 merged size+length centre
COMP_HDR_CX    = (TABLE_LEFT_X + COL_DIV_1) / 2     # 872.2   component header centre

# ── Title block (separate box above the main table) ──────────────────────────
TITLE_TOP_Y   = 3988.6
TITLE_BOT_Y   = 3538.6
TITLE_MID_Y   = 3763.6   # horizontal divider inside title block
TITLE_V_DIV   = 776.5    # vertical divider (label | value)
TITLE_LABEL_X = 77.2     # NAME / QTY label left edge

TEXT_H        = 100       # default text height for all entities

# A size string is "merged" (spans SIZE+LENGTH, divider broken) when it is long
# and the length column is unused.
_MERGE_MIN_LEN = 13

LAYER_TEXT    = "A-Main Text"
LAYER_BORDER  = "0-S2"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _text_left(msp: Modelspace, s: str, x: float, y: float,
               layer: str = LAYER_TEXT, height: float = TEXT_H) -> None:
    """Left-aligned TEXT, baseline at (x, y)."""
    t = msp.add_text(s, height=height, dxfattribs={"layer": layer})
    t.set_placement((x, y), align=TextEntityAlignment.LEFT)


def _text_center(msp: Modelspace, s: str, cx: float, y: float,
                 layer: str = LAYER_TEXT, height: float = TEXT_H) -> None:
    """Horizontally-centred TEXT, baseline-centre at (cx, y)."""
    t = msp.add_text(s, height=height, dxfattribs={"layer": layer})
    t.set_placement((cx, y), align=TextEntityAlignment.CENTER)


def _mtext_tl(msp: Modelspace, s: str, x: float, y_top: float,
              width: float, layer: str = LAYER_TEXT,
              height: float = TEXT_H) -> None:
    """MTEXT with TOP_LEFT attachment (group code 71 = 1) — top edge at y_top."""
    msp.add_mtext(s, dxfattribs={
        "layer":            layer,
        "char_height":      height,
        "insert":           (x, y_top),
        "attachment_point": 1,        # TOP_LEFT
        "width":            width,
    })


def _hline(msp: Modelspace, x0: float, x1: float, y: float) -> None:
    msp.add_line((x0, y), (x1, y), dxfattribs={"layer": LAYER_BORDER})


def _vline(msp: Modelspace, x: float, y0: float, y1: float) -> None:
    msp.add_line((x, y0), (x, y1), dxfattribs={"layer": LAYER_BORDER})


def _lwpoly(msp: Modelspace, pts: list, closed: bool = True) -> None:
    msp.add_lwpolyline(pts, close=closed, dxfattribs={"layer": LAYER_BORDER})


def _is_merged(row: CuttingRow) -> bool:
    """True if the size string should span the merged SIZE+LENGTH region."""
    return row.length == "-" and len(row.size) >= _MERGE_MIN_LEN


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
    """
    ox, oy = origin_x, origin_y

    def tx(x: float) -> float: return x + ox
    def ty(y: float) -> float: return y + oy

    n = len(rows)
    # outer-border bottom: one extra empty margin row below the last data row
    table_bot = HEADER_SEP_Y - (n + 1) * ROW_HEIGHT

    # ── Title block ───────────────────────────────────────────────────────────
    _lwpoly(msp, [
        (tx(TABLE_LEFT_X),  ty(TITLE_BOT_Y)),
        (tx(TABLE_RIGHT_X), ty(TITLE_BOT_Y)),
        (tx(TABLE_RIGHT_X), ty(TITLE_TOP_Y)),
        (tx(TABLE_LEFT_X),  ty(TITLE_TOP_Y)),
    ])
    _hline(msp, tx(TABLE_LEFT_X), tx(TABLE_RIGHT_X), ty(TITLE_MID_Y))
    _vline(msp, tx(TITLE_V_DIV), ty(TITLE_BOT_Y), ty(TITLE_TOP_Y))

    _text_left(msp, "NAME", tx(TITLE_LABEL_X), ty(TITLE_MID_Y + TEXT_VALUE_OFF))
    _text_left(msp, "QTY",  tx(TITLE_LABEL_X), ty(TITLE_BOT_Y + TEXT_VALUE_OFF))
    if panel_id:
        _text_left(msp, panel_id, tx(TITLE_V_DIV + 50),
                   ty(TITLE_MID_Y + TEXT_VALUE_OFF))

    # ── Main outer border ─────────────────────────────────────────────────────
    _lwpoly(msp, [
        (tx(TABLE_LEFT_X),  ty(table_bot)),
        (tx(TABLE_RIGHT_X), ty(table_bot)),
        (tx(TABLE_RIGHT_X), ty(TABLE_TOP_Y)),
        (tx(TABLE_LEFT_X),  ty(TABLE_TOP_Y)),
    ])

    # ── Header row ────────────────────────────────────────────────────────────
    _hline(msp, tx(TABLE_LEFT_X), tx(TABLE_RIGHT_X), ty(HEADER_SEP_Y))
    header_y = ty(HEADER_SEP_Y + TEXT_VALUE_OFF)
    _text_center(msp, "COMPONENT", tx(COMP_HDR_CX), header_y)
    _text_center(msp, "SIZE",      tx(SIZE_CX),     header_y)
    _text_center(msp, "LENGTH",    tx(LEN_CX),      header_y)
    _text_center(msp, "QTY",       tx(QTY_CX),      header_y)

    # ── Full-height vertical dividers (COMPONENT|SIZE and LENGTH|QTY) ──────────
    _vline(msp, tx(COL_DIV_1), ty(table_bot), ty(TABLE_TOP_Y))
    _vline(msp, tx(COL_DIV_3), ty(table_bot), ty(TABLE_TOP_Y))

    # SIZE|LENGTH divider across the header row (always present)
    _vline(msp, tx(COL_DIV_2), ty(HEADER_SEP_Y), ty(TABLE_TOP_Y))

    # ── Data rows ─────────────────────────────────────────────────────────────
    for i, row in enumerate(rows):
        row_bot = HEADER_SEP_Y - (i + 1) * ROW_HEIGHT
        row_top = row_bot + ROW_HEIGHT
        y_base  = ty(row_bot + TEXT_VALUE_OFF)
        y_label = ty(row_bot + TEXT_LABEL_OFF)
        merged  = _is_merged(row)

        # Component name — TOP_LEFT MTEXT (single line, vertically centred)
        _mtext_tl(msp, row.component, tx(COMP_LEFT_X), y_label,
                  width=COL_DIV_1 - COMP_LEFT_X)

        # Size value
        if merged:
            _text_center(msp, row.size, tx(MERGED_CX), y_base)
        else:
            _text_center(msp, row.size, tx(SIZE_CX), y_base)

        # Length value (skipped on merged rows)
        if not merged:
            _text_center(msp, row.length, tx(LEN_CX), y_base)

        # Qty value
        _text_center(msp, f"{row.qty} {row.unit}", tx(QTY_CX), y_base)

        # SIZE|LENGTH divider segment for this row (broken on merged rows)
        if not merged:
            _vline(msp, tx(COL_DIV_2), ty(row_bot), ty(row_top))

        # Bottom border of this row
        _hline(msp, tx(TABLE_LEFT_X), tx(TABLE_RIGHT_X), ty(row_bot))
