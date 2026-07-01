"""
Parse a CBFT door or window panel plan DXF and extract panel parameters.

Door/window plans are distinguished from wall plans by the presence of the
"AR-Jambs" layer.  Within that type, a door plan contains an ARC entity
(door swing) inside the panel block; a window plan does not.
"""

import ezdxf

# Keyword fragments that identify the door/window opening LWPOLY layer
_OPENING_LAYER_KEYS = ("DOOR", "WINDOW", "A-DOOR", "A-WINDOW")


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_panel_block_insert(msp):
    """Return the INSERT entity on the AR-Panels layer, or None."""
    for e in msp:
        if e.dxftype() == "INSERT" and e.dxf.layer == "AR-Panels":
            return e
    return None


def _detect_panel_type(doc, block_name: str) -> str:
    """
    Returns "door" if the block definition contains an ARC entity (door swing),
    otherwise "window".
    """
    if block_name not in doc.blocks:
        return "window"
    for e in doc.blocks[block_name]:
        if e.dxftype() == "ARC":
            return "door"
    return "window"


def _get_opening_width(doc, block_name: str):
    """
    Find the LWPOLY on a door/window layer inside the block and return the
    length of its longer axis — this is the opening width in mm.

    Returns None when no suitable LWPOLY is found.
    """
    if block_name not in doc.blocks:
        return None
    for e in doc.blocks[block_name]:
        if e.dxftype() != "LWPOLYLINE":
            continue
        layer_upper = e.dxf.layer.upper()
        if not any(k in layer_upper for k in _OPENING_LAYER_KEYS):
            continue
        pts = list(e.get_points("xy"))
        if len(pts) < 2:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x_span = abs(max(xs) - min(xs))
        y_span = abs(max(ys) - min(ys))
        opening = max(x_span, y_span)
        if opening > 200:   # sanity: real openings are at least 200 mm
            return round(opening, 1)
    return None


def _get_panel_width(msp) -> float:
    """
    Return total panel width (mm) from the largest DIMENSION measurement.
    Falls back to the widest LWPOLY extent in modelspace.
    """
    measurements = []
    for e in msp:
        if e.dxftype() == "DIMENSION":
            try:
                measurements.append(abs(float(e.dxf.actual_measurement)))
            except Exception:
                pass
    if measurements:
        return round(max(measurements), 1)

    # Fallback: largest LWPOLY extent
    best = 0.0
    for e in msp:
        if e.dxftype() != "LWPOLYLINE":
            continue
        pts = list(e.get_points("xy"))
        if len(pts) < 2:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        w = max(abs(max(xs) - min(xs)), abs(max(ys) - min(ys)))
        if w > best:
            best = w
    if best > 0:
        return round(best, 1)
    raise ValueError("Cannot determine panel width from DXF file.")


def _get_opening_from_dimensions(msp, panel_width: float):
    """
    Derive the door/window opening width from the horizontal dimension chain.

    The opening is the LARGEST sub-dimension (the other sub-dims are the
    solid-section bay spacings, which are all smaller).

    Returns the largest sub-dimension rounded to 1 decimal place, or None
    when the dimension chain cannot be read.
    """
    sub_dims = []
    for e in msp:
        if e.dxftype() != "DIMENSION":
            continue
        try:
            m = abs(float(e.dxf.actual_measurement))
        except Exception:
            continue
        if abs(m - panel_width) < 2.0:     # skip overall panel-width dimension
            continue
        if m < 50.0:
            continue
        try:
            dp2 = e.dxf.defpoint2
            dp3 = e.dxf.defpoint3
        except Exception:
            continue
        if abs(dp2.y - dp3.y) > 50.0:      # horizontal only
            continue
        if abs(dp2.x - dp3.x) < 5.0:
            continue
        sub_dims.append(m)

    if not sub_dims:
        return None
    return round(max(sub_dims), 1)


def _count_door_studs(msp, panel_width: float):
    """
    Derive T1 / T2 stud counts from the horizontal dimension chain in the plan.

    Strategy
    --------
    The plan encodes one sub-dimension per bay (gap between adjacent stud centres).
    One of those bays equals the door/window opening width; the rest are the
    solid-section bay spacings.

      n_bays      = number of sub-dimensions  (= n_studs - 1)
      n_solid_bays = n_bays - 1               (subtract the opening bay)
      T2           = max(0, n_solid_bays - 1) (intermediate studs in solid section)
      T1           = n_studs - T2             (everything else)

    Falls back to (2, 0) when fewer than two stud positions can be found.
    """
    xs: set[float] = set()
    for e in msp:
        if e.dxftype() != "DIMENSION":
            continue
        try:
            m = abs(float(e.dxf.actual_measurement))
        except Exception:
            continue
        if abs(m - panel_width) < 2.0:     # skip overall panel-width dimension
            continue
        if m < 50.0:                        # ignore tiny annotation dims
            continue
        try:
            dp2 = e.dxf.defpoint2
            dp3 = e.dxf.defpoint3
        except Exception:
            continue
        # Horizontal only: same Y within ±50 mm, meaningful X span
        if abs(dp2.y - dp3.y) > 50.0:
            continue
        if abs(dp2.x - dp3.x) < 5.0:
            continue
        xs.add(round(dp2.x, 0))
        xs.add(round(dp3.x, 0))

    n = len(xs)
    if n < 2:
        return 2, 0     # minimal: just two end studs, no T2

    # n stud positions → n-1 bays total, n-2 solid-section bays
    t2 = max(0, n - 3)
    t1 = n - t2
    return t1, t2


def _get_cladding(msp, panel_width: float) -> str:
    """
    Detect single vs double-sided cement plaster — same logic as wall_parser.
    Counts 0-S1 LWPOLY rectangles ≈ panel_width wide and ≈ 25 mm tall.
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
        long_dim  = max(abs(max(xs) - min(xs)), abs(max(ys) - min(ys)))
        short_dim = min(abs(max(xs) - min(xs)), abs(max(ys) - min(ys)))
        if abs(long_dim - panel_width) < 10.0 and abs(short_dim - _PLASTER_T) < 5.0:
            count += 1
    return "double" if count >= 2 else "single"


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def is_door_window_plan(dxf_path: str) -> bool:
    """
    Quick check — returns True when the DXF is a door or window panel plan.

    Three detection methods (any one is sufficient):
      1. "AR-Jambs" layer present (standard door/window style).
      2. Any layer whose name contains "DOOR" or "WINDOW" (older/imported plans).
      3. The panel block (INSERT on AR-Panels) contains an ARC entity (door swing)
         or a LWPOLY on a layer whose name contains "DOOR" or "WINDOW".
    """
    try:
        doc = ezdxf.readfile(dxf_path)

        # Method 1 — AR-Jambs layer
        for l in doc.layers:
            if l.dxf.name == "AR-Jambs":
                return True

        # Method 2 — any layer name containing DOOR or WINDOW
        for l in doc.layers:
            name_up = l.dxf.name.upper()
            if "DOOR" in name_up or "WINDOW" in name_up:
                return True

        # Method 3 — block geometry
        msp = doc.modelspace()
        for e in msp:
            if e.dxftype() != "INSERT" or e.dxf.layer != "AR-Panels":
                continue
            block_name = e.dxf.name
            if block_name not in doc.blocks:
                continue
            for be in doc.blocks[block_name]:
                if be.dxftype() == "ARC":
                    return True
                if be.dxftype() == "LWPOLYLINE":
                    layer_up = be.dxf.layer.upper()
                    if "DOOR" in layer_up or "WINDOW" in layer_up:
                        return True

        return False
    except Exception:
        return False


def parse_door_window_plan(dxf_path: str) -> dict:
    """
    Parse a CBFT door or window panel plan DXF.

    Returns
    -------
    dict with keys:
        panel_type    : str   — "door" or "window"
        panel_width   : float — total panel length in mm
        opening_width : float — clear door/window opening width in mm
        t1_count      : int   — end / structural bamboo studs
        t2_count      : int   — intermediate bamboo studs
        cladding      : str   — "single" or "double"
        source_file   : str   — input file path
    """
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    panel_width = _get_panel_width(msp)

    insert = _get_panel_block_insert(msp)
    if insert is None:
        raise ValueError(
            f"No INSERT on AR-Panels layer found in '{dxf_path}'. "
            "Check that the plan uses the standard CBFT block layout."
        )

    block_name = insert.dxf.name
    panel_type  = _detect_panel_type(doc, block_name)
    opening_width = _get_opening_width(doc, block_name)

    # Validate: opening must be meaningfully smaller than the panel
    if opening_width is not None and opening_width >= panel_width - 50:
        opening_width = None   # discard implausible value, try other methods

    if opening_width is None:
        # Fallback 1: derive from dimension chain (largest sub-dimension = opening)
        opening_width = _get_opening_from_dimensions(msp, panel_width)
    if opening_width is None:
        # Fallback 2: panel minus two plate thicknesses (last resort)
        from .cutting_rules import PLATE_THICKNESS
        opening_width = panel_width - 2 * PLATE_THICKNESS

    t1_count, t2_count = _count_door_studs(msp, panel_width)
    cladding = _get_cladding(msp, panel_width)

    return {
        "panel_type":    panel_type,
        "panel_width":   panel_width,
        "opening_width": opening_width,
        "t1_count":      t1_count,
        "t2_count":      t2_count,
        "cladding":      cladding,
        "source_file":   dxf_path,
    }
