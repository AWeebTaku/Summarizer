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
