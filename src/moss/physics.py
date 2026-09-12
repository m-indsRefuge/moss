"""Moss's genome - every tunable constant and every state mutation.

Tuning the pet means editing this file and nothing else. All functions
are PURE: (state, ...) -> new state. No I/O, no clock access (the
architecture tripwire enforces that).

Division of labor:
- decay():         time passing (hunger rises, energy drains)
- apply_action():  the consequence of a Decision - drives and stats
                   ONLY. Mood, diary and wish are the brain's
                   expression channel and are never written here.
- policy.py refuses the SITUATIONALLY illegal (thresholds, night);
  this module refuses the NONSENSICAL (eating from an empty bowl,
  unknown actions). Belt and suspenders.
"""
from __future__ import annotations

import copy
from datetime import timedelta
from typing import Any

# -- metabolism, per elapsed hour ---------------------------------
HUNGER_RATE = 0.04       # 0 -> 1.0 in ~24h of neglect
ENERGY_RATE = 0.002      # awake drain

# -- action economics ---------------------------------------------
SATIETY_PER_COMMIT = 0.2   # each eaten commit soothes this much hunger
SLEEP_RESTORES_TO = 0.85   # a nap tops up to here, not to 1.0
PLAY_ENERGY_COST = 0.15

# -- reflex thresholds (the fallback policy reads these) ----------
EAT_WHEN_HUNGRIER_THAN = 0.60
FULL_STOMACH = 0.15        # eating above this is waste - and illegal
TIRED_BELOW = 0.35
MIN_PLAY_ENERGY = 0.30     # play must never floor energy at zero
RESTLESS_ABOVE = 0.55      # bored + energetic -> play
SULK_AFTER_QUIET_HOURS = 36.0
NIGHT_UTC_START, NIGHT_UTC_END = 22, 7    # night = [22:00, 07:00) UTC


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def is_night(hour_utc: int) -> bool:
    """The night window wraps midnight - hence the awkward branch."""
    if NIGHT_UTC_START > NIGHT_UTC_END:
        return hour_utc >= NIGHT_UTC_START or hour_utc < NIGHT_UTC_END
    return NIGHT_UTC_START <= hour_utc < NIGHT_UTC_END


def decay(state: dict[str, Any], elapsed: timedelta) -> dict[str, Any]:
    """Hunger rises, energy falls. Negative elapsed is ignored, not
    punished - Moss should not starve because of our clock bugs."""
    if elapsed.total_seconds() < 0:
        elapsed = timedelta(0)
    hours = elapsed.total_seconds() / 3600.0
    new = copy.deepcopy(state)
    new["drives"]["hunger"] = _clamp01(new["drives"]["hunger"] + HUNGER_RATE * hours)
    new["drives"]["energy"] = _clamp01(new["drives"]["energy"] - ENERGY_RATE * hours)
    return new


def fill_bowl(state: dict[str, Any], new_commits: int) -> dict[str, Any]:
    """Commits arrived this tick; they land in the bowl and WAIT."""
    new = copy.deepcopy(state)
    new["bowl"]["commits"] += max(0, int(new_commits))
    return new


def _eat(state: dict[str, Any]) -> dict[str, Any]:
    n = state["bowl"]["commits"]
    if n <= 0:
        raise ValueError("eat with an empty bowl - policy should have vetoed this")
    new = copy.deepcopy(state)
    new["drives"]["hunger"] = _clamp01(
        new["drives"]["hunger"] - SATIETY_PER_COMMIT * n
    )
    new["bowl"]["commits"] = 0
    new["stats"]["commits_eaten"] += n
    return new


def _sleep(state: dict[str, Any]) -> dict[str, Any]:
    new = copy.deepcopy(state)
    new["drives"]["energy"] = max(new["drives"]["energy"], SLEEP_RESTORES_TO)
    return new


def _play(state: dict[str, Any]) -> dict[str, Any]:
    new = copy.deepcopy(state)
    new["drives"]["energy"] = _clamp01(new["drives"]["energy"] - PLAY_ENERGY_COST)
    return new


def _sulk(state: dict[str, Any]) -> dict[str, Any]:
    new = copy.deepcopy(state)
    new["stats"]["sulks"] += 1
    return new


_APPLY = {"eat": _eat, "sleep": _sleep, "play": _play, "sulk": _sulk}


def apply_action(state: dict[str, Any], action: str) -> dict[str, Any]:
    if action not in _APPLY:
        raise ValueError(f"unknown action {action!r}")
    return _APPLY[action](state)