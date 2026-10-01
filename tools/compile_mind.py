# -*- coding: utf-8 -*-
"""以 headless Chrome 執行 MindAR Compiler，把 assets/target.png 編譯成 assets/targets.mind。

用法：PYTHONUTF8=1 python tools/compile_mind.py
流程：本機 http.server（tools/devserver.py）→ headless Chrome 開 tools/compile.html
     → 頁面編譯完成後 fetch POST 回本機伺服器存檔 → 本腳本讀回報並檢查檔案。
"""
import queue
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import devserver  # noqa: E402
from chrome import Chrome  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main(timeout=600):
    srv = devserver.start(8765)
    target = ROOT / "assets" / "targets.mind"
    old_mtime = target.stat().st_mtime if target.exists() else 0
    ch = Chrome(port=9333)
    try:
        ch.send("Page.enable")
        ch.send("Page.navigate", {"url": "http://127.0.0.1:8765/tools/compile.html"})
        t0 = time.time()
        result = None
        while time.time() - t0 < timeout:
            try:
                r = srv.reports.get(timeout=1)
            except queue.Empty:
                continue
            print(r, flush=True)
            if r.get("event") in ("done", "error"):
                result = r
                break
        if not result or result["event"] != "done":
            print("編譯失敗：", result)
            return 1
        ok = target.exists() and target.stat().st_mtime > old_mtime and target.stat().st_size > 1000
        print("targets.mind:", target.stat().st_size, "bytes", "OK" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        ch.close()
        srv.shutdown()


if __name__ == "__main__":
    sys.exit(main())
