"""The transport: a real localhost HTTP server, no stdlib mocks.
Covers the envelope, the think-strip, and every failure mode."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from moss.llm import OllamaLLM, strip_thinking


class Controller:
    """What the fake server serves next; what it has received."""

    def __init__(self):
        self.status = 200
        self.payload: object = {"response": "ok"}
        self.sleep_s = 0.0
        self.requests: list[dict] = []
        self.url = ""


@pytest.fixture
def ollama():
    c = Controller()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            c.requests.append(json.loads(self.rfile.read(length).decode("utf-8")))
            if c.sleep_s:
                time.sleep(c.sleep_s)
            body = c.payload if isinstance(c.payload, bytes) else json.dumps(c.payload).encode("utf-8")
            self.send_response(c.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    c.url = f"http://127.0.0.1:{server.server_address[1]}"
    yield c
    server.shutdown()
    server.server_close()


def llm(c: Controller, **kw) -> OllamaLLM:
    return OllamaLLM(base_url=c.url, **kw)


# -- the think-strip ------------------------------------------------

def test_strip_removes_closed_blocks():
    assert strip_thinking("<think>hmm, eat? no, sleep</think>ACTION: eat") == "ACTION: eat"


def test_strip_removes_truncated_blocks():
    assert strip_thinking("ACTION: eat<think>wait, maybe") == "ACTION: eat"


def test_strip_leaves_plain_text_alone():
    assert strip_thinking("ACTION: eat") == "ACTION: eat"


# -- the happy path --------------------------------------------------

def test_complete_returns_stripped_answer(ollama):
    ollama.payload = {"response": "<think>reasoning here</think>THOUGHT: t\nACTION: eat"}
    out = llm(ollama).complete("prompt")
    assert out == "THOUGHT: t\nACTION: eat"


def test_complete_sends_model_think_false_and_options(ollama):
    transport = OllamaLLM(model="qwen3:14b", base_url=ollama.url, temperature=0.5)
    transport.complete("prompt")
    sent = ollama.requests[0]
    assert sent["model"] == "qwen3:14b"
    assert sent["think"] is False
    assert sent["stream"] is False
    assert sent["options"] == {"temperature": 0.5, "num_predict": 200}
    assert sent["prompt"] == "prompt"


# -- every failure mode: one bucket, RuntimeError --------------------

def test_http_500_raises_runtimeerror(ollama):
    ollama.status = 500
    with pytest.raises(RuntimeError):
        llm(ollama).complete("prompt")


def test_connection_refused_raises_runtimeerror():
    with pytest.raises(RuntimeError):
        OllamaLLM(base_url="http://127.0.0.1:1").complete("prompt")


def test_timeout_raises_runtimeerror(ollama):
    ollama.sleep_s = 1.0
    with pytest.raises(RuntimeError):
        llm(ollama, timeout_s=0.2).complete("prompt")


def test_malformed_json_raises_runtimeerror(ollama):
    ollama.payload = b"this is not json {{{"
    with pytest.raises(RuntimeError):
        llm(ollama).complete("prompt")


def test_envelope_without_response_text_raises(ollama):
    ollama.payload = {"no_response_key": 1}
    with pytest.raises(RuntimeError):
        llm(ollama).complete("prompt")