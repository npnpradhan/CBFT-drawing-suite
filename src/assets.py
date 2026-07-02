"""
Manages import of CBFT standard blocks from 'Assets Description.dxf'.

Each block was defined at large absolute coordinates (not centered at origin).
The BLOCK_REF dict stores the point in each block's local coordinate space that
should coincide with the desired target position when the block is inserted.

Insert formula:  INSERT at (target_x - ref_x,  target_y - ref_y)
"""
import os
import sys
from typing import Optional
import ezdxf

# ── Reference points (block-local coords that map to the target position) ────
BLOCK_REF = {
    "bps1":        (30825.297, -11129.534),  # circle center (T1 stud plan)
    "bpns1":       (31425.348, -11129.090),  # circle center (T2 stud plan)
    "N2N":         (97952.690, -28168.810),  # T1 stud bottom-centre (elev)
    "Type B":      ( 9798.260,  16186.020),  # T2 stud bottom-centre (elev)
    "BFGGBN":      ( 6742.606, -34201.289),  # callout marker centre
    "Dowel Hole":  (92154.931,  31231.187),  # hole centre
    "J-Bolt Hole": (91204.931,  31514.696),  # hole centre
}

# Native stud heights in block coords (before yscale)
_N2N_STUD_H  = 2024.0   # N2N  (T1 stud with connection detail)
_TYPEB_STUD_H = 2024.0  # Type B (T2 intermediate stud)


def _assets_path() -> Optional[str]:
    if getattr(sys, "frozen", False):
        candidates = [
            os.path.join(sys._MEIPASS, "Assets Description.dxf"),
            os.path.join(os.path.dirname(sys.executable), "Assets Description.dxf"),
        ]
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates = [os.path.join(base, "Assets Description.dxf")]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


_cache: Optional[ezdxf.document.Drawing] = None


def _source():
    global _cache
    if _cache is None:
        p = _assets_path()
        if p:
            _cache = ezdxf.readfile(p)
    return _cache


def import_blocks(target_doc: ezdxf.document.Drawing) -> bool:
    """
    Copy CBFT standard blocks from Assets Description.dxf into target_doc.
    Returns True on success; False if assets file not found.
    """
    src = _source()
    if src is None:
        return False
    try:
        from ezdxf.addons.importer import Importer
        imp = Importer(src, target_doc)
        for name in list(BLOCK_REF.keys()) + ["A$C62F95397"]:
            if name in src.blocks and name not in target_doc.blocks:
                imp.import_block(name)
        return True
    except Exception:
        return False


def has_block(doc: ezdxf.document.Drawing, name: str) -> bool:
    return name in doc.blocks


def add_blockref(msp, block_name: str,
                 target_cx: float, target_cy: float,
                 xscale: float = 1.0, yscale: float = 1.0,
                 rotation: float = 0.0, layer: str = "0") -> bool:
    """
    Insert block_name so its reference point lands at (target_cx, target_cy).
    Returns False if the block does not exist in the document.
    """
    if not has_block(msp.doc, block_name):
        return False
    rx, ry = BLOCK_REF[block_name]
    ix = target_cx - rx * xscale
    iy = target_cy - ry * yscale
    msp.add_blockref(block_name, (ix, iy), dxfattribs={
        "xscale": xscale, "yscale": yscale,
        "rotation": rotation, "layer": layer,
    })
    return True


_NODE_PITCH    = 355.0    # bamboo internode pitch (mm)
_JBOLT_REF_Y   = 262.5   # y of right-rod top within A$C62F95397 block
_JBOLT_YSCALE  = 2.0     # scale so J-bolt extends ~525 mm past stud top (beyond first node at 355 mm)
_FOUND_LINE_H  = 600.0   # foundation embedded-rebar line height (mm)
_MORTAR_ZONES  = 2       # number of internodes to fill with mortar at each end


def add_n2n_stud(msp, stud_cx: float, stud_bottom_y: float,
                 stud_height: float = _N2N_STUD_H,
                 layer: str = "AR-Bamboo Stud") -> bool:
    """
    Draw a T1 end/corner stud elevation:
      (a) Bamboo body rectangle   – layer 0-S2
      (b) Cement mortar fill      – layer .     (DOTS, bottom 2 + top 2 internodes only)
      (c) Bamboo node double-lines– layer 0-S1  (_USER hatch, 355 mm pitch)
      (d) Top J-bolt connection   – layer Bolts (A$C62F95397 block, scaled to reach past 1st node)
      (e) Foundation embedded rod – layer Bolts (600 mm line from stud bottom)
    """
    sr  = 50.0
    x_l = stud_cx - sr
    x_r = stud_cx + sr
    y_b = stud_bottom_y
    y_t = stud_bottom_y + stud_height
    rect = [(x_l, y_b), (x_r, y_b), (x_r, y_t), (x_l, y_t)]

    # (a) Bamboo body rectangle
    msp.add_lwpolyline(rect, close=True, dxfattribs={"layer": "0-S2"})

    # (b) Cement mortar fill — only at the internode zones containing hardware
    #     bottom zone: 2 internodes (covers 600 mm foundation rod)
    #     top zone:    2 internodes (covers J-bolt depth)
    mortar_depth = _MORTAR_ZONES * _NODE_PITCH   # 710 mm
    y_bot_hi = min(y_b + mortar_depth, y_t)
    y_top_lo = max(y_t - mortar_depth, y_b)
    # avoid double-filling when stud is very short (zones overlap)
    if y_top_lo < y_bot_hi:
        y_top_lo = y_bot_hi

    for (z_b, z_t) in [(y_b, y_bot_hi), (y_top_lo, y_t)]:
        if z_t > z_b:
            zone = [(x_l, z_b), (x_r, z_b), (x_r, z_t), (x_l, z_t)]
            h = msp.add_hatch(dxfattribs={"layer": "."})
            h.set_pattern_fill("DOTS", scale=20.0)
            h.paths.add_polyline_path(zone, is_closed=True)

    # (c) Bamboo node double-lines over full stud height
    for base_y in [0.0, 10.0]:
        h_node = msp.add_hatch(dxfattribs={"layer": "0-S1"})
        h_node.set_pattern_fill("_USER", definition=[(0.0, (0, base_y), (0, _NODE_PITCH), [])])
        h_node.paths.add_polyline_path(rect, is_closed=True)

    # (d) Top J-bolt: scale yscale so hook extends past first node (~525 mm deep)
    #     Insert formula: INSERT.y = y_t - _JBOLT_REF_Y * yscale
    if has_block(msp.doc, "A$C62F95397"):
        msp.add_blockref(
            "A$C62F95397",
            (stud_cx - 25.0, y_t - _JBOLT_REF_Y * _JBOLT_YSCALE),
            dxfattribs={"layer": "Bolts", "yscale": _JBOLT_YSCALE},
        )

    # (e) Foundation embedded rod: 600 mm line from stud bottom
    msp.add_line(
        (stud_cx, y_b), (stud_cx, y_b + _FOUND_LINE_H),
        dxfattribs={"layer": "Bolts"},
    )
    return True


def add_type_b_stud(msp, stud_cx: float, stud_bottom_y: float,
                    stud_height: float = _TYPEB_STUD_H,
                    layer: str = "AR-Bamboo Stud") -> bool:
    """
    Insert the Type B block (T2 intermediate stud with flat-bar hatching)
    centred at stud_cx with its bottom at stud_bottom_y.
    """
    if not has_block(msp.doc, "Type B"):
        return False
    yscale = stud_height / _TYPEB_STUD_H
    rx, ry = BLOCK_REF["Type B"]  # (9798.26, 16186.02) stud bottom-centre
    ix = stud_cx - rx
    iy = stud_bottom_y - ry * yscale
    msp.add_blockref("Type B", (ix, iy), dxfattribs={
        "xscale": 1.0, "yscale": yscale, "layer": layer,
    })
    return True
