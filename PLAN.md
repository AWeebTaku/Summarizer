# Summarizer: plan

Reference: `../career-job-search-and-project-priorities.md` (priorities), `../career-role-market-research.md` (market evidence), `../profile-resume.md` and `../profile-portfolio.md` (how to present it).

## Brief

**Status:** built; evaluation, edge cases and Known limits done (2026-11-25). **One line:** Offline summarizer that picks real sentences from PDFs, Word files, web pages and CSV batches.

**Roles it serves:** Desktop (lead); backend/NLP (support)

**Stack:** Python, ONNX Runtime, sentence embeddings, TextRank, MMR

**Resume and portfolio line (truthful, edit numbers only if they change):**
- Embeds sentences, ranks with TextRank, selects with MMR, so it never invents text.
- Desktop app, CLI and library with installers and CI on three operating systems.

**Proof gaps (what a reviewer will look for):**
- No try-in-browser demo. (Evaluation numbers and 'Known limits' now exist.)

**Next (only this):**
Optional hosted demo (deliberately not built, see the status log). Decide what to do about the topic (centroid) prior, using a separate development set.

## Suggestions and status log

Priority: **Maintain, low effort.** Already your most complete app.

1. Add an **evaluation**: ROUGE vs a baseline (lead-3, plain TextRank) on CNN/DailyMail or a small set; put the table in README. This turns it from "app" into "measured work".
2. Cover edge cases: scanned PDFs (no text), very short input, non-English text (detect and warn).
3. Add a "Known limits" README section (extractive only, English-tuned model).
4. Keep releases tidy: confirm installers build in CI for all 3 OSes; keep CHANGELOG current.
5. Optional AI rewrite: document privacy clearly (what is sent, to whom).

Skip: new input formats, UI polish, until the evaluation exists.

### Status update (2026-11-11) and new priority

Priority: **High.** It is the base for the Android app (see `../Summarizer-Android/PLAN.md`).

Done: CI, installers, pages and release workflows already exist.
Left:
- [ ] ROUGE evaluation (this repo vs lead-3 and plain TextRank), results table in the README. Reuse the same eval set for the Android app.
- [ ] "Known limits" README section.
- [ ] Edge cases: scanned PDFs, very short input, non-English text.

### Role-focus update (2026-11-25)

**Roles:** Desktop (lead), backend/NLP (support). **Priority: one upgrade, then maintain.**
- [ ] **ROUGE evaluation** vs lead-3 and plain TextRank; one table in the README. This is what makes it a technical project.
- [ ] A **hosted web demo** (paste text, get a summary) would let hiring managers try it without installing; the repo already has `text_summarizer/server.py`. Optional: the ~130 MB model may need a smaller model or a free-tier-friendly setup.
- [ ] "Known limits" section, scanned-PDF handling, non-English warning.
- [ ] Resume line: embeddings + TextRank + MMR, offline, installers on three OSes; add the ROUGE numbers when they exist.

### Status update (2026-11-25, work done)

- [x] **ROUGE evaluation** in `evaluation/` (500 CNN/DailyMail test articles; random, lead-3, TF-IDF TextRank, embedding TextRank; bootstrap intervals; component ablation). Table and caveats in the README. Result: beats random (+2.9 ROUGE-1) and embedding-only TextRank (+1.6), but **loses to classic TF-IDF TextRank (-1.3) and lead-3 (-8.0) on news**. The ablation shows MMR and the position prior help and the topic prior slightly hurts (-0.6). `evaluation/sample_ids.txt` pins the article set for the Android app to reuse.
- [x] **"Known limits"** README section, and the AI rewrite's privacy stated plainly (what is sent, to whom, and that it is the one mode that can invent text).
- [x] **Edge cases:** scanned PDF (clear error, tested), password-protected PDF, very short input (returned whole with a note), non-English text (warning; heuristic flagged 1 of 500 real English articles, a golf leaderboard). Warnings show in the command line, the API and the app. Also fixed keywords being cut at accented letters.
- [ ] **Hosted web demo: not built, on purpose.** The hosted web app was removed earlier by decision (no login or rate limiting on a public server, an SSRF-prone URL fetcher, a 130 MB model). If wanted later, the safest shape is a text-paste-only demo on a free CPU host (for example a Hugging Face Space) with URL and file input disabled.
- [ ] **Resume line:** add the numbers only as measured: embeddings + TextRank + MMR beats random and embedding-only TextRank on CNN/DailyMail ROUGE, and trails lead-3 and TF-IDF TextRank on news. Do not claim it beats baselines overall.
