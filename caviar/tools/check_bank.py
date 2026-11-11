# -*- coding: utf-8 -*-
"""晶球護衛隊 2.0：content.js 內容與題庫結構檢查。

不需 node：以 Python 小型解析器讀取 js/content.js 所有 `export const X = <字面值>;`。
檢查：
  - BANK 三個程度（elem／junior／senior）各 10 題，題號 E／J／S 1–10 依序
  - 每程度 pre 恰 3 題，面向為知識／探究／態度各 1；非前測行動題 ≥ 2；四個面向都有
  - 每題四個不重複選項、answer = 0、explain 非空
  - 全檔不含「方向盤」「煞車」
  - LEVELS 的 intro／learn 皆有三個程度；LEGEND 8 關、sprite 與 engine 契約一致、note 三程度且 ≤ 22 字
  - LEGEND 的 sprite 影格 `${sprite}_0` 存在於 assets/sprites.json
通過後把題庫匯出為 tools/out/bank_v2.json（撈取工具更新題庫用）。
用法：PYTHONUTF8=1 python tools/check_bank.py   → 輸出 PASS／FAIL
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "js" / "content.js"
SPRITES = ROOT / "assets" / "sprites.json"
OUT = ROOT / "tools" / "out" / "bank_v2.json"
GRADES = ("elem", "junior", "senior")
PREFIX = {"elem": "E", "junior": "J", "senior": "S"}
FORBIDDEN = ("方向盤", "煞車")
LEGEND_PLAN = [
    {"collect": ["item_kelp"], "bonus": ["item_trash"], "avoid": ["haz_wave"]},
    {"collect": ["item_powder"], "avoid": ["haz_fisheye"]},
    {"collect": ["item_h2o", "item_powder"], "avoid": ["haz_bubble"]},
    {"collect": ["item_ca"], "avoid": ["haz_mg", "haz_vapor"]},
    {"collect": ["item_ca"], "avoid": ["haz_na", "haz_high"]},
    {"collect": ["item_drop"], "avoid": ["haz_tail", "haz_flat"]},
    {"collect": ["item_bead"], "bonus": ["item_hard"], "avoid": ["haz_burst"]},
    {"collect": ["item_cell", "item_ink", "item_filter", "item_pack"], "avoid": ["haz_bottle"]},
]


# ---- 迷你 JS 字面值解析器（字串、數字、true/false/null、陣列、物件、未加引號的鍵、註解、尾逗號）----
class JSParser:
    def __init__(self, s, i=0):
        self.s, self.i = s, i

    def ws(self):
        s = self.s
        while self.i < len(s):
            c = s[self.i]
            if c in " \t\r\n":
                self.i += 1
            elif s.startswith("//", self.i):
                self.i = s.index("\n", self.i) if "\n" in s[self.i:] else len(s)
            elif s.startswith("/*", self.i):
                self.i = s.index("*/", self.i) + 2
            else:
                break

    def err(self, msg):
        line = self.s.count("\n", 0, self.i) + 1
        raise SyntaxError(f"content.js 第 {line} 行：{msg}")

    def value(self):
        self.ws()
        c = self.s[self.i]
        if c == "{":
            return self.obj()
        if c == "[":
            return self.arr()
        if c in "\"'`":
            return self.string()
        m = re.compile(r"-?\d+(\.\d+)?").match(self.s, self.i)
        if m:
            self.i = m.end()
            return float(m.group()) if m.group(1) else int(m.group())
        for kw, v in (("true", True), ("false", False), ("null", None)):
            if self.s.startswith(kw, self.i):
                self.i += len(kw)
                return v
        self.err(f"無法解析的值 {self.s[self.i:self.i + 20]!r}")

    def string(self):
        q = self.s[self.i]
        self.i += 1
        out = []
        while True:
            if self.i >= len(self.s):
                self.err("字串未結束")
            c = self.s[self.i]
            if c == "\\":
                nxt = self.s[self.i + 1]
                out.append({"n": "\n", "t": "\t"}.get(nxt, nxt))
                self.i += 2
                continue
            if c == "\n" and q != "`":
                self.err("字串內換行（引號未成對）")
            if c == q:
                self.i += 1
                return "".join(out)
            if q == "`" and self.s.startswith("${", self.i):
                self.err("樣板字串含 ${}，無法靜態解析")
            out.append(c)
            self.i += 1

    def key(self):
        self.ws()
        if self.s[self.i] in "\"'":
            return self.string()
        m = re.compile(r"[A-Za-z_$一-鿿][\w$一-鿿]*").match(self.s, self.i)
        if not m:
            self.err("物件鍵無效")
        self.i = m.end()
        return m.group()

    def expect(self, ch):
        self.ws()
        if self.s[self.i] != ch:
            self.err(f"預期 {ch!r}，實際 {self.s[self.i]!r}")
        self.i += 1

    def obj(self):
        self.expect("{")
        d = {}
        while True:
            self.ws()
            if self.s[self.i] == "}":
                self.i += 1
                return d
            k = self.key()
            self.expect(":")
            d[k] = self.value()
            self.ws()
            if self.s[self.i] == ",":
                self.i += 1
            elif self.s[self.i] != "}":
                self.err("物件元素之間缺逗號")

    def arr(self):
        self.expect("[")
        a = []
        while True:
            self.ws()
            if self.s[self.i] == "]":
                self.i += 1
                return a
            a.append(self.value())
            self.ws()
            if self.s[self.i] == ",":
                self.i += 1
            elif self.s[self.i] != "]":
                self.err("陣列元素之間缺逗號")


def load_exports(src):
    exports = {}
    for m in re.finditer(r"^export const (\w+) = ", src, re.M):
        p = JSParser(src, m.end())
        exports[m.group(1)] = p.value()
        p.ws()
        if src[p.i] != ";":
            p.err(f"{m.group(1)} 結尾缺分號")
    return exports


def graded_ok(v):
    return isinstance(v, dict) and all(isinstance(v.get(g), str) and v[g].strip() for g in GRADES)


def main():
    src = CONTENT.read_text(encoding="utf-8")
    errs, warns = [], []
    try:
        ex = load_exports(src)
    except SyntaxError as e:
        print("  ✗", e)
        print("FAIL")
        return 1

    for w in FORBIDDEN:
        if w in src:
            errs.append(f"content.js 含禁用詞「{w}」")

    for k in ("CREDIT", "VERSION", "TITLE", "TITLE_EN", "STORE_KEY", "GRADE_LABEL", "GRADE_DESC", "ROLES", "INTRO",
              "CONTROL_HELP", "LEGEND", "LEVELS", "MATES", "SAFETY", "ENDING", "FACETS", "FACET_NAMES", "BANK"):
        if k not in ex:
            errs.append(f"缺少匯出 {k}")
    if not str(ex.get("VERSION") or "").startswith("2.0."):
        errs.append(f"VERSION 應為 2.0.x，實際 {ex.get('VERSION')!r}")
    if ex.get("GRADE_LABEL") != {"elem": "初階", "junior": "中階", "senior": "高階"}:
        errs.append("GRADE_LABEL 與契約不符")
    if ex.get("GRADE_DESC") != {"elem": "國小程度", "junior": "國中・高中程度", "senior": "大學・研究所程度"}:
        errs.append("GRADE_DESC 與契約不符")
    if ex.get("ROLES") != ["國小學生", "國中學生", "高中職學生", "大學生", "研究生", "教師", "一般民眾"]:
        errs.append("ROLES 與契約不符")
    for i, line in enumerate(ex.get("INTRO", [])):
        if not (isinstance(line, str) or graded_ok(line)):
            errs.append(f"INTRO[{i}] 須為字串或三程度物件")

    # LEVELS
    levels = ex.get("LEVELS", [])
    if len(levels) != 8:
        errs.append(f"LEVELS 應 8 關，實際 {len(levels)}")
    for n, lv in enumerate(levels, 1):
        for j, t in enumerate(lv.get("intro", [])):
            if isinstance(t, dict) and not graded_ok(t):
                errs.append(f"LEVELS 關 {n} intro[{j}] 缺三程度")
        if not graded_ok(lv.get("learn")):
            errs.append(f"LEVELS 關 {n} learn 缺三程度")
    if "繞圈" in json.dumps(levels[1] if len(levels) > 1 else {}, ensure_ascii=False):
        errs.append("LEVELS 第 2 關仍要求繞圈")

    # LEGEND
    legend = ex.get("LEGEND", [])
    frames = set((json.loads(SPRITES.read_text(encoding="utf-8")).get("frames") or {}).keys())
    if len(legend) != 8:
        errs.append(f"LEGEND 應 8 關，實際 {len(legend)}")
    for n, (lg, plan) in enumerate(zip(legend, LEGEND_PLAN), 1):
        for kind in ("collect", "bonus", "avoid"):
            got = [it.get("sprite") for it in lg.get(kind, [])]
            if got != plan.get(kind, []):
                errs.append(f"LEGEND 關 {n} {kind} sprite {got} ≠ 契約 {plan.get(kind, [])}")
            for it in lg.get(kind, []):
                if f"{it.get('sprite')}_0" not in frames:
                    errs.append(f"LEGEND 關 {n} sprite {it.get('sprite')}_0 不在 sprites.json")
                if not it.get("name"):
                    errs.append(f"LEGEND 關 {n} {it.get('sprite')} 缺 name")
                if not graded_ok(it.get("note")):
                    errs.append(f"LEGEND 關 {n} {it.get('sprite')} note 缺三程度")
                else:
                    for g in GRADES:
                        if len(it["note"][g]) > 22:
                            errs.append(f"LEGEND 關 {n} {it['sprite']} note[{g}] {len(it['note'][g])} 字 > 22")
    if len(legend) >= 6 and "3 cm" not in legend[5]["collect"][0].get("name", ""):
        errs.append("LEGEND 關 6 液滴名稱須含「3 cm」")

    # BANK
    bank = ex.get("BANK", {})
    for g in GRADES:
        qs = bank.get(g, [])
        if len(qs) != 10:
            errs.append(f"{g} 題數 {len(qs)}，應 10")
        for k, q in enumerate(qs, 1):
            qid = q.get("id")
            if qid != f"{PREFIX[g]}{k}":
                errs.append(f"{g} 第 {k} 題題號 {qid}，應 {PREFIX[g]}{k}")
            opts = q.get("options") or []
            if len(opts) != 4 or len(set(opts)) != 4 or not all(isinstance(o, str) and o.strip() for o in opts):
                errs.append(f"{g} {qid} 需四個不重複且非空的選項")
            if q.get("answer") != 0:
                errs.append(f"{g} {qid} answer 須為 0")
            if not str(q.get("explain", "")).strip():
                errs.append(f"{g} {qid} explain 為空")
            if not str(q.get("q", "")).strip():
                errs.append(f"{g} {qid} 題幹為空")
            if q.get("facet") not in ("知識", "態度", "行動", "探究"):
                errs.append(f"{g} {qid} 面向 {q.get('facet')} 無效")
            if len(opts) == 4:
                lens = [len(o) for o in opts]
                if lens[0] > max(lens[1:]) + 3:
                    warns.append(f"{g} {qid} 正解比其他選項長 {lens[0] - max(lens[1:])} 字")
        pre = [q for q in qs if q.get("pre")]
        if sorted(q.get("facet") for q in pre) != sorted(["知識", "探究", "態度"]):
            errs.append(f"{g} 前測應恰 3 題（知識、探究、態度各 1），實際 {[q.get('facet') for q in pre]}")
        act = [q for q in qs if not q.get("pre") and q.get("facet") == "行動"]
        if len(act) < 2:
            errs.append(f"{g} 非前測行動題 {len(act)} 題，應 ≥ 2")
        if {q.get("facet") for q in qs} != {"知識", "態度", "行動", "探究"}:
            errs.append(f"{g} 四個面向未全部出現")

    n = sum(len(bank.get(g, [])) for g in GRADES)
    print(f"讀取方式：python 解析器；匯出 {len(ex)} 項；題庫 {n} 題")
    for g in GRADES:
        print(f"  {g}: " + " ".join(f"{q.get('id')}{q.get('facet')}{'*' if q.get('pre') else ''}" for q in bank.get(g, [])))
    for w in warns:
        print("  ⚠", w)
    if errs:
        for e in errs:
            print("  ✗", e)
        print("FAIL")
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    snap = {"version": ex["VERSION"], "grades": list(GRADES),
            "bank": {g: [{"id": q["id"], "facet": q["facet"], "pre": bool(q.get("pre")), "q": q["q"],
                          "options": q["options"], "answer": q["answer"], "explain": q["explain"]} for q in bank[g]]
                     for g in GRADES}}
    OUT.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已匯出 {OUT.relative_to(ROOT)}")
    print("PASS（三程度各 10 題、前測配置、行動題、四選項、answer=0、explain、禁用詞、LEVELS／LEGEND 結構）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
