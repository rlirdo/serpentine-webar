# -*- coding: utf-8 -*-
"""自動通關測試：play.html?autoplay=1 逐步觸發互動，走完 開場→前測→八關→後測→行動承諾→結果頁。

用法：PYTHONUTF8=1 python tools/autoplay_test.py [mobile|desktop|landscape|all]
- 手機直向 390×844（觸控模擬）與桌機 1280×720 各一輪（all，國小版）；landscape＝手機橫向 844×390 加測（國中版）。
- 每個等待輸入的狀態截圖到 tools/shots/<視窗>_<序號>_<狀態>.png，並以 window.__ap.check()
  檢查右下製作者字樣（存在、在視窗內、z-index 最高、不與按鈕重疊）與文字是否出界。
- 收集 console error／未捕捉例外。結果寫入 tools/out/autoplay_<視窗>.json。
"""
import functools
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import devserver  # noqa: E402
from chrome import Chrome  # noqa: E402

print = functools.partial(print, flush=True)  # noqa: A001
ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "tools" / "shots"
OUT = ROOT / "tools" / "out"
VIEWPORTS = {"mobile": (390, 844, True), "desktop": (1280, 720, False), "landscape": (844, 390, True)}


def run(name, port=8766, settle=0.55, max_steps=400):
    w, h, mobile = VIEWPORTS[name]
    SHOTS.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for old in SHOTS.glob(f"{name}_*.png"):
        old.unlink()
    ch = Chrome(port={"mobile": 9334, "desktop": 9335, "landscape": 9337}[name], width=w, height=h)
    console_errors = []
    records = []
    try:
        ch.send("Page.enable")
        ch.send("Runtime.enable")
        ch.send("Log.enable")
        ch.set_viewport(w, h, mobile=mobile, dpr=1)
        grade = "junior" if name == "landscape" else "elem"  # 橫向加測順便跑國中版題庫與文案
        ch.send("Page.navigate", {"url": f"http://127.0.0.1:{port}/play.html?autoplay=1&grade={grade}"})
        t_start = time.time()
        for _ in range(200):
            if ch.eval("!!(window.__ap && window.__ap.ready)"):
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("autoplay 未就緒")
        n = 0
        last_seq = -1
        while n < max_steps:
            # 等待下一個可互動狀態
            t0 = time.time()
            while time.time() - t0 < 40:
                st = ch.eval("({label: __ap.label, seq: __ap.seq, ready: __ap.ready})")
                if st["label"] == "result" or (st["ready"] and st["seq"] != last_seq):
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError(f"等待逾時：{st}")
            time.sleep(settle)
            st = ch.eval("({label: __ap.label, seq: __ap.seq})")
            last_seq = st["seq"]
            n += 1
            fn = f"{name}_{n:02d}_{st['label']}.png"
            ch.screenshot(str(SHOTS / fn))
            chk = ch.eval("__ap.check()")
            records.append({"n": n, "label": st["label"], "shot": f"tools/shots/{fn}", "check": chk})
            if st["label"] == "result":
                # 結果頁可捲動：再截一張捲到底
                ch.eval("(() => { const m = document.querySelector('.modal-wrap'); m.scrollTop = m.scrollHeight; return true; })()")
                time.sleep(0.4)
                n += 1
                fn = f"{name}_{n:02d}_result-bottom.png"
                ch.screenshot(str(SHOTS / fn))
                records.append({"n": n, "label": "result-bottom", "shot": f"tools/shots/{fn}", "check": ch.eval("__ap.check()")})
                break
            ch.eval("__ap.step()")
        ch.poll_events(0.5)
        for ev in ch.events:
            m = ev.get("method")
            p = ev.get("params", {})
            if m == "Runtime.exceptionThrown":
                console_errors.append(json.dumps(p.get("exceptionDetails", {}), ensure_ascii=False)[:400])
            elif m == "Runtime.consoleAPICalled" and p.get("type") == "error":
                console_errors.append(" ".join(str(a.get("value", a.get("description", ""))) for a in p.get("args", []))[:400])
            elif m == "Log.entryAdded" and p.get("entry", {}).get("level") == "error":
                console_errors.append(p["entry"].get("text", "")[:400])
        ap_errors = ch.eval("__ap.errors")
        store = ch.eval("localStorage.getItem('serpentineWebAR.records.v1')")
        elapsed = round(time.time() - t_start, 1)
    finally:
        ch.close()
    bad_credit = [r for r in records if not (r["check"]["credit"] and r["check"]["creditTop"]) or r["check"].get("btnOverlap")]
    overflow = [r for r in records if r["check"]["overflow"]]
    result = {
        "viewport": f"{w}x{h}", "screens": len(records), "reached_result": records[-1]["label"].startswith("result"),
        "seconds": elapsed, "console_errors": console_errors, "ap_errors": ap_errors,
        "credit_problems": [(r["n"], r["label"], r["check"]) for r in bad_credit],
        "overflow_problems": [(r["n"], r["label"], r["check"]["overflow"]) for r in overflow],
        "saved_record": json.loads(store)[-1] if store else None, "records": records,
    }
    (OUT / f"autoplay_{name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{name}] screens={result['screens']} result={result['reached_result']} secs={elapsed} "
          f"console_errors={len(console_errors)} ap_errors={len(ap_errors)} credit_problems={len(bad_credit)} overflow={len(overflow)}")
    for e in console_errors[:10] + ap_errors[:10]:
        print("  ERR", e)
    for r in bad_credit[:10]:
        print("  CREDIT", r["n"], r["label"], r["check"])
    for r in overflow[:20]:
        print("  OVERFLOW", r["n"], r["label"], r["check"]["overflow"])
    return result


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    srv = devserver.start(8766)
    try:
        names = ["mobile", "desktop"] if which == "all" else [which]
        res = [run(n) for n in names]
    finally:
        srv.shutdown()
    ok = all(r["reached_result"] and not r["console_errors"] and not r["ap_errors"] and not r["credit_problems"] for r in res)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
