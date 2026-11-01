import io
import json

import pytest

from text_summarizer import cli, engine
from tests.test_core import DOC, fake_embed


@pytest.fixture(autouse=True)
def fast_model(monkeypatch):
    monkeypatch.setattr(engine, "embed", fake_embed)


def run(capsys, *argv, stdin=None, monkeypatch=None):
    if stdin is not None:
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    code = cli.main(list(argv))
    out = capsys.readouterr()
    return code, out.out, out.err


def test_text_and_bullets(capsys):
    code, out, _ = run(capsys, DOC, "-n", "2")
    assert code == 0 and out.count(".") >= 2 and not out.startswith("-")
    code, out, _ = run(capsys, DOC, "-n", "2", "-b")
    assert code == 0 and out.startswith("- ") and out.count("\n- ") == 1


def test_json_output_is_parseable(capsys):
    code, out, _ = run(capsys, DOC, "-n", "2", "-f", "json")
    [d] = json.loads(out)
    assert code == 0 and d["name"] == "text" and len(d["sentences"]) == 2 and d["summary_words"] < d["source_words"]


def test_markdown_and_keywords(capsys):
    _, out, _ = run(capsys, DOC, "-n", "2", "-f", "markdown")
    assert out.startswith("## text") and "*Keywords:" in out
    _, out, _ = run(capsys, DOC, "-n", "2", "-k")
    assert "keywords:" in out


def test_stdin(capsys, monkeypatch):
    code, out, _ = run(capsys, "-n", "1", stdin=DOC, monkeypatch=monkeypatch)
    assert code == 0 and out.strip()
    code, out, _ = run(capsys, "-", "-n", "1", stdin=DOC, monkeypatch=monkeypatch)
    assert code == 0 and out.strip()


def test_several_sources_and_output_file(capsys, tmp_path):
    a, b, out_file = tmp_path / "a.txt", tmp_path / "b.txt", tmp_path / "out.md"
    a.write_text(DOC)
    b.write_text(DOC)
    code, out, _ = run(capsys, str(a), str(b), "-n", "1", "-f", "markdown", "-o", str(out_file))
    assert code == 0 and out == ""
    text = out_file.read_text(encoding="utf-8")
    assert "## a.txt" in text and "## b.txt" in text
    _, out, _ = run(capsys, str(a), str(b), "-n", "1")
    assert "== a.txt ==" in out and "== b.txt ==" in out


def test_one_bad_source_does_not_stop_the_rest(capsys, tmp_path):
    good = tmp_path / "good.txt"
    good.write_text(DOC)
    code, out, err = run(capsys, "missing.pdf", str(good), "-n", "1")
    assert code == 1 and "missing.pdf" in err and "no such file" in err and out.strip()


def test_bad_arguments_exit_2(capsys):
    for argv in (["x", "-r", "2"], ["x", "-n", "0"], ["x", "-n", "2", "-r", "0.2"], ["x", "-f", "xml"]):
        with pytest.raises(SystemExit) as e:
            cli.main(argv)
        assert e.value.code == 2
    capsys.readouterr()


def test_empty_document_warns(capsys):
    code, out, err = run(capsys, "ok. no.")
    assert code == 0 and out == "" and "no sentences found" in err


def test_ai_needs_a_key(capsys, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    code, _, err = run(capsys, DOC, "--ai")
    assert code == 1 and "ANTHROPIC_API_KEY" in err


def test_version_and_help(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["--version"])
    assert e.value.code == 0 and "summarize 2.0.0" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    assert "examples:" in capsys.readouterr().out
