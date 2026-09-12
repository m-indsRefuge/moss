"""Senses: the pure hinge, the scripted world, and the real world
(hermetic throwaway repos - no network, deterministic dates)."""
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from moss.clock import SimClock
from moss.senses import FixtureSenses, GitSenses, Observation, make_scene

UTC = timezone.utc
T0 = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
LAST_TICK = T0 - timedelta(hours=7)


def scene(obs, now=T0, last_tick=LAST_TICK):
    return make_scene(obs, last_tick=last_tick, now=now)


# -- the pure hinge ------------------------------------------------

def test_make_scene_counts_commits():
    assert scene(Observation(new_commits=3, last_commit_at=T0)).new_commits == 3


def test_make_scene_clamps_negative_commits():
    assert scene(Observation(new_commits=-5, last_commit_at=T0)).new_commits == 0


def test_make_scene_quiet_since_last_food():
    fed_at = T0 - timedelta(hours=2)
    assert scene(Observation(0, fed_at)).hours_quiet == pytest.approx(2.0)


def test_make_scene_quiet_falls_back_to_last_tick():
    # a repo that has never fed anyone: quiet counts from last_tick
    assert scene(Observation(0, None)).hours_quiet == pytest.approx(7.0)


def test_make_scene_future_food_never_negative_quiet():
    fed_at = T0 + timedelta(hours=9)   # clock skew: commit "from the future"
    assert scene(Observation(0, fed_at)).hours_quiet == 0.0


def test_make_scene_night_flag_follows_physics():
    late = scene(Observation(0, None), now=T0.replace(hour=23))
    noon = scene(Observation(0, None), now=T0.replace(hour=12))
    assert late.is_night and not noon.is_night


# -- the scripted world --------------------------------------------

SCENARIO = [
    {"advance_hours": 20, "new_commits": 3},
    {"advance_hours": 240, "new_commits": 0},
    {"advance_hours": 3, "new_commits": 11},
]


def test_fixture_replays_steps_in_order():
    senses = FixtureSenses(SCENARIO)
    counts = [senses.observe(T0, LAST_TICK).new_commits for _ in range(3)]
    assert counts == [3, 0, 11]


def test_fixture_quiet_tracks_the_last_feeding():
    clock, senses = SimClock(T0), FixtureSenses(SCENARIO)
    last_tick = clock.now()

    obs = senses.observe(clock.now(), last_tick)          # fed right now
    assert make_scene(obs, last_tick, clock.now()).hours_quiet == 0.0

    clock.advance(hours=20)
    obs = senses.observe(clock.now(), last_tick)          # quiet since the feed
    assert obs.new_commits == 0
    assert make_scene(obs, last_tick, clock.now()).hours_quiet == pytest.approx(20.0)

    clock.advance(hours=240)
    obs = senses.observe(clock.now(), last_tick)          # the feast arrives
    assert obs.new_commits == 11
    assert make_scene(obs, last_tick, clock.now()).hours_quiet == 0.0


def test_fixture_starvation_accumulates_quiet():
    senses = FixtureSenses([{"new_commits": 0}, {"new_commits": 0}])
    clock, last_tick = SimClock(T0), T0
    senses.observe(clock.now(), last_tick)
    clock.advance(hours=5)
    obs = senses.observe(clock.now(), last_tick)
    assert make_scene(obs, last_tick, clock.now()).hours_quiet == pytest.approx(5.0)


def test_fixture_exhausted_script_starves_forever():
    senses = FixtureSenses([{"new_commits": 1}])
    clock, last_tick = SimClock(T0), T0
    assert senses.observe(clock.now(), last_tick).new_commits == 1
    clock.advance(hours=100)
    obs = senses.observe(clock.now(), last_tick)          # script over: silence
    assert obs.new_commits == 0
    assert make_scene(obs, last_tick, clock.now()).hours_quiet == pytest.approx(100.0)


def test_fixture_never_fed_uses_last_tick_as_anchor():
    senses = FixtureSenses([{"new_commits": 0}])
    obs = senses.observe(T0, LAST_TICK)
    assert obs.last_commit_at is None
    assert make_scene(obs, LAST_TICK, T0).hours_quiet == pytest.approx(7.0)


# -- the real world (hermetic throwaway repos) ----------------------

def _git(repo: Path, *args: str, dates: tuple[datetime, datetime] | None = None) -> None:
    env = dict(os.environ)
    if dates is not None:
        author, committer = dates
        env["GIT_AUTHOR_DATE"] = author.isoformat()
        env["GIT_COMMITTER_DATE"] = committer.isoformat()
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, text=True, encoding="utf-8", env=env)


def _init_repo(tmp_path: Path, name: str = "repo") -> Path:
    repo = tmp_path / name
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "moss@example.com")
    _git(repo, "config", "user.name", "Moss Test")
    return repo


def _commit_at(repo: Path, when: datetime, msg: str = "meal") -> None:
    _git(repo, "commit", "--allow-empty", "--no-gpg-sign", "-q", "-m", msg,
         dates=(when, when))


def test_git_empty_repo_reads_as_quiet_and_foodless(tmp_path):
    repo = _init_repo(tmp_path)
    obs = GitSenses(repo).observe(T0, LAST_TICK)
    assert obs == Observation(new_commits=0, last_commit_at=None)


def test_git_not_a_repo_degrades_gracefully(tmp_path):
    # git walks UP the tree looking for .git - the dummy file is a
    # barrier that keeps the test hermetic even on odd machines.
    lonely = tmp_path / "lonely"
    lonely.mkdir()
    (lonely / ".git").write_text("gitdir: nowhere\n", encoding="utf-8")
    obs = GitSenses(lonely).observe(T0, LAST_TICK)
    assert obs == Observation(new_commits=0, last_commit_at=None)


def test_git_counts_commits_since_last_tick(tmp_path):
    # old news predates last_tick (T0-7h); fresh postdates it
    repo = _init_repo(tmp_path)
    _commit_at(repo, T0 - timedelta(hours=9), "old news")
    _commit_at(repo, T0 - timedelta(hours=1), "fresh")
    obs = GitSenses(repo).observe(T0, LAST_TICK)
    assert obs.new_commits == 1                          # only the fresh one
    assert obs.last_commit_at == T0 - timedelta(hours=1)
    assert scene(obs).hours_quiet == pytest.approx(1.0)


def test_git_last_commit_at_is_exact_and_aware(tmp_path):
    repo = _init_repo(tmp_path)
    exact = datetime(2024, 12, 31, 23, 45, tzinfo=UTC)
    _commit_at(repo, exact, "new year's eve")
    assert GitSenses(repo).observe(T0, LAST_TICK).last_commit_at == exact