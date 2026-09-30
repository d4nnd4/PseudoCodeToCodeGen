"""

Estos tests fueron hechos con un modelo local.

"""

import json
import os
import tempfile

os.environ.setdefault("GENERATED_DIR", tempfile.mkdtemp(prefix="gen_"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import llm, main  # noqa: E402

client = TestClient(main.app)


def fake_stream(tokens):
    async def _stream(system, user):
        for t in tokens:
            yield t
    return _stream


def read_events(resp):
    return [json.loads(line) for line in resp.text.splitlines() if line.strip()]


def test_languages():
    ids = [l["id"] for l in client.get("/api/languages").json()]
    assert ids == ["python", "go", "typescript", "rpgle"]


def test_clean_code_strips_fences():
    raw = "Here you go:\n```python\nprint('hi')\n```\nBye"
    assert llm.clean_code(raw) == "print('hi')\n"
    assert llm.clean_code("print(1)") == "print(1)\n"


@pytest.mark.parametrize("lang,ext", [("python", "py"), ("go", "go"), ("typescript", "ts"), ("rpgle", "rpgle")])
def test_generate_saves_file(monkeypatch, lang, ext):
    monkeypatch.setattr(llm, "stream_chat", fake_stream(["```\n", "code ", "here\n", "```"]))
    resp = client.post("/api/generate", json={"pseudocode": "LEER n\nIMPRIMIR n", "language": lang})
    events = read_events(resp)
    assert [e["type"] for e in events[:-1]] == ["token"] * 4
    done = events[-1]
    assert done["type"] == "done"
    item = done["item"]
    assert item["code"] == "code here\n"
    assert item["path"].startswith(f"{lang}/") and item["path"].endswith(f".{ext}")
    assert (main.storage.root / item["path"]).read_text() == "code here\n"


def test_history_crud(monkeypatch):
    monkeypatch.setattr(llm, "stream_chat", fake_stream(["x = 1"]))
    item = read_events(client.post("/api/generate", json={"pseudocode": "x <- 1", "language": "python", "name": "Asignación"}))[-1]["item"]
    assert item["name"] == "Asignación"
    assert client.get("/api/history").json()[0]["id"] == item["id"]

    updated = client.put(f"/api/history/{item['id']}", json={"code": "x = 2\n"}).json()
    assert updated["code"] == "x = 2\n"
    assert client.get(f"/api/history/{item['id']}").json()["code"] == "x = 2\n"
    assert client.get(f"/api/history/{item['id']}/download").text == "x = 2\n"

    assert client.delete(f"/api/history/{item['id']}").status_code == 204
    assert client.get(f"/api/history/{item['id']}").status_code == 404


def test_generate_reports_llm_error(monkeypatch):
    async def boom(system, user):
        raise llm.LLMError("Ollama caído")
        yield  # pragma: no cover

    monkeypatch.setattr(llm, "stream_chat", boom)
    events = read_events(client.post("/api/generate", json={"pseudocode": "algo", "language": "go"}))
    assert events == [{"type": "error", "message": "Ollama caído"}]


def test_rejects_unknown_language():
    assert client.post("/api/generate", json={"pseudocode": "algo", "language": "cobol"}).status_code == 400
