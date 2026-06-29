"""
CBFT DXF document template.

`setup_layers(doc)` configures a blank ezdxf document so that its
layers, text styles, linetypes, and dimension style exactly match the
reference panel drawings.  Call this once, immediately after
`ezdxf.new()`, before drawing anything.

All values extracted directly from the reference DXF files:
  panel_1200A_detail.dxf / panel_1200A_plan.dxf (and the 1000A / 1500A/B set).
"""

from __future__ import annotations
import ezdxf


# ── Layer definitions ─────────────────────────────────────────────────────────
# (name, ACI_color, lineweight_hundredths, linetype, plot)
# lineweight: -3 = ByLayer default; 70 = 0.70 mm
_LAYERS: list[tuple] = [
    # name                    color  lw    linetype       plot
    (".",                         5,  70, "Continuous",      1),
    ("0",                         7,  -3, "Continuous",      1),
    ("0-S1",                      1,  -3, "Continuous",      1),  # red  — leaders / callout boxes
    ("0-S2",                      2,  -3, "Continuous",      1),  # yellow — table borders / outlines
    ("0-S8",                      8,  -3, "Continuous",      1),
    ("1CO",                       1,  -3, "Continuous",      1),
    ("A-BAMBOO POLE",             2,  -3, "Continuous",      1),
    ("A-DIMENSIONS",             30,  -3, "Continuous",      1),  # orange — dimensions
    ("A-Hatch",                   8,  -3, "Continuous",      1),  # dark grey — hatch
    ("A-Main Text",               3,  -3, "Continuous",      1),  # green — primary table text
    ("A-Specifications",          2,  -3, "Continuous",      1),  # yellow — secondary annotations
    ("A-WALL",                    4,  -3, "Continuous",      1),
    ("AR-Bamboo Stud",            2,  -3, "Continuous",      1),
    ("AR-FURNITURES",             9,  -3, "Continuous",      1),
    ("AR-Flatbar",              143,  -3, "Continuous",      1),  # ACI 143 (olive-grey)
    ("AR-Panels",                 4,  -3, "Continuous",      1),  # cyan — stud inserts
    ("AR-Timber Plate",           3,  -3, "Continuous",      1),  # green — plate rectangles
    ("Bolts",                     4,  -3, "HIDDEN2",         1),
    ("Defpoints",                36,  -3, "Continuous",      0),  # no-plot
    ("Screw Connection",         13,  -3, "Continuous",      1),
    ("Screw Dowel",             140,  -3, "Continuous",      1),
    ("Screw J-Bolt",             64,  -3, "Continuous",      1),
    ("VP",                        7,  -3, "Continuous",      1),  # viewport borders
]


# ── Text style definitions ────────────────────────────────────────────────────
# (name, font_file)
_STYLES: list[tuple[str, str]] = [
    ("Standard",    "arial.ttf"),    # default — used by most TEXT / MTEXT
    ("Annotative",  "arial.ttf"),
    ("LEROY",       "simplex.shx"),  # used by dimensions (DIM100)
]


# ── DIM100 dimension style ────────────────────────────────────────────────────
# Values extracted directly from Assets Description.dxf (DIM100 and BASE styles).
_DIM100 = {
    "dimscale": 1.0,
    "dimtxt":   100.0,       # text height (was 220 — assets: 100)
    "dimasz":    50.0,       # arrow/tick size (was 180 — assets: 50)
    "dimblk1":  "_ArchTick", # arrow 1 — arch tick (assets: _ArchTick)
    "dimblk2":  "_ArchTick", # arrow 2
    "dimsah":   1,           # separate arrow blocks
    "dimclrd":  30,          # dimension line colour (ACI 30)
    "dimclre":  30,          # extension line colour
    "dimclrt":   3,          # text colour (ACI 3 = green; was 7)
    "dimtxsty": "LEROY",
    "dimgap":   50.0,        # gap between text and dimension line
    "dimexe":    0.0,        # extension line extension beyond dim line
    "dimexo":  100.0,        # extension line origin offset
    "dimtad":    1,          # text above dimension line
    "dimtix":    1,          # force text inside extension lines
    "dimtofl":   1,          # force dim line between extension lines
    "dimtmove":  1,          # move text with a leader when outside
    "dimdec":    0,          # 0 decimal places for dimensions
    "dimadec":   2,
    "dimzin":    1,
}


# ─────────────────────────────────────────────────────────────────────────────
# Public function
# ─────────────────────────────────────────────────────────────────────────────

def setup_layers(doc: ezdxf.document.Drawing) -> None:
    """
    Initialise a freshly-created DXF document with the complete CBFT layer
    template — layers, text styles, linetypes, and dimension style.

    Safe to call multiple times; existing entries are updated in-place.
    """

    # ── 1. Linetypes ─────────────────────────────────────────────────────────
    if "HIDDEN2" not in doc.linetypes:
        doc.linetypes.new("HIDDEN2", dxfattribs={
            "description": "Hidden (.5x) _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _",
            "pattern": "A,.25,-.125",
        })

    # ── 2. Text styles ────────────────────────────────────────────────────────
    for name, font in _STYLES:
        if name in doc.styles:
            doc.styles.get(name).dxf.font = font
        else:
            doc.styles.new(name, dxfattribs={"font": font})

    # ── 3. Layers ─────────────────────────────────────────────────────────────
    for name, color, lw, ltype, plot in _LAYERS:
        if name in doc.layers:
            layer = doc.layers.get(name)
        else:
            layer = doc.layers.new(name)
        layer.dxf.color      = color
        layer.dxf.lineweight = lw
        layer.dxf.linetype   = ltype
        layer.dxf.plot       = plot

    # ── 4. Arrow block ────────────────────────────────────────────────────────
    # _ArchTick = diagonal line from (-0.5,-0.5) to (0.5,0.5) — confirmed from
    # assets analysis.  Must exist before DIM100 references it.
    if "_ArchTick" not in doc.blocks:
        blk = doc.blocks.new("_ArchTick")
        blk.add_lwpolyline([(-0.5, -0.5), (0.5, 0.5)],
                           dxfattribs={"layer": "0"})

    # ── 5. Dimension style ────────────────────────────────────────────────────
    if "DIM100" in doc.dimstyles:
        ds = doc.dimstyles.get("DIM100")
    else:
        ds = doc.dimstyles.new("DIM100")
    for attr, val in _DIM100.items():
        ds.dxf.set(attr, val)
