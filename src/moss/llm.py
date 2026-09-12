"""LLM transports - how a prompt becomes text.

The transport contract with the rest of Moss: hand it a prompt, get
back the model's ANSWER - not its monologue. Model-family noise
(Qwen3's <think> blocks) is normalized HERE, at the boundary, so
brain.py's parser stays generic and StubLLM stays honest.

Failure policy (the one the brain already trusts): ANY failure -
refused connection, timeout, HTTP 500, malformed envelope - raises
RuntimeError. LLMBrain catches it and hands the leash to the
reflexes. The transport never retries; retry policy lives above.

OllamaLLM speaks /api/generate: flat prompt in, flat text out - the
natural shape for our flat-prompt protocol. `think: false` asks
Qwen3-class models to skip reasoning; strip_thinking is the belt to
that suspenders (older servers ignore the flag; a generation cut off
mid-think leaks an unclosed <think>).

Still zero dependencies: stdlib urllib only.
"""
from __future__ import annotations

import json
import re
import urllib.request

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:0.5b"
DEFAULT_TEMPERATURE = 0.7     # harness absorbs the risk; personality needs heat
DEFAULT_TIMEOUT_S = 120.0     # 14B on a laptop CPU can be slow; reflexes catch timeouts
NUM_PREDICT = 200             # 5 short lines; a runaway think-block eats budget

_THINK_CLOSED = re.compile(r"<think>.*?</think>", re.DOTALL)
_THINK_OPEN = re.compile(r"<think>.*", re.DOTALL)   # truncated mid-monologue


def strip_thinking(text: str) -> str:
    """Remove <think> blocks - closed or truncated. Plain text passes through."""
    return _THINK_OPEN.sub("", _THINK_CLOSED.sub("", text)).strip()


class OllamaLLM:
    """A local Ollama server, as seen through one method: complete()."""

    def __init__(self, model: str = DEFAULT_MODEL,
                 base_url: str = DEFAULT_BASE_URL,
                 temperature: float = DEFAULT_TEMPERATURE,
                 timeout_s: float = DEFAULT_TIMEOUT_S) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.timeout_s = timeout_s

    def complete(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {"temperature": self.temperature, "num_predict": NUM_PREDICT},
        }
        req = urllib.request.Request(
            self.base_url + "/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                envelope = json.loads(resp.read().decode("utf-8"))
        except (OSError, ValueError) as e:
            # URLError, refused, reset, timeout (all OSError); bad JSON or
            # undecodable bytes (ValueError). One bucket: transport failed.
            raise RuntimeError(f"ollama transport failed: {e}") from e
        text = envelope.get("response")
        if not isinstance(text, str):
            raise RuntimeError("ollama reply carried no 'response' text")
        return strip_thinking(text)