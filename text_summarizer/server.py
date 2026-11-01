"""FastAPI app: the JSON API and the UI that the desktop window (or, as a fallback, your browser) shows."""
import tempfile
import threading
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import ai, engine, ingest

STATIC = Path(__file__).parent / "static"
MAX_UPLOAD = 25_000_000
MAX_TEXT = 2_000_000
MAX_AI_DOCS = 5  # each AI document is a paid API call
ALLOWED = {".txt", ".md", ".pdf", ".docx", ".csv"}


class ExportDoc(BaseModel):
    name: str
    summary: str
    sentences: list[str] = []
    keywords: list[str] = []


class ExportBody(BaseModel):
    docs: list[ExportDoc]


def create_app(browser: bool = False):
    app = FastAPI(title="Summarizer")
    app.state.browser = browser    # True when the UI is in a browser tab instead of the native window
    app.state.last_ping = 0.0      # in browser mode the page pings us, so the app can quit when the tab closes
    model = {"ready": False, "error": None}  # lets the UI explain the first-run download

    def warm():
        try:
            engine.warm_up()
            model["ready"] = True
        except Exception as e:  # offline on first run, disk full, ...
            model["error"] = f"{type(e).__name__}: {e}"[:300]

    threading.Thread(target=warm, daemon=True).start()

    @app.post("/api/summarize")
    def summarize(text: str = Form(""), url: str = Form(""), file: UploadFile | None = File(None),
                  n: int | None = Form(None), ratio: float | None = Form(None), column: str = Form(""), use_ai: bool = Form(False), bullets: bool = Form(False)):
        if n is not None and not 1 <= n <= 50:
            raise HTTPException(422, "sentences must be 1-50")
        if ratio is not None and not 0.01 <= ratio <= 0.9:
            raise HTTPException(422, "ratio must be 0.01-0.9")
        try:
            if file and file.filename:
                ext = Path(file.filename).suffix.lower()
                if ext not in ALLOWED:
                    raise HTTPException(415, f"unsupported file type {ext or '?'}; use {', '.join(sorted(ALLOWED))}")
                data = file.file.read(MAX_UPLOAD + 1)
                if len(data) > MAX_UPLOAD:
                    raise HTTPException(413, "file too large (25 MB max)")
                with tempfile.TemporaryDirectory() as d:  # fixed name: never trust the client's filename
                    p = Path(d) / f"upload{ext}"
                    p.write_bytes(data)
                    docs = ingest.load(str(p), column or None)
                docs = [(file.filename if n_ == "upload" + ext else n_, t) for n_, t in docs]
            elif url.strip():
                docs = ingest.load(url.strip())
            elif text.strip():
                if len(text) > MAX_TEXT:
                    raise HTTPException(413, "text too long")
                docs = [("Pasted text", text)]
            else:
                raise HTTPException(422, "provide text, a URL or a file")
        except ValueError as e:
            raise HTTPException(422, str(e))
        if use_ai and len(docs) > MAX_AI_DOCS:
            raise HTTPException(422, f"AI rewrite is limited to {MAX_AI_DOCS} documents per request")
        out = []
        for name, t in docs[:200]:
            try:
                r = engine.summarize(t, n=n, ratio=ratio).to_dict()
            except ValueError as e:  # e.g. both n and ratio sent
                raise HTTPException(422, str(e))
            r["name"], r["ai"] = name, None
            if use_ai and r["sentences"]:
                r["ai"] = _rewrite(r["sentences"], bullets)
            out.append(r)
        return {"docs": out, "truncated": len(docs) > 200}

    def _rewrite(sentences, bullets):
        if not ai.available():
            raise HTTPException(503, "AI rewrite is not configured on this server (set ANTHROPIC_API_KEY)")
        try:
            return ai.rewrite(sentences, bullets)
        except ImportError:
            raise HTTPException(503, "AI rewrite needs the anthropic package: pip install anthropic")
        except Exception as e:  # anthropic.APIError and friends: keep the extractive result usable
            raise HTTPException(502, f"AI rewrite failed: {type(e).__name__}")

    @app.get("/api/config")
    def config():
        return {"ai": ai.available(), "browser": app.state.browser, **model}

    @app.post("/api/ping")
    def ping():
        app.state.last_ping = time.time()
        return {"ok": True}

    @app.post("/api/export/docx")
    def export_docx(body: ExportBody):
        import io

        import docx
        d = docx.Document()
        d.add_heading("Summary", 0)
        for x in body.docs[:200]:
            d.add_heading(x.name[:200], 1)
            if x.sentences:
                for sent in x.sentences:
                    d.add_paragraph(sent, style="List Bullet")
            else:
                d.add_paragraph(x.summary)
            if x.keywords:
                d.add_paragraph().add_run("Keywords: " + ", ".join(x.keywords)).italic = True
        buf = io.BytesIO()
        d.save(buf)
        return Response(buf.getvalue(), headers={"Content-Disposition": 'attachment; filename="summary.docx"'},
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    # same files GitHub Pages serves; mounted last so /api routes win
    app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
    return app
