"""
CBFT panel drawings beyond the cutting-list table:
  1. Wall elevation view  — L × H mm, plates, studs (N2N block), X-brace, dimensions
  2. Flat-bar plan callout — cross-section with stud circles (bpns1/bps1 blocks)
  3. Bot-plate detail     — plate cross-section with dowel holes
  4. Top-plate detail     — plate cross-section with J-bolt holes

All major components are inserted as blocks from Assets Description.dxf so the
drawing matches the reference standard.  Falls back to manual geometry when the
assets file is not present.
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
from . import assets as _assets

# ── Layer names ───────────────────────────────────────────────────────────────
_L_ELEV    = "0-S2"
_L_VP      = "VP"
_L_PLATE   = "AR-Timber Plate"
_L_STUD    = "AR-Bamboo Stud"
_L_PANELS  = "AR-Panels"
_L_FLATBAR = "AR-Flatbar"
_L_LEADER  = "0-S1"
_L_TEXT    = "A-Main Text"
_L_SPEC    = "A-Specifications"
_L_DIM     = "A-DIMENSIONS"
_L_HATCH   = "A-Hatch"

# ── Derived constants ─────────────────────────────────────────────────────────
STUD_RADIUS  = STUD_DIAMETER / 2
TABLE_CX     = (TABLE_LEFT_X + TABLE_RIGHT_X) / 2

# ── Plan cross-section constants ──────────────────────────────────────────────
_PANEL_DEPTH = 100   # bamboo frame depth (front-to-back in plan view, mm)
_PLASTER_T   = 25    # cement plaster / sheathing thickness per face (mm)

# ── Vertical stacking ─────────────────────────────────────────────────────────
_GAP_TITLE_ELEV = 300
_GAP_ELEV_FB    = 550
_GAP_FB_BP      = 700
_GAP_BP_TP      = 450

# ── Dimension offsets ─────────────────────────────────────────────────────────
_DIM_OFF_1 = 150
_DIM_OFF_2 = 400

# ── Plate callout box ─────────────────────────────────────────────────────────
_BOX_H        = 100
_PLATE_MARGIN = (_BOX_H - PLATE_WIDTH) / 2

_TH = 100   # label text height


# ─────────────────────────────────────────────────────────────────────────────
# Geometry helpers
# ─────────────────────────────────────────────────────────────────────────────

def _stud_x_all(L: float, t1: int, t2: int) -> list[float]:
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
    return [STUD_RADIUS, L - STUD_RADIUS]


def _panel_left(L: float) -> float:
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


# ── Dimension helpers ─────────────────────────────────────────────────────────

def _hdim(msp, x1, x2, y_geom, y_dimline):
    dim = msp.add_linear_dim(
        base=((x1 + x2) / 2, y_dimline),
        p1=(x1, y_geom), p2=(x2, y_geom),
        angle=0, dimstyle="DIM100",
        dxfattribs={"layer": _L_DIM},
    )
    dim.render()


def _vdim(msp, y1, y2, x_geom, x_dimline):
    dim = msp.add_linear_dim(
        base=(x_dimline, (y1 + y2) / 2),
        p1=(x_geom, y1), p2=(x_geom, y2),
        angle=90, dimstyle="DIM100",
        dxfattribs={"layer": _L_DIM},
    )
    dim.render()


# ── BFGGBN callout marker ─────────────────────────────────────────────────────

def _callout_marker(msp, cx, cy):
    """
    Draw a flat-bar corner callout marker at (cx, cy).
    Uses BFGGBN block from assets; falls back to manual geometry.
    BFGGBN: r=4.5 circle on 0-S4 + 50×38 VP box, both centred at (cx, cy).
    """
    if _assets.add_blockref(msp, "BFGGBN", cx, cy, layer="0-S4"):
        return
    # Fallback: draw manually
    _circle(msp, cx, cy, 4.5, "0-S4")
    _poly(msp, [(cx - 25, cy - 19), (cx + 25, cy - 19),
                (cx + 25, cy + 19), (cx - 25, cy + 19)],
          closed=True, layer=_L_VP)


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Full wall elevation view
# ─────────────────────────────────────────────────────────────────────────────

def _draw_elevation(msp, L, ox, oy, stud_positions, wall_height=WALL_HEIGHT_TOTAL):
    """Draw a 1:1 wall elevation with plates, studs, X-brace and dimensions.

    stud_positions: list of (relative_x, is_t1) sorted left-to-right,
                    where relative_x is measured from the panel left edge.
    """
    H  = wall_height
    tp = PLATE_THICKNESS      # 38
    sh = H - 2 * tp           # stud height

    # Panel outline
    _poly(msp, [(ox, oy), (ox + L, oy), (ox + L, oy + H), (ox, oy + H)],
          closed=True, layer=_L_ELEV)

    # Bottom + top timber plates (hatched)
    _poly(msp, [(ox, oy), (ox + L, oy), (ox + L, oy + tp), (ox, oy + tp)],
          closed=True, layer=_L_PLATE)
    _hatch_rect(msp, ox, oy, L, tp)
    _poly(msp, [(ox, oy + H - tp), (ox + L, oy + H - tp),
                (ox + L, oy + H),   (ox, oy + H)],
          closed=True, layer=_L_PLATE)
    _hatch_rect(msp, ox, oy + H - tp, L, tp)

    # Bamboo studs — positions and types come from the plan DXF
    # T1 (end/corner): N2N block — J-bolt + foundation connection hatching
    # T2 (intermediate): Type B block — flat-bar hatch, no plate connections
    for sx, is_t1 in stud_positions:
        cx = ox + sx
        if is_t1:
            placed = _assets.add_n2n_stud(msp, cx, oy + tp, stud_height=sh,
                                           layer=_L_STUD)
        else:
            placed = _assets.add_type_b_stud(msp, cx, oy + tp, stud_height=sh,
                                              layer=_L_STUD)
        if not placed:
            sr = STUD_RADIUS
            _poly(msp, [(cx - sr, oy + tp),  (cx + sr, oy + tp),
                        (cx + sr, oy + H - tp), (cx - sr, oy + H - tp)],
                  closed=True, layer=_L_STUD)

    # Flat-bar X-brace
    # Endpoints at plate CENTRES (matching reference sp01-elevation)
    xl   = ox + FLATBAR_H_TRIM / 2
    xr   = ox + L - FLATBAR_H_TRIM / 2
    y_bc = oy + tp / 2           # centre of bottom plate
    y_tc = oy + H - tp / 2       # centre of top plate
    _line(msp, (xl, y_bc), (xr, y_tc), _L_FLATBAR)
    _line(msp, (xl, y_tc), (xr, y_bc), _L_FLATBAR)

    # Callout markers at all 4 X-brace corners (BFGGBN or manual)
    for cx_fb, cy_fb in [(xl, y_bc), (xr, y_bc), (xl, y_tc), (xr, y_tc)]:
        _callout_marker(msp, cx_fb, cy_fb)

    # ── Top dimension chain: stud spacings + overall width ────────────────────
    studs = [sx for sx, _ in stud_positions]
    y_d1 = oy + H + _DIM_OFF_1
    y_d2 = oy + H + _DIM_OFF_2
    for a, b in zip(studs, studs[1:]):
        _hdim(msp, ox + a, ox + b, oy + H, y_d1)
    _hdim(msp, ox, ox + L, oy + H, y_d2)

    # ── Left dimension chain: plate / stud / overall heights ──────────────────
    x_d1 = ox - _DIM_OFF_1
    x_d2 = ox - _DIM_OFF_2
    _vdim(msp, oy,          oy + tp,     ox, x_d1)   # bottom plate
    _vdim(msp, oy + tp,     oy + H - tp, ox, x_d1)   # stud clear
    _vdim(msp, oy + H - tp, oy + H,      ox, x_d1)   # top plate
    _vdim(msp, oy,          oy + H,      ox, x_d2)   # overall


# ─────────────────────────────────────────────────────────────────────────────
# 2.  Flat-bar plan callout
# ─────────────────────────────────────────────────────────────────────────────

def _draw_flatbar_callout(msp, L, ox, oy, stud_positions, cladding="single"):
    """Plan-view cross-section showing panel body, cement plaster, and studs.

    Draws the full panel cross-section:
      - AR-Panels rectangle  : bamboo frame body, _PANEL_DEPTH (100 mm) deep
      - 0-S1 rectangle(s)   : cement plaster strip, _PLASTER_T (25 mm) thick
      - A-Hatch ANSI32 fills : one per plaster strip
      single → one plaster strip (back face only)
      double → two plaster strips (front and back faces)
    """
    pd     = _PANEL_DEPTH
    pt     = _PLASTER_T
    double = (cladding == "double")

    # ── Panel body Y extents (front plaster is below when double-sided) ───────
    y_panel_lo = oy + (pt if double else 0)
    y_panel_hi = y_panel_lo + pd
    stud_cy    = (y_panel_lo + y_panel_hi) / 2

    # Panel body rectangle (AR-Panels)
    _poly(msp, [(ox, y_panel_lo), (ox + L, y_panel_lo),
                (ox + L, y_panel_hi), (ox, y_panel_hi)],
          closed=True, layer=_L_PANELS)

    # Flat-bar at front face of panel body
    fb_y = y_panel_lo
    _poly(msp, [(ox + FLATBAR_H_TRIM / 2, fb_y),
                (ox + L - FLATBAR_H_TRIM / 2, fb_y)],
          closed=False, layer=_L_FLATBAR)

    # Stud circles — positions and types come from plan DXF
    for sx, is_t1 in stud_positions:
        cx = ox + sx
        block = "bps1" if is_t1 else "bpns1"
        placed = _assets.add_blockref(msp, block, cx, stud_cy, layer=_L_STUD)
        if not placed:
            _circle(msp, cx, stud_cy, STUD_RADIUS, _L_PANELS)

    # Back plaster strip (always present — exterior / back face)
    _poly(msp, [(ox, y_panel_hi), (ox + L, y_panel_hi),
                (ox + L, y_panel_hi + pt), (ox, y_panel_hi + pt)],
          closed=True, layer=_L_LEADER)
    _hatch_rect(msp, ox, y_panel_hi, L, pt, pattern="ANSI32", scale=5.0)

    # Front plaster strip (double-sided only — interior / front face)
    if double:
        _poly(msp, [(ox, oy), (ox + L, oy),
                    (ox + L, oy + pt), (ox, oy + pt)],
              closed=True, layer=_L_LEADER)
        _hatch_rect(msp, ox, oy, L, pt, pattern="ANSI32", scale=5.0)

    # Stud-spacing dimensions (above the cross-section)
    y_top    = y_panel_hi + pt
    stud_xs  = [sx for sx, _ in stud_positions]
    y_d1     = y_top + _DIM_OFF_1
    y_d2     = y_top + _DIM_OFF_2
    for a, b in zip(stud_xs, stud_xs[1:]):
        _hdim(msp, ox + a, ox + b, y_top, y_d1)
    _hdim(msp, ox, ox + L, y_top, y_d2)

    # Label + leader (below the section, pointing to flat-bar face)
    lbl_x, lbl_y = ox + L * 0.55, oy - 170
    _text(msp, "FLATBAR", lbl_x, lbl_y, layer=_L_SPEC)
    _leader(msp, [(ox + L * 0.75, fb_y),
                  (ox + L * 0.75, lbl_y + _TH),
                  (lbl_x - 10,   lbl_y + _TH)])


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Individual plate detail callout
# ─────────────────────────────────────────────────────────────────────────────

def _draw_plate_callout(msp, L, hole_block: str, hole_r: float, ox, oy,
                        plate_label, hole_label, show_inner_dim=False):
    """One plate connection-detail callout (top or bottom plate)."""
    # Outer viewport border
    _poly(msp, [(ox, oy), (ox + L, oy), (ox + L, oy + _BOX_H), (ox, oy + _BOX_H)],
          closed=True, layer=_L_VP)
    # Plate rectangle (88 mm, centred in the box)
    py0 = oy + _PLATE_MARGIN
    py1 = py0 + PLATE_WIDTH
    _poly(msp, [(ox, py0), (ox + L, py0), (ox + L, py1), (ox, py1)],
          closed=True, layer=_L_PLATE)

    # Connection holes at T1 positions — use asset block or manual circle
    cy = oy + _BOX_H / 2
    holes = _t1_x(L)
    for hx in holes:
        target_x = ox + hx
        placed = _assets.add_blockref(msp, hole_block, target_x, cy,
                                      layer=_L_PANELS)
        if not placed:
            _solid_circle(msp, target_x, cy, hole_r, _L_PANELS)

    # Dimensions
    if show_inner_dim and len(holes) >= 2:
        _hdim(msp, ox + holes[0], ox + holes[-1],
              oy + _BOX_H, oy + _BOX_H + _DIM_OFF_1)
        _hdim(msp, ox, ox + L, oy + _BOX_H, oy + _BOX_H + _DIM_OFF_2)
    else:
        _hdim(msp, ox, ox + L, oy + _BOX_H, oy + _BOX_H + _DIM_OFF_1)

    # Labels
    _text(msp, plate_label, ox + 40, oy + _BOX_H + 30, layer=_L_TEXT)
    ann_x = ox + L + 120
    ann_y = oy + _BOX_H * 0.55
    _text(msp, hole_label, ann_x, ann_y, layer=_L_SPEC)
    _leader(msp, [(ox + L - STUD_RADIUS, cy),
                  (ox + L + 60, ann_y + 40),
                  (ann_x - 10,  ann_y + 40)])


# ─────────────────────────────────────────────────────────────────────────────
# Backwards-compat shim
# ─────────────────────────────────────────────────────────────────────────────

def ensure_layers(doc) -> None:
    """No-op: all layers are registered by setup_layers() in src/layers.py."""


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def draw_details(msp: Modelspace,
                 wall_length:     float,
                 t1_count:        int,
                 t2_count:        int,
                 origin_x:        float = 0.0,
                 origin_y:        float = 0.0,
                 wall_height:     float = WALL_HEIGHT_TOTAL,
                 stud_positions=None,
                 cladding:        str   = "single") -> None:
    """
    Draw the elevation view and three detail callouts, stacked vertically above
    the cutting-list table.  Call this AFTER write_cutting_table().

    stud_positions: list of (relative_x, is_t1) from parse_wall_plan(), giving
                    actual stud X coordinates from the plan DXF.  When None or
                    empty, positions are computed from t1_count / t2_count with
                    even spacing as a fallback.
    cladding: "single" → one cement plaster strip in plan view
              "double" → two cement plaster strips (both faces)

    Imports CBFT standard blocks from Assets Description.dxf when available.
    """
    L  = wall_length
    ox = origin_x + _panel_left(L)

    # Build stud position list — use plan-extracted positions when available,
    # fall back to even-spacing when the parser couldn't extract them.
    if stud_positions:
        sp = stud_positions
    else:
        xs     = _stud_x_all(L, t1_count, t2_count)
        t1_set = {xs[0], xs[-1]} if len(xs) >= 2 else set(xs)
        sp     = [(x, x in t1_set) for x in xs]

    # Import asset blocks into the document (no-op if already imported or
    # if assets file not present)
    _assets.import_blocks(msp.doc)

    # 1. Elevation
    elev_oy = origin_y + TITLE_TOP_Y + _GAP_TITLE_ELEV
    _draw_elevation(msp, L, ox, elev_oy, sp, wall_height)

    # 2. Flat-bar plan callout
    y_fb = elev_oy + wall_height + _DIM_OFF_2 + _GAP_ELEV_FB
    _draw_flatbar_callout(msp, L, ox, y_fb, sp, cladding=cladding)

    # 3. Bottom-plate detail (dowel holes)
    y_bp = y_fb + _DIM_OFF_2 + _GAP_FB_BP
    _draw_plate_callout(msp, L, "Dowel Hole", 16.0, ox, y_bp,
                        "BOT. PLATE", "DOWEL HOLE")

    # 4. Top-plate detail (J-bolt holes)
    y_tp = y_bp + _BOX_H + _DIM_OFF_1 + _GAP_BP_TP
    _draw_plate_callout(msp, L, "J-Bolt Hole", 14.0, ox, y_tp,
                        "TOP PLATE", "J-BOLT HOLE", show_inner_dim=True)
