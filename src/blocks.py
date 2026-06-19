"""
Define reusable DXF block definitions used across floor plans.
All blocks are origin-centred so INSERT places them correctly.
"""
import math
import ezdxf
from .constants import (
    GRID_BUBBLE_R, BAMBOO_POLE_R, L_GRID, L_BAMBOO, L_WALL, L_DOOR,
    L_WINDOW, L_HIDDEN, L_CENTER
)


def _make_block(doc, name: str) -> ezdxf.layouts.BlockLayout:
    if name in doc.blocks:
        return doc.blocks[name]
    return doc.blocks.new(name)


def define_grid_bubble(doc) -> None:
    """Circle + attribute for grid line designation (column or row label)."""
    blk = _make_block(doc, "GRID_BUBBLE")
    blk.add_circle((0, 0), GRID_BUBBLE_R, dxfattribs={"layer": L_GRID})
    blk.add_attdef(
        "LABEL", (0, 0),
        dxfattribs={
            "layer": L_GRID,
            "height": GRID_BUBBLE_R * 0.8,
            "halign": 1,  # center
            "valign": 2,  # middle
        }
    )


def define_door_tag(doc) -> None:
    """Circle designation tag for door number (matches at-door convention)."""
    r = 500
    blk = _make_block(doc, "DOOR_TAG")
    blk.add_circle((0, 0), r, dxfattribs={"layer": L_DOOR})
    blk.add_line((-r, 0), (r, 0), dxfattribs={"layer": L_DOOR})
    blk.add_attdef(
        "TAG", (0, 0),
        dxfattribs={
            "layer": L_DOOR,
            "height": r * 0.7,
            "halign": 1,
            "valign": 2,
        }
    )


def define_window_tag(doc) -> None:
    """Hexagon designation tag for window number (matches at-wind convention)."""
    r = 500
    blk = _make_block(doc, "WINDOW_TAG")
    pts = [(r * math.cos(math.radians(30 + 60 * i)),
            r * math.sin(math.radians(30 + 60 * i))) for i in range(6)]
    blk.add_lwpolyline(pts, close=True, dxfattribs={"layer": L_WINDOW})
    blk.add_line((-r, 0), (r, 0), dxfattribs={"layer": L_WINDOW})
    blk.add_attdef(
        "TAG", (0, 0),
        dxfattribs={
            "layer": L_WINDOW,
            "height": r * 0.7,
            "halign": 1,
            "valign": 2,
        }
    )


def define_bamboo_pole(doc) -> None:
    """Small solid circle representing a bamboo pole cross-section in plan."""
    blk = _make_block(doc, "BAMBOO_POLE")
    blk.add_circle((0, 0), BAMBOO_POLE_R, dxfattribs={"layer": L_BAMBOO})
    # Diagonal cross inside to distinguish from other circles
    r = BAMBOO_POLE_R * 0.7
    blk.add_line((-r, -r), (r, r), dxfattribs={"layer": L_BAMBOO})
    blk.add_line((-r, r), (r, -r), dxfattribs={"layer": L_BAMBOO})


def define_all_blocks(doc) -> None:
    define_grid_bubble(doc)
    define_door_tag(doc)
    define_window_tag(doc)
    define_bamboo_pole(doc)
