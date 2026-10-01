# -*- coding: utf-8 -*-
"""自我測試用的本機 HTTP 伺服器（只綁 127.0.0.1）。

- 以 repo 根目錄為網站根目錄提供靜態檔（強制 .js 為 text/javascript，避免 Windows 登錄檔 MIME 錯誤）。
- POST /__save?path=相對路徑   ：把 body 原樣存檔（只允許 assets/ 與 tools/out/ 之下）。
- POST /__report               ：收 JSON 回報，放進 server.reports 佇列供測試腳本讀取。
"""
import json
import queue
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = ("assets/", "tools/out/")


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
        ".mjs": "text/javascript",
        ".mind": "application/octet-stream",
        ".json": "application/json",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".pdf": "application/pdf",
        ".html": "text/html; charset=utf-8",
        ".css": "text/css",
        ".svg": "image/svg+xml",
    }

    def log_message(self, fmt, *args):  # 安靜
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(n)
        if u.path == "/__save":
            rel = parse_qs(u.query).get("path", [""])[0].replace("\\", "/")
            if not rel.startswith(ALLOWED) or ".." in rel:
                self.send_error(403)
                return
            out = ROOT / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(body)
            self.server.reports.put({"event": "saved", "path": rel, "bytes": len(body)})
        elif u.path == "/__report":
            try:
                data = json.loads(body.decode("utf-8"))
            except Exception:
                data = {"raw": body.decode("utf-8", "replace")}
            self.server.reports.put(data)
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")


def start(port=8765):
    srv = ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=str(ROOT)))
    srv.reports = queue.Queue()
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


if __name__ == "__main__":
    import sys
    p = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    s = start(p)
    print(f"serving {ROOT} at http://127.0.0.1:{p}/  (Ctrl+C 結束)")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        s.shutdown()
