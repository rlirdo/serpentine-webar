# -*- coding: utf-8 -*-
"""自動通關測試：play.html?autoplay=1 逐步觸發互動，走完 開場→前測→八關→後測→行動承諾→結果頁。

用法：PYTHONUTF8=1 python tools/autoplay_test.py [mobile|desktop|landscape|all] [--base URL] [--tag 名稱]
      [--speech normal|none|novoice] [--audible]
- --base：對指定網址測試（例如線上 https://rlirdo.github.io/serpentine-webar/ 或 exe 提供的 http://127.0.0.1:埠/），
  不指定則自動起本機 tools/devserver.py。--tag 加在截圖與結果檔名前面，避免覆蓋。
- 以 CDP Network 事件記錄頁面發出的每一個請求，結果檔 requests_hosts 列出所有主機，external_requests 列出 base 以外的請求。
- 手機直向 390×844（觸控模擬）與桌機 1280×720 各一輪（all，國小版）；landscape＝手機橫向 844×390 加測（國中版）。
- 每個等待輸入的狀態截圖到 tools/shots/<視窗>_<序號>_<狀態>.png，並以 window.__ap.check()
  檢查右下製作者字樣（存在、在視窗內、z-index 最高、不與按鈕重疊）與文字是否出界。
- 收集 console error／未捕捉例外。結果寫入 tools/out/autoplay_<視窗>.json。
- 2.0.0 語音：每一步以 userGesture 觸發（讓真正的 speechSynthesis 路徑也被執行），預設音量設 0（測試時不出聲，
  --audible 才出聲）。每個畫面呼叫 __ap.speechCheck() 確認畫面上的對話／題目／選項／詳解／提示框都有對應的 speak()；
  結束時讀 window.__speech.log，以 __speech.residue() 檢查正規化後殘留符號。
  --speech none：模擬 speechSynthesis 不存在；--speech novoice：模擬裝置只有英文語音（沒有中文語音）。
"""
import functools
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import devserver  # noqa: E402
from chrome import Chrome  # noqa: E402

print = functools.partial(print, flush=True)  # noqa: A001
ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "tools" / "shots"
OUT = ROOT / "tools" / "out"
VIEWPORTS = {"mobile": (390, 844, True), "desktop": (1280, 720, False), "landscape": (844, 390, True)}
SPEECH_INIT = {
    "normal": "",
    "none": """try { Object.defineProperty(window, 'speechSynthesis', { value: undefined, configurable: true }); } catch (e) {}
try { Object.defineProperty(window, 'SpeechSynthesisUtterance', { value: undefined, configurable: true }); } catch (e) {}""",
    "novoice": """(() => { const s = window.speechSynthesis; if (!s) return;
  const fake = [{ name: 'Test English', lang: 'en-US', localService: true, default: true, voiceURI: 'test-en' }];
  s.getVoices = () => fake; })();""",
}


def run(name, port=8766, settle=0.55, max_steps=400, base=None, tag="", speech="normal", audible=False):
    w, h, mobile = VIEWPORTS[name]
    base = (base or f"http://127.0.0.1:{port}/").rstrip("/") + "/"
    base_host = urlparse(base).netloc
    label = f"{tag}{name}"
    SHOTS.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for old in SHOTS.glob(f"{label}_*.png"):
        old.unlink()
    ch = Chrome(port={"mobile": 9334, "desktop": 9335, "landscape": 9337}[name], width=w, height=h)
    console_errors = []
    records = []
    try:
        ch.send("Page.enable")
        ch.send("Runtime.enable")
        ch.send("Log.enable")
        ch.send("Network.enable")
        ch.set_viewport(w, h, mobile=mobile, dpr=1)
        init = ("" if audible else "window.__speechTestVolume = 0;\n") + SPEECH_INIT[speech]
        if init:
            ch.send("Page.addScriptToEvaluateOnNewDocument", {"source": init})
        grade = "junior" if name == "landscape" else "elem"  # 橫向加測順便跑國中版題庫與文案
        ch.send("Page.navigate", {"url": f"{base}play.html?autoplay=1&grade={grade}"})
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
            fn = f"{label}_{n:02d}_{st['label']}.png"
            ch.screenshot(str(SHOTS / fn))
            chk = ch.eval("__ap.check()")
            spk = ch.eval("__ap.speechCheck()")
            records.append({"n": n, "label": st["label"], "shot": f"tools/shots/{fn}", "check": chk, "speech": spk})
            if st["label"] == "result":
                # 結果頁可捲動：再截一張捲到底
                ch.eval("(() => { const m = document.querySelector('.modal-wrap'); m.scrollTop = m.scrollHeight; return true; })()")
                time.sleep(0.4)
                n += 1
                fn = f"{label}_{n:02d}_result-bottom.png"
                ch.screenshot(str(SHOTS / fn))
                records.append({"n": n, "label": "result-bottom", "shot": f"tools/shots/{fn}", "check": ch.eval("__ap.check()"),
                                "speech": ch.eval("__ap.speechCheck()")})
                break
            ch.eval("__ap.step()", user_gesture=True)
        ch.poll_events(0.5)
        req_urls = [ev["params"]["request"]["url"] for ev in ch.events if ev.get("method") == "Network.requestWillBeSent"]
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
        speech_log = ch.eval("""(() => { const s = window.__speech; if (!s) return null;
          return { state: s.state(), log: s.log.map((e) => ({ ...e, residue: s.residue(e.pre) })) }; })()""")
        elapsed = round(time.time() - t_start, 1)
    finally:
        ch.close()
    bad_credit = [r for r in records if not (r["check"]["credit"] and r["check"]["creditTop"]) or r["check"].get("btnOverlap")]
    overflow = [r for r in records if r["check"]["overflow"]]
    hosts = {}
    for u in req_urls:
        pu = urlparse(u)
        key = pu.netloc or pu.scheme  # data:/blob: 沒有主機
        hosts[key] = hosts.get(key, 0) + 1
    external = [u for u in req_urls if urlparse(u).scheme in ("http", "https", "ws", "wss") and urlparse(u).netloc != base_host]
    slog = (speech_log or {}).get("log", [])
    text_screens = [r for r in records if r.get("speech", {}).get("pieces")]
    speech_missing = [(r["n"], r["label"], r["speech"]["missing"]) for r in records if r.get("speech", {}).get("missing")]
    residue = [(e["i"], e["src"][:40], e["residue"]) for e in slog if e.get("residue")]
    speech_summary = {
        "mode": speech, "state": (speech_log or {}).get("state"), "speak_calls": len(slog),
        "speak_kinds": {k: sum(1 for e in slog if e["kind"] == k) for k in sorted({e["kind"] for e in slog})},
        "screens_with_text": len(text_screens), "screens_missing_speech": speech_missing, "residue": residue,
    }
    result = {
        "base": base, "viewport": f"{w}x{h}", "requests_total": len(req_urls), "requests_hosts": hosts,
        "external_requests": external, "screens": len(records), "reached_result": records[-1]["label"].startswith("result"),
        "seconds": elapsed, "console_errors": console_errors, "ap_errors": ap_errors,
        "credit_problems": [(r["n"], r["label"], r["check"]) for r in bad_credit],
        "overflow_problems": [(r["n"], r["label"], r["check"]["overflow"]) for r in overflow],
        "saved_record": json.loads(store)[-1] if store else None, "speech": speech_summary,
        "speech_log": slog, "records": records,
    }
    (OUT / f"autoplay_{label}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{label}] base={base} requests={len(req_urls)} hosts={hosts} external={len(external)}")
    print(f"[{label}] screens={result['screens']} result={result['reached_result']} secs={elapsed} "
          f"console_errors={len(console_errors)} ap_errors={len(ap_errors)} credit_problems={len(bad_credit)} overflow={len(overflow)}")
    print(f"[{label}] speech mode={speech} state={speech_summary['state']} speak_calls={len(slog)} "
          f"text_screens={len(text_screens)} missing={len(speech_missing)} residue={len(residue)}")
    for m in speech_missing[:10]:
        print("  SPEECH-MISSING", m)
    for r in residue[:10]:
        print("  RESIDUE", r)
    for e in console_errors[:10] + ap_errors[:10]:
        print("  ERR", e)
    for r in bad_credit[:10]:
        print("  CREDIT", r["n"], r["label"], r["check"])
    for r in overflow[:20]:
        print("  OVERFLOW", r["n"], r["label"], r["check"]["overflow"])
    return result


def main():
    args = sys.argv[1:]
    base = tag = None
    if "--base" in args:
        i = args.index("--base"); base = args[i + 1]; del args[i:i + 2]
    if "--tag" in args:
        i = args.index("--tag"); tag = args[i + 1]; del args[i:i + 2]
    speech = "normal"
    if "--speech" in args:
        i = args.index("--speech"); speech = args[i + 1]; del args[i:i + 2]
    audible = "--audible" in args
    if audible:
        args.remove("--audible")
    which = args[0] if args else "all"
    srv = None if base else devserver.start(8766)
    try:
        names = ["mobile", "desktop"] if which == "all" else [which]
        res = [run(n, base=base, tag=(tag + "_") if tag else "", speech=speech, audible=audible) for n in names]
    finally:
        if srv:
            srv.shutdown()
    ok = all(r["reached_result"] and not r["console_errors"] and not r["ap_errors"] and not r["credit_problems"]
             and not r["external_requests"] and not r["speech"]["residue"]
             and (speech != "normal" or not r["speech"]["screens_missing_speech"]) for r in res)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
