#!/usr/bin/env python3
"""Benchmark the hot paths: demo seeding + 90-day x all-rooms aggregation.

Usage:
    python scripts/bench.py [--runs 3]

Prints median wall-clock seconds for:
  - seed_cache   (demo generation + SQLite insert, HOURLY_DAYS x rooms)
  - aggregate    (since() + hourly_mean + heatmap_matrix per room)
"""
from __future__ import annotations

import argparse
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo's own app/, not an editable install

from app import cache as cache_mod
from app import config, demo_data


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    args = ap.parse_args()
    rooms = config.load_rooms()
    tmp = Path(tempfile.mkdtemp(prefix="cc-bench-"))

    seed_t, agg_t = [], []
    for i in range(args.runs):
        db = cache_mod.Cache(tmp / f"bench{i}.db")
        t0 = time.perf_counter()
        demo_data.seed_cache(db, rooms, days=demo_data.HOURLY_DAYS)
        seed_t.append(time.perf_counter() - t0)

        since = cache_mod.hours_ago_iso(demo_data.HOURLY_DAYS * 24)
        t0 = time.perf_counter()
        for r in rooms:
            pts = db.since(r, "temperature", since)
            cache_mod.hourly_mean(pts)
            cache_mod.heatmap_matrix(pts, demo_data.HOURLY_DAYS)
        agg_t.append(time.perf_counter() - t0)

    print(f"rooms={len(rooms)} days={demo_data.HOURLY_DAYS} runs={args.runs} (median)")
    print(f"seed_cache : {statistics.median(seed_t):.3f}s  {['%.3f' % t for t in seed_t]}")
    print(f"aggregate  : {statistics.median(agg_t):.3f}s  {['%.3f' % t for t in agg_t]}")


if __name__ == "__main__":
    main()
