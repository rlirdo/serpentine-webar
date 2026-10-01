# -*- coding: utf-8 -*-
"""AR 假相機自我測試。

1. 把任務卡（assets/target.png）以透視變形合成到「桌面」背景上（約佔畫面 50%），輸出 y4m 影片：
   0–7 秒有卡片 → 7–11 秒卡片移出畫面（測試追蹤遺失與懸浮模式）→ 11–18 秒卡片回來（測試重新貼回）。
2. 本機 http.server ＋ headless Chrome（--use-fake-device-for-media-stream --use-fake-ui-for-media-stream
   --use-file-for-fake-video-capture=…）開 ar.html?selftest=1。
3. 頁面在 targetFound 且完成首幀渲染後 POST 回報；另回報 targetLost／floatMode／reattached。
   每個事件以 CDP 截圖存 tools/shots/ar_*.png，結果寫 tools/out/selftest_ar.json。

用法：PYTHONUTF8=1 python tools/selftest_ar.py
"""
import json
import queue
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import devserver  # noqa: E402
from chrome import Chrome  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tools" / "out"
SHOTS = ROOT / "tools" / "shots"
W, H, FPS = 640, 480, 10
QUAD = [(150, 52), (502, 74), (544, 440), (108, 418)]  # 左上、右上、右下、左下


def perspective_coeffs(dst, src):
    """PIL PERSPECTIVE 係數：把輸出座標 dst 映射回輸入 src。"""
    A, b = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    return np.linalg.solve(np.array(A, float), np.array(b, float)).tolist()


def desk_background(seed=3):
    rng = np.random.default_rng(seed)
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(0, 1, W)[None, :]
    grain = np.sin(x * 60 + np.sin(y * 7) * 3) * 0.5 + 0.5
    noise = rng.normal(0, 1, (H, W))
    base = np.stack([150 + 40 * grain + 8 * noise, 110 + 30 * grain + 8 * noise, 75 + 20 * grain + 8 * noise], -1)
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    d = ImageDraw.Draw(img)
    d.rectangle([10, 300, 90, 470], fill=(225, 225, 215))  # 桌上的筆記本與鉛筆（增加真實感）
    d.line([(20, 30), (130, 120)], fill=(240, 200, 40), width=8)
    return img


def make_frames():
    bg = desk_background()
    card = Image.open(ROOT / "assets" / "target.png").convert("RGB")
    cw, ch = card.size
    coeffs = perspective_coeffs(QUAD, [(0, 0), (cw, 0), (cw, ch), (0, ch)])
    warped = card.transform((W, H), Image.PERSPECTIVE, coeffs, Image.BICUBIC)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon(QUAD, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(0.7))
    shadow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shadow).polygon([(x + 8, y + 10) for x, y in QUAD], fill=120)
    shadow = shadow.filter(ImageFilter.GaussianBlur(6))
    with_card = Image.composite(Image.new("RGB", (W, H), (40, 30, 20)), bg, shadow)
    with_card = Image.composite(warped, with_card, mask)
    area = np.array(mask).astype(float).sum() / 255 / (W * H)
    return np.array(with_card), np.array(bg), area


def to_yuv420(rgb):
    r, g, b = [rgb[..., i].astype(np.float32) for i in range(3)]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    u = -0.168736 * r - 0.331264 * g + 0.5 * b + 128
    v = 0.5 * r - 0.418688 * g - 0.081312 * b + 128
    sub = lambda c: c.reshape(H // 2, 2, W // 2, 2).mean(axis=(1, 3))
    return b"".join(np.clip(c, 0, 255).astype(np.uint8).tobytes() for c in (y, sub(u), sub(v)))


def write_y4m(path, seconds=18):
    card, bg, area = make_frames()
    Image.fromarray(card).save(OUT / "fake_cam_frame.png")
    with open(path, "wb") as f:
        f.write(f"YUV4MPEG2 W{W} H{H} F{FPS}:1 Ip A1:1 C420jpeg\n".encode())
        for i in range(seconds * FPS):
            t = i / FPS
            img = bg if 7 <= t < 11 else card
            dx, dy = int(round(2 * np.sin(i * 0.35))), int(round(2 * np.cos(i * 0.27)))  # 手持微晃
            img = np.roll(np.roll(img, dx, axis=1), dy, axis=0)
            f.write(b"FRAME\n")
            f.write(to_yuv420(img))
    return area


def main(timeout=240):
    OUT.mkdir(parents=True, exist_ok=True)
    SHOTS.mkdir(parents=True, exist_ok=True)
    for old in SHOTS.glob("ar_*.png"):
        old.unlink()
    video = OUT / "fake_cam.y4m"
    area = write_y4m(video)
    print(f"fake video: {video} ({video.stat().st_size // 1024} KB), card area ≈ {area:.0%}")
    srv = devserver.start(8767)
    ch = Chrome(port=9336, width=W, height=H, extra_args=[
        "--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream",
        f"--use-file-for-fake-video-capture={video}"])
    events = []
    shots = {}
    try:
        ch.send("Page.enable")
        ch.send("Runtime.enable")
        ch.set_viewport(W, H)
        ch.send("Page.navigate", {"url": "http://127.0.0.1:8767/ar.html?selftest=1"})
        t0 = time.time()
        need = {"targetFound", "floatMode", "reattached"}
        while time.time() - t0 < timeout and need:
            try:
                r = srv.reports.get(timeout=1)
            except queue.Empty:
                continue
            r["wall"] = round(time.time() - t0, 1)
            events.append(r)
            print(r, flush=True)
            ev = r.get("event")
            if ev in ("targetFound", "floatMode", "reattached", "targetLost"):
                time.sleep(0.4)
                fn = f"ar_{len(shots) + 1:02d}_{ev}.png"
                ch.screenshot(str(SHOTS / fn))
                shots[fn] = ev
                need.discard(ev)
            if ev == "error":
                print("頁面錯誤：", r)
        # 再等幾秒看遊戲開場畫面
        time.sleep(2)
        ch.screenshot(str(SHOTS / f"ar_{len(shots) + 1:02d}_after.png"))
        state = ch.eval("JSON.stringify(window.__arState)")
        ch.poll_events(0.3)
        errs = [e for e in ch.events if e.get("method") == "Runtime.exceptionThrown"]
    finally:
        ch.close()
        srv.shutdown()
    found = next((e for e in events if e.get("event") == "targetFound"), None)
    floatm = next((e for e in events if e.get("event") == "floatMode"), None)
    re = next((e for e in events if e.get("event") == "reattached"), None)
    in_view = lambda e: e and all(abs(v) <= 1 for v in e["stageNdc"][:2]) and e["holderVisible"]
    result = {
        "card_area_ratio": round(area, 3), "events": events, "shots": list(shots),
        "targetFound": bool(found), "found_ms": found and found["ms"],
        "floatMode": bool(floatm), "float_stage_in_view": bool(in_view(floatm)),
        "reattached": bool(re), "reattached_in_view": bool(in_view(re)),
        "exceptions": [json.dumps(e["params"].get("exceptionDetails", {}), ensure_ascii=False)[:300] for e in errs],
        "final_state": json.loads(state) if state else None,
    }
    (OUT / "selftest_ar.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "events"}, ensure_ascii=False, indent=1))
    ok = result["targetFound"] and result["floatMode"] and result["float_stage_in_view"] and result["reattached"]
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
