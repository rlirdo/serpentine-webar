# -*- coding: utf-8 -*-
"""晶球護衛隊：幻彩人工魚子醬大冒險 — 像素圖集產生器（沿用墨玉護衛隊產生器的畫布、字型與主角骨架）。

純程式繪製像素圖（PIL + numpy），確定性、可重跑；不讀取任何外部圖片或字型。
輸出：
  assets/sprites.png   RGBA 圖集（透明背景）
  assets/sprites.json  {"scale":1,"frames":{name:{x,y,w,h}}}
  assets/title.png     320x180 標題圖
  assets/title_4x.png  4 倍放大版（最近鄰）
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")

OUTLINE = (18, 16, 32, 255)
CLEAR = (0, 0, 0, 0)


def H(s, a=255):
    if isinstance(s, tuple):
        return s
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), a)


# ---------------------------------------------------------------- 畫布
class C:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.a = np.zeros((h, w, 4), np.uint8)

    def p(self, x, y, c):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            self.a[y, x] = H(c)

    def opaque(self, x, y):
        x, y = int(x), int(y)
        return 0 <= x < self.w and 0 <= y < self.h and self.a[y, x, 3] > 0

    def rect(self, x0, y0, x1, y1, c, clip=False):
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1):
                if not clip or self.opaque(x, y):
                    self.p(x, y, c)

    def circle(self, cx, cy, r, c, clip=False):
        self.ellipse(cx, cy, r, r, c, clip)

    def ellipse(self, cx, cy, rx, ry, c, clip=False):
        yy, xx = np.mgrid[0:self.h, 0:self.w]
        dx = (xx + 0.5 - cx) / max(rx, 0.01)
        dy = (yy + 0.5 - cy) / max(ry, 0.01)
        m = dx * dx + dy * dy <= 1.0
        if clip:
            m &= self.a[:, :, 3] > 0
        self.a[m] = H(c)

    def erase_ellipse(self, cx, cy, rx, ry):
        yy, xx = np.mgrid[0:self.h, 0:self.w]
        dx = (xx + 0.5 - cx) / rx
        dy = (yy + 0.5 - cy) / ry
        self.a[dx * dx + dy * dy <= 1.0] = 0

    def poly(self, pts, c, clip=False):
        m = Image.new("L", (self.w, self.h), 0)
        ImageDraw.Draw(m).polygon([tuple(p) for p in pts], fill=1, outline=1)
        mm = np.array(m) > 0
        if clip:
            mm &= self.a[:, :, 3] > 0
        self.a[mm] = H(c)

    def line(self, x0, y0, x1, y1, c, w=1, clip=False):
        x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            for ox in range(w):
                for oy in range(w):
                    if not clip or self.opaque(x0 + ox, y0 + oy):
                        self.p(x0 + ox, y0 + oy, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def sphere(self, cx, cy, r, dark, base, light, spec="#ffffff"):
        self.circle(cx, cy, r, dark)
        inside = self.a[:, :, 3].copy()
        tmp = self.a.copy()
        self.circle(cx - r * 0.18, cy - r * 0.18, r * 0.8, base)
        self.a[inside == 0] = tmp[inside == 0]
        self.circle(cx - r * 0.38, cy - r * 0.38, max(r * 0.32, 1.0), light, clip=True)
        if spec:
            self.p(cx - r * 0.5, cy - r * 0.5, spec)

    def outline(self, c=OUTLINE):
        al = self.a[:, :, 3] > 0
        pad = np.pad(al, 1)
        n = pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]
        ring = n & ~al
        self.a[ring] = c

    def img(self):
        return Image.fromarray(self.a, "RGBA")


# ---------------------------------------------------------------- 小字型（3x5 / 5x5）
F3 = {
    "2": ["111", "001", "111", "100", "111"], "3": ["111", "001", "011", "001", "111"],
    "+": ["000", "010", "111", "010", "000"], "F": ["111", "100", "110", "100", "100"],
    "e": ["000", "010", "101", "110", "011"], "T": ["111", "010", "010", "010", "010"],
    "C": ["111", "100", "100", "100", "111"], "a": ["000", "011", "101", "101", "011"],
}
F5 = {  # 5x7 點陣大寫字
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "11001", "10101", "10011", "10011", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    " ": ["000", "000", "000", "000", "000", "000", "000"],
}


def text(cv, s, x, y, c, font=F3, sp=1, scale=1):
    for ch in s:
        g = font[ch]
        for j, row in enumerate(g):
            for i, b in enumerate(row):
                if b == "1":
                    for a in range(scale):
                        for bb in range(scale):
                            cv.p(x + i * scale + a, y + j * scale + bb, c)
        x += (len(g[0]) + sp) * scale
    return x


def text_w(s, font=F3, sp=1, scale=1):
    return sum((len(font[ch][0]) + sp) * scale for ch in s) - sp * scale


# ---------------------------------------------------------------- 主角 24x32（面向右）
SKIN, SKIN_D = "#f2c29b", "#d39a72"
BANDS = {
    #        head_w head_h torso legs body_w
    "kid": (9, 9, 5, 4, 7),
    "teen": (8, 8, 7, 7, 6),
    "adult": (8, 8, 9, 8, 7),
    "elder": (8, 8, 8, 6, 7),
}
HAIR = {"f": ("#5a2e1a", "#3a1a0e"), "m": ("#1c1c2a", "#0e0e16"), "n": ("#7a5634", "#57391f")}
HAIR_ELDER = {"f": ("#d7d7dc", "#a9a9b4"), "m": ("#eeeeee", "#bdbdc4"), "n": ("#b9b9bf", "#8f8f99")}
SHIRT = {
    "kid": {"f": ("#ec6f9c", "#b8487a"), "m": ("#3d8fd6", "#2a63a0"), "n": ("#e8c547", "#b8962a")},
    "teen": {k: ("#2fa05f", "#1f6e42") for k in "fmn"},
    "adult": {k: ("#f7f9fb", "#c3ccd6") for k in "fmn"},
    "elder": {"f": ("#9a5fc0", "#6e3f8e"), "m": ("#9a6a3f", "#6e4826"), "n": ("#5e8f8a", "#3f6662")},
}
INNER = {"f": "#ec6f9c", "m": "#3d8fd6", "n": "#e8c547"}
PANTS = {
    "kid": {"f": ("#ec6f9c", "#b8487a"), "m": ("#2c3e78", "#1d2a55"), "n": ("#7d8a6a", "#5a654b")},
    "teen": {"f": ("#d23c4b", "#9c2534"), "m": ("#24345f", "#172240"), "n": ("#8a8f99", "#62666f")},
    "adult": {"f": ("#7a2f4f", "#561f37"), "m": ("#24345f", "#172240"), "n": ("#6f7a52", "#4f583a")},
    "elder": {"f": ("#4a3b5c", "#33283f"), "m": ("#5a4a3a", "#3e3226"), "n": ("#55606b", "#3c444c")},
}
SHOE = ("#3b2a20", "#24170f")


def draw_hero(band, g, frame):
    cv = C(24, 32)
    hw, hh, th, lh, bw = BANDS[band]
    cx = 11
    hunch = band == "elder"
    leg_top = 31 - lh
    torso_top = leg_top - th
    head_top = torso_top - hh
    hx0 = cx - hw // 2 + 1 + (2 if hunch else 0)
    hy0 = head_top + (1 if hunch else 0)
    hx1 = hx0 + hw - 1
    hy1 = hy0 + hh - 1
    shirt, shirt_d = SHIRT[band][g]
    pants, pants_d = PANTS[band][g]
    bx0 = cx - bw // 2
    bx1 = bx0 + bw - 1
    skirt = (g == "f" and band in ("kid", "teen"))
    hair, hair_d = (HAIR_ELDER if band == "elder" else HAIR)[g]

    # 走路：frame0 近腳在前、frame1 近腳在後
    stride = 2 if band == "kid" else 3
    near_dx, far_dx = (stride, -stride) if frame == 0 else (-stride, stride)

    # --- 背後：長髮、撿石袋
    if g == "f" and band != "elder":
        low = torso_top + (2 if band == "kid" else 3)
        cv.rect(hx0 - 1, hy0 + 2, hx0 + 2, low, hair_d)
        cv.rect(hx0, hy0 + 2, hx0 + 2, low - 1, hair)
    if band == "elder":
        cv.rect(bx0 - 4, torso_top + 1, bx0, torso_top + 7, "#a07a48")
        cv.rect(bx0 - 4, torso_top + 6, bx0, torso_top + 7, "#7a5a30")
        cv.rect(bx0 - 3, torso_top - 2, bx0 - 1, torso_top + 1, "#6b4f12")  # 藻籃露出褐藻
        cv.p(bx0 - 2, torso_top - 3, "#9a7a24")
        cv.line(bx0 - 3, torso_top + 3, bx0 - 1, torso_top + 3, "#7a5a30")

    legcol_far, legcol_near = pants_d, pants
    if skirt or (band == "adult" and g == "f"):
        legcol_far, legcol_near = SKIN_D, SKIN

    def leg(hipx, dx, col, shoe):
        fx = cx - 1 + dx
        cv.line(hipx, leg_top, fx, 28, col, w=2)
        cv.rect(fx, 29, fx + 2, 30, shoe)

    leg(cx - 1, far_dx, legcol_far, SHOE[1])

    # --- 身體
    cv.rect(bx0, torso_top, bx1, leg_top - 1, shirt)
    cv.rect(bx0, torso_top, bx0 + 1, leg_top - 1, shirt_d)
    if hunch:
        cv.rect(bx0 - 1, torso_top + 1, bx0 - 1, torso_top + 5, shirt_d)  # 駝背
        cv.rect(bx0 + 1, torso_top - 1, bx1, torso_top - 1, shirt)
    if band in ("teen", "elder") or (band == "kid" and g != "f"):
        cv.rect(bx0, leg_top - 1, bx1, leg_top - 1, pants_d)
    leg(cx, near_dx, legcol_near, SHOE[0])
    if skirt:
        sk, skd = (shirt, shirt_d) if band == "kid" else (pants, pants_d)
        cv.rect(bx0 - 1, leg_top - 1, bx1 + 1, leg_top + 1, sk)
        cv.rect(bx0 - 1, leg_top + 1, bx1 + 1, leg_top + 1, skd)
        for x in range(bx0, bx1 + 1, 2):
            cv.p(x, leg_top, skd)
    if band == "adult":  # 白色實驗衣
        cv.rect(bx0, torso_top, bx1, leg_top + 3, shirt)
        cv.rect(bx0 - 1, leg_top, bx1 + 1, leg_top + 3, shirt)
        cv.rect(bx0 - 1, leg_top, bx0, leg_top + 3, shirt_d)
        cv.rect(bx0, torso_top, bx0 + 1, leg_top - 1, shirt_d)
        cv.rect(bx0 - 1, leg_top + 3, bx1 + 1, leg_top + 3, shirt_d)
        cv.rect(bx1 - 1, torso_top + 2, bx1 - 1, leg_top + 2, shirt_d)  # 前襟
        cv.rect(bx1 - 2, torso_top, bx1, torso_top, INNER[g])  # 內衣領
        cv.p(bx1 - 1, torso_top + 1, INNER[g])
        fx, fy = bx1 - 5, torso_top + 2  # 綠燒瓶徽章
        cv.p(fx + 1, fy, "#1f6e42")
        cv.rect(fx, fy + 1, fx + 2, fy + 2, "#2fbf71")
        cv.p(fx + 1, fy + 1, "#9ff0c0")
    if band == "teen":
        cv.rect(bx0, torso_top, bx1, torso_top, "#1f6e42")
        cv.rect(bx1 - 2, torso_top + 2, bx1 - 1, torso_top + 3, "#e8fff0")  # 胸前東華小標
    if band == "kid":
        cv.rect(bx0 + 1, torso_top, bx1 - 1, torso_top, shirt_d)

    # --- 頭
    cv.rect(hx0, hy0, hx1, hy1, SKIN)
    for (x, y) in ((hx0, hy0), (hx1, hy0), (hx0, hy1), (hx1, hy1)):
        cv.p(x, y, CLEAR)
    ey = hy0 + hh // 2
    cv.p(hx1 + 1, ey + 1, SKIN)  # 鼻子
    cv.p(hx1 - 1, hy1, SKIN_D)
    cv.p(hx1 - 1, ey, "#1a1a2a")
    if band == "kid":
        cv.p(hx1 - 1, ey + 1, "#1a1a2a")
        cv.p(hx1 - 3, ey + 2, "#f08a8a")
    cv.p(hx1 - 1, ey + 2 + (1 if band == "kid" else 0), "#b0604a")  # 嘴
    if band == "elder":
        cv.p(hx1 - 2, ey - 1, "#b07a58")
        cv.p(hx1 - 3, ey + 2, "#c08a68")
    if g == "m":  # 刺刺短髮
        cv.rect(hx0, hy0, hx1 - 1, hy0 + 1, hair)
        cv.rect(hx0, hy0, hx0 + 2, ey, hair)
        for x in range(hx0, hx1, 2):
            cv.p(x, hy0 - 1, hair)
    elif g == "f":  # 長髮＋髮夾
        cv.rect(hx0, hy0, hx1, hy0 + 1, hair)
        cv.rect(hx0, hy0, hx0 + 2, hy1, hair)
        cv.p(hx1, hy0 + 2, hair)
        cv.rect(hx0 + 1, hy0 - 1, hx1 - 1, hy0 - 1, hair)
        cv.rect(hx0 + 3, hy0 - 1, hx0 + 4, hy0 - 1, "#ff6fa8")
    else:  # 中性：齊耳圓短髮
        cv.rect(hx0, hy0, hx1, hy0 + 2, hair)
        cv.rect(hx0, hy0, hx0 + 3, hy1 - 1, hair)
        cv.rect(hx0 - 1, hy0 + 1, hx0 - 1, hy1 - 1, hair_d)
        cv.rect(hx0 + 1, hy0 - 1, hx1 - 1, hy0 - 1, hair)
        cv.p(hx1, hy0 + 3, hair)
    if g != "n":
        cv.p(hx0 + 3, ey + 1, SKIN_D)  # 耳

    # --- 頭部配件
    if band == "kid":  # 七星潭漁夫帽（淺藍＋白浪紋）
        cv.rect(hx0, hy0 - 2, hx1, hy0 + 1, "#5cc3e8")
        cv.rect(hx0 - 2, hy0 + 1, hx1 + 2, hy0 + 1, "#2f8fbf")
        cv.p(hx0, hy0 - 2, CLEAR)
        cv.p(hx1, hy0 - 2, CLEAR)
        for x in range(hx0 + 1, hx1, 2):
            cv.p(x, hy0, "#ffffff")
    if band == "teen":  # 額頭上的護目鏡
        cv.rect(hx0, hy0 + 2, hx1, hy0 + 2, "#2a2a3a")
        cv.rect(hx1 - 3, hy0 + 1, hx1, hy0 + 3, "#2a2a3a")
        cv.rect(hx1 - 2, hy0 + 2, hx1 - 1, hy0 + 2, "#7fe6ff")
        cv.p(hx1 - 2, hy0 + 2, "#ffffff")
    if band == "elder":
        if g == "f":
            cv.rect(hx0 - 2, hy0 + 2, hx0, hy0 + 4, hair)  # 髮髻
            cv.p(hx0 - 2, hy0 + 4, hair_d)
        if g == "m":
            cv.rect(hx1 - 2, hy1, hx1, hy1 + 1, "#eeeeee")  # 白鬍
        cv.rect(hx0 - 2, hy0, hx1 + 2, hy0, "#e8c46a")  # 草帽
        cv.rect(hx0 - 2, hy0 + 1, hx1 + 2, hy0 + 1, "#b48d3a")
        cv.rect(hx0 + 1, hy0 - 3, hx1 - 1, hy0 - 1, "#e8c46a")
        cv.rect(hx0 + 1, hy0 - 1, hx1 - 1, hy0 - 1, "#c0392b")
        cv.p(hx0 + 2, hy0 - 3, "#f5dc8e")
        cv.p(hx0 + 4, hy0 - 2, "#c9a24c")
        cv.p(hx0, hy0, "#c9a24c")

    # --- 近側手臂＋手持物
    sy = torso_top + 1
    sx = cx + (2 if hunch else 0)
    alen = max(th - 1, 4)
    hand_dx = 2 if frame == 0 else -2
    if band == "elder":
        hand_dx = 4 if frame == 0 else 2
    hxh, hyh = sx + hand_dx, sy + alen - 1
    sleeve = shirt_d if band != "adult" else "#dde3ea"
    cv.line(sx, sy, hxh, hyh - 1, sleeve, w=2)
    cv.rect(hxh, hyh, hxh + 1, hyh + 1, SKIN)
    if band == "kid":  # 紅色滴管瓶
        bxk, byk = hxh - 1, hyh + 1
        cv.rect(bxk + 1, byk - 2, bxk + 2, byk - 1, "#e8eef2")
        cv.rect(bxk, byk, bxk + 3, byk + 4, "#e8eef2")
        cv.rect(bxk, byk + 2, bxk + 3, byk + 4, "#e0304a")
        cv.p(bxk, byk, "#ffffff")
    if band == "elder":  # 拐杖
        kx = hxh + 2
        cv.rect(kx, hyh, kx, 30, "#7a4a22")
        cv.p(kx - 1, hyh, "#7a4a22")
    cv.outline()
    return cv


# ---------------------------------------------------------------- 隊友 24x24
def eyes(cv, x, y, gap=4, big=True, look=1):
    for ex in (x, x + gap):
        if big:
            cv.rect(ex, y, ex + 1, y + 1, "#ffffff")
            cv.p(ex + look, y + 1, "#111122")
            cv.p(ex + look, y, "#111122")
        else:
            cv.p(ex, y, "#111122")
            cv.p(ex, y + 1, "#111122")


def smile(cv, x, y, c="#4a1a10"):
    cv.p(x, y, c); cv.p(x + 1, y + 1, c); cv.p(x + 2, y + 1, c); cv.p(x + 3, y, c)


def drop_shape(cv, cx, cy, rx, ry, top, dark, base, light):
    cv.ellipse(cx, cy, rx, ry, dark)
    cv.poly([(cx, top), (cx - rx * 0.75, cy - ry * 0.45), (cx + rx * 0.75, cy - ry * 0.45)], dark)
    cv.ellipse(cx - 0.6, cy - 0.6, rx - 1.4, ry - 1.4, base, clip=True)
    cv.poly([(cx, top + 2.5), (cx - rx * 0.45, cy - ry * 0.45), (cx + rx * 0.45, cy - ry * 0.45)], base, clip=True)
    cv.rect(cx - rx * 0.55, cy - ry * 0.5, cx - rx * 0.55, cy - ry * 0.1, light, clip=True)


def ion(cv, cx, cy, r, dark, base, light, label2=True):
    cv.sphere(cx, cy, r, dark, base, light)
    if label2:
        text(cv, "2", int(cx - 2), int(cy - 3), "#ffffff")
        text(cv, "+", int(cx + 1), int(cy - 4), "#ffffff")


def bead(cv, cx, cy, r, film="#7a1028", core="#ff4a6a", hi="#ffd0dc", opaque=False):
    cv.circle(cx, cy, r, film)
    cv.circle(cx - 0.3, cy - 0.3, r - (2.2 if opaque else 1.2), core, clip=True)
    if not opaque:
        cv.circle(cx + r * 0.25, cy + r * 0.25, r * 0.45, "#ff7a90", clip=True)
    cv.circle(cx - r * 0.38, cy - r * 0.38, max(r * 0.28, 1.0), hi, clip=True)


def mate(i, f):
    cv = C(24, 24)
    if i == 1:  # 海藻小藻：褐藻葉片
        sw = 1 if f else 0
        pts_l = [(12 + 3 * math.sin(y / 3.2 + sw), y) for y in range(2, 22)]
        for (x, y) in pts_l:
            w = 5.5 if 6 < y < 18 else 4
            cv.rect(x - w, y, x + w, y, "#6b4f12")
            cv.rect(x - w + 1, y, x + w - 2, y, "#9a7a24")
        for (x, y) in pts_l[::2]:
            cv.p(x, y, "#5a3f0a")  # 中肋
        cv.rect(10, 21, 14, 22, "#4a3a10")  # 固著器
        eyes(cv, 9, 9, gap=5)
        smile(cv, 11, 13)
        for (x, y) in ([(3, 4), (20, 15)] if f == 0 else [(4, 2), (21, 12)]):
            cv.circle(x, y, 1.3, "#9fd8ff")
    elif i == 2:  # 粉粉：海藻酸鈉粉末堆
        dy = -1 if f else 0
        cv.ellipse(12, 16 + dy, 9.5, 6, "#c8b48a")
        cv.ellipse(12, 15 + dy, 8.5, 5.5, "#f3e6c8", clip=True)
        cv.ellipse(12, 10 + dy, 5.5, 4.5, "#c8b48a")
        cv.ellipse(11.6, 9.6 + dy, 4.6, 3.8, "#fbf4e2", clip=True)
        for (x, y) in ((6, 17), (9, 19), (15, 18), (18, 16), (13, 14)):
            cv.p(x, y + dy, "#d8c8a0")
        eyes(cv, 9, 13 + dy, gap=5)
        smile(cv, 11, 17 + dy, "#8a6a3a")
        for (x, y) in ([(3, 4), (20, 3)] if f == 0 else [(4, 6), (19, 2), (21, 7)]):
            cv.p(x, y, "#ffffff"); cv.p(x + 1, y, "#fff4d0")
    elif i == 3:  # 暖暖水：溫熱水滴＋蒸氣
        drop_shape(cv, 12, 15, 7, 7, 5, "#c04a2a", "#ff9a6a", "#ffe0c8")
        eyes(cv, 9, 14, gap=5)
        smile(cv, 11, 18, "#7a2a10")
        o = 0 if f == 0 else 1
        for x0 in (6, 12, 18):
            for k in range(4):
                cv.p(x0 + (1 if (k + o) % 2 else 0), 4 - k + (1 if x0 == 12 else 0), "#e8e8f0")
    elif i == 4:  # 小鈣：Ca2+
        bob = -1 if f else 0
        ion(cv, 12, 13 + bob, 8, "#123f7a", "#3d8fd6", "#bfe3ff", label2=False)
        text(cv, "2", 17, 1, "#9fd8ff")
        text(cv, "+", 20, 1, "#9fd8ff")
        eyes(cv, 9, 11 + bob, gap=5)
        smile(cv, 11, 16 + bob, "#0b2a55")
        if f:
            cv.p(2, 6, "#bfe3ff"); cv.p(22, 18, "#bfe3ff")
    elif i == 5:  # 手銬 Ca：扣住兩條長鏈
        o = 0 if f == 0 else 1
        for y0 in (5, 19):
            for x in range(0, 24):
                y = y0 + (1 if (x // 3 + o) % 2 else 0)
                cv.p(x, y, "#8a6a1f")
                cv.p(x, y + 1, "#c8a04a")
        cv.rect(6, 7, 7, 18, "#d0d6dc"); cv.rect(16, 7, 17, 18, "#d0d6dc")  # 手銬鏈
        ion(cv, 12, 12.5, 6.5, "#123f7a", "#3d8fd6", "#bfe3ff", label2=False)
        eyes(cv, 9, 11, gap=5, big=False)
        smile(cv, 10, 14, "#0b2a55")
    elif i == 6:  # 滴滴：紅色海藻酸鈉液滴
        if f == 0:
            drop_shape(cv, 12, 14, 7.5, 7.5, 2, "#7a1028", "#e0304a", "#ffc0cc")
        else:
            drop_shape(cv, 12, 15, 8.5, 6.5, 4, "#7a1028", "#e0304a", "#ffc0cc")
        eyes(cv, 9, 13, gap=5)
        smile(cv, 11, 17, "#4a0010")
        cv.p(21, 3 if f == 0 else 5, "#ffc0cc")
    elif i == 7:  # 晶球寶：幻彩晶球
        r = 9.5 if f == 0 else 9
        bead(cv, 12, 12, r)
        for k, col in enumerate(("#ffd23a", "#7ef0b4", "#9fd8ff")):
            a = math.radians(200 + k * 30 + (f * 15))
            cv.p(12 + (r - 1.5) * math.cos(a), 12 + (r - 1.5) * math.sin(a), col)
        eyes(cv, 9, 11, gap=5)
        smile(cv, 11, 15, "#5a0018")
        for (x, y) in ([(2, 3), (21, 20)] if f == 0 else [(21, 3), (2, 20)]):
            for (a_, b_) in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                cv.p(x + a_, y + b_, "#fff2a0" if (a_ or b_) else "#ffffff")
    elif i == 8:  # 膜膜博士：細胞膜＋眼鏡
        cv.circle(12, 12, 10.5, "#1f6e42")
        cv.circle(12, 12, 9.2, "#5fd39a", clip=True)
        cv.circle(12, 12, 8, "#c8f5dc", clip=True)
        for k in range(16):  # 膜上的孔（半透）
            a = math.radians(k * 22.5 + f * 11)
            cv.p(12 + 9.6 * math.cos(a), 12 + 9.6 * math.sin(a), "#c8f5dc")
        cv.circle(15, 15, 2.6, "#7a9a3a", clip=True)  # 細胞核
        cv.rect(6, 9, 10, 12, "#1E293B"); cv.rect(7, 10, 9, 11, "#ffffff")
        cv.rect(13, 9, 17, 12, "#1E293B"); cv.rect(14, 10, 16, 11, "#ffffff")
        cv.line(10, 10, 13, 10, "#1E293B")
        cv.p(8, 11, "#111122"); cv.p(15, 11, "#111122")
        smile(cv, 9, 15, "#1f4a30")
    cv.outline()
    return cv


# ---------------------------------------------------------------- 收集物 16x16
def item(name, f):
    cv = C(16, 16)
    if name == "kelp":  # 褐藻
        sw = 0.9 if f else 0
        for y in range(1, 15):
            x = 8 + 2.2 * math.sin(y / 2.6 + sw)
            w = 2.5 if 3 < y < 12 else 1.5
            cv.rect(x - w, y, x + w, y, "#6b4f12")
            cv.p(x - w + 1, y, "#b8902a")
        cv.rect(6, 14, 10, 14, "#4a3a10")
        cv.p(12, 3 if f == 0 else 2, "#9fd8ff")
    elif name == "trash":
        dy = 0 if f == 0 else -1
        cv.rect(2, 6 + dy, 11, 11 + dy, "#bfe6f7")
        cv.rect(2, 10 + dy, 11, 11 + dy, "#8cc8e4")
        cv.rect(5, 6 + dy, 8, 11 + dy, "#e74c3c")
        cv.rect(12, 7 + dy, 12, 10 + dy, "#bfe6f7")
        cv.rect(13, 7 + dy, 14, 10 + dy, "#1e5bb8")
        cv.rect(3, 7 + dy, 4, 7 + dy, "#ffffff")
        if f:
            for (x, y) in ((2, 2), (1, 2), (3, 2), (2, 1), (2, 3)):
                cv.p(x, y, "#ffe04a")
        cv.rect(1, 13, 5, 13, "#d8c89a"); cv.rect(9, 13, 13, 13, "#d8c89a")
    elif name == "powder":  # 海藻酸鈉粉末（小匙）
        cv.ellipse(8, 10, 6.5, 4, "#b89a5a")
        cv.ellipse(8, 9.5, 5.5, 3.2, "#f3e6c8", clip=True)
        cv.rect(13, 9, 15, 10, "#9aa4b0")
        pts = [(5, 7), (8, 6), (10, 7), (7, 9), (11, 10)]
        for k, (x, y) in enumerate(pts):
            cv.p(x + (f if k % 2 else 0), y, "#fffaf0")
        if f:
            cv.p(3, 3, "#ffffff"); cv.p(12, 2, "#ffffff")
    elif name == "h2o":  # 水分子
        o = 0 if f == 0 else 1
        cv.sphere(8, 9, 4.6, "#0d4f8f", "#4fa3e0", "#d0ecff")
        cv.sphere(3.5, 4.5 + o, 2.6, "#8a9aa8", "#f4f8fb", "#ffffff", spec=None)
        cv.sphere(12.5, 4.5 + o, 2.6, "#8a9aa8", "#f4f8fb", "#ffffff", spec=None)
        cv.p(5, 6 + o, "#c0c8d0"); cv.p(11, 6 + o, "#c0c8d0")
    elif name == "ca":  # Ca2+
        ion(cv, 8, 8, 6.5 if f == 0 else 6, "#123f7a", "#3d8fd6", "#bfe3ff")
        if f:
            cv.p(1, 2, "#bfe3ff"); cv.p(14, 13, "#bfe3ff"); cv.p(14, 2, "#bfe3ff")
    elif name == "drop":  # 3 cm 正確液滴（紅）
        if f == 0:
            drop_shape(cv, 8, 10, 5, 5, 1, "#7a1028", "#e0304a", "#ffc0cc")
        else:
            drop_shape(cv, 8, 9, 5, 5, 0, "#7a1028", "#e0304a", "#ffc0cc")
        cv.p(13, 2 + f, "#ffe08a"); cv.p(14, 2 + f, "#ffe08a")
    elif name == "bead":  # 完成的晶球
        bead(cv, 8, 8.5, 6.5 if f == 0 else 6.9)
        if f:
            cv.p(14, 2, "#ffffff"); cv.p(13, 2, "#fff2a0")
    elif name == "hard":  # 二次熟化硬球（不透明、略小）
        bead(cv, 8, 9, 5.6, film="#4a0a1a", core="#b8405a", hi="#e8a0b0", opaque=True)
        cv.p(13, 3 + f, "#ffd23a"); cv.p(14, 3 + f, "#ffd23a"); cv.p(13, 2 + f, "#fff2a0")
    elif name in ("cell", "ink", "filter", "pack"):  # 應用卡（白卡＋圖示）
        dy = 0 if f == 0 else -1
        frame = {"cell": "#2e7d5b", "ink": "#d0601a", "filter": "#1c7293", "pack": "#b8902a"}[name]
        cv.rect(2, 1 + dy, 13, 14 + dy, frame)
        cv.rect(3, 2 + dy, 12, 13 + dy, "#fbfdfc")
        if name == "cell":
            cv.circle(7.5, 7.5 + dy, 4.2, "#2e7d5b")
            cv.circle(7.5, 7.5 + dy, 3.2, "#c8f5dc", clip=True)
            cv.p(8, 8 + dy, "#5a8a2a"); cv.p(9, 8 + dy, "#5a8a2a")
        elif name == "ink":
            cv.rect(6, 3 + dy, 9, 8 + dy, "#9aa4b0")
            cv.rect(7, 9 + dy, 8, 10 + dy, "#5a6470")
            cv.rect(5, 11 + dy, 10, 12 + dy, "#ff9f43")
            cv.rect(6, 10 + dy, 9, 10 + dy, "#ff9f43")
        elif name == "filter":
            drop_shape(cv, 7.5, 8 + dy, 3.6, 3.6, 3 + dy, "#0d3f8f", "#4fb0e0", "#d8f4ff")
            for (x, y) in ((5, 11), (8, 11), (10, 10)):
                cv.p(x, y + dy, "#ff6a8a")
        else:
            cv.ellipse(7.5, 8 + dy, 4.5, 3, "#b8902a")
            cv.ellipse(7.5, 7.6 + dy, 3.6, 2.2, "#ffe48a", clip=True)
            cv.p(5, 7 + dy, "#ffffff")
        if f:
            cv.p(14, 0, "#ffffff")
    cv.outline()
    return cv


# ---------------------------------------------------------------- 危險物
def warn_mark(cv, x, y):
    cv.rect(x, y, x, y + 2, "#ff2a2a"); cv.p(x, y + 4, "#ff2a2a")


def hazard(name, f):
    big = name == "wave"
    cv = C(24, 24) if big else C(16, 16)
    if name == "wave":
        o = 0 if f == 0 else 1
        cv.poly([(1, 21), (2, 12), (6, 6), (12, 3), (18, 4), (22, 8), (21, 12), (17, 10), (13, 11), (11, 15), (12, 21)], "#1d6fd0")
        cv.poly([(2, 21), (3, 14), (7, 9), (11, 8), (9, 13), (9, 21)], "#0d3f8f")
        cv.line(6, 6, 12, 3, "#ffffff", w=2)
        cv.line(12, 3, 18, 4, "#ffffff", w=2)
        cv.line(18, 4, 21, 8, "#ffffff", w=2)
        cv.p(20, 11 - o, "#ffffff"); cv.p(18, 10, "#cfeaff")
        cv.rect(1, 20, 22, 22, "#5fb0f0")
        for x in range(1 + o, 23, 3):
            cv.p(x, 20, "#ffffff")
        for (x, y) in ([(22, 2), (20, 1), (15, 1)] if f == 0 else [(22, 4), (21, 1), (16, 0)]):
            cv.p(x, y, "#ffffff")
    elif name == "fisheye":  # 魚眼結塊：外層膠、內藏乾粉
        w = 0 if f == 0 else 1
        cv.circle(8, 8.5, 6.8 + w * 0.4, "#a08a5a")
        cv.circle(8, 8.5, 5.8, "#d8c8a0", clip=True)
        cv.circle(8, 8.5, 3.2, "#fffaf0", clip=True)  # 乾粉核
        cv.circle(8.5 + w, 9, 1.4, "#3a2a10")  # 像魚眼
        cv.p(7, 7, "#ffffff")
        cv.line(3, 12, 5, 13, "#7a6a40"); cv.line(11, 13, 13, 12, "#7a6a40")
    elif name == "bubble":  # 氣泡
        r = 6.5 if f == 0 else 7
        cv.circle(8, 8, r, "#6ab0d8")
        cv.circle(8, 8, r - 1.2, "#e8f6ff", clip=True)
        cv.circle(8, 8, r - 2.4, "#cfe9f7", clip=True)
        cv.circle(5.5, 5.5, 1.6, "#ffffff", clip=True)
        cv.p(13, 2, "#cfefff"); cv.p(2, 13, "#cfefff")
    elif name == "mg":  # Mg2+（不會交聯）
        cv.sphere(8, 9, 6.4, "#0f6a5a", "#2ed3bc", "#b0fff0")
        cv.line(5, 12, 7, 11, "#0a3a30"); cv.line(9, 11, 11, 12, "#0a3a30")  # 皺眉嘴
        cv.p(6, 8, "#0a3a30"); cv.p(10, 8, "#0a3a30")
        text(cv, "2", 11, 0, "#2ed3bc")
        warn_mark(cv, 1, 1 + f)
    elif name == "vapor":  # 潮解水氣雲
        o = 0 if f == 0 else 1
        for (x, y, r) in ((5, 7, 3.5), (9, 6, 4), (12, 8, 3), (8, 9, 3.5)):
            cv.circle(x + o * (1 if x > 8 else 0), y, r, "#8a9aa8")
        for (x, y, r) in ((5, 6.5, 2.4), (9, 5.5, 3), (12, 7.5, 2)):
            cv.circle(x + o * (1 if x > 8 else 0), y, r, "#d8e2ea", clip=True)
        for (x, y) in ((5, 12 + o), (9, 13 - o), (12, 12 + o)):
            cv.p(x, y, "#4f9fe0"); cv.p(x, y + 1, "#2a6ab0")
    elif name == "na":  # Na+（會被換走）
        cv.sphere(8, 8.5, 6.4, "#4a1a7a", "#9a4ad8", "#e0b0ff")
        text(cv, "+", 6, 6, "#ffffff")
        if f:
            cv.line(1, 4, 3, 4, "#e0b0ff"); cv.line(0, 7, 2, 7, "#e0b0ff")
        else:
            cv.line(13, 4, 15, 4, "#e0b0ff"); cv.line(14, 7, 15, 7, "#e0b0ff")
    elif name == "high":  # 太高的落點
        cv.rect(7, 1, 8, 9, "#c99a3e")
        cv.poly([(7.5, 0), (3.5, 4), (11.5, 4)], "#c99a3e")
        cv.rect(3, 12, 12, 13, "#e0304a")  # 摔扁
        cv.rect(2, 13, 13, 13, "#7a1028")
        cv.p(1 + f, 11, "#ff8a9a"); cv.p(14 - f, 11, "#ff8a9a")
        warn_mark(cv, 12, 1)
    elif name == "tail":  # 太低拖尾
        o = 0 if f == 0 else 1
        cv.circle(5, 10, 3.6, "#7a1028")
        cv.circle(4.8, 9.8, 2.6, "#e0304a", clip=True)
        for x in range(7, 15):
            y = 10 - (x - 7) * 0.6 + (o if x % 2 else 0)
            cv.p(x, y, "#b0304a"); cv.p(x, y + 1, "#7a1028")
        warn_mark(cv, 13, 9)
    elif name == "flat":  # 太高摔扁
        w = 0 if f == 0 else 1
        cv.ellipse(8, 10, 7 + w * 0.5, 2.6 - w * 0.4, "#7a1028")
        cv.ellipse(8, 9.6, 6 + w * 0.5, 1.6, "#e05a6a", clip=True)
        for (x, y) in ((1, 6), (14, 5), (4, 4), (12, 3)):
            cv.p(x, y + w, "#ff8a9a")
        warn_mark(cv, 7, 1)
    elif name == "burst":  # 一撈就破的薄皮球
        cv.circle(8, 9, 5.5, "#c84a6a")
        cv.circle(8, 9, 4.5, "#ffb0c0", clip=True)
        cv.line(5, 6, 8, 9, "#5a0018"); cv.line(8, 9, 7, 12, "#5a0018"); cv.line(8, 9, 11, 8, "#5a0018")
        for (x, y) in (((1, 14), (14, 13), (2, 3)) if f == 0 else ((0, 12), (15, 14), (13, 2))):
            cv.p(x, y, "#e0304a")
    elif name == "bottle":  # 一次性塑膠瓶
        dy = 0 if f == 0 else -1
        cv.rect(6, 1 + dy, 9, 2 + dy, "#1e5bb8")
        cv.rect(5, 3 + dy, 10, 4 + dy, "#cfefff")
        cv.rect(4, 5 + dy, 11, 14 + dy, "#bfe6f7")
        cv.rect(4, 8 + dy, 11, 10 + dy, "#5ab8e0")
        cv.p(5, 6 + dy, "#ffffff")
        cv.line(3, 4, 12, 15, "#e02020"); cv.line(12, 4, 3, 15, "#e02020")
    cv.outline()
    return cv


# ---------------------------------------------------------------- 地磚 32x32
def tiles(s):
    rng = np.random.default_rng(1000 + s)
    out = {}

    def base(col):
        cv = C(32, 32)
        cv.rect(0, 0, 31, 31, col)
        return cv

    def noise(cv, cols, n):
        for _ in range(n):
            x, y = rng.integers(0, 32, 2)
            cv.p(x, y, cols[rng.integers(0, len(cols))])

    def wall(dark, mid, light):
        cv = base(dark)
        cv.rect(0, 0, 31, 3, light)
        cv.rect(0, 4, 31, 5, mid)
        for x in range(0, 32, 8):
            cv.rect(x, 6, x + 1, 31, mid)
        noise(cv, [mid], 30)
        return cv

    if s == 1:  # 七星潭礫石灘＋海浪線
        for key in ("a", "b"):
            cv = base("#cfc8bb")
            noise(cv, ["#bdb5a6", "#e0dbd0"], 80)
            for _ in range(14 if key == "a" else 8):
                x, y = rng.integers(3, 29, 2)
                r = rng.uniform(1.4, 2.6)
                col = ["#f2efe8", "#9a9488", "#7d8a86", "#8a6a1f", "#b8b0a2"][rng.integers(0, 5)]
                cv.ellipse(x, y, r * 1.3, r, "#8a8476")
                cv.ellipse(x - 0.3, y - 0.3, r * 1.3 - 0.6, r - 0.6, col)
                cv.p(x - r * 0.5, y - r * 0.5, "#ffffff")
            if key == "b":
                for x in range(32):
                    y = int(18 + 2 * math.sin(x / 32 * 2 * math.pi))
                    cv.rect(x, y, x, 31, "#3f8fc8")
                    cv.p(x, y, "#ffffff"); cv.p(x, y + 1, "#bfe6ff")
                    if x % 5 == 0:
                        cv.p(x, y + 6, "#7ab8e0")
            out[key] = cv
        cv = base("#4a4f55")  # 岩壁＋褐藻
        for _ in range(7):
            x, y = rng.integers(0, 32, 2)
            cv.poly([(x, y), (x + 9, y + 2), (x + 6, y + 8), (x - 2, y + 6)], "#5f666e")
        noise(cv, ["#3a3e44", "#6a727a"], 60)
        cv.rect(0, 0, 31, 2, "#8a6a1f"); cv.rect(0, 2, 31, 3, "#6b4f12")
        for x in range(0, 32, 3):
            cv.p(x, 4, "#8a6a1f")
        out["c"] = cv
    elif s == 2:  # 粉末工坊：淺木桌
        for key in ("a", "b"):
            cv = base("#8a6440")
            for y in range(0, 32, 8):
                cv.rect(0, y, 31, y, "#6e4e30")
                for x in range(0, 32, 5):
                    cv.p((x + y) % 32, y + 3, "#9a7450")
            if key == "b":  # 撒落粉末
                for _ in range(16):
                    x, y = rng.integers(4, 28, 2)
                    cv.p(x, y, "#fffaf0"); cv.p(x + 1, y, "#f3e6c8")
            out[key] = cv
        out["c"] = wall("#3a2a1a", "#5a4228", "#b8a47a")
    elif s == 3:  # 紅液燒杯
        for key in ("a", "b"):
            cv = base("#7a1f2e")
            for y in range(2, 32, 7):
                for x in range(32):
                    if (x + y) % 9 < 3:
                        cv.p(x, y + int(math.sin(x / 4) * 1.5), "#9a2f40")
            if key == "b":
                for _ in range(5):
                    x, y = rng.integers(4, 28, 2)
                    cv.circle(x, y, 1.6, "#c84a5a"); cv.p(x - 1, y - 1, "#ffd0d8")
            out[key] = cv
        out["c"] = wall("#2a0b12", "#4a1a24", "#d8e8f0")
    elif s == 4:  # 藍色鈣液
        for key in ("a", "b"):
            cv = base("#b8e0f2")
            for y in range(1, 32, 6):
                for x in range(32):
                    if (x * 3 + y) % 11 < 4:
                        cv.p(x, y + int(math.sin(x / 5 + y) * 1.2), "#a0d2ea")
            if key == "b":
                for _ in range(6):
                    x, y = rng.integers(4, 28, 2)
                    cv.circle(x, y, 1.5, "#e8f8ff"); cv.p(x, y, "#ffffff")
            out[key] = cv
        out["c"] = wall("#0d3b5c", "#16507a", "#d8e8f0")
    elif s == 5:  # 滴球工坊：深靛＋蛋盒格
        for key in ("a", "b"):
            cv = base("#2a2f5a")
            for y in range(32):
                for x in range(32):
                    if x % 16 == 0 or y % 16 == 0:
                        cv.p(x, y, "#3a4078")
            if key == "b":  # 蛋盒凹槽
                for (x, y) in ((8, 8), (24, 24)):
                    cv.ellipse(x, y, 5, 3.5, "#1a1e3e")
                    cv.ellipse(x, y - 0.6, 4, 2.4, "#454c8a", clip=True)
            out[key] = cv
        out["c"] = wall("#141830", "#22284a", "#c99a3e")
    elif s == 6:  # 實驗桌白磚＋高度尺
        for key in ("a", "b"):
            cv = base("#f2f5f3")
            for y in range(32):
                for x in range(32):
                    if x % 16 == 0 or y % 16 == 0:
                        cv.p(x, y, "#c8d4cf")
            if key == "b":
                cv.rect(14, 2, 17, 29, "#e8d8a8")
                for y in range(3, 29, 3):
                    cv.rect(14, y, 15 if y % 9 else 16, y, "#7a5a20")
            out[key] = cv
        out["c"] = wall("#2E7D5B", "#3f9a6e", "#c8f5dc")
    elif s == 7:  # 清水洗盆
        for key in ("a", "b"):
            cv = base("#1d5f7a")
            for y in range(3, 32, 8):
                for x in range(32):
                    cv.p(x, y + int(math.sin(x / 3 + y) * 1.4), "#2f7f9c")
            if key == "b":
                for _ in range(3):
                    x, y = rng.integers(6, 26, 2)
                    bead(cv, x, y, 2.6)
            out[key] = cv
        out["c"] = wall("#0b2f3d", "#164a5c", "#d8f0f8")
    elif s == 8:  # 仿生應用館：深紫地板＋金線
        for key in ("a", "b"):
            cv = base("#3b2a5c")
            for y in range(32):
                for x in range(32):
                    if (x + y) % 16 == 0:
                        cv.p(x, y, "#4a3672")
            if key == "b":
                cv.rect(4, 4, 27, 27, "#45326b")
                cv.rect(4, 4, 27, 4, "#c99a3e"); cv.rect(4, 27, 27, 27, "#c99a3e")
                cv.rect(4, 4, 4, 27, "#c99a3e"); cv.rect(27, 4, 27, 27, "#c99a3e")
            out[key] = cv
        out["c"] = wall("#1d1430", "#2e2048", "#c99a3e")
    return out


# ---------------------------------------------------------------- UI
def star(on):
    cv = C(16, 16)
    pts = []
    for k in range(10):
        r = 7.4 if k % 2 == 0 else 3.2
        a = math.radians(-90 + 36 * k)
        pts.append((7.5 + r * math.cos(a), 8.3 + r * math.sin(a)))
    cv.poly(pts, "#c9900e" if on else "#3a4250")
    inner = [(7.5 + (x - 7.5) * 0.65, 8.3 + (y - 8.3) * 0.65 - 0.3) for (x, y) in pts]
    cv.poly(inner, "#ffd23a" if on else "#6a7484")
    if on:
        cv.p(6, 6, "#fff6c0"); cv.p(6, 7, "#fff6c0")
    cv.outline()
    return cv


def heart():
    cv = C(16, 16)
    cv.circle(5, 6, 3.6, "#c81e3a"); cv.circle(11, 6, 3.6, "#c81e3a")
    cv.poly([(1.6, 7), (14.4, 7), (8, 14)], "#c81e3a")
    cv.circle(5, 5.6, 2.4, "#ff4a62", clip=True); cv.circle(10.5, 5.6, 2.2, "#ff4a62", clip=True)
    cv.p(4, 4, "#ffd0d8"); cv.p(4, 5, "#ffd0d8")
    cv.outline()
    return cv


def lattice(full):
    """蛋盒空穴：兩條鏈（上下褐線）之間的蛋盒凹槽；full＝Ca2+ 已嵌入。"""
    cv = C(16, 16)
    cv.rect(0, 2, 15, 3, "#8a6a1f"); cv.rect(0, 12, 15, 13, "#8a6a1f")
    for x in range(0, 16, 3):
        cv.p(x, 4, "#c8a04a"); cv.p(x + 1, 11, "#c8a04a")
    cv.ellipse(7.5, 8, 5.5, 3.6, "#f3e6c8")
    cv.ellipse(7.5, 8.4, 4.4, 2.6, "#f3e6c8" if full else "#8a7a5a", clip=True)
    if full:
        cv.sphere(7.5, 7.5, 3.4, "#123f7a", "#3d8fd6", "#bfe3ff")
    cv.outline()
    return cv


def harmony_icon():
    cv = C(32, 32)
    cv.circle(16, 16, 14.5, "#c99a3e")
    cv.circle(16, 16, 13, "#0b1f3a")
    cv.circle(16, 16, 11.5, "#1c7293")
    cv.circle(16, 16, 10.5, "#0b1f3a")
    cv.line(16, 10, 11, 19, "#9fd8ff"); cv.line(16, 10, 21, 19, "#9fd8ff"); cv.line(11, 19, 21, 19, "#9fd8ff")
    for k in range(3):
        a = math.radians(-90 + 120 * k)
        x, y = 16 + 6 * math.cos(a), 16 + 6 * math.sin(a)
        cv.circle(x, y, 3.6, ["#e0304a", "#3d8fd6", "#ffd23a"][k])
        cv.p(x - 1, y - 1, "#ffffff")
    for k in range(8):
        a = math.radians(22.5 + 45 * k)
        cv.p(16 + 14.8 * math.cos(a), 16 + 14.8 * math.sin(a), "#fff2a0")
    cv.outline()
    return cv


def wheel():
    S = 160
    cv = C(S, S)
    yy, xx = np.mgrid[0:S, 0:S]
    px, py = xx + 0.5 - 80, yy + 0.5 - 80
    d = np.hypot(px, py)
    ang = np.degrees(np.arctan2(py, px))
    A = cv.a

    def put(mask, col):
        A[mask] = H(col)

    put(d <= 78, "#0b1f3a")
    put((d <= 76) & (d > 60), "#065a82")
    put((d <= 76) & (d > 72), "#1c7293")
    put((d <= 63) & (d > 60), "#04405e")
    grip = ((np.floor((ang + 180) / 10) % 2) == 0) & (d <= 70) & (d > 66)
    put(grip, "#0b4a6e")
    A[d <= 59] = 0
    for sa in (90, 210, 330):  # 三根輪輻
        rad = math.radians(sa)
        ux, uy = math.cos(rad), math.sin(rad)
        t = px * ux + py * uy
        perp = np.abs(-px * uy + py * ux)
        m = (t > 0) & (t < 61) & (perp < 7)
        put(m, "#065a82")
        put(m & (perp < 3), "#1c7293")
    put(d <= 20, "#0b1f3a")
    put(d <= 17, "#065a82")
    put(d <= 11, "#c99a3e")
    put(d <= 8, "#e8c46a")
    put(np.hypot(px + 0.5, py + 0.5) <= 5.5, "#7a1028")  # 紅色晶球徽
    put(np.hypot(px + 0.8, py + 0.8) <= 4.2, "#e0304a")
    put(np.hypot(px + 2.2, py + 2.2) <= 1.4, "#ffd0dc")
    hl = (d <= 75) & (d > 73) & (ang > -160) & (ang < -110)
    put(hl, "#7fd0ff")
    # 金色指針標記（正上方）
    cv.poly([(80, 2), (70, 20), (90, 20)], "#c99a3e")
    cv.poly([(80, 7), (74.5, 18), (85.5, 18)], "#ffd23a")
    cv.rect(77, 20, 82, 24, "#c99a3e")
    cv.p(79, 11, "#fff6c0"); cv.p(79, 12, "#fff6c0")
    cv.outline()
    return cv


# ---------------------------------------------------------------- 標題圖 320x180
F5.update({
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "V": ["10001", "10001", "10001", "10001", "01010", "01010", "00100"],
})


def title():
    W, Hh = 320, 180
    cv = C(W, Hh)
    rng = np.random.default_rng(42)
    bg = ["#1a0b2e", "#24103e", "#2e1650", "#2a2060", "#1f3070"]
    for y in range(Hh):
        cv.rect(0, y, W - 1, y, bg[min(int(y / Hh * len(bg)), len(bg) - 1)])
    for _ in range(50):
        cv.p(rng.integers(0, W), rng.integers(0, 70), "#dfe8ff")
    # 藍色鈣液燒杯
    bx0, bx1, by0, by1 = 96, 224, 96, 172
    cv.rect(bx0 - 3, by0 - 4, bx1 + 3, by1 + 2, "#cfe8f4")
    cv.rect(bx0, by0 - 4, bx1, by1 - 1, "#24103e")
    cv.rect(bx0, by0 + 10, bx1, by1 - 1, "#1f6fa3")
    for y in range(by0 + 12, by1, 6):
        for x in range(bx0, bx1 + 1):
            if (x + y) % 11 < 3:
                cv.p(x, y, "#2f88c0")
    cv.rect(bx0, by0 + 10, bx1, by0 + 11, "#7fc8f0")
    for y in range(by0 + 20, by1 - 4, 12):
        cv.rect(bx1 - 10, y, bx1 - 2, y, "#9fd8ff")  # 刻度
    # 杯底幻彩晶球
    cols = [("#7a1028", "#e0304a", "#ffd0dc"), ("#8a5a10", "#ffb030", "#fff2c0"), ("#1f6e42", "#5fd39a", "#e0fff0"),
            ("#5a1a7a", "#b86ae0", "#f0d8ff"), ("#7a1028", "#ff6a8a", "#ffe0e8")]
    for _ in range(26):
        x = bx0 + 8 + int(rng.integers(0, bx1 - bx0 - 16))
        y = by1 - 6 - int(rng.integers(0, 22))
        film, core, hi = cols[int(rng.integers(0, len(cols)))]
        bead(cv, x, y, float(rng.uniform(3.4, 5.2)), film=film, core=core, hi=hi)
    # 滴管與落下的紅色液滴
    cv.rect(156, 68, 164, 82, "#e8eef2"); cv.rect(158, 82, 162, 87, "#e8eef2"); cv.p(160, 88, "#e8eef2")
    cv.rect(154, 61, 166, 68, "#e0304a"); cv.rect(156, 60, 164, 61, "#b0203a")
    cv.rect(158, 72, 162, 81, "#e0304a")
    for (y, rr) in ((94, 3.0), (101, 3.4)):
        cv.circle(160, y, rr, "#7a1028"); cv.circle(159.6, y - 0.4, rr - 1, "#e0304a", clip=True); cv.p(159, y - 1, "#ffd0dc")
    for k in range(10):  # 漣漪
        cv.p(146 + k * 3, by0 + 9 + (k % 2), "#bfe6ff")

    # 左右主角剪影＋海藻小藻
    def sil(spr, x, y, col="#0e0618"):
        al = spr.a[:, :, 3] > 0
        for yy in range(spr.h):
            for xx in range(spr.w):
                if al[yy, xx]:
                    cv.rect(x + xx * 2, y + yy * 2, x + xx * 2 + 1, y + yy * 2 + 1, col)
    sil(draw_hero("kid", "f", 0), -2, 112)
    sil(draw_hero("adult", "m", 1), 250, 110)
    kelp = mate(1, 0).a
    for yy in range(24):
        for xx in range(24):
            if kelp[yy, xx, 3]:
                cv.rect(44 + xx * 2, 124 + yy * 2, 45 + xx * 2, 125 + yy * 2, tuple(int(v) for v in kelp[yy, xx]))
    # 標題字
    for s_, y0, sc, col in (("CAVIAR BEAD", 6, 3, "#ff8aa0"), ("SQUAD", 32, 2, "#ffd23a"), ("HUALIEN", 50, 1, "#bfe6ff")):
        w = text_w(s_, F5, 1, sc)
        x0 = (W - w) // 2
        text(cv, s_, x0 + 1, y0 + 1, "#04101e", F5, 1, sc)
        text(cv, s_, x0, y0, col, F5, 1, sc)
    return cv


# ---------------------------------------------------------------- 打包
HERO_IDS = [f"{b}_{g}" for b in ("kid", "teen", "adult", "elder") for g in ("f", "m", "n")]
MATES = list(range(1, 9))
ITEMS = ["kelp", "trash", "powder", "h2o", "ca", "drop", "bead", "hard", "cell", "ink", "filter", "pack"]
HAZS = ["wave", "fisheye", "bubble", "mg", "vapor", "na", "high", "tail", "flat", "burst", "bottle"]
UIS = ["ui_wheel", "ui_star_on", "ui_star_off", "ui_heart", "ui_lattice_empty", "ui_lattice_full", "ui_harmony"]


def build_all():
    spr = {}
    for hid in HERO_IDS:
        b, g = hid.split("_")
        for f in (0, 1):
            spr[f"hero_{hid}_{f}"] = draw_hero(b, g, f)
    for i in MATES:
        for f in (0, 1):
            spr[f"mate_{i}_{f}"] = mate(i, f)
    for n in ITEMS:
        for f in (0, 1):
            spr[f"item_{n}_{f}"] = item(n, f)
    for n in HAZS:
        for f in (0, 1):
            spr[f"haz_{n}_{f}"] = hazard(n, f)
    for s in range(1, 9):
        for k, v in tiles(s).items():
            spr[f"tile_s{s}_{k}"] = v
    spr["ui_wheel"] = wheel()
    spr["ui_star_on"] = star(True)
    spr["ui_star_off"] = star(False)
    spr["ui_heart"] = heart()
    spr["ui_lattice_empty"] = lattice(False)
    spr["ui_lattice_full"] = lattice(True)
    spr["ui_harmony"] = harmony_icon()
    return spr


def pack(spr, width=512, pad=2):
    order = sorted(spr.keys(), key=lambda k: (-spr[k].h, k))
    x = y = row_h = 0
    pos = {}
    for k in order:
        w, h = spr[k].w, spr[k].h
        if x + w > width:
            x, y, row_h = 0, y + row_h + pad, 0
        pos[k] = (x, y, w, h)
        x += w + pad
        row_h = max(row_h, h)
    total_h = (y + row_h + 15) // 16 * 16
    sheet = Image.new("RGBA", (width, total_h), (0, 0, 0, 0))
    for k, (x, y, w, h) in pos.items():
        sheet.paste(spr[k].img(), (x, y))
    return sheet, pos


def main():
    os.makedirs(ASSETS, exist_ok=True)
    spr = build_all()
    sheet, pos = pack(spr)
    sheet.save(os.path.join(ASSETS, "sprites.png"))
    frames = {k: {"x": x, "y": y, "w": w, "h": h} for k, (x, y, w, h) in sorted(pos.items())}
    with open(os.path.join(ASSETS, "sprites.json"), "w", encoding="utf-8") as fp:
        json.dump({"scale": 1, "frames": frames}, fp, ensure_ascii=False, indent=1)
    t = title().img()
    t.save(os.path.join(ASSETS, "title.png"))
    t.resize((t.width * 4, t.height * 4), Image.NEAREST).save(os.path.join(ASSETS, "title_4x.png"))
    print(f"圖集 {sheet.width}x{sheet.height}，frame 共 {len(frames)} 個；標題圖 320x180 與 1280x720 已輸出。")


if __name__ == "__main__":
    main()
