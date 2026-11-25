"""Download the evaluation sample: 500 CNN/DailyMail test articles, evenly spaced through the 11,490-article test split.

    python evaluation/fetch_data.py            # writes evaluation/cnn_dailymail_500.jsonl (git-ignored)

The sample is deterministic (same offsets every time), so any other implementation, for example the Android app,
can be scored on exactly the same articles. evaluation/sample_ids.txt lists the article ids.
"""
import json
import time
import urllib.request
from pathlib import Path

API = "https://datasets-server.huggingface.co/rows?dataset=abisee/cnn_dailymail&config=3.0.0&split=test&offset={o}&length={n}"
TOTAL, CHUNKS, PER_CHUNK = 11490, 20, 25
OUT = Path(__file__).with_name("cnn_dailymail_500.jsonl")


def fetch(offset, n, tries=4):
    for t in range(tries):
        try:
            with urllib.request.urlopen(API.format(o=offset, n=n), timeout=60) as r:
                return [x["row"] for x in json.load(r)["rows"]]
        except Exception:
            if t == tries - 1:
                raise
            time.sleep(2 * (t + 1))


def main():
    stride = (TOTAL - PER_CHUNK) // (CHUNKS - 1)
    rows = []
    for c in range(CHUNKS):
        rows += fetch(c * stride, PER_CHUNK)
        print(f"  {len(rows)} articles", end="\r", flush=True)
    OUT.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    OUT.with_name("sample_ids.txt").write_text("\n".join(r["id"] for r in rows) + "\n")
    print(f"wrote {len(rows)} articles to {OUT.name}")


if __name__ == "__main__":
    main()
