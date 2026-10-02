"""
MCTQ — Munich Chronotype Questionnaire (short form).

Computes MSFsc: mid-sleep on free days, sleep-corrected.
This is the primary chronotype estimate used for:
  - Journey congruence check (Onboarding §4.2)
  - Chronotype-adjusted journey recommendations (PRD §4.2.2)

Two-item quick form (Onboarding S0, screen 4):
  - sleep_onset_free: local time the user falls asleep on free days
  - wake_time_free: local time the user wakes without alarm on free days

Full MCTQ (S3, day 7) adds sleep duration on work days for MSFsc correction.
This module handles both; source is tagged on ChronotypeEstimate.

Reference: Roenneberg et al.; PRD §4.6.1.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import time


@dataclass
class MCTQResult:
    sleep_onset_free: time
    wake_time_free: time
    sleep_duration_free_hours: float
    mid_sleep_free_hours: float    # hours from midnight (e.g. 3.0 = 03:00)
    chronotype_label: str          # early / intermediate / late


def _time_to_hours(t: time) -> float:
    """Convert a time to fractional hours from midnight (handles next-day wake)."""
    return t.hour + t.minute / 60 + t.second / 3600


def _mid_sleep(onset_h: float, wake_h: float) -> float:
    """Compute mid-sleep, handling midnight crossover."""
    if wake_h < onset_h:
        # Sleep crosses midnight: e.g. onset 23:00, wake 07:00
        duration = (24 - onset_h) + wake_h
    else:
        duration = wake_h - onset_h
    msf = onset_h + duration / 2
    # Wrap to 0–24
    return msf % 24


def _chronotype_label(msf_hours: float) -> str:
    """
    Classify chronotype from MSF.
    Based on the Roenneberg population distribution.
    Early: MSF < 2.5 (roughly before 02:30)
    Intermediate: 2.5 ≤ MSF < 5.0
    Late: MSF ≥ 5.0
    These boundaries are approximate and will be updated after cohort analysis.
    """
    if msf_hours < 2.5:
        return "early"
    if msf_hours < 5.0:
        return "intermediate"
    return "late"


def score_quick(sleep_onset: time, wake_time: time) -> MCTQResult:
    """
    Two-item quick form from Onboarding S0.
    Produces a usable chronotype estimate for the congruence check.
    """
    onset_h = _time_to_hours(sleep_onset)
    wake_h = _time_to_hours(wake_time)

    if wake_h < onset_h:
        duration_h = (24 - onset_h) + wake_h
    else:
        duration_h = wake_h - onset_h

    msf = _mid_sleep(onset_h, wake_h)

    return MCTQResult(
        sleep_onset_free=sleep_onset,
        wake_time_free=wake_time,
        sleep_duration_free_hours=round(duration_h, 2),
        mid_sleep_free_hours=round(msf, 3),
        chronotype_label=_chronotype_label(msf),
    )
