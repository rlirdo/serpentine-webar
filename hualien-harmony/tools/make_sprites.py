# -*- coding: utf-8 -*-
"""墨玉護衛隊：花蓮綠晶行動 — 像素圖集產生器（規格 §9）。

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
        cv.rect(bx0 - 3, torso_top - 1, bx0 - 1, torso_top + 1, "#2f6b4a")  # 袋口露出墨綠石
        cv.p(bx0 - 2, torso_top - 1, "#5fa98a")
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
    if band == "kid":  # 小水桶
        bxk, byk = hxh - 1, hyh + 2
        cv.p(bxk, byk - 1, "#7a6a50")
        cv.p(bxk + 3, byk - 1, "#7a6a50")
        cv.rect(bxk, byk, bxk + 3, byk + 3, "#f4c430")
        cv.rect(bxk, byk + 3, bxk + 3, byk + 3, "#c9971a")
        cv.rect(bxk, byk, bxk + 3, byk, "#ffe680")
        cv.p(bxk + 1, byk + 1, "#2f6b4a")
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


def mate(i, f):
    cv = C(24, 24)
    if i == 1:  # 墨玉小晶：六角綠晶
        dy = -1 if f else 0
        cx, cy, r = 12, 12 + dy, 9.5
        pts = [(cx + r * math.cos(math.radians(-90 + 60 * k)), cy + r * math.sin(math.radians(-90 + 60 * k))) for k in range(6)]
        shades = ["#5fd39a", "#2e8b57", "#1f5e3e", "#174a30", "#2e8b57", "#7fe6b0"]
        for k in range(6):
            cv.poly([(cx, cy), pts[k], pts[(k + 1) % 6]], shades[k])
        cv.poly([(cx + (p[0] - cx) * 0.55, cy + (p[1] - cy) * 0.55) for p in pts], "#3aa86c")
        eyes(cv, 9, 11 + dy, gap=4)
        cv.p(11, 15 + dy, "#174a30"); cv.p(12, 15 + dy, "#174a30")
        cv.p(7, 6 + dy, "#d8ffe8")
        if f:
            for (x, y) in ((20, 3), (19, 3), (21, 3), (20, 2), (20, 4)):
                cv.p(x, y, "#e8fff0")
        else:
            cv.p(3, 19, "#c8ffe0")
    elif i == 2:  # 球球：白色氧化鋯磨球
        if f == 0:
            cv.sphere(12, 12, 9.5, "#8a909c", "#e9ecf0", "#ffffff")
            cv.line(4, 15, 20, 9, "#bcc2cc", clip=True)
        else:
            cv.ellipse(12, 13, 10.5, 8.5, "#8a909c")
            cv.ellipse(11, 12, 9, 7, "#e9ecf0", clip=True)
            cv.circle(8, 10, 2.5, "#ffffff", clip=True)
            cv.line(5, 8, 19, 18, "#bcc2cc", clip=True)
        eyes(cv, 10, 11, gap=4)
        cv.p(12, 15, "#555a66"); cv.p(13, 15, "#555a66")
    elif i == 3:  # 泳圈 T（微胞）
        cv.circle(12, 12, 10, "#c85a10")
        cv.circle(11.5, 11.5, 9, "#ff8a2a", clip=True)
        for deg in ((15, 90, 165) if f == 0 else (-10, 50, 130, 190)):  # 白條紋只在下半圈，轉動時位移
            ang = math.radians(deg)
            cv.circle(12 + 7 * math.cos(ang), 12 + 7 * math.sin(ang), 2.4, "#ffffff", clip=True)
        cv.circle(12, 12, 5, "#c85a10")
        cv.erase_ellipse(12, 12, 3.6, 3.6)
        cv.rect(7, 3, 16, 7, "#ff8a2a", clip=True)
        cv.circle(12, 12, 5, "#c85a10")
        cv.erase_ellipse(12, 12, 3.6, 3.6)
        eyes(cv, 8, 4, gap=6, big=True)
        cv.rect(11, 5, 12, 5, "#7a2a00")
        cv.p(7, 6, "#ffb0a0"); cv.p(16, 6, "#ffb0a0")
    elif i == 4:  # 阿鐵 Fe3+
        bob = -1 if f else 0
        cv.sphere(11, 13 + bob, 7, "#a87a10", "#f2c230", "#fff2a0")
        eyes(cv, 9, 12 + bob, gap=4, big=False)
        cv.p(11, 16 + bob, "#7a5200"); cv.p(12, 16 + bob, "#7a5200")
        text(cv, "3", 16, 1, "#ffd84a")
        text(cv, "+", 20, 1, "#ffd84a")
        spark = [(3, 4), (21, 15), (4, 20)] if f == 0 else [(6, 2), (20, 20), (2, 12)]
        for (x, y) in spark:
            for (a, b) in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                cv.p(x + a, y + b, "#ffd84a" if (a or b) else "#fff8c0")
    elif i == 5:  # 深海水滴
        rx, ry, cy, top = (7.5, 7.5, 15, 2) if f == 0 else (8.8, 6.5, 16, 4)
        cv.ellipse(12, cy, rx, ry, "#0d3f8f")
        cv.poly([(12, top), (12 - rx * 0.75, cy - 3), (12 + rx * 0.75, cy - 3)], "#0d3f8f")
        cv.ellipse(11.3, cy - 0.8, rx - 1.6, ry - 1.6, "#1d6fd0", clip=True)
        cv.poly([(12, top + 3), (12 - rx * 0.5, cy - 3), (12 + rx * 0.5, cy - 3)], "#1d6fd0", clip=True)
        cv.rect(7, cy - 4, 7, cy - 1, "#8fd0ff", clip=True)
        cv.p(8, cy - 5, "#8fd0ff")
        eyes(cv, 10, cy - 1, gap=4)
        cv.p(12, cy + 3, "#0a2a60"); cv.p(13, cy + 3, "#0a2a60")
        cv.p(20, 4 if f == 0 else 7, "#8fd0ff")
        cv.p(3, 8 if f == 0 else 5, "#8fd0ff")
    elif i == 6:  # 旋風（離心）
        rows = [(2, 9.5), (5, 8.5), (8, 7), (11, 5.5), (14, 4.2), (17, 3), (20, 2)]
        sh = [0, 1, 0, -1, 0, 1, 0] if f == 0 else [0, -1, 0, 1, 0, -1, 0]
        for k, (y, hw) in enumerate(rows):
            cx = 12 + sh[k]
            cv.ellipse(cx, y + 1.5, hw, 2, "#5f9ab3")
            cv.ellipse(cx - 0.5, y + 1, hw - 1, 1.2, "#d6f1fa")
        for k in range(4):
            y = 3 + k * 4 + f * 2
            cv.line(13 - rows[k][1] + 2, y + 1, 12 + rows[k][1] - 2, y, "#3f7a93")
        eyes(cv, 9, 7, gap=4, big=True)
        cv.p(11, 10, "#2a5a70"); cv.p(12, 10, "#2a5a70")
        for (x, y) in ([(2, 14), (21, 6)] if f == 0 else [(21, 14), (2, 7)]):
            cv.p(x, y, "#5fa98a"); cv.p(x + 1, y, "#2f6b4a")
    elif i == 7:  # 暖暖（烘箱精靈）
        cv.rect(3, 5, 20, 19, "#e8712a")
        cv.rect(3, 5, 20, 6, "#ff9a4a")
        cv.rect(19, 5, 20, 19, "#b8521a")
        cv.rect(5, 9, 16, 17, "#3a1a10")
        cv.rect(6, 10, 15, 16, "#ffb030" if f == 0 else "#ff9420")
        cv.rect(6, 15, 15, 16, "#ff5a10")
        cv.line(6, 13, 15, 13, "#c06010")
        cv.p(18, 9, "#ffe0a0"); cv.p(18, 12, "#ffe0a0")
        eyes(cv, 8, 10, gap=4)
        if f == 0:
            cv.rect(5, 20, 7, 21, "#5a3a2a"); cv.rect(15, 20, 17, 21, "#5a3a2a")
            cv.p(11, 2, "#e8e8e8"); cv.p(12, 3, "#e8e8e8")
        else:
            cv.rect(7, 20, 9, 21, "#5a3a2a"); cv.rect(13, 20, 15, 20, "#5a3a2a")
            for (x, y) in ((9, 2), (10, 1), (14, 2), (13, 1), (15, 3)):
                cv.p(x, y, "#e8e8e8")
    elif i == 8:  # 光光（淡紅光子）
        ph = 0 if f == 0 else math.pi
        for x in range(1, 10):
            y = int(round(12 + 3 * math.sin(x * 0.9 + ph)))
            cv.p(x, y, "#ff9aa6")
            cv.p(x, y + 1, "#e05a6a")
        cv.circle(15, 12, 7, "#ff6a7e")
        cv.circle(14.5, 11.5, 5.5, "#ffb0b8", clip=True)
        cv.circle(13.5, 10.5, 2.5, "#ffe4e8", clip=True)
        eyes(cv, 13, 11, gap=4, big=False)
        cv.p(15, 15, "#a0304a"); cv.p(16, 15, "#a0304a")
        rays = [(15, 2), (22, 5), (22, 19), (15, 22)] if f == 0 else [(19, 2), (23, 12), (19, 22), (10, 3)]
        for (x, y) in rays:
            cv.p(x, y, "#ffc0c8")
    cv.outline()
    return cv


# ---------------------------------------------------------------- 收集物 16x16
def bottle(cv, body, liquid, cap, level=8, glint=0):
    cv.rect(6, 1, 9, 2, cap)
    cv.rect(6, 3, 9, 3, "#dfeaf0")
    cv.rect(4, 4, 11, 14, body)
    cv.rect(4, level, 11, 14, liquid)
    cv.p(5, 5 + glint, "#ffffff"); cv.p(5, 6 + glint, "#ffffff")


def item(name, f):
    cv = C(16, 16)
    if name == "rock":
        cv.poly([(2, 9), (4, 4), (8, 2), (12, 3), (14, 8), (12, 13), (6, 14), (2, 12)], "#1f4d36")
        cv.poly([(3, 9), (5, 5), (8, 3), (11, 4), (12, 8), (8, 9)], "#2f6b4a")
        cv.poly([(5, 6), (8, 4), (10, 5), (8, 7)], "#4f9a72")
        cv.line(4, 11, 12, 6, "#7fc8a0")  # 蛇紋石脈紋
        cv.line(6, 13, 12, 10, "#5fa98a")
        if f:
            for (x, y) in ((9, 1), (8, 1), (10, 1), (9, 0), (9, 2)):
                cv.p(x, y, "#ffffff")
        else:
            cv.p(4, 6, "#d8ffe8")
    elif name == "trash":
        dy = 0 if f == 0 else -1
        cv.rect(2, 6 + dy, 11, 11 + dy, "#bfe6f7")
        cv.rect(2, 10 + dy, 11, 11 + dy, "#8cc8e4")
        cv.rect(5, 6 + dy, 8, 11 + dy, "#e74c3c")
        cv.rect(12, 7 + dy, 12, 10 + dy, "#bfe6f7")
        cv.rect(13, 7 + dy, 14, 10 + dy, "#1e5bb8")
        cv.rect(3, 7 + dy, 4, 7 + dy, "#ffffff")
        cv.rect(6, 8 + dy, 7, 8 + dy, "#ffffff")
        if f:
            for (x, y) in ((2, 2), (1, 2), (3, 2), (2, 1), (2, 3)):
                cv.p(x, y, "#ffe04a")
        cv.rect(1, 13, 5, 13, "#d8c89a"); cv.rect(9, 13, 13, 13, "#d8c89a")
    elif name == "energy":
        r = 5.5 if f == 0 else 6.3
        cv.sphere(8, 8, r, "#d08a10", "#ffd030", "#fff6b0")
        cv.poly([(9, 3), (5, 9), (8, 9), (7, 13), (11, 7), (8, 7)], "#d0480a")
        if f:
            for (x, y) in [(0, 8), (15, 8), (8, 0), (8, 15), (2, 2), (13, 13), (13, 2), (2, 13)]:
                cv.p(x, y, "#fff080")
    elif name == "water":
        bottle(cv, "#e6f4fb", "#4fa3e0", "#1e5bb8", level=7 if f == 0 else 8, glint=f)
        cv.rect(5, 8, 10, 13, "#ffffff")
        cv.p(7, 9, "#2a7bd0"); cv.p(8, 9, "#2a7bd0"); cv.rect(6, 10, 9, 11, "#2a7bd0"); cv.rect(7, 12, 8, 12, "#2a7bd0")
        cv.p(6, 10, "#8fd0ff")
    elif name == "micelle":
        cv.rect(3, 2, 12, 4, "#f07a1a")
        cv.rect(3, 4, 12, 4, "#b8521a")
        cv.rect(3, 5, 12, 14, "#fbf3e0")
        cv.rect(11, 5, 12, 14, "#d8ccb0")
        cv.rect(3, 8, 12, 12, "#ff9a3a")
        text(cv, "T", 6, 8, "#ffffff")
        cv.p(4, 6 + f, "#ffffff")
        if f:
            cv.p(13, 1, "#ffe0a0"); cv.p(14, 0, "#ffe0a0")
    elif name == "fe":
        bottle(cv, "#8a5a2a", "#e8a020", "#5a3a1a", level=6, glint=f)
        cv.rect(4, 8, 11, 14, "#fff4d0")
        text(cv, "F", 4, 9, "#7a3a00")
        text(cv, "e", 8, 9, "#7a3a00")
        if f:
            cv.p(13, 3, "#ffd84a"); cv.p(13, 2, "#fff2a0"); cv.p(14, 3, "#ffd84a")
    elif name == "powder":
        pts = [(5, 5), (9, 4), (12, 7), (4, 10), (8, 9), (11, 12), (6, 13), (13, 11)]
        if f:
            pts = [(x + (1 if k % 2 else -1), y + (1 if k % 3 == 0 else 0)) for k, (x, y) in enumerate(pts)]
        for k, (x, y) in enumerate(pts):
            cv.circle(x + 0.5, y + 0.5, 1.8 if k % 3 else 2.3, "#2f6b4a")
            cv.p(x, y, "#7fc8a0")
    elif name == "mg":
        cv.sphere(8, 8, 6.5 if f == 0 else 6, "#0f8a7a", "#2ed3bc", "#b0fff0")
        text(cv, "2", 6, 6, "#ffffff")
        text(cv, "+", 9, 5, "#ffffff")
        if f:
            cv.p(1, 2, "#b0fff0"); cv.p(14, 13, "#b0fff0"); cv.p(14, 2, "#b0fff0")
    elif name == "salt":
        def cube(x, y, s):
            cv.rect(x, y, x + s, y + s, "#e8eef4")
            cv.rect(x, y, x + s, y, "#ffffff")
            cv.rect(x + s, y, x + s, y + s, "#b8c4d0")
            cv.rect(x, y + s, x + s, y + s, "#b8c4d0")
        cube(2, 8, 5); cube(8, 9, 4); cube(5, 3, 4)
        if f:
            for (x, y) in ((13, 4), (12, 4), (14, 4), (13, 3), (13, 5)):
                cv.p(x, y, "#cfe8ff")
        else:
            cv.p(2, 3, "#cfe8ff")
    elif name == "drop":
        rx, ry, cy, top = (5, 5, 10, 1) if f == 0 else (5.8, 4.3, 11, 3)
        cv.ellipse(8, cy, rx, ry, "#2a7bd0")
        cv.poly([(8, top), (8 - rx * 0.75, cy - 2.5), (8 + rx * 0.75, cy - 2.5)], "#2a7bd0")
        cv.ellipse(7.5, cy - 0.5, rx - 1.3, ry - 1.3, "#6fc0f8", clip=True)
        cv.rect(5, cy - 3, 5, cy - 1, "#e0f4ff", clip=True)
    elif name == "photon":
        ph = 0 if f == 0 else math.pi
        for x in range(0, 7):
            cv.p(x, int(round(8 + 2.2 * math.sin(x * 1.1 + ph))), "#ff8a9a")
        cv.circle(10.5, 8, 4.2 if f == 0 else 4.8, "#ff6a7e")
        cv.circle(10, 7.5, 2.6, "#ffd0d6", clip=True)
        cv.p(9, 6, "#ffffff")
    cv.outline()
    return cv


# ---------------------------------------------------------------- 危險物
def hazard(name, f):
    big = name in ("wave", "ball")
    cv = C(24, 24) if big else C(16, 16)
    if name == "wave":
        o = 0 if f == 0 else 1
        cv.poly([(1, 21), (2, 12), (6, 6), (12, 3), (18, 4), (22, 8), (21, 12), (17, 10), (13, 11), (11, 15), (12, 21)], "#1d6fd0")
        cv.poly([(2, 21), (3, 14), (7, 9), (11, 8), (9, 13), (9, 21)], "#0d3f8f")
        cv.line(6, 6, 12, 3, "#ffffff", w=2)
        cv.line(12, 3, 18, 4, "#ffffff", w=2)
        cv.line(18, 4, 21, 8, "#ffffff", w=2)
        cv.p(20, 11 - o, "#ffffff"); cv.p(18, 10, "#cfeaff")
        cv.line(14, 7, 16, 7, "#5fb0f0")
        cv.rect(1, 20, 22, 22, "#5fb0f0")
        for x in range(1 + o, 23, 3):
            cv.p(x, 20, "#ffffff")
        for (x, y) in ([(22, 2), (20, 1), (15, 1)] if f == 0 else [(22, 4), (21, 1), (16, 0)]):
            cv.p(x, y, "#ffffff")
    elif name == "ball":
        cv.sphere(13, 12, 9.5, "#7a808c", "#dfe3e8", "#ffffff")
        if f == 0:
            cv.line(5, 16, 21, 8, "#a8aeb8", w=2, clip=True)
        else:
            cv.line(9, 4, 17, 20, "#a8aeb8", w=2, clip=True)
        for k, y in enumerate((7, 12, 17)):
            x0 = 0 if (k + f) % 2 == 0 else 1
            cv.line(x0, y, x0 + 1, y, "#c0c6d0")
    elif name == "solvent":
        cv.rect(3, 2, 12, 14, "#6a4a8a")
        cv.rect(3, 2, 12, 2, "#8a6aaa"); cv.rect(3, 14, 12, 14, "#4a2f66")
        cv.rect(3, 5, 12, 5, "#4a2f66"); cv.rect(3, 12, 12, 12, "#4a2f66")
        cv.rect(11, 2, 12, 14, "#4a2f66")
        cv.rect(6, 7, 9, 9, "#ffffff"); cv.rect(7, 10, 8, 10, "#ffffff")  # 骷髏
        cv.p(6, 8, "#111111"); cv.p(9, 8, "#111111")
        cv.p(5, 11, "#ffffff"); cv.p(10, 11, "#ffffff"); cv.p(5, 6, "#ffffff"); cv.p(10, 6, "#ffffff")
        if f:
            cv.rect(13, 11, 13, 13, "#8aff4a"); cv.p(14, 14, "#8aff4a")
        else:
            cv.p(13, 11, "#8aff4a")
    elif name == "acid":
        bottle(cv, "#f0e6f0", "#e0303a", "#2a2a2a", level=6, glint=0)
        cv.poly([(7.5, 8), (4.5, 13), (10.5, 13)], "#ffd020")
        cv.rect(7, 9, 7, 11, "#111111"); cv.p(7, 12, "#111111")
        for (x, y) in ([(9, 0), (11, 1)] if f == 0 else [(10, 0), (12, 0), (12, 2)]):
            cv.p(x, y, "#c8f070")
    elif name == "clump":
        w = 0 if f == 0 else 1
        for (x, y, r) in [(6, 9, 4.5), (10, 8 - w, 4.5), (8, 11, 4.2), (5 + w, 6, 3), (11, 12 + w, 3)]:
            cv.circle(x, y, r, "#5a6e4a")
        for (x, y, r) in [(6, 8, 3), (10, 7 - w, 3), (8, 10, 2.5)]:
            cv.circle(x, y, r, "#7a8e62", clip=True)
        cv.line(4, 12, 7, 10, "#3a4a2e"); cv.line(9, 13, 12, 11, "#3a4a2e")
        cv.p(6, 8, "#111111"); cv.p(10, 8, "#111111")
        cv.p(5, 7, "#111111"); cv.p(11, 7, "#111111")
    elif name == "ca":
        cv.sphere(8, 8, 7.4, "#4a1a7a", "#9a4ad8", "#e0b0ff")
        text(cv, "C", 3, 5, "#ffffff"); text(cv, "a", 7, 5, "#ffffff")
        cv.rect(12, 3, 12, 5, "#ffffff"); cv.rect(11, 4, 13, 4, "#ffffff")
        if f:
            cv.line(4, 11, 6, 12, "#2a0a4a"); cv.line(11, 11, 9, 12, "#2a0a4a")
        else:
            cv.line(4, 12, 6, 12, "#2a0a4a"); cv.line(9, 12, 11, 12, "#2a0a4a")
    elif name == "wall":
        cv.rect(1, 1, 14, 14, "#6f7884")
        cv.rect(1, 1, 14, 2, "#9aa4b0")
        cv.rect(1, 13, 14, 14, "#4a525c")
        o = 0 if f == 0 else 2
        for y in range(6, 11):
            for x in range(1, 15):
                cv.p(x, y, "#f0c020" if ((x + y + o) // 2) % 2 == 0 else "#222222")
        for (x, y) in ((3, 3), (12, 3), (3, 12), (12, 12)):
            cv.p(x, y, "#d0d6dc")
    elif name == "fire":
        if f == 0:
            outer = [(8, 1), (11, 5), (13, 8), (13, 12), (10, 15), (5, 15), (2, 12), (3, 7), (5, 9), (6, 5)]
            mid = [(8, 5), (10, 9), (10, 12), (8, 14), (6, 14), (4, 12), (5, 9), (7, 10)]
        else:
            outer = [(7, 1), (9, 4), (12, 5), (13, 10), (11, 15), (5, 15), (2, 11), (4, 6), (6, 8)]
            mid = [(9, 6), (11, 10), (10, 13), (8, 14), (6, 14), (5, 11), (7, 9)]
        cv.poly(outer, "#e0301a")
        cv.poly(mid, "#ff8a1a")
        cv.ellipse(8, 12.5, 2.2, 2.5, "#ffe04a")
    elif name == "sign":
        t = 0 if f == 0 else 1
        cv.rect(7, 10, 8, 15, "#7a4a22")
        cv.rect(1, 2 - t, 14, 10 - t, "#d8a860")
        cv.rect(1, 2 - t, 14, 2 - t, "#f0c880"); cv.rect(1, 10 - t, 14, 10 - t, "#a07030")
        cv.rect(2, 4 - t, 4, 8 - t, "#e02020" if f == 0 else "#ff6040")
        cv.rect(3, 4 - t, 3, 6 - t, "#ffffff"); cv.p(3, 8 - t, "#ffffff")
        cv.rect(6, 4 - t, 12, 4 - t, "#5a3010"); cv.rect(6, 6 - t, 11, 6 - t, "#5a3010"); cv.rect(6, 8 - t, 12, 8 - t, "#5a3010")
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

    if s == 1:  # 七星潭礫石灘＋海浪線
        for key in ("a", "b"):
            cv = base("#cfc8bb")
            noise(cv, ["#bdb5a6", "#e0dbd0"], 80)
            for _ in range(14 if key == "a" else 8):
                x, y = rng.integers(3, 29, 2)
                r = rng.uniform(1.4, 2.6)
                col = ["#f2efe8", "#9a9488", "#7d8a86", "#2f6b4a", "#b8b0a2"][rng.integers(0, 5)]
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
        cv = base("#4a4f55")  # 岩壁
        for _ in range(7):
            x, y = rng.integers(0, 32, 2)
            cv.poly([(x, y), (x + 9, y + 2), (x + 6, y + 8), (x - 2, y + 6)], "#5f666e")
        noise(cv, ["#3a3e44", "#6a727a"], 60)
        cv.rect(0, 0, 31, 2, "#2f6b4a"); cv.rect(0, 2, 31, 3, "#24553a")
        for x in range(0, 32, 3):
            cv.p(x, 4, "#2f6b4a")
        out["c"] = cv
    elif s == 2:  # 球磨工坊鐵板（防滑紋）
        for key in ("a", "b"):
            cv = base("#4a4f57")
            for y in range(2, 32, 6):
                for x in range((y // 6 % 2) * 3 + 1, 32, 6):
                    cv.line(x, y + 1, x + 2, y - 1, "#6c727c")
                    cv.p(x, y + 2, "#33373d")
            cv.rect(0, 0, 31, 0, "#5c626b"); cv.rect(0, 0, 0, 31, "#5c626b")
            cv.rect(0, 31, 31, 31, "#2c3036"); cv.rect(31, 0, 31, 31, "#2c3036")
            if key == "b":
                for (x, y) in ((3, 3), (27, 3), (3, 27), (27, 27)):
                    cv.rect(x, y, x + 1, y + 1, "#8a9099"); cv.p(x + 1, y + 1, "#2c3036")
                cv.rect(0, 14, 31, 17, "#2c3036")
                for x in range(-4, 34, 6):
                    cv.poly([(x, 17), (x + 3, 14), (x + 5, 14), (x + 2, 17)], "#e0b020")
            out[key] = cv
        cv = base("#2c3036")  # 鋼製圍欄
        cv.rect(0, 4, 31, 7, "#e0b020"); cv.rect(0, 20, 31, 23, "#e0b020")
        for x in range(0, 32, 8):
            cv.rect(x, 0, x + 2, 31, "#7a828c"); cv.rect(x, 0, x, 31, "#a0a8b2")
        out["c"] = cv
    elif s == 3:  # 實驗室白磚＋綠線
        for key in ("a", "b"):
            cv = base("#f2f5f3")
            for y in range(32):
                for x in range(32):
                    if x % 16 == 0 or y % 16 == 0:
                        cv.p(x, y, "#5fa98a")
                    elif x % 16 == 15 or y % 16 == 15:
                        cv.p(x, y, "#d8e2dc")
            if key == "b":  # 綠燒瓶圖樣
                cv.rect(13, 4, 18, 4, "#1f6e42")
                cv.rect(14, 5, 17, 11, "#1f6e42"); cv.rect(15, 5, 16, 11, "#e6f4ec")
                cv.poly([(14, 11), (17, 11), (25, 26), (6, 26)], "#1f6e42")
                cv.poly([(15, 12), (16, 12), (23, 25), (8, 25)], "#e6f4ec")
                cv.poly([(11, 19), (20, 19), (23, 25), (8, 25)], "#2fbf71")
                cv.p(12, 22, "#9ff0c0"); cv.p(17, 21, "#9ff0c0"); cv.p(15, 23, "#9ff0c0")
            out[key] = cv
        cv = base("#2e7d5b")  # 實驗桌
        cv.rect(0, 0, 31, 5, "#3fa476"); cv.rect(0, 5, 31, 6, "#1f5e40")
        for x in range(2, 32, 8):
            cv.rect(x, 12, x + 4, 26, "#24684a"); cv.rect(x + 2, 18, x + 2, 19, "#d8e2dc")
        out["c"] = cv
    elif s == 4:  # 反應槽藍漩渦
        for key in ("a", "b"):
            cv = base("#1f5fa8")
            ph = 0 if key == "a" else 1.6
            k = 2 * math.pi / 16
            for y in range(32):
                for x in range(32):
                    v = math.sin((x + y) * k + ph) + math.sin((x - y) * k)
                    if v > 1.2:
                        cv.p(x, y, "#4a8fd8")
                    elif v < -1.2:
                        cv.p(x, y, "#16467e")
            if key == "b":
                for j in range(60):
                    a = j * 0.3
                    r = 1.5 + j * 0.22
                    cv.p(16 + r * math.cos(a), 16 + r * math.sin(a), "#bfe6ff")
                for (x, y) in ((5, 6), (25, 9), (8, 26)):
                    cv.circle(x, y, 1.6, "#bfe6ff"); cv.p(x, y, "#1f5fa8")
            out[key] = cv
        cv = base("#8a98a8")  # 槽壁
        cv.rect(0, 0, 31, 3, "#c0ccd8"); cv.rect(0, 28, 31, 31, "#5a6878")
        for x in range(4, 32, 10):
            cv.rect(x, 0, x, 31, "#6a7888")
            for y in (7, 20):
                cv.rect(x + 2, y, x + 3, y + 1, "#dfe6ee")
        cv.rect(0, 12, 31, 15, "#1f5fa8")
        out["c"] = cv
    elif s == 5:  # 太平洋深藍＋氣泡
        for key in ("a", "b"):
            cv = base("#0a2a5e")
            for y in range(32):
                for x in range(32):
                    if (x * 7 + y * 3) % 23 == 0:
                        cv.p(x, y, "#123a7a")
            noise(cv, ["#0e3470", "#082250"], 50)
            for _ in range(4):
                x, y = rng.integers(4, 28, 2)
                r = rng.uniform(1.4, 2.6)
                cv.circle(x, y, r, "#6fb8f0")
                cv.circle(x, y, r - 0.9, "#0a2a5e")
                cv.p(x - r * 0.4, y - r * 0.4, "#ffffff")
            if key == "b":  # 深層海水取水管
                cv.rect(12, 0, 19, 31, "#9aa4b0"); cv.rect(12, 0, 13, 31, "#c8d0d8"); cv.rect(18, 0, 19, 31, "#5a6470")
                for y in (6, 22):
                    cv.rect(10, y, 21, y + 2, "#c99a3e"); cv.rect(10, y + 2, 21, y + 2, "#8a6a2a")
            out[key] = cv
        cv = base("#1a2430")  # 礁岩
        for _ in range(9):
            x, y = rng.integers(0, 32, 2)
            cv.ellipse(x, y, rng.uniform(3, 6), rng.uniform(2, 4), "#2a3644")
        noise(cv, ["#0e141c", "#3a4a5c"], 60)
        for x in range(2, 32, 7):
            cv.line(x, 31, x + 1, 24, "#2e7d5b"); cv.p(x + 1, 23, "#5fa98a")
        out["c"] = cv
    elif s == 6:  # 離心盤金屬同心圓
        for key in ("a", "b"):
            cv = base("#8f99a4")
            for y in range(32):
                for x in range(32):
                    d = math.hypot(x - 15.5, y - 15.5)
                    if int(d) % 5 == 0:
                        cv.p(x, y, "#b8c2cc")
                    elif int(d) % 5 == 2:
                        cv.p(x, y, "#7a848f")
            if key == "b":  # 旋轉水流箭頭
                for j in range(40):
                    a = j / 40 * math.pi * 1.5
                    cv.p(15.5 + 11 * math.cos(a), 15.5 + 11 * math.sin(a), "#2f7fb8")
                    cv.p(15.5 + 10 * math.cos(a), 15.5 + 10 * math.sin(a), "#7ab8e0")
                ex, ey = 15.5, 4.5
                cv.poly([(ex, ey - 3), (ex + 4, ey), (ex, ey + 3)], "#2f7fb8")
            out[key] = cv
        cv = base("#4a525c")  # 離心壁
        cv.rect(0, 0, 31, 4, "#9aa4b0"); cv.rect(0, 4, 31, 5, "#2c3238")
        for x in range(3, 32, 8):
            cv.rect(x, 9, x + 1, 10, "#c0c8d0"); cv.rect(x + 4, 22, x + 5, 23, "#c0c8d0")
        cv.rect(0, 27, 31, 31, "#3a4048")
        out["c"] = cv
    elif s == 7:  # 烘箱格柵
        for key in ("a", "b"):
            cv = base("#5a5550")
            for y in range(0, 32, 4):
                cv.rect(0, y, 31, y + 1, "#8a847c"); cv.rect(0, y, 31, y, "#aaa49a")
            for x in range(0, 32, 8):
                cv.rect(x, 0, x + 1, 31, "#6e6860")
            if key == "b":  # 發熱管
                cv.rect(0, 13, 31, 18, "#3a2a20")
                cv.rect(0, 14, 31, 17, "#e85a1a"); cv.rect(0, 15, 31, 15, "#ffb040")
                for x in range(2, 32, 6):
                    cv.p(x, 16, "#ffe080")
            out[key] = cv
        cv = base("#3a3430")  # 烘箱壁
        cv.rect(0, 0, 31, 3, "#e8712a"); cv.rect(0, 3, 31, 4, "#a04a10")
        for x in (4, 27):
            for y in (10, 24):
                cv.rect(x, y, x + 1, y + 1, "#9a948a")
        cv.rect(8, 12, 23, 20, "#2a2420"); cv.rect(9, 13, 22, 19, "#5a2a10"); cv.rect(10, 14, 12, 15, "#ff9a40")
        out["c"] = cv
    elif s == 8:  # 量測台深紫＋光譜曲線
        for key in ("a", "b"):
            cv = base("#2a1f4a")
            for y in range(0, 32, 8):
                cv.rect(0, y, 31, y, "#3a2f62")
            for x in range(0, 32, 8):
                cv.rect(x, 0, x, 31, "#3a2f62")
            if key == "b":
                for x in range(32):
                    y = 20 - 9 * math.exp(-((x - 12) / 5) ** 2) - 4 * math.exp(-((x - 24) / 3) ** 2)
                    cv.p(x, int(y), "#ff8a9a"); cv.p(x, int(y) + 1, "#a04a7a")
                    y2 = 25 - 4 * math.exp(-((x - 14) / 6) ** 2)
                    if x % 2 == 0:
                        cv.p(x, int(y2), "#7fd0ff")
            out[key] = cv
        cv = base("#15102a")
        cv.rect(0, 0, 31, 3, "#6a5a9a"); cv.rect(0, 3, 31, 4, "#3a2f62")
        for x in range(2, 32, 6):
            cv.rect(x, 12, x + 2, 14, "#c99a3e"); cv.p(x + 1, 13, "#ffe0a0")
        cv.rect(0, 26, 31, 27, "#3a2f62")
        out["c"] = cv
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
    cv = C(16, 16)
    pts = [(7.5 + 7 * math.cos(math.radians(-90 + 60 * k)), 7.5 + 7 * math.sin(math.radians(-90 + 60 * k))) for k in range(6)]
    cv.poly(pts, "#2e8b57")
    inner = [(7.5 + (x - 7.5) * 0.7, 7.5 + (y - 7.5) * 0.7) for (x, y) in pts]
    cv.poly(inner, "#0e2a22")
    if full:
        cv.sphere(7.5, 7.5, 3.8, "#0f8a7a", "#2ed3bc", "#b0fff0")
    else:
        for k in (0, 2, 4):
            a = math.radians(60 * k)
            cv.p(7.5 + 2.5 * math.cos(a), 7.5 + 2.5 * math.sin(a), "#3a6a58")
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
        cv.circle(x, y, 3.6, ["#5fd39a", "#ffd23a", "#2ed3bc"][k])
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
    q = np.maximum(np.abs(px) * 0.866 + np.abs(py) * 0.5, np.abs(py))  # 墨玉六角徽
    put(q <= 5.5, "#2e8b57")
    put(q <= 2.5, "#5fd39a")
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
def title():
    W, Hh = 320, 180
    cv = C(W, Hh)
    rng = np.random.default_rng(42)
    sky = ["#0b1f3a", "#13305a", "#1c4a7a", "#2f6d9a", "#5a90b8", "#e8a86a", "#f5c88a"]
    for y in range(78):
        cv.rect(0, y, W - 1, y, sky[min(int(y / 78 * len(sky)), len(sky) - 1)])
    for _ in range(40):
        cv.p(rng.integers(0, W), rng.integers(0, 30), "#dfe8ff")
    cv.circle(250, 78, 14, "#ffd88a"); cv.circle(250, 78, 11, "#fff0c0")  # 太平洋日出
    sea = ["#2f6d9a", "#1f5f8f", "#165082", "#0e4070", "#0a3260"]
    for y in range(78, 128):
        cv.rect(0, y, W - 1, y, sea[min(int((y - 78) / 50 * len(sea)), len(sea) - 1)])
    for y in range(80, 126, 4):
        for x in range((y * 7) % 11, W, 13 + (y % 5)):
            cv.rect(x, y, x + 3, y, "#5a90c0")
    for x in range(220, 280):
        for y in range(80, 120, 3):
            if (x + y) % 7 == 0:
                cv.p(x, y, "#ffd88a")
    # 清水斷崖
    cv.poly([(0, 20), (22, 18), (46, 30), (70, 34), (92, 52), (112, 70), (128, 92), (138, 126), (0, 126)], "#2c3a34")
    cv.poly([(0, 24), (20, 22), (42, 34), (64, 40), (84, 58), (100, 76), (112, 100), (118, 126), (0, 126)], "#3c5248")
    for _ in range(18):
        x, y = rng.integers(4, 110), rng.integers(34, 120)
        cv.line(x, y, x + rng.integers(-4, 6), y + rng.integers(6, 14), "#26302c")
    for _ in range(60):
        x = rng.integers(0, 96)
        ytop = 20 + (x / 96) * 34
        cv.circle(x, ytop + rng.uniform(0, 6), rng.uniform(1.5, 3.5), ["#2e7d5b", "#24684a", "#3f9a6e"][rng.integers(0, 3)])
    for k in range(40):  # 斷崖底浪花
        x, y = rng.integers(112, 146), rng.integers(112, 126)
        if x > 112 + (y - 100) * 0.9:
            cv.p(x, y, "#e8f4ff")
    # 七星潭礫石灘
    for y in range(124, Hh):
        cv.rect(0, y, W - 1, y, "#cfc8bb")
    for x in range(W):
        y = int(124 + 6 * math.sin(x / W * math.pi))
        cv.rect(x, y - 2, x, y, "#ffffff")
        cv.rect(x, y - 4, x, y - 3, "#bfe6ff")
    for _ in range(260):
        x, y = rng.integers(0, W), rng.integers(132, Hh)
        r = rng.uniform(1.0, 2.8)
        col = ["#f2efe8", "#9a9488", "#7d8a86", "#2f6b4a", "#b8b0a2", "#e0dbd0"][rng.integers(0, 6)]
        cv.ellipse(x, y, r * 1.3, r, "#8a8476")
        cv.ellipse(x - 0.3, y - 0.3, max(r * 1.3 - 0.7, 0.6), max(r - 0.7, 0.6), col)
    # 六角綠晶（墨玉小晶）
    gx, gy, R = 160, 104, 24
    for rr in (R + 9, R + 5):
        for k in range(0, 36, 2):
            a = math.radians(k * 10)
            cv.p(gx + rr * math.cos(a), gy + rr * math.sin(a), "#9ff0c0")
    pts = [(gx + R * math.cos(math.radians(-90 + 60 * k)), gy + R * math.sin(math.radians(-90 + 60 * k))) for k in range(6)]
    shades = ["#5fd39a", "#2e8b57", "#1f5e3e", "#174a30", "#2e8b57", "#7fe6b0"]
    for k in range(6):
        cv.poly([(gx, gy), pts[k], pts[(k + 1) % 6]], shades[k])
    cv.poly([(gx + (p[0] - gx) * 0.55, gy + (p[1] - gy) * 0.55) for p in pts], "#3aa86c")
    for k in range(6):
        cv.line(gx + (pts[k][0] - gx) * 0.55, gy + (pts[k][1] - gy) * 0.55, pts[k][0], pts[k][1], "#1f5e3e")
    cv.rect(gx - 8, gy - 3, gx - 5, gy + 1, "#ffffff"); cv.rect(gx - 6, gy - 2, gx - 5, gy + 1, "#111122")
    cv.rect(gx + 4, gy - 3, gx + 7, gy + 1, "#ffffff"); cv.rect(gx + 6, gy - 2, gx + 7, gy + 1, "#111122")
    cv.line(gx - 2, gy + 5, gx + 1, gy + 5, "#174a30")
    cv.rect(gx - 14, gy - 14, gx - 12, gy - 12, "#e8fff0")
    # 三位主角剪影
    def sil(spr, x, y):
        al = spr.a[:, :, 3] > 0
        for yy in range(spr.h):
            for xx in range(spr.w):
                if al[yy, xx]:
                    cv.rect(x + xx * 2, y + yy * 2, x + xx * 2 + 1, y + yy * 2 + 1, "#0b1f3a")
    sil(draw_hero("kid", "f", 0), 206, 108)
    sil(draw_hero("adult", "m", 1), 236, 106)
    sil(draw_hero("elder", "n", 0), 268, 107)
    # 標題字（自訂 5x5 點陣）
    for s_, y0, sc, col in (("SERPENTINE", 5, 3, "#5fd39a"), ("HARMONY SQUAD", 31, 2, "#ffd23a"), ("HUALIEN", 50, 1, "#bfe6ff")):
        w = text_w(s_, F5, 1, sc)
        x0 = (W - w) // 2
        if sc > 1:
            text(cv, s_, x0 + 1, y0 + 1, "#04101e", F5, 1, sc)
        text(cv, s_, x0, y0, col, F5, 1, sc)
    return cv


# ---------------------------------------------------------------- 打包
HERO_IDS = [f"{b}_{g}" for b in ("kid", "teen", "adult", "elder") for g in ("f", "m", "n")]
MATES = list(range(1, 9))
ITEMS = ["rock", "trash", "energy", "water", "micelle", "fe", "powder", "mg", "salt", "drop", "photon"]
HAZS = ["wave", "ball", "solvent", "acid", "clump", "ca", "wall", "fire", "sign"]
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
