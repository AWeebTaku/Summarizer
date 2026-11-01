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
- **The macOS build is for Apple Silicon only.** Intel Macs can run the app from the pip install below.
- **Linux builds need glibc 2.35 or newer**: Ubuntu 22.04, Debian 12, Fedora 36 and later. They include their own browser engine (Qt WebEngine). The `.deb`, `.rpm` and Arch packages make your package manager fetch the few graphics libraries they need, and an AppImage expects the usual desktop graphics libraries (Mesa, which every desktop has). Running an AppImage on Ubuntu 22.04 or newer needs `libfuse2` (`sudo apt install libfuse2`).
- **The downloads are large** (about 260 MB on Linux) because each one carries the app's own copy of its libraries.
- The first summary downloads the language model once (about 130 MB) to `~/.cache/summarizer` (override with `SUMMARIZER_CACHE`). After that it works offline.
- Each release includes `SHA256SUMS.txt`. Check a download with `sha256sum -c SHA256SUMS.txt --ignore-missing`.

### Option 2: pip (Python 3.10 or newer)

```bash
pip install text-summarizer-aweebtaku              # library + CLI
pip install "text-summarizer-aweebtaku[desktop]"   # + the desktop app
pip install "text-summarizer-aweebtaku[ai]"        # + optional AI rewrite
```

Extras can be combined: `"text-summarizer-aweebtaku[desktop,ai]"`. A virtual environment or [`pipx`](https://pipx.pypa.io) is recommended.

**Linux:** the desktop window needs a GUI toolkit. The simplest choice is `pip install "text-summarizer-aweebtaku[desktop,qt]"`, which brings its own Qt (large, about 500 MB). Or use GTK instead: install `python3-gi` and `gir1.2-webkit2-4.1` (Debian, Ubuntu), `python3-gobject` and `webkit2gtk4.1` (Fedora) or `python-gobject` and `webkit2gtk-4.1` (Arch), and create the virtual environment with `python -m venv --system-site-packages .venv` so it can see them.

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
- **Linux, installed with pip: "You must have either QT or GTK ... installed":** add the Qt extra (`pip install "text-summarizer-aweebtaku[desktop,qt]"`) or use one of the packages from the download table, which include everything. The `summarize` command works without any of this.
- **AppImage does not start:** install `libfuse2`, or run it with `APPIMAGE_EXTRACT_AND_RUN=1 ./Summarizer-x86_64.AppImage`.
- **Windows says "Windows protected your PC", or macOS says the app can't be opened:** the installers aren't signed yet. See the notes under the download table.
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
  static/        the app's interface (HTML/CSS/JS, self-hosted fonts, icon)
  ai.py          optional Claude rewrite
packaging/       installers: build_bundle.py (PyInstaller), windows/ (Inno Setup, WiX), linux/ (nfpm, AppImage), icons/
site/            landing page, published to GitHub Pages
tests/           pytest suite
.github/workflows/  ci.yml (tests), installers.yml (builds and tests every installer), release.yml (PyPI + GitHub release), pages.yml (landing page)
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

1. Bump `__version__` in `text_summarizer/__init__.py` and add a section to `CHANGELOG.md`.
2. **Try the installers first, without releasing anything:** run the *Build installers* workflow (Actions tab, or `gh workflow run installers.yml`). It builds the Windows `.exe` and `.msi`, the macOS `.dmg` and the four Linux formats, then installs each one and runs the app's self-test (`summarizer-desktop --selftest`). Linux packages are installed in clean Ubuntu, Fedora and Arch containers. Download the results from the run's artifacts to try them by hand.
3. Push a tag such as `v2.0.1`. The *Release* workflow rebuilds and tests everything, and only if all of it passes does it publish to PyPI (needs the `PYPI_API_TOKEN` repository secret) and create the GitHub release with the installers and `SHA256SUMS.txt`. A PyPI version number can never be reused, which is why the order matters.

To rebuild the installers for an existing tag without touching PyPI, run the *Release* workflow by hand and enter the tag.

The installer pieces live in `packaging/`: `build_bundle.py` freezes the app, `windows/summarizer.iss` and `summarizer.wxs` make the Windows installers, `linux/nfpm.yaml` and `build.sh` make the `.deb`, `.rpm`, Arch package and AppImage, and `make_icons.py` regenerates the icons. Linux builds run on Ubuntu 22.04 on purpose, so they work on older distributions too.

## Credits

Interface type is [Geist](https://vercel.com/font) (SIL Open Font License, bundled in `site/fonts` and `text_summarizer/static/fonts`). Icons are [Phosphor](https://phosphoricons.com) (MIT).

## License

MIT
