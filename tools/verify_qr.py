# -*- coding: utf-8 -*-
"""實際解碼 QR：assets/qr.png 與 assets/target_print.pdf（PyMuPDF 轉 300 dpi 點陣）內的 QR 必須是部署網址。

用法：PYTHONUTF8=1 python tools/verify_qr.py   （需要 opencv-python、PyMuPDF）
"""
import sys
from pathlib import Path

import cv2
import fitz
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EXPECT = "https://rlirdo.github.io/serpentine-webar/"


def decode(img):
    det = cv2.QRCodeDetector()
    found = []
    for scale in (1.0, 0.5, 2.0):
        im = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale != 1 else img
        ok, texts, _, _ = det.detectAndDecodeMulti(im)
        if ok:
            found += [t for t in texts if t]
        if found:
            break
    if not found:
        t, _, _ = det.detectAndDecode(img)
        if t:
            found.append(t)
    return sorted(set(found))


def main():
    res = {}
    qr = cv2.imdecode(np.fromfile(str(ROOT / "assets" / "qr.png"), np.uint8), cv2.IMREAD_COLOR)
    qr = cv2.copyMakeBorder(qr, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    res["assets/qr.png"] = decode(qr)
    doc = fitz.open(str(ROOT / "assets" / "target_print.pdf"))
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=300)
        img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].copy()
        res[f"assets/target_print.pdf p{i + 1}"] = decode(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    ok = True
    for k, v in res.items():
        good = v == [EXPECT]
        ok &= good
        print(("OK  " if good else "FAIL"), k, v)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
