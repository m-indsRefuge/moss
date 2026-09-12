"""The brain file.

Moss is a stateless process; everything it IS lives in one JSON file.
This module owns that file: hatch, validate, migrate, save (atomically),
load (loudly). No other module touches the brain on disk.

Guarantees:
- Readers never see a half-written brain (tmp + fsync + os.replace).
- A corrupt brain raises CorruptStateError. We NEVER silently reset -
  a silent reset is how you lose a pet without noticing.
"""
from __future__ import annotations

import copy
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = 1
DIARY_LIMIT = 12


class StateError(ValueError):
    """The brain on disk violates the schema."""


class CorruptStateError(StateError):
    """The brain on disk is unreadable or from an incompatible version."""


def new_state(name: str, now: datetime) -> dict[str, Any]:
    """A freshly hatched Moss. Valid by construction."""
    return {
        "v": SCHEMA_VERSION,
        "name": name,
        "drives": {"hunger": 0.35, "energy": 0.90},
        "bowl": {"commits": 0},
        "mood": "content",
        "last_tick": now.isoformat(),
        "stats": {"commits_eaten": 0, "sulks": 0, "longest_neglect_days": 0},
        "diary": [],
        "wish": None,
    }


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise StateError(msg)


def parse_ts(value: Any) -> datetime:
    """Parse an ISO timestamp. Timezone-aware or bust."""
    if not isinstance(value, str):
        raise StateError(f"timestamp must be a string, got {type(value).__name__}")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))  # 3.10 Z-shim
    except ValueError as e:
        raise StateError(f"unparseable timestamp {value!r}") from e
    if dt.tzinfo is None:
        raise StateError(f"timestamp must be timezone-aware, got {value!r}")
    return dt


def validate(state: Any) -> None:
    """Raise StateError unless this is a well-formed brain.

    Drives are constrained to physics; mood is FREE expression (the
    brain chooses it) - capped for length only, never content.
    """
    _require(isinstance(state, dict), "state must be a dict")
    _require(state.get("v") == SCHEMA_VERSION,
             f"unsupported schema version {state.get('v')!r} (expected {SCHEMA_VERSION})")
    _require(isinstance(state.get("name"), str) and state["name"],
             "name must be a non-empty string")

    d = state.get("drives")
    _require(isinstance(d, dict), "drives must be a dict")
    for k in ("hunger", "energy"):
        v = d.get(k)
        _require(isinstance(v, (int, float)) and not isinstance(v, bool),
                 f"drive {k!r} must be a number, got {v!r}")
        _require(0.0 <= v <= 1.0, f"drive {k!r} out of range [0, 1]: {v!r}")

    bowl = state.get("bowl")
    _require(isinstance(bowl, dict), "bowl must be a dict")
    bc = bowl.get("commits")
    _require(isinstance(bc, int) and not isinstance(bc, bool) and bc >= 0,
             f"bowl commits must be a non-negative int, got {bc!r}")

    mood = state.get("mood")
    _require(isinstance(mood, str) and 0 < len(mood) <= 80,
             "mood must be a string of 1-80 chars")

    parse_ts(state.get("last_tick"))

    st = state.get("stats")
    _require(isinstance(st, dict), "stats must be a dict")
    for k in ("commits_eaten", "sulks", "longest_neglect_days"):
        v = st.get(k)
        _require(isinstance(v, int) and not isinstance(v, bool) and v >= 0,
                 f"stat {k!r} must be a non-negative int, got {v!r}")

    diary = state.get("diary")
    _require(isinstance(diary, list) and len(diary) <= DIARY_LIMIT,
             f"diary must be a list of at most {DIARY_LIMIT} entries")
    _require(all(isinstance(e, str) for e in diary), "diary entries must be strings")

    wish = state.get("wish")
    _require(wish is None or isinstance(wish, str), "wish must be null or a string")


def save(path: Path, state: dict[str, Any]) -> None:
    """Write the brain atomically: validate -> tmp (beside target) ->
    fsync -> os.replace. Readers see old XOR new, never a hybrid."""
    validate(state)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def load(path: Path) -> dict[str, Any] | None:
    """Read the brain. None if absent; LOUD error if corrupt."""
    path = Path(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    try:
        state = json.loads(raw)
    except json.JSONDecodeError as e:
        raise CorruptStateError(f"{path} is not valid JSON: {e}") from e

    state = _migrate(state, path)
    validate(state)

    try:
        path.with_name(path.name + ".tmp").unlink(missing_ok=True)
    except OSError:
        pass
    return state


_MIGRATIONS: dict[int, Callable[[dict], dict]] = {}


def _migrate(state: Any, path: Path) -> dict[str, Any]:
    if not isinstance(state, dict) or "v" not in state:
        raise CorruptStateError(f"{path} has no schema version")
    v = state["v"]
    if isinstance(v, bool) or not isinstance(v, int):
        raise CorruptStateError(f"{path}: schema version must be an int, got {v!r}")
    if v > SCHEMA_VERSION:
        raise CorruptStateError(
            f"{path} was written by a NEWER Moss (schema v{v} > v{SCHEMA_VERSION}). "
            "Upgrade moss, or restore a backup."
        )
    while v < SCHEMA_VERSION:
        step = _MIGRATIONS.get(v)
        if step is None:
            raise CorruptStateError(f"{path}: no migration path from schema v{v}")
        state = step(state)
        v = state["v"]
    return state


def record_diary(state: dict[str, Any], entry: str) -> dict[str, Any]:
    new = copy.deepcopy(state)
    new["diary"] = (new["diary"] + [entry])[-DIARY_LIMIT:]
    return new