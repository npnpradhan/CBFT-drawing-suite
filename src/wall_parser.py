"""
Parse a CBFT wall plan DXF and extract wall parameters:
  - wall_length     (mm)
  - t1_count        (end studs, block bps1)
  - t2_count        (intermediate studs, block bpns1)
  - stud_positions  list of (relative_x, is_t1) sorted left-to-right,
                    where relative_x is measured from the wall's left edge
"""

import ezdxf

# Block names that represent studs in the panel block
_T1_BLOCKS = {"bps1"}    # end / corner studs (solid bamboo)
_T2_BLOCKS = {"bpns1"}   # intermediate studs (non-structural / hollow centre)


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

    return {
        "wall_length":    wall_length,
        "t1_count":       t1_count,
        "t2_count":       t2_count,
        "stud_positions": stud_positions,
        "source_file":    dxf_path,
    }
