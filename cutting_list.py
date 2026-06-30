"""
CBFT Cutting List Generator
============================
Reads a CBFT wall plan DXF and outputs a detailed cutting list.

Usage
-----
    python cutting_list.py panel_1200A_plan.dxf
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
from src.table_writer      import write_cutting_table
from src.elevation_writer  import draw_details
from src.layers            import setup_layers


def write_csv(rows, csv_path: Path) -> None:
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["component", "size", "length", "qty", "unit"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row.as_dict())
    print(f"CSV saved : {csv_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a CBFT wall cutting list from a wall plan DXF."
    )
    parser.add_argument("plan", help="Path to CBFT wall plan DXF file")
    parser.add_argument("--output", "-o", default=None,
                        help="Output DXF path (default: <plan>_cutting_list.dxf)")
    parser.add_argument("--height", type=float, default=2100.0,
                        help="Total wall height in mm, incl. top and bottom plates "
                             "(default: 2100)")
    parser.add_argument("--cladding", choices=["single", "double"], default="single",
                        help="Infill matrix type: 'single' -> TADTAD (default), "
                             "'double' -> RIBLATH")
    parser.add_argument("--csv",  action="store_true",
                        help="Also export a CSV file")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"ERROR: file not found: {plan_path}", file=sys.stderr)
        sys.exit(1)

    # ── Parse plan ────────────────────────────────────────────────────────────
    params          = parse_wall_plan(str(plan_path))
    L               = params["wall_length"]
    t1              = params["t1_count"]
    t2              = params["t2_count"]
    stud_positions  = params.get("stud_positions", [])

    wall_height = args.height

    print(f"Wall length : {L:.0f} mm")
    print(f"Wall height : {wall_height:.0f} mm")
    print(f"T1 studs    : {t1}  (end/corner)")
    print(f"T2 studs    : {t2}  (intermediate)")
    print(f"Cladding    : {args.cladding}")
    if stud_positions:
        xs_str = ", ".join(f"{x:.0f}" for x, _ in stud_positions)
        print(f"Stud X pos  : [{xs_str}] mm from left")

    # ── Compute cutting list ──────────────────────────────────────────────────
    rows = compute_cutting_list(L, t1, t2, cladding=args.cladding,
                                wall_height=wall_height)

    if args.verbose:
        print("\n  COMPONENT               SIZE                  LENGTH       QTY")
        print("  " + "-" * 68)
        for r in rows:
            print(f"  {r.component:<24} {r.size:<22} {r.length:<12} {r.qty} {r.unit}")

    # ── Output DXF ────────────────────────────────────────────────────────────
    out_path = Path(args.output) if args.output else plan_path.with_name(
        plan_path.stem + "_cutting_list.dxf"
    )

    doc = ezdxf.new("R2018", setup="standard")
    setup_layers(doc)

    msp = doc.modelspace()
    panel_id = plan_path.stem.replace("_plan", "").upper()
    write_cutting_table(msp, rows, origin_x=0, origin_y=0, panel_id=panel_id)
    draw_details(msp, L, t1, t2, origin_x=0, origin_y=0, wall_height=wall_height,
                 stud_positions=stud_positions, cladding=args.cladding)

    doc.saveas(out_path)
    print(f"DXF saved  : {out_path}")

    # ── Optional CSV ──────────────────────────────────────────────────────────
    if args.csv:
        csv_path = out_path.with_suffix(".csv")
        write_csv(rows, csv_path)


if __name__ == "__main__":
    main()
