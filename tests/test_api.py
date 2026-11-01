from fastapi.testclient import TestClient

from text_summarizer import server
from tests.test_core import DOC, fake_embed  # noqa: F401

c = TestClient(server.create_app())


def test_index_and_summarize(monkeypatch):
    monkeypatch.setattr(server.engine, "embed", fake_embed)
    assert c.get("/").status_code == 200
    r = c.post("/api/summarize", data={"text": DOC, "n": 2})
    assert r.status_code == 200
    d = r.json()["docs"][0]
    assert len(d["sentences"]) == 2 and len(d["all"]) == 8


def test_validation():
    assert c.post("/api/summarize", data={}).status_code == 422
    assert c.post("/api/summarize", data={"text": "x", "n": 999}).status_code == 422
    assert c.post("/api/summarize", files={"file": ("a.exe", b"x")}).status_code == 415
    assert c.post("/api/summarize", data={"url": "http://127.0.0.1/"}).status_code == 422


def test_csv_upload(monkeypatch):
    monkeypatch.setattr(server.engine, "embed", fake_embed)
    csv = b"article_id,article_text\nA,Hello there big world.\nB,Another short doc here.\n"
    r = c.post("/api/summarize", files={"file": ("../../evil.csv", csv)})
    assert [d["name"] for d in r.json()["docs"]] == ["A", "B"]


def test_docx_export():
    import io

    import docx
    r = c.post("/api/export/docx", json={"docs": [{"name": "A", "summary": "s", "sentences": ["One fact.", "Two."], "keywords": ["k"]}]})
    assert r.status_code == 200
    text = "\n".join(p.text for p in docx.Document(io.BytesIO(r.content)).paragraphs)
    assert "One fact." in text and "Keywords: k" in text


def test_ai_off_by_default_and_rewrite(monkeypatch):
    monkeypatch.setattr(server.engine, "embed", fake_embed)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = c.get("/api/config").json()
    assert cfg["ai"] is False and set(cfg) == {"ai", "browser", "ready", "error"}
    assert c.post("/api/summarize", data={"text": DOC, "n": 2, "use_ai": "true"}).status_code == 503
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setattr(server.ai, "rewrite", lambda sents, bullets=False: "Fluent: " + sents[0])
    d = c.post("/api/summarize", data={"text": DOC, "n": 2, "use_ai": "true"}).json()["docs"][0]
    assert d["ai"].startswith("Fluent: ") and d["sentences"]
    csv = "article_id,article_text\n" + "".join(f"{i},Doc number {i} has words.\n" for i in range(6))
    r = c.post("/api/summarize", files={"file": ("d.csv", csv.encode())}, data={"use_ai": "true"})
    assert r.status_code == 422


def test_ai_failure_is_502(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setattr(server.ai, "rewrite", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(server.engine, "embed", fake_embed)
    assert c.post("/api/summarize", data={"text": DOC, "n": 2, "use_ai": "true"}).status_code == 502


def test_conflicting_length_options_are_a_422(monkeypatch):
    monkeypatch.setattr(server.engine, "embed", fake_embed)
    assert c.post("/api/summarize", data={"text": DOC, "n": 2, "ratio": 0.2}).status_code == 422


def test_damaged_pdf_is_a_422_not_a_500():
    assert c.post("/api/summarize", files={"file": ("bad.pdf", b"not a pdf")}).status_code == 422


def test_ping_records_that_the_page_is_alive():
    app = server.create_app()
    client = TestClient(app)
    assert app.state.last_ping == 0
    assert client.post("/api/ping").json() == {"ok": True}
    assert app.state.last_ping > 0
