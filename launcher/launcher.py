# -*- coding: utf-8 -*-
"""墨玉晶格修復任務 WebAR — Windows 啟動器（PyInstaller onefile、無主控台視窗）。

點兩下執行：
  1. 在 127.0.0.1 找可用的埠，啟動只供本機使用的 HTTP 伺服器（遊戲網頁完整打包在 exe 內，離線可用）。
  2. 以預設瀏覽器開 launcher.html（投影給全班看：任務卡＋手機掃描 QR＋電腦直接玩）。
  3. 顯示小控制視窗；關閉視窗或按〔結束遊戲〕即停止伺服器並結束行程。

參數：
  --selftest    啟動伺服器 → 逐一請求主要檔案，檢查 200 與 MIME → 結束（exit code 0／1），
                結果寫到 exe 同層的 墨玉晶格修復任務WebAR_selftest.log（不能寫就改寫 %TEMP%）。
  --no-browser  不自動開瀏覽器（仍顯示控制視窗）。
  --port N      指定埠（預設優先用 8731，被占用就往後找）。
  --version     顯示版本後結束。

手機不是連到這台電腦（區網 http 無法開相機），而是連 GitHub Pages 的 HTTPS 網址：
https://rlirdo.github.io/serpentine-webar/
"""
import datetime
import os
import socket
import sys
import tempfile
import threading
import urllib.request
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_NAME = "墨玉晶格修復任務WebAR"
VERSION = "1.0.0"
BUILD_DATE = "2026/10/01"
ONLINE_URL = "https://rlirdo.github.io/serpentine-webar/"
CREDIT = "NDHU自資系游豐兆製作"
PREFERRED_PORT = 8731  # 固定優先埠：同一台電腦每次開啟網址相同，教師頁的本機作答紀錄（localStorage）才看得到
FROZEN = getattr(sys, "frozen", False)

if FROZEN:
    WEB_ROOT = Path(sys._MEIPASS) / "web"
    EXE_DIR = Path(sys.executable).resolve().parent
    LAUNCHER_HTML = WEB_ROOT / "launcher.html"
else:
    WEB_ROOT = Path(__file__).resolve().parents[1]
    EXE_DIR = Path(__file__).resolve().parent
    LAUNCHER_HTML = Path(__file__).resolve().parent / "launcher.html"

MIME = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".wasm": "application/wasm",
    ".mind": "application/octet-stream",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".pdf": "application/pdf",
    ".md": "text/plain; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
}

# --selftest 要檢查的檔案與期望 MIME（前綴比對）
SELFTEST_FILES = [
    ("launcher.html", "text/html"), ("index.html", "text/html"), ("ar.html", "text/html"),
    ("play.html", "text/html"), ("card.html", "text/html"), ("teacher.html", "text/html"),
    ("css/style.css", "text/css"),
    ("js/game.js", "text/javascript"), ("js/content.js", "text/javascript"), ("js/hud.js", "text/javascript"),
    ("js/ar-host.js", "text/javascript"), ("js/play-host.js", "text/javascript"), ("js/models.js", "text/javascript"),
    ("js/character.js", "text/javascript"), ("js/fx.js", "text/javascript"), ("js/audio.js", "text/javascript"),
    ("js/layout.js", "text/javascript"), ("js/autoplay.js", "text/javascript"),
    ("vendor/three/three.module.js", "text/javascript"),
    ("vendor/mindar/mindar-image-three.prod.js", "text/javascript"),
    ("vendor/mindar/controller-mGt1s8dJ.js", "text/javascript"),
    ("vendor/mindar/ui-fBadYuor.js", "text/javascript"),
    ("vendor/es-module-shims.js", "text/javascript"),
    ("assets/targets.mind", "application/octet-stream"), ("assets/target.png", "image/png"),
    ("assets/target_print.pdf", "application/pdf"), ("assets/qr.png", "image/png"), ("assets/icon.png", "image/png"),
]


# ---------------------------------------------------------------- 記錄檔
class Log:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            self.f = open(path, "a", encoding="utf-8")
        except OSError:
            self.f = None

    def __call__(self, *parts):
        line = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S ") + " ".join(str(p) for p in parts)
        with self.lock:
            if self.f:
                self.f.write(line + "\n")
                self.f.flush()


def writable_dir(preferred):
    """回傳可寫入的資料夾：優先 preferred，否則 %TEMP%\\serpentine-webar。"""
    try:
        probe = preferred / ".write_probe"
        probe.write_text("x", encoding="ascii")
        probe.unlink()
        return preferred
    except OSError:
        d = Path(tempfile.gettempdir()) / "serpentine-webar"
        d.mkdir(parents=True, exist_ok=True)
        return d


LOG = None


# ---------------------------------------------------------------- 伺服器
class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, **MIME}
    server_version = "SerpentineWebAR/" + VERSION
    sys_version = ""

    def guess_type(self, path):
        return MIME.get(Path(str(path)).suffix.lower(), "application/octet-stream")

    def translate_path(self, path):
        clean = path.split("?", 1)[0].split("#", 1)[0]
        if clean in ("/launcher.html", "/launcher"):
            return str(LAUNCHER_HTML)
        return super().translate_path(path)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def log_message(self, fmt, *args):
        if LOG:
            LOG("http", self.client_address[0], fmt % args)

    def do_POST(self):  # 遊戲頁的自我測試回報（?selftest=1）在 exe 中不需要，回 204 即可
        n = int(self.headers.get("Content-Length", "0") or 0)
        if n:
            self.rfile.read(n)
        self.send_response(204)
        self.end_headers()


def port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def start_server(preferred=PREFERRED_PORT):
    candidates = [preferred] + [p for p in range(preferred + 1, preferred + 40)]
    for port in candidates:
        if not port_free(port):
            continue
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=str(WEB_ROOT)))
            break
        except OSError:
            continue
    else:
        srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(WEB_ROOT)))
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


# ---------------------------------------------------------------- 各模式
def run_selftest(preferred):
    out_dir = writable_dir(EXE_DIR)
    log_path = out_dir / f"{APP_NAME}_selftest.log"
    try:
        log_path.unlink()
    except OSError:
        pass
    log = Log(log_path)
    global LOG
    LOG = None  # 自檢時不記每一筆 http
    log(f"{APP_NAME} {VERSION} selftest start; frozen={FROZEN}; web_root={WEB_ROOT}")
    ok = True
    try:
        srv, port = start_server(preferred)
        base = f"http://127.0.0.1:{port}/"
        log("server", base)
        for rel, want in SELFTEST_FILES:
            try:
                with urllib.request.urlopen(base + rel, timeout=15) as r:
                    body = r.read()
                    ctype = r.headers.get("Content-Type", "")
                    good = r.status == 200 and ctype.startswith(want) and len(body) > 0
                    log("OK  " if good else "FAIL", r.status, ctype, len(body), rel)
            except Exception as e:  # noqa: BLE001
                good = False
                log("FAIL", repr(e), rel)
            ok &= good
        # 根目錄應回 index.html
        with urllib.request.urlopen(base, timeout=15) as r:
            good = r.status == 200 and b"<title>" in r.read()
            log("OK  " if good else "FAIL", "/ ->", r.status)
            ok &= good
        srv.shutdown()
        srv.server_close()
    except Exception as e:  # noqa: BLE001
        ok = False
        log("FAIL exception", repr(e))
    log("RESULT", "PASS" if ok else "FAIL", "exit", 0 if ok else 1)
    return 0 if ok else 1


def emit_text(text):
    """無主控台 exe：若有繼承的標準輸出就寫進去，否則用訊息框。"""
    try:
        if sys.stdout is not None:
            sys.stdout.write(text + "\n")
            sys.stdout.flush()
            return
        import ctypes
        import msvcrt
        h = ctypes.windll.kernel32.GetStdHandle(-11)
        if h not in (0, -1, None):
            fd = msvcrt.open_osfhandle(h, os.O_WRONLY)
            os.write(fd, (text + "\n").encode("utf-8"))
            return
    except Exception:  # noqa: BLE001
        pass
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, APP_NAME, 0x40)
    except Exception:  # noqa: BLE001
        pass


def run_gui(preferred, open_browser):
    global LOG
    log_dir = Path(tempfile.gettempdir()) / "serpentine-webar"
    LOG = Log(log_dir / "launcher.log")
    srv, port = start_server(preferred)
    url = f"http://127.0.0.1:{port}/launcher.html"
    LOG(f"{APP_NAME} {VERSION} start; pid={os.getpid()}; port={port}; url={url}; web_root={WEB_ROOT}")
    # 給測試程式讀埠號
    try:
        (log_dir / "launcher_port.txt").write_text(f"{port}\n{os.getpid()}\n", encoding="ascii")
    except OSError:
        pass

    def open_page():
        try:
            webbrowser.open(url)
        except Exception as e:  # noqa: BLE001
            LOG("open browser failed", repr(e))

    import tkinter as tk
    from tkinter import font as tkfont

    root = tk.Tk()
    root.title(f"墨玉晶格修復任務 WebAR　v{VERSION}")
    root.configure(bg="#0B1F3A")
    root.resizable(False, False)
    try:
        ico = WEB_ROOT / "assets" / "icon.png"
        root.iconphoto(True, tk.PhotoImage(file=str(ico)))
    except Exception:  # noqa: BLE001
        pass
    fam = "Microsoft JhengHei UI" if "Microsoft JhengHei UI" in tkfont.families() else "Microsoft JhengHei"
    f_title = (fam, 16, "bold")
    f_body = (fam, 11)
    f_btn = (fam, 11, "bold")
    f_small = (fam, 9)

    def shutdown(*_):
        LOG("shutdown requested")
        try:
            srv.shutdown()
            srv.server_close()
        except Exception:  # noqa: BLE001
            pass
        try:
            root.destroy()
        except Exception:  # noqa: BLE001
            pass
        LOG("exit")
        os._exit(0)  # 確保不殘留任何執行緒或背景行程

    frame = tk.Frame(root, bg="#0B1F3A", padx=18, pady=14)
    frame.pack(fill="both", expand=True)
    tk.Label(frame, text="墨玉晶格修復任務 WebAR", font=f_title, fg="#ffffff", bg="#0B1F3A").pack(anchor="w")
    tk.Label(frame, text="遊戲伺服器執行中（只供這台電腦使用，不需網路）", font=f_body,
             fg="#7ef0b4", bg="#0B1F3A").pack(anchor="w", pady=(4, 8))
    tk.Label(frame, text="目前網址：", font=f_body, fg="#cfe8df", bg="#0B1F3A").pack(anchor="w")
    url_var = tk.StringVar(value=url)
    ent = tk.Entry(frame, textvariable=url_var, font=f_body, width=46, state="readonly",
                   readonlybackground="#14324f", fg="#ffffff", relief="flat")
    ent.pack(anchor="w", fill="x", ipady=4)
    tk.Label(frame, text=f"手機請掃投影畫面上的 QR 碼，連到線上網址：\n{ONLINE_URL}", font=f_small,
             fg="#cfe8df", bg="#0B1F3A", justify="left").pack(anchor="w", pady=(6, 10))
    row = tk.Frame(frame, bg="#0B1F3A")
    row.pack(anchor="w", fill="x")
    tk.Button(row, text="重新開啟頁面", font=f_btn, command=open_page, bg="#C99A3E", fg="#0B1F3A",
              activebackground="#e0b35a", relief="flat", padx=14, pady=6, cursor="hand2").pack(side="left")
    tk.Button(row, text="結束遊戲", font=f_btn, command=shutdown, bg="#2E7D5B", fg="#ffffff",
              activebackground="#2a9a6c", relief="flat", padx=14, pady=6, cursor="hand2").pack(side="left", padx=(10, 0))
    tk.Label(frame, text="關閉這個視窗就會結束遊戲伺服器。", font=f_small, fg="#9fb3c8",
             bg="#0B1F3A").pack(anchor="w", pady=(10, 0))
    tk.Label(frame, text=CREDIT, font=f_small, fg="#ffffff", bg="#06162b", padx=8, pady=3).pack(anchor="e", pady=(6, 0))
    root.protocol("WM_DELETE_WINDOW", shutdown)
    if open_browser:
        root.after(300, open_page)
    try:
        root.mainloop()
    finally:
        shutdown()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    preferred = PREFERRED_PORT
    if "--port" in argv:
        i = argv.index("--port")
        preferred = int(argv[i + 1])
    if "--version" in argv:
        emit_text(f"{APP_NAME} {VERSION}（{BUILD_DATE}）\n{ONLINE_URL}\n{CREDIT}")
        return 0
    if "--selftest" in argv:
        return run_selftest(preferred)
    run_gui(preferred, open_browser="--no-browser" not in argv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
