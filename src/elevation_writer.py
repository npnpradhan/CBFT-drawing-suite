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
from .layers import setup_layers as _setup_layers

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
    # Endpoints at plate CENTRES, 25 mm inside each panel edge (outside half of end studs)
    xl   = ox + FLATBAR_H_TRIM / 2
    xr   = ox + L - FLATBAR_H_TRIM / 2
    y_bc = oy + tp / 2           # centre of bottom plate
    y_tc = oy + H - tp / 2       # centre of top plate
    # Thin centreline (construction geometry)
    _line(msp, (xl, y_bc), (xr, y_tc), _L_FLATBAR)
    _line(msp, (xl, y_tc), (xr, y_bc), _L_FLATBAR)
    # Thick polyline — 25 mm wide, represents physical flat bar (matches DP01-Elev)
    msp.add_lwpolyline([(xl, y_bc), (xr, y_tc)],
                       dxfattribs={"layer": _L_FLATBAR, "const_width": 25.0})
    msp.add_lwpolyline([(xl, y_tc), (xr, y_bc)],
                       dxfattribs={"layer": _L_FLATBAR, "const_width": 25.0})

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

def _draw_flatbar_callout(msp, L, ox, oy, stud_positions, cladding="single",
                          plaster_break=None):
    """Plan-view cross-section showing panel body, cement plaster, and studs.

    Draws the full panel cross-section:
      - AR-Panels rectangle  : bamboo frame body, _PANEL_DEPTH (100 mm) deep
      - 0-S1 rectangle(s)   : cement plaster strip, _PLASTER_T (25 mm) thick
      - A-Hatch ANSI32 fills : one per plaster strip
      single → one plaster strip on the flat-bar face
      double → two plaster strips (flat-bar face + opposite face)

    plaster_break: optional (break_left_x, break_right_x) in absolute coords.
                   When provided the plaster strip is split into two segments
                   (left and right of the door opening), as in the reference drawing.
    """
    pd     = _PANEL_DEPTH
    pt     = _PLASTER_T
    double = (cladding == "double")

    # Front plaster strip always occupies [oy, oy+pt] — same face as flat bar.
    # Panel body sits above it.  Back plaster is added on top for double only.
    y_panel_lo = oy + pt
    y_panel_hi = y_panel_lo + pd
    stud_cy    = (y_panel_lo + y_panel_hi) / 2

    # Panel body rectangle (AR-Panels)
    _poly(msp, [(ox, y_panel_lo), (ox + L, y_panel_lo),
                (ox + L, y_panel_hi), (ox, y_panel_hi)],
          closed=True, layer=_L_PANELS)

    # Flat-bar at front face of panel body (top of front plaster)
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

    # Helper — draw one plaster segment (rect + hatch) with optional gap
    def _plaster_seg(x0, x1, y0, h):
        w = x1 - x0
        if w < 1.0:
            return
        _poly(msp, [(x0, y0), (x1, y0), (x1, y0 + h), (x0, y0 + h)],
              closed=True, layer=_L_LEADER)
        _hatch_rect(msp, x0, y0, w, h, pattern="ANSI32", scale=5.0)

    # Front plaster strip (always — same side as flat bar); breaks at door opening
    if plaster_break is None:
        _plaster_seg(ox, ox + L, oy, pt)
    else:
        bl, br = plaster_break
        tp_jamb = PLATE_THICKNESS       # jamb timber width = 38 mm
        # jamb extents derived from stud inner faces (bl, br)
        jamb_lx0 = bl                   # left stud inner face = left jamb outer x
        jamb_lx1 = bl + tp_jamb         # left jamb inner x (start of clear opening)
        jamb_rx1 = br                   # right stud inner face = right jamb inner x
        jamb_rx0 = br - tp_jamb         # right jamb outer x (end of clear opening)
        clear_w  = jamb_rx0 - jamb_lx1  # clear opening width

        _plaster_seg(ox,   jamb_lx0,  oy, pt)   # left of opening
        _plaster_seg(jamb_rx1, ox + L, oy, pt)  # right of opening

        # ── Door jambs in plan (hatched rectangles at each side of opening) ────
        _poly(msp, [(jamb_lx0, y_panel_lo), (jamb_lx1, y_panel_lo),
                    (jamb_lx1, y_panel_hi), (jamb_lx0, y_panel_hi)],
              closed=True, layer=_L_PLATE)
        _hatch_rect(msp, jamb_lx0, y_panel_lo, tp_jamb, pd)

        _poly(msp, [(jamb_rx0, y_panel_lo), (jamb_rx1, y_panel_lo),
                    (jamb_rx1, y_panel_hi), (jamb_rx0, y_panel_hi)],
              closed=True, layer=_L_PLATE)
        _hatch_rect(msp, jamb_rx0, y_panel_lo, tp_jamb, pd)

        # ── Door swing symbol above the panel body (flush with back face) ───────
        # Hinge at inner face of left jamb, flush with top/back face of panel.
        # Door swings outward (+Y direction, above the wall in plan view). Red.
        _DOOR_LEAF_T = 50
        _door_attr = {"layer": _L_ELEV, "color": 1}  # color 1 = red
        hx, hy = jamb_lx1, y_panel_hi

        # Closed position: horizontal line across the clear opening
        msp.add_line((hx, hy), (hx + clear_w, hy), dxfattribs=_door_attr)

        # Open position: door leaf rectangle pointing upward (+Y)
        msp.add_lwpolyline(
            [(hx, hy), (hx + _DOOR_LEAF_T, hy),
             (hx + _DOOR_LEAF_T, hy + clear_w), (hx, hy + clear_w)],
            close=True, dxfattribs=_door_attr)

        # Arc: swing path of door tip — CCW from 0° (closed, +X) to 90° (open, +Y)
        msp.add_arc((hx, hy), clear_w, 0, 90, dxfattribs=_door_attr)

    # Back plaster strip (double-sided only — opposite face)
    if double:
        if plaster_break is None:
            _plaster_seg(ox, ox + L, y_panel_hi, pt)
        else:
            # bl / br already set above when plaster_break is not None
            _plaster_seg(ox,        jamb_lx0,  y_panel_hi, pt)
            _plaster_seg(jamb_rx1,  ox + L,    y_panel_hi, pt)

    # Stud-spacing dimensions (above the cross-section)
    y_top   = y_panel_hi + (pt if double else 0)
    stud_xs = [sx for sx, _ in stud_positions]
    y_d1    = y_top + _DIM_OFF_1
    y_d2    = y_top + _DIM_OFF_2
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
# 5.  Door / window elevation helpers
# ─────────────────────────────────────────────────────────────────────────────

def _door_stud_positions(L: float, opening_width: float,
                         t1_count: int, t2_count: int) -> list:
    """
    Build the (relative_x, is_t1) stud list for a door panel.

    Assumes the door opening is at the LEFT edge of the panel:
      - T1 at x = STUD_RADIUS  (left-end stud, also door-left framing)
      - T1 at x = STUD_RADIUS + opening_width  (door-right framing)
      - Additional T1 / T2 studs evenly distributed in the solid section
      - T1 at x = L - STUD_RADIUS  (right-end stud)
    """
    n_total = t1_count + t2_count
    left_x     = STUD_RADIUS
    door_rgt_x = STUD_RADIUS + opening_width
    right_x    = L - STUD_RADIUS

    if n_total <= 2:
        # All-door panel — just end studs; door-right = right-end
        return [(left_x, True), (right_x, True)]

    # Solid section: studs between door-right T1 and right-end T1
    solid_w       = right_x - door_rgt_x
    n_interior    = n_total - 3          # studs between door-right and right-end
    n_interior    = max(0, n_interior)
    n_interior_t1 = max(0, t1_count - 3) # how many of those are T1

    interior_xs = []
    if n_interior > 0:
        step = solid_w / (n_interior + 1)
        interior_xs = [door_rgt_x + step * i for i in range(1, n_interior + 1)]

    sp  = [(left_x, True), (door_rgt_x, True)]
    sp += [(x, i < n_interior_t1) for i, x in enumerate(interior_xs)]
    sp += [(right_x, True)]
    return sp


def _draw_door_elevation(msp, L: float, ox: float, oy: float,
                         opening_width: float,
                         opening_height: float,
                         t1_count: int = 2,
                         t2_count: int = 0,
                         wall_height: float = WALL_HEIGHT_TOTAL) -> list:
    """
    Door panel elevation.

    Draws:
      - top / bottom timber plates (hatched)
      - all bamboo studs at full height (T1 via N2N block, T2 via Type-B)
      - door opening from bottom plate to head jamb
      - door head jamb (timber) at the correct height
      - short bamboo stud above the head jamb (centred between door T1 studs)
      - flat-bar X-brace on the solid section only
      - horizontal + vertical dimension chains

    Returns the stud_positions list (for re-use in plan callout).
    """
    H  = wall_height
    tp = PLATE_THICKNESS
    sh = H - 2 * tp   # full bamboo stud height

    # ── Panel outline ─────────────────────────────────────────────────────────
    _poly(msp, [(ox, oy), (ox+L, oy), (ox+L, oy+H), (ox, oy+H)],
          closed=True, layer=_L_ELEV)

    # ── Timber plates ─────────────────────────────────────────────────────────
    _poly(msp, [(ox, oy),      (ox+L, oy),      (ox+L, oy+tp),   (ox, oy+tp)],
          closed=True, layer=_L_PLATE)
    _hatch_rect(msp, ox, oy, L, tp)
    _poly(msp, [(ox, oy+H-tp), (ox+L, oy+H-tp), (ox+L, oy+H),    (ox, oy+H)],
          closed=True, layer=_L_PLATE)
    _hatch_rect(msp, ox, oy+H-tp, L, tp)

    # ── Stud positions ────────────────────────────────────────────────────────
    stud_positions = _door_stud_positions(L, opening_width, t1_count, t2_count)

    # Door-left and door-right framing T1 centres (in panel-relative coords)
    door_left_x  = stud_positions[0][0]       # STUD_RADIUS
    door_right_x = stud_positions[1][0]       # STUD_RADIUS + opening_width

    # ── Draw all bamboo studs at full height ──────────────────────────────────
    for sx, is_t1 in stud_positions:
        cx = ox + sx
        if is_t1:
            placed = _assets.add_n2n_stud(msp, cx, oy+tp, stud_height=sh,
                                          layer=_L_STUD)
        else:
            placed = _assets.add_type_b_stud(msp, cx, oy+tp, stud_height=sh,
                                             layer=_L_STUD)
        if not placed:
            sr = STUD_RADIUS
            _poly(msp, [(cx-sr, oy+tp), (cx+sr, oy+tp),
                        (cx+sr, oy+H-tp), (cx-sr, oy+H-tp)],
                  closed=True, layer=_L_STUD)

    # ── Door opening geometry ─────────────────────────────────────────────────
    # Stud inner faces — door jamb timbers sit here, adjacent to studs
    jamb_lx0  = ox + door_left_x  + STUD_RADIUS   # left stud inner face
    jamb_rx1  = ox + door_right_x - STUD_RADIUS   # right stud inner face
    jamb_lx1  = jamb_lx0 + tp                     # right edge of left jamb
    jamb_rx0  = jamb_rx1 - tp                     # left edge of right jamb

    op_y0   = oy + tp                    # bottom of opening (top of bot plate)
    head_y0 = op_y0 + opening_height     # bottom of door head jamb
    head_y1 = head_y0 + tp               # top of door head jamb

    # Left door jamb timber (hatched)
    _poly(msp, [(jamb_lx0, op_y0), (jamb_lx1, op_y0),
                (jamb_lx1, head_y0), (jamb_lx0, head_y0)],
          closed=True, layer=_L_PLATE)
    _hatch_rect(msp, jamb_lx0, op_y0, tp, opening_height)

    # Right door jamb timber (hatched)
    _poly(msp, [(jamb_rx0, op_y0), (jamb_rx1, op_y0),
                (jamb_rx1, head_y0), (jamb_rx0, head_y0)],
          closed=True, layer=_L_PLATE)
    _hatch_rect(msp, jamb_rx0, op_y0, tp, opening_height)

    # Clear opening rectangle (void between the two jambs)
    _poly(msp, [(jamb_lx1, op_y0), (jamb_rx0, op_y0),
                (jamb_rx0, head_y0), (jamb_lx1, head_y0)],
          closed=True, layer=_L_ELEV)

    # Door head jamb — spans stud-centre to stud-centre (= opening_width)
    head_x0 = ox + door_left_x    # left framing stud centre
    head_x1 = ox + door_right_x   # right framing stud centre
    head_w  = head_x1 - head_x0   # = opening_width
    _poly(msp, [(head_x0, head_y0), (head_x1, head_y0),
                (head_x1, head_y1), (head_x0, head_y1)],
          closed=True, layer=_L_PLATE)
    _hatch_rect(msp, head_x0, head_y0, head_w, tp)

    # Short bamboo stud above head jamb — T2 type, drawn directly
    # (block ref would compress too many nodes; use explicit lines at 500 mm pitch)
    short_cx     = ox + (door_left_x + door_right_x) / 2
    short_height = H - tp - opening_height - tp
    if short_height > 0:
        sr   = STUD_RADIUS
        x_l, x_r = short_cx - sr, short_cx + sr
        y_b, y_t = head_y1, head_y1 + short_height
        _poly(msp, [(x_l, y_b), (x_r, y_b), (x_r, y_t), (x_l, y_t)],
              closed=True, layer="0-S2")
        n_nodes = max(1, int(short_height / 500))
        for i in range(1, n_nodes + 1):
            y_node = y_b + i * short_height / (n_nodes + 1)
            _line(msp, (x_l, y_node),      (x_r, y_node),      "0-S1")
            _line(msp, (x_l, y_node + 10), (x_r, y_node + 10), "0-S1")

    # ── Flat-bar X-brace — solid section only ────────────────────────────────
    right_end_x = stud_positions[-1][0]
    solid_ox = ox + door_right_x
    solid_L  = right_end_x - door_right_x
    if solid_L > FLATBAR_H_TRIM:
        # Extend 25 mm OUTSIDE each stud centre (outside/front half), matching reference
        xl   = solid_ox - FLATBAR_H_TRIM / 2
        xr   = solid_ox + solid_L + FLATBAR_H_TRIM / 2
        y_bc = oy + tp / 2
        y_tc = oy + H - tp / 2
        # Thin centreline
        _line(msp, (xl, y_bc), (xr, y_tc), _L_FLATBAR)
        _line(msp, (xl, y_tc), (xr, y_bc), _L_FLATBAR)
        # Thick polyline — 25 mm wide, matches DP01-Elev reference
        msp.add_lwpolyline([(xl, y_bc), (xr, y_tc)],
                           dxfattribs={"layer": _L_FLATBAR, "const_width": 25.0})
        msp.add_lwpolyline([(xl, y_tc), (xr, y_bc)],
                           dxfattribs={"layer": _L_FLATBAR, "const_width": 25.0})
        for cx_fb, cy_fb in [(xl, y_bc), (xr, y_bc), (xl, y_tc), (xr, y_tc)]:
            _callout_marker(msp, cx_fb, cy_fb)

    # ── Dimension chains ──────────────────────────────────────────────────────
    stud_xs = [sx for sx, _ in stud_positions]
    y_d1 = oy + H + _DIM_OFF_1
    y_d2 = oy + H + _DIM_OFF_2
    for a, b in zip(stud_xs, stud_xs[1:]):
        _hdim(msp, ox+a, ox+b, oy+H, y_d1)
    _hdim(msp, ox, ox+L, oy+H, y_d2)

    x_d1 = ox - _DIM_OFF_1
    x_d2 = ox - _DIM_OFF_2
    _vdim(msp, oy,      oy+tp,    ox, x_d1)   # bottom plate
    _vdim(msp, oy+tp,   head_y0,  ox, x_d1)   # opening height
    _vdim(msp, head_y0, head_y1,  ox, x_d1)   # door head jamb
    _vdim(msp, head_y1, oy+H-tp,  ox, x_d1)   # short stud zone
    _vdim(msp, oy+H-tp, oy+H,     ox, x_d1)   # top plate
    _vdim(msp, oy,      oy+H,     ox, x_d2)   # overall

    return stud_positions


def _draw_window_elevation(msp, L: float, ox: float, oy: float,
                           opening_width: float, opening_height: float,
                           wall_height: float = WALL_HEIGHT_TOTAL) -> None:
    """Window panel elevation: plates, end T1 studs, framed opening, head + sill."""
    H  = wall_height
    tp = PLATE_THICKNESS

    # Panel outline
    _poly(msp, [(ox, oy), (ox+L, oy), (ox+L, oy+H), (ox, oy+H)],
          closed=True, layer=_L_ELEV)

    # Bottom + top plates
    _poly(msp, [(ox, oy), (ox+L, oy), (ox+L, oy+tp), (ox, oy+tp)],
          closed=True, layer=_L_PLATE)
    _hatch_rect(msp, ox, oy, L, tp)
    _poly(msp, [(ox, oy+H-tp), (ox+L, oy+H-tp), (ox+L, oy+H), (ox, oy+H)],
          closed=True, layer=_L_PLATE)
    _hatch_rect(msp, ox, oy+H-tp, L, tp)

    # T1 bamboo studs at each end (full stud zone — windows don't interrupt ends)
    sh = H - 2 * tp
    for sx in [STUD_RADIUS, L - STUD_RADIUS]:
        placed = _assets.add_n2n_stud(msp, ox+sx, oy+tp, stud_height=sh,
                                       layer=_L_STUD)
        if not placed:
            sr = STUD_RADIUS
            _poly(msp, [(ox+sx-sr, oy+tp), (ox+sx+sr, oy+tp),
                        (ox+sx+sr, oy+H-tp), (ox+sx-sr, oy+H-tp)],
                  closed=True, layer=_L_STUD)

    # Window opening: centred both horizontally and vertically in the stud zone
    op_x0 = ox + (L - opening_width) / 2
    op_x1 = op_x0 + opening_width
    stud_zone = H - 2 * tp
    sill_offset = (stud_zone - opening_height - 2 * tp) / 2   # space for head+sill
    sill_y0 = oy + tp + sill_offset           # bottom of sill timber
    sill_y1 = sill_y0 + tp                    # top of sill / bottom of opening
    head_y0 = sill_y1 + opening_height        # bottom of head timber
    head_y1 = head_y0 + tp                    # top of head

    # Sill timber
    _poly(msp, [(op_x0, sill_y0), (op_x1, sill_y0),
                (op_x1, sill_y1), (op_x0, sill_y1)],
          closed=True, layer=_L_PLATE)
    _hatch_rect(msp, op_x0, sill_y0, opening_width, tp)

    # Head timber
    _poly(msp, [(op_x0, head_y0), (op_x1, head_y0),
                (op_x1, head_y1), (op_x0, head_y1)],
          closed=True, layer=_L_PLATE)
    _hatch_rect(msp, op_x0, head_y0, opening_width, tp)

    # Opening outline
    _poly(msp, [(op_x0, sill_y1), (op_x1, sill_y1),
                (op_x1, head_y0), (op_x0, head_y0)],
          closed=True, layer=_L_ELEV)

    # Dimensions — top
    y_d1 = oy + H + _DIM_OFF_1
    y_d2 = oy + H + _DIM_OFF_2
    _hdim(msp, op_x0, op_x1, oy+H, y_d1)
    _hdim(msp, ox,    ox+L,   oy+H, y_d2)

    # Dimensions — left
    x_d1 = ox - _DIM_OFF_1
    x_d2 = ox - _DIM_OFF_2
    _vdim(msp, oy,       oy+tp,   ox, x_d1)       # bot plate
    _vdim(msp, oy+tp,    sill_y0, ox, x_d1)       # below window
    _vdim(msp, sill_y0,  sill_y1, ox, x_d1)       # sill timber
    _vdim(msp, sill_y1,  head_y0, ox, x_d1)       # clear opening height
    _vdim(msp, head_y0,  head_y1, ox, x_d1)       # head timber
    _vdim(msp, head_y1,  oy+H-tp, ox, x_d1)       # above window
    _vdim(msp, oy+H-tp,  oy+H,    ox, x_d1)       # top plate
    _vdim(msp, oy,       oy+H,    ox, x_d2)        # overall


# ─────────────────────────────────────────────────────────────────────────────
# DP01-Plan block import helper
# ─────────────────────────────────────────────────────────────────────────────

def _insert_door_plan_block(msp, source_dxf_path: str,
                            ox: float, oy: float) -> None:
    """
    Import DP01-Plan block from *source_dxf_path* into the current drawing
    and insert it at (ox, oy).  Silently skips if the block is not found or
    if the import fails for any reason.
    """
    try:
        import ezdxf as _ezdxf
        from ezdxf.addons.importer import Importer as _DXFImporter
        src = _ezdxf.readfile(source_dxf_path)
        if 'DP01-Plan' not in src.blocks:
            return
        imp = _DXFImporter(src, msp.doc)
        imp.import_blocks(['DP01-Plan'])
        msp.add_blockref('DP01-Plan', (ox, oy),
                         dxfattribs={'layer': _L_PANELS})
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Public door / window entry points
# ─────────────────────────────────────────────────────────────────────────────

def draw_door_details(msp: Modelspace,
                      panel_width:    float,
                      opening_width:  float,
                      opening_height: float,
                      t1_count:       int   = 2,
                      t2_count:       int   = 0,
                      origin_x:       float = 0.0,
                      origin_y:       float = 0.0,
                      wall_height:    float = WALL_HEIGHT_TOTAL,
                      cladding:       str   = "single",
                      source_dxf:     str   = None) -> None:
    """
    Draw door-panel detail drawings stacked above the cutting-list table.
    Produces: door elevation, flat-bar plan callout, bot-plate detail,
    top-plate detail.

    source_dxf: path to the source DXF; when provided, the DP01-Plan block
                is imported and inserted below the flat-bar callout.
    """
    L  = panel_width
    ox = origin_x + _panel_left(L)

    _assets.import_blocks(msp.doc)
    _setup_layers(msp.doc)

    elev_oy = origin_y + TITLE_TOP_Y + _GAP_TITLE_ELEV
    sp = _draw_door_elevation(msp, L, ox, elev_oy, opening_width,
                              opening_height, t1_count, t2_count, wall_height)

    # Cement plaster breaks at the door opening (stud inner faces)
    door_left_x  = sp[0][0]   # = STUD_RADIUS
    door_right_x = sp[1][0]   # = STUD_RADIUS + opening_width
    plaster_break = (
        ox + door_left_x  + STUD_RADIUS,   # left stud inner face
        ox + door_right_x - STUD_RADIUS,   # right stud inner face
    )

    y_fb = elev_oy + wall_height + _DIM_OFF_2 + _GAP_ELEV_FB
    _draw_flatbar_callout(msp, L, ox, y_fb, sp, cladding=cladding,
                          plaster_break=plaster_break)

    y_bp = y_fb + _DIM_OFF_2 + _GAP_FB_BP
    _draw_plate_callout(msp, L, "Dowel Hole", 16.0, ox, y_bp,
                        "BOT. PLATE", "DOWEL HOLE")

    y_tp = y_bp + _BOX_H + _DIM_OFF_1 + _GAP_BP_TP
    _draw_plate_callout(msp, L, "J-Bolt Hole", 14.0, ox, y_tp,
                        "TOP PLATE", "J-BOLT HOLE", show_inner_dim=True)

    # Door plan view from source DXF block DP01-Plan
    if source_dxf:
        y_plan = y_tp + _BOX_H + _DIM_OFF_2 + _GAP_BP_TP
        _insert_door_plan_block(msp, source_dxf, ox, y_plan)


def draw_window_details(msp: Modelspace,
                        panel_width:    float,
                        opening_width:  float,
                        opening_height: float,
                        origin_x:       float = 0.0,
                        origin_y:       float = 0.0,
                        wall_height:    float = WALL_HEIGHT_TOTAL,
                        cladding:       str   = "single") -> None:
    """
    Draw window-panel detail drawings stacked above the cutting-list table.
    Produces: window elevation, flat-bar plan callout, bot-plate detail,
    top-plate detail.
    """
    L  = panel_width
    ox = origin_x + _panel_left(L)
    sp = [(STUD_RADIUS, True), (L - STUD_RADIUS, True)]

    _assets.import_blocks(msp.doc)
    _setup_layers(msp.doc)

    elev_oy = origin_y + TITLE_TOP_Y + _GAP_TITLE_ELEV
    _draw_window_elevation(msp, L, ox, elev_oy, opening_width, opening_height, wall_height)

    y_fb = elev_oy + wall_height + _DIM_OFF_2 + _GAP_ELEV_FB
    _draw_flatbar_callout(msp, L, ox, y_fb, sp, cladding=cladding)

    y_bp = y_fb + _DIM_OFF_2 + _GAP_FB_BP
    _draw_plate_callout(msp, L, "Dowel Hole", 16.0, ox, y_bp,
                        "BOT. PLATE", "DOWEL HOLE")

    y_tp = y_bp + _BOX_H + _DIM_OFF_1 + _GAP_BP_TP
    _draw_plate_callout(msp, L, "J-Bolt Hole", 14.0, ox, y_tp,
                        "TOP PLATE", "J-BOLT HOLE", show_inner_dim=True)


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
    _setup_layers(msp.doc)

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
