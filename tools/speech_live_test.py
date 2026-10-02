# -*- coding: utf-8 -*-
"""有頭 Chrome 實際發聲測試（2.0.0）：確認真的選到 zh-TW 語音、進入 speaking，並記錄 utterance 的 start／end／error 事件。

用法：PYTHONUTF8=1 python tools/speech_live_test.py
- 會開一個「看得到」的 Chrome 視窗並從喇叭唸出前幾個畫面（約 30 秒）。
- 以 CDP Input.dispatchMouseEvent 送出真的滑鼠點擊（使用者手勢），讓瀏覽器允許語音播放。
- 以 addScriptToEvaluateOnNewDocument 包住 speechSynthesis.speak，記錄每個 utterance 的事件與所用語音。
- 結果寫到 tools/out/speech_live.json。
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import devserver  # noqa: E402
from chrome import Chrome  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tools" / "out"

HOOK = """(() => {
  const s = window.speechSynthesis; if (!s) return;
  window.__live = { events: [], samples: [] };
  const orig = s.speak.bind(s);
  s.speak = (u) => {
    const rec = (type, extra) => window.__live.events.push(Object.assign({ type, t: Math.round(performance.now()),
      text: String(u.text).slice(0, 30), voice: u.voice ? u.voice.name + ' (' + u.voice.lang + ')' : null, lang: u.lang, rate: u.rate, volume: u.volume }, extra || {}));
    u.addEventListener('start', () => rec('start'));
    u.addEventListener('end', () => rec('end'));
    u.addEventListener('error', (e) => rec('error', { error: e.error }));
    rec('speak-called');
    return orig(u);
  };
  setInterval(() => window.__live.samples.push([Math.round(performance.now()), s.speaking ? 1 : 0, s.pending ? 1 : 0]), 100);
})();"""


def click_center(ch, selector):
    r = ch.eval(f"""(() => {{ const e = document.querySelector({json.dumps(selector)}); if (!e) return null;
      const b = e.getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2]; }})()""")
    if not r:
        return False
    x, y = r
    for t in ("mouseMoved", "mousePressed", "mouseReleased"):
        p = {"type": t, "x": x, "y": y}
        if t != "mouseMoved":
            p.update({"button": "left", "clickCount": 1})
        ch.send("Input.dispatchMouseEvent", p)
    return True


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    srv = devserver.start(8769)
    ch = Chrome(port=9341, width=1280, height=800, headless=False)
    result = {"steps": []}
    try:
        ch.send("Page.enable")
        ch.send("Runtime.enable")
        ch.send("Page.addScriptToEvaluateOnNewDocument", {"source": HOOK})
        ch.send("Page.navigate", {"url": "http://127.0.0.1:8769/play.html?autoplay=1"})
        for _ in range(200):
            if ch.eval("!!(window.__ap && window.__ap.ready)"):
                break
            time.sleep(0.1)
        time.sleep(1.5)
        result["voices"] = ch.eval("speechSynthesis.getVoices().filter(v => /^zh|^cmn/i.test(v.lang)).map(v => [v.name, v.lang, v.localService, v.default])")
        result["state_before_gesture"] = ch.eval("__speech.state()")
        result["speaking_before_gesture"] = ch.eval("speechSynthesis.speaking")
        # 前幾個畫面：每次用真的滑鼠點〔下一步〕，再觀察 3.5 秒
        for k in range(4):
            label = ch.eval("__ap.label")
            ok = click_center(ch, "#hud .btns .btn")
            t0 = time.time()
            seen = False
            while time.time() - t0 < 3.5:
                if ch.eval("speechSynthesis.speaking"):
                    seen = True
                time.sleep(0.1)
            result["steps"].append({"clicked_from": label, "click_ok": ok, "speaking_seen": seen,
                                    "say": ch.eval("document.querySelector('#hud .say').textContent"),
                                    "state": ch.eval("__speech.state()")})
        # 關閉語音：應立即停止
        click_center(ch, "#hud .voice")
        time.sleep(0.3)
        result["after_voice_off"] = {"speaking": ch.eval("speechSynthesis.speaking"), "pending": ch.eval("speechSynthesis.pending"),
                                     "button": ch.eval("document.querySelector('#hud .voice').textContent"),
                                     "stored": ch.eval("localStorage.getItem('serpentineWebAR.voice')")}
        click_center(ch, "#hud .voice")  # 恢復開啟
        time.sleep(2.5)
        result["after_voice_on_again"] = {"speaking_seen": ch.eval("speechSynthesis.speaking"),
                                          "stored": ch.eval("localStorage.getItem('serpentineWebAR.voice')")}
        ch.eval("speechSynthesis.cancel(); localStorage.removeItem('serpentineWebAR.voice'); true")
        live = ch.eval("window.__live")
        result["events"] = live["events"]
        samples = live["samples"]
        result["speaking_samples"] = {"total": len(samples), "speaking": sum(s[1] for s in samples)}
        result["errors"] = ch.eval("__ap.errors")
    finally:
        ch.close()
        srv.shutdown()
    ev = result["events"]
    starts = [e for e in ev if e["type"] == "start"]
    result["summary"] = {
        "zh_tw_voices": [v[0] for v in result["voices"] if v[1].lower().replace("_", "-").startswith("zh-tw")],
        "chosen_voice": result["steps"][-1]["state"]["voice"] if result["steps"] else None,
        "speak_called": sum(1 for e in ev if e["type"] == "speak-called"),
        "start_events": len(starts), "end_events": sum(1 for e in ev if e["type"] == "end"),
        "error_events": [e for e in ev if e["type"] == "error"],
        "start_voices": sorted({e["voice"] or "" for e in starts}),
        "steps_speaking_seen": [s["speaking_seen"] for s in result["steps"]],
        "page_errors": result["errors"],
    }
    (OUT / "speech_live.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=1))
    print("before gesture speaking:", result["speaking_before_gesture"], "| voice off:", result["after_voice_off"],
          "| on again:", result["after_voice_on_again"])
    ok = result["summary"]["start_events"] > 0 and all(result["summary"]["steps_speaking_seen"]) \
        and any("zh-TW" in v for v in result["summary"]["start_voices"]) and not result["after_voice_off"]["speaking"]
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
