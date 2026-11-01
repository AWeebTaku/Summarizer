import json
import sys
import time
import types
import urllib.request

from text_summarizer import desktop


def _get(url):
    return urllib.request.urlopen(url, timeout=5)


def test_local_server_serves_the_ui_and_assets():
    server, port, _ = desktop._serve()
    try:
        base = f"http://127.0.0.1:{port}"
        assert b"Summarizer" in _get(base + "/").read()
        for path in ("/icon.png", "/fonts/Geist-Variable.woff2", "/api/config"):
            assert _get(base + path).status == 200
    finally:
        server.should_exit = True


def test_browser_mode_is_reported_and_the_page_can_ping():
    server, port, app = desktop._serve(browser=True)
    try:
        base = f"http://127.0.0.1:{port}"
        assert json.load(_get(base + "/api/config"))["browser"] is True
        assert app.state.last_ping == 0
        _get(urllib.request.Request(base + "/api/ping", method="POST"))
        assert app.state.last_ping > 0
    finally:
        server.should_exit = True


def _fake_app(last_ping):
    return types.SimpleNamespace(state=types.SimpleNamespace(browser=False, last_ping=last_ping))


def test_browser_mode_opens_the_page_and_quits_when_it_goes_quiet(monkeypatch):
    opened = []
    monkeypatch.setattr(desktop.webbrowser, "open", lambda url: opened.append(url))
    monkeypatch.setattr(desktop, "QUIT_AFTER", 0.2)
    app = _fake_app(time.time())
    desktop._run_browser(app, "http://127.0.0.1:1/")  # returns once pings stop
    assert opened == ["http://127.0.0.1:1/"] and app.state.browser is True


def test_browser_mode_gives_up_if_the_page_never_loads(monkeypatch):
    monkeypatch.setattr(desktop.webbrowser, "open", lambda url: True)
    monkeypatch.setattr(desktop, "FIRST_LOAD", 0.2)
    desktop._run_browser(_fake_app(0.0), "http://127.0.0.1:1/")


def test_native_window_is_skipped_on_linux_without_a_display(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    assert desktop._native_ok() is False
    monkeypatch.setattr(sys, "platform", "win32")
    assert desktop._native_ok() is True  # Windows and macOS raise ordinary errors, handled by _run_window


def test_a_window_that_cannot_open_falls_back_instead_of_crashing(monkeypatch):
    broken = types.ModuleType("webview")

    def create_window(*a, **k):
        raise RuntimeError("no toolkit")

    broken.create_window = create_window
    monkeypatch.setitem(sys.modules, "webview", broken)
    assert desktop._run_window("http://127.0.0.1:1/") is False


def test_linux_window_defaults_to_software_rendering_and_can_be_overridden(monkeypatch):
    import os
    monkeypatch.delenv("QTWEBENGINE_CHROMIUM_FLAGS", raising=False)
    desktop._linux_env()
    assert "--disable-gpu" in os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] and "--no-sandbox" in os.environ["QTWEBENGINE_CHROMIUM_FLAGS"]
    monkeypatch.setenv("QTWEBENGINE_CHROMIUM_FLAGS", "--my-flag")
    desktop._linux_env()
    assert os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] == "--my-flag"


def test_programs_started_by_a_frozen_linux_app_do_not_inherit_its_bundled_libraries(monkeypatch):
    import os
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("LD_LIBRARY_PATH", "/opt/summarizer/_internal:/usr/local/lib")
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "/usr/local/lib")
    desktop._restore_library_path()
    assert os.environ["LD_LIBRARY_PATH"] == "/usr/local/lib" and "LD_LIBRARY_PATH_ORIG" not in os.environ
    # it was unset originally: nothing should be left behind (an empty entry would mean "the current directory")
    monkeypatch.setenv("LD_LIBRARY_PATH", "/opt/summarizer/_internal")
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "")
    desktop._restore_library_path()
    assert "LD_LIBRARY_PATH" not in os.environ


def test_library_path_is_left_alone_when_not_frozen(monkeypatch):
    import os
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setenv("LD_LIBRARY_PATH", "/my/libs")
    desktop._restore_library_path()
    assert os.environ["LD_LIBRARY_PATH"] == "/my/libs"
