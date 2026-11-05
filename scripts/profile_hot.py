#!/usr/bin/env python3
"""Profile the hot paths of climate-canvas (demo seeding + aggregation).

Usage:
    python scripts/profile_hot.py [--days 90]

Runs cProfile over (1) demo history generation + SQLite seeding and
(2) the /api/heatmap aggregation (90 days x all rooms) and prints the
top functions by cumulative / internal time. Numbers are stable enough
to compare before/after an optimization commit.
"""
from __future__ import annotations

import argparse
import cProfile
import io
import pstats
import tempfile
import time
from pathlib import Path

from app import cache as cache_mod
from app import config, demo_data


def _run(label: str, fn) -> None:
    pr = cProfile.Profile()
    t0 = time.perf_counter()
    pr.enable()
    fn()
    pr.disable()
    dt = time.perf_counter() - t0
    print(f"\n=== {label}: {dt:.3f}s ===")
    for sort in ("cumulative", "tottime"):
        s = io.StringIO()
        pstats.Stats(pr, stream=s).sort_stats(sort).print_stats(8)
        print(s.getvalue())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=demo_data.HOURLY_DAYS)
    args = ap.parse_args()
    rooms = config.load_rooms()
    tmp = Path(tempfile.mkdtemp(prefix="cc-profile-"))

    db = cache_mod.Cache(tmp / "profile.db")
    _run(f"seed_cache({args.days}d x {len(rooms)} rooms)",
         lambda: demo_data.seed_cache(db, rooms, days=args.days))

    db2 = cache_mod.Cache(tmp / "agg.db")
    db2.add_readings([
        (r, "temperature", rd["ts"], rd["value"])
        for r in rooms
        for rd in demo_data.generate_hours(r, hours=args.days * 24)
    ])
    since = cache_mod.hours_ago_iso(args.days * 24)

    def aggregate() -> None:
        for r in rooms:
            pts = db2.since(r, "temperature", since)
            cache_mod.hourly_mean(pts)
            cache_mod.heatmap_matrix(pts, args.days)

    _run(f"aggregation {args.days}d x {len(rooms)} rooms (timeline+heatmap)", aggregate)


if __name__ == "__main__":
    main()
