# -*- coding: utf-8 -*-
"""fetch_feedback 單元測試：假資料只放系統暫存資料夾，不碰 GitHub 寫入。
執行：set PYTHONUTF8=1 && python test_fetch_feedback.py [--live]
--live：另以唯讀 GET 查詢 GitHub 實際 responses 筆數（下載到暫存資料夾）。
v2.0.0：涵蓋 v1／v2 混合、知識題正解計分、量表面向平均、空簡答、簡答清單、--aggregate 不互動模式。
v3.0.0：TestGame 涵蓋遊戲前後測讀取、壞型別、30 分鐘去重、sid 配對、時間篩選邊界、六工作表、
--game-export --offline、404＝0 筆（全部 mock，不連網）。
v4.0.0：TestGameV2 涵蓋 webar-game-v2（年齡／性別／單位／主角、mode=drive）讀取與壞值、v1＋v2 混合、
依活動篩選、年齡帶邊界、各工作表新欄位、依活動分組與年齡帶／性別統計、--event；題庫比對兩個遊戲。
v5.0.0：TestCaviar 涵蓋人工魚子醬題庫（逐字依規格）、依 event 選題庫、依 event 選問卷正解與題目標籤、
人工魚子醬遊戲紀錄彙整與題目對照標明活動、混合活動分段統計、下拉顯示名→代碼、設定檔記住活動；
題庫比對加 caviar/js/content.js（檔案不存在時跳過並印提示）。
v6：新增 TestCaviarSR（高階 -SR 題號對應、程度顯示、活動合併篩選、org 拆欄）；題庫另與 caviar/tools/out/bank_v2.json 全文比對。
v7：新增 TestResearch（研究用前後測 feedback/test：樣本 test_samples/research 為中繼 Code.gs v5 清理後的實際紀錄＋重複上傳／
只有前測／缺獨立前測檔；sid＋階段去重留最早、sid 配對、態度題不計分、篩選、xlsx 六工作表＋分析用 CSV、--research-export、
404＝尚無研究資料、只下載到 test_json；題庫與 js/content.js、js/study.js、Code.gs 一致）。
v7.1：新增 TestStudentSurvey（研究資料夾 research_dest 設定與舊 config 相容、學生版課後問卷挑選與成人版排除、
由研究紀錄／代碼推斷組別學段、統計數字、空資料、下載到 json；樣本 test_samples/student_feedback 為虛構作答）。
研究匯出另查 feedback/responses，故 v7 兩個 mock 測試改為檢查第一個／最後一個請求、補一個空清單回應；xlsx 工作表加兩張。"""
import re
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from openpyxl import load_workbook

import fetch_feedback as ff

FAKE = [  # v1 舊版回覆
    {"schema": "webar-feedback-v1", "submitted_at": "2026-10-23T10:21:05+08:00",
     "event": "SEET2026-A155-07", "role": "國中教師", "role_other": "",
     "teach_level": "國中", "played": "完整玩完", "device": "iPhone",
     "q1_clear": 5, "q2_fun": 4, "q3_easy": 3, "q4_mechanism": 5,
     "q5_feedback_useful": 4, "q6_use_in_class": 5,
     "best_part": "補 Mg²⁺ 的動畫", "suggest": "=HYPERLINK(\"x\")", "fit_level": "國中",
     "contact_ok": "願意", "contact": "", "ua": "Mozilla/5.0 (iPhone)"},
    {"schema": "webar-feedback-v1", "submitted_at": "2026-10-23T11:02:44+08:00",
     "event": "SEET2026-A155-07", "role": "其他", "role_other": "家長",
     "teach_level": "不適用", "played": "只看示範", "device": "Android",
     "q1_clear": 4, "q2_fun": "5", "q3_easy": 2, "q4_mechanism": 4,
     "q5_feedback_useful": 9, "q6_use_in_class": 3,
     "best_part": "", "suggest": "字可以大一點", "fit_level": "皆可",
     "contact_ok": "不願意", "ua": "Mozilla/5.0 (Linux; Android)"},
]


def v2(**kw):
    d = {"schema": "webar-feedback-v2", "submitted_at": "2026-10-31T10:00:00+08:00",
         "event": "SEET2026-A155-07", "k_open": "", "a_open": "", "i_open": "", "s_open": "",
         "ua": "Mozilla/5.0 (v2)"}
    d.update(kw)
    return d


V2 = [
    # 三題全對；有兩則簡答（其一為公式注入）
    v2(submitted_at="2026-10-31T10:00:00+08:00", k1="B", k2="C", k3="A", k_open="粒徑越小表面積越大",
       a1=5, a2=4, a3=3, i1=4, i2=4, i3=4, i_open="=cmd|' /C calc'!A0", s1=5, s2=5, s3=5),
    # 答對 1 題（k3 小寫 d 視為 D）；a2=9 超界剔除、a1 為字串；全部簡答空白
    v2(submitted_at="2026-10-31T10:05:00+08:00", k1="A", k2="C", k3="d",
       a1="3", a2=9, a3=1, i1=2, i2=2, i3=2, s1=1, s2=2, s3=3),
    # k2 漏答（不列入 k2 作答數）；答對 2 題
    v2(submitted_at="2026-10-31T10:10:00+08:00", k1="B", k2="", k3="A",
       a1=4, a2=4, a3=2, i1=3, i2=3, i3=3, s1=4, s2=4, s3=4, s_open="遠紅外真的會變強嗎？"),
]


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dest = Path(self.tmp.name)
        j = self.dest / "json"
        j.mkdir()
        files = {"20261023-102105_abc123.json": FAKE[0], "20261023-110244_def456.json": FAKE[1],
                 "20261031-100000_v2aaaa.json": V2[0], "20261031-100500_v2bbbb.json": V2[1],
                 "20261031-101000_v2cccc.json": V2[2]}
        for name, obj in files.items():
            (j / name).write_text(json.dumps(obj, ensure_ascii=False), "utf-8")
        (j / "20261031-120000_broken.json").write_text("{not json", "utf-8")
        self.logs = []

    def tearDown(self):
        self.tmp.cleanup()

    def test_answer_key_not_in_public_form_shape(self):
        self.assertEqual(ff.ANSWER_KEY, {"k1": "B", "k2": "C", "k3": "A"})
        self.assertEqual(len(ff.LIKERT_V2), 9)
        self.assertEqual([k for k, _ in ff.OPENS_V2], ["k_open", "a_open", "i_open", "s_open"])

    def test_load_mixed_versions(self):
        rows = ff.load_records(self.dest / "json", log=self.logs.append)
        self.assertEqual(len(rows), 5)                            # 壞檔被略過
        self.assertTrue(any("壞檔" in m for m in self.logs))
        self.assertEqual([r["ver"] for r in rows], ["v1", "v1", "v2", "v2", "v2"])
        r1, r3, r4, r5 = rows[0], rows[2], rows[3], rows[4]
        # v1 列：v2 欄位全空、v1 原欄位保留
        self.assertEqual((r1["k1"], r1["a1"], r1["k_score"], r1["k_open"]), ("", "", "", ""))
        self.assertEqual((r1["role"], r1["q1_clear"], r1["best_part"]), ("國中教師", 5, "補 Mg²⁺ 的動畫"))
        # v2 列：v1 欄位全空
        self.assertEqual((r3["role"], r3["q1_clear"], r3["contact"]), ("", "", ""))
        # 正解計分
        self.assertEqual((r3["k1_ok"], r3["k2_ok"], r3["k3_ok"], r3["k_score"]), (1, 1, 1, 3))
        self.assertEqual((r4["k1_ok"], r4["k2_ok"], r4["k3"], r4["k3_ok"], r4["k_score"]), (0, 1, "D", 0, 1))
        self.assertEqual((r5["k2"], r5["k2_ok"], r5["k_score"]), ("", "", 2))
        # 量表轉數字、超界剔除；空簡答為空字串
        self.assertEqual((r4["a1"], r4["a2"]), (3, ""))
        self.assertEqual((r4["k_open"], r4["a_open"], r4["i_open"], r4["s_open"]), ("", "", "", ""))

    def test_stats(self):
        rows = ff.load_records(self.dest / "json", log=self.logs.append)
        st = ff.compute_stats(rows)
        self.assertEqual((st["total"], st["n_v2"], st["n_v1"]), (5, 3, 2))
        kn = st["knowledge"]
        self.assertEqual((kn["k1"]["n"], kn["k1"]["correct"], kn["k1"]["rate"]), (3, 2, 0.6667))
        self.assertEqual((kn["k2"]["n"], kn["k2"]["correct"], kn["k2"]["rate"]), (2, 2, 1.0))
        self.assertEqual((kn["k3"]["n"], kn["k3"]["correct"]), (3, 2))
        self.assertEqual(kn["k1"]["dist"], {"A": 1, "B": 2, "C": 0, "D": 0})
        self.assertEqual(st["k_score_mean"], (2.0, 3))
        self.assertEqual(st["likert"]["a1"], (4.0, 3))
        self.assertEqual(st["likert"]["a2"], (4.0, 2))           # 9 超界剔除
        self.assertEqual(st["likert"]["a3"], (2.0, 3))
        self.assertEqual(st["facets"]["a"], (3.25, 8))
        self.assertEqual(st["facets"]["i"], (3.0, 9))
        self.assertEqual(st["facets"]["s"], (3.67, 9))
        # v1 舊統計仍保留
        self.assertEqual(st["v1_means"]["q1_clear"], (4.5, 2))
        self.assertEqual(st["v1_means"]["q2_fun"], (4.5, 2))     # "5" 字串轉數字
        self.assertEqual(st["v1_means"]["q5_feedback_useful"], (4.0, 1))
        self.assertEqual(st["roles"]["國中教師"], 1)
        # 簡答清單：v2 三則（空白不列）＋ v1 三則
        v2_opens = [o for o in st["opens"] if o[2] == "v2"]
        self.assertEqual(len(v2_opens), 3)
        self.assertEqual({o[3] for o in v2_opens}, {"環境知識", "行動意向", "科學探究"})
        self.assertEqual(len([o for o in st["opens"] if o[2] == "v1"]), 3)

    def test_outputs(self):
        n, st = ff.aggregate(self.dest, log=self.logs.append)
        self.assertEqual(n, 5)
        # CSV：UTF-8 BOM、欄位順序（v2 為主、v1 在右）、公式注入防護
        raw = (self.dest / ff.CSV_NAME).read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        rows = list(csv.reader(raw.decode("utf-8-sig").splitlines()))
        keys = [h.split("(")[-1][:-1] for h in rows[0]]
        self.assertEqual(keys, [k for k, _ in ff.FIELDS])
        self.assertEqual(rows[0][0], "檔名(file)")
        self.assertLess(keys.index("s_open"), keys.index("role"))
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[1][keys.index("ver")], "v1")
        self.assertEqual(rows[1][keys.index("k1")], "")
        self.assertTrue(rows[1][keys.index("suggest")].startswith("'="))
        self.assertTrue(rows[3][keys.index("i_open")].startswith("'="))
        self.assertEqual(rows[3][keys.index("k_score")], "3")
        # XLSX：三個工作表、統計內容、公式以文字保存
        wb = load_workbook(self.dest / ff.XLSX_NAME)
        self.assertEqual(wb.sheetnames, ["回覆", "統計", "簡答"])
        ws = wb["回覆"]
        self.assertEqual(ws.max_row, 6)
        self.assertEqual(ws.cell(4, keys.index("i_open") + 1).data_type, "s")
        sv = {r[0].value: [c.value for c in r[1:]] for r in wb["統計"].iter_rows() if r[0].value}
        self.assertEqual(sv["總回覆數"][0], 5)
        self.assertEqual(sv["v2 回覆數（四面向問卷）"][0], 3)
        self.assertEqual(sv["K1 微米化的主要好處"][:4], ["B", 3, 2, 0.6667])
        self.assertEqual(sv["【環境態度】面向平均"][:2], [3.25, 8])
        self.assertEqual(sv["【科學探究】面向平均"][0], 3.67)
        self.assertEqual(sv["平均答對題數（0–3）"][0], 2.0)
        self.assertEqual(sv["v1 Q1 說明清楚易懂"][0], 4.5)
        op = wb["簡答"]
        self.assertEqual(op.max_row, 1 + 6)
        self.assertEqual(op.cell(1, 6).value, "內容")

    def test_empty(self):
        with tempfile.TemporaryDirectory() as d:
            n, st = ff.aggregate(Path(d))
            self.assertEqual(n, 0)
            self.assertEqual(st["knowledge"]["k1"]["rate"], None)
            self.assertTrue((Path(d) / ff.XLSX_NAME).exists())

    def test_only_v1(self):
        with tempfile.TemporaryDirectory() as d:
            j = Path(d) / "json"
            j.mkdir()
            (j / "a.json").write_text(json.dumps(FAKE[0], ensure_ascii=False), "utf-8")
            n, st = ff.aggregate(Path(d))
            self.assertEqual((n, st["n_v2"], st["n_v1"]), (1, 0, 1))
            self.assertEqual(st["facets"]["a"], (None, 0))

    def test_cli_aggregate(self):
        code = ff.cli_aggregate(self.dest)
        self.assertEqual(code, 0)
        txt = (self.dest / ff.SUMMARY_NAME).read_text("utf-8")
        self.assertIn("總回覆 5 筆（v2 3、v1 2）", txt)
        self.assertIn("K1 2/3", txt)

    def test_remote_404_is_zero(self):
        r = mock.Mock(status_code=404, headers={})
        s = mock.Mock(get=mock.Mock(return_value=r))
        self.assertEqual(ff.list_remote(session=s), [])

    def test_rate_limit_message(self):
        r = mock.Mock(status_code=403, headers={"X-RateLimit-Remaining": "0",
                                                 "X-RateLimit-Reset": "1793000000"})
        s = mock.Mock(get=mock.Mock(return_value=r))
        with self.assertRaises(ff.FetchError) as cm:
            ff.list_remote(session=s)
        self.assertIn("Token", str(cm.exception))

    def test_network_error(self):
        s = mock.Mock(get=mock.Mock(side_effect=ff.requests.ConnectionError()))
        with self.assertRaises(ff.FetchError) as cm:
            ff.list_remote(session=s)
        self.assertIn("網路", str(cm.exception))

    def test_download_only_new_and_bad(self):
        listing = mock.Mock(status_code=200, headers={})
        listing.json.return_value = [
            {"type": "file", "name": ".gitkeep", "download_url": "u0"},
            {"type": "file", "name": "20261023-102105_abc123.json", "download_url": "u1"},
            {"type": "file", "name": "20261101-090000_zzz999.json", "download_url": "u2"},
            {"type": "file", "name": "20261101-090001_bad000.json", "download_url": "u3"},
            {"type": "file", "name": "..\\evil.json", "download_url": "u4"},
        ]
        good = mock.Mock(status_code=200, headers={},
                         content=json.dumps(V2[0], ensure_ascii=False).encode("utf-8"))
        bad = mock.Mock(status_code=200, headers={}, content=b"<html>")
        s = mock.Mock()
        s.get.side_effect = lambda url, **kw: {"u2": good, "u3": bad}.get(url, listing)
        remote = ff.list_remote(session=s)
        self.assertEqual(len(remote), 4)                 # .gitkeep 排除
        ok, nbad = ff.download_new(self.dest, remote, log=self.logs.append, session=s)
        self.assertEqual((ok, nbad), (1, 1))             # 已有的不重下、壞檔另存、不合規略過
        self.assertTrue((self.dest / "json" / "壞檔" / "20261101-090001_bad000.json").exists())
        self.assertFalse((self.dest / "evil.json").exists())
        ok2, _ = ff.download_new(self.dest, remote, session=s)
        self.assertEqual(ok2, 0)                          # 第二次不重下

    def test_no_token_written(self):
        with mock.patch.object(ff, "app_dir", return_value=self.dest):
            ff.save_config("D:\\x")
            self.assertEqual(json.loads((self.dest / "config.json").read_text("utf-8")), {"dest": "D:\\x"})


# ---------------------------------------------------------------- v3 遊戲前後測
def ans(*items):
    return [{"id": i, "facet": ff.QUESTION_INDEX[i]["facet"], "pick": p, "correct": p == 0}
            for i, p in items]


def game(phase, at, pid, sid, **kw):
    d = {"schema": "webar-game-v1", "submitted_at": at, "event": "SEET2026-A155-07",
         "pid": pid, "sid": sid, "phase": phase, "grade": "elem", "mode": "ar",
         "client_time": "", "pre": ans(("E1", 0), ("E2", 2), ("E3", 0)), "post": [],
         "preScore": 2, "postSame3": "", "postScore": "", "stars": [], "totalStars": "",
         "facets": {}, "commit": "", "ua": "Mozilla/5.0 (game)"}
    if phase == "post":
        d.update(post=ans(("E1", 0), ("E2", 0), ("E3", 0), ("E4", 1), ("E6", 0)),
                 postSame3=3, postScore=4, stars=[3, 2, 3, 1, 3, 3, 2, 3], totalStars=20,
                 facets={"知識": 67, "態度": 100, "行動": 100, "探究": 100}, commit="做好垃圾分類回收")
    d.update(kw)
    return d


GAME_FILES = {
    "20261031-100000_pre_aaaaaa.json": game("pre", "2026-10-31T10:00:00+08:00", "p1", "s1"),
    "20261031-100400_pre_bbbbbb.json": game("pre", "2026-10-31T10:04:00+08:00", "p1", "s2"),  # 5 分鐘內重複
    "20261031-102000_post_cccccc.json": game("post", "2026-10-31T10:20:00+08:00", "p1", "s1",
                                             commit="=HYPERLINK(\"x\")"),
    "20261031-100000_pre_dddddd.json": game("pre", "2026-10-31T10:00:00+08:00", "p2", "s3",
                                            grade="junior", mode="play",
                                            pre=ans(("J1", 0), ("J2", 0), ("J3", 1)), preScore=2),
    "20261031-104000_pre_eeeeee.json": game("pre", "2026-10-31T10:40:00+08:00", "p2", "s4",
                                            grade="junior", mode="play",
                                            pre=ans(("J1", 1), ("J2", 1), ("J3", 1)), preScore=0),  # 相隔 40 分鐘
    "20261031-105500_post_ffffff.json": game("post", "2026-10-31T10:55:00+08:00", "p2", "s4",
                                             grade="junior", mode="play",
                                             pre=ans(("J1", 1), ("J2", 1), ("J3", 1)),
                                             post=ans(("J1", 0), ("J2", 0), ("J3", 1), ("J7", 0), ("J5", 0))),
    "20261031-110000_pre_gggggg.json": game("pre", "2026-10-31T11:00:00+08:00", "", "s5"),  # 缺 pid
    "20261031-111000_post_hhhhhh.json": game("post", "2026-10-31T03:10:00Z", "p4", "s6"),   # 只有後測、UTC
    # 壞型別：pid 為數字、phase 缺（依檔名）、pre 不是陣列、時間亂碼、stars/facets 型別錯
    "20261031-112000_pre_iiiiii.json": {"schema": "webar-game-v1", "submitted_at": "昨天下午",
                                        "pid": 123, "sid": "s7", "grade": "高中", "mode": None,
                                        "pre": "notalist", "post": None, "preScore": True,
                                        "stars": "x", "facets": [], "commit": 5, "ua": None},
}


GAME_REPO = Path(r"D:\02-aitt_claude_agent\serpentine-webar")
GAME_CONTENT_JS = [GAME_REPO / "js" / "content.js",                       # 舊遊戲（WebAR）
                   GAME_REPO / "hualien-harmony" / "js" / "content.js"]   # 新遊戲（墨玉護衛隊）
CAVIAR_CONTENT_JS = GAME_REPO / "caviar" / "js" / "content.js"             # 11/27 人工魚子醬（2.0）
BANK_V2_JSON = GAME_REPO / "caviar" / "tools" / "out" / "bank_v2.json"       # v6 題庫唯一來源


def check_bank_in_js(tc, src: str, index: dict) -> None:
    """content.js 逐題比對：以題號切出區塊，區塊內須有逐字相同的題目、四個選項（依原始順序）、正解 0。"""
    pos = []
    for qid in index:
        m = re.search(r"""\bid["']?\s*:\s*["']%s["']""" % qid, src)
        tc.assertIsNotNone(m, f"content.js 找不到題號 {qid}")
        pos.append((m.start(), qid))
    pos.sort()
    for i, (start, qid) in enumerate(pos):
        end = pos[i + 1][0] if i + 1 < len(pos) else len(src)
        blk = src[start:end]
        q = index[qid]
        with tc.subTest(qid=qid):
            tc.assertIn(q["q"], blk)
            at = -1
            for o in q["options"]:
                k = blk.find(f'"{o}"', at + 1)
                tc.assertGreater(k, at, f"{qid} 選項不符或順序不同：{o}")
                at = k
            tc.assertRegex(blk, r"""answer["']?\s*:\s*0\b""")
            tc.assertIn(q["facet"], blk)


class TestGame(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dest = Path(self.tmp.name)
        self.jdir = self.dest / ff.GAME_JSON_SUBDIR
        self.jdir.mkdir()
        for name, obj in GAME_FILES.items():
            (self.jdir / name).write_text(json.dumps(obj, ensure_ascii=False), "utf-8")
        (self.jdir / "20261031-120000_pre_broken.json").write_text("{not json", "utf-8")
        self.logs = []

    def tearDown(self):
        self.tmp.cleanup()

    def load(self):
        return ff.load_game_records(self.jdir, log=self.logs.append)

    def test_bank(self):
        self.assertEqual(len(ff.QUESTION_BANK["elem"]), 10)
        self.assertEqual(len(ff.QUESTION_BANK["junior"]), 10)
        self.assertEqual(ff.PRE_IDS, {"E1", "E2", "E3", "J1", "J2", "J3"})
        self.assertTrue(all(q["answer"] == 0 and len(q["options"]) == 4 for q in ff.QUESTION_INDEX.values()))

    @unittest.skipUnless(any(p.exists() for p in GAME_CONTENT_JS), "本機無遊戲 repo")
    def test_bank_matches_game_repo(self):
        checked = 0
        for path in GAME_CONTENT_JS:                       # 新遊戲 content.js 尚未建立時只跳過該檔
            if not path.exists():
                continue
            checked += 1
            src = path.read_text("utf-8")
            with self.subTest(path=str(path)):
                for q in ff.QUESTION_INDEX.values():
                    self.assertIn(f'id: "{q["id"]}"', src)
                    self.assertIn(q["q"], src)
                    for o in q["options"]:
                        self.assertIn(f'"{o}"', src)
        self.assertGreaterEqual(checked, 1)
        # v5：人工魚子醬 caviar/js/content.js（另一代理同時製作中；尚未建立時跳過並印提示）
        if not CAVIAR_CONTENT_JS.exists():
            print(f"\n  [提示] {CAVIAR_CONTENT_JS} 尚未建立，人工魚子醬題庫比對略過；建立後請重跑測試。")
            return
        js = CAVIAR_CONTENT_JS.read_text("utf-8")
        check_bank_in_js(self, js, ff.QUESTION_INDEXES[ff.EVENT_CAVIAR])           # 初階 E1–10、中階 J1–10
        # v6 高階：索引鍵為上傳題號 J*，content.js 內為原題號 S* → 以 src_id 重新索引後比對
        sr = {q["src_id"]: q for q in ff.QUESTION_INDEXES[ff.EVENT_CAVIAR_SR].values()}
        self.assertEqual(sorted(sr, key=lambda k: int(k[1:])), [f"S{i}" for i in range(1, 11)])
        check_bank_in_js(self, js, sr)

    def test_load_and_bad_types(self):
        recs = self.load()
        self.assertEqual(len(recs), 9)                                  # 壞檔略過
        self.assertTrue(any("壞檔" in m for m in self.logs))
        bad = next(r for r in recs if r["file"].endswith("iiiiii.json"))
        self.assertIsNone(bad["submitted_at"])
        self.assertEqual((bad["pid"], bad["phase"], bad["grade"], bad["mode"]), ("123", "pre", "", ""))
        self.assertEqual((bad["pre"], bad["stars"], bad["preScore"], bad["commit"]), ([], [], "", "5"))
        self.assertEqual(bad["facets"], {f: "" for f in ff.GAME_FACETS})
        self.assertIn("無法解析", bad["note"])
        utc = next(r for r in recs if r["file"].endswith("hhhhhh.json"))
        self.assertEqual(utc["submitted_at"].strftime("%Y-%m-%d %H:%M %z"), "2026-10-31 11:10 +0800")
        first = next(r for r in recs if r["file"].endswith("aaaaaa.json"))
        self.assertEqual([a["text"] for a in first["pre"]], ["變多", "問朋友覺得對不對", "可能是能再利用的資源"])
        self.assertEqual([a["correct"] for a in first["pre"]], [1, 0, 1])

    def test_dedupe_rules(self):
        kept, dropped = ff.dedupe_records(self.load(), 30)
        self.assertEqual([r["file"] for r in dropped], ["20261031-100400_pre_bbbbbb.json"])
        self.assertEqual(dropped[0]["dup_minutes"], 4.0)
        self.assertIn("30 分鐘內重複（前測）", dropped[0]["dup_reason"])
        self.assertEqual(dropped[0]["dup_base"], "20261031-100000_pre_aaaaaa.json")
        names = {r["file"] for r in kept}
        self.assertIn("20261031-104000_pre_eeeeee.json", names)        # 相隔 40 分鐘 → 都保留
        self.assertIn("20261031-100000_pre_dddddd.json", names)
        nopid = next(r for r in kept if r["file"].endswith("gggggg.json"))
        self.assertIn("缺 pid", nopid["note"])
        self.assertEqual(len(kept), 8)

    def test_dedupe_baseline_is_last_kept(self):
        recs = [{"file": f"{i}.json", "pid": "p", "phase": "pre", "note": "",
                 "submitted_at": ff.parse_game_time(t)} for i, t in
                enumerate(["2026-10-31T10:00:00+08:00", "2026-10-31T10:20:00+08:00",
                           "2026-10-31T10:35:00+08:00", "2026-10-31T10:50:00+08:00"])]
        kept, dropped = ff.dedupe_records(recs, 30)
        self.assertEqual([r["file"] for r in kept], ["0.json", "2.json"])   # 10:35 距 10:00 ≥ 30 → 新一次
        self.assertEqual([r["file"] for r in dropped], ["1.json", "3.json"])  # 10:50 距 10:35 只 15 分

    def test_pairing(self):
        kept, _ = ff.dedupe_records(self.load(), 30)
        pairs = ff.pair_plays(kept)
        self.assertEqual(len(pairs), 6)
        by_sid = {p["sid"]: p for p in pairs}
        s1 = by_sid["s1"]
        self.assertTrue(s1["complete"])
        self.assertEqual((s1["pre_score"], s1["post_same3"], s1["post_score"], s1["gain"]), (2, 3, 4, 1))
        self.assertEqual(s1["total_stars"], 20)
        s4 = by_sid["s4"]
        self.assertEqual((s4["pre_score"], s4["post_same3"], s4["post_score"], s4["gain"]), (0, 2, 4, 2))
        self.assertIsNone(by_sid["s3"]["post_rec"])                       # 玩到一半
        self.assertIn("玩到一半", by_sid["s3"]["note"])
        s6 = by_sid["s6"]                                                 # 只有後測
        self.assertIsNone(s6["pre_rec"])
        self.assertEqual([a["id"] for a in s6["pre_answers"]], ["E1", "E2", "E3"])
        self.assertEqual(s6["pre_score"], 2)
        self.assertEqual(sum(1 for p in pairs if p["complete"]), 2)
        self.assertEqual([p["no"] for p in pairs], list(range(1, 7)))

    def test_time_filter_boundary(self):
        recs = self.load()
        tz = ff.TZ_TPE
        from datetime import datetime as dt
        r = ff.filter_by_time(recs, dt(2026, 10, 31, 10, 0), dt(2026, 10, 31, 10, 40))  # naive＝台北
        self.assertEqual(len(r), 5)                                      # 10:00 與 10:40 都含
        r = ff.filter_by_time(recs, dt(2026, 10, 31, 10, 0, 1, tzinfo=tz), dt(2026, 10, 31, 10, 39, 59, tzinfo=tz))
        self.assertEqual(len(r), 2)                                      # 10:04、10:20
        self.assertEqual(len(ff.filter_by_time(recs, None, None)), 9)     # 不限＝含時間無法解析者
        self.assertEqual(len(ff.filter_by_time(recs, dt(2026, 10, 31, 11, 5), None)), 1)  # UTC 03:10＝11:10
        end = ff.parse_user_time("2026-10-31 10:40", is_end=True)
        self.assertEqual((end.second, end.microsecond), (59, 999999))
        self.assertEqual(ff.parse_user_time("  "), None)
        with self.assertRaises(ValueError):
            ff.parse_user_time("10/31 上午")

    def test_xlsx(self):
        out = self.dest / "out" / "遊戲前後測.xlsx"
        res = ff.run_game_export(self.dest, out, None, None, 30, None, log=self.logs.append, offline=True)
        self.assertEqual((res["local"], res["in_range"], res["kept"], res["dropped"]), (9, 9, 8, 1))
        self.assertEqual((res["players"], res["plays"], res["complete"]), (4, 6, 2))
        wb = load_workbook(out)
        self.assertEqual(wb.sheetnames, ["玩家彙整", "前測", "後測", "已略過(重複)", "統計", "題目對照"])
        ws = wb["玩家彙整"]
        self.assertEqual(ws.max_row, 1 + 6)
        hdr = [c.value for c in ws[1]]
        self.assertEqual(hdr[:5], ["序號", "pid（玩家代碼）", "sid（遊玩代碼）", "版本", "模式"])
        row1 = [c.value for c in ws[2]]
        self.assertEqual(row1[1:5], ["p1", "s1", "國小", "AR"])
        self.assertEqual(row1[hdr.index("前測Q2 選項文字")], "問朋友覺得對不對")
        self.assertEqual(row1[hdr.index("進步（後測同3題−前測）")], 1)
        self.assertEqual(row1[hdr.index("八關星數")], "3,2,3,1,3,3,2,3")
        c = ws.cell(2, hdr.index("小行動承諾") + 1)
        self.assertTrue(str(c.value).startswith("'="))                    # 公式注入防護
        self.assertEqual(wb["前測"].max_row, 1 + 5)
        self.assertEqual(wb["後測"].max_row, 1 + 3)
        self.assertEqual(wb["已略過(重複)"].max_row, 1 + 1)
        self.assertEqual(wb["題目對照"].max_row, 1 + 20)
        self.assertEqual(wb["題目對照"]["F2"].value, "變多")
        sv = {r[0].value: [x.value for x in r[1:]] for r in wb["統計"].iter_rows() if r[0].value}
        self.assertEqual(sv["略過筆數（重複）"][0], 1)
        self.assertEqual(sv["完整遊玩數（有前測也有後測）"][0], 2)
        self.assertEqual(sv["國中版人數"][0], 1)
        self.assertEqual(sv["平均進步（後測同3題−前測）"][:2], [1.33, 3])
        self.assertEqual(sv["E1（前測題）"][1:5], [3, 1.0, 2, 1.0])
        self.assertEqual(ws["A2"].font.name, ff.FONT_NAME)

    def test_cli_game_export_offline(self):
        out = self.dest / "x.xlsx"
        code = ff.cli_game_export([str(self.dest), str(out), "--from", "2026-10-31 10:00",
                                   "--to", "2026-10-31 10:40", "--window", "30", "--offline"])
        self.assertEqual(code, 0)
        txt = (self.dest / ff.GAME_SUMMARY_NAME).read_text("utf-8")
        self.assertIn("區間內 5 筆", txt)
        self.assertIn("略過重複 1 筆", txt)
        self.assertTrue(out.exists())
        code = ff.cli_game_export([str(self.dest), str(out), "--from", "明天", "--offline"])
        self.assertEqual(code, 1)
        self.assertIn("時間格式錯誤", (self.dest / ff.GAME_SUMMARY_NAME).read_text("utf-8"))

    def test_remote_404_is_zero(self):
        r = mock.Mock(status_code=404, headers={})
        s = mock.Mock(get=mock.Mock(return_value=r))
        self.assertEqual(ff.list_remote(session=s, api_url=ff.GAME_API_URL), [])
        self.assertIn("feedback/game", s.get.call_args[0][0])
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "g.xlsx"
            res = ff.run_game_export(Path(d), out, None, None, 30, None, log=self.logs.append, session=s)
            self.assertEqual((res["remote"], res["new"], res["kept"], res["plays"]), (0, 0, 0, 0))
            self.assertTrue(out.exists())

    def test_download_game_to_game_json(self):
        listing = mock.Mock(status_code=200, headers={})
        listing.json.return_value = [
            {"type": "file", "name": "20261031-100000_pre_aaaaaa.json", "download_url": "u1"},  # 已有
            {"type": "file", "name": "20261101-090000_pre_zzzzzz.json", "download_url": "u2"},
            {"type": "file", "name": "20261101-090001_post_badbad.json", "download_url": "u3"},
        ]
        good = mock.Mock(status_code=200, headers={}, content=json.dumps(
            game("pre", "2026-11-01T09:00:00+08:00", "p9", "s9"), ensure_ascii=False).encode("utf-8"))
        bad = mock.Mock(status_code=200, headers={}, content=b"<html>")
        s = mock.Mock()
        s.get.side_effect = lambda url, **kw: {"u2": good, "u3": bad}.get(url, listing)
        out = self.dest / "g.xlsx"
        res = ff.run_game_export(self.dest, out, None, None, 30, None, log=self.logs.append, session=s)
        self.assertEqual((res["remote"], res["new"], res["bad"], res["local"]), (3, 1, 1, 10))
        self.assertTrue((self.jdir / "壞檔" / "20261101-090001_post_badbad.json").exists())
        self.assertFalse((self.dest / "json").exists())                   # 不碰回饋問卷資料夾
        self.assertTrue(any("game_json\\壞檔" in m for m in self.logs))

    def test_xlsx_locked(self):
        out = self.dest / "locked.xlsx"
        with mock.patch.object(ff, "write_game_xlsx", side_effect=PermissionError()):
            with self.assertRaises(ff.FetchError) as cm:
                ff.run_game_export(self.dest, out, offline=True, log=self.logs.append)
        self.assertIn("請關閉後再試", str(cm.exception))

    def test_config_game_window_no_token(self):
        with mock.patch.object(ff, "app_dir", return_value=self.dest):
            ff.save_config("D:\\x", 45)
            self.assertEqual(json.loads((self.dest / "config.json").read_text("utf-8")),
                             {"dest": "D:\\x", "game_window": 45})
            ff.save_config("D:\\y")                                       # 保留原分鐘數
            self.assertEqual(ff.load_config(), {"dest": "D:\\y", "game_window": 45})


# ---------------------------------------------------------------- v4 新遊戲（webar-game-v2）
HL = "HL-STATION-2026-1127"


def game2(phase, at, pid, sid, **kw):
    d = game(phase, at, pid, sid)
    d.update(schema="webar-game-v2", event=HL, mode="drive", age=10, gender="女", org="測試國小",
             hero="kid_f")
    keys = list(d)                                     # 依中繼 GAME_FIELDS_V2 順序排（age 在 client_time 後）
    order = ["schema", "submitted_at", "event", "pid", "sid", "phase", "grade", "mode", "client_time",
             "age", "gender", "org", "hero"]
    d = {k: d[k] for k in order + [k for k in keys if k not in order]}
    d.update(kw)
    return d


V2_GAME_FILES = {
    # 完整一局：10 歲女、國小、kid_f
    "20261127-100000_pre_v2aaaa.json": game2("pre", "2026-11-27T10:00:00+08:00", "hpid00000001", "hsid00000001"),
    "20261127-101500_post_v2bbbb.json": game2("post", "2026-11-27T10:15:00+08:00", "hpid00000001", "hsid00000001"),
    # 35 歲男、國中題、只有前測
    "20261127-103000_pre_v2cccc.json": game2("pre", "2026-11-27T10:30:00+08:00", "hpid00000002", "hsid00000002",
                                            grade="junior", age="35", gender="男", org="花蓮某公司",
                                            hero="adult_m", pre=ans(("J1", 0), ("J2", 0), ("J3", 0))),
    # 壞值：年齡 200、性別亂填、單位過長、主角過長、age 布林 → 全空白／截斷
    "20261127-110000_post_v2dddd.json": game2("post", "2026-11-27T11:00:00+08:00", "hpid00000003", "hsid00000003",
                                             age=200, gender="X", org="甲" * 80, hero="h" * 30),
    # 70 歲、不透露、單位空白
    "20261127-113000_pre_v2eeee.json": game2("pre", "2026-11-27T11:30:00+08:00", "hpid00000004", "hsid00000004",
                                            age=70, gender="不透露", org=""),
}


class TestGameV2(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dest = Path(self.tmp.name)
        self.jdir = self.dest / ff.GAME_JSON_SUBDIR
        self.jdir.mkdir()
        for name, obj in {**GAME_FILES, **V2_GAME_FILES}.items():
            (self.jdir / name).write_text(json.dumps(obj, ensure_ascii=False), "utf-8")
        self.logs = []

    def tearDown(self):
        self.tmp.cleanup()

    def load(self):
        return ff.load_game_records(self.jdir, log=self.logs.append)

    def test_constants(self):
        self.assertEqual(ff.VERSION, "7.1.0")   # v7.1.0：研究資料夾＋學生版課後問卷
        self.assertEqual(ff.GAME_SCHEMAS, ("webar-game-v1", "webar-game-v2"))
        self.assertEqual(ff.MODE_LABEL["drive"], "方向盤版")
        self.assertIn(HL, ff.EVENT_PRESETS)
        self.assertIn("SEET2026-A155-07", ff.EVENT_PRESETS)

    def test_load_v2_and_v1_blank(self):
        recs = self.load()
        self.assertEqual(len(recs), 9 + 5)
        self.assertFalse(any("v2" in m and "schema" in m for m in self.logs))   # v2 不再被警告
        by = {r["file"]: r for r in recs}
        a = by["20261127-100000_pre_v2aaaa.json"]
        self.assertEqual((a["schema"], a["event"], a["mode"], a["age"], a["gender"], a["org"], a["hero"]),
                         ("webar-game-v2", HL, "drive", 10, "女", "測試國小", "kid_f"))
        c = by["20261127-103000_pre_v2cccc.json"]
        self.assertEqual((c["age"], c["gender"], c["grade"]), (35, "男", "junior"))   # "35" 字串轉整數
        d = by["20261127-110000_post_v2dddd.json"]
        self.assertEqual((d["age"], d["gender"], len(d["org"]), len(d["hero"])), ("", "", 60, 20))
        v1 = by["20261031-100000_pre_aaaaaa.json"]
        self.assertEqual((v1["age"], v1["gender"], v1["org"], v1["hero"], v1["mode"]), ("", "", "", "", "ar"))

    def test_age_band(self):
        self.assertEqual([ff.age_band(x) for x in (3, 12, 13, 18, 19, 64, 65, 120)],
                         ["≤12 歲", "≤12 歲", "13–18 歲", "13–18 歲", "19–64 歲", "19–64 歲", "≥65 歲", "≥65 歲"])
        self.assertEqual((ff.age_band(""), ff.age_band(None), ff.age_band(True)), ("", "", ""))

    def test_event_filter(self):
        recs = self.load()
        self.assertEqual(len(ff.filter_by_event(recs, HL)), 5)
        self.assertEqual(len(ff.filter_by_event(recs, " hl-station-2026-1127 ")), 5)   # 不分大小寫
        self.assertEqual(len(ff.filter_by_event(recs, "SEET2026-A155-07")), 8)        # 缺 event 的壞型別紀錄不算
        self.assertEqual(len(ff.filter_by_event(recs, "全部")), 14)
        self.assertEqual(len(ff.filter_by_event(recs, "")), 14)
        self.assertEqual(ff.filter_by_event(recs, "不存在的活動"), [])

    def test_pairing_carries_player_fields(self):
        kept, _ = ff.dedupe_records(ff.filter_by_event(self.load(), HL), 30)
        pairs = ff.pair_plays(kept)
        self.assertEqual(len(pairs), 4)
        p1 = next(p for p in pairs if p["sid"] == "hsid00000001")
        self.assertTrue(p1["complete"])
        self.assertEqual((p1["event"], p1["age"], p1["gender"], p1["org"], p1["hero"], p1["mode"]),
                         (HL, 10, "女", "測試國小", "kid_f", "drive"))
        self.assertEqual((p1["pre_score"], p1["post_same3"], p1["gain"]), (2, 3, 1))

    def test_export_only_hl(self):
        out = self.dest / "hl.xlsx"
        res = ff.run_game_export(self.dest, out, None, None, 30, None, log=self.logs.append,
                                 offline=True, event=HL)
        self.assertEqual((res["local"], res["in_range"], res["kept"], res["plays"], res["complete"]),
                         (14, 5, 5, 4, 1))
        wb = load_workbook(out)
        self.assertEqual(wb.sheetnames, ["玩家彙整", "前測", "後測", "已略過(重複)", "統計", "題目對照"])
        ws = wb["玩家彙整"]
        hdr = [c.value for c in ws[1]]
        self.assertEqual(hdr[:14], ["序號", "pid（玩家代碼）", "sid（遊玩代碼）", "版本", "模式",
                                    "活動", "年齡", "性別", "學校／單位", "身分", "單位", "主角", "前測時間", "後測時間"])
        row = {c.value: v.value for c, v in zip(ws[1], ws[2])}
        self.assertEqual((row["模式"], row["活動"], row["年齡"], row["性別"], row["學校／單位"], row["主角"]),
                         ("方向盤版", HL, 10, "女", "測試國小", "kid_f"))
        self.assertEqual((row["身分"], row["單位"], row["版本"]), (None, "測試國小", "國小"))   # 無「｜」→身分空白
        self.assertEqual(ws.cell(2, hdr.index("前測時間") + 1).number_format, "yyyy-mm-dd hh:mm:ss")
        self.assertEqual(row["進步（後測同3題−前測）"], 1)
        for name, n in (("前測", 1 + 3), ("後測", 1 + 2)):
            sh = wb[name]
            h2 = [c.value for c in sh[1]]
            self.assertEqual(h2[:13], ["檔名", "上傳時間", "pid", "sid", "版本", "模式",
                                       "活動", "年齡", "性別", "學校／單位", "身分", "單位", "主角"])
            self.assertEqual(sh.max_row, n)
        pre = wb["前測"]
        self.assertEqual([pre.cell(2, i).value for i in range(6, 14)],
                         ["方向盤版", HL, 10, "女", "測試國小", None, "測試國小", "kid_f"])
        sv = {r[0].value: [x.value for x in r[1:]] for r in wb["統計"].iter_rows() if r[0].value}
        self.assertEqual(sv["篩選活動"][0], HL)
        self.assertEqual(sv["方向盤版模式人數"][0], 4)
        self.assertEqual(sv[HL][:4], [4, 4, 1, 2.25])              # 人數、遊玩、完整、前測平均
        self.assertNotIn("SEET2026-A155-07", sv)
        self.assertEqual(sv["年齡 ≤12 歲"][0], 1)
        self.assertEqual(sv["年齡 19–64 歲"][0], 1)
        self.assertEqual(sv["年齡 ≥65 歲"][0], 1)
        self.assertEqual(sv["年齡（未填）"][0], 1)               # 200 歲 → 空白
        self.assertEqual(sv["性別 女"][0], 1)
        self.assertEqual(sv["性別 男"][0], 1)
        self.assertEqual(sv["性別 不透露"][0], 1)
        self.assertEqual(sv["性別（未填）"][0], 1)
        self.assertEqual(sv["平均年齡"][:2], [38.33, 3])

    def test_export_all_groups_by_event(self):
        out = self.dest / "all.xlsx"
        res = ff.run_game_export(self.dest, out, None, None, 30, None, log=self.logs.append, offline=True)
        self.assertEqual((res["local"], res["in_range"], res["kept"]), (14, 14, 13))
        st = res["stats"]
        self.assertEqual(list(st["events"])[:2], ["SEET2026-A155-07", HL])
        self.assertEqual(st["events"][HL]["people"], 4)
        self.assertEqual(st["events"]["SEET2026-A155-07"]["people"], 4)    # p1、p2、p4、無 pid 的 s5
        self.assertIn("（未填）", st["events"])                               # 缺活動的壞型別紀錄
        self.assertEqual(st["mode_people"]["drive"], 4)
        self.assertGreaterEqual(st["age_people"]["（未填）"], 4)             # v1 玩家全部計入未填
        wb = load_workbook(out)
        ws = wb["玩家彙整"]
        hdr = [c.value for c in ws[1]]
        v1row = {c.value: v.value for c, v in zip(ws[1], ws[2])}
        self.assertEqual(v1row["pid（玩家代碼）"], "p1")
        self.assertEqual((v1row["活動"], v1row["年齡"], v1row["主角"]), ("SEET2026-A155-07", None, None))
        self.assertIn("活動", [c.value for c in wb["已略過(重複)"][1]])
        self.assertEqual(len(hdr), len(set(hdr)))

    def test_cli_event(self):
        out = self.dest / "cli.xlsx"
        code = ff.cli_game_export([str(self.dest), str(out), "--event", HL, "--offline"])
        self.assertEqual(code, 0)
        txt = (self.dest / ff.GAME_SUMMARY_NAME).read_text("utf-8")
        self.assertIn(f"活動：{HL}", txt)
        self.assertIn("區間內 5 筆", txt)
        self.assertIn(f"活動 {HL}：4 人", txt)
        code = ff.cli_game_export([str(self.dest), str(out), "--offline"])
        self.assertEqual(code, 0)
        self.assertIn("活動：全部", (self.dest / ff.GAME_SUMMARY_NAME).read_text("utf-8"))
        code = ff.cli_game_export([str(self.dest), str(out), "--event"])      # 缺值
        self.assertEqual(code, 1)


# ---------------------------------------------------------------- v5 人工魚子醬（HL-STATION-2026-1127-CAVIAR）
CAV = "HL-STATION-2026-1127-CAVIAR"


def cav_ans(*items):
    idx = ff.QUESTION_INDEXES[CAV]
    return [{"id": i, "facet": idx[i]["facet"], "pick": p, "correct": p == 0} for i, p in items]


def game_cav(phase, at, pid, sid, **kw):
    d = game2(phase, at, pid, sid, event=CAV, org="測試國小",
              pre=cav_ans(("E1", 0), ("E2", 1), ("E3", 0)))
    if phase == "post":
        d.update(post=cav_ans(("E1", 0), ("E2", 0), ("E3", 0), ("E5", 0), ("E8", 2)),
                 postSame3=3, postScore=4)
    d.update(kw)
    return d


CAV_GAME_FILES = {
    "20261127-140000_pre_cav001.json": game_cav("pre", "2026-11-27T14:00:00+08:00", "cpid00000001", "csid00000001"),
    "20261127-141000_post_cav002.json": game_cav("post", "2026-11-27T14:10:00+08:00", "cpid00000001", "csid00000001"),
    # 國中版：J1 錯、J2 對、J3 對；後測 J1 對
    "20261127-142000_pre_cav003.json": game_cav("pre", "2026-11-27T14:20:00+08:00", "cpid00000002", "csid00000002",
                                                grade="junior", age=13,
                                                pre=cav_ans(("J1", 2), ("J2", 0), ("J3", 0))),
    "20261127-143000_post_cav004.json": game_cav("post", "2026-11-27T14:30:00+08:00", "cpid00000002", "csid00000002",
                                                 grade="junior", age=13,
                                                 pre=cav_ans(("J1", 2), ("J2", 0), ("J3", 0)),
                                                 post=cav_ans(("J1", 0), ("J2", 0), ("J3", 0), ("J4", 0), ("J9", 1)),
                                                 postSame3=3, postScore=4),
    # 活動代碼大小寫／空白不同，仍應用人工魚子醬題庫；grade 缺 → 由題號推回
    "20261127-150000_pre_cav005.json": game_cav("pre", "2026-11-27T15:00:00+08:00", "cpid00000003", "csid00000003",
                                                event=" hl-station-2026-1127-caviar ", grade=""),
}

CAV_FEEDBACK = [
    v2(submitted_at="2026-11-27T14:40:00+08:00", event=CAV, k1="B", k2="C", k3="A", k_open="鈣離子像手銬",
       a1=5, a2=5, a3=5, i1=4, i2=4, i3=5, s1=4, s2=5, s3=4),
    v2(submitted_at="2026-11-27T14:45:00+08:00", event=CAV, k1="A", k2="C", k3="B",
       a1=3, a2=4, a3=5, i1=3, i2=3, i3=3, s1=2, s2=3, s3=4, s_open="泡更久會怎樣？"),
]


class TestCaviar(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dest = Path(self.tmp.name)
        self.jdir = self.dest / ff.GAME_JSON_SUBDIR
        self.jdir.mkdir()
        for name, obj in CAV_GAME_FILES.items():
            (self.jdir / name).write_text(json.dumps(obj, ensure_ascii=False), "utf-8")
        self.logs = []

    def tearDown(self):
        self.tmp.cleanup()

    def add_default_games(self):
        for name, obj in {**GAME_FILES, **V2_GAME_FILES}.items():
            (self.jdir / name).write_text(json.dumps(obj, ensure_ascii=False), "utf-8")

    def write_feedback(self, with_default=True):
        j = self.dest / "json"
        j.mkdir(exist_ok=True)
        files = {"20261127-144000_cav111.json": CAV_FEEDBACK[0], "20261127-144500_cav222.json": CAV_FEEDBACK[1]}
        if with_default:
            files.update({"20261031-100000_v2aaaa.json": V2[0], "20261031-100500_v2bbbb.json": V2[1],
                          "20261031-101000_v2cccc.json": V2[2]})
        for name, obj in files.items():
            (j / name).write_text(json.dumps(obj, ensure_ascii=False), "utf-8")

    # ---- 題庫
    def test_caviar_bank_verbatim(self):
        b = ff.CAVIAR_BANK
        self.assertEqual([q["id"] for q in b["elem"]], [f"E{i}" for i in range(1, 11)])
        self.assertEqual([q["id"] for q in b["junior"]], [f"J{i}" for i in range(1, 11)])
        self.assertEqual([q["facet"] for q in b["elem"]],
                         ["知識", "探究", "態度", "知識", "知識", "行動", "態度", "行動", "探究", "知識"])
        self.assertEqual([q["facet"] for q in b["junior"]],
                         ["知識", "探究", "態度", "知識", "知識", "知識", "行動", "態度", "探究", "行動"])
        idx = ff.QUESTION_INDEXES[CAV]
        self.assertTrue(all(q["answer"] == 0 and len(q["options"]) == 4 for q in idx.values()))
        self.assertEqual({k for k, q in idx.items() if q["pre"]}, {"E1", "E2", "E3", "J1", "J2", "J3"})
        self.assertEqual(idx["E1"]["q"], "做晶球用的海藻酸鈉，是從哪裡來的？")             # v6 2.0 題庫
        self.assertEqual(idx["E4"]["options"][0], "鈣液裡的鈣離子 Ca²⁺")
        if BANK_V2_JSON.exists():                                                    # 唯一來源全文比對
            src = json.loads(BANK_V2_JSON.read_text("utf-8"))["bank"]
            keys = ("id", "facet", "pre", "q", "options", "answer", "explain")
            for g in ("elem", "junior"):
                self.assertEqual([{k: q[k] for k in keys} for q in b[g]], [{k: q[k] for k in keys} for q in src[g]])
        else:
            print(f"\n  [提示] {BANK_V2_JSON} 不存在，略過 bank_v2.json 全文比對。")
        self.assertTrue(all(re.fullmatch(r"[EJ](10|[1-9])", k) for k in idx))     # 中繼 ID_RE
        self.assertIs(ff.QUESTION_BANKS["default"], ff.QUESTION_BANK)                # 既有題庫不變
        self.assertEqual(ff.QUESTION_INDEX["E1"]["options"][0], "變多")

    def test_bank_by_event(self):
        for ev in (CAV, " hl-station-2026-1127-caviar ", f"{CAV}｜11/27 花蓮站 人工魚子醬", "11/27 花蓮站 人工魚子醬"):
            self.assertEqual(ff.bank_key_for_event(ev), CAV, ev)
        for ev in ("HL-STATION-2026-1127", "SEET2026-A155-07", "", None, "不存在", "全部"):
            self.assertEqual(ff.bank_key_for_event(ev), "default", ev)
        self.assertEqual(ff.bank_index(CAV)["E1"]["q"], "做晶球用的海藻酸鈉，是從哪裡來的？")
        self.assertEqual(ff.bank_index("HL-STATION-2026-1127")["E1"]["q"], "把大石頭敲成很多小碎塊，露出來的表面會怎樣？")
        self.assertEqual(ff.event_code(f"{CAV}｜11/27 花蓮站 人工魚子醬"), CAV)
        self.assertEqual(ff.EVENT_PRESETS[CAV], "11/27 花蓮站 人工魚子醬")
        self.assertTrue(all(ff.EVENT_PRESETS[k] for k in ("SEET2026-A155-07", "HL-STATION-2026-1127")))
        self.assertEqual(ff.EVENT_DEFAULT_DEST[CAV],
                         r"D:\01-FC東華\05-專案\2026_科普列車_花蓮新城站\07-20261127花蓮站科普列車\05-回饋問卷與遊戲前後測")

    def test_load_uses_event_bank(self):
        recs = ff.load_game_records(self.jdir, log=self.logs.append)
        self.assertEqual(len(recs), 5)
        by = {r["file"]: r for r in recs}
        a = by["20261127-140000_pre_cav001.json"]
        self.assertEqual(a["bank"], CAV)
        self.assertEqual([x["text"] for x in a["pre"]],
                         ["海裡的褐藻（像海帶）", "時間和鈣液濃度一起改，比較快", "不可以，這是實驗品不能吃"])
        self.assertEqual([x["correct"] for x in a["pre"]], [1, 0, 1])
        e = by["20261127-150000_pre_cav005.json"]                 # 大小寫／空白不同、grade 由題號推回
        self.assertEqual((e["bank"], e["grade"]), (CAV, "elem"))
        # 同題號不同活動 → 不同選項文字
        self.add_default_games()
        recs = ff.load_game_records(self.jdir, log=self.logs.append)
        hl = next(r for r in recs if r["file"] == "20261127-100000_pre_v2aaaa.json")
        self.assertEqual((hl["bank"], hl["pre"][0]["text"]), ("default", "變多"))

    def test_caviar_export(self):
        out = self.dest / "cav.xlsx"
        res = ff.run_game_export(self.dest, out, None, None, 30, None, log=self.logs.append,
                                 offline=True, event=f"{CAV}｜11/27 花蓮站 人工魚子醬")
        self.assertEqual((res["local"], res["in_range"], res["kept"], res["plays"], res["complete"]),
                         (5, 5, 5, 3, 2))
        st = res["stats"]
        self.assertEqual(st["event_filter"], CAV)
        self.assertEqual(st["q_banks"], [CAV])
        self.assertEqual(st["per_q"][CAV]["E2"], {"pre_n": 2, "pre_ok": 0, "post_n": 1, "post_ok": 1,
                                                  "pre_rate": 0.0, "post_rate": 1.0})
        self.assertEqual(st["per_q"][CAV]["J9"]["post_ok"], 0)
        wb = load_workbook(out)
        ws = wb["玩家彙整"]
        hdr = [c.value for c in ws[1]]
        row = {c.value: v.value for c, v in zip(ws[1], ws[2])}
        self.assertEqual(row["活動"], CAV)
        self.assertEqual(row["前測Q1 選項文字"], "海裡的褐藻（像海帶）")
        self.assertEqual(row["後測Q4 選項文字"], "表面張力把液滴拉成圓球")
        self.assertEqual(row["後測Q5 選項文字"], "鈣液沒有毒，直接倒進水槽")
        self.assertEqual(row["版本"], "初階")                                         # v6 程度顯示
        self.assertEqual((row["前測答對數(0–3)"], row["後測同3題答對數(0–3)"], row["進步（後測同3題−前測）"]), (2, 3, 1))
        jr = {c.value: v.value for c, v in zip(ws[1], ws[3])}
        self.assertEqual((jr["版本"], jr["前測Q1 選項文字"], jr["進步（後測同3題−前測）"]), ("中階", "不帶電（正負互相抵銷）", 1))
        self.assertEqual(len(hdr), len(set(hdr)))
        post = wb["後測"]
        ph = [c.value for c in post[1]]
        self.assertEqual(post.cell(2, ph.index("Q4 選項文字") + 1).value, "表面張力把液滴拉成圓球")
        qa = wb["題目對照"]
        self.assertEqual(qa.max_row, 1 + 20)
        self.assertEqual(qa["F2"].value, "海裡的褐藻（像海帶）")
        self.assertEqual(qa["K1"].value, "活動（題庫）")
        self.assertTrue(all(CAV in qa.cell(r, 11).value for r in range(2, 22)))
        self.assertEqual(qa["E2"].value, "做晶球用的海藻酸鈉，是從哪裡來的？")
        self.assertEqual((qa["B2"].value, qa["B12"].value), ("初階", "中階"))
        sv = {r[0].value: [x.value for x in r[1:]] for r in wb["統計"].iter_rows() if r[0].value}
        self.assertTrue(any(k.startswith("每題作答｜" + CAV) for k in sv))
        self.assertEqual(sv["E2（前測題）"][1:5], [2, 0.0, 1, 1.0])
        self.assertEqual(sv["E2（前測題）"][5], "探究")
        self.assertEqual(sv[CAV][:4], [3, 3, 2, 2.0])

    def test_mixed_export_separates_banks(self):
        self.add_default_games()
        out = self.dest / "all.xlsx"
        res = ff.run_game_export(self.dest, out, None, None, 30, None, log=self.logs.append, offline=True)
        st = res["stats"]
        self.assertEqual(st["q_banks"], ["default", CAV])
        only = ff.run_game_export(self.dest, self.dest / "d.xlsx", None, None, 30, None, log=self.logs.append,
                                  offline=True, event="SEET2026-A155-07")["stats"]["per_q"]["default"]["E1"]
        hl = ff.run_game_export(self.dest, self.dest / "h.xlsx", None, None, 30, None, log=self.logs.append,
                                offline=True, event="HL-STATION-2026-1127")["stats"]["per_q"]["default"]["E1"]
        self.assertEqual(st["per_q"]["default"]["E1"]["pre_n"], only["pre_n"] + hl["pre_n"])  # 墨玉 E1 不混入魚子醬 E1
        self.assertEqual(st["per_q"][CAV]["E1"]["pre_n"], 2)
        self.assertEqual(list(st["events"])[:3], ["SEET2026-A155-07", "HL-STATION-2026-1127", CAV])
        wb = load_workbook(out)
        qa = wb["題目對照"]
        self.assertEqual(qa.max_row, 1 + 40)
        labels = [qa.cell(r, 11).value for r in range(2, 42)]
        self.assertEqual(sum(1 for x in labels if x.startswith("default")), 20)
        self.assertEqual(sum(1 for x in labels if x.startswith(CAV)), 20)
        heads = [r[0].value for r in wb["統計"].iter_rows() if r[0].value and str(r[0].value).startswith("每題作答")]
        self.assertEqual(len(heads), 2)

    def test_cli_caviar(self):
        out = self.dest / "cli.xlsx"
        code = ff.cli_game_export([str(self.dest), str(out), "--event", CAV, "--offline"])
        self.assertEqual(code, 0)
        txt = (self.dest / ff.GAME_SUMMARY_NAME).read_text("utf-8")
        self.assertIn(f"活動：{CAV}", txt)
        self.assertIn("區間內 5 筆", txt)
        self.assertIn(f"活動 {CAV}：3 人", txt)

    # ---- 回饋問卷
    def test_feedback_answer_key_by_event(self):
        self.assertEqual(ff.answer_key_for(CAV), {"k1": "B", "k2": "C", "k3": "A"})
        self.assertEqual(ff.answer_key_for("SEET2026-A155-07"), ff.ANSWER_KEY)
        self.assertEqual([lab for _, lab in ff.knowledge_for(CAV)],
                         ["K1 扣住海藻酸鈉長鏈形成薄膜的離子", "K2 讓液滴收縮成圓球的力量", "K3 海藻酸鈉萃取自哪一類生物"])
        self.assertEqual(ff.knowledge_for("HL-STATION-2026-1127"), ff.KNOWLEDGE)
        self.write_feedback()
        rows = ff.load_records(self.dest / "json")
        by = {r["file"]: r for r in rows}
        c1, c2 = by["20261127-144000_cav111.json"], by["20261127-144500_cav222.json"]
        self.assertEqual((c1["_bank"], c1["k_score"], c2["k1_ok"], c2["k2_ok"], c2["k3_ok"], c2["k_score"]),
                         (CAV, 3, 0, 1, 0, 1))
        # 正解確實依活動切換：改人工魚子醬的 k1 正解，只影響人工魚子醬列
        with mock.patch.dict(ff.FEEDBACK_SETS[CAV]["answer"], {"k1": "A"}):
            rows = ff.load_records(self.dest / "json")
            by = {r["file"]: r for r in rows}
            self.assertEqual((by["20261127-144000_cav111.json"]["k1_ok"],
                              by["20261127-144500_cav222.json"]["k1_ok"]), (0, 1))
            self.assertEqual(by["20261031-100000_v2aaaa.json"]["k1_ok"], 1)   # default 列仍以 B 計

    def test_feedback_aggregate_mixed(self):
        self.write_feedback()
        n, st = ff.aggregate(self.dest)
        self.assertEqual(n, 5)
        self.assertEqual(st["banks"], ["default", CAV])
        self.assertEqual((st["groups"]["default"]["n"], st["groups"][CAV]["n"]), (3, 2))
        self.assertEqual(st["knowledge"]["k1"]["n"], 3)                      # 頂層＝default（相容舊版）
        g = st["groups"][CAV]
        self.assertEqual((g["knowledge"]["k1"]["correct"], g["knowledge"]["k1"]["n"]), (1, 2))
        self.assertEqual(g["k_score_mean"], (2.0, 2))
        self.assertEqual(g["facets"]["a"], (4.5, 6))
        cav_opens = [o for o in st["opens"] if o[0].startswith("20261127")]
        self.assertEqual({o[4] for o in cav_opens}, {"K 簡答：記得的科學觀念", "S 簡答：想探究的問題"})
        wb = load_workbook(self.dest / ff.XLSX_NAME)
        sv = {r[0].value: [c.value for c in r[1:]] for r in wb["統計"].iter_rows() if r[0].value}
        self.assertIn("v2 環境知識題｜" + ff.BANK_LABEL[CAV], sv)
        self.assertEqual(sv["K1 扣住海藻酸鈉長鏈形成薄膜的離子"][:4], ["B", 2, 1, 0.5])
        self.assertEqual(sv["K1 微米化的主要好處"][:4], ["B", 3, 2, 0.6667])
        self.assertIn("　A1 海裡藻類是值得珍惜的資源", sv)
        head = [c.value for c in wb["回覆"][1]]
        self.assertIn("K1（依活動題目）(k1)", head)                          # 混合活動→通用表頭
        txt = "\n".join(ff.summary_lines(st))
        self.assertIn("K1 1/2", txt)
        self.assertIn("K1 2/3", txt)

    def test_feedback_only_caviar_headers(self):
        self.write_feedback(with_default=False)
        n, st = ff.aggregate(self.dest)
        self.assertEqual((n, st["banks"]), (2, [CAV]))
        raw = (self.dest / ff.CSV_NAME).read_text("utf-8-sig")
        head = next(csv.reader(raw.splitlines()))
        self.assertIn("K2 讓液滴收縮成圓球的力量(k2)", head)
        self.assertIn("K2 答對(1/0)(k2_ok)", head)
        self.assertIn("A1 海裡藻類是值得珍惜的資源(a1)", head)
        self.assertEqual([h.split("(")[-1][:-1] for h in head], [k for k, _ in ff.FIELDS])

    def test_config_remembers_event_no_token(self):
        with mock.patch.object(ff, "app_dir", return_value=self.dest):
            ff.save_config(ff.CAVIAR_DEST, 30, CAV)
            self.assertEqual(ff.load_config(), {"dest": ff.CAVIAR_DEST, "game_window": 30, "event": CAV})
            ff.save_config("D:\\y")                                           # 保留分鐘數與活動
            cfg = ff.load_config()
            self.assertEqual(cfg, {"dest": "D:\\y", "game_window": 30, "event": CAV})
            self.assertFalse(any("token" in k.lower() for k in cfg))


# ---------------------------------------------------------------- v6 晶球護衛隊 2.0 高階（-SR）
SR = "HL-STATION-2026-1127-CAVIAR-SR"


def sr_ans(*items):
    idx = ff.QUESTION_INDEXES[SR]
    return [{"id": i, "facet": idx[i]["facet"], "pick": p, "correct": p == 0} for i, p in items]


def game_sr(phase, at, pid, sid, **kw):
    """高階上傳格式：event -SR、grade junior、題號 S→J。"""
    d = game2(phase, at, pid, sid, event=SR, grade="junior", age=21, org="大學生｜東華大學",
              pre=sr_ans(("J1", 0), ("J2", 1), ("J3", 0)))
    if phase == "post":
        d.update(post=sr_ans(("J1", 0), ("J2", 0), ("J3", 0), ("J4", 0), ("J9", 2)),
                 postSame3=3, postScore=4)
    d.update(kw)
    return d


SR_GAME_FILES = {
    "20261127-160000_pre_sr0001.json": game_sr("pre", "2026-11-27T16:00:00+08:00", "spid00000001", "ssid00000001"),
    "20261127-161000_post_sr0002.json": game_sr("post", "2026-11-27T16:10:00+08:00", "spid00000001", "ssid00000001"),
    # 只有身分（無「｜」）
    "20261127-162000_pre_sr0003.json": game_sr("pre", "2026-11-27T16:20:00+08:00", "spid00000002", "ssid00000002",
                                               org="研究生"),
}


class TestCaviarSR(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dest = Path(self.tmp.name)
        self.jdir = self.dest / ff.GAME_JSON_SUBDIR
        self.jdir.mkdir()
        for name, obj in {**CAV_GAME_FILES, **SR_GAME_FILES}.items():
            (self.jdir / name).write_text(json.dumps(obj, ensure_ascii=False), "utf-8")
        self.logs = []

    def tearDown(self):
        self.tmp.cleanup()

    def load(self):
        return ff.load_game_records(self.jdir, log=self.logs.append)

    def test_sr_bank_id_mapping(self):
        self.assertEqual(ff.EVENT_CAVIAR_SR, SR)
        self.assertEqual(ff.EVENT_PRESETS[SR], "11/27 花蓮站 人工魚子醬（高階）")
        self.assertEqual(ff.EVENT_DEFAULT_DEST[SR], ff.CAVIAR_DEST)
        self.assertIs(ff.feedback_set(SR), ff.feedback_set(CAV))                 # 回饋問卷沿用 CAVIAR
        self.assertEqual(list(ff.CAVIAR_SR_BANK), ["junior"])
        idx = ff.QUESTION_INDEXES[SR]
        self.assertEqual(list(idx), [f"J{i}" for i in range(1, 11)])
        self.assertTrue(all(q["src_id"] == "S" + k[1:] and q["grade"] == "junior" for k, q in idx.items()))
        self.assertTrue(all(re.fullmatch(r"[EJ](10|[1-9])", k) for k in idx))     # 中繼 ID_RE
        self.assertEqual({k for k, q in idx.items() if q["pre"]}, {"J1", "J2", "J3"})
        self.assertEqual(idx["J1"]["q"], "為什麼 Ca²⁺ 能使海藻酸鈉成膠，Na⁺ 卻不能？")
        self.assertNotEqual(idx["J1"]["q"], ff.QUESTION_INDEXES[CAV]["J1"]["q"])   # 同題號不同題庫
        self.assertEqual(ff.display_qid(idx["J3"]), "J3（S3）")
        for ev in (SR, " hl-station-2026-1127-caviar-sr ", f"{SR}｜11/27 花蓮站 人工魚子醬（高階）",
                   "11/27 花蓮站 人工魚子醬（高階）"):
            self.assertEqual(ff.bank_key_for_event(ev), SR, ev)
        if BANK_V2_JSON.exists():
            src = json.loads(BANK_V2_JSON.read_text("utf-8"))["bank"]["senior"]
            for q, s in zip(ff.CAVIAR_SR_BANK["junior"], src):
                self.assertEqual((q["src_id"], q["q"], q["options"], q["explain"], q["facet"], q["pre"]),
                                 (s["id"], s["q"], s["options"], s["explain"], s["facet"], s["pre"]))

    def test_level_label(self):
        self.assertEqual(ff.level_label("elem", CAV), "初階")
        self.assertEqual(ff.level_label("junior", CAV), "中階")
        self.assertEqual(ff.level_label("junior", SR), "高階")
        self.assertEqual(ff.level_label("", SR), "高階")
        self.assertEqual(ff.level_label("elem", "default"), "國小")
        self.assertEqual(ff.level_label("junior"), "國中")
        recs = {r["file"]: r for r in self.load()}
        self.assertEqual(recs["20261127-160000_pre_sr0001.json"]["level"], "高階")
        self.assertEqual(recs["20261127-140000_pre_cav001.json"]["level"], "初階")
        self.assertEqual(recs["20261127-142000_pre_cav003.json"]["level"], "中階")
        a = recs["20261127-160000_pre_sr0001.json"]
        self.assertEqual((a["bank"], a["grade"]), (SR, "junior"))
        self.assertEqual([x["text"] for x in a["pre"]],
                         [ff.QUESTION_INDEXES[SR][i]["options"][p] for i, p in (("J1", 0), ("J2", 1), ("J3", 0))])

    def test_split_org(self):
        self.assertEqual(ff.split_org("大學生｜東華大學"), ("大學生", "東華大學"))
        self.assertEqual(ff.split_org(" 教師 ｜ 花蓮某國小 "), ("教師", "花蓮某國小"))
        self.assertEqual(ff.split_org("研究生"), ("", "研究生"))
        self.assertEqual(ff.split_org("家長｜"), ("家長", ""))
        self.assertEqual(ff.split_org(""), ("", ""))
        self.assertEqual(ff.split_org(None), ("", ""))
        r = {x["file"]: x for x in self.load()}
        self.assertEqual((r["20261127-160000_pre_sr0001.json"]["role"], r["20261127-160000_pre_sr0001.json"]["unit"],
                          r["20261127-160000_pre_sr0001.json"]["org"]), ("大學生", "東華大學", "大學生｜東華大學"))
        self.assertEqual((r["20261127-162000_pre_sr0003.json"]["role"], r["20261127-162000_pre_sr0003.json"]["unit"]),
                         ("", "研究生"))

    def test_event_family_filter(self):
        recs = self.load()
        self.assertEqual(len(ff.filter_by_event(recs, CAV)), 5 + 3)                # 含 -SR 高階
        self.assertEqual(len(ff.filter_by_event(recs, " hl-station-2026-1127-caviar ")), 8)
        self.assertEqual(len(ff.filter_by_event(recs, f"{CAV}｜11/27 花蓮站 人工魚子醬")), 8)
        self.assertEqual(len(ff.filter_by_event(recs, SR)), 3)                      # 直接指定 -SR 只取高階
        self.assertEqual(len(ff.filter_by_event(recs, "HL-STATION-2026-1127")), 0)  # 墨玉不受影響
        self.assertIn("含", ff.event_filter_text(CAV))
        self.assertEqual(ff.event_filter_text(SR), SR)

    def test_export_family_groups_by_level(self):
        out = self.dest / "fam.xlsx"
        res = ff.run_game_export(self.dest, out, None, None, 30, None, log=self.logs.append,
                                 offline=True, event=CAV)
        self.assertEqual((res["in_range"], res["plays"], res["complete"]), (8, 5, 3))
        st = res["stats"]
        self.assertEqual(st["event_filter"], CAV)
        self.assertEqual(st["q_banks"], [CAV, SR])
        self.assertEqual(list(st["levels"]), ["初階", "中階", "高階"])
        self.assertEqual((st["levels"]["初階"]["people"], st["levels"]["中階"]["people"],
                          st["levels"]["高階"]["people"]), (2, 1, 2))
        self.assertEqual(st["levels"]["高階"]["complete"], 1)
        self.assertEqual(st["per_q"][SR]["J2"]["pre_n"], 2)
        self.assertEqual(st["per_q"][CAV]["J2"]["pre_n"], 1)                       # 中階 J2 不混入高階
        wb = load_workbook(out)
        ws = wb["玩家彙整"]
        rows = [{c.value: v.value for c, v in zip(ws[1], r)} for r in ws.iter_rows(min_row=2)]
        hi = next(r for r in rows if r["sid（遊玩代碼）"] == "ssid00000001")
        self.assertEqual((hi["版本"], hi["活動"], hi["身分"], hi["單位"], hi["學校／單位"]),
                         ("高階", SR, "大學生", "東華大學", "大學生｜東華大學"))
        self.assertEqual(hi["前測Q1 選項文字"], ff.QUESTION_INDEXES[SR]["J1"]["options"][0])
        self.assertEqual(hi["後測Q5 選項文字"], ff.QUESTION_INDEXES[SR]["J9"]["options"][2])
        self.assertEqual({r["版本"] for r in rows}, {"初階", "中階", "高階"})
        for name in ("前測", "後測"):
            sh = wb[name]
            h = [c.value for c in sh[1]]
            vals = {sh.cell(i, h.index("版本") + 1).value for i in range(2, sh.max_row + 1)}
            self.assertIn("高階", vals)
            self.assertNotIn("國中", vals)
        sv = {r[0].value: [x.value for x in r[1:]] for r in wb["統計"].iter_rows() if r[0].value}
        self.assertIn("依程度分組", sv)
        self.assertEqual(sv["高階"][:3], [2, 2, 1])
        self.assertEqual(sv["高階人數"][0], 2)
        self.assertIn("含", sv["篩選活動"][0])
        self.assertIn("J3（S3）（前測題）", sv)
        self.assertEqual(sv["J3（S3）（前測題）"][0], "高階")
        qa = wb["題目對照"]
        self.assertEqual(qa.max_row, 1 + 20 + 10)
        srow = [[c.value for c in r] for r in qa.iter_rows(min_row=2) if SR in (r[10].value or "")]
        self.assertEqual(len(srow), 10)
        self.assertEqual((srow[0][0], srow[0][1], srow[0][4]),
                         ("J1（S1）", "高階", ff.QUESTION_INDEXES[SR]["J1"]["q"]))

    def test_cli_sr_only(self):
        out = self.dest / "sr.xlsx"
        code = ff.cli_game_export([str(self.dest), str(out), "--event", SR, "--offline"])
        self.assertEqual(code, 0)
        txt = (self.dest / ff.GAME_SUMMARY_NAME).read_text("utf-8")
        self.assertIn(f"活動：{SR}；", txt)
        self.assertIn("區間內 3 筆", txt)
        self.assertIn("程度 高階：2 人", txt)
        self.assertNotIn("程度 初階", txt)
        code = ff.cli_game_export([str(self.dest), str(out), "--event", CAV, "--offline"])
        self.assertEqual(code, 0)
        txt = (self.dest / ff.GAME_SUMMARY_NAME).read_text("utf-8")
        self.assertIn("區間內 8 筆", txt)
        self.assertIn("程度 高階：2 人", txt)
        self.assertIn("程度 初階：2 人", txt)


# ---------------------------------------------------------------- v7：研究用前後測（feedback/test，webar-test-v1）
SAMPLES = Path(__file__).resolve().parent / "test_samples" / "research"   # 經中繼 Code.gs v5 清理後的實際紀錄＋補充案例
STUDY_JS = GAME_REPO / "js" / "study.js"
CODE_GS = GAME_REPO / "feedback" / "relay" / "Code.gs"


def rans(grade, picks):
    """10 題作答（picks＝原始選項索引）；correct 依正解 0，態度題 null（與中繼一致）。"""
    out = []
    for q, p in zip(ff.RESEARCH_BANK[grade], picks):
        att = q["facet"] == "態度"
        out.append({"id": q["id"], "facet": q["facet"], "pick": p, "correct": None if att else p == 0})
    return out


def rrec(phase, at, sid, group="control", grade="elem", pre=None, post=None, **kw):
    d = {"schema": "webar-test-v1", "submitted_at": at, "event": kw.pop("event", "CTRL-TEST"), "group": group,
         "pid": kw.pop("pid", "p" * 12), "sid": sid, "phase": phase, "grade": grade,
         "mode": "test" if group == "control" else "play", "client_time": "",
         "pre": pre if pre is not None else rans(grade, [0] * 10),
         "post": (post if post is not None else rans(grade, [0] * 10)) if phase == "post" else [],
         "preScore": 0, "postScore": "", "maxScore": 8,
         "stars": [3, 3, 3, 3, 3, 3, 3, 3] if (group == "game" and phase == "post") else [],
         "totalStars": "", "restarts": 0 if group == "game" else "",
         "commit": "做好垃圾分類回收" if phase == "post" else "", "commitPick": 0 if phase == "post" else "",
         "ua": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Safari/604.1"}
    d.update(kw)
    return d


class TestResearch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dest = Path(self.tmp.name)
        self.tdir = self.dest / ff.TEST_JSON_SUBDIR
        self.tdir.mkdir()
        for p in SAMPLES.glob("*.json"):
            (self.tdir / p.name).write_bytes(p.read_bytes())
        self.logs = []

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, name, obj):
        (self.tdir / name).write_text(json.dumps(obj, ensure_ascii=False), "utf-8")

    def pipeline(self, **kw):
        recs = ff.load_research_records(self.tdir, log=self.logs.append)
        kept, dropped = ff.dedupe_research(ff.filter_research(recs, **kw))
        return recs, kept, dropped, {s["sid"]: s for s in ff.pair_students(kept)}

    def test_constants_and_bank(self):
        self.assertEqual(ff.SCHEMA_TEST, "webar-test-v1")
        self.assertIn("feedback/test", ff.TEST_API_URL)
        self.assertEqual(ff.TEST_JSON_SUBDIR, "test_json")
        self.assertEqual({g: len(q) for g, q in ff.RESEARCH_BANK.items()}, {"elem": 10, "junior": 10})
        self.assertEqual(ff.ATTITUDE_IDS, {"elem": ["E3", "E7"], "junior": ["J3", "J8"]})
        self.assertEqual(ff.RESEARCH_MAX, {"elem": 8, "junior": 8})
        self.assertEqual(len(ff.COMMITS), 4)

    @unittest.skipUnless((GAME_REPO / "js" / "content.js").exists(), "本機無遊戲 repo")
    def test_research_bank_matches_game_repo(self):
        """研究用 10 題＝遊戲 js/content.js 的 BANK（逐題：題目、四選項順序、正解 0、面向）；
        態度題不計分要與 js/study.js（ATTITUDE="態度"、N=10）及中繼 Code.gs（TEST_ATTITUDE、TEST_N）一致；行動承諾文字一致。"""
        src = (GAME_REPO / "js" / "content.js").read_text("utf-8")
        check_bank_in_js(self, src, ff.RESEARCH_INDEX)
        for c in ff.COMMITS:
            self.assertIn(f'"{c}"', src)
        if STUDY_JS.exists():
            sj = STUDY_JS.read_text("utf-8")
            self.assertRegex(sj, r'export const N = 10;')
            self.assertRegex(sj, r'export const ATTITUDE = "態度";')
            self.assertIn('SCHEMA = "webar-test-v1"', sj)
        else:
            print("  （提示）找不到 js/study.js，略過研究模式共用模組比對")
        if CODE_GS.exists():
            gs = CODE_GS.read_text("utf-8")
            m = re.search(r"TEST_ATTITUDE = \[([^\]]*)\]", gs)
            self.assertIsNotNone(m)
            self.assertEqual(sorted(re.findall(r"'(\w+)'", m.group(1))),
                             sorted(ff.ATTITUDE_IDS["elem"] + ff.ATTITUDE_IDS["junior"]))
            self.assertRegex(gs, r"var TEST_N = 10;")
            self.assertRegex(gs, r"var TEST_DIR = 'feedback/test';")

    def test_samples_load_dedupe_pair(self):
        recs, kept, dropped, by = self.pipeline()
        self.assertEqual((len(recs), len(kept), len(dropped)), (9, 8, 1))
        self.assertEqual(dropped[0]["file"], "20261201-094003_post_dup001.json")
        self.assertEqual(dropped[0]["base_file"], "20261201-094000_post_1cwmab.json")
        self.assertEqual(len(by), 5)
        c = by["1cwmab7ytay0"]                      # 對照班國小：4 → 8
        self.assertEqual((c["group"], c["grade"], c["pre_total"], c["post_total"], c["gain"]), ("control", "elem", 4, 8, 4))
        self.assertEqual(c["pre"]["E3"]["correct"], "")              # 態度題不計對錯
        self.assertEqual(c["pre"]["E3"]["text"], "可能是能再利用的資源")
        self.assertEqual(c["stars"], [])
        self.assertEqual(by["fyfkxt0q9qy8"]["post_total"], 7)
        g = by["seedgame0001"]                      # 遊戲班國小
        self.assertEqual((g["pre_total"], g["post_total"], g["totalStars"], g["restarts"]), (0, 7, 20, 0))
        self.assertEqual(g["stars"], [3, 2, 3, 3, 2, 3, 1, 3])
        self.assertEqual(g["commit"], "做好垃圾分類回收")
        j = by["3wqs0m1umrsl"]                      # 只有前測
        self.assertFalse(j["completed"])
        self.assertIn("未完成後測", j["note"])
        self.assertEqual((j["post_total"], j["gain"]), ("", ""))
        e = by["ml8dvd0phfju"]                      # 缺獨立前測檔
        self.assertTrue(e["completed"])
        self.assertEqual(e["pre_source"], "後測檔內的前測作答")
        self.assertIn("前測作答取自後測檔", e["note"])
        self.assertEqual(len(e["pre"]), 10)
        self.assertIsNone(e["pre_time"])

    def test_attitude_never_scored_and_picks_recomputed(self):
        pre = rans("junior", [0, 1, 0, 2, 0, 0, 0, 3, 0, 0])
        pre[2]["correct"] = True                    # 竄改：態度題 J3 送 true
        pre[0]["correct"] = True                    # 竄改：J1 實際選 0 → 正確；
        pre[1]["correct"] = True                    # 竄改：J2 選 1 → 應判錯
        self.put("20261202-080000_pre_zzzzzz.json", rrec("pre", "2026-12-02T08:00:00+08:00", "s" * 12, grade="junior", pre=pre))
        _, _, _, by = self.pipeline(group="control", grade="junior")
        s = by["s" * 12]
        self.assertEqual(s["pre"]["J3"]["correct"], "")
        self.assertEqual(s["pre"]["J8"]["correct"], "")
        self.assertEqual(s["pre"]["J2"]["correct"], 0)
        self.assertEqual(s["pre_total"], 6)          # 8 題計分題中 J2、J4 錯

    def test_dedupe_keeps_earliest_time_not_file_order(self):
        sid = "d" * 12
        self.put("20261203-090000_post_aaaaaa.json", rrec("post", "2026-12-03T09:30:00+08:00", sid))
        self.put("20261203-080000_post_bbbbbb.json", rrec("post", "2026-12-03T08:10:00+08:00", sid,
                                                           post=rans("elem", [1] * 10)))
        self.put("20261203-070000_pre_cccccc.json", rrec("pre", "2026-12-03T08:00:00+08:00", sid))
        recs, kept, dropped, by = self.pipeline(event="CTRL-TEST", grade="elem")
        self.assertEqual([d["file"] for d in dropped], ["20261203-090000_post_aaaaaa.json"])
        self.assertEqual(by[sid]["post_file"], "20261203-080000_post_bbbbbb.json")
        self.assertEqual(by[sid]["post_total"], 0)

    def test_filters(self):
        _, _, _, by = self.pipeline(group="game")
        self.assertEqual(set(by), {"seedgame0001", "3wqs0m1umrsl", "ml8dvd0phfju"})
        _, _, _, by = self.pipeline(group="control", grade="junior")
        self.assertEqual(set(by), {"fyfkxt0q9qy8"})
        _, _, _, by = self.pipeline(event="ap-study-test")          # 不分大小寫
        self.assertEqual(set(by), {"3wqs0m1umrsl", "ml8dvd0phfju"})
        recs = ff.load_research_records(self.tdir, log=self.logs.append)
        t = ff.filter_by_time(recs, ff.parse_user_time("2026-12-01 09:00"), ff.parse_user_time("2026-12-01 09:03", True))
        self.assertEqual(len(t), 3)                                  # 09:00–09:03 的 3 筆前測（09:04 的前測與 09:40 後的後測在外）
        self.assertEqual(ff.norm_group("遊戲班"), "game")
        self.assertEqual(ff.norm_grade("國中"), "junior")
        self.assertEqual(ff.norm_group("全部"), "")
        with self.assertRaises(ValueError):
            ff.norm_group("老師")

    def test_bad_types_do_not_crash(self):
        self.put("20261204-080000_pre_badbad.json", {"schema": "x", "group": "teacher", "grade": "senior",
                                                     "sid": 5, "pre": "oops", "stars": "3", "commitPick": "9"})
        self.put("20261204-080001_post_badba2.json", rrec("post", "壞時間", "b" * 12, group="game", stars=[3, 3]))
        self.put("20261204-080002_pre_broken.json", "{not json")
        (self.tdir / "20261204-080003_pre_broke2.json").write_text("{not json", "utf-8")
        recs = ff.load_research_records(self.tdir, log=self.logs.append)
        bad = next(r for r in recs if r["file"] == "20261204-080000_pre_badbad.json")
        self.assertEqual((bad["group"], bad["grade"], bad["pre"], bad["stars"], bad["commitPick"]), ("", "", {}, [], ""))
        self.assertIn("組別不明", bad["note"])
        b2 = next(r for r in recs if r["file"].endswith("badba2.json"))
        self.assertIsNone(b2["submitted_at"])
        self.assertIn("遊戲班後測缺八關星數", b2["note"])
        self.assertTrue(any("略過壞檔" in m for m in self.logs))
        ff.pair_students(ff.dedupe_research(recs)[0])                # 不崩潰

    def test_xlsx_and_csv(self):
        out = self.dest / "r.xlsx"
        res = ff.run_research_export(self.dest, out, offline=True, log=self.logs.append)
        self.assertEqual((res["local"], res["kept"], res["dropped"], res["students"], res["complete"]), (9, 8, 1, 5, 4))
        wb = load_workbook(out)
        self.assertEqual(wb.sheetnames, ["學生彙整", "分析用_國小elem", "分析用_國中junior", "統計",
                                         "課後問卷", "課後問卷統計", "已略過（重複）", "題目對照"])   # v7.1 加兩張
        ws = wb["學生彙整"]
        hdr = [c.value for c in ws[1]]
        for col in ("活動代碼", "組別", "版本", "pid", "sid", "前測時間", "後測時間", "作答模式", "前測Q10 選項文字",
                    "後測Q1 選項索引", "前測總分(8題)", "後測總分(8題)", "進步分數", "態度題1（E3／J3）前測選擇",
                    "行動承諾", "第8關星數", "總星數", "restarts（重闖次數）", "裝置摘要", "完成後測", "資料來源註記"):
            self.assertIn(col, hdr)
        rows = [dict(zip(hdr, r)) for r in ws.iter_rows(min_row=2, values_only=True)]
        self.assertEqual(len(rows), 5)
        r = next(x for x in rows if x["sid"] == "1cwmab7ytay0")
        self.assertEqual((r["組別"], r["版本"], r["前測Q3 對錯(1/0；態度題—)"], r["裝置摘要"]), ("對照班", "國小", "—", "Windows／Chrome"))
        el = wb["分析用_國小elem"]
        cols = [c.value for c in el[1]]
        self.assertEqual(cols, ff.analysis_columns("elem"))
        self.assertNotIn("pre_E3", cols)
        self.assertIn("att2_post", cols)
        self.assertTrue(all(re.fullmatch(r"[a-z_0-9A-Z]+", c) for c in cols))
        data = [dict(zip(cols, r)) for r in el.iter_rows(min_row=2, values_only=True)]
        self.assertEqual({d["sid"] for d in data}, {"1cwmab7ytay0", "seedgame0001", "ml8dvd0phfju"})
        ctl = next(d for d in data if d["group"] == "control")
        self.assertEqual((ctl["group_code"], ctl["pre_total"], ctl["post_total"], ctl["gain"], ctl["stars1"], ctl["att1_pre"]),
                         (0, 4, 8, 4, None, 0))
        gm = next(d for d in data if d["sid"] == "ml8dvd0phfju")
        self.assertEqual((gm["group_code"], gm["pre_from_post"], gm["total_stars"], gm["restarts"]), (1, 1, 21, 1))
        jr = [dict(zip([c.value for c in wb["分析用_國中junior"][1]], r))
              for r in wb["分析用_國中junior"].iter_rows(min_row=2, values_only=True)]
        inc = next(d for d in jr if d["sid"] == "3wqs0m1umrsl")
        self.assertEqual((inc["completed"], inc["post_total"], inc["post_J1"]), (0, None, None))
        csvp = res["csv"]["elem"]
        raw = Path(csvp).read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        with open(csvp, encoding="utf-8-sig", newline="") as f:
            crow = list(csv.reader(f))
        self.assertEqual(crow[0], cols)
        self.assertEqual(len(crow), 4)
        self.assertTrue(Path(res["csv"]["junior"]).exists())
        st = [r for r in wb["統計"].iter_rows(values_only=True)]
        flat = [str(v) for r in st for v in r if v is not None]
        self.assertIn("對照班｜國小｜CTRL-E-R2", flat)
        self.assertTrue(any(s.startswith("逐題答對率｜遊戲班｜國小") for s in flat))
        self.assertTrue(any(s.startswith("態度題選項人數｜對照班｜國中") for s in flat))
        self.assertTrue(any(s.startswith("行動承諾分布") for s in flat))
        skip = list(wb["已略過（重複）"].iter_rows(values_only=True))
        self.assertEqual(len(skip), 2)
        qrows = list(wb["題目對照"].iter_rows(min_row=2, values_only=True))
        self.assertEqual(len(qrows), 20)
        e3 = next(q for q in qrows if q[0] == "E3")
        self.assertTrue(e3[3].startswith("否"))
        self.assertEqual(sum(1 for q in qrows if q[3] == "是"), 16)

    def test_cli_research_offline(self):
        out = self.dest / "cli.xlsx"
        code = ff.cli_research_export([str(self.dest), str(out), "--group", "遊戲班", "--grade", "國小", "--offline"])
        self.assertEqual(code, 0)
        txt = (self.dest / ff.RESEARCH_SUMMARY_NAME).read_text("utf-8")
        self.assertIn("篩選：組別 遊戲班；版本 國小", txt)
        self.assertIn("學生 2 人", txt)
        self.assertIn("_分析用_elem.csv", txt)
        self.assertTrue(out.exists())
        self.assertEqual(ff.cli_research_export([str(self.dest), str(out), "--group", "老師", "--offline"]), 1)
        self.assertIn("組別必須是", (self.dest / ff.RESEARCH_SUMMARY_NAME).read_text("utf-8"))
        self.assertEqual(ff.cli_research_export([str(self.dest), str(out), "--bogus"]), 1)

    def test_remote_404_shows_no_research_data(self):
        r = mock.Mock(status_code=404, headers={})
        s = mock.Mock(get=mock.Mock(return_value=r))
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "x.xlsx"
            res = ff.run_research_export(Path(d), out, session=s, log=self.logs.append)
            urls = [c[0][0] for c in s.get.call_args_list]             # v7.1：另查 feedback/responses（課後問卷）
            self.assertIn("feedback/test", urls[0])
            self.assertIn("feedback/responses", urls[-1])
            self.assertEqual((res["remote"], res["local"], res["students"]), (0, 0, 0))
            self.assertTrue(any("尚無研究資料" in m for m in self.logs))
            self.assertTrue(out.exists())
            self.assertEqual(load_workbook(out)["分析用_國小elem"].max_row, 1)

    def test_download_goes_to_test_json_only(self):
        listing = mock.Mock(status_code=200, headers={})
        listing.json.return_value = [{"type": "file", "name": "20261205-090000_pre_newnew.json", "download_url": "u1"}]
        good = mock.Mock(status_code=200, headers={}, content=json.dumps(
            rrec("pre", "2026-12-05T09:00:00+08:00", "n" * 12), ensure_ascii=False).encode("utf-8"))
        empty = mock.Mock(status_code=200, headers={})              # v7.1：feedback/responses 清單（空）
        empty.json.return_value = []
        s = mock.Mock(get=mock.Mock(side_effect=[listing, good, empty]))
        with tempfile.TemporaryDirectory() as d:
            res = ff.run_research_export(Path(d), Path(d) / "y.xlsx", session=s, log=self.logs.append)
            self.assertEqual((res["remote"], res["new"], res["students"]), (1, 1, 1))
            self.assertTrue((Path(d) / "test_json" / "20261205-090000_pre_newnew.json").exists())
            self.assertFalse((Path(d) / ff.GAME_JSON_SUBDIR).exists())
            self.assertFalse((Path(d) / "json" / "20261205-090000_pre_newnew.json").exists())

    def test_game_export_ignores_test_json(self):
        """原有遊戲前後測只讀 game_json：test_json 內的研究紀錄不會混進去。"""
        out = self.dest / "g.xlsx"
        res = ff.run_game_export(self.dest, out, offline=True, log=self.logs.append)
        self.assertEqual((res["local"], res["kept"]), (0, 0))

    def test_ua_and_default_name(self):
        self.assertEqual(ff.ua_summary("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/156.0 Mobile Safari/537.36"),
                         "Android／Chrome")
        self.assertEqual(ff.ua_summary("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Safari/604.1"), "iPhone／Safari")
        self.assertEqual(ff.ua_summary("Mozilla/5.0 (iPhone) Line/14.0"), "iPhone／LINE")
        self.assertEqual(ff.ua_summary(""), "")
        now = ff.datetime(2026, 12, 1, 18, 5)
        self.assertEqual(ff.research_default_name(None, None, now), "研究用前後測_全部_匯出20261201-1805.xlsx")
        self.assertEqual(ff.research_default_name(ff.parse_user_time("2026-12-01 08:00"),
                                                  ff.parse_user_time("2026-12-01 17:00", True), now),
                         "研究用前後測_20261201-0800至20261201-1700_匯出20261201-1805.xlsx")


# ---------------------------------------------------------------- v7.1：研究資料夾＋學生版課後問卷
STUDENT_SAMPLES = Path(__file__).resolve().parent / "test_samples" / "student_feedback"   # 虛構作答，簡答不含姓名


class TestStudentSurvey(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dest = Path(self.tmp.name)
        for sub, src in ((ff.TEST_JSON_SUBDIR, SAMPLES), (ff.JSON_SUBDIR, STUDENT_SAMPLES)):
            (self.dest / sub).mkdir()
            for p in src.glob("*.json"):
                (self.dest / sub / p.name).write_bytes(p.read_bytes())
        self.logs = []

    def tearDown(self):
        self.tmp.cleanup()

    def surveys(self, codes=None, **kw):
        recs = ff.load_research_records(self.dest / ff.TEST_JSON_SUBDIR, log=self.logs.append)
        if codes is None:
            codes = {r["event"] for r in recs}
        rows = ff.load_survey_records(self.dest / ff.JSON_SUBDIR, recs, codes, log=self.logs.append)
        return {r["file"].split("_")[1][:6]: r for r in ff.filter_surveys(rows, **kw)}

    # -- 研究資料夾設定
    def test_research_dest_config_and_old_config(self):
        self.assertEqual(ff.DEFAULT_RESEARCH_DEST,
                         r"D:\01-FC東華\01-畢業論文及實驗\2026_蛇紋石DSW實驗記錄\05-論文WebAR\研究用前後測資料")
        with mock.patch.object(ff, "app_dir", return_value=self.dest):
            cfgp = self.dest / "config.json"
            cfgp.write_text(json.dumps({"dest": "D:\\old", "game_window": 20}), "utf-8")   # 舊 config（v7.0.0）
            self.assertEqual(ff.research_dest_from(ff.load_config()), ff.DEFAULT_RESEARCH_DEST)
            ff.save_research_dest("E:\\研究")
            self.assertEqual(ff.load_config(), {"dest": "D:\\old", "game_window": 20, "research_dest": "E:\\研究"})
            ff.save_config("D:\\new")                                   # 回饋問卷分頁存檔不影響研究資料夾
            self.assertEqual(ff.load_config(), {"dest": "D:\\new", "game_window": 20, "research_dest": "E:\\研究"})
            ff.save_config("D:\\new2", 30, "SEET2026-A155-07")
            cfg = ff.load_config()
            self.assertEqual((cfg["dest"], cfg["research_dest"]), ("D:\\new2", "E:\\研究"))
            self.assertEqual(ff.research_dest_from(cfg), "E:\\研究")
            self.assertFalse(any("token" in k.lower() for k in cfg))
            self.assertNotIn("token", cfgp.read_text("utf-8").lower())
        self.assertEqual(ff.research_dest_from({"research_dest": "  "}), ff.DEFAULT_RESEARCH_DEST)
        self.assertEqual(ff.research_dest_from({"research_dest": 5}), ff.DEFAULT_RESEARCH_DEST)

    # -- 挑選與排除
    def test_select_research_surveys_excludes_adult(self):
        self.assertTrue(ff.is_research_event("CTRL-E-20261201"))
        self.assertTrue(ff.is_research_event("game-j-20261203-2"))
        self.assertTrue(ff.is_research_event(" student-test "))
        self.assertTrue(ff.is_research_event("STUDY-GAME"))
        self.assertTrue(ff.is_research_event("STUDY-E-R2", {"study-e-r2"}))
        self.assertFalse(ff.is_research_event("STUDY-E-R2"))
        for ev in ("SEET2026-A155-07", "HL-STATION-2026-1127-CAVIAR", "HL-STATION-2026-1127", ""):
            self.assertFalse(ff.is_research_event(ev, {"CTRL-E-R2"}), ev)
        by = self.surveys()
        self.assertEqual(set(by), {"ctrle1", "ctrle2", "gamee1", "gamee2", "gamej1", "studye", "ctrlr2", "stutst"})
        self.assertNotIn("seet01", by)
        self.assertNotIn("cav001", by)
        # 不在研究紀錄、也不符合命名規則的代碼不納入
        self.assertNotIn("studye", self.surveys(codes=set()))

    def test_filters_time_event_group_grade(self):
        self.assertEqual(set(self.surveys(group="game")), {"gamee1", "gamee2", "gamej1", "studye"})
        self.assertEqual(set(self.surveys(group="control", grade="elem")), {"ctrle1", "ctrle2", "ctrlr2"})
        self.assertEqual(set(self.surveys(grade="junior")), {"gamej1"})
        self.assertEqual(set(self.surveys(event="ctrl-e-20261201")), {"ctrle1", "ctrle2"})   # 不分大小寫
        t = self.surveys(start=ff.parse_user_time("2026-12-01 10:00"), end=ff.parse_user_time("2026-12-01 11:00", True))
        self.assertEqual(set(t), {"ctrle1", "ctrle2", "gamee1"})

    # -- 組別／學段判定
    def test_group_grade_from_records_and_code(self):
        self.assertEqual(ff.infer_group_grade("CTRL-E-20261201"), ("control", "elem"))
        self.assertEqual(ff.infer_group_grade("game-j-20261203-2"), ("game", "junior"))
        self.assertEqual(ff.infer_group_grade("STUDY-GAME"), ("game", ""))
        self.assertEqual(ff.infer_group_grade("CTRL-TEST"), ("control", ""))
        self.assertEqual(ff.infer_group_grade("STUDENT-TEST"), ("", ""))
        by = self.surveys()
        s = by["studye"]                         # 代碼推不出組別 → 依研究紀錄 STUDY-E-R2（遊戲班國小）
        self.assertEqual((s["group"], s["grade"], s["basis"]), ("game", "elem", "研究紀錄"))
        c = by["ctrlr2"]                         # 小寫代碼也對到研究紀錄 CTRL-E-R2
        self.assertEqual((c["group"], c["grade"], c["basis"]), ("control", "elem", "研究紀錄"))
        g = by["gamej1"]
        self.assertEqual((g["group"], g["grade"], g["basis"]), ("game", "junior", "代碼推斷"))
        u = by["stutst"]
        self.assertEqual((u["group"], u["grade"], u["basis"]), ("", "", "無法判定"))
        # 研究紀錄優先於代碼：同 event 的研究紀錄寫遊戲班國中時以紀錄為準
        emap = ff.research_event_map([{"event": "CTRL-E-X", "group": "game", "grade": "junior"}])
        self.assertEqual(ff.survey_group_grade("ctrl-e-x", emap)[:2], ("game", "junior"))
        self.assertEqual(ff.survey_group_grade("CTRL-TEST", {}), ("control", "", "代碼推斷＋部分未知"))

    def test_student_feedback_set_labels(self):
        fs = ff.feedback_set("CTRL-E-20261201")
        self.assertIs(fs, ff.FEEDBACK_SETS[ff.BANK_STUDENT])
        self.assertEqual(fs["answer"], {"k1": "B", "k2": "C", "k3": "A"})
        self.assertIn("磨成很細的微米粉", dict(fs["knowledge"])["k1"])
        self.assertIs(ff.feedback_set("STUDENT-TEST"), fs)
        self.assertIs(ff.feedback_set("SEET2026-A155-07"), ff.FEEDBACK_SETS[ff.BANK_DEFAULT])     # 既有活動不變
        self.assertIs(ff.feedback_set("HL-STATION-2026-1127-CAVIAR"), ff.FEEDBACK_SETS[ff.EVENT_CAVIAR])
        # 一般回饋問卷分頁：研究代碼用學生版題組、成人版維持 default
        rows = ff.load_records(self.dest / ff.JSON_SUBDIR, log=self.logs.append)
        bank = {r["file"].split("_")[1][:6]: r["_bank"] for r in rows}
        self.assertEqual((bank["ctrle1"], bank["stutst"], bank["seet01"], bank["cav001"]),
                         (ff.BANK_STUDENT, ff.BANK_STUDENT, ff.BANK_DEFAULT, ff.EVENT_CAVIAR))
        stats = ff.compute_stats(rows)
        # 一般分頁不讀研究紀錄：只依命名規則判定，STUDY-E-R2 不符規則仍歸 default（研究匯出時才依研究紀錄納入）
        self.assertEqual(bank["studye"], ff.BANK_DEFAULT)
        self.assertEqual(stats["groups"][ff.BANK_STUDENT]["n"], 7)
        self.assertEqual(stats["groups"][ff.BANK_DEFAULT]["n"], 2)
        ff.aggregate(self.dest, log=self.logs.append)
        head = [c.value for c in load_workbook(self.dest / ff.XLSX_NAME)["回覆"][1]]
        self.assertIn("K1（依活動題目）(k1)", head)

    # -- 統計
    def test_survey_stats_numbers(self):
        rows = list(self.surveys().values())
        sst = ff.compute_survey_stats(rows)
        self.assertEqual(sst["n"], 8)
        self.assertEqual(sst["by_group"], {"game": 4, "control": 3, "": 1})
        self.assertEqual(sst["order"][0], ("game", "elem", "GAME-E-20261201"))
        self.assertEqual(sst["order"][-1], ("", "", "STUDENT-TEST"))
        d = sst["groups"][("control", "elem", "CTRL-E-20261201")]
        self.assertEqual(d["n"], 2)
        self.assertEqual((d["k"]["k1"][0], d["k"]["k2"][0], d["k"]["k3"][0]), (0.5, 1.0, 1.0))
        self.assertEqual(d["k_score"], (2.5, 2))
        self.assertEqual(d["items"]["a1"], (4.5, 0.707, 2))
        self.assertEqual(d["items"]["s3"][:2], (2.5, 0.707))
        self.assertAlmostEqual(d["facets"]["a"][0], (14 / 3 + 4) / 2, delta=0.002)
        self.assertEqual(d["facets"]["a"][2], 2)
        one = sst["groups"][("game", "junior", "GAME-J-20261203")]
        self.assertEqual((one["n"], one["items"]["a1"]), (1, (4, "", 1)))   # 1 份：標準差留白
        m = sst["merged"][("control", "elem")]                              # 合併 CTRL-E-20261201＋ctrl-e-r2
        self.assertEqual((m["n"], m["k"]["k3"][0]), (3, round(2 / 3, 4)))
        self.assertEqual(sst["all"]["n"], 8)
        txt = ff.survey_count_text(sst)
        self.assertEqual(txt, "課後問卷 8 份（遊戲班 4、對照班 3、組別未知 1）")

    def test_export_sheets_and_csv(self):
        out = self.dest / "r.xlsx"
        res = ff.run_research_export(self.dest, out, offline=True, log=self.logs.append)
        self.assertEqual((res["students"], res["surveys"]), (5, 8))
        wb = load_workbook(out)
        self.assertIn("課後問卷", wb.sheetnames)
        ws = wb["課後問卷"]
        hdr = [c.value for c in ws[1]]
        for col in ("序號", "活動代碼", "組別", "學段", "填答時間", "K1 作答", "K1 對錯(1/0；正解 B)", "知識答對數(0–3)",
                    "A1 沒有人要的石頭（像墨玉）也可能是可以再利用的資源", "環境態度平均", "行動意向平均", "科學探究平均",
                    "K 簡答：學到的一件新事情", "S 簡答：最想用實驗弄清楚的問題", "裝置摘要", "檔名"):
            self.assertIn(col, hdr)
        rows = [dict(zip(hdr, r)) for r in ws.iter_rows(min_row=2, values_only=True)]
        self.assertEqual(len(rows), 8)
        self.assertNotIn("SEET2026-A155-07", {r["活動代碼"] for r in rows})
        u = next(r for r in rows if r["活動代碼"] == "STUDENT-TEST")
        self.assertEqual((u["組別"], u["學段"]), ("未知", "未知"))
        g = next(r for r in rows if r["檔名"] == "20261201-110000_gamee1.json")
        self.assertEqual((g["組別"], g["學段"], g["知識答對數(0–3)"], g["環境態度平均"], g["裝置摘要"]),
                         ("遊戲班", "國小", 3, 5, "Windows／Chrome"))
        flat = [str(v) for r in wb["課後問卷統計"].iter_rows(values_only=True) for v in r if v is not None]
        self.assertTrue(any("沒有個人層級的對應" in s for s in flat))
        self.assertIn("對照班｜國小｜CTRL-E-20261201", flat)
        self.assertIn("遊戲班｜國中｜GAME-J-20261203", flat)
        self.assertIn("未知｜未知｜STUDENT-TEST", flat)
        self.assertIn("對照班｜國小", flat)
        self.assertIn("環境態度標準差", flat)
        p = Path(res["survey_csv"])
        self.assertEqual(p.name, "r_課後問卷_分析用.csv")
        self.assertTrue(p.read_bytes().startswith(b"\xef\xbb\xbf"))
        with open(p, encoding="utf-8-sig", newline="") as f:
            crow = list(csv.reader(f))
        self.assertEqual(crow[0], ff.survey_columns())
        self.assertTrue(all(re.fullmatch(r"[a-z_0-9]+", c) for c in crow[0]))
        for c in ("event", "group", "grade", "k1_correct", "k3_correct", "a1", "s3", "attitude_mean",
                  "action_mean", "inquiry_mean"):
            self.assertIn(c, crow[0])
        self.assertEqual(len(crow), 9)
        d = [dict(zip(crow[0], r)) for r in crow[1:]]
        self.assertEqual({x["group"] for x in d}, {"game", "control", "unknown"})
        c1 = next(x for x in d if x["file"] == "20261201-100200_ctrle2.json")
        self.assertEqual((c1["group_code"], c1["grade"], c1["k1_correct"], c1["k2_correct"], c1["attitude_mean"]),
                         ("0", "elem", "0", "1", "4.0"))
        summ = "\n".join(self.logs)
        self.assertIn("課後問卷 8 份（遊戲班 4、對照班 3、組別未知 1）", summ)
        self.assertIn("_課後問卷_分析用.csv", summ)

    def test_cli_summary_and_filters(self):
        out = self.dest / "cli.xlsx"
        code = ff.cli_research_export([str(self.dest), str(out), "--group", "對照班", "--offline"])
        self.assertEqual(code, 0)
        txt = (self.dest / ff.RESEARCH_SUMMARY_NAME).read_text("utf-8")
        self.assertIn("課後問卷 3 份（遊戲班 0、對照班 3）", txt)
        self.assertIn("對照班｜國小｜CTRL-E-20261201：2 份", txt)
        self.assertIn("CSV（課後問卷）：", txt)
        self.assertEqual(load_workbook(out)["課後問卷"].max_row, 4)

    def test_empty_surveys(self):
        """沒有任何研究問卷（只有成人版、或 json 不存在）：工作表照建並寫「尚無課後問卷」，不報錯。"""
        for p in list((self.dest / ff.JSON_SUBDIR).glob("*.json")):
            if not p.name.endswith(("seet01.json", "cav001.json")):
                p.unlink()
        out = self.dest / "e.xlsx"
        res = ff.run_research_export(self.dest, out, offline=True, log=self.logs.append)
        self.assertEqual(res["surveys"], 0)
        wb = load_workbook(out)
        self.assertEqual(wb["課後問卷"]["A2"].value, "尚無課後問卷")
        flat = [str(v) for r in wb["課後問卷統計"].iter_rows(values_only=True) for v in r if v is not None]
        self.assertIn("尚無課後問卷", flat)
        with open(res["survey_csv"], encoding="utf-8-sig", newline="") as f:
            self.assertEqual(len(list(csv.reader(f))), 1)
        self.assertIn("課後問卷 0 份（遊戲班 0、對照班 0）", "\n".join(self.logs))
        with tempfile.TemporaryDirectory() as d:                     # 研究資料夾全空（沒有 json、test_json）
            res = ff.run_research_export(Path(d), Path(d) / "z.xlsx", offline=True, log=lambda m: None)
            self.assertEqual((res["local"], res["surveys"]), (0, 0))
            self.assertEqual(load_workbook(Path(d) / "z.xlsx")["課後問卷"]["A2"].value, "尚無課後問卷")
        sst = ff.compute_survey_stats([])
        self.assertEqual((sst["n"], sst["order"], sst["all"]["k_score"]), (0, [], ("", 0)))

    def test_survey_download_to_json_and_failure_tolerated(self):
        listing_t = mock.Mock(status_code=200, headers={})
        listing_t.json.return_value = []
        listing_r = mock.Mock(status_code=200, headers={})
        listing_r.json.return_value = [{"type": "file", "name": "20261205-100000_newstu.json", "download_url": "u9"}]
        body = json.loads((STUDENT_SAMPLES / "20261201-110000_gamee1.json").read_text("utf-8"))
        body["event"] = "GAME-E-20261205"
        good = mock.Mock(status_code=200, headers={}, content=json.dumps(body, ensure_ascii=False).encode("utf-8"))
        s = mock.Mock(get=mock.Mock(side_effect=[listing_t, listing_r, good]))
        with tempfile.TemporaryDirectory() as d:
            res = ff.run_research_export(Path(d), Path(d) / "y.xlsx", session=s, log=self.logs.append)
            self.assertTrue((Path(d) / "json" / "20261205-100000_newstu.json").exists())
            self.assertEqual((res["survey_remote"], res["survey_new"], res["surveys"]), (1, 1, 1))
        bad = mock.Mock(status_code=500, headers={})                  # responses 失敗：前後測仍照常匯出
        s2 = mock.Mock(get=mock.Mock(side_effect=[listing_t, bad]))
        with tempfile.TemporaryDirectory() as d:
            res = ff.run_research_export(Path(d), Path(d) / "y.xlsx", session=s2, log=self.logs.append)
            self.assertTrue((Path(d) / "y.xlsx").exists())
            self.assertTrue(any("回饋問卷下載失敗" in m for m in self.logs))


if __name__ == "__main__":
    live = "--live" in sys.argv
    if live:
        sys.argv.remove("--live")
    res = unittest.main(exit=False, verbosity=2).result
    if live:
        with tempfile.TemporaryDirectory() as d:
            out = ff.run_fetch(Path(d), None, log=lambda m: print("  [live]", m))
            print(f"LIVE: GitHub 上 {out['remote']} 筆、彙整 {out['total']} 筆")
    sys.exit(0 if res.wasSuccessful() else 1)
