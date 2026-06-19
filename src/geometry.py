import math
from typing import Tuple

Point = Tuple[float, float]


def add(a: Point, b: Point) -> Point:
    return (a[0] + b[0], a[1] + b[1])


def sub(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1])


def scale(v: Point, s: float) -> Point:
    return (v[0] * s, v[1] * s)


def length(v: Point) -> float:
    return math.sqrt(v[0] ** 2 + v[1] ** 2)


def normalize(v: Point) -> Point:
    l = length(v)
    return (v[0] / l, v[1] / l) if l > 1e-9 else (1.0, 0.0)


def dist(a: Point, b: Point) -> float:
    return length(sub(b, a))


def perp_left(v: Point) -> Point:
    """90° CCW of v (left-hand normal when facing direction v)."""
    return (-v[1], v[0])


def perp_right(v: Point) -> Point:
    """90° CW of v (right-hand normal when facing direction v)."""
    return (v[1], -v[0])


def angle_deg(v: Point) -> float:
    return math.degrees(math.atan2(v[1], v[0]))


def along(start: Point, end: Point, t: float) -> Point:
    """Point at distance t from start along start→end."""
    d = normalize(sub(end, start))
    return add(start, scale(d, t))


def midpoint(a: Point, b: Point) -> Point:
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def offset_point(start: Point, end: Point, t: float, n: float) -> Point:
    """Point at parameter t along wall, offset n perpendicular (left = positive)."""
    d = normalize(sub(end, start))
    nl = perp_left(d)
    return add(add(start, scale(d, t)), scale(nl, n))


def wall_rect(start: Point, end: Point, thickness: float) -> list:
    """Four corners of wall rectangle as list of (x,y), starting at bottom-left going CCW."""
    d = normalize(sub(end, start))
    nl = perp_left(d)
    L = dist(start, end)
    p0 = start
    p1 = add(start, scale(d, L))
    p2 = add(p1, scale(nl, thickness))
    p3 = add(p0, scale(nl, thickness))
    return [p0, p1, p2, p3]
