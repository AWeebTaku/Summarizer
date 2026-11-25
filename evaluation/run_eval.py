"""ROUGE evaluation of the summarizer against simple baselines.

    python evaluation/fetch_data.py                 # once: download the 500-article sample
    python evaluation/run_eval.py                   # -n 3 sentences per summary (the CNN/DailyMail convention)
    python evaluation/run_eval.py --limit 50        # quick check

Every method picks 3 whole sentences from the article, and every method uses the same sentence splitter as the app,
so the comparison is about *which* sentences are chosen. Scores are ROUGE-1/2/L F1 (rouge-score, with stemming) against
the human-written "highlights", averaged over the sample, with 95% bootstrap intervals for the differences.
"""
import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from text_summarizer import engine  # noqa: E402

DATA = Path(__file__).with_name("cnn_dailymail_500.jsonl")
CLEAN_LEAD = re.compile(r"^(?:\(CNN\)|By \. [^.]{1,60} \. |UPDATED: \. [^.]{1,40} \. )\s*")


def clean(article: str) -> str:
    """CNN/DailyMail articles start with a dateline or byline ("(CNN)", "By . Name ."). Not part of the story."""
    return CLEAN_LEAD.sub("", article.strip())


# ---- the methods: each takes a list of sentences, returns the sorted indices it picks -----------------------------

def lead3(sents, k=3):
    return list(range(min(k, len(sents))))


def random3(sents, k=3, _rng=random.Random(0)):
    return sorted(_rng.sample(range(len(sents)), min(k, len(sents))))


def _pagerank(S, d=0.85, iters=100):
    n = len(S)
    P = S / np.maximum(S.sum(axis=1, keepdims=True), 1e-9)
    r = np.full(n, 1 / n)
    for _ in range(iters):
        new = (1 - d) / n + d * (P.T @ r)
        if np.abs(new - r).sum() < 1e-8:
            break
        r = new
    return r


def _tfidf(sents):
    toks = [[w for w in re.findall(r"[a-z][a-z'-]+", s.lower()) if w not in engine._STOP] for s in sents]
    vocab = {w: i for i, w in enumerate(sorted({w for t in toks for w in t}))}
    if not vocab:
        return np.zeros((len(sents), 1))
    tf = np.zeros((len(sents), len(vocab)))
    for i, t in enumerate(toks):
        for w in t:
            tf[i, vocab[w]] += 1
    df = (tf > 0).sum(axis=0)
    X = tf * np.log((1 + len(sents)) / (1 + df))
    return X / np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-9)


def textrank_tfidf(sents, k=3):
    """Classic TextRank (Mihalcea and Tarau): PageRank over a sentence graph weighted by TF-IDF cosine similarity."""
    if len(sents) <= k:
        return list(range(len(sents)))
    X = _tfidf(sents)
    S = X @ X.T
    np.fill_diagonal(S, 0)
    return sorted(np.argsort(-_pagerank(S))[:k].tolist())


def textrank_embeddings(sents, k=3, E=None):
    """The same PageRank idea, but over sentence-embedding similarity. No position prior, no centroid, no MMR."""
    if len(sents) <= k:
        return list(range(len(sents)))
    S = np.clip(E @ E.T, 0, None)
    np.fill_diagonal(S, 0)
    return sorted(np.argsort(-_pagerank(S))[:k].tolist())


def _blend(E, w_centroid=0.5, w_pos=0.25):
    """engine._scores with the prior weights exposed, so each part can be switched off for the ablation."""
    n = len(E)
    S = np.clip(E @ E.T, 0, None)
    np.fill_diagonal(S, 0)
    r = engine._minmax(_pagerank(S))
    c = E.mean(axis=0)
    centroid = E @ (c / max(np.linalg.norm(c), 1e-9))
    pos = 1 / (1 + np.log1p(np.arange(n)))
    return r + w_centroid * engine._minmax(centroid) + w_pos * pos


def ablation(sents, k, E, w_centroid, w_pos, use_mmr):
    if len(sents) <= k:
        return list(range(len(sents)))
    sc = _blend(E, w_centroid, w_pos)
    return engine._mmr(E, sc, k) if use_mmr else sorted(np.argsort(-sc)[:k].tolist())


def summarizer(sents, k=3, E=None):
    """The app's engine: embeddings, TextRank + topic + position priors, then MMR."""
    if len(sents) <= k:
        return list(range(len(sents)))
    return engine._mmr(E, engine._scores(E), k)


METHODS = ["random", "lead-3", "textrank (tf-idf)", "textrank (embeddings)", "this app"]
ABLATIONS = {  # what each part of the app contributes: (centroid weight, position weight, MMR on/off)
    "app, no MMR": (0.5, 0.25, False),
    "app, no position prior": (0.5, 0.0, True),
    "app, no centroid prior": (0.0, 0.25, True),
    "app, TextRank only": (0.0, 0.0, False),
}
ALL = METHODS + list(ABLATIONS)

CACHE = Path(__file__).with_name(".cache")


def embeddings(article_id, sents):
    """Sentence embeddings are the slow part, so keep them between runs (git-ignored)."""
    f = CACHE / f"{article_id}.npy"
    if f.exists():
        E = np.load(f)
        if len(E) == len(sents):
            return E
    E = engine.embed(sents)
    CACHE.mkdir(exist_ok=True)
    np.save(f, E)
    return E


def pick_all(article_id, article, k=3):
    sents = engine.split_sentences(clean(article))
    if not sents:
        return {m: [] for m in ALL}, sents
    E = embeddings(article_id, sents) if len(sents) > k else None
    out = {
        "random": random3(sents, k),
        "lead-3": lead3(sents, k),
        "textrank (tf-idf)": textrank_tfidf(sents, k),
        "textrank (embeddings)": textrank_embeddings(sents, k, E),
        "this app": summarizer(sents, k, E),
    }
    for name, (wc, wp, mmr) in ABLATIONS.items():
        out[name] = ablation(sents, k, E, wc, wp, mmr)
    return out, sents


def _check_blend_matches_engine():
    rng = np.random.default_rng(1)
    E = rng.normal(size=(12, 16)).astype(np.float32)
    E /= np.linalg.norm(E, axis=1, keepdims=True)
    assert np.allclose(_blend(E), engine._scores(E), atol=1e-4), "ablation weights drifted from engine._scores"


def main():
    _check_blend_matches_engine()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, help="only the first N articles")
    ap.add_argument("-k", type=int, default=3, help="sentences per summary")
    ap.add_argument("--out", default=str(Path(__file__).with_name("results.json")))
    a = ap.parse_args()
    if not DATA.exists():
        sys.exit("no data: run  python evaluation/fetch_data.py  first")

    from rouge_score import rouge_scorer
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeLsum"], use_stemmer=True)
    rows = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines()][: a.limit]

    scores = {m: [] for m in ALL}
    t0 = time.time()
    for i, row in enumerate(rows, 1):
        picks, sents = pick_all(row["id"], row["article"], a.k)
        if not sents:
            continue
        for m in ALL:
            summary = "\n".join(sents[j] for j in picks[m])
            s = scorer.score(row["highlights"], summary)
            scores[m].append([s["rouge1"].fmeasure, s["rouge2"].fmeasure, s["rougeLsum"].fmeasure])
        if i % 25 == 0:
            print(f"  {i}/{len(rows)}  {time.time() - t0:.0f}s", end="\r", flush=True)
    print()

    A = {m: np.array(v) * 100 for m, v in scores.items()}
    n = len(A["lead-3"])
    rng = np.random.default_rng(0)
    idx = rng.integers(0, n, size=(2000, n))  # bootstrap resamples, shared by all comparisons (paired)

    def ci(diff):  # 95% interval of the mean of `diff` (shape n)
        means = diff[idx].mean(axis=1)
        return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))

    result = {"articles": n, "sentences_per_summary": a.k, "dataset": "CNN/DailyMail 3.0.0 test, 500 evenly spaced articles",
              "methods": {}, "this_app_minus": {}}
    print(f"\n{n} articles, {a.k} sentences each. ROUGE F1 x100 (higher is better)\n")
    print(f"{'method':<24}{'ROUGE-1':>9}{'ROUGE-2':>9}{'ROUGE-L':>9}")
    for m in ALL:
        mean = A[m].mean(axis=0)
        result["methods"][m] = {"rouge1": round(mean[0], 2), "rouge2": round(mean[1], 2), "rougeL": round(mean[2], 2)}
        print(f"{m:<24}{mean[0]:>9.2f}{mean[1]:>9.2f}{mean[2]:>9.2f}")
    print("\nthis app minus each baseline (mean difference, 95% bootstrap interval)")
    for m in METHODS[:-1]:
        d = A["this app"] - A[m]
        row = {}
        parts = []
        for j, name in enumerate(["rouge1", "rouge2", "rougeL"]):
            lo, hi = ci(d[:, j])
            row[name] = {"diff": round(float(d[:, j].mean()), 2), "ci95": [round(lo, 2), round(hi, 2)]}
            parts.append(f"{name} {d[:, j].mean():+.2f} [{lo:+.2f}, {hi:+.2f}]")
        result["this_app_minus"][m] = row
        print(f"  vs {m:<22}" + "   ".join(parts))
    print("\nablation: this app minus a variant with one part removed (positive = that part helps)")
    result["ablation_app_minus"] = {}
    for m in ABLATIONS:
        d = A["this app"] - A[m]
        lo, hi = ci(d[:, 0])
        result["ablation_app_minus"][m] = {"rouge1": {"diff": round(float(d[:, 0].mean()), 2), "ci95": [round(lo, 2), round(hi, 2)]}}
        print(f"  vs {m:<26} rouge1 {d[:, 0].mean():+.2f} [{lo:+.2f}, {hi:+.2f}]")
    result["seconds"] = round(time.time() - t0)
    Path(a.out).write_text(json.dumps(result, indent=2) + "\n")
    print(f"\nsaved {a.out}")


if __name__ == "__main__":
    main()
