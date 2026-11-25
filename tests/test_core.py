import re
import zlib

import numpy as np

from text_summarizer import engine, ingest


def fake_embed(sents):
    """Hashed bag-of-words: deterministic, no model download."""
    out = np.zeros((len(sents), 64), dtype=np.float32)
    for i, s in enumerate(sents):
        for w in re.findall(r"\w+", s.lower()):
            out[i, zlib.crc32(w.encode()) % 64] += 1
    return out / np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-9)


DOC = ("Solar power is growing fast. Panels are getting cheaper every year. Many homes now use solar panels. "
       "Wind farms also produce clean energy. Batteries store energy for the night. Dogs are loyal pets. "
       "Cats prefer sleeping all day. Governments subsidise solar installation.")


def test_split_and_filter_short():
    assert engine.split_sentences("Hi. This is a real sentence. Ok.") == ["This is a real sentence."]


def test_n_respected_and_order_preserved():
    r = engine.summarize(DOC, n=3, embedder=fake_embed)
    assert len(r["sentences"]) == 3
    assert r["indices"] == sorted(r["indices"])


def test_empty_and_single_sentence():
    assert engine.summarize("", embedder=fake_embed)["summary"] == ""
    assert engine.summarize("Just one sentence here.", embedder=fake_embed)["sentences"] == ["Just one sentence here."]


def test_repetitive_text_can_yield_fewer_than_n():
    r = engine.summarize("Solar is great for homes. " * 6, n=4, embedder=fake_embed)
    assert 1 <= len(r.sentences) <= 4


def test_mmr_avoids_duplicates():
    doc = "Solar is great for homes. " * 5 + "Wind turbines spin in the breeze. Batteries store power overnight."
    r = engine.summarize(doc, n=3, embedder=fake_embed)
    assert len(set(r["sentences"])) == 3


def test_scores_ignore_negative_similarity():
    E = np.array([[1, 0], [-1, 0], [0, 1]], dtype=np.float32)
    assert np.isfinite(engine._scores(E)).all()


def test_documents_ranked_independently():
    a, b = DOC, "Football is popular worldwide. Teams train every day. Fans fill the stadium."
    many = engine.summarize_many([("a", a), ("b", b)], n=2, embedder=fake_embed)
    assert [name for name, _ in many] == ["a", "b"]
    assert many[0][1] == engine.summarize(a, n=2, embedder=fake_embed)


def test_long_document_map_reduce():
    words = "river stone market engine violin garden orbit harvest copper window thunder ledger meadow harbor quartz lantern".split()
    doc = " ".join(f"The {words[i % 16]} and the {words[(i * 5 + 3) % 16]} met near the {words[(i * 7 + 1) % 16]} number {i}." for i in range(700))
    r = engine.summarize(doc, n=5, embedder=fake_embed)
    assert len(r.sentences) == 5 and r.indices == sorted(r.indices)
    assert r.indices[-1] - r.indices[0] > 150  # picks come from across the document, not one chunk


def test_ingest_text_csv_docx(tmp_path):
    assert ingest.load("raw text here")[0] == ("text", "raw text here")
    c = tmp_path / "d.csv"
    c.write_text("article_id,article_text\n7,Hello there world.\n8,Second doc text.\n")
    assert ingest.load(str(c)) == [("7", "Hello there world."), ("8", "Second doc text.")]
    import docx
    d = docx.Document()
    d.add_paragraph("A paragraph in word.")
    d.save(tmp_path / "x.docx")
    assert ingest.load(str(tmp_path / "x.docx"))[0][1] == "A paragraph in word."


def test_url_errors_are_value_errors():
    import pytest
    with pytest.raises(ValueError):
        ingest.from_url("file:///etc/passwd")
    with pytest.raises(ValueError):
        ingest.from_url("http://127.0.0.1:9/")  # nothing listens: clean error, not a traceback


def test_summary_object():
    s = engine.summarize(DOC, n=2, embedder=fake_embed)
    assert str(s) == s.text and s and len(s.sentences) == 2
    assert s.bullets().count("\n") == 1 and s.bullets().startswith("- ")
    assert s["summary"] == s.text and s["all"] == s.source_sentences  # dict-style access still works
    assert 0 < s.reduction < 1 and s.summary_words < s.source_words
    assert set(s.to_dict()) == {"summary", "sentences", "indices", "keywords", "all", "warnings"}
    empty = engine.summarize("", embedder=fake_embed)
    assert not empty and empty.reduction == 0.0


def test_argument_validation():
    import pytest
    for bad in ({"n": 0}, {"ratio": 0}, {"ratio": 1.5}, {"n": 2, "ratio": 0.2}):
        with pytest.raises(ValueError):
            engine.summarize(DOC, embedder=fake_embed, **bad)
    with pytest.raises(TypeError):
        engine.summarize(None)


def test_summarize_file_and_default_embedder_is_swappable(monkeypatch, tmp_path):
    monkeypatch.setattr(engine, "embed", fake_embed)  # the default is looked up per call
    f = tmp_path / "notes.txt"
    f.write_text(DOC)
    [(name, s)] = engine.summarize_file(str(f), n=2)
    assert name == "notes.txt" and len(s.sentences) == 2


def test_missing_file_and_damaged_files_have_clear_errors(tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError):
        ingest.load("reprot.pdf")
    assert ingest.load("a short note")[0][0] == "text"  # plain text is still text
    (tmp_path / "x.pdf").write_bytes(b"nope")
    (tmp_path / "x.docx").write_bytes(b"nope")
    for name in ("x.pdf", "x.docx"):
        with pytest.raises(ValueError):
            ingest.load(str(tmp_path / name))


ENGLISH = ("The committee met on Tuesday to discuss the budget for the coming year, and most of the members said that "
           "they would support the plan if it included more money for the schools in the northern part of the city.")
OTHER = {
    "spanish": "El comité se reunió el martes para discutir el presupuesto del próximo año, y la mayoría de los miembros dijo que apoyaría el plan si incluía más dinero para las escuelas de la parte norte de la ciudad.",
    "french": "Le comité s'est réuni mardi pour discuter du budget de l'année prochaine, et la plupart des membres ont déclaré qu'ils soutiendraient le plan s'il prévoyait plus d'argent pour les écoles du nord de la ville.",
    "german": "Der Ausschuss traf sich am Dienstag, um den Haushalt für das kommende Jahr zu besprechen, und die meisten Mitglieder sagten, dass sie den Plan unterstützen würden, wenn er mehr Geld für die Schulen im Norden der Stadt enthielte.",
    "russian": "Комитет собрался во вторник, чтобы обсудить бюджет на следующий год, и большинство членов заявили, что поддержат план, если он предусматривает больше денег для школ в северной части города.",
    "hindi": "समिति ने मंगलवार को अगले वर्ष के बजट पर चर्चा करने के लिए बैठक की और अधिकांश सदस्यों ने कहा कि यदि योजना में शहर के उत्तरी हिस्से के स्कूलों के लिए अधिक धन शामिल होगा तो वे इसका समर्थन करेंगे।",
    "chinese": "委员会周二开会讨论明年的预算，大多数成员表示，如果该计划为城市北部的学校提供更多资金，他们将支持该计划。",
}


def test_language_check():
    assert engine.looks_english(ENGLISH)
    assert engine.looks_english("Short text")                    # too little to judge: no false alarm
    assert engine.looks_english("def f(x):\n    return x * 2\n" * 3)  # code is not "foreign"
    for lang, text in OTHER.items():
        assert not engine.looks_english(text), lang


def test_non_english_text_still_summarizes_but_warns():
    r = engine.summarize(" ".join(OTHER["spanish"] + " " for _ in range(4)), n=1, embedder=fake_embed)
    assert r.sentences and any("English" in w for w in r.warnings)
    assert not engine.summarize(DOC, n=2, embedder=fake_embed).warnings


def test_short_input_is_returned_whole_with_a_note():
    r = engine.summarize("Cats sleep a lot. Dogs bark at the mailman.", n=3, embedder=fake_embed)
    assert len(r.sentences) == 2 and any("short" in w for w in r.warnings)
    r = engine.summarize("Hi. Ok.", embedder=fake_embed)
    assert not r and any("Nothing to summarize" in w for w in r.warnings)


def test_scanned_pdf_gets_a_clear_error(tmp_path):
    import pytest
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    w.add_blank_page(width=200, height=200)
    f = tmp_path / "scan.pdf"
    with open(f, "wb") as fh:
        w.write(fh)
    with pytest.raises(ingest.NoTextError, match="2 pages but no text.*scan.*OCR"):
        ingest.load(str(f))
    assert issubclass(ingest.NoTextError, ValueError)  # so the CLI and the API report it like any bad input


def test_keywords_keep_accented_words_whole():
    kw = engine._keywords(["El comité votó el presupuesto.", "El comité aprobó la reunión del martes."])
    assert "comité" in kw and "comit" not in kw


def test_password_protected_pdf_says_so(tmp_path):
    import pytest
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(width=100, height=100)
    w.encrypt("secret", algorithm="RC4-128")
    f = tmp_path / "locked.pdf"
    with open(f, "wb") as fh:
        w.write(fh)
    with pytest.raises(ValueError, match="password protected"):
        ingest.load(str(f))
