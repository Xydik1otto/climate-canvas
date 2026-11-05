"""Psychrometric helpers: dew point (Magnus formula) and mold risk index.

Pure functions, no I/O — unit-tested against known reference values.
"""
from __future__ import annotations

import math

# Magnus-Tetens coefficients (valid for -40..+50 °C over water).
_MAGNUS_A = 17.62
_MAGNUS_B = 243.12

RISK_LEVEL = {"low": 0, "medium": 1, "high": 2}


def dew_point(t_celsius: float, rh_percent: float) -> float:
    """Dew point (°C) from air temperature and relative humidity (Magnus formula).

    gamma(T, RH) = ln(RH/100) + a*T / (b + T);  dew = b*gamma / (a - gamma)
    """
    if not 0.0 < rh_percent <= 100.0:
        raise ValueError("relative humidity must be within (0, 100]")
    gamma = math.log(rh_percent / 100.0) + (_MAGNUS_A * t_celsius) / (_MAGNUS_B + t_celsius)
    return round((_MAGNUS_B * gamma) / (_MAGNUS_A - gamma), 2)


def mold_risk(t_celsius: float, rh_percent: float) -> str:
    """Qualitative mold/condensation risk: 'low' | 'medium' | 'high'.

    high:   RH >= 70 % at T < 20 °C — classic condensation-on-cold-surface zone.
    medium: RH >= 65 % (approaching the danger zone).
    low:    everything else.
    """
    if rh_percent >= 70.0 and t_celsius < 20.0:
        return "high"
    if rh_percent >= 65.0:
        return "medium"
    return "low"
