"""
Parse a CBFT wall plan DXF and extract wall parameters:
  - wall_length     (mm)
  - t1_count        (end studs, block bps1)
  - t2_count        (intermediate studs, block bpns1)
  - stud_positions  list of (relative_x, is_t1) sorted left-to-right,
                    where relative_x is measured from the wall's left edge

Multi-plan DXFs (multiple panel blocks in modelspace on the AR-Panels layer)
are handled by parse_multi_plan_dxf(), which returns one dict per plan block.
"""

import ezdxf
from typing import Optional

# Block names that represent studs in the panel block
_T1_BLOCKS = {"bps1"}    # end / corner studs (solid bamboo)
_T2_BLOCKS = {"bpns1"}   # intermediate studs (non-structural / hollow centre)

# Layers used for the wall-outline polyline in plan view
_PLAN_OUTLINE_LAYERS = {"VP", "AR-Timber Plate"}
_MIN_PLAN_WIDTH = 200.0   # ignore polys narrower than this (stud cross-sections, etc.)


def _get_wall_length(msp) -> float:
    """
    Return wall length in mm.
    Priority: (1) total-span DIMENSION, (2) 0-S1 LWPOLY width.
    """
    # Method 1 — largest dimension measurement
    measurements = []
    for e in msp:
        if e.dxftype() == "DIMENSION":
            try:
                measurements.append(float(e.dxf.actual_measurement))
            except Exception:
                pass
    if measurements:
        return round(max(measurements), 1)

    # Method 2 — LWPOLY on 0-S1 layer (wall border line)
    for e in msp:
        if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "0-S1":
            pts = list(e.get_points("xy"))
            if len(pts) >= 2:
                xs = [p[0] for p in pts]
                return round(max(xs) - min(xs), 1)

    raise ValueError("Cannot determine wall length from DXF file.")


def _get_wall_left_x(msp):
    """Return the left-edge world X of the wall from the 0-S1 LWPOLY, or None."""
    for e in msp:
        if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "0-S1":
            pts = list(e.get_points("xy"))
            if len(pts) >= 2:
                return min(p[0] for p in pts)
    return None


def _count_studs_in_block(doc, block_name: str):
    """Walk a block definition and count T1 / T2 stud inserts."""
    t1 = t2 = 0
    if block_name not in doc.blocks:
        return t1, t2
    for e in doc.blocks[block_name]:
        if e.dxftype() == "INSERT":
            name = e.dxf.name.lower()
            if name in _T1_BLOCKS:
                t1 += 1
            elif name in _T2_BLOCKS:
                t2 += 1
    return t1, t2


def _count_studs(doc, msp):
    """
    Find the panel INSERT in modelspace (on AR-Panels layer) and
    count stud blocks inside its block definition.
    """
    for e in msp:
        if e.dxftype() == "INSERT" and e.dxf.layer == "AR-Panels":
            t1, t2 = _count_studs_in_block(doc, e.dxf.name)
            if t1 + t2 > 0:
                return t1, t2

    # Fallback: count directly in modelspace (flat drawing)
    t1 = t2 = 0
    for e in msp:
        if e.dxftype() == "INSERT":
            name = e.dxf.name.lower()
            if name in _T1_BLOCKS:
                t1 += 1
            elif name in _T2_BLOCKS:
                t2 += 1
    return t1, t2


def _t1_indices(n_total: int, t1_count: int) -> set:
    """
    Return the set of 0-based indices that should be T1 studs.

    T1 studs are always at the first and last positions.  Any additional
    T1 studs are distributed as evenly as possible across all positions.

    Examples:
      n=5, t1=2  →  {0, 4}          (ends only)
      n=5, t1=3  →  {0, 2, 4}       (ends + centre)
      n=3, t1=2  →  {0, 2}          (ends only)
    """
    if n_total <= 0 or t1_count <= 0:
        return set()
    if t1_count >= n_total:
        return set(range(n_total))
    if t1_count == 1:
        return {0}
    # Evenly distribute t1_count positions across [0, n_total-1]
    return {round(i * (n_total - 1) / (t1_count - 1)) for i in range(t1_count)}


def _get_cladding(msp, wall_length: float) -> str:
    """
    Detect single vs double-sided cement plaster from the plan DXF.

    Counts LWPOLYLINE rectangles on the 0-S1 layer that are approximately
    wall_length wide and ~25 mm tall — these are the plaster strip outlines.
      1 strip → "single"   (one cladded face)
      2 strips → "double"  (both faces cladded)
    """
    _PLASTER_T = 25.0
    count = 0
    for e in msp:
        if e.dxftype() != "LWPOLYLINE" or e.dxf.layer != "0-S1":
            continue
        pts = list(e.get_points("xy"))
        if len(pts) < 4:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        w = max(xs) - min(xs)
        h = max(ys) - min(ys)
        if abs(w - wall_length) < 10.0 and abs(h - _PLASTER_T) < 5.0:
            count += 1
    return "double" if count >= 2 else "single"


def _get_stud_positions_relative(msp, wall_left, wall_length, t1_count, t2_count):
    """
    Extract stud centre X positions from the horizontal dimension chain
    in modelspace, then assign T1/T2 types by even-distribution.

    The dimension chain defpoints encode the actual stud positions as drawn
    in the plan.  The first/last stud and any evenly-distributed intermediate
    positions are marked T1; the rest are T2.

    Returns sorted list of (relative_x, is_t1) where relative_x is measured
    from wall_left.  Returns an empty list if fewer than 2 stud positions are
    found, or if the extracted count does not match t1_count + t2_count.
    """
    if wall_left is None:
        return []

    n_expected = t1_count + t2_count

    # --- collect all unique X values from non-overall horizontal dimensions ---
    xs_world = set()
    for e in msp:
        if e.dxftype() != "DIMENSION":
            continue
        try:
            m = abs(float(e.dxf.actual_measurement))
        except Exception:
            continue
        # Skip the overall wall-length dimension
        if abs(m - wall_length) < 2.0:
            continue
        try:
            dp2 = e.dxf.defpoint2
            dp3 = e.dxf.defpoint3
        except Exception:
            continue
        # Only horizontal: same Y (±50 mm tolerance), meaningful X span
        if abs(dp2.y - dp3.y) > 50.0:
            continue
        if abs(dp2.x - dp3.x) < 5.0:
            continue
        xs_world.add(round(dp2.x, 2))
        xs_world.add(round(dp3.x, 2))

    if not xs_world:
        return []

    # Convert to relative and clip to wall bounds (±10 mm tolerance)
    xs_rel = sorted(
        round(x - wall_left, 2) for x in xs_world
        if -10.0 <= (x - wall_left) <= wall_length + 10.0
    )

    if len(xs_rel) < 2:
        return []

    # If count doesn't match expectation, return empty (caller uses fallback)
    if n_expected > 0 and len(xs_rel) != n_expected:
        return []

    # Assign T1/T2 by even distribution
    t1_idx = _t1_indices(len(xs_rel), t1_count)
    return [(x, i in t1_idx) for i, x in enumerate(xs_rel)]


def parse_wall_plan(dxf_path: str) -> dict:
    """
    Parse a CBFT wall plan DXF file.

    Returns
    -------
    dict with keys:
        wall_length     : float  — total wall length in mm
        t1_count        : int    — number of T1 (end) bamboo studs
        t2_count        : int    — number of T2 (intermediate) bamboo studs
        stud_positions  : list   — [(relative_x, is_t1), ...] sorted left-to-right
        cladding        : str    — "single" or "double" (from 0-S1 plaster strips)
        source_file     : str    — input file path
    """
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    wall_length = _get_wall_length(msp)
    t1_count, t2_count = _count_studs(doc, msp)

    # Minimal sanity: every wall needs at least 2 end studs
    if t1_count == 0 and t2_count == 0:
        raise ValueError(
            f"No bamboo stud blocks (bps1 / bpns1) found in '{dxf_path}'. "
            "Check that the plan uses the standard CBFT blocks."
        )

    wall_left      = _get_wall_left_x(msp)
    stud_positions = _get_stud_positions_relative(
        msp, wall_left, wall_length, t1_count, t2_count
    )
    cladding       = _get_cladding(msp, wall_length)

    return {
        "wall_length":    wall_length,
        "t1_count":       t1_count,
        "t2_count":       t2_count,
        "stud_positions": stud_positions,
        "cladding":       cladding,
        "source_file":    dxf_path,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Multi-plan support
# ─────────────────────────────────────────────────────────────────────────────

def _block_wall_length(blk) -> Optional[float]:
    """
    Return the wall length (mm) from the widest LWPOLYLINE on VP or
    AR-Timber Plate layers inside a block definition.

    Ignores polys narrower than _MIN_PLAN_WIDTH (stud cross-sections, etc.).
    """
    best: Optional[float] = None
    for e in blk:
        if e.dxftype() != "LWPOLYLINE":
            continue
        if e.dxf.layer not in _PLAN_OUTLINE_LAYERS:
            continue
        pts = list(e.get_points("xy"))
        if len(pts) < 2:
            continue
        xs = [p[0] for p in pts]
        w  = max(xs) - min(xs)
        if w > _MIN_PLAN_WIDTH and (best is None or w > best):
            best = w
    return round(best, 1) if best is not None else None


def _block_panel_width(blk) -> Optional[float]:
    """
    Return the total panel width (mm) as the combined x-range of all
    LWPOLYLINE entities in the block.  Used for door/window panels where
    the VP poly covers only the solid section.
    """
    all_xs = []
    for e in blk:
        if e.dxftype() != "LWPOLYLINE":
            continue
        pts = list(e.get_points("xy"))
        all_xs += [p[0] for p in pts]
    if not all_xs:
        return None
    w = max(all_xs) - min(all_xs)
    return round(w, 1) if w > _MIN_PLAN_WIDTH else None


def _block_panel_type(blk) -> str:
    """
    Determine panel type from block contents:
      - AR-Jambs polys present + ARC entity   → "door"
      - AR-Jambs polys present + 3 lines between jambs → "window"
      - AR-Jambs polys present (ambiguous)    → "door"  (ARC is primary signal)
      - No AR-Jambs                           → "wall"

    Door signal  : door-swing ARC between the two vertical jamb rectangles.
    Window signal: 3 horizontal lines between the jamb rectangles (sill + glazing lines).
    """
    jamb_polys = [
        e for e in blk
        if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "AR-Jambs"
    ]
    if not jamb_polys:
        return "wall"

    # ARC present → door swing → door panel
    for e in blk:
        if e.dxftype() == "ARC":
            return "door"

    # Count lines that fall between the two jamb rectangles (x-range)
    if len(jamb_polys) >= 2:
        jamb_polys.sort(key=lambda p: min(pt[0] for pt in p.get_points("xy")))
        left_inner  = max(pt[0] for pt in jamb_polys[0].get_points("xy"))
        right_inner = min(pt[0] for pt in jamb_polys[-1].get_points("xy"))
        lines_between = sum(
            1 for e in blk
            if e.dxftype() == "LINE"
            and left_inner - 5 <= min(e.dxf.start.x, e.dxf.end.x)
            and max(e.dxf.start.x, e.dxf.end.x) <= right_inner + 5
        )
        if lines_between >= 3:
            return "window"

    return "door"  # AR-Jambs present but no window signal → door


def _block_opening_width(blk) -> Optional[float]:
    """
    Return the clear opening width (mm) from AR-Jambs polys.

    The two jamb rectangles are the vertical timber jambs shown in plan
    cross-section.  The clear opening is the gap between their inner faces.
    """
    jamb_polys = [
        e for e in blk
        if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "AR-Jambs"
    ]
    if len(jamb_polys) < 2:
        return None
    jamb_polys.sort(key=lambda p: min(pt[0] for pt in p.get_points("xy")))
    left_inner  = max(pt[0] for pt in jamb_polys[0].get_points("xy"))
    right_inner = min(pt[0] for pt in jamb_polys[-1].get_points("xy"))
    w = right_inner - left_inner
    return round(w, 1) if w > 50 else None


def _panel_id_from_block_name(block_name: str) -> str:
    """Strip common plan suffixes to produce a short panel ID."""
    pid = block_name
    for suffix in ("-Plan", "-plan", "_Plan", "_plan"):
        if pid.endswith(suffix):
            pid = pid[: -len(suffix)]
            break
    return pid


def parse_multi_plan_dxf(dxf_path: str) -> list:
    """
    Detect and parse multiple plan blocks in a DXF file.

    Scans modelspace for INSERT entities.  Any block that contains bps1 / bpns1
    stud inserts AND a recognisable wall-outline polyline is treated as one panel.

    Panel type is auto-detected per block:
      "wall"   — no AR-Jambs layer polys
      "door"   — AR-Jambs polys + ARC entity (door swing)
      "window" — AR-Jambs polys + 3 lines between jambs (glazing lines)

    Returns
    -------
    A list of dicts, one per detected plan block.  Common keys:
        panel_id, block_name, panel_type, t1_count, t2_count,
        cladding, stud_positions, source_file
    Wall panels add:   wall_length
    Door/window add:   panel_width, opening_width

    Returns an empty list when fewer than 2 detectable panels are found.
    """
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    plans = []
    for e in msp:
        if e.dxftype() != "INSERT":
            continue
        block_name = e.dxf.name
        if block_name not in doc.blocks:
            continue
        blk = doc.blocks[block_name]

        t1 = sum(
            1 for x in blk
            if x.dxftype() == "INSERT" and x.dxf.name in _T1_BLOCKS
        )
        t2 = sum(
            1 for x in blk
            if x.dxftype() == "INSERT" and x.dxf.name in _T2_BLOCKS
        )
        if t1 + t2 == 0:
            continue

        panel_type = _block_panel_type(blk)

        plan = {
            "panel_id":       _panel_id_from_block_name(block_name),
            "block_name":     block_name,
            "panel_type":     panel_type,
            "t1_count":       t1,
            "t2_count":       t2,
            "stud_positions": [],
            "cladding":       "single",
            "source_file":    dxf_path,
        }

        if panel_type == "wall":
            wall_length = _block_wall_length(blk)
            if wall_length is None:
                continue
            plan["wall_length"] = wall_length
        else:
            # door or window: panel_width = full combined x-extent
            panel_width = _block_panel_width(blk)
            if panel_width is None:
                continue
            opening_width = _block_opening_width(blk)
            if opening_width is None:
                continue
            plan["panel_width"]   = panel_width
            plan["opening_width"] = opening_width

        plans.append(plan)

    # Only report as multi-plan when at least 2 panels were found
    return plans if len(plans) >= 2 else []
