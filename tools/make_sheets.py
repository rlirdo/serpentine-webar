# -*- coding: utf-8 -*-
"""把 tools/shots/*.png 縮成總覽圖（JPEG）存 tools/shots/sheets/，供 repo 保存測試證據。

原始 PNG 體積大，不進 git（見 .gitignore）；需要時重跑 autoplay_test.py／selftest_ar.py／pages_shots.py 即可重產。
用法：PYTHONUTF8=1 python tools/make_sheets.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "tools" / "shots"
OUT = SHOTS / "sheets"
GROUPS = {"mobile": (0.34, 8), "desktop": (0.22, 5), "landscape": (0.3, 6), "ar": (0.5, 5), "page": (0.3, 6)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype(r"C:\Windows\Fonts\msjh.ttc", 14)
    for g, (scale, per) in GROUPS.items():
        fs = sorted(SHOTS.glob(f"{g}_*.png"))
        if not fs:
            continue
        ims = [Image.open(p).convert("RGB") for p in fs]
        tw = max(int(i.width * scale) for i in ims)
        th = max(int(i.height * scale) for i in ims)
        rows = (len(ims) + per - 1) // per
        sheet = Image.new("RGB", (per * (tw + 6), rows * (th + 22)), "white")
        d = ImageDraw.Draw(sheet)
        for k, (p, im) in enumerate(zip(fs, ims)):
            x, y = (k % per) * (tw + 6), (k // per) * (th + 22)
            sheet.paste(im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS), (x, y + 20))
            d.text((x + 2, y + 2), p.stem, font=font, fill="black")
        out = OUT / f"{g}_overview.jpg"
        sheet.save(out, quality=78, optimize=True)
        print("saved", out, f"{len(fs)} shots", f"{out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
