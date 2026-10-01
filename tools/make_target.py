# -*- coding: utf-8 -*-
"""產生任務卡（MindAR 追蹤目標）assets/target.png（1200×1200）。

用法：
    python tools/make_target.py [石料照片路徑]

- 不給參數時使用 repo 內已縮圖的 assets/serpentine_closeup.jpg 當底紋。
- 給原始照片路徑時，會先裁切石面特寫、縮圖後覆寫 assets/serpentine_closeup.jpg。
  （照片需無人物、無車牌、無門牌；repo 內檔名一律中性。）
- 字型：Windows 內建微軟正黑體。
"""
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
CLOSEUP = ASSETS / "serpentine_closeup.jpg"
OUT = ASSETS / "target.png"
FONT_BD = r"C:\Windows\Fonts\msjhbd.ttc"
FONT_RG = r"C:\Windows\Fonts\msjh.ttc"
FONT_EN_I = r"C:\Windows\Fonts\georgiai.ttf"
FONT_EN_B = r"C:\Windows\Fonts\georgiab.ttf"
S = 1200
CREDIT = "NDHU自資系游豐兆製作"


def font(path, size):
    return ImageFont.truetype(path, size)


SUP = {"⁺": "+", "²": "2", "³": "3", "⁻": "-"}
SUB = {"₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4", "₅": "5"}


def chem_text(d, xy, text, path, size, fill):
    """以小字上下標方式畫化學式（微軟正黑體缺 Unicode 上下標字形）。回傳結束 x。"""
    x, y = xy
    f = font(path, size)
    fs = font(path, int(size * 0.62))
    for ch in text:
        if ch in SUP:
            d.text((x, y - size * 0.08), SUP[ch], font=fs, fill=fill)
            x += d.textlength(SUP[ch], font=fs)
        elif ch in SUB:
            d.text((x, y + size * 0.45), SUB[ch], font=fs, fill=fill)
            x += d.textlength(SUB[ch], font=fs)
        else:
            d.text((x, y), ch, font=f, fill=fill)
            x += d.textlength(ch, font=f)
    return x


def make_closeup(src):
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    w, h = im.size
    # 取石面中央偏右的斑點紋理（原圖 4000×3000 時約為 x1150–3450, y700–3000）
    side = int(min(w, h) * 0.76)
    cx, cy = int(w * 0.575), int(h * 0.62)
    box = (cx - side // 2, cy - side // 2, cx + side // 2, cy + side // 2)
    crop = im.crop(box).resize((S, S), Image.LANCZOS)
    crop.save(CLOSEUP, quality=86)
    print("saved", CLOSEUP)


def draw_crystal(d, cx, cy, r, mood="happy"):
    """畫墨玉小晶：六角柱雙錐晶體＋表情。"""
    top = (cx, cy - r * 1.35)
    bot = (cx, cy + r * 1.35)
    hexpts = [(cx + r * math.cos(math.radians(a)), cy + 0.42 * r * math.sin(math.radians(a)) - r * 0.35)
              for a in range(0, 360, 60)]
    low = [(x, y + r * 0.7) for x, y in hexpts]
    greens = ["#0f5132", "#1d6b46", "#2e8b57", "#3fa56b", "#1a5e3f", "#14492f"]
    # 上錐
    for i in range(6):
        a, b = hexpts[i], hexpts[(i + 1) % 6]
        d.polygon([top, a, b], fill=greens[i % 6], outline="#0b2e1f")
    # 柱身（前半）
    for i in range(6):
        a, b = hexpts[i], hexpts[(i + 1) % 6]
        c2, c1 = low[(i + 1) % 6], low[i]
        if a[1] + b[1] > 2 * (cy - r * 0.35) - 1:  # 前面
            d.polygon([a, b, c2, c1], fill=greens[(i + 2) % 6], outline="#0b2e1f")
    # 下錐（前半）
    for i in range(6):
        a, b = low[i], low[(i + 1) % 6]
        if a[1] + b[1] > 2 * (cy + r * 0.35) - 1:
            d.polygon([bot, a, b], fill=greens[(i + 4) % 6], outline="#0b2e1f")
    # 高光
    d.polygon([(cx - r * 0.55, cy - r * 0.6), (cx - r * 0.35, cy - r * 1.05), (cx - r * 0.25, cy - r * 0.55)],
              fill="#a7f3c8")
    # 臉
    ey = cy + r * 0.05
    for sx in (-1, 1):
        ex = cx + sx * r * 0.33
        d.ellipse([ex - r * 0.17, ey - r * 0.21, ex + r * 0.17, ey + r * 0.21], fill="white", outline="#0b2e1f",
                  width=3)
        d.ellipse([ex - r * 0.1 + sx * 3, ey - r * 0.1, ex + r * 0.1 + sx * 3, ey + r * 0.14], fill="#0b1f3a")
        d.ellipse([ex - r * 0.04 + sx * 3, ey - r * 0.08, ex + r * 0.03 + sx * 3, ey - r * 0.01], fill="white")
        d.ellipse([ex - r * 0.16, ey + r * 0.27, ex + r * 0.06, ey + r * 0.36], fill="#f59e9e")
    my = cy + r * 0.42
    d.arc([cx - r * 0.2, my - r * 0.16, cx + r * 0.2, my + r * 0.12], 20, 160, fill="#0b2e1f", width=5)


def main():
    if len(sys.argv) > 1:
        make_closeup(sys.argv[1])
    if not CLOSEUP.exists():
        sys.exit("缺少 assets/serpentine_closeup.jpg，請提供石料照片路徑")
    rnd = random.Random(20260715)
    bg = Image.open(CLOSEUP).convert("RGB").resize((S, S), Image.LANCZOS)
    bg = ImageEnhance.Contrast(bg).enhance(1.35)
    bg = ImageEnhance.Color(bg).enhance(1.25)
    img = bg.copy()

    # 不對稱暗角：左上較暗、右下較亮，增加明暗梯度
    shade = Image.new("L", (S, S), 0)
    sd = ImageDraw.Draw(shade)
    for i in range(60):
        sd.ellipse([-500 + i * 6, -500 + i * 6, 900 - i * 4, 800 - i * 4], fill=int(i * 2.2))
    shade = shade.filter(ImageFilter.GaussianBlur(60))
    dark = Image.new("RGB", (S, S), (8, 24, 40))
    img = Image.composite(dark, img, shade.point(lambda v: min(150, v)))

    ov = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    # 六角晶格線稿（右側，大小、粗細、缺漏皆不規則）
    hx0, hy0, hr = 640, 300, 64
    for row in range(8):
        for col in range(6):
            cx = hx0 + col * hr * 1.5
            cy = hy0 + row * hr * math.sqrt(3) + (col % 2) * hr * math.sqrt(3) / 2
            if rnd.random() < 0.28 or cx > S - 40 or cy > S - 150:
                continue
            rr = hr * rnd.uniform(0.82, 1.0)
            pts = [(cx + rr * math.cos(math.radians(60 * k + 7 * row)), cy + rr * math.sin(math.radians(60 * k + 7 * row)))
                   for k in range(6)]
            w = rnd.choice([2, 3, 4, 6])
            col_line = rnd.choice([(255, 255, 255, 210), (120, 230, 200, 230), (201, 154, 62, 230)])
            d.line(pts + [pts[0]], fill=col_line, width=w)
            # 原子小圓
            for k, (px, py) in enumerate(pts):
                if rnd.random() < 0.35:
                    rad = rnd.choice([7, 10, 13])
                    fill = rnd.choice([(46, 125, 91, 255), (28, 114, 147, 255), (201, 154, 62, 255), (240, 240, 240, 255)])
                    d.ellipse([px - rad, py - rad, px + rad, py + rad], fill=fill, outline=(10, 30, 40, 255), width=2)
            if rnd.random() < 0.18:  # 發亮的空位
                d.ellipse([cx - 18, cy - 18, cx + 18, cy + 18], outline=(255, 200, 80, 255), width=5)
                d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(255, 236, 170, 255))

    # 原子符號標記（非對稱散佈）
    for txt, (x, y), c in [("Mg²⁺", (720, 560), (110, 231, 200, 255)), ("Si", (980, 380), (255, 255, 255, 255)),
                           ("O", (860, 760), (255, 214, 120, 255)), ("Ca²⁺", (1040, 900), (160, 220, 170, 255)),
                           ("Fe³⁺", (690, 870), (255, 196, 64, 255))]:
        d.rounded_rectangle([x - 8, y - 4, x + 18 * len(txt) + 18, y + 46], radius=12, fill=(8, 24, 40, 170))
        chem_text(d, (x, y), txt, FONT_BD, 34, c)

    # 標題帶（左上，非滿版）
    d.rounded_rectangle([40, 40, 820, 250], radius=28, fill=(11, 31, 58, 215))
    d.rectangle([40, 40, 64, 250], fill=(201, 154, 62, 255))
    d.text((92, 58), "墨玉晶格修復任務卡", font=font(FONT_BD, 72), fill="white")
    d.text((96, 150), "Serpentine Lattice Repair · WebAR", font=font(FONT_EN_I, 38), fill=(170, 225, 205, 255))
    d.text((96, 200), "掃描我 → 叫出墨玉小晶", font=font(FONT_RG, 28), fill=(255, 220, 150, 255))

    # 八步驟小圓（左緣直列，顏色輪替）
    cols = [(28, 114, 147), (6, 90, 130), (46, 125, 91), (201, 154, 62), (11, 31, 58)]
    fnum = font(FONT_BD, 30)
    for i in range(8):
        x, y = 70 + (i % 2) * 34, 300 + i * 74
        c = cols[i % 5]
        d.ellipse([x - 28, y - 28, x + 28, y + 28], fill=c + (255,), outline=(255, 255, 255, 255), width=3)
        d.text((x - 9, y - 21), str(i + 1), font=fnum, fill="white")
        if i < 7:
            d.line([(x, y + 28), (70 + ((i + 1) % 2) * 34, y + 46)], fill=(255, 255, 255, 200), width=3)

    # 墨玉小晶（左下）
    d.ellipse([170, 640, 560, 1040], fill=(255, 255, 255, 60))
    for k in range(5):  # 遠紅外波紋（弧線，不封閉）
        rr = 230 + k * 34
        d.arc([365 - rr, 840 - rr, 365 + rr, 840 + rr], 200 + k * 9, 300 + k * 6,
              fill=(239, 108, 60, 220 - k * 30), width=8 - k)
    draw_crystal(d, 365, 840, 150)

    # 小標語卡片（右下偏中）
    d.rounded_rectangle([600, 1000, 1130, 1088], radius=20, fill=(255, 255, 255, 225))
    chem_text(d, (626, 1016), "Mg₃Si₂O₅(OH)₄ ＋ 深層海水", FONT_BD, 36, (11, 31, 58, 255))

    # 編號角標（右上）
    d.polygon([(1060, 0), (S, 0), (S, 140)], fill=(46, 125, 91, 255))
    d.text((1112, 14), "01", font=font(FONT_EN_B, 40), fill="white")

    # 製作者字樣（右下，固定）
    fc = font(FONT_BD, 30)
    tw = d.textlength(CREDIT, font=fc)
    d.rounded_rectangle([S - tw - 52, S - 76, S - 20, S - 20], radius=14, fill=(0, 0, 0, 170))
    d.text((S - tw - 36, S - 70), CREDIT, font=fc, fill="white")

    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    img.save(OUT, optimize=True)
    print("saved", OUT, img.size)

    # 網頁小圖示（墨玉小晶）
    ico = Image.new("RGBA", (192, 192), (11, 31, 58, 255))
    draw_crystal(ImageDraw.Draw(ico), 96, 100, 62)
    ico.save(ASSETS / "icon.png")
    print("saved", ASSETS / "icon.png")


if __name__ == "__main__":
    main()
