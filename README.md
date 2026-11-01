# Summarizer

Summarize anything you need to read: articles, reports, PDFs, Word files, web pages, CSV batches, or pasted text. It picks the sentences that carry the most meaning and returns them in their original order, so it **never invents facts**. It runs on your own machine, with no account, and nothing leaves your computer unless you turn on the optional AI rewrite.

It comes as a **desktop app** for Windows, macOS and Linux, a **command-line tool**, and a **Python library**. The project's landing page is published with GitHub Pages from the `site/` folder.

- Input: pasted text, `.txt`, `.md`, `.pdf`, `.docx`, web page links, and CSV files (one summary per row)
- Output: copy, or export to Markdown, Word and CSV. It also shows keywords and can highlight the chosen sentences in the original text.

## How it works

1. The text is split into sentences.
2. Each sentence becomes a vector with a small sentence-embedding model (`bge-small-en-v1.5`, about 130 MB as ONNX). It runs on the CPU and needs no GPU.
3. Sentences are ranked per document by **TextRank** (similar sentences vouch for each other), plus how close each sentence is to the document's overall topic and a small bonus for opening sentences.
4. **MMR** picks the final sentences. It favours important sentences that don't repeat ones already chosen, and drops near-duplicates.
5. Long documents are processed in chunks, then ranked again, so a 100-page PDF stays fast.

---

## Install

### Option 1: Desktop app (no Python needed)

Download the file for your system from the [latest release](https://github.com/AWeebTaku/Summarizer/releases/latest) and unpack it.

| System | File | Run |
|---|---|---|
| Windows 10/11 | `Summarizer-Windows.zip` | Unzip, open the `Summarizer` folder, run `Summarizer.exe`. If SmartScreen warns, choose *More info, Run anyway*. Needs the Edge WebView2 runtime, which is already on current Windows. |
| macOS | `Summarizer-macOS.tar.gz` | Unpack, then **right-click `Summarizer.app`, choose Open** the first time (the app isn't signed). |
| Linux | `Summarizer-Linux.tar.gz` | Needs GTK + WebKit: `sudo apt install python3-gi gir1.2-webkit2-4.1` (Debian/Ubuntu), `sudo dnf install python3-gobject webkit2gtk4.1` (Fedora), `sudo pacman -S python-gobject webkit2gtk-4.1` (Arch). Then run `./Summarizer/Summarizer`. |

The first summary downloads the model once (about 130 MB) to `~/.cache/summarizer` (override with `SUMMARIZER_CACHE`). After that it works offline.

### Option 2: pip (Python 3.10 or newer)

```bash
pip install text-summarizer-aweebtaku              # library + CLI
pip install "text-summarizer-aweebtaku[desktop]"   # + the desktop app
pip install "text-summarizer-aweebtaku[ai]"        # + optional AI rewrite
```

Extras can be combined: `"text-summarizer-aweebtaku[desktop,ai]"`. A virtual environment or [`pipx`](https://pipx.pypa.io) is recommended. On Linux, the desktop window needs the GTK/WebKit packages from the table above.

### Option 3: From source

```bash
git clone https://github.com/AWeebTaku/Summarizer.git
cd Summarizer
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[desktop,ai,dev]"
pytest                             # optional: run the tests
```

## Use

### Command line

```bash
summarize report.pdf                        # a file: pdf, docx, txt, md, csv
summarize report.pdf -n 5 -f bullets        # five bullet points
summarize https://example.com/post          # a web page
summarize a.pdf b.docx -r 0.1 -f markdown -o notes.md   # several files into one Markdown file
summarize data.csv -c body                  # one summary per row, text in column "body"
cat essay.txt | summarize -k                # from stdin, with keywords
summarize report.pdf -f json | jq .         # for scripts
python -m text_summarizer report.pdf        # same command, no PATH needed
```

| Option | Meaning |
|---|---|
| `-n N` or `-r R` | keep at most N sentences, or the fraction R of the document (default: 20%, at most 10) |
| `-f text\|bullets\|markdown\|json`, `-b` | output format (`-b` is short for `-f bullets`) |
| `-k` | also print keywords (always included in markdown and json) |
| `-c NAME` | CSV column holding the text |
| `-o FILE` | write to a file instead of the terminal |
| `--ai` | rewrite the result as prose with Claude (see below) |

A source that fails (missing file, damaged PDF, unreachable page) prints an error and the others still run. The exit status is `0` on success, `1` if any source failed, and `2` for bad arguments. Run `summarize --help` for examples.

### Python

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

Everything is exported from the top level: `summarize`, `summarize_file`, `summarize_many` (a list of `(name, text)` pairs), `load` (turns any source into `(name, text)` pairs), `Summary`, and `warm_up()`, which loads the model up front so the first call isn't slow. Bad input raises `ValueError`, `FileNotFoundError` or `TypeError` with a readable message. The package is typed (`py.typed`).

CSV files use an `article_text` column (or the first column) and an optional `article_id` column. Pass `-c` / `column=` / the app's column field to choose another column.

## Optional: AI rewrite

The default summaries are extractive: offline, free and faithful to the source. For smoother prose you can have Claude rewrite the selected sentences.

1. `pip install "text-summarizer-aweebtaku[ai]"`
2. Set `ANTHROPIC_API_KEY` in the environment that starts the app.
3. Tick **AI rewrite** in the app. It only appears when a key is set.

Only the selected sentences are sent, not the whole document, and the model is told to add no facts. It is limited to 5 documents per request. The model defaults to `claude-opus-5-5`. Set `SUMMARIZER_MODEL=claude-haiku-5-5` for a cheaper one.

## Settings

| Variable | Purpose | Default |
|---|---|---|
| `SUMMARIZER_CACHE` | where the model is stored | `~/.cache/summarizer` |
| `ANTHROPIC_API_KEY` | enables AI rewrite | unset |
| `SUMMARIZER_MODEL` | model for AI rewrite | `claude-opus-5-5` |

## Troubleshooting

- **First run is slow:** the model is being downloaded once. Later runs start in about a second.
- **Linux: "You must have either QT or GTK ... installed":** install the GTK/WebKit packages from the install table. You can still use the `summarize` command without them.
- **Scanned PDFs return nothing:** the PDF has no text layer. OCR isn't supported yet.
- **Non-English text:** the sentence splitter and the default model are tuned for English.

## Project layout

```
text_summarizer/
  engine.py      ranking, MMR, keywords
  ingest.py      text / file / URL / CSV loading
  cli.py         the `summarize` command
  __main__.py    python -m text_summarizer
  desktop.py     desktop window (pywebview)
  server.py      local API the desktop window talks to
  static/        the app's interface (HTML/CSS/JS, self-hosted fonts)
  ai.py          optional Claude rewrite
site/            landing page, published to GitHub Pages
tests/           pytest suite
.github/workflows/  ci.yml (tests on Windows/macOS/Linux), pages.yml (landing page), release.yml (PyPI + desktop builds)
```

## Landing page (GitHub Pages)

`site/` is plain HTML, so there's nothing to build.

1. In the repository, open **Settings, Pages, Build and deployment, Source: GitHub Actions**.
2. Push to `main`, or run **Deploy landing page** from the Actions tab.
3. The site appears at `https://<your-username>.github.io/<repo-name>/`. Free Pages needs a public repository.

Preview it locally with `python -m http.server -d site` and open http://localhost:8000. The download buttons point at the latest GitHub release, so they work once a release exists. The page is AMOLED black with one blue accent and has three moving parts: the typing demo in the hero (its sentence picks come from the real engine), an interactive grid that lights up under the pointer, and spotlight borders on the feature cards. All of it respects `prefers-reduced-motion`. To refresh the app screenshot, replace `site/app-dark.png`.

## Contributing

```bash
pip install -e ".[desktop,ai,dev]"
pytest
```

Changes go in `CHANGELOG.md`.

## Releasing (maintainers)

Pushing a tag like `v2.0.0` runs the tests, publishes to PyPI (needs the `PYPI_API_TOKEN` repository secret), builds the desktop app on Windows, macOS and Linux, and attaches the archives to a GitHub release.

## Credits

Interface type is [Geist](https://vercel.com/font) (SIL Open Font License, bundled in `site/fonts` and `text_summarizer/static/fonts`). Icons are [Phosphor](https://phosphoricons.com) (MIT).

## License

MIT
