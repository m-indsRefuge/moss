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
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Protocol

from moss import physics as ph
from moss.policy import Scene
from moss.state import StateError, parse_ts

GIT_TIMEOUT_S = 10.0
MAX_COMMIT_SUBJECTS = 5
MAX_CHANGED_FILES = 20
MAX_COMMIT_SUBJECT_LENGTH = 120
MAX_CHANGED_PATH_LENGTH = 160
_HASH = re.compile(r"^[0-9a-f]{40}$")
_CATEGORY_ORDER = ("tests", "python", "qml", "docs", "config", "assets", "other")


@dataclass(frozen=True)
class RepoDigest:
    """Small, immutable facts about the commits delivered by one observation."""

    branch: str = ""
    new_commits: int = 0
    commit_subjects: tuple[str, ...] = ()
    changed_files: tuple[str, ...] = ()
    changed_file_count: int = 0
    additions: int = 0
    deletions: int = 0
    categories: Mapping[str, int] = field(default_factory=dict)
    truncated: bool = False

    def __post_init__(self) -> None:
        normalized = {name: int(self.categories.get(name, 0))
                      for name in _CATEGORY_ORDER if int(self.categories.get(name, 0)) > 0}
        object.__setattr__(self, "categories", MappingProxyType(normalized))


def _category(path: str) -> str:
    """Classify one path once, with tests taking precedence over extensions."""
    normalized = path.replace("\\", "/").lower()
    name = normalized.rsplit("/", 1)[-1]
    if normalized.startswith("tests/") or "/tests/" in normalized or name.startswith("test_") or name.endswith("_test.py"):
        return "tests"
    if normalized.endswith(".py"):
        return "python"
    if normalized.endswith(".qml"):
        return "qml"
    if normalized.startswith("docs/") or "/docs/" in normalized or normalized.endswith((".md", ".rst", ".txt")):
        return "docs"
    if name in {"pyproject.toml", "setup.cfg", "setup.py", "tox.ini", "package.json", "package-lock.json"} or normalized.endswith((".toml", ".ini", ".cfg", ".yaml", ".yml", ".json")):
        return "config"
    if normalized.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".wav", ".mp3")):
        return "assets"
    return "other"


def _bounded_digest(branch: str, records: list[tuple[datetime, str, list[tuple[int | None, int | None, str]]]]) -> RepoDigest | None:
    if not records:
        return None
    subjects = []
    paths: list[str] = []
    seen_paths: set[str] = set()
    categories: dict[str, int] = {name: 0 for name in _CATEGORY_ORDER}
    additions = deletions = 0
    truncated = len(records) > MAX_COMMIT_SUBJECTS
    for _date, subject, stats in records:
        if len(subject) > MAX_COMMIT_SUBJECT_LENGTH:
            truncated = True
        if len(subjects) < MAX_COMMIT_SUBJECTS:
            subjects.append(subject[:MAX_COMMIT_SUBJECT_LENGTH])
        for added, removed, path in stats:
            additions += added or 0
            deletions += removed or 0
            if path not in seen_paths:
                seen_paths.add(path)
                categories[_category(path)] += 1
                if len(paths) < MAX_CHANGED_FILES:
                    if len(path) > MAX_CHANGED_PATH_LENGTH:
                        truncated = True
                    paths.append(path[:MAX_CHANGED_PATH_LENGTH])
                else:
                    truncated = True
    return RepoDigest(branch=branch, new_commits=len(records),
                      commit_subjects=tuple(subjects), changed_files=tuple(paths),
                      changed_file_count=len(seen_paths), additions=additions,
                      deletions=deletions, categories=categories,
                      truncated=truncated)


def _fixture_digest(step: Mapping[str, Any], new_commits: int) -> RepoDigest | None:
    if new_commits <= 0:
        return None
    subjects = [str(value) for value in step.get("commit_subjects", [])][:new_commits]
    raw_paths = [str(value) for value in step.get("changed_files", [])]
    unique_paths = list(dict.fromkeys(raw_paths))
    truncated = len(subjects) > MAX_COMMIT_SUBJECTS or len(unique_paths) > MAX_CHANGED_FILES
    bounded_subjects = []
    for subject in subjects[:MAX_COMMIT_SUBJECTS]:
        truncated = truncated or len(subject) > MAX_COMMIT_SUBJECT_LENGTH
        bounded_subjects.append(subject[:MAX_COMMIT_SUBJECT_LENGTH])
    bounded_paths = []
    for path in unique_paths[:MAX_CHANGED_FILES]:
        truncated = truncated or len(path) > MAX_CHANGED_PATH_LENGTH
        bounded_paths.append(path[:MAX_CHANGED_PATH_LENGTH])
    categories = {name: 0 for name in _CATEGORY_ORDER}
    for path in unique_paths:
        categories[_category(path)] += 1
    return RepoDigest(
        branch=str(step.get("branch", "fixture")), new_commits=new_commits,
        commit_subjects=tuple(bounded_subjects), changed_files=tuple(bounded_paths),
        changed_file_count=len(unique_paths), additions=max(0, int(step.get("additions", 0))),
        deletions=max(0, int(step.get("deletions", 0))), categories=categories,
        truncated=truncated,
    )


@dataclass(frozen=True)
class Observation:
    """Raw facts from a sense organ. No arithmetic, no policy."""

    new_commits: int
    last_commit_at: datetime | None   # None = never fed / unreadable repo
    repo_digest: RepoDigest | None = None


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
        repo_digest=obs.repo_digest,
    )


class GitSenses:
    """The real world, via subprocess git. Degrades, never dies."""

    def __init__(self, repo: Path) -> None:
        self.repo = Path(repo)

    def _branch(self) -> str:
        try:
            proc = subprocess.run(
                ["git", "-C", str(self.repo), "symbolic-ref", "--short", "-q", "HEAD"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=GIT_TIMEOUT_S,
            )
            branch = proc.stdout.strip()
            if proc.returncode == 0 and branch:
                return branch
            proc = subprocess.run(
                ["git", "-C", str(self.repo), "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=GIT_TIMEOUT_S,
            )
            head = proc.stdout.strip()
            return f"detached@{head}" if proc.returncode == 0 and head else ""
        except (OSError, subprocess.SubprocessError):
            return ""

    def _history(self) -> tuple[list[tuple[datetime, str, list[tuple[int | None, int | None, str]]]], datetime | None] | None:
        try:
            proc = subprocess.run(
                ["git", "-C", str(self.repo), "log", "--format=%H%x00%cI%x00%s%x00",
                 "--numstat", "-z", "--no-renames"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=GIT_TIMEOUT_S,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if proc.returncode != 0:
            return None
        records = []
        current = None
        tokens = proc.stdout.split("\x00")
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if _HASH.fullmatch(token) and i + 2 < len(tokens):
                try:
                    date = parse_ts(tokens[i + 1])
                except StateError:
                    i += 1
                    continue
                if current is not None:
                    records.append(current)
                current = [date, tokens[i + 2], []]
                i += 3
                continue
            if current is not None and token:
                token = token.lstrip("\r\n")
                fields = token.split("\t", 2)
                if len(fields) == 3:
                    added = int(fields[0]) if fields[0].isdigit() else None
                    removed = int(fields[1]) if fields[1].isdigit() else None
                    current[2].append((added, removed, fields[2]))
            i += 1
        if current is not None:
            records.append(current)
        return records, (records[0][0] if records else None)

    def observe(self, now: datetime, last_tick: datetime) -> Observation:
        history = self._history()
        if history is None:
            return Observation(new_commits=0, last_commit_at=None)
        records, newest = history
        fresh = [record for record in records if record[0] > last_tick]
        return Observation(
            new_commits=len(fresh), last_commit_at=newest,
            repo_digest=_bounded_digest(self._branch(), fresh),
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
        digest = _fixture_digest(step, new_commits)
        return Observation(new_commits=new_commits, last_commit_at=self._last_food,
                           repo_digest=digest)
