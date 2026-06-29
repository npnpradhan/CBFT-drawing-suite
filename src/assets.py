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
    "N2N":         (97952.690, -28168.810),  # stud body BOTTOM-centre
    "BFGGBN":      ( 6742.606, -34201.289),  # callout marker centre
    "Dowel Hole":  (92154.931,  31231.187),  # hole centre
    "J-Bolt Hole": (91204.931,  31514.696),  # hole centre
}

# N2N stud body dimensions (native, before any yscale)
_N2N_STUD_H = 2024.0   # height of stud rectangle in block coords


def _assets_path() -> Optional[str]:
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = os.path.join(base, "Assets Description.dxf")
    return p if os.path.exists(p) else None


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
        from ezdxf.importer import Importer
        imp = Importer(src, target_doc)
        for name in list(BLOCK_REF.keys()) + ["A$C62F95397"]:
            if name in src.blocks:
                imp.import_block(name)
        imp.execute()
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


def add_n2n_stud(msp, stud_cx: float, stud_bottom_y: float,
                 stud_height: float = _N2N_STUD_H,
                 layer: str = "AR-Bamboo Stud") -> bool:
    """
    Insert the N2N stud block centred at stud_cx with its bottom at stud_bottom_y.
    yscale is applied to match a non-standard stud height.
    """
    if not has_block(msp.doc, "N2N"):
        return False
    yscale = stud_height / _N2N_STUD_H
    # BLOCK_REF["N2N"] = (97952.69, -28168.81) is the stud bottom-centre
    rx, ry = BLOCK_REF["N2N"]
    ix = stud_cx - rx                        # xscale always 1
    iy = stud_bottom_y - ry * yscale
    msp.add_blockref("N2N", (ix, iy), dxfattribs={
        "xscale": 1.0, "yscale": yscale, "layer": layer,
    })
    return True
