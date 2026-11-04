# -*- coding: utf-8 -*-
"""檢查 assets/sprites.json 與 sprites.png 是否符合規格 §9，並輸出放大預覽圖。"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
PREV = os.path.join(ROOT, "tools", "_preview")

HERO_IDS = [f"{b}_{g}" for b in ("kid", "teen", "adult", "elder") for g in ("f", "m", "n")]
ITEMS = ["rock", "trash", "energy", "water", "micelle", "fe", "powder", "mg", "salt", "drop", "photon"]
HAZS = ["wave", "ball", "solvent", "acid", "clump", "ca", "wall", "fire", "sign"]


def expected():
    e = {}
    for h in HERO_IDS:
        for f in (0, 1):
            e[f"hero_{h}_{f}"] = (24, 32, "主角")
    for i in range(1, 9):
        for f in (0, 1):
            e[f"mate_{i}_{f}"] = (24, 24, "隊友")
    for n in ITEMS:
        for f in (0, 1):
            e[f"item_{n}_{f}"] = (16, 16, "收集物")
    for n in HAZS:
        sz = 24 if n in ("wave", "ball") else 16
        for f in (0, 1):
            e[f"haz_{n}_{f}"] = (sz, sz, "危險物")
    for s in range(1, 9):
        for k in "abc":
            e[f"tile_s{s}_{k}"] = (32, 32, "地磚")
    e["ui_wheel"] = (160, 160, "UI")
    for n in ("ui_star_on", "ui_star_off", "ui_heart", "ui_lattice_empty", "ui_lattice_full"):
        e[n] = (16, 16, "UI")
    e["ui_harmony"] = (32, 32, "UI")
    return e


CAT_FILE = {"主角": "heroes", "隊友": "mates", "收集物": "items", "危險物": "hazards", "地磚": "tiles", "UI": "ui"}


def checker(w, h, s=8):
    a = np.zeros((h, w, 4), np.uint8)
    yy, xx = np.mgrid[0:h, 0:w]
    m = ((xx // s + yy // s) % 2) == 0
    a[m] = (70, 74, 82, 255)
    a[~m] = (52, 56, 64, 255)
    return Image.fromarray(a, "RGBA")


def preview(cat, names, sheet, frames, scale, path):
    font = ImageFont.load_default()
    cells = []
    for n in names:
        f = frames[n]
        im = sheet.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"]))
        cells.append((n, im.resize((f["w"] * scale, f["h"] * scale), Image.NEAREST)))
    cw = max(c[1].width for c in cells) + 16
    ch = max(c[1].height for c in cells) + 28
    cols = 6 if cat in ("主角", "隊友", "地磚") else 8
    if cat == "UI":
        cols = 4
    rows = (len(cells) + cols - 1) // cols
    W, Hh = cols * cw, rows * ch
    bg = checker(W, Hh)
    d = ImageDraw.Draw(bg)
    for i, (n, im) in enumerate(cells):
        x = (i % cols) * cw + 8
        y = (i // cols) * ch + 6
        bg.alpha_composite(im, (x, y))
        d.text((x, y + im.height + 4), n, fill=(255, 255, 255, 255), font=font)
    bg.save(path)


def main():
    errs = []
    js = json.load(open(os.path.join(ASSETS, "sprites.json"), encoding="utf-8"))
    sheet = Image.open(os.path.join(ASSETS, "sprites.png")).convert("RGBA")
    A = np.array(sheet)
    frames = js.get("frames", {})
    if js.get("scale") != 1:
        errs.append("scale 不是 1")
    exp = expected()
    for n, (w, h, _) in exp.items():
        if n not in frames:
            errs.append(f"缺少 {n}")
            continue
        f = frames[n]
        if (f["w"], f["h"]) != (w, h):
            errs.append(f"{n} 尺寸 {f['w']}x{f['h']}，應為 {w}x{h}")
    extra = sorted(set(frames) - set(exp))
    if extra:
        errs.append(f"多出未定義名稱：{extra}")
    occ = np.zeros(A.shape[:2], np.int32)
    for n, f in frames.items():
        x, y, w, h = f["x"], f["y"], f["w"], f["h"]
        if x < 0 or y < 0 or x + w > sheet.width or y + h > sheet.height:
            errs.append(f"{n} 超出圖集範圍")
            continue
        occ[y:y + h, x:x + w] += 1
        if A[y:y + h, x:x + w, 3].max() == 0:
            errs.append(f"{n} 全透明")
    if occ.max() > 1:
        bad = [n for n, f in frames.items() if occ[f["y"]:f["y"] + f["h"], f["x"]:f["x"] + f["w"]].max() > 1]
        errs.append(f"有 frame 互相重疊：{bad[:10]}")
    for n in exp:
        if n.endswith("_0") and n[:-2] + "_1" in exp:
            a, b = frames.get(n), frames.get(n[:-2] + "_1")
            if a and b:
                ca = A[a["y"]:a["y"] + a["h"], a["x"]:a["x"] + a["w"]]
                cb = A[b["y"]:b["y"] + b["h"], b["x"]:b["x"] + b["w"]]
                diff = int((ca != cb).any(axis=2).sum())
                if diff < 4:
                    errs.append(f"{n[:-2]} 兩幀差異過小（{diff} px）")
    # 標題圖
    for fn, sz in (("title.png", (320, 180)), ("title_4x.png", (1280, 720))):
        p = os.path.join(ASSETS, fn)
        if not os.path.exists(p):
            errs.append(f"缺少 {fn}")
        elif Image.open(p).size != sz:
            errs.append(f"{fn} 尺寸 {Image.open(p).size}，應為 {sz}")

    os.makedirs(PREV, exist_ok=True)
    sheet.resize((sheet.width * 4, sheet.height * 4), Image.NEAREST).save(os.path.join(PREV, "sheet_4x.png"))
    for cat, fn in CAT_FILE.items():
        names = [n for n, v in exp.items() if v[2] == cat and n in frames]
        sc = 2 if cat == "UI" else (4 if cat == "地磚" else 6)
        preview(cat, names, sheet, frames, sc, os.path.join(PREV, f"{fn}_x{sc}.png"))

    print(f"圖集 {sheet.width}x{sheet.height}，frame {len(frames)} 個（規格 {len(exp)} 個）")
    if errs:
        print("檢查未通過：")
        for e in errs:
            print("  ✗", e)
        sys.exit(1)
    print("✓ 名稱齊全、尺寸正確、不重疊、無全透明、兩幀皆有差異、標題圖尺寸正確")
    print("預覽圖輸出於", PREV)


if __name__ == "__main__":
    main()
