"""
CBFT Drawing Suite — Floor Plan Generator
Usage:
    python main.py config/single_story.json
    python main.py config/two_story.json  --output my_house.dxf
"""
import argparse
import json
import sys
from pathlib import Path

import ezdxf

from src.layers import setup_layers
from src.blocks import define_all_blocks
from src.floor_plan import build_floor_plan, grid_size


def main():
    parser = argparse.ArgumentParser(
        description="Generate a CBFT house floor plan DXF from a JSON config."
    )
    parser.add_argument("config", help="Path to JSON configuration file")
    parser.add_argument("--output", "-o", default=None,
                        help="Output DXF file path (default: same name as config with .dxf)")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"ERROR: config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)

    output_path = Path(args.output) if args.output else config_path.with_suffix(".dxf")

    # ── Build DXF document ────────────────────────────────────────────────────
    doc = ezdxf.new("R2018", setup="standard")
    setup_layers(doc)
    define_all_blocks(doc)

    msp = doc.modelspace()
    grid = cfg["grid"]

    stories = cfg.get("stories", 1)
    floors  = cfg.get("floors", [])

    if len(floors) != stories:
        print(f"WARNING: 'stories'={stories} but {len(floors)} floor(s) defined. "
              "Using floor count.", file=sys.stderr)

    # Stack floors horizontally with a gap between them
    W, H = grid_size(grid)
    H_GAP = H * 0.5  # vertical gap between stacked floor plans

    for i, floor in enumerate(floors):
        # Stack floors vertically: ground floor at y=0, upper floor above
        origin = (0.0, i * (H + H_GAP))
        build_floor_plan(msp, doc, grid, floor, origin=origin)

    doc.saveas(output_path)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
