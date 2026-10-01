# -*- coding: utf-8 -*-
"""產生 QR 碼（assets/qr.png）與 A4 列印頁（assets/target_print.pdf：任務卡 12 cm 寬＋QR＋操作三步驟）。

用法：PYTHONUTF8=1 python tools/make_qr.py [網址]
預設網址：https://rlirdo.github.io/serpentine-webar/
需要：pip install qrcode（純 Python）
"""
import sys
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
URL = sys.argv[1] if len(sys.argv) > 1 else "https://rlirdo.github.io/serpentine-webar/"
DPI = 200
CM = DPI / 2.54
FONT_BD = r"C:\Windows\Fonts\msjhbd.ttc"
FONT_RG = r"C:\Windows\Fonts\msjh.ttc"
FONT_EN_I = r"C:\Windows\Fonts\georgiai.ttf"
CREDIT = "NDHU自資系游豐兆製作"


def main():
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=12, border=2)
    qr.add_data(URL)
    qr.make(fit=True)
    qimg = qr.make_image(fill_color="#0B1F3A", back_color="white").convert("RGB")
    qimg.save(ASSETS / "qr.png")
    print("saved", ASSETS / "qr.png", URL)

    W, H = int(21 * CM), int(29.7 * CM)
    page = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(page)
    f = lambda p, s: ImageFont.truetype(p, s)
    # 標題
    d.rectangle([0, 0, W, int(2.6 * CM)], fill="#0B1F3A")
    d.text((int(1.5 * CM), int(0.45 * CM)), "墨玉晶格修復任務卡", font=f(FONT_BD, 72), fill="white")
    d.text((int(1.55 * CM), int(1.65 * CM)), "Serpentine Lattice Repair · WebAR", font=f(FONT_EN_I, 38), fill="#A7E3CF")
    # 任務卡 12 cm
    card = Image.open(ASSETS / "target.png").convert("RGB")
    cw = int(12 * CM)
    card = card.resize((cw, cw), Image.LANCZOS)
    cx = (W - cw) // 2
    cy = int(3.4 * CM)
    page.paste(card, (cx, cy))
    d.rectangle([cx - 2, cy - 2, cx + cw + 1, cy + cw + 1], outline="#94A3B8", width=2)
    d.text((cx, cy + cw + 12), "任務卡寬 12 cm（列印時請選「實際大小／100%」）", font=f(FONT_RG, 28), fill="#64748B")
    # QR＋三步驟
    top = cy + cw + int(1.6 * CM)
    qs = int(4.2 * CM)
    page.paste(qimg.resize((qs, qs), Image.NEAREST), (int(1.6 * CM), top))
    d.text((int(1.6 * CM), top + qs + 6), "掃我開啟遊戲", font=f(FONT_BD, 30), fill="#0B1F3A")
    x = int(1.6 * CM) + qs + int(1.0 * CM)
    d.text((x, top), "操作三步驟", font=f(FONT_BD, 46), fill="#1C7293")
    steps = ["用手機掃左邊的 QR 碼，打開遊戲網頁。", "按〔開始 AR（開相機）〕，允許使用相機。", "把相機對準上方任務卡，跟墨玉小晶闖 8 關！"]
    for i, s in enumerate(steps):
        y = top + 90 + i * 92
        d.ellipse([x, y, x + 60, y + 60], fill=["#1C7293", "#2E7D5B", "#C99A3E"][i])
        d.text((x + 19, y + 4), str(i + 1), font=f(FONT_BD, 40), fill="white")
        d.text((x + 80, y + 8), s, font=f(FONT_RG, 34), fill="#1E293B")
    d.text((x, top + 90 + 3 * 92 + 6), "沒有相機也能玩：首頁選〔沒有任務卡：直接玩〕。", font=f(FONT_RG, 28), fill="#64748B")
    d.text((int(1.6 * CM), H - int(2.2 * CM)), "遊戲中「晶格修復讓遠紅外線變強」為研究團隊的工作假設，尚待實驗驗證。", font=f(FONT_RG, 26), fill="#64748B")
    # 製作者字樣（右下）
    fc = f(FONT_BD, 32)
    tw = d.textlength(CREDIT, font=fc)
    d.rounded_rectangle([W - tw - int(1.4 * CM) - 20, H - int(1.3 * CM) - 10, W - int(1.4 * CM) + 20, H - int(0.5 * CM)], radius=12, fill="#0B1F3A")
    d.text((W - tw - int(1.4 * CM), H - int(1.3 * CM)), CREDIT, font=fc, fill="white")
    out = ASSETS / "target_print.pdf"
    page.save(out, "PDF", resolution=DPI)
    page.resize((W // 3, H // 3)).save(ROOT / "tools" / "out" / "target_print_preview.png")
    print("saved", out)


if __name__ == "__main__":
    main()
