"""SQLite cache for long-term history."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


class Cache:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self._rowcount = 0
        self._agg_cache: dict[tuple, object] = {}
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS readings (
                room TEXT NOT NULL,
                metric TEXT NOT NULL,
                ts TEXT NOT NULL,
                value REAL NOT NULL,
                PRIMARY KEY (room, metric, ts)
            );
            CREATE INDEX IF NOT EXISTS idx_readings_ts ON readings(ts);
            CREATE TABLE IF NOT EXISTS annotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room TEXT NOT NULL,
                ts TEXT NOT NULL,
                label TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_annotations_room_ts ON annotations(room, ts);
            """
        )
        self.conn.commit()
        self._rowcount = self.count()

    def _invalidate(self) -> None:
        """Drop memoized aggregates after any write (rowcount changes too)."""
        self._agg_cache.clear()

    def add_reading(self, room: str, metric: str, ts: str, value: float) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO readings(room, metric, ts, value) VALUES (?, ?, ?, ?)",
            (room, metric, ts, value),
        )
        self._rowcount += 1
        self._invalidate()

    def add_readings(self, rows: list[tuple[str, str, str, float]]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO readings(room, metric, ts, value) VALUES (?, ?, ?, ?)", rows
        )
        self.conn.commit()
        self._rowcount = self.count()
        self._invalidate()

    def since(self, room: str, metric: str, since_iso: str) -> list[tuple[str, float]]:
        cur = self.conn.execute(
            "SELECT ts, value FROM readings WHERE room=? AND metric=? AND ts>=? ORDER BY ts",
            (room, metric, since_iso),
        )
        return cur.fetchall()

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]

    # ----- annotations (user markers on the timeline) -----

    def add_annotation(self, room: str, ts: str, label: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO annotations(room, ts, label) VALUES (?, ?, ?)", (room, ts, label)
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def annotations_since(self, room: str, since_iso: str) -> list[tuple[int, str, str]]:
        """[(id, ts, label)] ordered by timestamp."""
        cur = self.conn.execute(
            "SELECT id, ts, label FROM annotations WHERE room=? AND ts>=? ORDER BY ts",
            (room, since_iso),
        )
        return cur.fetchall()

    def delete_annotation(self, ann_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM annotations WHERE id=?", (ann_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def wipe(self) -> int:
        """Delete ALL readings and annotations (data-safety: UI asks to confirm)."""
        n = self.conn.execute("DELETE FROM readings").rowcount
        self.conn.execute("DELETE FROM annotations")
        self.conn.commit()
        self._rowcount = 0
        self._invalidate()
        return n

    def all_readings(self) -> list[tuple[str, str, str, float]]:
        """Every cached reading (room, metric, ts, value) — full-data export."""
        cur = self.conn.execute(
            "SELECT room, metric, ts, value FROM readings ORDER BY ts, room, metric"
        )
        return cur.fetchall()

    def all_annotations(self) -> list[tuple[int, str, str, str]]:
        """Every annotation (id, room, ts, label) — full-data export."""
        cur = self.conn.execute("SELECT id, room, ts, label FROM annotations ORDER BY id")
        return cur.fetchall()

    # ----- memoized aggregates (hot endpoints: /api/timeline, /api/heatmap) -----

    def hourly_since(self, room: str, metric: str, since_iso: str) -> list[tuple[str, float]]:
        """`hourly_mean(since(...))` memoized per (room, metric, since, rowcount).

        A repeat request within the same hour window reuses the computed
        series instead of re-reading and re-aggregating the raw table.
        Any write bumps rowcount / clears the memo, so results stay fresh.
        """
        key = ("hourly", room, metric, since_iso, self._rowcount)
        cached = self._agg_cache.get(key)
        if cached is None:
            cached = hourly_mean(self.since(room, metric, since_iso))
            self._agg_cache[key] = cached
        return cached

    def heatmap_since(self, room: str, metric: str, since_iso: str, days: int) -> dict:
        """`heatmap_matrix(since(...), days)` memoized like `hourly_since`."""
        key = ("heatmap", room, metric, since_iso, days, self._rowcount)
        cached = self._agg_cache.get(key)
        if cached is None:
            cached = heatmap_matrix(self.since(room, metric, since_iso), days)
            self._agg_cache[key] = cached
        return cached


def hourly_mean(points: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """Aggregate raw (ts, value) points to hourly means, keyed by hour bucket."""
    sums: dict[str, list[float]] = {}  # hour -> [running_sum, count]
    for ts, value in points:
        hour = ts[:13] + ":00:00+00:00" if len(ts) >= 13 else ts
        acc = sums.get(hour)
        if acc is None:
            sums[hour] = [value, 1]
        else:
            acc[0] += value
            acc[1] += 1
    return [(h, round(acc[0] / acc[1], 3)) for h, acc in sorted(sums.items())]


def heatmap_matrix(points: list[tuple[str, float]], days: int) -> dict:
    """Build a days × hours matrix of mean temperature from (ts, value) points.

    Returns {"days": [iso-date...], "hours": [0..23], "values": [[per-hour...]...]}
    with None where no data exists for a cell.
    """
    sums: dict[str, list[list[float]]] = {}  # date -> 24 x [running_sum, count]
    for ts, value in points:
        try:
            dt = datetime.fromisoformat(ts)
        except ValueError:
            continue
        key = dt.strftime("%Y-%m-%d")
        row = sums.get(key)
        if row is None:
            row = sums[key] = [[0.0, 0] for _ in range(24)]
        cell = row[dt.hour]
        cell[0] += value
        cell[1] += 1
    # Keep only the last `days` dates with data.
    dates = sorted(sums)[-days:]
    values = []
    for d in dates:
        row = []
        for acc in sums[d]:
            row.append(round(acc[0] / acc[1], 2) if acc[1] else None)
        values.append(row)
    return {"days": dates, "hours": list(range(24)), "values": values}


def seasonal_means(points: list[tuple[str, float]]) -> dict[str, float | None]:
    """Mean value per year for points that fall in a given month.

    Input points are already filtered to the target month; keys are years.
    """
    per_year: dict[str, list[float]] = {}
    for ts, value in points:
        try:
            dt = datetime.fromisoformat(ts)
        except ValueError:
            continue
        per_year.setdefault(str(dt.year), []).append(value)
    return {y: round(sum(v) / len(v), 2) for y, v in sorted(per_year.items())}


def parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def hours_ago_iso(hours: int, now: datetime | None = None) -> str:
    now = (now or datetime.now(timezone.utc)).replace(minute=0, second=0, microsecond=0)
    return (now - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:00:00+00:00")
