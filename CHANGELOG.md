# Changelog

## 2.0.0

A ground-up rewrite, with a new interface and a new summarizer.

### New
- **A new app** for Windows, macOS and Linux, with real installers: `Summarizer-setup.exe` (per user) and `Summarizer.msi` for Windows, a `.dmg` for macOS, and `.deb`, `.rpm`, `.pkg.tar.zst` and `.AppImage` for Linux. Each release lists SHA-256 checksums.
- **Works on any system.** If a native window cannot be opened (no display, a missing graphics library, a broken toolkit), the app opens your browser instead and quits when you close the tab. Linux builds carry their own Qt WebEngine.
- **A new summarizer.** Sentences are embedded with a small ONNX model (`bge-small-en-v1.5`, about 130 MB, downloaded on first use) instead of GloVe (an 862 MB download that ran on every import). Each document is ranked on its own with TextRank plus topic and position priors, and MMR removes repeated points. Long documents are processed in chunks.
- **More input:** PDF, Word, text, Markdown, CSV and web pages, with a first-run model status, drag and drop, length presets, highlighting of the chosen sentences in the original, and export to Markdown, Word and CSV.
- **A command line** (`python -m text_summarizer`) with several sources, stdin, `-f text|bullets|markdown|json`, `-o FILE`, `-n` or `-r`, and `--ai`.
- **A typed Python API:** `summarize()` returns a `Summary` object, with `summarize_file()`, `summarize_many()`, `load()` and `warm_up()`.
- **Optional AI rewrite** with Claude. Only the chosen sentences are sent.
- **Self-tests** (`--selftest`, `--selftest-window`) that the release build uses to install and start every installer, including a real native window, before anything is published.
- A landing page, published with GitHub Pages.

### Changed
- Python 3.10 or newer. The app is run from source with `requirements*.txt`; it is no longer a Python package, and nothing is published to PyPI.

### Removed
- The tkinter window, the GloVe download, and the import-time side effects (downloads, `nltk.download`).

## 1.0.0

The original version, kept for reference: a tkinter window and GloVe word embeddings, summarizing with PageRank. Version 2.0.0 replaces it.
