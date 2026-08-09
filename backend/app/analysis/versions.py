"""Version parsing and comparison (dependency-light, no `packaging` needed)."""
from __future__ import annotations

import re

_NUM_RE = re.compile(r"[0-9]+")

# "Severely outdated" threshold: more than this many major versions behind.
SEVERELY_BEHIND_MAJORS = 2


def parse_version(v: str | None) -> tuple[int, int, int] | None:
    """Return (major, minor, patch) ignoring pre-release/build suffixes."""
    if not v:
        return None
    # Strip a leading 'v' and any range operators.
    v = v.strip().lstrip("v=^~<>! ")
    # Take the numeric dotted head (stop at first non [0-9.] char).
    head = re.match(r"[0-9]+(?:\.[0-9]+)*", v)
    if not head:
        return None
    parts = [int(p) for p in head.group(0).split(".")[:3]]
    while len(parts) < 3:
        parts.append(0)
    return parts[0], parts[1], parts[2]


def compare(a: str | None, b: str | None) -> int:
    """Return -1 if a<b, 0 if equal/uncomparable, 1 if a>b."""
    pa, pb = parse_version(a), parse_version(b)
    if pa is None or pb is None:
        return 0
    return (pa > pb) - (pa < pb)


def versions_behind(current: str | None, latest: str | None) -> int:
    """Major versions between current and latest (0 if unknown or up to date)."""
    pc, pl = parse_version(current), parse_version(latest)
    if pc is None or pl is None:
        return 0
    return max(0, pl[0] - pc[0])


def is_outdated(current: str | None, latest: str | None) -> bool:
    return compare(current, latest) < 0


def is_severely_outdated(current: str | None, latest: str | None) -> bool:
    return versions_behind(current, latest) > SEVERELY_BEHIND_MAJORS
