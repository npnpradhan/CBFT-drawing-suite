"""
CBFT Floor Plan Generator
Draws walls, doors, windows, bamboo poles, grid, dimensions, and room labels.
"""
import math
from typing import List, Tuple, Dict, Any

import ezdxf
from ezdxf.layouts import Modelspace

from .constants import (
    WALL_THICKNESS, BAMBOO_POLE_R, GRID_BUBBLE_R, GRID_BUBBLE_OFFSET,
    GRID_LINE_EXTEND, DIM_OFFSET, DIM_GAP, TEXT_HEIGHT,
    L_WALL, L_DOOR, L_WINDOW, L_BAMBOO, L_GRID, L_GRIDLN,
    L_DIM, L_TEXT, L_HIDDEN, L_CENTER, L_DEFPTS, L_ANNOTEXT2
)
from .geometry import (
    add, sub, scale, normalize, dist, length, perp_left, perp_right,
    angle_deg, along, midpoint, offset_point, wall_rect
)

Point = Tuple[float, float]


# ─── Grid helpers ────────────────────────────────────────────────────────────

def grid_origin(grid: Dict) -> Point:
    return (0.0, 0.0)


def grid_point(grid: Dict, col: int, row: int) -> Point:
    """World coordinate of grid intersection (col, row)."""
    x = sum(grid["x_spacings"][:col])
    y = sum(grid["y_spacings"][:row])
    return (float(x), float(y))


def grid_world(grid: Dict, gp: List) -> Point:
    """Convert [col, row] grid reference to world (x, y)."""
    return grid_point(grid, gp[0], gp[1])


def grid_size(grid: Dict) -> Tuple[float, float]:
    return (sum(grid["x_spacings"]), sum(grid["y_spacings"]))


# ─── Wall drawing ────────────────────────────────────────────────────────────

def _sorted_openings(openings: List[Dict], wall_from: List, wall_to: List) -> List[Dict]:
    """Return openings that belong to this wall, sorted by offset."""
    result = []
    for op in openings:
        wf = op.get("wall", [None, None])[0]
        wt = op.get("wall", [None, None])[1]
        if wf == wall_from and wt == wall_to:
            result.append(op)
    result.sort(key=lambda o: o["offset"])
    return result


def draw_wall(msp: Modelspace, start: Point, end: Point,
              openings: List[Dict], thickness: float = WALL_THICKNESS) -> List[Point]:
    """
    Draw one wall segment with gaps for openings.
    Returns list of bamboo-pole candidate points (corners of openings + wall ends).
    """
    L = dist(start, end)
    pole_candidates = [start, end]

    # Build gap list: (gap_start, gap_end)
    gaps = [(op["offset"], op["offset"] + op["width"]) for op in openings]
    gaps.sort()

    # Solid segments between gaps
    solid_segments = []
    cursor = 0.0
    for gs, ge in gaps:
        if gs > cursor:
            solid_segments.append((cursor, gs))
        cursor = ge
    if cursor < L:
        solid_segments.append((cursor, L))

    d = normalize(sub(end, start))
    nl = perp_left(d)

    for seg_s, seg_e in solid_segments:
        p0 = add(start, scale(d, seg_s))
        p1 = add(start, scale(d, seg_e))
        p2 = add(p1, scale(nl, thickness))
        p3 = add(p0, scale(nl, thickness))
        msp.add_lwpolyline([p0, p1, p2, p3], close=True,
                           dxfattribs={"layer": L_WALL})

    # Collect pole points at each opening jamb
    for gs, ge in gaps:
        for t in (gs, ge):
            pole_candidates.append(add(start, scale(d, t)))
            pole_candidates.append(add(add(start, scale(d, t)), scale(nl, thickness)))

    return pole_candidates


# ─── Door drawing ────────────────────────────────────────────────────────────

def draw_door(msp: Modelspace, start: Point, end: Point, opening: Dict,
              thickness: float = WALL_THICKNESS) -> None:
    """
    Draw door swing symbol in plan:
      - Door leaf line (from hinge, perpendicular to wall)
      - Quarter-circle swing arc (dashed)
      - Door designation tag
    """
    w = opening["width"]
    offset = opening["offset"]
    hinge_side = opening.get("hinge", "start")   # "start" or "end"
    swing = opening.get("swing", "in")            # "in" (left side of wall) or "out"
    tag = opening.get("tag", "D")

    d = normalize(sub(end, start))
    nl = perp_left(d)   # left of direction of travel = "inside" by convention

    # Hinge and free-jamb points on wall face (left face = inside face)
    p_start_jamb = add(start, scale(d, offset))
    p_end_jamb   = add(start, scale(d, offset + w))

    if hinge_side == "start":
        hinge = p_start_jamb
        free_jamb = p_end_jamb
    else:
        hinge = p_end_jamb
        free_jamb = p_start_jamb

    # Swing direction: "in" = into left-normal side, "out" = opposite
    swing_n = nl if swing == "in" else perp_right(d)

    # Door leaf endpoint (leaf perpendicular to wall, width W into room)
    leaf_end = add(hinge, scale(swing_n, w))

    # Door leaf line
    msp.add_line(hinge, leaf_end, dxfattribs={"layer": L_DOOR})

    # Swing arc from leaf_end back to free jamb (quarter-circle)
    # Arc center = hinge, radius = w
    ang_leaf = angle_deg(sub(leaf_end, hinge))
    ang_jamb = angle_deg(sub(free_jamb, hinge))

    # Determine arc direction: should sweep from jamb angle to leaf angle
    # going through 90° of rotation
    if swing == "in":
        start_a = ang_jamb
        end_a   = ang_leaf
        # Ensure arc goes CCW (positive direction) by adjusting if needed
        if end_a < start_a:
            end_a += 360
    else:
        start_a = ang_leaf
        end_a   = ang_jamb
        if end_a < start_a:
            end_a += 360

    msp.add_arc(hinge, w, start_a, end_a, dxfattribs={"layer": L_HIDDEN})

    # Door tag: placed at midpoint of opening, offset from wall
    tag_center = add(
        midpoint(p_start_jamb, p_end_jamb),
        scale(swing_n, thickness / 2 + GRID_BUBBLE_R * 0.8)
    )
    scale_f = 0.38  # matches reference drawing tag scale
    msp.add_blockref(
        "DOOR_TAG", tag_center,
        dxfattribs={"layer": L_DOOR, "xscale": scale_f, "yscale": scale_f},
    ).add_auto_attribs({"TAG": tag})


# ─── Window drawing ──────────────────────────────────────────────────────────

def draw_window(msp: Modelspace, start: Point, end: Point, opening: Dict,
                thickness: float = WALL_THICKNESS) -> None:
    """
    Draw window in plan as triple-line symbol (outer frame + glass lines).
    """
    w = opening["width"]
    offset = opening["offset"]
    tag = opening.get("tag", "W")

    d = normalize(sub(end, start))
    nl = perp_left(d)

    # Four corners of the opening rectangle
    left_in   = add(start, scale(d, offset))
    right_in  = add(start, scale(d, offset + w))
    left_out  = add(left_in,  scale(nl, thickness))
    right_out = add(right_in, scale(nl, thickness))

    # Outer frame rectangle
    msp.add_lwpolyline([left_in, right_in, right_out, left_out], close=True,
                       dxfattribs={"layer": L_WINDOW})

    # Two glass lines at 1/3 and 2/3 of thickness
    for frac in (1/3, 2/3):
        p_l = add(left_in,  scale(nl, thickness * frac))
        p_r = add(right_in, scale(nl, thickness * frac))
        msp.add_line(p_l, p_r, dxfattribs={"layer": L_WINDOW})

    # Jamb return lines at opening ends
    msp.add_line(left_in,  left_out,  dxfattribs={"layer": L_WINDOW})
    msp.add_line(right_in, right_out, dxfattribs={"layer": L_WINDOW})

    # Window tag: offset outside the wall (on exterior face)
    tag_mid = add(
        midpoint(left_out, right_out),
        scale(nl, GRID_BUBBLE_R * 0.8)
    )
    scale_f = 0.38
    msp.add_blockref(
        "WINDOW_TAG", tag_mid,
        dxfattribs={"layer": L_WINDOW, "xscale": scale_f, "yscale": scale_f},
    ).add_auto_attribs({"TAG": tag})


# ─── Bamboo poles ────────────────────────────────────────────────────────────

def place_bamboo_poles(msp: Modelspace, grid: Dict) -> None:
    """Place bamboo pole markers at every grid intersection."""
    cols = len(grid["columns"])
    rows = len(grid["rows"])
    for ci in range(cols):
        for ri in range(rows):
            pt = grid_point(grid, ci, ri)
            msp.add_blockref("BAMBOO_POLE", pt, dxfattribs={"layer": L_BAMBOO})


# ─── Grid ────────────────────────────────────────────────────────────────────

def draw_grid(msp: Modelspace, grid: Dict) -> None:
    """Draw structural grid: dashed lines + bubble circles with labels."""
    cols = len(grid["columns"])
    rows = len(grid["rows"])
    W, H = grid_size(grid)
    off = GRID_BUBBLE_OFFSET
    ext = GRID_LINE_EXTEND

    # Vertical grid lines (constant x, labelled with column letters)
    for ci, label in enumerate(grid["columns"]):
        x = sum(grid["x_spacings"][:ci])
        y_bot = -off - ext
        y_top = H + off + ext
        msp.add_line((x, y_bot), (x, y_top), dxfattribs={"layer": L_GRIDLN})

        # Bubble at bottom
        bc = (x, -off)
        msp.add_blockref("GRID_BUBBLE", bc, dxfattribs={"layer": L_GRID}).add_auto_attribs({"LABEL": label})
        # Bubble at top
        tc = (x, H + off)
        msp.add_blockref("GRID_BUBBLE", tc, dxfattribs={"layer": L_GRID}).add_auto_attribs({"LABEL": label})

    # Horizontal grid lines (constant y, labelled with row numbers)
    for ri, label in enumerate(grid["rows"]):
        y = sum(grid["y_spacings"][:ri])
        x_left  = -off - ext
        x_right = W + off + ext
        msp.add_line((x_left, y), (x_right, y), dxfattribs={"layer": L_GRIDLN})

        # Bubble at left
        lc = (-off, y)
        msp.add_blockref("GRID_BUBBLE", lc, dxfattribs={"layer": L_GRID}).add_auto_attribs({"LABEL": label})
        # Bubble at right
        rc = (W + off, y)
        msp.add_blockref("GRID_BUBBLE", rc, dxfattribs={"layer": L_GRID}).add_auto_attribs({"LABEL": label})


# ─── Dimensions ──────────────────────────────────────────────────────────────

def _ensure_dimstyle(doc) -> str:
    style_name = "CBFT_DIM"
    if style_name not in doc.dimstyles:
        ds = doc.dimstyles.new(style_name)
        ds.dxf.dimtxt  = 200   # text height mm
        ds.dxf.dimasz  = 150   # arrow size mm
        ds.dxf.dimexo  = 100   # extension line offset
        ds.dxf.dimexe  = 150   # extension line extension
        ds.dxf.dimgap  = 100   # text gap
        ds.dxf.dimdli  = 0     # dimension line increment
    return style_name


def draw_dimensions(msp: Modelspace, doc, grid: Dict) -> None:
    """Auto-dimension all grid bays on all four sides."""
    style = _ensure_dimstyle(doc)
    cols = len(grid["columns"])
    rows = len(grid["rows"])
    W, H = grid_size(grid)
    off = GRID_BUBBLE_OFFSET + GRID_BUBBLE_R

    # Bottom: dimension each x-bay, then overall
    y_dim = -off - DIM_OFFSET
    for ci in range(cols - 1):
        x0 = sum(grid["x_spacings"][:ci])
        x1 = x0 + grid["x_spacings"][ci]
        msp.add_linear_dim(
            base=(midpoint((x0, y_dim), (x1, y_dim))[0], y_dim),
            p1=(x0, 0), p2=(x1, 0),
            angle=0, dimstyle=style,
            dxfattribs={"layer": L_DIM}
        ).render()
    # Overall bottom
    msp.add_linear_dim(
        base=(W / 2, y_dim - DIM_GAP),
        p1=(0, 0), p2=(W, 0),
        angle=0, dimstyle=style,
        dxfattribs={"layer": L_DIM}
    ).render()

    # Left: dimension each y-bay, then overall
    x_dim = -off - DIM_OFFSET
    for ri in range(rows - 1):
        y0 = sum(grid["y_spacings"][:ri])
        y1 = y0 + grid["y_spacings"][ri]
        msp.add_linear_dim(
            base=(x_dim, midpoint((0, y0), (0, y1))[1]),
            p1=(0, y0), p2=(0, y1),
            angle=90, dimstyle=style,
            dxfattribs={"layer": L_DIM}
        ).render()
    # Overall left
    msp.add_linear_dim(
        base=(x_dim - DIM_GAP, H / 2),
        p1=(0, 0), p2=(0, H),
        angle=90, dimstyle=style,
        dxfattribs={"layer": L_DIM}
    ).render()


# ─── Room labels ─────────────────────────────────────────────────────────────

def _add_mtext(msp, text: str, x: float, y: float, height: float, layer: str) -> None:
    mt = msp.add_mtext(text, dxfattribs={
        "layer": layer,
        "char_height": height,
        "insert": (x, y),
    })
    mt.dxf.attachment_point = 5  # middle-centre


def draw_room_labels(msp: Modelspace, grid: Dict, floor: Dict) -> None:
    for room in floor.get("rooms", []):
        name = room["name"]
        # Support both grid-fraction and absolute coordinates
        if "grid" in room:
            gx, gy = room["grid"]
            x_spacings = grid["x_spacings"]
            y_spacings = grid["y_spacings"]

            def interp_spacing(spacings, val):
                idx = int(val)
                frac = val - idx
                total = sum(spacings[:idx])
                if idx < len(spacings):
                    total += spacings[idx] * frac
                return total

            x = interp_spacing(x_spacings, gx)
            y = interp_spacing(y_spacings, gy)
        else:
            x, y = room.get("x", 0), room.get("y", 0)

        _add_mtext(msp, name, x, y, TEXT_HEIGHT, L_TEXT)

        area = room.get("area_sqm")
        if area:
            _add_mtext(msp, f"{area:.2f} sq.m.", x, y - TEXT_HEIGHT * 1.5,
                       TEXT_HEIGHT * 0.7, L_ANNOTEXT2)


# ─── Drawing title ───────────────────────────────────────────────────────────

def draw_floor_title(msp: Modelspace, grid: Dict, floor: Dict) -> None:
    W, _ = grid_size(grid)
    label = floor.get("label", f"LEVEL {floor['level']} FLOOR PLAN")
    scale_str = floor.get("scale", "1:50")
    off = GRID_BUBBLE_OFFSET + GRID_BUBBLE_R
    y = -(off + DIM_OFFSET + DIM_GAP * 2 + TEXT_HEIGHT * 3)

    _add_mtext(msp, label.upper(), W / 2, y, TEXT_HEIGHT * 1.4, L_TEXT)
    _add_mtext(msp, f"SCALE {scale_str}", W / 2, y - TEXT_HEIGHT * 2,
               TEXT_HEIGHT * 0.9, L_ANNOTEXT2)


# ─── Main floor plan builder ─────────────────────────────────────────────────

def build_floor_plan(msp: Modelspace, doc, grid: Dict, floor: Dict,
                     origin: Point = (0.0, 0.0)) -> None:
    """
    Build one floor plan into `msp` at world `origin`.

    Parameters
    ----------
    msp     : model-space layout
    doc     : ezdxf document (for dimension styles)
    grid    : grid definition dict from config
    floor   : floor dict from config
    origin  : (x, y) offset so multi-storey plans don't overlap
    """
    openings = floor.get("openings", [])

    for wall_def in floor.get("walls", []):
        wf = wall_def["from"]
        wt = wall_def["to"]
        start = add(grid_world(grid, wf), origin)
        end   = add(grid_world(grid, wt), origin)

        # Gather openings for this wall
        wall_openings = [
            op for op in openings
            if op.get("wall", [None, None])[0] == wf
            and op.get("wall", [None, None])[1] == wt
        ]

        draw_wall(msp, start, end, wall_openings)

        for op in wall_openings:
            if op["type"] == "door":
                draw_door(msp, start, end, op)
            elif op["type"] == "window":
                draw_window(msp, start, end, op)

    place_bamboo_poles(msp, grid)
    draw_grid(msp, grid)
    draw_dimensions(msp, doc, grid)
    draw_room_labels(msp, grid, floor)
    draw_floor_title(msp, grid, floor)
