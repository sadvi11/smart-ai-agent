"""The API must actually reach the agent.

This file exists because it once did not. `POST /chat` returned

    f"[Agent response to: {message}]"

a hardcoded echo, and `POST /history` returned a hardcoded empty list. app.py
imported neither agent nor memory. Every check in CI passed anyway: flake8's
error rules and `compileall` are both perfectly happy with a stub, because a
stub is valid Python.

Linting proves code parses. These tests prove it is connected.
"""
from unittest.mock import patch

import pytest

import app as app_module


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def test_app_imports_the_agent_layer():
    """app.py must hold a reference to the agent, not reimplement it."""
    assert hasattr(app_module, "run_agent"), "app.py does not import run_agent"
    assert hasattr(app_module, "memory"), "app.py does not import the memory layer"


def test_chat_calls_the_agent():
    """The endpoint must delegate to run_agent — this is the regression test."""
    with patch.object(app_module, "run_agent", return_value=("real answer", [])) as ra, \
            patch.object(app_module.memory, "load_history", return_value=[]), \
            patch.object(app_module.memory, "save_message"):
        app_module.app.config["TESTING"] = True
        with app_module.app.test_client() as c:
            r = c.post("/chat", json={"message": "hello", "session_id": "s1"})

    assert ra.called, "/chat did not call run_agent — the endpoint is a stub"
    assert r.status_code == 200
    assert r.get_json()["answer"] == "real answer"


def test_chat_never_returns_the_stub_echo(client):
    """Guard the exact shape of the original bug."""
    with patch.object(app_module, "run_agent", return_value=("ok", [])), \
            patch.object(app_module.memory, "load_history", return_value=[]), \
            patch.object(app_module.memory, "save_message"):
        r = client.post("/chat", json={"message": "ping", "session_id": "s1"})

    body = str(r.get_json())
    assert "Agent response to" not in body, "the placeholder echo is back"
    assert "ping" != r.get_json()["answer"], "/chat is echoing the input"


def test_chat_persists_both_sides_of_the_turn():
    with patch.object(app_module, "run_agent", return_value=("answer", [])), \
            patch.object(app_module.memory, "load_history", return_value=[]), \
            patch.object(app_module.memory, "save_message") as save:
        app_module.app.config["TESTING"] = True
        with app_module.app.test_client() as c:
            c.post("/chat", json={"message": "q", "session_id": "s1"})

    roles = [call.args[1] for call in save.call_args_list]
    assert "user" in roles and "assistant" in roles, f"only persisted {roles}"


def test_chat_survives_a_memory_outage():
    """A Supabase failure must not cost the user their answer."""
    with patch.object(app_module, "run_agent", return_value=("answer", [])), \
            patch.object(app_module.memory, "load_history", return_value=[]), \
            patch.object(app_module.memory, "save_message", side_effect=Exception("db down")):
        app_module.app.config["TESTING"] = True
        with app_module.app.test_client() as c:
            r = c.post("/chat", json={"message": "q", "session_id": "s1"})

    assert r.status_code == 200, "a memory write failure must not fail the request"
    assert r.get_json()["answer"] == "answer"


def test_history_returns_stored_messages(client):
    stored = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    with patch.object(app_module.memory, "load_history", return_value=stored) as lh:
        r = client.post("/history", json={"session_id": "s1"})

    assert lh.called, "/history did not call memory.load_history — it is a stub"
    body = r.get_json()
    assert body["messages"] == stored
    assert body["message_count"] == 2


def test_validation_rejects_bad_input(client):
    assert client.post("/chat", json={"message": "", "session_id": "s1"}).status_code == 400
    assert client.post("/chat", json={"message": "hi", "session_id": ""}).status_code == 400
    assert client.post("/chat", json={"message": "x" * 10001, "session_id": "s1"}).status_code == 400


def test_health_reports_metrics(client):
    body = client.get("/health").get_json()
    assert body["status"] == "healthy"
    assert "metrics" in body


def test_model_is_not_a_retired_id():
    """A retired model ID looks correct in code and 404s on every request."""
    import agent
    retired = {
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-20240620",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-5-haiku-20241022",
        "claude-3-7-sonnet-20250219",
    }
    source = open(agent.__file__).read()
    for model in retired:
        assert model not in source, f"{model} is retired and will 404"
