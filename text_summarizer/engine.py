"""Extractive summarizer: sentence embeddings + per-document TextRank + MMR."""
import math
import re
import threading
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pysbd

from . import ingest

MODEL = "BAAI/bge-small-en-v1.5"  # ~130 MB ONNX, CPU only, downloaded on first use
CHUNK = 150          # sentences per chunk for long documents
DUP = 0.92           # cosine above this = same sentence
CHUNK_LIMIT = 300   # documents longer than this go through map-reduce

_seg = pysbd.Segmenter(language="en", clean=False)

# ponytail: English-only stopwords for keywords; swap for a language-aware list if multilingual matters
_STOP = set("""a about above after again all also am an and any are as at be because been before being below between both
but by can did do does doing down during each few for from further had has have having he her here hers him his how i if in
into is it its just me more most my no nor not now of off on once only or other our out over own same she should so some such
than that the their them then there these they this those through to too under until up very was we were what when where
which while who whom why will with would you your""".split())


_lock = threading.Lock()  # the startup warm-up and a first request must not both download the model


def _model():
    with _lock:
        return _load()


@lru_cache(maxsize=1)
def _load():
    import os
    from fastembed import TextEmbedding
    cache = os.environ.get("SUMMARIZER_CACHE") or os.path.join(os.path.expanduser("~"), ".cache", "summarizer")
    return TextEmbedding(MODEL, cache_dir=cache)  # fastembed's default is the temp dir, wiped on reboot


def embed(sentences: list[str]):
    """Default embedder: unit-norm float32 matrix, one row per sentence."""
    v = np.array(list(_model().embed(sentences)), dtype=np.float32)
    return v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    return [s.strip() for s in _seg.segment(text) if len(s.split()) >= 3]


def _minmax(x):
    r = x.max() - x.min()
    return (x - x.min()) / r if r > 1e-9 else np.zeros_like(x)


def _scores(E):
    """TextRank over the cosine graph (negatives clamped), blended with centroid and position priors."""
    n = len(E)
    S = np.clip(E @ E.T, 0, None)
    np.fill_diagonal(S, 0)
    P = S / np.maximum(S.sum(axis=1, keepdims=True), 1e-9)
    r = np.full(n, 1 / n)
    for _ in range(50):
        new = 0.15 / n + 0.85 * (P.T @ r)
        if np.abs(new - r).sum() < 1e-6:
            break
        r = new
    c = E.mean(axis=0)
    centroid = E @ (c / max(np.linalg.norm(c), 1e-9))
    pos = 1 / (1 + np.log1p(np.arange(n)))  # lead sentences carry the topic in news/reports/essays
    return _minmax(r) + 0.5 * _minmax(centroid) + 0.25 * pos


def _mmr(E, scores, k, lam=0.7):
    """Greedy pick: relevant but not redundant with what's already chosen."""
    scores = _minmax(scores)
    S = E @ E.T
    chosen = []
    for _ in range(min(k, len(E))):
        pen = S[:, chosen].max(axis=1) if chosen else np.zeros(len(E))
        m = lam * scores - (1 - lam) * pen
        m[pen > DUP] = -np.inf  # near-duplicates never make it in
        m[chosen] = -np.inf
        if not np.isfinite(m).any():
            break
        chosen.append(int(m.argmax()))
    return sorted(chosen)


def _keywords(sents, k=8):
    words = re.findall(r"[a-z][a-z'-]{2,}", " ".join(sents).lower())
    return [w for w, _ in Counter(w for w in words if w not in _STOP).most_common(k)]


def _length(n_sents, n, ratio):
    if n:
        return max(1, min(n, n_sents))
    return max(1, min(n_sents, round(n_sents * (ratio or 0.2)), 10))  # default: 20%, capped at 10


@dataclass(frozen=True)
class Summary:
    """The result of :func:`summarize`. ``str(summary)`` is the summary text; an empty summary is falsy."""

    text: str
    sentences: list[str]          # the chosen sentences, in original order
    indices: list[int]            # their positions in ``source_sentences``
    keywords: list[str]
    source_sentences: list[str]   # every sentence of the input

    def __str__(self) -> str:
        return self.text

    def __bool__(self) -> bool:
        return bool(self.text)

    @property
    def source_words(self) -> int:
        return sum(len(s.split()) for s in self.source_sentences)

    @property
    def summary_words(self) -> int:
        return sum(len(s.split()) for s in self.sentences)

    @property
    def reduction(self) -> float:
        """Fraction removed: 0.85 means the summary is 85% shorter than the source."""
        return 1 - self.summary_words / self.source_words if self.source_words else 0.0

    def bullets(self) -> str:
        return "\n".join(f"- {s}" for s in self.sentences)

    def to_dict(self) -> dict:
        return {"summary": self.text, "sentences": self.sentences, "indices": self.indices,
                "keywords": self.keywords, "all": self.source_sentences}

    def __getitem__(self, key: str):  # dict-style access, e.g. summary["keywords"]
        return self.to_dict()[key]


def summarize(text: str, *, n: int | None = None, ratio: float | None = None, embedder=None, lam: float = 0.7) -> Summary:
    """Summarize one document.

    n: number of sentences to keep (at most; fewer if the rest would only repeat what is already chosen). ratio: fraction of the document to keep (0 < ratio <= 1).
    With neither, keeps 20% of the sentences, at most 10. Pass one or the other, not both.
    embedder: optional ``callable(list[str]) -> array`` returning one unit-length vector per sentence.
    Long documents are chunked: each chunk shortlists candidates, then one final pass picks the summary.
    """
    if not isinstance(text, str):
        raise TypeError(f"text must be a str, not {type(text).__name__}")
    if n is not None and ratio is not None:
        raise ValueError("pass either n or ratio, not both")
    if n is not None and n < 1:
        raise ValueError("n must be at least 1")
    if ratio is not None and not 0 < ratio <= 1:
        raise ValueError("ratio must be greater than 0 and at most 1")
    embedder = embedder or embed  # looked up per call, so embed can be replaced (tests, custom models)
    sents = split_sentences(text)
    if not sents:
        return Summary("", [], [], [], [])
    k = _length(len(sents), n, ratio)
    if k >= len(sents):
        idx = list(range(len(sents)))
    else:
        E = np.asarray(embedder(sents), dtype=np.float32)
        cand = np.arange(len(sents))
        if len(sents) > CHUNK_LIMIT:  # map: shortlist per chunk (3x the share it would get)
            cand = np.concatenate([
                lo + np.array(_mmr(E[lo:lo + CHUNK], _scores(E[lo:lo + CHUNK]),
                                   max(1, math.ceil(3 * k * len(E[lo:lo + CHUNK]) / len(sents)))), dtype=int)
                for lo in range(0, len(sents), CHUNK)])
        Ec = E[cand]  # reduce: final ranking over candidates
        idx = [int(cand[i]) for i in _mmr(Ec, _scores(Ec), k, lam)]
    chosen = [sents[i] for i in idx]
    return Summary(" ".join(chosen), chosen, idx, _keywords(sents), sents)


def summarize_many(docs: Iterable[tuple[str, str]], **options) -> list[tuple[str, Summary]]:
    """docs: iterable of (name, text). Each document is ranked on its own. Options are those of :func:`summarize`."""
    return [(name, summarize(text, **options)) for name, text in docs]


def summarize_file(source: str, *, column: str | None = None, **options) -> list[tuple[str, Summary]]:
    """Summarize a file (.txt .md .pdf .docx .csv) or web page URL. A CSV gives one summary per row.

    Returns ``[(name, Summary), ...]``. Raises FileNotFoundError or ValueError with a readable message.
    """
    return summarize_many(ingest.load(source, column), **options)


def warm_up() -> None:
    """Load the embedding model now (downloads it on first use) so the first summarize() call is fast."""
    embed(["warm up the model"])
