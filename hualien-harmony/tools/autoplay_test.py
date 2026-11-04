# -*- coding: utf-8 -*-
"""墨玉護衛隊自動通關測試：index.html?autoplay=1 走完
開場 → 玩家資料 → 主角 → 前測 → 八關（駕駛）→ 後測 → 行動承諾 → 結果。

用法：PYTHONUTF8=1 python tools/autoplay_test.py [mobile|desktop|landscape|all] [--base URL] [--tag 名稱] [--audible] [--no-atlas]
- --no-atlas：擋掉 assets/sprites.json，驗證圖集缺席時以純色占位跑完全程（該 404／blocked 列為預期）。
- 不指定 --base 時自動起本機 tools/devserver.py（網站根目錄＝hualien-harmony/）。
- 手機直向 390×844（觸控模擬）與桌機 1280×720 各一輪（all）；landscape＝手機橫向 844×390 加測。
- 每個等待輸入的畫面截圖到 tools/shots/<視窗>_<序號>_<畫面>.png；每關駕駛中再截一張。
- 每個畫面呼叫 __ap.check()（右下製作者字樣存在／在視窗內／z-index 最高／不與按鈕重疊、文字不出界、方向盤可見）
  與 __ap.speechCheck()（畫面文字都有對應 speak()）。
- 收集 console error／未捕捉例外；檢查 __audio.log 非空、__speech.log 非空；每關駕駛需在 25 秒內完成。
- 上傳紀錄（autoplay 不真的上傳）檢查 schema webar-game-v2 欄位順序。結果寫入 tools/out/autoplay_<視窗>.json。
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
FIELDS_V2 = ["schema", "submitted_at", "event", "pid", "sid", "phase", "grade", "mode", "client_time", "age", "gender", "org",
             "hero", "pre", "post", "preScore", "postSame3", "postScore", "stars", "totalStars", "facets", "commit", "ua"]
LEVEL_LIMIT = 25.0


def run(name, port=8777, settle=0.45, max_steps=300, base=None, tag="", audible=False, no_atlas=False):
    w, h, mobile = VIEWPORTS[name]
    base = (base or f"http://127.0.0.1:{port}/").rstrip("/") + "/"
    base_host = urlparse(base).netloc
    label = f"{tag}{name}"
    SHOTS.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for old in SHOTS.glob(f"{label}_*.png"):
        old.unlink()
    ch = Chrome(port={"mobile": 9344, "desktop": 9345, "landscape": 9347}[name], width=w, height=h)
    console_errors, records, play_shots = [], [], []
    t_start = time.time()
    try:
        ch.send("Page.enable")
        ch.send("Runtime.enable")
        ch.send("Log.enable")
        ch.send("Network.enable")
        ch.set_viewport(w, h, mobile=mobile, dpr=1)
        if no_atlas:  # 模擬圖集尚未產出：擋掉 sprites.json，遊戲應以純色占位跑完全程
            ch.send("Network.setBlockedURLs", {"urls": ["*assets/sprites.json*"]})
        if not audible:
            ch.send("Page.addScriptToEvaluateOnNewDocument", {"source": "window.__speechTestVolume = 0;"})
        ch.send("Page.navigate", {"url": f"{base}index.html?autoplay=1"})
        for _ in range(300):
            try:
                if ch.eval("!!(window.__ap && window.__ap.ready)"):
                    break
            except RuntimeError:
                pass
            time.sleep(0.1)
        else:
            raise RuntimeError("autoplay 未就緒")
        n = 0
        last_seq = -1
        steps = 0
        while steps < max_steps:
            t0 = time.time()
            while True:
                st = ch.eval("__ap.state()")
                if st["screen"] == "result" or st["playing"] or (st["waiting"] and st["seq"] != last_seq):
                    break
                if time.time() - t0 > 30:
                    raise RuntimeError(f"等待逾時：{st}")
                time.sleep(0.1)
            if st["playing"]:
                # 駕駛中：1 秒後截一張（第 1、5 關另外強制撞一次危險物），之後等關卡結束
                lv = st["screen"]
                tp = time.time()
                time.sleep(1.0)
                n += 1
                fn = f"{label}_{n:02d}_{lv}.png"
                ch.screenshot(str(SHOTS / fn))
                chk = ch.eval("__ap.check()")
                info = ch.eval("__ap.state()")
                records.append({"n": n, "label": lv, "shot": f"tools/shots/{fn}", "check": chk, "speech": ch.eval("__ap.speechCheck()"), "hud": info.get("hud"),
                                "still_playing": info.get("playing")})
                play_shots.append(fn)
                if lv in ("L1-play", "L5-play"):
                    hz = ch.eval("__ap.forceHit()")
                    time.sleep(0.35)
                    n += 1
                    fn = f"{label}_{n:02d}_{lv}-hit.png"
                    ch.screenshot(str(SHOTS / fn))
                    records.append({"n": n, "label": lv + "-hit", "shot": f"tools/shots/{fn}", "check": ch.eval("__ap.check()"),
                                    "speech": ch.eval("__ap.speechCheck()"), "hud": ch.eval("__ap.state().hud"), "forced": hz,
                                    "toast": ch.eval("__ap.toast()")})
                    play_shots.append(fn)
                while ch.eval("__ap.state().playing"):
                    if time.time() - tp > 60:
                        raise RuntimeError(f"{lv} 超過 60 秒未完成：{ch.eval('__ap.state()')}")
                    time.sleep(0.2)
                continue
            time.sleep(settle)
            st = ch.eval("__ap.state()")
            last_seq = st["seq"]
            n += 1
            fn = f"{label}_{n:02d}_{st['screen']}.png"
            ch.screenshot(str(SHOTS / fn))
            records.append({"n": n, "label": st["screen"], "shot": f"tools/shots/{fn}", "check": ch.eval("__ap.check()"), "speech": ch.eval("__ap.speechCheck()")})
            if st["screen"] == "result":
                ch.eval("(() => { const p = document.getElementById('panel'); p.scrollTop = p.scrollHeight; return true; })()")
                time.sleep(0.4)
                n += 1
                fn = f"{label}_{n:02d}_result-bottom.png"
                ch.screenshot(str(SHOTS / fn))
                records.append({"n": n, "label": "result-bottom", "shot": f"tools/shots/{fn}", "check": ch.eval("__ap.check()"), "speech": ch.eval("__ap.speechCheck()")})
                break
            ch.eval("__ap.step()", user_gesture=True)
            steps += 1
        ch.poll_events(0.6)
        req_urls = [ev["params"]["request"]["url"] for ev in ch.events if ev.get("method") == "Network.requestWillBeSent"]
        for ev in ch.events:
            m = ev.get("method")
            p = ev.get("params", {})
            if m == "Runtime.exceptionThrown":
                console_errors.append(json.dumps(p.get("exceptionDetails", {}), ensure_ascii=False)[:400])
            elif m == "Runtime.consoleAPICalled" and p.get("type") == "error":
                console_errors.append(" ".join(str(a.get("value", a.get("description", ""))) for a in p.get("args", []))[:400])
            elif m == "Log.entryAdded" and p.get("entry", {}).get("level") == "error":
                e = p["entry"]
                console_errors.append((e.get("text", "") + " " + e.get("url", ""))[:400])
        ap_errors = ch.eval("__ap.errors")
        level_times = ch.eval("__ap.levelTimes")
        audio = ch.eval("({ n: __audio.log.length, state: __audio.state(), names: [...new Set(__audio.log.map((e) => e.name))] })")
        speech = ch.eval("""(() => { const s = window.__speech; if (!s) return null;
          return { state: s.state(), n: s.log.length, residue: s.log.map((e) => [e.src.slice(0, 30), s.residue(e.pre)]).filter((x) => x[1].length) }; })()""")
        sent = ch.eval("__ap.reporter()")
        sprite_src = ch.eval("__ap.state().sprites")
        fps = ch.eval("__ap.fps")
    finally:
        ch.close()
    elapsed = round(time.time() - t_start, 1)
    # 圖集尚未產出時，sprites.json 的 404 屬預期（遊戲以純色占位），另外列出不算錯誤
    atlas_missing = no_atlas or not (ROOT / "assets" / "sprites.json").exists()
    expected_404 = [e for e in console_errors if atlas_missing and "sprites.json" in e and ("404" in e or "BLOCKED" in e.upper())]
    real_errors = [e for e in console_errors if e not in expected_404]
    bad_credit = [r for r in records if not (r["check"]["credit"] and r["check"]["creditTop"]) or r["check"].get("btnOverlap")]
    overflow = [r for r in records if r["check"]["overflow"]]
    hits = [(r["label"], r.get("forced"), (r.get("hud") or {}).get("hits"), r.get("toast")) for r in records if r["label"].endswith("-hit")]
    hit_bad = [x for x in hits if not x[2] or not x[3]]
    wheel_bad = [r["label"] for r in records if r["label"].endswith("-play") and r.get("still_playing") and not (r["check"]["wheel"]["visible"] and r["check"]["wheel"]["inView"])]
    slow_levels = [lt for lt in level_times if lt["seconds"] > LEVEL_LIMIT]
    speech_missing = [(r["n"], r["label"], r["speech"]["missing"]) for r in records if r["speech"]["missing"]]
    order_ok = all(list(rec.keys()) == FIELDS_V2 for rec in sent) and len(sent) == 2
    external = [u for u in req_urls if urlparse(u).scheme in ("http", "https", "ws", "wss") and urlparse(u).netloc != base_host]
    result = {
        "base": base, "viewport": f"{w}x{h}", "seconds": elapsed, "sprites": sprite_src, "fps_last": fps,
        "screens": len(records), "reached_result": records[-1]["label"].startswith("result") if records else False,
        "level_times": level_times, "slow_levels": slow_levels,
        "console_errors": real_errors, "expected_atlas_404": expected_404, "ap_errors": ap_errors,
        "credit_problems": [(r["n"], r["label"], r["check"]) for r in bad_credit],
        "overflow_problems": [(r["n"], r["label"], r["check"]["overflow"]) for r in overflow],
        "wheel_problems": wheel_bad, "forced_hits": hits, "hit_problems": hit_bad, "audio": audio, "speech": speech, "speech_missing": speech_missing,
        "upload_records": sent, "upload_field_order_ok": order_ok, "external_requests": external,
        "play_shots": play_shots, "records": records,
    }
    (OUT / f"autoplay_{label}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{label}] 結果頁={result['reached_result']} 畫面={len(records)} 秒數={elapsed} 圖集={sprite_src} fps={fps}")
    print(f"[{label}] 每關秒數=" + ", ".join(f"L{lt['level']}:{lt['seconds']}s/{lt['stars']}★" for lt in level_times))
    print(f"[{label}] console_errors={len(real_errors)}（預期圖集 404={len(expected_404)}） ap_errors={len(ap_errors)} "
          f"credit={len(bad_credit)} overflow={len(overflow)} wheel={len(wheel_bad)} slow={len(slow_levels)}")
    print(f"[{label}] audio n={audio['n']} state={audio['state']} names={audio['names']}")
    print(f"[{label}] speech n={(speech or {}).get('n')} missing={len(speech_missing)} residue={len((speech or {}).get('residue', []))} "
          f"上傳欄位順序={order_ok} 外部請求={len(external)}")
    print(f"[{label}] 強制撞擊={hits}")
    for e in (real_errors + ap_errors)[:10]:
        print("  ERR", e)
    for r in bad_credit[:10]:
        print("  CREDIT", r["n"], r["label"], r["check"].get("btnOverlap"), r["check"].get("creditRect"))
    for r in overflow[:20]:
        print("  OVERFLOW", r["n"], r["label"], r["check"]["overflow"][:3])
    for m in speech_missing[:10]:
        print("  SPEECH-MISSING", m)
    result["ok"] = bool(result["reached_result"] and not real_errors and not ap_errors and not bad_credit and not overflow
                        and not wheel_bad and not hit_bad and not slow_levels and audio["n"] > 0 and speech and speech["n"] > 0
                        and not speech_missing and order_ok and not external)
    print(f"[{label}] {'通過' if result['ok'] else '未通過'}")
    return result


def main():
    args = sys.argv[1:]
    base = tag = None
    if "--base" in args:
        i = args.index("--base"); base = args[i + 1]; del args[i:i + 2]
    if "--tag" in args:
        i = args.index("--tag"); tag = args[i + 1]; del args[i:i + 2]
    audible = "--audible" in args
    if audible:
        args.remove("--audible")
    no_atlas = "--no-atlas" in args
    if no_atlas:
        args.remove("--no-atlas")
    which = args[0] if args else "all"
    srv = None if base else devserver.start(8777)
    try:
        names = ["mobile", "desktop"] if which == "all" else [which]
        res = [run(n, base=base, tag=(tag + "_") if tag else "", audible=audible, no_atlas=no_atlas) for n in names]
    finally:
        if srv:
            srv.shutdown()
    return 0 if all(r["ok"] for r in res) else 1


if __name__ == "__main__":
    sys.exit(main())
