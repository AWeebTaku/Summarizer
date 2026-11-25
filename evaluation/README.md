# Evaluation

ROUGE comparison of the summarizer against simple baselines on 500 CNN/DailyMail test articles. The headline table is in the
[main README](../README.md#evaluation). This folder has everything needed to reproduce it.

```bash
pip install -r requirements-eval.txt
python evaluation/fetch_data.py     # downloads the sample (2 MB, needs internet, git-ignored)
python evaluation/run_eval.py       # about 9 minutes the first time; embeddings are cached, so reruns take under a minute
```

- `fetch_data.py` takes 20 blocks of 25 articles at evenly spaced offsets through the 11,490-article test split. It is
  deterministic, so the sample is identical every run. `sample_ids.txt` lists the article ids, so another implementation
  (for example the Android app) can be scored on exactly the same articles.
- `run_eval.py` writes `results.json` (committed) and prints the tables.
- Each method picks 3 whole sentences, using the app's own sentence splitter, so the comparison is about which sentences are
  chosen. Scores are ROUGE-1/2/L F1 (`rouge-score`, stemming on, ROUGE-L is the summary-level variant) against the reference
  "highlights". Intervals are 95% paired bootstrap intervals over articles (2,000 resamples).
- Dateline and byline prefixes ("(CNN)", "By . Name .") are stripped from the article first.

## Methods

| Method | What it does |
|---|---|
| random | 3 random sentences (seeded) |
| lead-3 | the first 3 sentences |
| textrank (tf-idf) | classic TextRank: PageRank over a sentence graph weighted by TF-IDF cosine similarity |
| textrank (embeddings) | the same PageRank over sentence-embedding similarity; no priors, no MMR |
| this app | embeddings, TextRank plus topic and position priors, then MMR (what the app ships) |

The ablation rows switch off one part of the app at a time (MMR, the position prior, the centroid prior). A test checks the
ablation code reproduces the engine's scores exactly, so the rows really are variants of the app.

## Caveats

- One dataset, one domain (English news), one summary length. It says nothing about reports, papers or other languages.
- ROUGE measures word overlap with a human summary. It rewards the lead sentences of news and can't tell a faithful summary
  from a lucky one.
- The ablation is read from the same 500 articles it is reported on. Don't tune the engine on it without a separate
  development set.
