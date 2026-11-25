"""Turn any source (text, file, URL, CSV) into [(name, text)] documents."""
import csv
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

MAX_BYTES = 50_000_000
MAX_PAGE = 5_000_000
EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".csv"}


class NoTextError(ValueError):
    """A document that opened fine but has no text in it (a scanned PDF, an empty file)."""


def _fetch(url):
    if urlparse(url).scheme not in ("http", "https"):
        raise ValueError(f"bad URL: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; Summarizer)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            ctype = r.headers.get("Content-Type", "text/html")
            if "html" not in ctype and "text" not in ctype:
                raise ValueError("URL is not a web page")
            data = r.read(MAX_PAGE + 1)
    except (urllib.error.URLError, TimeoutError) as e:
        raise ValueError(f"could not fetch {url}: {getattr(e, 'reason', e)}")
    if len(data) > MAX_PAGE:
        raise ValueError("page too large")
    return data


def from_url(url):
    import trafilatura
    text = trafilatura.extract(_fetch(url))
    if not text:
        raise ValueError(f"could not extract text from {url}")
    return [(url, text)]


def from_pdf(path):
    from pypdf import PdfReader
    name = Path(path).name
    try:
        reader = PdfReader(path)
        if reader.is_encrypted and not reader.decrypt(""):  # many PDFs are "encrypted" with an empty password
            raise ValueError(f"{name} is password protected")
        pages = [p.extract_text() or "" for p in reader.pages]
    except ValueError:
        raise
    except Exception as e:  # pypdf raises its own error types for damaged files
        raise ValueError(f"could not read {name} as a PDF ({type(e).__name__})") from e
    text = "\n".join(pages)
    if not text.strip():
        raise NoTextError(f"{name} has {len(pages)} page{'s' if len(pages) != 1 else ''} but no text. "
                          "It is probably a scan (pictures of pages), and OCR is not supported yet. "
                          "Run it through an OCR tool first, then try again.")
    return [(name, text)]


def from_docx(path):
    import docx
    try:
        return [(Path(path).name, "\n".join(p.text for p in docx.Document(path).paragraphs))]
    except Exception as e:  # not a zip, missing parts, ...
        raise ValueError(f"could not read {Path(path).name} as a Word file ({type(e).__name__})") from e


def from_csv(path, column=None, id_column=None):
    """One doc per row. Defaults: 'article_text' (or the first column) for text, 'article_id' (or row number) for names."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return []
    cols = list(rows[0])
    column = column or ("article_text" if "article_text" in cols else cols[0])
    if column not in cols:
        raise ValueError(f"column {column!r} not in {cols}")
    id_column = id_column or ("article_id" if "article_id" in cols else None)
    return [(str(r[id_column]) if id_column else str(i + 1), r[column] or "") for i, r in enumerate(rows)]


def load(source: str, column: str | None = None) -> list[tuple[str, str]]:
    """Turn a source into ``[(name, text), ...]``.

    source: a web page URL, a file path (.txt .md .pdf .docx .csv), or raw text.
    Raises FileNotFoundError when it looks like a file path but doesn't exist (so a typo isn't summarized as text).
    """
    if not isinstance(source, str):
        raise TypeError(f"source must be a str, not {type(source).__name__}")
    if source.startswith(("http://", "https://")):
        return from_url(source)
    p = Path(source) if "\n" not in source and len(source) < 4096 else None
    try:
        is_file = bool(p and p.is_file())
    except (OSError, ValueError):  # characters a filesystem rejects: it's text
        is_file = False
    if is_file:
        if p.stat().st_size > MAX_BYTES:
            raise ValueError("file too large")
        ext = p.suffix.lower()
        if ext == ".pdf":
            return from_pdf(p)
        if ext == ".docx":
            return from_docx(p)
        if ext == ".csv":
            return from_csv(p, column)
        return [(p.name, p.read_text(encoding="utf-8", errors="replace"))]
    if p and p.suffix.lower() in EXTENSIONS and not any(c.isspace() for c in source):
        raise FileNotFoundError(f"no such file: {source}")
    return [("text", source)]
