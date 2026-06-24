"""
CBFT panel drawings beyond the cutting-list table:
  1. Wall elevation view  — L × 2100 mm, plates, studs, X-brace, full dimensions
  2. Flat-bar plan callout — thin cross-section with stud-spacing dimensions
  3. Bot-plate detail     — plate cross-section with dowel holes
  4. Top-plate detail     — plate cross-section with J-bolt holes

Layout (matching the reference panel_1200A_detail.dxf): all four drawings are
stacked VERTICALLY above the cutting-list table, horizontally centred on the
table width.  Dimensions use real DXF DIMENSION entities with the DIM100 style.
"""
from __future__ import annotations
import math
from ezdxf.layouts import Modelspace

from .cutting_rules import (
    PLATE_THICKNESS, PLATE_WIDTH, STUD_DIAMETER,
    WALL_HEIGHT_TOTAL, STUD_HEIGHT, FLATBAR_H_TRIM,
)
from .table_writer import (
    TABLE_LEFT_X, TABLE_RIGHT_X, TITLE_TOP_Y,
)

# ── Derived constants ─────────────────────────────────────────────────────────
STUD_RADIUS  = STUD_DIAMETER / 2     # 50 mm
TABLE_CX     = (TABLE_LEFT_X + TABLE_RIGHT_X) / 2   # horizontal centre of table

# ── Layer names (registered by src/layers.setup_layers) ───────────────────────
_L_ELEV    = "0-S2"              # elevation panel outline
_L_VP      = "VP"               # outer callout box border
_L_PLATE   = "AR-Timber Plate"  # timber-plate rectangles
_L_STUD    = "AR-Bamboo Stud"   # stud bodies
_L_PANELS  = "AR-Panels"        # stud cross-section circles + hole circles
_L_FLATBAR = "AR-Flatbar"       # flat bar / X-brace
_L_LEADER  = "0-S1"             # leaders and flat-bar anchor box
_L_TEXT    = "A-Main Text"      # primary labels
_L_SPEC    = "A-Specifications" # secondary annotations
_L_DIM     = "A-DIMENSIONS"     # dimension lines
_L_HATCH   = "A-Hatch"          # hatching

# ── Vertical stacking (absolute Y, above the title block top) ─────────────────
_GAP_TITLE_ELEV = 300    # title-block top → elevation bottom
_GAP_ELEV_FB    = 550    # elevation top   → flat-bar callout
_GAP_FB_BP      = 700    # flat-bar callout → bot-plate detail
_GAP_BP_TP      = 450    # bot-plate detail → top-plate detail

# ── Dimension offsets ─────────────────────────────────────────────────────────
_DIM_OFF_1 = 150    # first dimension line offset from the geometry
_DIM_OFF_2 = 400    # overall dimension line offset

# ── Callout box ───────────────────────────────────────────────────────────────
_BOX_H        = 100
_PLATE_MARGIN = (_BOX_H - PLATE_WIDTH) / 2   # 6 mm centring margin

_TH = 100   # label text height


# ─────────────────────────────────────────────────────────────────────────────
# Geometry helpers
# ─────────────────────────────────────────────────────────────────────────────

def _stud_x_all(L: float, t1: int, t2: int) -> list[float]:
    """X of all studs (T1+T2), left→right, relative to panel left edge."""
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
    """X of the two end T1 studs (connection-hole positions)."""
    return [STUD_RADIUS, L - STUD_RADIUS]


def _panel_left(L: float) -> float:
    """Left edge X so the panel is centred on the table width."""
    return TABLE_CX - L / 2


def _poly(msp, pts, closed, layer):
    msp.add_lwpolyline(pts, close=closed, dxfattribs={"layer": layer})


def _line(msp, p0, p1, layer):
    msp.add_line(p0, p1, dxfattribs={"layer": layer})


def _circle(msp, cx, cy, r, layer):
    msp.add_circle((cx, cy), r, dxfattribs={"layer": layer})


def _text(msp, s, x, y, layer=_L_TEXT, h=_TH):
    msp.add_text(s, height=h, dxfattribs={"layer": layer, "insert": (x, y)})


def _leader(msp, pts):
    msp.add_leader(pts, dxfattribs={"layer": _L_LEADER})


def _hatch_rect(msp, x, y, w, h, pattern="ANSI31", scale=25.0):
    hatch = msp.add_hatch(dxfattribs={"layer": _L_HATCH})
    hatch.set_pattern_fill(pattern, scale=scale)
    hatch.paths.add_polyline_path(
        [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], is_closed=True)


def _solid_circle(msp, cx, cy, r, layer):
    _circle(msp, cx, cy, r, layer)
    n = 24
    pts = [(cx + r * math.cos(2 * math.pi * i / n),
            cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    h = msp.add_hatch(dxfattribs={"layer": layer})
    h.set_pattern_fill("SOLID")
    h.paths.add_polyline_path(pts, is_closed=True)


# ── Real DXF dimensions (DIM100 style) ────────────────────────────────────────

def _hdim(msp, x1, x2, y_geom, y_dimline):
    """Horizontal linear dimension between x1 and x2."""
    dim = msp.add_linear_dim(
        base=((x1 + x2) / 2, y_dimline),
        p1=(x1, y_geom), p2=(x2, y_geom),
        angle=0, dimstyle="DIM100",
        dxfattribs={"layer": _L_DIM},
    )
    dim.render()


def _vdim(msp, y1, y2, x_geom, x_dimline):
    """Vertical linear dimension between y1 and y2."""
    dim = msp.add_linear_dim(
        base=(x_dimline, (y1 + y2) / 2),
        p1=(x_geom, y1), p2=(x_geom, y2),
        angle=90, dimstyle="DIM100",
        dxfattribs={"layer": _L_DIM},
    )
    dim.render()


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Full wall elevation view
# ─────────────────────────────────────────────────────────────────────────────

def _draw_elevation(msp, L, t1, t2, ox, oy, wall_height=WALL_HEIGHT_TOTAL):
    """Draw a 1:1 wall elevation with plates, studs, X-brace and dimensions.
    (ox, oy) = bottom-left corner of the panel."""
    H  = wall_height
    tp = PLATE_THICKNESS      # 38
    sr = STUD_RADIUS          # 50

    # Panel outline
    _poly(msp, [(ox, oy), (ox + L, oy), (ox + L, oy + H), (ox, oy + H)],
          closed=True, layer=_L_ELEV)

    # Bottom + top timber plates (hatched)
    _poly(msp, [(ox, oy), (ox + L, oy), (ox + L, oy + tp), (ox, oy + tp)],
          closed=True, layer=_L_PLATE)
    _hatch_rect(msp, ox, oy, L, tp)
    _poly(msp, [(ox, oy + H - tp), (ox + L, oy + H - tp),
                (ox + L, oy + H), (ox, oy + H)], closed=True, layer=_L_PLATE)
    _hatch_rect(msp, ox, oy + H - tp, L, tp)

    # Bamboo studs: body rectangle + circular cross-sections at both plates
    studs = _stud_x_all(L, t1, t2)
    for sx in studs:
        cx = ox + sx
        _poly(msp, [(cx - sr, oy + tp), (cx + sr, oy + tp),
                    (cx + sr, oy + H - tp), (cx - sr, oy + H - tp)],
              closed=True, layer=_L_STUD)
        _circle(msp, cx, oy + tp / 2, sr, _L_PANELS)
        _circle(msp, cx, oy + H - tp / 2, sr, _L_PANELS)

    # Flat-bar X-brace (full panel height, trimmed at ends)
    xl = ox + FLATBAR_H_TRIM / 2
    xr = ox + L - FLATBAR_H_TRIM / 2
    _line(msp, (xl, oy + tp), (xr, oy + H - tp), _L_FLATBAR)
    _line(msp, (xl, oy + H - tp), (xr, oy + tp), _L_FLATBAR)

    # ── Top dimension chain: stud spacings + overall width ────────────────────
    y_d1 = oy + H + _DIM_OFF_1
    y_d2 = oy + H + _DIM_OFF_2
    for a, b in zip(studs, studs[1:]):
        _hdim(msp, ox + a, ox + b, oy + H, y_d1)
    _hdim(msp, ox, ox + L, oy + H, y_d2)

    # ── Left dimension chain: plate / stud / overall heights ──────────────────
    x_d1 = ox - _DIM_OFF_1
    x_d2 = ox - _DIM_OFF_2
    _vdim(msp, oy, oy + tp, ox, x_d1)                    # bottom plate (38)
    _vdim(msp, oy + tp, oy + H - tp, ox, x_d1)           # stud clear (2024)
    _vdim(msp, oy + H - tp, oy + H, ox, x_d1)            # top plate (38)
    _vdim(msp, oy, oy + H, ox, x_d2)                     # overall (2100)


# ─────────────────────────────────────────────────────────────────────────────
# 2.  Flat-bar plan callout
# ─────────────────────────────────────────────────────────────────────────────

def _draw_flatbar_callout(msp, L, t1, t2, ox, oy):
    """Plan-view cross-section at the flat-bar level with stud-spacing dims.
    (ox, oy) = bottom-left of the thin anchor strip."""
    strip_h = 25
    # Leader-anchor strip (0-S1)
    _poly(msp, [(ox, oy), (ox + L, oy), (ox + L, oy + strip_h), (ox, oy + strip_h)],
          closed=True, layer=_L_LEADER)
    # Flat-bar line just above the strip
    fb_y = oy + strip_h + 6
    _poly(msp, [(ox + FLATBAR_H_TRIM / 2, fb_y),
                (ox + L - FLATBAR_H_TRIM / 2, fb_y)],
          closed=False, layer=_L_FLATBAR)
    # Stud circles
    stud_cy = fb_y
    for sx in _stud_x_all(L, t1, t2):
        _circle(msp, ox + sx, stud_cy, STUD_RADIUS, _L_PANELS)

    # Stud-spacing dimensions above
    studs = _stud_x_all(L, t1, t2)
    y_d1 = oy + strip_h + STUD_RADIUS + _DIM_OFF_1
    y_d2 = y_d1 + (_DIM_OFF_2 - _DIM_OFF_1)
    for a, b in zip(studs, studs[1:]):
        _hdim(msp, ox + a, ox + b, fb_y, y_d1)
    _hdim(msp, ox, ox + L, fb_y, y_d2)

    # Label + leader
    lbl_x, lbl_y = ox + L * 0.55, oy - 170
    _text(msp, "FLATBAR", lbl_x, lbl_y, layer=_L_SPEC)
    _leader(msp, [(ox + L * 0.75, oy),
                  (ox + L * 0.75, oy - 120),
                  (lbl_x - 10, oy - 120)])


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Individual plate detail callout
# ─────────────────────────────────────────────────────────────────────────────

def _draw_plate_callout(msp, L, hole_r, ox, oy,
                        plate_label, hole_label, show_inner_dim=False):
    """One plate connection-detail callout (top or bottom plate).
    (ox, oy) = bottom-left of the outer 100 mm box."""
    # Outer viewport border
    _poly(msp, [(ox, oy), (ox + L, oy), (ox + L, oy + _BOX_H), (ox, oy + _BOX_H)],
          closed=True, layer=_L_VP)
    # Plate rectangle (88 mm, centred in the box)
    py0 = oy + _PLATE_MARGIN
    py1 = py0 + PLATE_WIDTH
    _poly(msp, [(ox, py0), (ox + L, py0), (ox + L, py1), (ox, py1)],
          closed=True, layer=_L_PLATE)
    # Connection holes at T1 positions
    cy = oy + _BOX_H / 2
    holes = _t1_x(L)
    for hx in holes:
        _solid_circle(msp, ox + hx, cy, hole_r, _L_PANELS)

    # Inner hole-to-hole dimension (closest to plate) + overall width above it
    if show_inner_dim and len(holes) >= 2:
        _hdim(msp, ox + holes[0], ox + holes[-1], oy + _BOX_H, oy + _BOX_H + _DIM_OFF_1)
        _hdim(msp, ox, ox + L, oy + _BOX_H, oy + _BOX_H + _DIM_OFF_2)
    else:
        _hdim(msp, ox, ox + L, oy + _BOX_H, oy + _BOX_H + _DIM_OFF_1)

    # Plate label (left, above the box)
    _text(msp, plate_label, ox + 40, oy + _BOX_H + 30, layer=_L_TEXT)
    # Hole annotation + leader
    ann_x = ox + L + 120
    ann_y = oy + _BOX_H * 0.55
    _text(msp, hole_label, ann_x, ann_y, layer=_L_SPEC)
    _leader(msp, [(ox + L - STUD_RADIUS, cy),
                  (ox + L + 60, ann_y + 40),
                  (ann_x - 10, ann_y + 40)])


# ─────────────────────────────────────────────────────────────────────────────
# Backwards-compat shim
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
                 origin_y:    float = 0.0,
                 wall_height: float = WALL_HEIGHT_TOTAL) -> None:
    """
    Draw the elevation view and three detail callouts, stacked vertically above
    the cutting-list table (matching the reference layout).

    Call this AFTER write_cutting_table().
    """
    L  = wall_length
    ox = origin_x + _panel_left(L)

    # 1. Elevation — just above the title block
    elev_oy = origin_y + TITLE_TOP_Y + _GAP_TITLE_ELEV
    _draw_elevation(msp, L, t1_count, t2_count, ox, elev_oy, wall_height)

    # 2. Flat-bar plan callout
    y_fb = elev_oy + wall_height + _DIM_OFF_2 + _GAP_ELEV_FB
    _draw_flatbar_callout(msp, L, t1_count, t2_count, ox, y_fb)

    # 3. Bottom-plate detail
    y_bp = y_fb + _DIM_OFF_2 + _GAP_FB_BP
    _draw_plate_callout(msp, L, 16.0, ox, y_bp,
                        "BOT. PLATE", "DOWEL HOLE")

    # 4. Top-plate detail
    y_tp = y_bp + _BOX_H + _DIM_OFF_1 + _GAP_BP_TP
    _draw_plate_callout(msp, L, 14.0, ox, y_tp,
                        "TOP PLATE", "J-BOLT HOLE", show_inner_dim=True)
