# -*- coding: utf-8 -*-
"""晶球護衛隊：題庫逐字比對。

讀取 js/content.js 的 BANK（用 node 匯入 ES module；沒有 node 時改用 Python 解析物件字面值），
與 SPEC_COMMON 題庫（下方 EXPECTED，由規格逐字轉出）逐字比對：題號、面向、pre、題目、四個選項、answer=0、說明。
也可用 --spec <SPEC_COMMON.md> 直接重新解析規格比對。
另檢查：題號符合中繼 ID_RE=/^[EJ](10|[1-9])$/、前測各 3 題、面向配置、行動題至少 1 題可供後測抽題。
用法：PYTHONUTF8=1 python tools/check_bank.py [--spec 路徑]   → 輸出 PASS／FAIL
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "js" / "content.js"
EXPECTED = json.loads(r"""{
 "elem": [
  {
   "id": "E1",
   "facet": "知識",
   "pre": true,
   "q": "海藻酸鈉是從哪裡來的？",
   "options": [
    "海裡的褐藻（像海帶）",
    "牛奶",
    "石油",
    "樹葉"
   ],
   "answer": 0,
   "explain": "海藻酸鈉是褐藻細胞壁裡的多醣長鏈。"
  },
  {
   "id": "E2",
   "facet": "探究",
   "pre": true,
   "q": "想知道「泡越久，球會不會越硬」，最好的做法是？",
   "options": [
    "泡不同的時間各做一顆，再捏捏看比較",
    "直接猜一個答案",
    "問同學覺得呢",
    "只做一顆就下結論"
   ],
   "answer": 0,
   "explain": "改變一個條件、其他不變，再比較結果，這就是實驗。"
  },
  {
   "id": "E3",
   "facet": "態度",
   "pre": true,
   "q": "做出來的晶球很漂亮，可以吃嗎？",
   "options": [
    "不可以，這是實驗品不能吃",
    "可以，看起來像魚子醬",
    "洗一洗就可以吃",
    "只吃一顆沒關係"
   ],
   "answer": 0,
   "explain": "實驗室的藥品和杯子都不是食品級，絕對不能吃。"
  },
  {
   "id": "E4",
   "facet": "知識",
   "pre": false,
   "q": "紅色水滴進藍色水，是誰把海藻長鏈扣在一起變成一層皮？",
   "options": [
    "帶正電的鈣離子 Ca²⁺",
    "水分子",
    "紅色色素",
    "空氣"
   ],
   "answer": 0,
   "explain": "鈣離子像手銬，一次扣住兩條海藻酸長鏈。"
  },
  {
   "id": "E5",
   "facet": "知識",
   "pre": false,
   "q": "為什麼液滴落下時會變成圓球？",
   "options": [
    "表面張力把液滴收成表面最小的形狀",
    "因為紅色水比較重",
    "因為杯子是圓的",
    "因為鈣離子推它"
   ],
   "answer": 0,
   "explain": "表面張力讓液滴縮成球，球是表面積最小的形狀。"
  },
  {
   "id": "E6",
   "facet": "行動",
   "pre": false,
   "q": "實驗做完，剩下的紅色海藻酸鈉液應該怎麼處理？",
   "options": [
    "倒進鈣液讓它變成膠，瀝乾後當一般垃圾",
    "直接倒進水槽",
    "倒在地上",
    "帶回家吃"
   ],
   "answer": 0,
   "explain": "紅液倒進排水孔會遇到硬水結膠堵塞，先讓它成膠再丟。"
  },
  {
   "id": "E7",
   "facet": "態度",
   "pre": false,
   "q": "「反著滴」把藍色水滴進紅色水，球會拖尾巴變形，這告訴我們什麼？",
   "options": [
    "誰在外面、誰在裡面很重要，順序會改變結果",
    "實驗失敗就沒有意義",
    "鈣離子壞掉了",
    "紅色水有毒"
   ],
   "answer": 0,
   "explain": "失敗的結果也是資料，它告訴我們順序是關鍵。"
  },
  {
   "id": "E8",
   "facet": "行動",
   "pre": false,
   "q": "用過的藍色鈣液和洗球的水，應該怎麼處理？",
   "options": [
    "集中起來，加很多清水稀釋再倒掉",
    "直接倒進花圃",
    "倒進紅色水裡再倒水槽",
    "留著喝"
   ],
   "answer": 0,
   "explain": "鈣液含鈣離子和氯離子，稀釋後再排放比較安全。"
  },
  {
   "id": "E9",
   "facet": "探究",
   "pre": false,
   "q": "泡 60 秒的球一捏就爆汁，泡 180 秒的球捏不破，可以推論什麼？",
   "options": [
    "泡越久，鈣離子往裡面走越深、皮越厚",
    "球泡久了會慢慢消失",
    "時間不會影響球",
    "鈣液已經用完了"
   ],
   "answer": 0,
   "explain": "鈣離子要慢慢擴散進去，時間越長皮越厚。"
  },
  {
   "id": "E10",
   "facet": "知識",
   "pre": false,
   "q": "海藻酸鈣的這層「皮」，最像我們身體裡的什麼？",
   "options": [
    "細胞膜，會挑選東西進出",
    "骨頭",
    "頭髮",
    "牙齒"
   ],
   "answer": 0,
   "explain": "這層薄膜像細胞膜一樣是半透膜，科學家用它做人工細胞。"
  }
 ],
 "junior": [
  {
   "id": "J1",
   "facet": "知識",
   "pre": true,
   "q": "海藻酸鈉溶在水裡解離後，長鏈上帶什麼電荷？",
   "options": [
    "負電（羧基 –COO⁻）",
    "正電",
    "不帶電",
    "時正時負"
   ],
   "answer": 0,
   "explain": "羧基解離成 –COO⁻，長鏈帶負電、互相排斥而伸展，所以很黏。"
  },
  {
   "id": "J2",
   "facet": "探究",
   "pre": true,
   "q": "要驗證「膜厚和浸泡時間的開根號成正比」，應該記錄什麼？",
   "options": [
    "不同浸泡時間下的膜厚或硬度",
    "只記錄顏色深淺",
    "滴管的品牌",
    "杯子的形狀"
   ],
   "answer": 0,
   "explain": "自變項是時間，應變項是膜厚；其他條件固定。"
  },
  {
   "id": "J3",
   "facet": "態度",
   "pre": true,
   "q": "實驗室做的晶球不能食用，主要原因是？",
   "options": [
    "藥品是實驗級、器材不是食品級，安全第一",
    "因為味道不好",
    "因為老師不准",
    "因為會變色"
   ],
   "answer": 0,
   "explain": "安全守則第一條：絕對禁食。"
  },
  {
   "id": "J4",
   "facet": "知識",
   "pre": false,
   "q": "「蛋盒模型」描述的是什麼？",
   "options": [
    "Ca²⁺ 嵌在兩條海藻酸鏈的 G 嵌段之間形成交聯",
    "雞蛋在盒子裡排列",
    "鈉離子包住鈣離子",
    "色素附著在長鏈上"
   ],
   "answer": 0,
   "explain": "Grant 等人 1973 年提出的蛋盒模型：Ca²⁺ 同時與兩條鏈的羧基氧配位。"
  },
  {
   "id": "J5",
   "facet": "知識",
   "pre": false,
   "q": "正向球化時，凝膠膜為什麼由外向內生長？",
   "options": [
    "Ca²⁺ 由鈣液向液滴內擴散，先遇到最外層的海藻酸鏈",
    "海藻酸鏈會往外跑",
    "表面張力把鈣推進去",
    "色素先凝固"
   ],
   "answer": 0,
   "explain": "膠永遠長在有海藻酸的那一側，由擴散控制。"
  },
  {
   "id": "J6",
   "facet": "知識",
   "pre": false,
   "q": "反向球化（鈣液滴入海藻酸鈉浴）常拖尾或成片狀，主因是？",
   "options": [
    "浴液黏度高、密度差小，液滴難沉入而被黏滯力拉變形",
    "鈣離子太少",
    "色素不同",
    "溫度太高"
   ],
   "answer": 0,
   "explain": "連續相太黏，液滴來不及縮成球就被拉變形。"
  },
  {
   "id": "J7",
   "facet": "行動",
   "pre": false,
   "q": "用過的鈣液與洗球水（含 Ca²⁺、Cl⁻）較恰當的處理是？",
   "options": [
    "集中後以大量清水稀釋再排放",
    "直接倒入排水孔",
    "倒入土壤",
    "與紅液混合後倒入水槽"
   ],
   "answer": 0,
   "explain": "稀釋排放；紅液遇鈣會結膠，不可混倒入水槽。"
  },
  {
   "id": "J8",
   "facet": "態度",
   "pre": false,
   "q": "二次熟化後球變硬、不透明且略縮小，對材料設計的啟示是？",
   "options": [
    "交聯密度可調控力學性質與孔隙，適合做載體或支架",
    "時間越久材料越差",
    "只有美觀上的差異",
    "與應用無關"
   ],
   "answer": 0,
   "explain": "控制時間就能控制交聯密度，這是材料設計的變數。"
  },
  {
   "id": "J9",
   "facet": "探究",
   "pre": false,
   "q": "一顆 0.05 mL 液滴只需約 2.5 µmol Ca²⁺，鈣液含量遠多於此，代表成膜的限制因素是？",
   "options": [
    "Ca²⁺ 的擴散速率",
    "鈣的總量不足",
    "海藻酸鈉不夠",
    "色素濃度"
   ],
   "answer": 0,
   "explain": "計量上鈣遠遠過量，所以限制因素是擴散而不是計量。"
  },
  {
   "id": "J10",
   "facet": "行動",
   "pre": false,
   "q": "海藻酸鈣凝膠珠用於淨水的原理是？",
   "options": [
    "Ca²⁺ 與 Pb²⁺、Cu²⁺ 等重金屬離子交換而吸附",
    "凝膠珠會吃掉細菌",
    "凝膠珠會讓水蒸發",
    "凝膠珠加熱後殺菌"
   ],
   "answer": 0,
   "explain": "鉛、銅對海藻酸的親和力比鈣高，會把鈣換出來並被留在珠子裡。"
  }
 ]
}""")
FACET_PLAN = {
    "elem": ["知識", "探究", "態度", "知識", "知識", "行動", "態度", "行動", "探究", "知識"],
    "junior": ["知識", "探究", "態度", "知識", "知識", "知識", "行動", "態度", "探究", "行動"],
}


def parse_spec(path):
    src = Path(path).read_text(encoding="utf-8")
    bank = {"elem": [], "junior": []}
    for line in src.splitlines():
        m = re.match(r"^- ([EJ]\d+) (\S+?)( pre)?｜(.+?)｜(\[.+\])｜(.+)$", line)
        if not m:
            continue
        qid, facet, pre, q, opts, ex = m.groups()
        bank["elem" if qid[0] == "E" else "junior"].append(
            {"id": qid, "facet": facet, "pre": bool(pre), "q": q, "options": json.loads(opts), "answer": 0, "explain": ex})
    return bank


def load_bank():
    node = shutil.which("node")
    if node:
        js = ("import(" + json.dumps(CONTENT.as_uri()) + ").then((m) => { process.stdout.write(JSON.stringify(m.BANK)); })"
              ".catch((e) => { console.error(e); process.exit(2); });")
        out = subprocess.run([node, "-e", js], capture_output=True, timeout=60)
        if out.returncode == 0:
            return json.loads(out.stdout.decode("utf-8")), "node"
    # 後備：把 BANK 物件字面值轉成 JSON（鍵加引號、去尾逗號）
    s = CONTENT.read_text(encoding="utf-8")
    body = s[s.index("export const BANK = ") + len("export const BANK = "):]
    body = body[:body.index("\n};") + 3].rstrip(";")
    body = re.sub(r"([{,]\s*)([A-Za-z_]+)\s*:", r'\1"\2":', body)
    body = re.sub(r",(\s*[}\]])", r"\1", body)
    return json.loads(body), "python"


def main():
    args = sys.argv[1:]
    expected = EXPECTED
    if "--spec" in args:
        expected = parse_spec(args[args.index("--spec") + 1])
    bank, how = load_bank()
    errs = []
    idre = re.compile(r"^[EJ](10|[1-9])$")
    for g in ("elem", "junior"):
        got, exp = bank.get(g, []), expected[g]
        if len(got) != len(exp):
            errs.append(f"{g} 題數 {len(got)}，規格 {len(exp)}")
        for a, e in zip(got, exp):
            norm = {"id": a.get("id"), "facet": a.get("facet"), "pre": bool(a.get("pre")), "q": a.get("q"),
                    "options": a.get("options"), "answer": a.get("answer"), "explain": a.get("explain")}
            for k in e:
                if norm[k] != e[k]:
                    errs.append(f"{g} {e['id']} 欄位 {k} 不一致：\n    遊戲＝{norm[k]!r}\n    規格＝{e[k]!r}")
            if not idre.match(str(a.get("id"))):
                errs.append(f"{g} 題號 {a.get('id')} 不符 ID_RE")
            if len(a.get("options") or []) != 4:
                errs.append(f"{g} {a.get('id')} 選項數不是 4")
        if [q.get("facet") for q in got] != FACET_PLAN[g]:
            errs.append(f"{g} 面向配置與既有遊戲不同")
        if sum(1 for q in got if q.get("pre")) != 3:
            errs.append(f"{g} 前測不是 3 題")
        if not [q for q in got if not q.get("pre") and q.get("facet") == "行動"]:
            errs.append(f"{g} 沒有可抽的行動題")
    n = sum(len(bank.get(g, [])) for g in ("elem", "junior"))
    print(f"讀取方式：{how}；遊戲題庫 {n} 題；比對來源：{'SPEC 檔' if expected is not EXPECTED else '內建規格'}")
    if errs:
        for e in errs:
            print("  ✗", e)
        print("FAIL")
        return 1
    print("PASS（20 題逐字一致：題號、面向、前測旗標、題目、選項、正解索引 0、說明）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
