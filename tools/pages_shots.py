# -*- coding: utf-8 -*-
"""一般頁面截圖與製作者字樣檢查：index／card／teacher（含一筆示範紀錄）／ar 載入畫面。

用法：PYTHONUTF8=1 python tools/pages_shots.py
截圖存 tools/shots/page_<視窗>_<頁>.png，結果寫 tools/out/pages.json。
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import devserver  # noqa: E402
from chrome import Chrome  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "tools" / "shots"
OUT = ROOT / "tools" / "out"
VIEWPORTS = {"mobile": (390, 844, True), "desktop": (1280, 720, False)}
PAGES = ["index.html", "card.html", "teacher.html"]
CHECK = """(() => {
  const c = document.getElementById('credit'); if (!c) return {credit:false};
  const r = c.getBoundingClientRect(), cs = getComputedStyle(c);
  const overX = [...document.querySelectorAll('body *')].filter(e => { const q = e.getBoundingClientRect(); return q.width && (q.right > innerWidth + 1) && !e.closest('.tablewrap'); }).map(e => e.tagName + '.' + e.className).slice(0, 5);
  return {credit: c.textContent.trim() === 'NDHU自資系游豐兆製作' && r.right <= innerWidth && r.bottom <= innerHeight && r.width > 0,
          zIndex: cs.zIndex, position: cs.position, rect: [r.left, r.top, r.right, r.bottom].map(Math.round), overflowX: overX};
})()"""
DEMO = {"time": "2026-10-01T08:00:00.000Z", "grade": "elem", "stars": [3, 3, 2, 3, 3, 2, 2, 3], "totalStars": 21,
        "pre": [{"id": "E1", "facet": "知識", "correct": False}, {"id": "E2", "facet": "探究", "correct": False}, {"id": "E3", "facet": "態度", "correct": True}],
        "post": [{"id": "E1", "facet": "知識", "correct": True}, {"id": "E2", "facet": "探究", "correct": True}, {"id": "E3", "facet": "態度", "correct": True},
                 {"id": "E6", "facet": "行動", "correct": True}, {"id": "E5", "facet": "知識", "correct": True}],
        "preScore": 1, "postSame3": 3, "postScore": 5, "facets": {"知識": 100, "態度": 100, "行動": 100, "探究": 100},
        "commit": "跟家人分享今天學到的事", "mode": "play", "autoplay": True}


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    srv = devserver.start(8768)
    res = {}
    try:
        for vp, (w, h, mobile) in VIEWPORTS.items():
            ch = Chrome(port=9338, width=w, height=h)
            try:
                ch.send("Page.enable")
                ch.send("Runtime.enable")
                ch.set_viewport(w, h, mobile=mobile)
                for pg in PAGES:
                    if pg == "teacher.html":
                        ch.send("Page.navigate", {"url": "http://127.0.0.1:8768/index.html"})
                        time.sleep(0.8)
                        ch.eval(f"localStorage.setItem('serpentineWebAR.records.v1', JSON.stringify([{json.dumps(DEMO, ensure_ascii=False)}]))")
                    ch.send("Page.navigate", {"url": f"http://127.0.0.1:8768/{pg}"})
                    time.sleep(1.5)
                    fn = f"page_{vp}_{pg.replace('.html', '')}.png"
                    ch.screenshot(str(SHOTS / fn))
                    res[f"{vp}/{pg}"] = {"shot": f"tools/shots/{fn}", **ch.eval(CHECK)}
                    print(vp, pg, res[f"{vp}/{pg}"], flush=True)
                ch.poll_events(0.3)
                exc = [e for e in ch.events if e.get("method") == "Runtime.exceptionThrown"]
                res[f"{vp}/exceptions"] = len(exc)
            finally:
                ch.close()
    finally:
        srv.shutdown()
    (OUT / "pages.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = all(v["credit"] for k, v in res.items() if isinstance(v, dict)) and not any(res[k] for k in res if k.endswith("exceptions"))
    print("OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
