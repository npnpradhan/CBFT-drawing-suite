"""
CBFT panel drawings beyond the cutting-list table:
  1. Wall elevation view  — L × 2100 mm, with plates, studs, and X-brace
  2. Flat-bar plan callout — thin cross-section at flat-bar height (plan view)
  3. Bot-plate detail     — plate cross-section with dowel holes (R=16)
  4. Top-plate detail     — plate cross-section with J-bolt holes (R=14)

Layout (all Y values absolute, not relative to origin):
  Elevation view : placed to the RIGHT of the cutting-list table
  Detail callouts: stacked above the cutting-list table
"""
from __future__ import annotations
import math
from ezdxf.layouts import Modelspace

from .cutting_rules import (
    PLATE_THICKNESS, PLATE_WIDTH, STUD_DIAMETER,
    WALL_HEIGHT_TOTAL, STUD_HEIGHT, FLATBAR_H_TRIM, FLATBAR_W, FLATBAR_T,
)
from .table_writer import (
    TABLE_LEFT_X, TABLE_RIGHT_X, TABLE_TOP_Y,
    TITLE_TOP_Y,
)

# ── Derived constants ─────────────────────────────────────────────────────────
STUD_RADIUS = STUD_DIAMETER / 2      # 50 mm

# ── Layer names (matching reference files) ────────────────────────────────────
_L_ELEV    = "0-S2"              # elevation outline
_L_VP      = "VP"               # outer callout box border
_L_PLATE   = "AR-Timber Plate"  # plate rectangles
_L_PANELS  = "AR-Panels"        # stud profiles + hole circles
_L_FLATBAR = "AR-Flatbar"       # flat bar / X-brace
_L_LEADER  = "0-S1"             # leaders and flatbar anchor box
_L_TEXT    = "A-Main Text"      # primary labels
_L_SPEC    = "A-Specifications" # secondary annotations
_L_DIM     = "A-DIMENSIONS"     # dimension lines
_L_HATCH   = "A-Hatch"          # hatching

# ── Elevation placement: to the right of the cutting-list table ───────────────
ELEV_GAP_X   = 600   # gap between table right edge and elevation left edge
ELEV_OFFSET_X = TABLE_RIGHT_X + ELEV_GAP_X   # start X for elevation drawing

# ── Detail callout placement: above the table ─────────────────────────────────
_BOX_H          = 100    # outer callout box height
_PLATE_MARGIN   = (_BOX_H - PLATE_WIDTH) / 2    # 6 mm centring margin
_GAP_ABOVE_TABLE = 500   # gap from TITLE_TOP_Y to bottom of flatbar callout
_GAP_FB_BP      = 350    # gap between flatbar callout and bot-plate detail
_GAP_BP_TP      = 450    # gap between bot-plate and top-plate details

# ── Text heights ──────────────────────────────────────────────────────────────
_TH = 100


# ─────────────────────────────────────────────────────────────────────────────
# Geometry helpers
# ─────────────────────────────────────────────────────────────────────────────

def _stud_x_all(L: float, t1: int, t2: int) -> list[float]:
    """X positions of all studs (T1 + T2), left to right, relative to panel left."""
    total = t1 + t2
    if total == 0:
        return []
    if total == 1:
        return [L / 2]
    left, right = STUD_RADIUS, L - STUD_RADIUS
    inner_n = total - 2
    inner: list[float] = []
    if inner_n > 0:
        sp = (right - left) / (inner_n + 1)
        inner = [left + sp * i for i in range(1, inner_n + 1)]
    return [left] + inner + [right]


def _t1_x(L: float) -> list[float]:
    """X positions of the two end T1 studs."""
    return [STUD_RADIUS, L - STUD_RADIUS]


def _poly(msp: Modelspace, pts: list[tuple], closed: bool, layer: str) -> None:
    msp.add_lwpolyline(pts, close=closed, dxfattribs={"layer": layer})


def _line(msp: Modelspace, p0: tuple, p1: tuple, layer: str) -> None:
    msp.add_line(p0, p1, dxfattribs={"layer": layer})


def _circle(msp: Modelspace, cx: float, cy: float, r: float, layer: str) -> None:
    msp.add_circle((cx, cy), r, dxfattribs={"layer": layer})


def _filled_circle(msp: Modelspace, cx: float, cy: float, r: float,
                   layer: str = _L_PANELS) -> None:
    """Circle + SOLID hatch approximated as a 32-point polyline."""
    _circle(msp, cx, cy, r, layer)
    n = 32
    pts = [(cx + r * math.cos(2 * math.pi * i / n),
            cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    h = msp.add_hatch(dxfattribs={"layer": layer})
    h.set_pattern_fill("SOLID")
    h.paths.add_polyline_path(pts, is_closed=True)


def _text(msp: Modelspace, s: str, x: float, y: float,
          layer: str = _L_TEXT, h: float = _TH) -> None:
    msp.add_text(s, dxfattribs={"layer": layer, "height": h, "insert": (x, y)})


def _leader(msp: Modelspace, pts: list[tuple]) -> None:
    msp.add_leader(pts, dxfattribs={"layer": _L_LEADER})


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Full wall elevation view
# ─────────────────────────────────────────────────────────────────────────────

def _draw_elevation(msp: Modelspace, L: float,
                    t1: int, t2: int,
                    ox: float, oy: float) -> None:
    """
    Draw a 1:1 wall elevation of the panel at origin (ox, oy).

    Shows: panel outline, timber plates (hatched), bamboo stud profiles
    (rectangles + circles at plate cross-sections), flat-bar X-brace,
    and dimension annotations.
    """
    H  = WALL_HEIGHT_TOTAL    # 2100
    tp = PLATE_THICKNESS      # 38
    sr = STUD_RADIUS          # 50

    # ── Panel outline ─────────────────────────────────────────────────────────
    _poly(msp, [(ox, oy), (ox+L, oy), (ox+L, oy+H), (ox, oy+H)],
          closed=True, layer=_L_ELEV)

    # ── Bottom timber plate (hatched) ─────────────────────────────────────────
    _poly(msp, [(ox, oy), (ox+L, oy), (ox+L, oy+tp), (ox, oy+tp)],
          closed=True, layer=_L_PLATE)
    _hatch_rect(msp, ox, oy, L, tp)

    # ── Top timber plate (hatched) ────────────────────────────────────────────
    _poly(msp, [(ox, oy+H-tp), (ox+L, oy+H-tp),
                (ox+L, oy+H),  (ox, oy+H)],
          closed=True, layer=_L_PLATE)
    _hatch_rect(msp, ox, oy+H-tp, L, tp)

    # ── Bamboo studs in elevation ──────────────────────────────────────────────
    stud_positions = _stud_x_all(L, t1, t2)
    for sx in stud_positions:
        cx = ox + sx
        # Stud body: vertical rectangle between plates
        _poly(msp, [
            (cx - sr, oy + tp),   (cx + sr, oy + tp),
            (cx + sr, oy + H-tp), (cx - sr, oy + H-tp),
        ], closed=True, layer=_L_PANELS)
        # Circular cross-section at bottom plate
        _circle(msp, cx, oy + tp / 2, sr, _L_PANELS)
        # Circular cross-section at top plate
        _circle(msp, cx, oy + H - tp / 2, sr, _L_PANELS)

    # ── Flat-bar X-brace ──────────────────────────────────────────────────────
    fb_x_l = ox + FLATBAR_H_TRIM / 2    # 25 mm from left
    fb_x_r = ox + L - FLATBAR_H_TRIM / 2
    fb_y_b = oy + tp                     # top of bottom plate
    fb_y_t = oy + H                      # top of panel (= bottom of top plate? no — full H)

    _line(msp, (fb_x_l, fb_y_b), (fb_x_r, fb_y_t), _L_FLATBAR)
    _line(msp, (fb_x_l, fb_y_t), (fb_x_r, fb_y_b), _L_FLATBAR)

    # ── Dimension: overall width ───────────────────────────────────────────────
    _dim_linear_h(msp, ox, ox + L, oy - 300, f"{L:.0f}")

    # ── Dimension: overall height ──────────────────────────────────────────────
    _dim_linear_v(msp, oy, oy + H, ox + L + 300, f"{H:.0f}")

    # ── Dimension: plate thickness ────────────────────────────────────────────
    _dim_linear_v(msp, oy, oy + tp, ox + L + 600, f"{tp:.0f}")

    # ── Flat-bar label ─────────────────────────────────────────────────────────
    fb_mid_x = ox + L / 2
    fb_mid_y = oy + H / 2
    _text(msp, "FLATBAR", fb_mid_x + 100, fb_mid_y, layer=_L_SPEC)


def _hatch_rect(msp: Modelspace,
                x: float, y: float, w: float, h: float) -> None:
    """ANSI31 hatch for a rectangle."""
    hatch = msp.add_hatch(dxfattribs={"layer": _L_HATCH})
    hatch.set_pattern_fill("ANSI31", scale=50)
    hatch.paths.add_polyline_path(
        [(x, y), (x+w, y), (x+w, y+h), (x, y+h)], is_closed=True
    )


def _dim_linear_h(msp: Modelspace, x0: float, x1: float,
                  y_line: float, label: str) -> None:
    """Minimal horizontal dimension line with text."""
    _line(msp, (x0, y_line), (x1, y_line), _L_DIM)
    _line(msp, (x0, y_line - 50), (x0, y_line + 50), _L_DIM)
    _line(msp, (x1, y_line - 50), (x1, y_line + 50), _L_DIM)
    _text(msp, label, (x0 + x1) / 2, y_line - 170, layer=_L_DIM)


def _dim_linear_v(msp: Modelspace, y0: float, y1: float,
                  x_line: float, label: str) -> None:
    """Minimal vertical dimension line with text."""
    _line(msp, (x_line, y0), (x_line, y1), _L_DIM)
    _line(msp, (x_line - 50, y0), (x_line + 50, y0), _L_DIM)
    _line(msp, (x_line - 50, y1), (x_line + 50, y1), _L_DIM)
    _text(msp, label, x_line + 30, (y0 + y1) / 2, layer=_L_DIM)


# ─────────────────────────────────────────────────────────────────────────────
# 2.  Flat-bar plan callout
# ─────────────────────────────────────────────────────────────────────────────

def _draw_flatbar_callout(msp: Modelspace, L: float,
                          t1: int, t2: int,
                          ox: float, oy: float) -> None:
    """
    Plan-view cross-section at the flat-bar level.
    ox, oy = bottom-left of the outer 100 mm box.
    """
    anchor_h = 25
    # Leader-anchor box (0-S1)
    _poly(msp, [(ox, oy), (ox+L, oy), (ox+L, oy+anchor_h), (ox, oy+anchor_h)],
          closed=True, layer=_L_LEADER)

    # Plate cross-section (PLATE_WIDTH deep)
    p0, p1 = oy + anchor_h + 5, oy + anchor_h + 5 + PLATE_WIDTH
    _poly(msp, [(ox, p0), (ox+L, p0), (ox+L, p1), (ox, p1)],
          closed=True, layer=_L_PLATE)

    # Flat-bar line inside the plate
    fb_y = p0 + PLATE_THICKNESS
    _poly(msp, [(ox + FLATBAR_H_TRIM / 2, fb_y),
                (ox + L - FLATBAR_H_TRIM / 2, fb_y)],
          closed=False, layer=_L_FLATBAR)

    # Stud circles (plan view)
    stud_cy = p0 + PLATE_WIDTH / 2
    for sx in _stud_x_all(L, t1, t2):
        _circle(msp, ox + sx, stud_cy, STUD_RADIUS, _L_PANELS)

    # Label + leader
    lbl_x, lbl_y = ox + L / 2, oy - 150
    _text(msp, "FLATBAR", lbl_x, lbl_y, layer=_L_SPEC)
    _leader(msp, [(ox + L * 0.75, oy + anchor_h + 5),
                  (ox + L * 0.75, oy - 100),
                  (lbl_x - 10, oy - 100)])


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Individual plate detail callout
# ─────────────────────────────────────────────────────────────────────────────

def _draw_plate_callout(msp: Modelspace, L: float,
                        hole_r: float,
                        ox: float, oy: float,
                        plate_label: str,
                        hole_label: str) -> None:
    """
    One plate connection-detail callout (top or bottom plate).
    ox, oy = bottom-left of the outer 100 mm box.
    """
    # Outer viewport border
    _poly(msp, [(ox, oy), (ox+L, oy), (ox+L, oy+_BOX_H), (ox, oy+_BOX_H)],
          closed=True, layer=_L_VP)

    # Plate rectangle (PLATE_WIDTH = 88 mm, centred in box)
    py0 = oy + _PLATE_MARGIN
    py1 = py0 + PLATE_WIDTH
    _poly(msp, [(ox, py0), (ox+L, py0), (ox+L, py1), (ox, py1)],
          closed=True, layer=_L_PLATE)

    # Connection holes at T1 positions
    cy = oy + _BOX_H / 2
    for hx in _t1_x(L):
        _filled_circle(msp, ox + hx, cy, hole_r)

    # Plate label (above the box)
    _text(msp, plate_label, ox + 40, oy + _BOX_H + 30, layer=_L_TEXT)

    # Hole annotation + leader
    ann_x = ox + L + 120
    ann_y = oy + _BOX_H * 0.65
    _text(msp, hole_label, ann_x, ann_y, layer=_L_SPEC)
    _leader(msp, [(ox + L - STUD_RADIUS, cy),
                  (ox + L + 60, cy + 60),
                  (ann_x - 10, cy + 60)])


# ─────────────────────────────────────────────────────────────────────────────
# Layer registration
# ─────────────────────────────────────────────────────────────────────────────

def ensure_layers(doc) -> None:
    """No-op: all layers are registered by setup_layers() in src/layers.py."""


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def draw_details(msp: Modelspace,
                 wall_length: float,
                 t1_count:    int,
                 t2_count:    int,
                 origin_x:    float = 0.0,
                 origin_y:    float = 0.0) -> None:
    """
    Draw the elevation view and three detail callouts alongside the table.

    Call this AFTER write_cutting_table().

    Placement
    ---------
    • Elevation  : to the right of the cutting-list table
    • Callouts   : stacked above the cutting-list table (title block)

    Parameters
    ----------
    msp         : ezdxf model-space layout
    wall_length : panel length in mm
    t1_count    : number of T1 (end) bamboo studs
    t2_count    : number of T2 (intermediate) bamboo studs
    origin_x/y  : offset applied to all geometry (default 0)
    """
    L = wall_length

    # ── 1. Elevation view ─────────────────────────────────────────────────────
    # Vertically centred on the table+title region
    total_h = TITLE_TOP_Y - 0    # ≈ 3989 mm
    elev_oy = origin_y + (total_h - WALL_HEIGHT_TOTAL) / 2
    elev_ox = origin_x + ELEV_OFFSET_X

    _draw_elevation(msp, L, t1_count, t2_count, elev_ox, elev_oy)

    # ── Detail callout X: centre panel on the table width ─────────────────────
    detail_ox = origin_x + max(TABLE_LEFT_X, (TABLE_RIGHT_X - L) / 2)

    # ── 2. Flatbar plan callout ───────────────────────────────────────────────
    y_fb = origin_y + TITLE_TOP_Y + _GAP_ABOVE_TABLE
    _draw_flatbar_callout(msp, L, t1_count, t2_count, detail_ox, y_fb)

    # ── 3. Bottom-plate detail ────────────────────────────────────────────────
    y_bp = y_fb + _BOX_H + _GAP_FB_BP
    _draw_plate_callout(msp, L, 16.0, detail_ox, y_bp,
                        "BOT. PLATE", "DOWEL HOLE")

    # ── 4. Top-plate detail ───────────────────────────────────────────────────
    y_tp = y_bp + _BOX_H + _GAP_BP_TP
    _draw_plate_callout(msp, L, 14.0, detail_ox, y_tp,
                        "TOP PLATE", "J-BOLT HOLE")
