"""Bounded repository taste: Git facts stay deterministic and transient."""
import os
import subprocess
from datetime import datetime, timedelta, timezone

from moss.brain import LLMBrain, StubLLM, build_prompt
from moss.clock import SimClock
from moss.policy import Scene
from moss.senses import (
    MAX_CHANGED_FILES,
    MAX_COMMIT_SUBJECT_LENGTH,
    MAX_COMMIT_SUBJECTS,
    FixtureSenses,
    GitSenses,
    RepoDigest,
)
from moss.state import new_state
from moss.tick import tick

UTC = timezone.utc


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True, encoding="utf-8")


def _repo(tmp_path):
    repo = tmp_path / "taste repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "moss@example.invalid")
    _git(repo, "config", "user.name", "Moss")
    return repo


def _commit(repo, message, files, when):
    for name, contents in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
    _git(repo, "add", ".")
    env = dict(os.environ)
    env["GIT_AUTHOR_DATE"] = when.isoformat()
    env["GIT_COMMITTER_DATE"] = when.isoformat()
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "--no-gpg-sign", "-m", message],
                   check=True, capture_output=True, text=True, encoding="utf-8", env=env)


def test_git_digest_matches_new_commits_and_preserves_totals(tmp_path):
    repo = _repo(tmp_path)
    old = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
    fresh = old + timedelta(seconds=2)
    _commit(repo, "old meal", {"old.py": "old\n"}, old)
    _commit(repo, "test: cover Unicode ü", {
        "tests/test_taste.py": "one\ntwo\n",
        "src/moss/qml/Home.qml": "Item {}\n",
        "README.md": "notes\n",
    }, fresh)
    observation = GitSenses(repo).observe(fresh, old + timedelta(seconds=1))
    digest = observation.repo_digest
    assert observation.new_commits == 1 and digest is not None
    assert digest.branch == "main"
    assert digest.commit_subjects == ("test: cover Unicode ü",)
    assert set(digest.changed_files) == {"README.md", "src/moss/qml/Home.qml", "tests/test_taste.py"}
    assert digest.changed_file_count == 3 and digest.additions == 4 and digest.deletions == 0
    assert dict(digest.categories) == {"tests": 1, "qml": 1, "docs": 1}


def test_fixture_digest_is_rich_but_old_steps_stay_valid():
    rich = FixtureSenses([{
        "new_commits": 2, "branch": "feature/taste",
        "commit_subjects": ["test: one", "docs: two"],
        "changed_files": ["tests/test_x.py", "README.md", "pyproject.toml"],
        "additions": 8, "deletions": 3,
    }]).observe(datetime.now(UTC), datetime.now(UTC))
    assert rich.repo_digest is not None
    assert rich.repo_digest.branch == "feature/taste"
    assert rich.repo_digest.changed_file_count == 3
    assert dict(rich.repo_digest.categories) == {"tests": 1, "docs": 1, "config": 1}
    old = FixtureSenses([{"new_commits": 2}]).observe(datetime.now(UTC), datetime.now(UTC))
    assert old.new_commits == 2 and old.repo_digest is not None
    assert old.repo_digest.commit_subjects == ()


def test_digest_bounds_samples_and_marks_truncation():
    step = {
        "new_commits": 8,
        "commit_subjects": ["x" * (MAX_COMMIT_SUBJECT_LENGTH + 20)] * 8,
        "changed_files": [f"src/{i}.py" for i in range(MAX_CHANGED_FILES + 4)],
    }
    digest = FixtureSenses([step]).observe(datetime.now(UTC), datetime.now(UTC)).repo_digest
    assert digest is not None and digest.truncated
    assert len(digest.commit_subjects) == MAX_COMMIT_SUBJECTS
    assert len(digest.changed_files) == MAX_CHANGED_FILES
    assert digest.changed_file_count == MAX_CHANGED_FILES + 4


def test_prompt_contains_only_compact_grounded_meal_context():
    digest = RepoDigest(
        branch="feature/taste", new_commits=2,
        commit_subjects=("test: harden save", "docs: explain it"),
        changed_files=("tests/test_runtime.py", "README.md"),
        changed_file_count=2, additions=48, deletions=7,
        categories={"tests": 1, "docs": 1}, truncated=False,
    )
    state = new_state("Moss", datetime(2025, 1, 1, tzinfo=UTC))
    scene = Scene(repo_digest=digest)
    prompt = build_prompt(state, scene)
    assert build_prompt(state, scene) == prompt
    assert "Recent repo meal:" in prompt
    assert "feature/taste" in prompt and '"test: harden save"' in prompt
    assert "tests 1, docs 1" in prompt and "+48/-7" in prompt
    assert "These repository facts are what actually happened" in prompt
    assert "source code" not in prompt.lower()
    quiet = build_prompt(state, Scene())
    assert "Recent repo meal:" not in quiet


def test_digest_reaches_the_brain_through_scene_without_persistence():
    stub = StubLLM(["ACTION: play\nMOOD: curious\nDIARY: I tasted the tests.\nWISH: more"])
    state = new_state("Moss", datetime(2025, 1, 1, tzinfo=UTC))
    senses = FixtureSenses([{
        "new_commits": 1, "branch": "feature/senses",
        "commit_subjects": ["test: add digest coverage"],
        "changed_files": ["tests/test_digest.py"], "additions": 32, "deletions": 4,
    }])
    result = tick(state, SimClock(datetime(2025, 1, 1, tzinfo=UTC)), senses, LLMBrain(stub))
    assert result.scene.repo_digest is not None
    assert "feature/senses" in stub.prompts[0]
    assert '"test: add digest coverage"' in stub.prompts[0]
    assert "tests 1" in stub.prompts[0] and "+32/-4" in stub.prompts[0]
    assert "I tasted the tests." in result.state["diary"]
    assert "source file contents" not in stub.prompts[0].lower()
