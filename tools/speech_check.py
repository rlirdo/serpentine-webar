# -*- coding: utf-8 -*-
"""語音正規化檢查（2.0.0）：列出所有會被唸的句子「正規化前 → 正規化後」，並檢查殘留符號＝0。

用法：PYTHONUTF8=1 python tools/speech_check.py
- 用 headless Chrome 載入 js/speech.js 與 js/content.js（與遊戲完全相同的正規化程式），不在 Python 重寫一份。
- 檢查範圍：
  A. content.js 匯出的全部字串（遞迴，含國小／國中兩版、題目、選項、詳解；名稱類常數除外）。
  B. game.js／hud.js 內交給語音的硬編字串（hud.say／next／choose／toast／modal 的 speech 參數、speech.speak）。
     樣板字串的 ${…} 以「1」代入。
  C. 自動通關實際記錄到的每一次 speak()（讀 tools/out/autoplay_*.json 的 speech_log）。
- 殘留＝正規化後（不做最後的保險清除）仍有：非中文／數字／單一英文字母／中文標點的字元，或連續 2 個以上英文字母。
- 結果寫到 tools/speech_lines.txt；有殘留時 exit 1。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import devserver  # noqa: E402
from chrome import Chrome  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT_TXT = ROOT / "tools" / "speech_lines.txt"
CJK = re.compile(r"[㐀-鿿]")
SPEECH_LINE = re.compile(r"hud\.(say|next|choose|toast)\(|speech:|speech\.speak\(|\.speak\(")
BSL = chr(92)
NL = chr(10)
STR_RE = re.compile(r'"((?:[^"\\]|\\.)*)"|`((?:[^`\\]|\\.)*)`')


def scan_strings(line):
    """逐字掃描一行 JS：回傳 (起點, 字串內容)；樣板字串的 ${…}（可巢狀）以「1」代入。"""
    out = []
    i, n = 0, len(line)
    while i < n:
        c = line[i]
        if c == '"' or c == "'":
            j = i + 1
            buf = []
            while j < n and line[j] != c:
                if line[j] == BSL and j + 1 < n:
                    buf.append(line[j:j + 2]); j += 2; continue
                buf.append(line[j]); j += 1
            out.append((i, "".join(buf)))
            i = j + 1
        elif c == "`":
            j = i + 1
            buf = []
            while j < n and line[j] != "`":
                if line.startswith("${", j):
                    depth, k = 1, j + 2
                    while k < n and depth:
                        if line.startswith("${", k):
                            depth += 1; k += 2; continue
                        if line[k] == "{":
                            depth += 1
                        elif line[k] == "}":
                            depth -= 1
                        k += 1
                    buf.append("1")
                    j = k
                    continue
                buf.append(line[j]); j += 1
            out.append((i, "".join(buf)))
            i = j + 1
        elif c == "/" and line.startswith("//", i):
            break
        else:
            i += 1
    return out


def js_literals():
    """game.js／hud.js 中交給語音的字串（含 CJK），排除按鈕 label。"""
    found = []
    for f in ("js/game.js", "js/hud.js"):
        for n, line in enumerate((ROOT / f).read_text(encoding="utf-8").splitlines(), 1):
            if not SPEECH_LINE.search(line):
                continue
            for start, text in scan_strings(line):
                before = line[:start].rstrip()
                if before.endswith("label:") or before.endswith("label =") or not CJK.search(text):
                    continue
                text = re.sub(r"<[^>]+>", NL, text).replace(BSL + "n", NL)
                text = NL.join(x.strip() for x in text.split(NL) if x.strip())
                if text:
                    found.append((f"{f}:{n}", text))
    return found


def runtime_lines():
    lines = {}
    for p in sorted((ROOT / "tools" / "out").glob("autoplay_*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for e in d.get("speech_log") or []:
            lines.setdefault(e["src"], p.name)
    return lines


def main():
    srv = devserver.start(8768)
    ch = Chrome(port=9340)
    try:
        ch.send("Runtime.enable")
        ch.send("Page.enable")
        ch.send("Page.navigate", {"url": "http://127.0.0.1:8768/index.html"})
        for _ in range(50):
            if ch.eval("document.readyState") == "complete":
                break
            ch.poll_events(0.1)
        content = ch.eval("""(async () => {
          const C = await import('/js/content.js');
          const skip = new Set(['CREDIT', 'TITLE', 'STORE_KEY', 'VERSION', 'FACETS', 'GRADE_LABEL']);
          const out = [];
          const walk = (v, path) => {
            if (typeof v === 'string') { if (/[\\u3400-\\u9fff]/.test(v)) out.push([path, v]); return; }
            if (Array.isArray(v)) { v.forEach((x, i) => walk(x, path + '[' + i + ']')); return; }
            if (v && typeof v === 'object') for (const k of Object.keys(v)) {
              if (['id', 'facet', 'face', 'name'].includes(k)) continue;
              walk(v[k], path + '.' + k);
            }
          };
          for (const k of Object.keys(C)) if (!skip.has(k)) walk(C[k], k);
          return out;
        })()""")
        literals = js_literals()
        runtime = runtime_lines()
        items = [("A", p, t) for p, t in content] + [("B", p, t) for p, t in literals] + [("C", src, t) for t, src in runtime.items()]
        payload = json.dumps([t for _, _, t in items], ensure_ascii=False)
        normed = ch.eval(f"""(async () => {{
          const S = await import('/js/speech.js');
          return {payload}.map((t) => {{
            const pre = S.normalizeForSpeech(t, {{ sweep: false }});
            return [pre, S.normalizeForSpeech(t), S.speechResidue(pre)];
          }});
        }})()""")
    finally:
        ch.close()
        srv.shutdown()

    sections = {"A": "A. content.js 全部字串", "B": "B. game.js／hud.js 交給語音的硬編字串",
                "C": "C. 自動通關實際 speak() 紀錄（tools/out/autoplay_*.json）"}
    residue_total = 0
    body = []
    counts = {"A": 0, "B": 0, "C": 0}
    for sec in "ABC":
        body.append("")
        body.append("=" * 72)
        body.append(sections[sec])
        body.append("=" * 72)
        for (s, where, text), (pre, final, res) in zip(items, normed):
            if s != sec:
                continue
            counts[sec] += 1
            residue_total += len(res)
            flag = f"   ← 殘留：{' '.join(res)}" if res else ""
            body.append(f"[{where}]")
            body.append("  原文：" + text.replace("\n", " ⏎ "))
            body.append("  唸法：" + pre + flag)
            if final != pre:
                body.append("  （保險清除後）" + final)
    head = [
        "墨玉晶格修復任務 WebAR 2.0.0 — 語音正規化對照表",
        "由 tools/speech_check.py 自動產生；正規化程式＝js/speech.js normalizeForSpeech()（與遊戲相同）。",
        "「唸法」是正規化後、尚未做最後保險清除的結果；殘留符號必須為 0。",
        f"句數：A {counts['A']}、B {counts['B']}、C {counts['C']}（合計 {sum(counts.values())}）",
        f"殘留符號：{residue_total}",
    ]
    OUT_TXT.write_text("\n".join(head + body) + "\n", encoding="utf-8")
    print("\n".join(head))
    print(f"寫入 {OUT_TXT.relative_to(ROOT).as_posix()}")
    if residue_total:
        for (s, where, text), (pre, final, res) in zip(items, normed):
            if res:
                print("  RESIDUE", s, where, res, "|", pre[:60])
    return 1 if residue_total else 0


if __name__ == "__main__":
    sys.exit(main())
