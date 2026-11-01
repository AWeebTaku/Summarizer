"""Desktop app: the web UI in a native window, with the server on a free local port.

    summarizer-desktop              open the app
    summarizer-desktop --selftest   start the server, check the UI is served and the bundled libraries
                                    load, then exit 0. The installer builds use this to test themselves
                                    in CI without a display.
"""
import json
import os
import socket
import sys
import threading
import time
import urllib.request

from text_summarizer.server import STATIC, create_app


def _serve():
    """Start the API and UI on a free local port. Returns (server, port) once it answers."""
    import uvicorn

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="warning", log_config=None))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=0.2)
            return server, port
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("the local server did not start")


def _linux_env():
    """Chromium flags for the Qt window. Set QTWEBENGINE_CHROMIUM_FLAGS yourself to override them.

    --no-sandbox: the window only shows our own local page, so the sandbox adds little, and it refuses to
        start on systems that restrict user namespaces (Ubuntu 24.04) and when run as root (containers).
    --disable-gpu: this is a text interface, so software rendering is plenty, and it avoids the crashes
        QtWebEngine hits when the graphics stack is missing or odd (virtual machines, remote desktops,
        containers: "Failed to get system egl display").
    """
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")


def _check_qt(base: str):
    """Load the app's page in a real Qt WebEngine view: proves the bundled Qt, its plugins and the system graphics libraries work."""
    from qtpy.QtCore import QEventLoop, QTimer, QUrl
    from qtpy.QtWebEngineWidgets import QWebEngineView
    from qtpy.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv[:1] or ["Summarizer"])  # noqa: F841  (must stay alive while the view exists)
    view = QWebEngineView()
    loop = QEventLoop()
    view.loadFinished.connect(lambda ok: loop.quit())
    QTimer.singleShot(40000, loop.quit)
    view.load(QUrl(base + "/"))
    loop.exec()
    assert view.title() == "Summarizer", f"the page did not load in Qt WebEngine (title={view.title()!r})"


def selftest() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # nothing is shown; set QT_QPA_PLATFORM=xcb to test a real display
    if sys.platform.startswith("linux"):
        _linux_env()
    try:
        server, port = _serve()
        try:
            base = f"http://127.0.0.1:{port}"
            assert b"Summarizer" in urllib.request.urlopen(base + "/").read(), "UI page missing"
            for path in ("/fonts/Geist-Variable.woff2", "/icon.png"):
                urllib.request.urlopen(base + path).read()
            assert "ready" in json.load(urllib.request.urlopen(base + "/api/config")), "API not answering"
            import docx, fastembed, numpy, onnxruntime, pypdf, pysbd, trafilatura  # noqa: E401,F401  (bundled?)
            from text_summarizer import engine
            assert len(engine.split_sentences("One two three. Four five six.")) == 2, "sentence splitter"
            if sys.platform.startswith("linux"):
                _check_qt(base)
        finally:
            server.should_exit = True
    except Exception as e:
        print(f"selftest failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    print("selftest ok")
    return 0


def main():
    if sys.stdout is None or sys.stderr is None:  # PyInstaller --windowed on Windows
        sys.stdout = sys.stderr = open(os.devnull, "w")
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if sys.platform.startswith("linux"):
        _linux_env()
    import webview

    server, port = _serve()
    webview.create_window("Summarizer", f"http://127.0.0.1:{port}/", width=980, height=780, min_size=(420, 500))
    webview.start(icon=str(STATIC / "icon.png"))  # the icon applies on Linux (GTK/Qt); other systems use the app's own
    server.should_exit = True


if __name__ == "__main__":
    main()
