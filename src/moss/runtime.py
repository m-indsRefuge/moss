"""Interface-independent transactions. The core remains the sole organism.

One runtime per habitat; its lock includes load (which cleans stale save
debris), hatch, tick and save. Separate processes/instances are NOT locked.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from moss.brain import LLMBrain, ReflexBrain
from moss.clock import Clock, RealClock
from moss.llm import (
    DEFAULT_BASE_URL, DEFAULT_MODEL, DEFAULT_TEMPERATURE, DEFAULT_TIMEOUT_S,
    OllamaLLM,
)
from moss.senses import GitSenses, Observation, Senses
from moss.state import load, new_state, save
from moss.tick import Brain, TickResult, tick

STATE_FILENAME = "moss.state.json"


@dataclass(frozen=True)
class MossSnapshot:
    repo_path: str
    name: str
    hunger: float
    energy: float
    bowl: int
    mood: str
    diary: tuple[str, ...]
    wish: str
    last_tick: str
    action: str = "idle"
    thought: str = ""
    brain_status: str = "Not run this visit"
    repo_status: str = "Not sensed this visit"
    commits_eaten: int = 0
    sulks: int = 0
    longest_neglect_days: int = 0
    has_tick: bool = False
    commits_arrived: int = 0
    commits_eaten_this_tick: int = 0
    decision_attempts: int = 0
    used_fallback: bool = False
    hours_quiet: float = 0.0
    is_night: bool = False
    last_commit_at: str = ""


class _ObservedSenses:
    """Pass-through telemetry, with no extra Git call or observation rules."""

    def __init__(self, senses: Senses) -> None:
        self.senses = senses
        self.observation: Observation | None = None

    def observe(self, now, last_tick) -> Observation:
        self.observation = self.senses.observe(now=now, last_tick=last_tick)
        return self.observation


class MossRuntime:
    def __init__(self, repo: Path, *, clock: Clock | None = None,
                 senses: Senses | None = None, brain: Brain | None = None) -> None:
        # Match CLI cwd semantics, including when launched in a subdirectory.
        self.repo = Path(repo).resolve()
        self.state_path = self.repo / STATE_FILENAME
        self.clock = clock if clock is not None else RealClock()
        self.senses = senses if senses is not None else GitSenses(self.repo)
        self.brain = brain if brain is not None else ReflexBrain()
        self._lock = Lock()

    @property
    def brain_label(self) -> str:
        """Configured identity, without contacting the model or changing it."""
        if isinstance(self.brain, LLMBrain):
            transport = self.brain.llm
            return f"Ollama · {transport.model}" if isinstance(transport, OllamaLLM) else "LLM"
        return "Reflex" if isinstance(self.brain, ReflexBrain) else "Custom brain"

    def _load_or_hatch(self):
        existing = load(self.state_path)
        return existing if existing is not None else new_state("Moss", self.clock.now())

    def _snapshot(self, state, result: TickResult | None = None,
                  observed: Observation | None = None) -> MossSnapshot:
        brain_status = "Not run this visit"
        repo_status = "Not sensed this visit"
        if result is not None:
            reply = result.reply
            brain_status = ("Reflex fallback" if reply.used_fallback else
                            "LLM decision" if isinstance(self.brain, LLMBrain) else
                            "Reflex" if isinstance(self.brain, ReflexBrain) else "Custom brain")
            # GitSenses collapses unreadable and empty history. Do not invent
            # a healthy/quiet verdict from that ambiguous public observation.
            repo_status = ("Git history read" if observed and observed.last_commit_at else
                           "Git unavailable or empty history") if isinstance(self.senses, GitSenses) else "Injected senses"
        return MossSnapshot(
            repo_path=str(self.repo), name=state["name"],
            hunger=state["drives"]["hunger"], energy=state["drives"]["energy"],
            bowl=state["bowl"]["commits"], mood=state["mood"],
            diary=tuple(state["diary"]), wish=state["wish"] or "",
            last_tick=state["last_tick"],
            action=result.reply.decision.action if result else "idle",
            thought=result.reply.decision.thought if result else "",
            brain_status=brain_status, repo_status=repo_status,
            commits_eaten=state["stats"]["commits_eaten"],
            sulks=state["stats"]["sulks"],
            longest_neglect_days=state["stats"]["longest_neglect_days"],
            has_tick=result is not None,
            commits_arrived=result.filled if result else 0,
            commits_eaten_this_tick=result.ate if result else 0,
            decision_attempts=result.reply.attempts if result else 0,
            used_fallback=result.reply.used_fallback if result else False,
            hours_quiet=result.scene.hours_quiet if result else 0.0,
            is_night=result.scene.is_night if result else False,
            last_commit_at=observed.last_commit_at.isoformat() if observed and observed.last_commit_at else "",
        )

    def open(self) -> MossSnapshot:
        """Opening observes existing state; only a missing pet is saved at birth."""
        with self._lock:
            existing = load(self.state_path)
            if existing is None:
                existing = new_state("Moss", self.clock.now())
                save(self.state_path, existing)
            return self._snapshot(existing)

    def live_tick(self) -> MossSnapshot:
        with self._lock:
            existing = self._load_or_hatch()
            senses = _ObservedSenses(self.senses)
            result = tick(existing, self.clock, senses, self.brain)
            snapshot = self._snapshot(result.state, result, senses.observation)
            save(self.state_path, result.state)
            return snapshot  # publication is strictly after successful save


def configured_runtime(repo: Path, *, brain: str = "reflex",
                       model: str = DEFAULT_MODEL, ollama_url: str = DEFAULT_BASE_URL,
                       temperature: float = DEFAULT_TEMPERATURE,
                       timeout: float = DEFAULT_TIMEOUT_S) -> MossRuntime:
    if brain not in ("reflex", "llm"):
        raise ValueError("brain must be reflex or llm")
    selected = LLMBrain(OllamaLLM(model=model, base_url=ollama_url,
                                 temperature=temperature, timeout_s=timeout)) if brain == "llm" else ReflexBrain()
    return MossRuntime(repo, brain=selected)
