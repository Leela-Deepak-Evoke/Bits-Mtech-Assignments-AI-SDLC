"""Local wall-clock -> aware instant with explicit DST gap / overlap handling (DT-12, DT-13)."""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

GAP = "dst_gap_shifted_forward"
OVERLAP = "dst_overlap_first_occurrence"


def local_to_aware(naive: dt.datetime, zone: ZoneInfo) -> tuple[dt.datetime, str | None]:
    """Resolve ``naive`` in ``zone``. Returns (aware datetime, optional DST assumption code).

    * Gap (non-existent local time): shifted forward by the gap length.
    * Overlap (ambiguous local time): the earlier (first) occurrence.
    """
    first = naive.replace(tzinfo=zone, fold=0)
    instant = first.astimezone(dt.timezone.utc)  # noqa: UP017
    back = instant.astimezone(zone)
    if back.replace(tzinfo=None) != naive:
        return back, GAP
    second = naive.replace(tzinfo=zone, fold=1)
    if first.utcoffset() != second.utcoffset():
        return back, OVERLAP
    return back, None
