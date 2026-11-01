"""The desktop app: the web UI in a native window, with the server on a free local port.

    python -m text_summarizer.desktop                    open the app
    python -m text_summarizer.desktop --browser          use your default browser instead of a native window
    python -m text_summarizer.desktop --selftest         start the server, check the UI is served and the bundled
                                                         libraries load, then exit 0
    python -m text_summarizer.desktop --selftest-window  the same, and also open a real native window, check it
                                                         shows the app, and close it

The installers are tested with the two self-tests in CI. If a native window cannot be created (a missing
toolkit, a broken graphics stack, no display), the app opens your browser instead, so it still works.
"""
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

from text_summarizer.server import STATIC, create_app

QUIT_AFTER = 20      # browser mode: seconds of silence from the page before the app exits
FIRST_LOAD = 90      # browser mode: seconds to wait for the page to load the first time


def _exit(code: int):
    """Exit immediately. Qt WebEngine can abort during normal interpreter shutdown ("terminate called without
    an active exception") after all the work is done, which would turn a good run into a crash report."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except Exception:
            pass
    os._exit(code)


def _serve(browser: bool = False):
    """Start the API and UI on a free local port. Returns (server, port, app) once it answers."""
    import uvicorn

    app = create_app(browser=browser)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", log_config=None))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=0.2)
            return server, port, app
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


def _say(message: str):
    try:
        print(message, file=sys.stderr)
    except Exception:
        pass


def _native_ok() -> bool:
    """Can a native window open here? On Linux, Qt aborts the whole process when there is no display or a plugin
    library is missing, and Python cannot catch that, so try it in a child process first."""
    if not sys.platform.startswith("linux"):
        return True
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return False
    cmd = [sys.executable, "--probe-native"] if getattr(sys, "frozen", False) else [sys.executable, "-m", "text_summarizer.desktop", "--probe-native"]
    try:
        return subprocess.run(cmd, capture_output=True, timeout=60).returncode == 0
    except Exception:
        return False


def _probe_native():
    """Open a hidden window and close it again: the check _native_ok runs in a child process."""
    import webview

    window = webview.create_window("Summarizer", html="<title>ok</title>", hidden=True)
    webview.start(lambda w: w.destroy(), window)
    _exit(0)


def _run_window(url: str) -> bool:
    """Show the native window and block until it is closed. Returns False if no window could be created."""
    try:
        import webview

        webview.create_window("Summarizer", url, width=980, height=780, min_size=(420, 500))
        webview.start(icon=str(STATIC / "icon.png"))  # the icon applies on Linux (GTK/Qt); other systems use the app's own
        return True
    except Exception as e:
        _say(f"A native window could not be opened ({type(e).__name__}: {e}). Using your browser instead.")
        return False


def _restore_library_path():
    """A frozen Linux app has LD_LIBRARY_PATH pointing at its bundled libraries, and every program it starts inherits
    that. The browser would then load our (older) OpenSSL, libstdc++ and Qt instead of its own and can crash.
    PyInstaller keeps the original value in LD_LIBRARY_PATH_ORIG."""
    if getattr(sys, "frozen", False) and sys.platform.startswith("linux"):
        original = os.environ.pop("LD_LIBRARY_PATH_ORIG", "")
        if original:
            os.environ["LD_LIBRARY_PATH"] = original
        else:
            os.environ.pop("LD_LIBRARY_PATH", None)


def _run_browser(app, url: str):
    """Open the browser and keep serving until its tab is closed (the page pings us every few seconds)."""
    app.state.browser = True  # tells the page to send its heartbeat
    _say(f"Summarizer is running at {url}\nClose the browser tab to quit, or press Ctrl+C.")
    _restore_library_path()  # the browser must not inherit our bundled libraries
    webbrowser.open(url)
    started = time.time()
    try:
        while True:
            time.sleep(1)
            last = app.state.last_ping
            if (last and time.time() - last > QUIT_AFTER) or (not last and time.time() - started > FIRST_LOAD):
                return
    except KeyboardInterrupt:
        return


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


def _check_window(url: str):
    """Open the real native window, confirm it shows the app, then close it."""
    import webview

    seen = {}

    def probe(window):
        try:
            for _ in range(120):
                try:
                    title = window.evaluate_js("document.title")
                except Exception:
                    title = None  # the page is still loading
                if title == "Summarizer":
                    seen["title"] = title
                    return
                time.sleep(0.5)
        finally:
            window.destroy()

    window = webview.create_window("Summarizer", url, width=980, height=780)
    webview.start(probe, window)
    assert seen.get("title") == "Summarizer", "the native window did not show the app"


def selftest(window: bool = False) -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # nothing is shown unless QT_QPA_PLATFORM names a real display
    if sys.platform.startswith("linux"):
        _linux_env()
    try:
        server, port, _ = _serve()
        try:
            base = f"http://127.0.0.1:{port}"
            assert b"Summarizer" in urllib.request.urlopen(base + "/").read(), "UI page missing"
            for path in ("/fonts/Geist-Variable.woff2", "/icon.png"):
                urllib.request.urlopen(base + path).read()
            assert "ready" in json.load(urllib.request.urlopen(base + "/api/config")), "API not answering"
            import docx, fastembed, numpy, onnxruntime, pypdf, pysbd, trafilatura  # noqa: E401,F401  (bundled?)
            from text_summarizer import engine
            assert len(engine.split_sentences("One two three. Four five six.")) == 2, "sentence splitter"
            if window:
                _check_window(base + "/")
            elif sys.platform.startswith("linux"):
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
    args = sys.argv[1:]
    if sys.platform.startswith("linux"):
        _linux_env()
    if "--probe-native" in args:
        _probe_native()
    if "--selftest" in args or "--selftest-window" in args:
        _exit(selftest(window="--selftest-window" in args))
    browser = "--browser" in args
    server, port, app = _serve(browser=browser)
    url = f"http://127.0.0.1:{port}/"
    if browser or not _native_ok() or not _run_window(url):
        _run_browser(app, url)
    server.should_exit = True
    _exit(0)


if __name__ == "__main__":
    main()
