"""The command line: python -m text_summarizer FILE_OR_URL ..."""
import argparse
import json
import os
import sys

from . import __version__, engine, ingest

EXAMPLES = """\
examples:
  python -m text_summarizer report.pdf                       summarize a file (pdf, docx, txt, md, csv)
  python -m text_summarizer report.pdf -n 5 -f bullets       five bullet points
  python -m text_summarizer a.pdf b.docx -r 0.1 -o out.md -f markdown
  python -m text_summarizer https://example.com/article      a web page
  python -m text_summarizer data.csv -c body                 one summary per row, text in column "body"
  cat essay.txt | python -m text_summarizer -k               from stdin, with keywords
  python -m text_summarizer report.pdf -f json | jq .        machine-readable output

exit status: 0 on success, 1 if any source failed, 2 for bad arguments.
"""


def _ratio(value):
    try:
        r = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {value!r}")
    if not 0 < r <= 1:
        raise argparse.ArgumentTypeError("must be greater than 0 and at most 1 (for example 0.2)")
    return r


def _count(value):
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a whole number: {value!r}")
    if n < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return n


def build_parser():
    ap = argparse.ArgumentParser(
        prog="python -m text_summarizer", description="Summarize text, files (txt, md, pdf, docx, csv) and web pages.",
        epilog=EXAMPLES, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sources", nargs="*", metavar="source",
                    help="file path, web page URL or raw text; '-' or no argument reads stdin")
    size = ap.add_mutually_exclusive_group()
    size.add_argument("-n", "--sentences", type=_count, metavar="N", help="number of sentences to keep (at most)")
    size.add_argument("-r", "--ratio", type=_ratio, metavar="R", help="fraction of the document to keep (default 0.2)")
    ap.add_argument("-f", "--format", choices=["text", "bullets", "markdown", "json"], default="text",
                    help="output format (default: text)")
    ap.add_argument("-b", "--bullets", action="store_true", help="shorthand for --format bullets")
    ap.add_argument("-k", "--keywords", action="store_true", help="also print keywords (always included in markdown and json)")
    ap.add_argument("-c", "--column", metavar="NAME", help="CSV column holding the text (default: article_text, else the first)")
    ap.add_argument("-o", "--output", metavar="FILE", help="write the result to FILE instead of stdout")
    ap.add_argument("--ai", action="store_true",
                    help="rewrite the chosen sentences as fluent prose with Claude (needs ANTHROPIC_API_KEY and: pip install anthropic)")
    ap.add_argument("-V", "--version", action="version", version=f"Summarizer {__version__}")
    return ap


def _render(results, fmt, keywords):
    """results: [(name, Summary, ai_text_or_None)] -> the text to print."""
    many = len(results) > 1
    if fmt == "json":
        return json.dumps([{
            "name": name, "summary": ai or s.text, "sentences": s.sentences, "keywords": s.keywords,
            "source_words": s.source_words, "summary_words": s.summary_words,
            **({"extractive_summary": s.text} if ai else {}),
        } for name, s, ai in results], ensure_ascii=False, indent=2)
    blocks = []
    for name, s, ai in results:
        body = ai or (s.bullets() if fmt in ("bullets", "markdown") else s.text)
        if fmt == "markdown":
            parts = [f"## {name}", body, f"*Keywords: {', '.join(s.keywords)}*" if s.keywords else ""]
        else:
            parts = [f"== {name} ==" if many else "", body, f"keywords: {', '.join(s.keywords)}" if keywords and s.keywords else ""]
        blocks.append("\n".join(p for p in parts if p))
    return "\n\n".join(blocks)


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    if args.bullets:
        args.format = "bullets"
    for stream in (sys.stdout, sys.stderr):  # Windows consoles default to a legacy codepage
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    sources = args.sources
    if not sources:
        if sys.stdin.isatty():  # nothing to read: show help rather than hang waiting for input
            ap.print_help(sys.stderr)
            return 2
        sources = ["-"]

    if args.ai:
        from . import ai
        if not ai.available():
            print("summarizer: error: --ai needs ANTHROPIC_API_KEY to be set", file=sys.stderr)
            return 1

    results, failed = [], False
    for source in sources:
        try:
            docs = [("stdin", sys.stdin.read())] if source == "-" else ingest.load(source, args.column)
            for name, text in docs:
                s = engine.summarize(text, n=args.sentences, ratio=args.ratio)
                if not s:
                    print(f"summarizer: warning: {name}: no sentences found (a scanned PDF has no text layer)", file=sys.stderr)
                    continue
                ai_text = None
                if args.ai:
                    ai_text = ai.rewrite(s.sentences, bullets=args.format in ("bullets", "markdown"))
                    if ai_text is None:
                        print(f"summarizer: warning: {name}: the model declined, showing the extractive summary", file=sys.stderr)
                results.append((name, s, ai_text))
        except (ValueError, OSError) as e:  # includes FileNotFoundError and unreadable files
            label = source if len(source) < 60 and "\n" not in source else "input"
            print(f"summarizer: error: {e}" if isinstance(e, FileNotFoundError) else f"summarizer: error: {label}: {e}", file=sys.stderr)
            failed = True
        except ImportError:
            print("summarizer: error: --ai needs the anthropic package: pip install anthropic", file=sys.stderr)
            return 1
        except Exception as e:  # e.g. an API error from --ai
            print(f"summarizer: error: {type(e).__name__}: {e}", file=sys.stderr)
            failed = True

    if results:
        out = _render(results, args.format, args.keywords)
        try:
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(out + "\n")
            else:
                print(out)
                sys.stdout.flush()
        except BrokenPipeError:  # e.g. `summarize big.pdf | head`
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except OSError as e:
            print(f"summarizer: error: could not write {args.output}: {e}", file=sys.stderr)
            return 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
