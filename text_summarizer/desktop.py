"""Desktop app: the web UI in a native window, server on a free local port."""
import os
import socket
import sys
import threading
import time
import urllib.request

from text_summarizer.server import create_app


def main():
    if sys.stdout is None or sys.stderr is None:  # PyInstaller --windowed on Windows
        sys.stdout = sys.stderr = open(os.devnull, "w")
    import uvicorn
    import webview

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="warning", log_config=None))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):  # wait until the server answers
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=0.2)
            break
        except OSError:
            time.sleep(0.1)
    webview.create_window("Summarizer", f"http://127.0.0.1:{port}/", width=980, height=780, min_size=(420, 500))
    webview.start()
    server.should_exit = True


if __name__ == "__main__":
    main()
