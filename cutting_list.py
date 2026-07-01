"""
CBFT Cutting List Generator
============================
Reads a CBFT panel plan DXF and outputs a detailed cutting list.

Supports wall panels, door panels, and window panels.
Panel type is auto-detected from the plan DXF.

Usage
-----
    python cutting_list.py panel_1200A_plan.dxf
    python cutting_list.py door_1000.dxf
    python cutting_list.py window_900.dxf --opening-height 1230
    python cutting_list.py panel_1200A_plan.dxf --cladding double
    python cutting_list.py panel_1200A_plan.dxf --output my_panel.dxf
    python cutting_list.py panel_1200A_plan.dxf --csv

Cladding
--------
  --cladding single   TADTAD bamboo matrix (default — single-cladded panel)
  --cladding double   RIBLATH expanded metal lath (double-cladded panel)

Outputs
-------
  <name>_cutting_list.dxf   — DXF table (matches reference drawing style)
  <name>_cutting_list.csv   — spreadsheet-friendly CSV  (with --csv flag)
"""

import argparse
import csv
import sys
from pathlib import Path

import ezdxf

from src.wall_parser       import parse_wall_plan
from src.cutting_rules     import compute_cutting_list
from src.door_parser       import is_door_window_plan, parse_door_window_plan
from src.door_rules        import (compute_door_cutting_list, compute_window_cutting_list,
                                   DOOR_WALL_HEIGHT, DOOR_OPENING_HEIGHT)
from src.table_writer      import write_cutting_table
from src.elevation_writer  import draw_details, draw_door_details, draw_window_details
from src.layers            import setup_layers


def _print_verbose(rows) -> None:
    """Print cutting list to stdout, replacing characters the console can't encode."""
    enc = sys.stdout.encoding or "ascii"
    def safe(s):
        return s.encode(enc, errors="replace").decode(enc)
    print("\n  COMPONENT               SIZE                  LENGTH       QTY")
    print("  " + "-" * 68)
    for r in rows:
        line = f"  {r.component:<24} {r.size:<22} {r.length:<12} {r.qty} {r.unit}"
        print(safe(line))


def write_csv(rows, csv_path: Path) -> None:
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["component", "size", "length", "qty", "unit"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row.as_dict())
    print(f"CSV saved : {csv_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a CBFT panel cutting list from a plan DXF."
    )
    parser.add_argument("plan", help="Path to CBFT panel plan DXF file")
    parser.add_argument("--output", "-o", default=None,
                        help="Output DXF path (default: <plan>_cutting_list.dxf)")
    parser.add_argument("--height", type=float, default=None,
                        help="Total panel height in mm, incl. top and bottom plates "
                             "(default: 2440 for door/window panels, 2100 for wall panels)")
    parser.add_argument("--cladding", choices=["single", "double"], default=None,
                        help="Override cladding type: 'single' (TADTAD) or 'double' "
                             "(RIBLATH).  Detected automatically from the plan DXF "
                             "when not specified.")
    parser.add_argument("--opening-height", type=float, default=None,
                        help="Door/window opening clear height in mm "
                             f"(default for doors: {DOOR_OPENING_HEIGHT} mm; "
                             "required for window panels).")
    parser.add_argument("--csv",  action="store_true",
                        help="Also export a CSV file")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"ERROR: file not found: {plan_path}", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.output) if args.output else plan_path.with_name(
        plan_path.stem + "_cutting_list.dxf"
    )

    doc = ezdxf.new("R2018", setup="standard")
    setup_layers(doc)
    msp = doc.modelspace()
    panel_id = plan_path.stem.replace("_plan", "").upper()

    # ── Detect panel type and parse ───────────────────────────────────────────
    if is_door_window_plan(str(plan_path)):
        # ── Door or window panel ─────────────────────────────────────────────
        params        = parse_door_window_plan(str(plan_path))
        panel_type    = params["panel_type"]
        panel_width   = params["panel_width"]
        opening_width = params["opening_width"]
        t1_count      = params["t1_count"]
        t2_count      = params["t2_count"]
        cladding      = args.cladding or params.get("cladding", "single")
        # Default height: 2440 mm for door/window panels (8 ft standard)
        panel_height  = args.height if args.height is not None else DOOR_WALL_HEIGHT

        print(f"Panel type  : {panel_type.upper()}")
        print(f"Panel width : {panel_width:.0f} mm")
        print(f"Panel height: {panel_height:.0f} mm")
        print(f"Opening W   : {opening_width:.0f} mm")
        print(f"T1 studs    : {t1_count}  T2 studs: {t2_count}")
        print(f"Cladding    : {cladding}{'' if args.cladding else ' (from plan)'}")

        if panel_type == "door":
            opening_height = args.opening_height if args.opening_height is not None \
                             else DOOR_OPENING_HEIGHT
            print(f"Opening H   : {opening_height:.0f} mm")
            rows = compute_door_cutting_list(
                panel_width, opening_width, opening_height,
                t1_count=t1_count, t2_count=t2_count,
                cladding=cladding, panel_height=panel_height,
            )
            draw_fn_kwargs = dict(
                opening_width=opening_width,
                opening_height=opening_height,
                t1_count=t1_count,
                t2_count=t2_count,
                wall_height=panel_height,
                cladding=cladding,
                source_dxf=str(plan_path),
            )
            draw_fn = draw_door_details

        else:   # window
            if args.opening_height is None:
                print(
                    "ERROR: --opening-height is required for window panels.\n"
                    "  Example: --opening-height 1230",
                    file=sys.stderr,
                )
                sys.exit(1)
            opening_height = args.opening_height
            print(f"Opening H   : {opening_height:.0f} mm")
            rows = compute_window_cutting_list(
                panel_width, opening_width, opening_height,
                t1_count=t1_count, t2_count=t2_count,
                cladding=cladding, panel_height=panel_height,
            )
            draw_fn_kwargs = dict(
                opening_width=opening_width,
                opening_height=opening_height,
                wall_height=panel_height,
                cladding=cladding,
            )
            draw_fn = draw_window_details

        if args.verbose:
            _print_verbose(rows)

        write_cutting_table(msp, rows, origin_x=0, origin_y=0, panel_id=panel_id)
        draw_fn(msp, panel_width, origin_x=0, origin_y=0, **draw_fn_kwargs)

    else:
        # ── Wall panel ───────────────────────────────────────────────────────
        panel_height   = args.height if args.height is not None else 2100.0
        params         = parse_wall_plan(str(plan_path))
        L              = params["wall_length"]
        t1             = params["t1_count"]
        t2             = params["t2_count"]
        stud_positions = params.get("stud_positions", [])
        cladding       = args.cladding or params.get("cladding", "single")

        print(f"Panel type  : WALL")
        print(f"Wall length : {L:.0f} mm")
        print(f"Wall height : {panel_height:.0f} mm")
        print(f"T1 studs    : {t1}  (end/corner)")
        print(f"T2 studs    : {t2}  (intermediate)")
        print(f"Cladding    : {cladding}{'' if args.cladding else ' (from plan)'}")
        if stud_positions:
            xs_str = ", ".join(f"{x:.0f}" for x, _ in stud_positions)
            print(f"Stud X pos  : [{xs_str}] mm from left")

        rows = compute_cutting_list(L, t1, t2, cladding=cladding,
                                    wall_height=panel_height)

        if args.verbose:
            _print_verbose(rows)

        write_cutting_table(msp, rows, origin_x=0, origin_y=0, panel_id=panel_id)
        draw_details(msp, L, t1, t2, origin_x=0, origin_y=0,
                     wall_height=panel_height,
                     stud_positions=stud_positions, cladding=cladding)

    doc.saveas(out_path)
    print(f"DXF saved  : {out_path}")

    if args.csv:
        csv_path = out_path.with_suffix(".csv")
        write_csv(rows, csv_path)


if __name__ == "__main__":
    main()
