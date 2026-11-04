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
            """
        )
        self.conn.commit()

    def add_reading(self, room: str, metric: str, ts: str, value: float) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO readings(room, metric, ts, value) VALUES (?, ?, ?, ?)",
            (room, metric, ts, value),
        )

    def add_readings(self, rows: list[tuple[str, str, str, float]]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO readings(room, metric, ts, value) VALUES (?, ?, ?, ?)", rows
        )
        self.conn.commit()

    def since(self, room: str, metric: str, since_iso: str) -> list[tuple[str, float]]:
        cur = self.conn.execute(
            "SELECT ts, value FROM readings WHERE room=? AND metric=? AND ts>=? ORDER BY ts",
            (room, metric, since_iso),
        )
        return cur.fetchall()

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]


def hourly_mean(points: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """Aggregate raw (ts, value) points to hourly means, keyed by hour bucket."""
    buckets: dict[str, list[float]] = {}
    for ts, value in points:
        hour = ts[:13] + ":00:00+00:00" if len(ts) >= 13 else ts
        buckets.setdefault(hour, []).append(value)
    return [(h, round(sum(v) / len(v), 3)) for h, v in sorted(buckets.items())]


def heatmap_matrix(points: list[tuple[str, float]], days: int) -> dict:
    """Build a days × hours matrix of mean temperature from (ts, value) points.

    Returns {"days": [iso-date...], "hours": [0..23], "values": [[per-hour...]...]}
    with None where no data exists for a cell.
    """
    grid: dict[str, list[list[float]]] = {}
    for ts, value in points:
        try:
            dt = datetime.fromisoformat(ts)
        except ValueError:
            continue
        key = dt.strftime("%Y-%m-%d")
        grid.setdefault(key, [[] for _ in range(24)])[dt.hour].append(value)
    # Keep only the last `days` dates with data.
    dates = sorted(grid)[-days:]
    values = []
    for d in dates:
        row = []
        for h in range(24):
            cell = grid[d][h]
            row.append(round(sum(cell) / len(cell), 2) if cell else None)
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
