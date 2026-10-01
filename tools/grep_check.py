# -*- coding: utf-8 -*-
"""全文檢索：repo 內不得出現禁用詞、身體功效宣稱字眼、外部 CDN／外部網址（vendor/ 內第三方原始碼除外）。

用法：PYTHONUTF8=1 python tools/grep_check.py
禁用詞以 Unicode 碼位存放，避免本檔自己被檢出。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "vendor", "out", "__pycache__", "shots"}
TEXT_EXT = {".html", ".js", ".css", ".py", ".md", ".txt", ".json", ".gitignore", ".nojekyll", ""}

def u(*cps):
    return "".join(chr(c) for c in cps)


BANNED = {
    "引擎名稱": "U" + "nity",
    "舊稱呼": u(0x8f49, 0x77f3),
    "廠商名": u(0x4e09, 0x6cf0),
    "人名稱呼": u(0x8cf4, 0x54e5),
    "排放敘述": u(0x77f3, 0x6750, 0x52a0, 0x5de5, 0x5ee0, 0x6392, 0x653e),
}
BODY_CLAIMS = [u(0x7642, 0x6548),
               u(0x6cbb, 0x7642),
               u(0x6cbb, 0x7652),
               u(0x4fdd, 0x5065),
               u(0x990a, 0x751f),
               u(0x8840, 0x6db2, 0x5faa, 0x74b0),
               u(0x6539, 0x5584, 0x7761, 0x7720),
               u(0x9178, 0x75db),
               u(0x75bc, 0x75db),
               u(0x6d88, 0x708e),
               u(0x514d, 0x75ab),
               u(0x6297, 0x8001),
               u(0x6392, 0x6bd2),
               u(0x5065, 0x5eb7),
               u(0x8212, 0x7de9),
               u(0x75c5)]
URL_RE = re.compile(r"https?://[^\s\"'<>)]+")
URL_ALLOW = ("https://rlirdo.github.io/serpentine-webar", "http://127.0.0.1", "http://localhost")


def files():
    for p in ROOT.rglob("*"):
        if p.is_dir() or any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts):
            continue
        if p.suffix.lower() in TEXT_EXT:
            yield p


def main():
    hits = []
    n = 0
    for p in files():
        n += 1
        rel = p.relative_to(ROOT).as_posix()
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for k, w in BANNED.items():
                if w.lower() in line.lower():
                    hits.append((rel, i, k, line.strip()[:80]))
            for w in BODY_CLAIMS:
                if w in line:
                    hits.append((rel, i, "身體功效字眼", line.strip()[:80]))
            for url in URL_RE.findall(line):
                if not url.startswith(URL_ALLOW):
                    hits.append((rel, i, "外部網址", url))
    print(f"檢查檔案數：{n}（略過 vendor/、tools/out/、tools/shots/、.git/）")
    if hits:
        for h in hits:
            print("  HIT", *h)
        print(f"共 {len(hits)} 筆命中")
        return 1
    print("通過：無禁用詞、無身體功效字眼、無外部 CDN／外部網址")
    return 0


if __name__ == "__main__":
    sys.exit(main())
