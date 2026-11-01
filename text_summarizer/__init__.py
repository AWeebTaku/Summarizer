"""Summarize text, files and web pages with sentence embeddings, TextRank and MMR.

    from text_summarizer import summarize, summarize_file

    summary = summarize(text, ratio=0.2)       # or n=5
    print(summary)                             # the summary text
    summary.sentences, summary.keywords, summary.reduction

    for name, summary in summarize_file("report.pdf"):   # also .docx .txt .md .csv or a URL
        print(name, summary)
"""
from .engine import Summary, summarize, summarize_file, summarize_many, warm_up
from .ingest import load

__version__ = "2.0.0"
__all__ = ["Summary", "summarize", "summarize_file", "summarize_many", "load", "warm_up", "__version__"]
