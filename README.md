# Summarizer

Summarize anything you need to read: articles, reports, PDFs, Word files, web pages, CSV batches, or pasted text. It picks the sentences that carry the most meaning and returns them in their original order, so it **never invents facts**. It runs on your own machine, with no account, and nothing leaves your computer unless you turn on the optional AI rewrite.

It is a **desktop app** for Windows, macOS and Linux. It also has a **command line** and can be used from Python code. The project's landing page is published with GitHub Pages from the `site/` folder.

- Input: pasted text, `.txt`, `.md`, `.pdf`, `.docx`, web page links, and CSV files (one summary per row)
- Output: copy, or export to Markdown, Word and CSV. It also shows keywords and can highlight the chosen sentences in the original text.

> Looking for the original version (GloVe embeddings and a tkinter window)? It is kept as the [v1.0.0 release](https://github.com/AWeebTaku/Summarizer/releases/tag/v1.0.0) for reference. Version 2 replaces it.

## How it works

1. The text is split into sentences.
2. Each sentence becomes a vector with a small sentence-embedding model (`bge-small-en-v1.5`, about 130 MB as ONNX). It runs on the CPU and needs no GPU.
3. Sentences are ranked per document by **TextRank** (similar sentences vouch for each other), plus how close each sentence is to the document's overall topic and a small bonus for opening sentences.
4. **MMR** picks the final sentences. It favours important sentences that don't repeat ones already chosen, and drops near-duplicates.
5. Long documents are processed in chunks, then ranked again, so a 100-page PDF stays fast.

---

## Evaluation

ROUGE F1 (x100, higher is better) on 500 CNN/DailyMail test articles, evenly sampled from the test split, picking 3 sentences each, scored against the human-written highlights:

| Method | ROUGE-1 | ROUGE-2 | ROUGE-L |
|---|---|---|---|
| random | 30.1 | 10.0 | 27.1 |
| lead-3 (first three sentences) | 40.9 | 18.4 | 37.4 |
| TextRank, TF-IDF similarity (classic) | 34.3 | 14.3 | 30.9 |
| TextRank, embedding similarity | 31.4 | 11.9 | 28.1 |
| **This app** (embeddings + priors + MMR) | 33.0 | 12.8 | 29.5 |

How to read it honestly:

- **It beats chance and plain embedding TextRank, by a clear margin.** vs random: +2.9 (+1.8 to +3.9) ROUGE-1 (95% interval). vs embedding-only TextRank: +1.6 (+1.1 to +2.1).
- **It loses to two simple baselines on news.** vs classic TF-IDF TextRank: -1.3 (-2.2 to -0.4). vs lead-3: -8.0 (-9.1 to -6.9). News writing puts the key facts in the first sentences, so lead-3 is famously hard to beat on this dataset, and ROUGE rewards the word overlap that TF-IDF similarity captures directly.
- **What the parts do** (this app minus a version with one part removed, ROUGE-1): MMR +0.7 (+0.3 to +1.1), position prior +0.9 (+0.5 to +1.3), topic (centroid) prior -0.6 (-0.9 to -0.3). MMR and the position prior help. The topic prior slightly **hurts** on this data. That is a finding to follow up with a separate development set, not something to tune away on the test articles.
- This measures overlap with a human summary on one English news dataset. It does not measure faithfulness (the app only returns sentences from your text, so that is true by construction), readability, other languages or other kinds of documents.

Reproduce it, and see the method details and caveats, in [`evaluation/`](evaluation/README.md). `evaluation/sample_ids.txt` pins the exact articles so other implementations can be scored on the same set.

## Install

### Option 1: Download the app (no Python needed)

Download the file for your system from the [latest release](https://github.com/AWeebTaku/Summarizer/releases/latest).

| System | File |
|---|---|
| Windows | `Summarizer-setup.exe` (installs for the current user, no admin rights) or `Summarizer.msi` (all users) |
| macOS (Apple Silicon) | `Summarizer-macOS-arm64.dmg` |
| Debian, Ubuntu, Mint | `Summarizer-amd64.deb` (`sudo apt install ./Summarizer-amd64.deb`) |
| Fedora, openSUSE | `Summarizer-x86_64.rpm` (`sudo dnf install ./Summarizer-x86_64.rpm`, or `sudo zypper install ./Summarizer-x86_64.rpm`) |
| Arch, Manjaro | `Summarizer-x86_64.pkg.tar.zst` (`sudo pacman -U Summarizer-x86_64.pkg.tar.zst`) |
| Any Linux | `Summarizer-x86_64.AppImage` (`chmod +x Summarizer-x86_64.AppImage`, then run it) |

Things worth knowing:

- **The installers aren't code-signed yet**, so your system warns the first time.
  - *Windows:* in SmartScreen choose **More info, then Run anyway**.
  - *macOS:* open the disk image and drag Summarizer to Applications. On macOS 14 and earlier, right-click it and choose **Open**. On macOS 15 and later, try to open it once, then go to **System Settings, Privacy & Security** and choose **Open Anyway**. If macOS says the app is damaged, run `xattr -dr com.apple.quarantine /Applications/Summarizer.app`.
- **The macOS build is for Apple Silicon only.** On an Intel Mac, run the app from source (below).
- **Linux builds need glibc 2.35 or newer**: Ubuntu 22.04, Debian 12, Fedora 36 and later. They include their own browser engine (Qt WebEngine). The `.deb`, `.rpm` and Arch packages make your package manager fetch the few graphics libraries they need, and an AppImage expects the usual desktop graphics libraries (Mesa, which every desktop has). Running an AppImage on Ubuntu 22.04 or newer needs `libfuse2` (`sudo apt install libfuse2`).
- **The downloads are large** (about 260 MB on Linux) because each one carries the app's own copy of its libraries.
- The first summary downloads the language model once (about 130 MB) to `~/.cache/summarizer` (override with `SUMMARIZER_CACHE`). After that it works offline.
- Each release includes `SHA256SUMS.txt`. Check a download with `sha256sum -c SHA256SUMS.txt --ignore-missing`.

If a native window can't be opened on your machine (no display, a missing graphics library, a broken toolkit), the app **opens your default browser instead** and quits when you close the tab. You can force that with `--browser`.

### Option 2: Run from source (Python 3.10 or newer)

```bash
git clone https://github.com/AWeebTaku/Summarizer.git
cd Summarizer
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-desktop.txt
python -m text_summarizer.desktop  # the app
```

`requirements-desktop.txt` installs the window toolkit: WebView2 on Windows and WebKit on macOS come with the system, and on Linux it installs Qt, which brings its own browser engine (large, about 500 MB). If you only want the command line, or you'd rather use your browser, `pip install -r requirements.txt` is enough and `python -m text_summarizer.desktop --browser` runs the app in a browser tab.

On Linux you can use GTK instead of Qt: install `python3-gi` and `gir1.2-webkit2-4.1` (Debian, Ubuntu), `python3-gobject` and `webkit2gtk4.1` (Fedora) or `python-gobject` and `webkit2gtk-4.1` (Arch), create the environment with `python -m venv --system-site-packages .venv`, and run `pip install -r requirements.txt pywebview` instead.

## Use

### Command line

```bash
python -m text_summarizer report.pdf                        # a file: pdf, docx, txt, md, csv
python -m text_summarizer report.pdf -n 5 -f bullets        # five bullet points
python -m text_summarizer https://example.com/post          # a web page
python -m text_summarizer a.pdf b.docx -r 0.1 -f markdown -o notes.md   # several files into one Markdown file
python -m text_summarizer data.csv -c body                  # one summary per row, text in column "body"
cat essay.txt | python -m text_summarizer -k                # from stdin, with keywords
python -m text_summarizer report.pdf -f json | jq .         # for scripts
```

| Option | Meaning |
|---|---|
| `-n N` or `-r R` | keep at most N sentences, or the fraction R of the document (default: 20%, at most 10) |
| `-f text\|bullets\|markdown\|json`, `-b` | output format (`-b` is short for `-f bullets`) |
| `-k` | also print keywords (always included in markdown and json) |
| `-c NAME` | CSV column holding the text |
| `-o FILE` | write to a file instead of the terminal |
| `--ai` | rewrite the result as prose with Claude (see below) |

A source that fails (missing file, damaged PDF, unreachable page) prints an error and the others still run. The exit status is `0` on success, `1` if any source failed, and `2` for bad arguments. Run `python -m text_summarizer --help` for examples.

### Python

From a checkout of this repository (or with its folder on `PYTHONPATH`):

```python
from text_summarizer import summarize, summarize_file

summary = summarize(text, ratio=0.2)          # or n=5
print(summary)                                # the summary text
summary.sentences                             # the chosen sentences, in original order
summary.keywords                              # ['solar', 'energy', ...]
summary.reduction                             # 0.85 means 85% shorter than the source
summary.bullets()                             # "- first sentence\n- second sentence"

for name, summary in summarize_file("report.pdf"):   # also .docx .txt .md .csv or a URL; CSV gives one per row
    print(name, summary)
```

`summarize_many` takes a list of `(name, text)` pairs, `load` turns any source into `(name, text)` pairs, and `warm_up()` loads the model up front so the first call isn't slow. Bad input raises `ValueError`, `FileNotFoundError` or `TypeError` with a readable message.

CSV files use an `article_text` column (or the first column) and an optional `article_id` column. Pass `-c` / `column=` / the app's column field to choose another column.

## Optional: AI rewrite

The default summaries are extractive: offline, free and faithful to the source. For smoother prose you can have Claude rewrite the selected sentences.

1. `pip install anthropic`
2. Set `ANTHROPIC_API_KEY` in the environment that starts the app.
3. Tick **AI rewrite** in the app, or pass `--ai` on the command line. It only appears when a key is set.

**What is sent, and to whom.** Only when you tick **AI rewrite** (or pass `--ai`), the app sends the sentences it selected, plus a fixed instruction asking for a faithful rewrite, to the Anthropic API (`api.anthropic.com`) using your own key. Nothing else leaves your machine: not the rest of the document, the file name, the keywords or the URL. With the option off, which is the default, the app makes no network request except the one-time model download (and fetching a web page when you ask it to summarize a link). The app stores nothing: your key is read from the environment and never written to disk, and summaries are not saved anywhere unless you export them. What Anthropic keeps is governed by [its terms and privacy policy](https://www.anthropic.com/legal/privacy) and your account settings, so don't use the option on text you aren't allowed to share with a third party.

**It is also the one mode that can be wrong.** The default summary is made only of sentences from your document, so it cannot contain a fact the document doesn't. A rewrite is new text produced by a language model. It is told to add nothing, but check it against the original (use **Show in original**). It is limited to 5 documents per request. The model defaults to `claude-opus-5-5`. Set `SUMMARIZER_MODEL=claude-haiku-5-5` for a cheaper one.

## Settings

| Variable | Purpose | Default |
|---|---|---|
| `SUMMARIZER_CACHE` | where the model is stored | `~/.cache/summarizer` |
| `ANTHROPIC_API_KEY` | enables AI rewrite | unset |
| `SUMMARIZER_MODEL` | model for AI rewrite | `claude-opus-5-5` |
| `QTWEBENGINE_CHROMIUM_FLAGS` | Linux window: replaces the defaults `--no-sandbox --disable-gpu` | unset |

## Troubleshooting

- **First run is slow:** the model is being downloaded once. Later runs start in about a second.
- **The window doesn't open and a browser tab does instead:** that is the fallback working. It means a native window couldn't be created here, usually because there is no display or a graphics or toolkit library is missing. The message in the terminal says why. On Linux, installing your distribution's Mesa/OpenGL libraries (`libgl1`, `libegl1`) usually fixes it.
- **The app is still running after I closed the browser tab:** it quits about 20 seconds after the page stops responding. Press Ctrl+C in the terminal to stop it sooner.
- **AppImage does not start:** install `libfuse2`, or run it with `APPIMAGE_EXTRACT_AND_RUN=1 ./Summarizer-x86_64.AppImage`.
- **Windows says "Windows protected your PC", or macOS says the app can't be opened:** the installers aren't signed yet. See the notes under the download table.
- **Scanned PDFs return nothing:** the PDF has no text layer. OCR isn't supported yet.
- **Non-English text:** the sentence splitter and the default model are tuned for English.

## Known limits

- **It only picks sentences.** It never rewrites, merges or compresses, so a summary can read choppily, can start with a pronoun ("He said...") whose referent was left out, and can't combine two facts into one sentence. That is the price of never inventing text. The optional AI rewrite smooths this, with the caveats above.
- **It is tuned for English.** The sentence splitter, the stopword list used for keywords and the embedding model are English. Other languages still produce a summary, but a warning says it may be poor. The check is a heuristic, not a language detector: in 500 real English news articles it wrongly flagged one (a golf leaderboard, mostly names and scores), and it can't tell similar languages apart.
- **Scanned PDFs have no text.** A PDF made of page images gives a clear error ("N pages but no text") instead of an empty summary. OCR isn't included. A PDF with some scanned pages and some real text is summarized from the real text and the scanned pages are silently skipped.
- **Very short input is returned as is,** with a note, because there is nothing to leave out. A "sentence" needs at least three words, so headlines and fragments are ignored.
- **Tables, lists and code are poor input.** Sentence splitting assumes prose. Spreadsheet-like text, slides and source code are split in odd places.
- **On news, it does not beat simply taking the first three sentences, or classic TextRank** (see the evaluation above). I have measured only English news, so I can't say how it compares on reports, papers or meeting notes, where the key sentences are less often at the top.
- **Long documents are summarized in two passes** (a shortlist per chunk, then a final ranking), which is fast but can miss a sentence that only matters in context.
- **Size and warm-up.** The language model is about 130 MB and downloads on first use. Installers are 55 to 260 MB.
- **Web pages:** article extraction works on normal articles. Pages that need JavaScript to show their text, or sit behind a login or paywall, return little or nothing.

## Project layout

```
text_summarizer/
  engine.py      ranking, MMR, keywords
  ingest.py      text / file / URL / CSV loading
  cli.py         the command line
  desktop.py     the app: native window, browser fallback, self-tests
  server.py      local API the window talks to
  static/        the app's interface (HTML/CSS/JS, self-hosted fonts, icon)
  ai.py          optional Claude rewrite
packaging/       installers: build_bundle.py (PyInstaller), windows/ (Inno Setup, WiX), linux/ (nfpm, AppImage), icons/
site/            landing page, published to GitHub Pages
tests/           pytest suite
evaluation/      ROUGE evaluation against baselines (fetch_data.py, run_eval.py, results.json)
requirements.txt, requirements-desktop.txt, requirements-dev.txt, requirements-eval.txt
.github/workflows/  ci.yml (tests), installers.yml (builds and tests every installer), release.yml (GitHub release), pages.yml (landing page)
```

## Landing page (GitHub Pages)

`site/` is plain HTML, so there's nothing to build.

1. In the repository, open **Settings, Pages, Build and deployment, Source: GitHub Actions**.
2. Push to `main`, or run **Deploy landing page** from the Actions tab.
3. The site appears at `https://<your-username>.github.io/<repo-name>/`. Free Pages needs a public repository.

Preview it locally with `python -m http.server -d site` and open http://localhost:8000. The download buttons point at the latest GitHub release, so they work once a release exists. To refresh the app screenshot, replace `site/app-dark.png`.

## Contributing

```bash
pip install -r requirements-dev.txt
pytest
```

To rerun the ROUGE evaluation: `pip install -r requirements-eval.txt`, then see [`evaluation/`](evaluation/README.md). Changes go in `CHANGELOG.md`.

## Releasing (maintainers)

Nothing is published to PyPI: the downloads on the releases page are the product.

1. Bump `__version__` in `text_summarizer/__init__.py` and add a section to `CHANGELOG.md`.
2. **Try the installers first, without releasing anything:** run the *Build installers* workflow (Actions tab, or `gh workflow run installers.yml`). It builds the Windows `.exe` and `.msi`, the macOS `.dmg` and the four Linux formats. It tests each frozen app (including a real native window on all three systems), installs each installer, and runs the app's self-test from the installed copy. Linux packages are installed in clean Ubuntu, Debian, Fedora and Arch containers. Download the results from the run's artifacts to try them by hand.
3. Push a tag such as `v2.0.0`. The *Release* workflow rebuilds and tests everything, and only if all of it passes does it create the GitHub release with the installers and `SHA256SUMS.txt`.

To rebuild the installers for an existing tag, run the *Release* workflow by hand and enter the tag.

The installer pieces live in `packaging/`: `build_bundle.py` freezes the app, `windows/summarizer.iss` and `summarizer.wxs` make the Windows installers, `linux/nfpm.yaml` and `build.sh` make the `.deb`, `.rpm`, Arch package and AppImage, and `make_icons.py` regenerates the icons. Linux builds run on Ubuntu 22.04 on purpose, so they work on older distributions too.

## Credits

Interface type is [Geist](https://vercel.com/font) (SIL Open Font License, bundled in `site/fonts` and `text_summarizer/static/fonts`). Icons are [Phosphor](https://phosphoricons.com) (MIT).

## License

MIT
