# Changelog

## 2.0.1

### Fixed
- **The Linux desktop app could not open a window.** The 2.0.0 Linux download was built without a GUI toolkit and could not find the system's GTK, so it failed at startup on every machine. Linux builds now carry their own Qt WebEngine.
- A damaged PDF or Word file uploaded in the app is reported as a normal error instead of a server error.

### Added
- **Real installers** instead of zipped folders: `Summarizer-setup.exe` (per user) and `Summarizer.msi` for Windows, a `.dmg` for macOS, and `.deb`, `.rpm`, `.pkg.tar.zst` and `.AppImage` for Linux. Each release also lists SHA-256 checksums.
- An app icon, and `summarizer-desktop --selftest`, which the release build uses to install and start every installer before anything is published.
- A `qt` extra for pip installs on Linux: `pip install "text-summarizer-aweebtaku[desktop,qt]"`.

### Changed
- Releases are published to PyPI only after every installer has built and passed its tests.

## 2.0.0

A ground-up rewrite. **This release breaks the 1.x API and removes the old GUI.**

### Changed
- The GloVe embeddings (an 862 MB download that ran on every import) are replaced by a small sentence-embedding model (`bge-small-en-v1.5`, about 130 MB, downloaded on first use, cached in `~/.cache/summarizer`).
- Each document is now ranked on its own. In 1.x every sentence of a CSV was ranked together, so articles influenced each other.
- Ranking uses TextRank with topic and position priors, then MMR to avoid repeated points. Long documents are processed in chunks.
- `summarize()` returns a `Summary` object (`str(summary)` is the text). Options are keyword-only. New helpers: `summarize_file()`, `summarize_many()`, `load()`, `warm_up()`.
- `summarize` is a real command now. It accepts several sources, stdin, `-f text|bullets|markdown|json`, `-o FILE`, `-r`/`-n`, and `--ai`. The 1.x CLI crashed on startup.
- Python 3.10 or newer is required. `pandas`, `scikit-learn`, `networkx`, `requests` and `nltk` are no longer dependencies.

### Added
- Desktop app for Windows, macOS and Linux (`summarizer-desktop`, or download from Releases).
- Input from PDF, Word, text, Markdown, CSV and web pages.
- Optional AI rewrite with Claude (`pip install "text-summarizer-aweebtaku[ai]"`).
- Export to Markdown, Word and CSV. Highlighting of the chosen sentences in the original text.
- Landing page published with GitHub Pages.

### Removed
- The tkinter GUI (`text-summarizer-gui`), `text-summarizer-shortcuts`, and the legacy `UI.py` / `textsummarization.py` scripts.
- The GloVe download and the import-time side effects (downloads, `nltk.download`).
