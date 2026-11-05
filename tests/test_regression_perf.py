"""Regression pins: endpoints/aggregators must return the SAME numbers after
the performance optimization (captured from pre-optimization v1.0.0 code)."""
from datetime import datetime, timezone

from app import cache as cache_mod
from app.demo_data import generate_hours, hour_value, outdoor_hour

# room|iso-ts|metric -> golden value (pre-optimization output, byte-exact)
GOLDEN = {
        "Living Room|2025-01-15T00:00:00+00:00|temperature": 14.8,
        "Living Room|2025-01-15T00:00:00+00:00|humidity": 83.43,
        "Living Room|2025-01-15T00:00:00+00:00|energy": 0.732,
        "Living Room|2025-01-15T00:00:00+00:00|co2": 465.7,
        "Living Room|2025-01-15T00:00:00+00:00|voc": 120.6,
        "Living Room|2025-01-15T09:00:00+00:00|temperature": 16.57,
        "Living Room|2025-01-15T09:00:00+00:00|humidity": 79.19,
        "Living Room|2025-01-15T09:00:00+00:00|energy": 0.732,
        "Living Room|2025-01-15T09:00:00+00:00|co2": 465.7,
        "Living Room|2025-01-15T09:00:00+00:00|voc": 120.6,
        "Living Room|2025-01-15T15:00:00+00:00|temperature": 19.07,
        "Living Room|2025-01-15T15:00:00+00:00|humidity": 73.19,
        "Living Room|2025-01-15T15:00:00+00:00|energy": 0.732,
        "Living Room|2025-01-15T15:00:00+00:00|co2": 465.7,
        "Living Room|2025-01-15T15:00:00+00:00|voc": 120.6,
        "Living Room|2025-01-15T21:00:00+00:00|temperature": 16.57,
        "Living Room|2025-01-15T21:00:00+00:00|humidity": 79.19,
        "Living Room|2025-01-15T21:00:00+00:00|energy": 1.632,
        "Living Room|2025-01-15T21:00:00+00:00|co2": 815.7,
        "Living Room|2025-01-15T21:00:00+00:00|voc": 180.6,
        "Living Room|2025-07-20T14:00:00+00:00|temperature": 26.53,
        "Living Room|2025-07-20T14:00:00+00:00|humidity": 74.71,
        "Living Room|2025-07-20T14:00:00+00:00|energy": 0.285,
        "Living Room|2025-07-20T14:00:00+00:00|co2": 462.8,
        "Living Room|2025-07-20T14:00:00+00:00|voc": 120.1,
        "Bedroom|2025-01-15T00:00:00+00:00|temperature": 15.81,
        "Bedroom|2025-01-15T00:00:00+00:00|humidity": 85.95,
        "Bedroom|2025-01-15T00:00:00+00:00|energy": 0.618,
        "Bedroom|2025-01-15T00:00:00+00:00|co2": 442.5,
        "Bedroom|2025-01-15T00:00:00+00:00|voc": 112.5,
        "Bedroom|2025-01-15T09:00:00+00:00|temperature": 17.58,
        "Bedroom|2025-01-15T09:00:00+00:00|humidity": 81.7,
        "Bedroom|2025-01-15T09:00:00+00:00|energy": 0.618,
        "Bedroom|2025-01-15T09:00:00+00:00|co2": 442.5,
        "Bedroom|2025-01-15T09:00:00+00:00|voc": 112.5,
        "Bedroom|2025-01-15T15:00:00+00:00|temperature": 20.08,
        "Bedroom|2025-01-15T15:00:00+00:00|humidity": 75.7,
        "Bedroom|2025-01-15T15:00:00+00:00|energy": 0.618,
        "Bedroom|2025-01-15T15:00:00+00:00|co2": 442.5,
        "Bedroom|2025-01-15T15:00:00+00:00|voc": 112.5,
        "Bedroom|2025-01-15T21:00:00+00:00|temperature": 17.58,
        "Bedroom|2025-01-15T21:00:00+00:00|humidity": 81.7,
        "Bedroom|2025-01-15T21:00:00+00:00|energy": 1.518,
        "Bedroom|2025-01-15T21:00:00+00:00|co2": 792.5,
        "Bedroom|2025-01-15T21:00:00+00:00|voc": 172.5,
        "Bedroom|2025-07-20T14:00:00+00:00|temperature": 28.67,
        "Bedroom|2025-07-20T14:00:00+00:00|humidity": 78.68,
        "Bedroom|2025-07-20T14:00:00+00:00|energy": 0.313,
        "Bedroom|2025-07-20T14:00:00+00:00|co2": 454.1,
        "Bedroom|2025-07-20T14:00:00+00:00|voc": 124.7,
        "Kitchen|2025-01-15T00:00:00+00:00|temperature": 16.51,
        "Kitchen|2025-01-15T00:00:00+00:00|humidity": 83.79,
        "Kitchen|2025-01-15T00:00:00+00:00|energy": 0.586,
        "Kitchen|2025-01-15T00:00:00+00:00|co2": 468.7,
        "Kitchen|2025-01-15T00:00:00+00:00|voc": 117.2,
        "Kitchen|2025-01-15T09:00:00+00:00|temperature": 18.28,
        "Kitchen|2025-01-15T09:00:00+00:00|humidity": 79.55,
        "Kitchen|2025-01-15T09:00:00+00:00|energy": 0.586,
        "Kitchen|2025-01-15T09:00:00+00:00|co2": 468.7,
        "Kitchen|2025-01-15T09:00:00+00:00|voc": 117.2,
        "Kitchen|2025-01-15T15:00:00+00:00|temperature": 20.78,
        "Kitchen|2025-01-15T15:00:00+00:00|humidity": 73.55,
        "Kitchen|2025-01-15T15:00:00+00:00|energy": 0.586,
        "Kitchen|2025-01-15T15:00:00+00:00|co2": 468.7,
        "Kitchen|2025-01-15T15:00:00+00:00|voc": 117.2,
        "Kitchen|2025-01-15T21:00:00+00:00|temperature": 18.28,
        "Kitchen|2025-01-15T21:00:00+00:00|humidity": 79.55,
        "Kitchen|2025-01-15T21:00:00+00:00|energy": 1.486,
        "Kitchen|2025-01-15T21:00:00+00:00|co2": 818.7,
        "Kitchen|2025-01-15T21:00:00+00:00|voc": 177.2,
        "Kitchen|2025-07-20T14:00:00+00:00|temperature": 28.16,
        "Kitchen|2025-07-20T14:00:00+00:00|humidity": 76.59,
        "Kitchen|2025-07-20T14:00:00+00:00|energy": 0.306,
        "Kitchen|2025-07-20T14:00:00+00:00|co2": 414.8,
        "Kitchen|2025-07-20T14:00:00+00:00|voc": 117.2,
        "Office|2025-01-15T00:00:00+00:00|temperature": 16.14,
        "Office|2025-01-15T00:00:00+00:00|humidity": 85.02,
        "Office|2025-01-15T00:00:00+00:00|energy": 0.671,
        "Office|2025-01-15T00:00:00+00:00|co2": 473.5,
        "Office|2025-01-15T00:00:00+00:00|voc": 121.9,
        "Office|2025-01-15T09:00:00+00:00|temperature": 17.91,
        "Office|2025-01-15T09:00:00+00:00|humidity": 80.77,
        "Office|2025-01-15T09:00:00+00:00|energy": 0.671,
        "Office|2025-01-15T09:00:00+00:00|co2": 473.5,
        "Office|2025-01-15T09:00:00+00:00|voc": 121.9,
        "Office|2025-01-15T15:00:00+00:00|temperature": 20.41,
        "Office|2025-01-15T15:00:00+00:00|humidity": 74.77,
        "Office|2025-01-15T15:00:00+00:00|energy": 0.671,
        "Office|2025-01-15T15:00:00+00:00|co2": 473.5,
        "Office|2025-01-15T15:00:00+00:00|voc": 121.9,
        "Office|2025-01-15T21:00:00+00:00|temperature": 17.91,
        "Office|2025-01-15T21:00:00+00:00|humidity": 80.77,
        "Office|2025-01-15T21:00:00+00:00|energy": 1.571,
        "Office|2025-01-15T21:00:00+00:00|co2": 823.5,
        "Office|2025-01-15T21:00:00+00:00|voc": 181.9,
        "Office|2025-07-20T14:00:00+00:00|temperature": 28.13,
        "Office|2025-07-20T14:00:00+00:00|humidity": 74.72,
        "Office|2025-07-20T14:00:00+00:00|energy": 0.339,
        "Office|2025-07-20T14:00:00+00:00|co2": 430.6,
        "Office|2025-07-20T14:00:00+00:00|voc": 117.5,
        "Ω-test|2025-01-15T00:00:00+00:00|temperature": 15.7,
        "Ω-test|2025-01-15T00:00:00+00:00|humidity": 81.89,
        "Ω-test|2025-01-15T00:00:00+00:00|energy": 0.779,
        "Ω-test|2025-01-15T00:00:00+00:00|co2": 425.7,
        "Ω-test|2025-01-15T00:00:00+00:00|voc": 116.4,
        "Ω-test|2025-01-15T09:00:00+00:00|temperature": 17.47,
        "Ω-test|2025-01-15T09:00:00+00:00|humidity": 77.65,
        "Ω-test|2025-01-15T09:00:00+00:00|energy": 0.779,
        "Ω-test|2025-01-15T09:00:00+00:00|co2": 425.7,
        "Ω-test|2025-01-15T09:00:00+00:00|voc": 116.4,
        "Ω-test|2025-01-15T15:00:00+00:00|temperature": 19.97,
        "Ω-test|2025-01-15T15:00:00+00:00|humidity": 71.65,
        "Ω-test|2025-01-15T15:00:00+00:00|energy": 0.779,
        "Ω-test|2025-01-15T15:00:00+00:00|co2": 425.7,
        "Ω-test|2025-01-15T15:00:00+00:00|voc": 116.4,
        "Ω-test|2025-01-15T21:00:00+00:00|temperature": 17.47,
        "Ω-test|2025-01-15T21:00:00+00:00|humidity": 77.65,
        "Ω-test|2025-01-15T21:00:00+00:00|energy": 1.679,
        "Ω-test|2025-01-15T21:00:00+00:00|co2": 775.7,
        "Ω-test|2025-01-15T21:00:00+00:00|voc": 176.4,
        "Ω-test|2025-07-20T14:00:00+00:00|temperature": 27.68,
        "Ω-test|2025-07-20T14:00:00+00:00|humidity": 69.55,
        "Ω-test|2025-07-20T14:00:00+00:00|energy": 0.242,
        "Ω-test|2025-07-20T14:00:00+00:00|co2": 414.3,
        "Ω-test|2025-07-20T14:00:00+00:00|voc": 104.7
    }

GOLDEN_UNPACKED = {
    "_generate_first5": [
        [
            "2025-05-30T12:00:00+00:00",
            "temperature",
            26.64
        ],
        [
            "2025-05-30T12:00:00+00:00",
            "humidity",
            78.71
        ],
        [
            "2025-05-30T12:00:00+00:00",
            "energy",
            0.386
        ],
        [
            "2025-05-30T12:00:00+00:00",
            "co2",
            439.2
        ],
        [
            "2025-05-30T12:00:00+00:00",
            "voc",
            95.6
        ]
    ],
    "_generate_last2": [
        [
            "2025-06-01T11:00:00+00:00",
            "co2",
            430.9
        ],
        [
            "2025-06-01T11:00:00+00:00",
            "voc",
            104.4
        ]
    ],
    "_generate_outdoor": 6.21,
    "_hourly_mean": [
        [
            "2025-03-01T00:00:00+00:00",
            20.7
        ],
        [
            "2025-03-01T01:00:00+00:00",
            19.7
        ],
        [
            "2025-03-02T13:00:00+00:00",
            25.75
        ],
        [
            "bad-ts",
            1.0
        ]
    ],
    "_heatmap": {
        "days": [
            "2025-03-01",
            "2025-03-02"
        ],
        "hours": [
            0,
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            11,
            12,
            13,
            14,
            15,
            16,
            17,
            18,
            19,
            20,
            21,
            22,
            23
        ],
        "values": [
            [
                20.7,
                19.7,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None
            ],
            [
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                25.75,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None
            ]
        ]
    },
    "_seasonal": {
        "2025": 22.52
    }
}

def test_hour_value_unchanged():
    for key, expected in GOLDEN.items():
        room, ts_iso, metric = key.split("|", 2)
        ts = datetime.fromisoformat(ts_iso)
        assert hour_value(room, ts, metric) == expected, key


def test_generate_hours_unchanged():
    end = datetime(2025, 6, 1, 12, tzinfo=timezone.utc)
    rows = generate_hours("Bedroom", hours=48, end=end)
    got_first = [(r["ts"], r["metric"], r["value"]) for r in rows[:5]]
    got_last = [(r["ts"], r["metric"], r["value"]) for r in rows[-2:]]
    assert got_first == [tuple(x) for x in GOLDEN_UNPACKED["_generate_first5"]]
    assert got_last == [tuple(x) for x in GOLDEN_UNPACKED["_generate_last2"]]


def test_outdoor_hour_unchanged():
    assert outdoor_hour(datetime(2025, 2, 3, 18, tzinfo=timezone.utc)) == GOLDEN_UNPACKED["_generate_outdoor"]


POINTS = [
    ("2025-03-01T00:05:00+00:00", 20.1),
    ("2025-03-01T00:45:00+00:00", 21.3),
    ("2025-03-01T01:10:00+00:00", 19.7),
    ("2025-03-02T13:00:00+00:00", 25.4),
    ("2025-03-02T13:30:00+00:00", 26.1),
    ("bad-ts", 1.0),
]


def test_hourly_mean_unchanged():
    assert cache_mod.hourly_mean(POINTS) == [tuple(x) for x in GOLDEN_UNPACKED["_hourly_mean"]]


def test_heatmap_matrix_unchanged():
    assert cache_mod.heatmap_matrix(POINTS, days=7) == GOLDEN_UNPACKED["_heatmap"]


def test_seasonal_means_unchanged():
    assert cache_mod.seasonal_means(POINTS) == GOLDEN_UNPACKED["_seasonal"]


def test_aggregate_memo_hit_and_invalidation(tmp_path):
    from app.cache import Cache
    db = Cache(tmp_path / "c.db")
    db.add_readings([("R", "temperature", "2025-03-01T0%d:00:00+00:00" % h, 20.0 + h) for h in range(3)])
    since = "2025-01-01T00:00:00+00:00"
    a = db.hourly_since("R", "temperature", since)
    b = db.hourly_since("R", "temperature", since)
    assert a == b == [("2025-03-01T00:00:00+00:00", 20.0), ("2025-03-01T01:00:00+00:00", 21.0), ("2025-03-01T02:00:00+00:00", 22.0)]
    hm = db.heatmap_since("R", "temperature", since, 7)
    assert hm == db.heatmap_since("R", "temperature", since, 7)
    # any write invalidates the memo (rowcount changes)
    db.add_reading("R", "temperature", "2025-03-01T03:00:00+00:00", 99.0)
    assert db.hourly_since("R", "temperature", since)[-1] == ("2025-03-01T03:00:00+00:00", 99.0)
