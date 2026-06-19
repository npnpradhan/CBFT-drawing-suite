"""
Parse a CBFT wall plan DXF and extract wall parameters:
  - wall_length  (mm)
  - t1_count     (end studs, block bps1)
  - t2_count     (intermediate studs, block bpns1)
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


def parse_wall_plan(dxf_path: str) -> dict:
    """
    Parse a CBFT wall plan DXF file.

    Returns
    -------
    dict with keys:
        wall_length  : float  — total wall length in mm
        t1_count     : int    — number of T1 (end) bamboo studs
        t2_count     : int    — number of T2 (intermediate) bamboo studs
        source_file  : str    — input file path
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

    return {
        "wall_length": wall_length,
        "t1_count":    t1_count,
        "t2_count":    t2_count,
        "source_file": dxf_path,
    }
