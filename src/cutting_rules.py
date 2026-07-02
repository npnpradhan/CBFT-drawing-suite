"""
CBFT wall cutting list rules.
Given wall parameters (length, stud counts, cladding type), compute every
component's size, length, and quantity.
"""

import math
from dataclasses import dataclass

# ── Standard CBFT dimensions (mm) ────────────────────────────────────────────
PLATE_THICKNESS    = 38     # timber plate thickness
PLATE_WIDTH        = 88     # timber plate face width (nominal 38×88 = 2×4)
STUD_DIAMETER      = 100    # bamboo stud nominal diameter
STUD_HEIGHT        = 2024   # clear stud height between plates
WALL_HEIGHT_TOTAL  = STUD_HEIGHT + 2 * PLATE_THICKNESS   # 2100 mm
FLATBAR_W          = 25     # flat bar width (mm)
FLATBAR_T          = 3      # flat bar thickness (mm)
ROD_10_LENGTH      = 150    # 10mm threaded rod length (mm)
TADTAD_STRIP_W     = 300    # flattened bamboo strip width (one row)
RIBLATH_STRIP_W    = 600    # expanded metal lath strip width
FLATBAR_H_TRIM     = 50     # horizontal clearance at each wall end (total)
FLATBAR_V_TRIM     = 38     # vertical clearance (= one plate thickness)
FLATBAR_EXTRA      = 30     # connection lapping allowance

# ── Per-stud connection hardware ──────────────────────────────────────────────
# T1 (bps1) studs connect to BOTH timber plates with 12 mm hardware:
#   bottom plate: 1× J-bolt (cast into slab/foundation)
#   top plate:    1× straight threaded rod
#   Nuts and washers cover all connections — 1 per bolt/rod end plus 1 lock nut.
T1_JBOLT_EA   = 1   # J-bolt per T1 stud
T1_STROD_EA   = 1   # straight threaded rod per T1 stud
T1_NUTS12_EA  = 3   # 12 mm nuts per T1 stud  (J-bolt top + J-bolt bot + rod)
T1_WASH12_EA  = 3   # 12 mm washers per T1 stud

# T2 (bpns1) studs are intermediate — held in-plane by the flat-bar X-brace.
# They do NOT require 12 mm plate-connection hardware.


@dataclass
class CuttingRow:
    component: str
    size:      str
    length:    str            # formatted string, "-" if not applicable
    qty:       int
    unit:      str = "PC"

    def as_dict(self) -> dict:
        return {
            "component": self.component,
            "size":      self.size,
            "length":    self.length,
            "qty":       self.qty,
            "unit":      self.unit,
        }


def _flatbar_length(wall_length: float, wall_height: float = WALL_HEIGHT_TOTAL) -> int:
    """Diagonal X-brace length for a given wall length (mm)."""
    h = wall_length - FLATBAR_H_TRIM
    v = wall_height - FLATBAR_V_TRIM
    return round(math.sqrt(h**2 + v**2) + FLATBAR_EXTRA)


def _rod_10_count(t1: int, t2: int) -> int:
    """
    10 mm threaded rod count (flat-bar X-brace pin connections).

    Each stud needs 2 rods (one per diagonal flat bar).
    Exception: for even-T1 panels, paired end studs share one rod at the
    X-brace crossing, reducing the count by T1//2.

    Verified:
      1200A (T1=2, T2=1) → 5  |  1500A (T1=3, T2=1) → 8  |
      1500B (T1=4, T2=1) → 8
    """
    base    = 2 * (t1 + t2)
    sharing = (t1 // 2) if (t1 % 2 == 0) else 0
    return base - sharing


def _riblath_count(t1: int) -> int:
    """
    RIBLATH strip count for double-cladded panels.

    Formula validated against reference panels:
      T1=3 → 5 PC  |  T1=4 → 10 PC
    For T1=2 double-cladded, defaults to 5 PC (same as T1=3).
    """
    return 5 * max(1, t1 - 2)


def compute_cutting_list(wall_length: float,
                         t1_count:    int,
                         t2_count:    int,
                         cladding:    str   = "single",
                         wall_height: float = WALL_HEIGHT_TOTAL) -> list:
    """
    Compute CBFT wall cutting list.

    Parameters
    ----------
    wall_length : total wall plan length (mm)
    t1_count    : end / corner bamboo studs (bps1 in plan DXF)
    t2_count    : intermediate bamboo studs (bpns1 in plan DXF)
    cladding    : "single" -> TADTAD infill matrix (default)
                  "double" -> RIBLATH infill matrix
    wall_height : total wall height incl. plates (default 2100 mm)

    Returns
    -------
    List of CuttingRow objects.
    """
    L           = wall_length
    stud_height = wall_height - 2 * PLATE_THICKNESS
    fb          = _flatbar_length(L, wall_height)

    # ── 10 mm flat-bar rods (all studs contribute) ────────────────────────────
    rod_10 = _rod_10_count(t1_count, t2_count)

    # ── 12 mm plate-connection hardware (T1 studs only) ──────────────────────
    jbolt_count    = t1_count * T1_JBOLT_EA
    strod_count    = t1_count * T1_STROD_EA
    nuts_12_count  = t1_count * T1_NUTS12_EA
    wash_12_count  = t1_count * T1_WASH12_EA

    # ── Structural components ─────────────────────────────────────────────────
    rows = [
        CuttingRow("TOP TIMBER PLATE",  "38X88 MM",                f"{L:.0f} MM",         1),
        CuttingRow("BOT. TIMBER PLATE", "38X88 MM",                f"{L:.0f} MM",         1),
        CuttingRow("T1 BAMBOO STUD",    "100MM ∅",            f"{stud_height:.0f} MM",   t1_count),
    ]
    if t2_count > 0:
        rows.append(
            CuttingRow("T2 BAMBOO STUD", "100MM ∅",           f"{stud_height:.0f} MM",   t2_count)
        )

    rows += [
        CuttingRow("FLAT BAR",          f"{FLATBAR_W}x{FLATBAR_T}MM THK.", f"{fb} MM",        2),
        # ── 10 mm flat-bar hardware (all studs) ──────────────────────────────
        CuttingRow("THREADED ROD",      "10MM ∅",              f"{ROD_10_LENGTH} MM", rod_10),
        CuttingRow("NUTS",              "10MM ∅",              "-",                   2 * rod_10),
        CuttingRow("WASHER",            "2.1MM THK. X 25MM∅",  "-",                   2 * rod_10),
        # ── 12 mm plate-connection hardware (T1 studs only) ──────────────────
        CuttingRow("THREADED J-BOLT",   "12MM ∅",              "-",                   jbolt_count),
        CuttingRow("STR. THREADED ROD", "12MM ∅",              "-",                   strod_count),
        CuttingRow("NUTS",              "12MM ∅",              "-",                   nuts_12_count),
        CuttingRow("WASHER",            "2.8MM THK. X 35MM∅",  "-",                   wash_12_count),
    ]

    # ── Infill matrix (user cladding choice) ──────────────────────────────────
    if cladding == "double":
        rows.append(
            CuttingRow("RIBLATH", f"600 X {L:.0f} MM", "-", _riblath_count(t1_count))
        )
    else:   # "single" — default
        tadtad_count = math.ceil(wall_height / TADTAD_STRIP_W)
        rows.append(
            CuttingRow("TADTAD", f"300x{L:.0f} MM", "-", tadtad_count)
        )

    return rows
