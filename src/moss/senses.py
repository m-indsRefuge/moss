"""Moss's senses - how the outside world becomes a Scene.

Two implementations of one Protocol:
- GitSenses: reads a real repository through subprocess git. The repo
  is an external service - git missing, not-a-repo, or an empty
  history all degrade to the same quiet, foodless observation. The
  brain got this resilience policy first; the senses get it second.
- FixtureSenses: replays a scripted timeline. Each observe() consumes
  the next step, so N scenario steps = N ticks. An exhausted script
  means eternal quiet - neglect forever.

make_scene() is the pure hinge: (Observation, last_tick, now) ->
Scene. All arithmetic lives there: anchors, fallbacks, clamps.

THE LAW still holds: nothing here queries wall time. `now` arrives
as a parameter, injected by tick from the injected Clock. Moss's
nights are UTC nights, tunable in physics.py.

Why not `git log --since=<date>`? Git's date filtering is fuzzier
than it looks; one call listing ISO dates (%cI, committer date,
newest first) lets US count and filter with the parser we already
trust. One subprocess call, two facts: last_commit_at + new_commits.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Protocol

from moss import physics as ph
from moss.policy import Scene
from moss.state import StateError, parse_ts

GIT_TIMEOUT_S = 10.0


@dataclass(frozen=True)
class Observation:
    """Raw facts from a sense organ. No arithmetic, no policy."""

    new_commits: int
    last_commit_at: datetime | None   # None = never fed / unreadable repo


class Senses(Protocol):
    """Anything that can answer 'what just happened out there?'."""

    def observe(self, now: datetime, last_tick: datetime) -> Observation: ...


def make_scene(obs: Observation, last_tick: datetime, now: datetime) -> Scene:
    """The pure hinge: raw facts -> policy's language.

    hours_quiet = time since the repo last fed Moss, falling back to
    last_tick for a repo that has never fed it. Never negative: a
    commit timestamped in the future (clock skew) is quiet now, not
    a paradox.
    """
    anchor = obs.last_commit_at if obs.last_commit_at is not None else last_tick
    hours_quiet = max(0.0, (now - anchor).total_seconds() / 3600.0)
    return Scene(
        new_commits=max(0, obs.new_commits),
        hours_quiet=hours_quiet,
        is_night=ph.is_night(now.hour),
    )


class GitSenses:
    """The real world, via subprocess git. Degrades, never dies."""

    def __init__(self, repo: Path) -> None:
        self.repo = Path(repo)

    def _commit_dates(self) -> list[datetime] | None:
        try:
            proc = subprocess.run(
                ["git", "-C", str(self.repo), "log", "--pretty=%cI"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=GIT_TIMEOUT_S,
            )
        except (OSError, subprocess.SubprocessError):
            return None   # git missing, hung, or exploded: unreadable
        if proc.returncode != 0:
            return None   # not a repo / no commits yet: unreadable
        dates: list[datetime] = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                dates.append(parse_ts(line))
            except StateError:
                continue   # one weird line never blinds the senses
        return dates

    def observe(self, now: datetime, last_tick: datetime) -> Observation:
        dates = self._commit_dates()
        if dates is None:
            return Observation(new_commits=0, last_commit_at=None)
        # git lists newest first; strict '>' counts commits that
        # arrived after the last tick closed.
        return Observation(
            new_commits=sum(1 for d in dates if d > last_tick),
            last_commit_at=dates[0] if dates else None,
        )


class FixtureSenses:
    """A scripted world. The offline twin of GitSenses.

    Each observe() consumes the next step of the scenario, so a
    scenario maps 1:1 onto ticks. Quiet anchoring mirrors reality:
    a step with food stamps 'fed now'; foodless steps let the quiet
    accumulate from the last feed (or from last_tick, before the
    first-ever meal).
    """

    def __init__(self, steps: Iterable[dict[str, Any]]) -> None:
        self._steps = [dict(s) for s in steps]
        self._i = 0
        self._last_food: datetime | None = None

    def observe(self, now: datetime, last_tick: datetime) -> Observation:
        step = self._steps[self._i] if self._i < len(self._steps) else {}
        self._i += 1
        new_commits = max(0, int(step.get("new_commits", 0)))
        if new_commits > 0:
            self._last_food = now
        return Observation(new_commits=new_commits, last_commit_at=self._last_food)