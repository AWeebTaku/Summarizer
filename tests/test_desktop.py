import urllib.request

from text_summarizer import desktop


def test_local_server_serves_the_ui_and_assets():
    server, port = desktop._serve()
    try:
        base = f"http://127.0.0.1:{port}"
        assert b"Summarizer" in urllib.request.urlopen(base + "/").read()
        for path in ("/icon.png", "/fonts/Geist-Variable.woff2", "/api/config"):
            assert urllib.request.urlopen(base + path).status == 200
    finally:
        server.should_exit = True


def test_linux_window_defaults_to_software_rendering_and_can_be_overridden(monkeypatch):
    monkeypatch.delenv("QTWEBENGINE_CHROMIUM_FLAGS", raising=False)
    desktop._linux_env()
    import os
    assert "--disable-gpu" in os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] and "--no-sandbox" in os.environ["QTWEBENGINE_CHROMIUM_FLAGS"]
    monkeypatch.setenv("QTWEBENGINE_CHROMIUM_FLAGS", "--my-flag")
    desktop._linux_env()
    assert os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] == "--my-flag"
