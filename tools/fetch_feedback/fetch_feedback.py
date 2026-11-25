# -*- coding: utf-8 -*-
"""撈取 GitHub 問卷資料（WebAR 回饋問卷下載與彙整）

來源：GitHub repo rlirdo/serpentine-webar 的 feedback/responses/*.json
      （schema = webar-feedback-v2；舊回覆為 webar-feedback-v1，由 Apps Script 中繼寫入）
輸出：<目的資料夾>\\json\\*.json、回饋問卷彙整.csv（UTF-8 BOM）、
      回饋問卷彙整.xlsx（工作表「回覆」「統計」「簡答」）、下載紀錄.log

v2（2026/10/29）：環境知識（k1–k3 四選一，有正解）、環境態度（a1–a3）、行動意向（i1–i3）、
科學探究（s1–s3）五點量表，各面向 1 題簡答（*_open）。彙整以 v2 欄位為主，v1 列以空值補齊並標版本，
v1 原欄位附在右側保留。

不互動模式：撈取GitHub問卷與遊戲前後測資料.exe --aggregate <資料夾>
            只把 <資料夾>\\json\\ 重新彙整（不連網），結果寫入 <資料夾>\\彙整結果.txt 後結束。

v3（2026/10/29）：新增「WebAR 遊戲前後測」：feedback/game/*.json（schema = webar-game-v1）
下載到 <目的資料夾>\\game_json\\，可依起迄時間篩選、同一玩家代碼（pid）N 分鐘內重複的前測／後測
只取第一筆，以 sid 配對前後測，匯出 Excel（玩家彙整／前測／後測／已略過(重複)／統計／題目對照）。
            撈取GitHub問卷與遊戲前後測資料.exe --game-export <資料夾> <輸出.xlsx>
                [--from "YYYY-MM-DD HH:MM"] [--to "YYYY-MM-DD HH:MM"] [--window 30] [--offline]
            摘要寫入 <資料夾>\\遊戲前後測_匯出結果.txt 後結束（--offline 不連網，只用本機 game_json）。

v4（2026/11/04）：遊戲紀錄同時接受 webar-game-v1 與 webar-game-v2（新遊戲「墨玉護衛隊：花蓮綠晶行動」，
方向盤版 mode=drive，多了 年齡 age／性別 gender／學校或單位 org／主角 hero；v1 紀錄這些欄位留空）。
各工作表加「活動、年齡、性別、學校／單位、主角」欄；統計加「依活動分組的人數與前後測平均」「年齡帶／性別分布」。
可依活動篩選：GUI「活動」下拉；CLI 加 [--event <活動代碼>]（不給或「全部」＝不篩選）。

v5（2026/11/05）：支援 11/27 花蓮站「幻彩人工魚子醬」活動（HL-STATION-2026-1127-CAVIAR）。
遊戲題庫依紀錄的 event 切換（QUESTION_BANKS；找不到活動＝default 墨玉題庫）；玩家彙整／前測／後測／統計／
題目對照都用該活動的題目、正解與面向，題目對照加「活動（題庫）」欄。回饋問卷的知識題正解與題目標籤也依 event
切換（FEEDBACK_SETS；人工魚子醬 k1=B、k2=C、k3=A）。GUI 選到人工魚子醬時自動建議專案的目的資料夾。

v6（2026/11/11）：同步「晶球護衛隊 2.0」：CAVIAR_BANK（初階 elem／中階 junior）換成新題庫
（由 caviar/tools/out/bank_v2.json 程式產生）；新增高階活動 HL-STATION-2026-1127-CAVIAR-SR（中繼只收 elem|junior、
E/J 題號，遊戲把高階上傳成 grade junior、題號 S→J；本工具以 CAVIAR_SR_BANK 對應 senior 十題，題目對照標原題號）。
「版本」欄改顯示程度：人工魚子醬 elem→初階、junior→中階、-SR→高階（其他活動維持國小／國中）；統計加「依程度分組」。
以 HL-STATION-2026-1127-CAVIAR 篩選時一併納入 -SR 高階玩家；直接指定 -SR 只取高階。
org（「身分｜單位」）拆成「身分」「單位」兩欄（無「｜」時身分留空、單位＝原值），原「學校／單位」欄保留。

v7（2026/11/25）：新增「研究用前後測」：feedback/test/*.json（schema = webar-test-v1；遊戲班 group=game＝
遊戲研究模式 ?study=1、對照班 group=control＝test/ 測驗頁；前後測各同一份整份 10 題，態度題不計分）。
下載到 <目的資料夾>\\test_json\\（GitHub 尚無 feedback/test 時顯示「尚無研究資料」），以 sid 配對前後測、
同一 sid＋階段重複時留最早一筆，可依起迄時間／活動／組別／版本篩選，匯出 xlsx（學生彙整／分析用_國小elem／
分析用_國中junior／統計／已略過（重複）／題目對照）＋分析用 CSV（UTF-8 BOM，國小、國中各一檔）。
            撈取GitHub問卷與遊戲前後測資料.exe --research-export <資料夾> <輸出.xlsx>
                [--from ..] [--to ..] [--event 代碼] [--group 遊戲班|對照班] [--grade 國小|國中] [--offline]
            摘要寫入 <資料夾>\\研究用前後測_匯出結果.txt 後結束。原有問卷與遊戲前後測功能、輸出格式不變。

v7.1（2026/11/25）：
 1. 研究專用目的資料夾：研究分頁有自己的目的資料夾（預設 DEFAULT_RESEARCH_DEST，記在 config.json 的 research_dest，
    與 dest 互不影響；舊 config 沒有此鍵時用預設值）。研究分頁的 test_json\\、json\\（課後問卷）、xlsx／CSV／摘要檔都放這裡。
 2. 研究匯出納入學生版課後問卷（feedback/student.html，沿用 webar-feedback-v2 欄位、寫進 feedback/responses/）：
    研究匯出時一併下載 responses 到 <研究資料夾>\\json\\，挑出 event 屬於研究的問卷（本次研究紀錄出現的活動代碼、
    GAME-／CTRL- 開頭、CTRL-TEST／STUDY-GAME／STUDENT-TEST），依同樣的時間／活動／組別／學段篩選；組別與學段先看同 event
    的研究紀錄、否則由代碼推斷（GAME→遊戲班、CTRL→對照班；第二段 E→國小、J→國中），推不出來標「未知」。
    xlsx 加「課後問卷」「課後問卷統計」兩張工作表，另存 jamovi 用 CSV（<輸出檔名>_課後問卷_分析用.csv）。
    問卷沒有 sid，與前後測只能做班級層級比較。研究活動代碼的問卷（含一般回饋問卷分頁）改用學生版題組標籤（STUDENT_FACETS）。
    活動代碼規則：組別-學段-施測日期（GAME＝遊戲班、CTRL＝對照班；E＝國小、J＝國中），例 CTRL-E-20261201、GAME-J-20261203，
    同日同組多班加 -2。CLI --research-export 介面不變。

v7.2（2026/11/25）：學生版課後問卷（遊戲班）新增六題科技接受度（TAM，改編自 Davis, 1989；題目文字為草稿）：
    選填鍵 pe1–pe3（知覺易用性 PEOU）、pu1–pu3（知覺有用性 PU），1–5 整數。六題齊全且有效才採用；
    不齊或越界的那份，六題留空並在「科技接受度註記」欄標示（整份問卷照常納入）；沒有這些鍵的紀錄照舊。
    「課後問卷」加 PE1–PE3、PU1–PU3、知覺易用性平均、知覺有用性平均、科技接受度註記欄；
    「課後問卷統計」加「科技接受度（僅遊戲班作答）」區；課後問卷 CSV 加 pe1–pu3、peou_mean、pu_mean。
    一般回饋問卷分頁（成人版彙整）不加這六欄，帶 TAM 鍵的學生問卷照常彙整、輸出格式不變。
    摘要（GUI 研究分頁、CLI）加「其中含科技接受度題 N 份」。

安全原則：GitHub Token 只存在記憶體，不寫入任何檔案或日誌。
版本：7.2.0（2026/11/25）
"""
from __future__ import annotations

import csv
import json
import os
import queue
import re
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

APP_TITLE = "撈取 GitHub 問卷資料"
VERSION = "7.2.0"
OWNER = "rlirdo"
REPO = "serpentine-webar"
REMOTE_DIR = "feedback/responses"
API_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{REMOTE_DIR}"
DEFAULT_DEST = (r"D:\01-FC東華\02-研討會及發表文章\2026_研討會發表"
                r"\20261030-1101-環教研討會\05-回饋問卷")
DEFAULT_RESEARCH_DEST = (r"D:\01-FC東華\01-畢業論文及實驗\2026_蛇紋石DSW實驗記錄"     # v7.1：研究資料另放
                         r"\05-論文WebAR\研究用前後測資料")
CSV_NAME = "回饋問卷彙整.csv"
XLSX_NAME = "回饋問卷彙整.xlsx"
LOG_NAME = "下載紀錄.log"
SUMMARY_NAME = "彙整結果.txt"
JSON_SUBDIR = "json"
BAD_SUBDIR = "壞檔"
FONT_NAME = "微軟正黑體"
SAFE_NAME = re.compile(r"^[A-Za-z0-9_\-]+\.json$")
TIMEOUT = 20

SCHEMA_V1 = "webar-feedback-v1"
SCHEMA_V2 = "webar-feedback-v2"

# ---- v3：WebAR 遊戲前後測（feedback/game）
GAME_REMOTE_DIR = "feedback/game"
GAME_API_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{GAME_REMOTE_DIR}"
GAME_JSON_SUBDIR = "game_json"
SCHEMA_GAME = "webar-game-v1"
SCHEMA_GAME_V2 = "webar-game-v2"
GAME_SCHEMAS = (SCHEMA_GAME, SCHEMA_GAME_V2)
EVENT_ALL = "全部"
EVENT_CAVIAR = "HL-STATION-2026-1127-CAVIAR"
EVENT_CAVIAR_SR = "HL-STATION-2026-1127-CAVIAR-SR"   # v6：晶球護衛隊 2.0 高階（題號 S→J、grade junior 上傳）
EVENT_PRESETS = {                       # 活動代碼 → 顯示名（GUI 下拉、統計排序用）
    "SEET2026-A155-07": "10/30–11/01 環教研討會壁報",
    "HL-STATION-2026-1127": "11/27 花蓮站 墨玉護衛隊",
    EVENT_CAVIAR: "11/27 花蓮站 人工魚子醬",
    EVENT_CAVIAR_SR: "11/27 花蓮站 人工魚子醬（高階）",
}
# v6：以活動篩選時一併納入的子活動（同一場活動的高階玩家）；直接指定子活動則只取該活動
EVENT_FAMILY = {EVENT_CAVIAR: (EVENT_CAVIAR, EVENT_CAVIAR_SR)}
EVENT_SEP = "｜"                          # 下拉選項「代碼｜顯示名」
ORG_SEP = "｜"                            # v6：org＝「身分｜單位」
BANK_DEFAULT = "default"
CAVIAR_DEST = (r"D:\01-FC東華\05-專案\2026_科普列車_花蓮新城站"
               r"\07-20261127花蓮站科普列車\05-回饋問卷與遊戲前後測")
EVENT_DEFAULT_DEST = {EVENT_CAVIAR: CAVIAR_DEST,     # GUI 選到該活動時建議的目的資料夾
                      EVENT_CAVIAR_SR: CAVIAR_DEST}
GENDERS = ["男", "女", "其他", "不透露"]
AGE_BANDS = ["≤12 歲", "13–18 歲", "19–64 歲", "≥65 歲"]          # 與新遊戲主角年齡帶一致
NO_VALUE = "（未填）"
DEDUP_MINUTES_DEFAULT = 30
GAME_SUMMARY_NAME = "遊戲前後測_匯出結果.txt"
TZ_TPE = timezone(timedelta(hours=8), "Asia/Taipei")
GRADE_LABEL = {"elem": "國小", "junior": "國中"}
MODE_LABEL = {"ar": "AR", "play": "免相機", "drive": "方向盤版"}
PHASE_LABEL = {"pre": "前測", "post": "後測"}
GAME_FACETS = ["知識", "態度", "行動", "探究"]
N_PRE, N_POST, N_STAGES = 3, 5, 8

# 題庫：自 serpentine-webar/js/content.js 的 BANK 原樣複製（2026/10/29）；正解索引一律 0，
# 遊戲畫面會洗牌，但 JSON 的 pick 是原始選項索引。改題目時兩邊須同步。
QUESTION_BANK = {
    "elem": [
        {"id": "E1", "facet": "知識", "pre": True,
         "q": "把大石頭敲成很多小碎塊，露出來的表面會怎樣？",
         "options": ["變多", "變少", "不變", "消失"],
         "answer": 0, "explain": "切得越小，露出來的表面越多，越容易和水接觸。"},
        {"id": "E2", "facet": "探究", "pre": True,
         "q": "科學家猜「補好破洞的石頭會放出更多看不見的光」，接下來最該做什麼？",
         "options": ["用儀器做實驗檢查", "直接宣布是真的", "問朋友覺得對不對", "不用管它"],
         "answer": 0, "explain": "猜想要靠實驗證據來證明。"},
        {"id": "E3", "facet": "態度", "pre": True,
         "q": "沒人要的閒置石頭，你覺得可以怎麼看待它？",
         "options": ["可能是能再利用的資源", "一定是垃圾", "丟到河裡就好", "跟我沒有關係"],
         "answer": 0, "explain": "閒置石料經過研究，可能變成有用的材料。"},
        {"id": "E4", "facet": "知識", "pre": False,
         "q": "深層海水裡，哪一種離子最適合補進小晶的破洞？",
         "options": ["Mg²⁺", "Ca²⁺", "沙子", "塑膠粒"],
         "answer": 0, "explain": "Mg²⁺ 大小剛好；Ca²⁺ 個子比較大。"},
        {"id": "E5", "facet": "知識", "pre": False,
         "q": "遠紅外線是什麼？",
         "options": ["一種看不見的光（熱輻射）", "一種食物", "紅色的油漆", "一種聲音"],
         "answer": 0, "explain": "遠紅外線是眼睛看不見的光，也就是熱輻射。"},
        {"id": "E6", "facet": "行動", "pre": False,
         "q": "實驗洗下來的廢液，應該怎麼處理？",
         "options": ["收集起來交給專人處理", "倒進水槽", "倒進水溝", "倒在草地上"],
         "answer": 0, "explain": "廢液要收集處理，不能亂倒。"},
        {"id": "E7", "facet": "態度", "pre": False,
         "q": "調反應液時，為什麼用水、不用有毒的溶劑？",
         "options": ["比較安全也比較環保", "因為水比較貴", "有毒的才好玩", "沒有原因"],
         "answer": 0, "explain": "綠色化學：能用水就不用有毒溶劑。"},
        {"id": "E8", "facet": "行動", "pre": False,
         "q": "下面哪個做法最能節省能源？",
         "options": ["低溫慢慢烘、不用的燈要關", "一直開高溫烤箱", "冷氣開最冷再開窗", "電燈整天開著"],
         "answer": 0, "explain": "省電省能，就是愛護地球。"},
        {"id": "E9", "facet": "探究", "pre": False,
         "q": "第八關的「修復後（預期）」曲線代表什麼？",
         "options": ["科學家的預期，還要實驗證明", "已經百分之百證明", "隨便畫的", "跟石頭無關"],
         "answer": 0, "explain": "那是預期，真正的實驗還在進行中。"},
        {"id": "E10", "facet": "知識", "pre": False,
         "q": "遊戲裡的深層海水來自哪裡？",
         "options": ["花蓮外海的深海", "自來水管", "游泳池", "路邊水溝"],
         "answer": 0, "explain": "深層海水是花蓮在地的海洋資源。"},
    ],
    "junior": [
        {"id": "J1", "facet": "知識", "pre": True,
         "q": "把蛇紋石從塊狀磨成約 2–4 微米的粉末，主要改變了什麼？",
         "options": ["總表面積大幅增加", "化學式變成水", "質量變成零", "顏色一定變白"],
         "answer": 0, "explain": "粒徑越小，總表面積越大，可反應的位置越多。"},
        {"id": "J2", "facet": "探究", "pre": True,
         "q": "團隊推測「晶格修復後遠紅外放射增強」，要怎麼確認？",
         "options": ["用 FTIR／XRD／XPS 與放射率量測驗證", "用投票決定", "看網路留言", "只看石頭顏色"],
         "answer": 0, "explain": "工作假設需要儀器量測的證據支持。"},
        {"id": "J3", "facet": "態度", "pre": True,
         "q": "在地撿石人無償提供的閒置蛇紋石，最符合哪個觀念？",
         "options": ["邊緣資材增值、資源循環", "用一次就丟", "越多越好、盡量開採", "和永續無關"],
         "answer": 0, "explain": "把閒置資材轉成有用材料，是資源循環的精神。"},
        {"id": "J4", "facet": "知識", "pre": False,
         "q": "在離子交換的工作假設中，哪個離子較適合補入蛇紋石晶格空位？",
         "options": ["Mg²⁺", "Ca²⁺", "Na⁺", "Cl⁻"],
         "answer": 0, "explain": "蛇紋石 Mg₃Si₂O₅(OH)₄ 本身含鎂，Mg²⁺ 大小較合適。"},
        {"id": "J5", "facet": "知識", "pre": False,
         "q": "反應液中的 Fe³⁺ 扮演什麼角色？",
         "options": ["觸媒摻雜，錨定在表面羥基", "當作溶劑", "讓溶液結冰", "只是裝飾顏色"],
         "answer": 0, "explain": "Fe³⁺ 是觸媒摻雜，錨定在 ≡Mg–OH／≡Si–OH。"},
        {"id": "J6", "facet": "知識", "pre": False,
         "q": "「遠紅外線 4–14 微米」中的 4–14 微米指的是什麼？",
         "options": ["熱輻射的波長範圍", "粉末的重量", "溫度的單位", "實驗時間"],
         "answer": 0, "explain": "這裡的微米是波長單位，屬於熱輻射範圍。"},
        {"id": "J7", "facet": "行動", "pre": False,
         "q": "離心洗滌後含鹽的廢液，正確處理方式是？",
         "options": ["分類收集，交由實驗室廢液處理", "直接倒入水槽沖掉", "倒進雨水溝", "倒在花圃"],
         "answer": 0, "explain": "廢液分類收集是實驗室安全與環保的基本要求。"},
        {"id": "J8", "facet": "態度", "pre": False,
         "q": "乾燥為什麼選 50 °C、48 小時，而不是 200 °C？",
         "options": ["低溫省能，也較能保護結構", "高溫一定比較好", "時間越短越準", "溫度不重要"],
         "answer": 0, "explain": "低溫乾燥兼顧節能與結構保護。"},
        {"id": "J9", "facet": "探究", "pre": False,
         "q": "「修復後（預期）」曲線的正確解讀是？",
         "options": ["預期結果，尚待量測證實", "已發表的真實數據", "可以直接拿去宣傳", "可以直接當結論"],
         "answer": 0, "explain": "預期必須經過實驗量測才能成為結論。"},
        {"id": "J10", "facet": "行動", "pre": False,
         "q": "日常生活中，哪個行動最能呼應「珍惜在地資源」？",
         "options": ["減少浪費、物盡其用", "東西用一次就丟", "多買不需要的東西", "把垃圾丟進河川"],
         "answer": 0, "explain": "物盡其用就是珍惜資源。"},
    ],
}

# v6：11/27 花蓮站「晶球護衛隊 2.0」題庫（由 serpentine-webar/caviar/tools/out/bank_v2.json v2.0.0 程式產生，
# 對應 caviar/js/content.js 的 BANK；正解索引一律 0）。初階 elem／中階 junior 上傳 event＝HL-STATION-2026-1127-CAVIAR。
CAVIAR_BANK = {
    "elem": [
        {"id": "E1", "facet": "知識", "pre": True,
         "q": "做晶球用的海藻酸鈉，是從哪裡來的？",
         "options": ["海裡的褐藻（像海帶）", "海裡的魚卵（魚子）", "海水晒乾的海鹽", "海邊的珊瑚礁"],
         "answer": 0, "explain": "海藻酸鈉是褐藻細胞壁裡的多醣長鏈，和魚卵、海鹽都沒有關係。"},
        {"id": "E2", "facet": "探究", "pre": True,
         "q": "想知道「泡越久，球會不會越硬」，最好的做法是？",
         "options": ["只改泡的時間，其他條件都一樣", "時間和鈣液濃度一起改，比較快", "做一顆泡很久的球，捏捏看", "看別人做的球，比比看誰比較亮"],
         "answer": 0, "explain": "一次只改變一個條件、其他保持一樣，比較結果才知道是時間造成的。"},
        {"id": "E3", "facet": "態度", "pre": True,
         "q": "做出來的晶球很漂亮，可以吃嗎？",
         "options": ["不可以，這是實驗品不能吃", "可以，因為材料來自海藻", "用清水洗乾淨就可以吃", "只吃一顆小的沒關係"],
         "answer": 0, "explain": "實驗室的藥品和器材都不是食品級，洗過也一樣不能吃。"},
        {"id": "E4", "facet": "知識", "pre": False,
         "q": "紅色液滴進藍色鈣液，是誰把海藻長鏈扣在一起變成一層皮？",
         "options": ["鈣液裡的鈣離子 Ca²⁺", "鈣液裡的氯離子 Cl⁻", "紅液裡的紅色色素", "鈣液比較冷，讓紅液凝固"],
         "answer": 0, "explain": "鈣離子帶兩個正電，像手銬一樣一次扣住兩條海藻長鏈。"},
        {"id": "E5", "facet": "知識", "pre": False,
         "q": "為什麼液滴落下時會變成圓球？",
         "options": ["表面張力把液滴拉成圓球", "掉下來時被空氣吹成圓的", "鈣液從四面八方把它壓圓", "滴管的出口本來就是圓的"],
         "answer": 0, "explain": "表面張力讓液滴縮成表面最小的形狀，也就是圓球。"},
        {"id": "E6", "facet": "行動", "pre": False,
         "q": "實驗做完，剩下的紅色海藻酸鈉液應該怎麼處理？",
         "options": ["倒進鈣液變成膠，再當垃圾丟", "加很多水沖淡後倒進水槽", "倒進馬桶，用水沖掉就好", "倒回原本的藥品瓶裡保存"],
         "answer": 0, "explain": "紅液進到水管會遇到硬水結膠堵塞；倒回原瓶會汙染藥品。"},
        {"id": "E7", "facet": "態度", "pre": False,
         "q": "「反著滴」把藍色鈣液滴進紅液，球會拖尾巴變形，你怎麼看？",
         "options": ["順序會改變結果，失敗也能學到東西", "結果不好，代表這次實驗白做了", "反著滴才是正確的做法", "一定是鈣液太少才會這樣"],
         "answer": 0, "explain": "失敗的結果也是資料，它告訴我們誰在外、誰在內很重要。"},
        {"id": "E8", "facet": "行動", "pre": False,
         "q": "用過的藍色鈣液和洗球的水，應該怎麼處理？",
         "options": ["集中起來，加很多清水稀釋再倒掉", "鈣是養分，直接倒進花圃當肥料", "鈣液沒有毒，直接倒進水槽", "放著等水自己蒸發就好"],
         "answer": 0, "explain": "鈣液含鈣離子和氯離子，集中後加大量清水稀釋再排放比較安全。"},
        {"id": "E9", "facet": "探究", "pre": False,
         "q": "泡 60 秒的球一捏就爆汁，泡 180 秒的球捏不破，可以推論什麼？",
         "options": ["泡越久，鈣離子跑越深、皮越厚", "泡越久，球吸了更多水而變大", "180 秒那杯鈣液比較濃", "60 秒那顆裡面的紅液比較少"],
         "answer": 0, "explain": "兩顆只差在時間，鈣離子要慢慢往裡走，時間越長皮越厚。"},
        {"id": "E10", "facet": "知識", "pre": False,
         "q": "晶球外面的那層「皮」，最像生物身上的什麼？",
         "options": ["細胞膜，能讓小東西進出", "蛋殼，完全不讓東西進出", "骨頭，因為裡面有鈣", "魚鱗，一片一片疊起來"],
         "answer": 0, "explain": "這層膜和細胞膜一樣是半透膜，水和小東西可以通過。"},
    ],
    "junior": [
        {"id": "J1", "facet": "知識", "pre": True,
         "q": "海藻酸鈉溶在水裡（還沒加鈣）解離後，長鏈上帶什麼電荷？",
         "options": ["負電（羧基 –COO⁻）", "正電（Na⁺ 留在鏈上）", "不帶電（正負互相抵銷）", "要看加了多少鈣才知道"],
         "answer": 0, "explain": "Na⁺ 解離到水中，鏈上留下 –COO⁻，整條鏈帶負電、互相排斥而伸展，所以很黏。"},
        {"id": "J2", "facet": "探究", "pre": True,
         "q": "要驗證「膜厚和浸泡時間的開根號成正比」，應該記錄什麼？",
         "options": ["不同浸泡時間下的膜厚", "同一浸泡時間下各球的顏色", "不同落高下的晶球直徑", "不同鈣液濃度下的成球數"],
         "answer": 0, "explain": "自變項是浸泡時間，應變項是膜厚；其他條件固定（控制變因）。"},
        {"id": "J3", "facet": "態度", "pre": True,
         "q": "實驗室做的晶球不能食用，主要原因是？",
         "options": ["試劑與器材都不是食品級的", "因為晶球吃起來沒有味道", "因為氯化鈣是有毒的重金屬", "因為晶球放久會變色變硬"],
         "answer": 0, "explain": "安全守則第一條：實驗室絕對禁食；鈣也不是重金屬。"},
        {"id": "J4", "facet": "知識", "pre": False,
         "q": "「蛋盒模型」描述的是什麼？",
         "options": ["Ca²⁺ 嵌在兩條鏈 G 嵌段間形成交聯", "Na⁺ 嵌在兩條鏈之間形成交聯", "Ca²⁺ 與 Cl⁻ 排成蛋盒狀的晶體", "長鏈捲成小球，像蛋放在盒中"],
         "answer": 0, "explain": "Grant 等人 1973 年提出：Ca²⁺ 同時與兩條鏈 G 嵌段的羧基氧配位，像蛋放進蛋盒。"},
        {"id": "J5", "facet": "知識", "pre": False,
         "q": "紅液滴入鈣液（正向球化）時，凝膠膜為什麼由外向內生長？",
         "options": ["Ca²⁺ 由外往內擴散，外層先成膠", "海藻酸鏈由內往外擴散，先到表面", "表面張力把外層的鏈先壓成固體", "外層水分接觸空氣先蒸發變硬"],
         "answer": 0, "explain": "膠長在有海藻酸的一側；Ca²⁺ 從外面擴散進來，所以外層先成膠。"},
        {"id": "J6", "facet": "知識", "pre": False,
         "q": "反向球化（鈣液滴入海藻酸鈉浴）常拖尾或成片狀，主因是？",
         "options": ["浴液很黏，液滴未收成球就被拉長", "Ca²⁺ 濃度太低，無法形成凝膠膜", "Na⁺ 會把 Ca²⁺ 擋在液滴外面", "反向時不會發生離子交換反應"],
         "answer": 0, "explain": "連續相黏度高，黏滯力把液滴拉長，來不及靠表面張力收成球。"},
        {"id": "J7", "facet": "行動", "pre": False,
         "q": "用過的鈣液與洗球水（含 Ca²⁺、Cl⁻）較恰當的處理是？",
         "options": ["集中後以大量清水稀釋再排放", "直接倒入排水孔，反正是鹽類", "倒入花圃，鈣可以當作肥料", "和剩下的紅液混合後倒入水槽"],
         "answer": 0, "explain": "稀釋後排放；鹽分會影響土壤，紅液遇鈣結膠會堵塞水管。"},
        {"id": "J8", "facet": "態度", "pre": False,
         "q": "二次熟化後球變硬、不透明且略縮小，對材料設計的啟示是？",
         "options": ["交聯程度可調控硬度與孔隙，依用途設計", "熟化越久越好，應一律延長浸泡", "變硬變不透明代表失敗，應丟棄", "只是外觀改變，材料性質不受影響"],
         "answer": 0, "explain": "控制時間就能控制交聯程度，這是材料設計可調的變因。"},
        {"id": "J9", "facet": "探究", "pre": False,
         "q": "一顆 0.05 mL 液滴只需約 2.5 µmol Ca²⁺，鈣液含量遠多於此，代表成膜的限制因素是？",
         "options": ["Ca²⁺ 向內擴散的速率", "鈣液中 Ca²⁺ 總量不足", "液滴中海藻酸鈉不足", "鈣液中 Cl⁻ 的濃度"],
         "answer": 0, "explain": "計量上鈣遠遠過量，所以限制成膜快慢的是擴散，而不是總量。"},
        {"id": "J10", "facet": "行動", "pre": False,
         "q": "班上要做晶球，哪個做法最能減少產生的廢液？",
         "options": ["依人數估算用量，鈣液可連續用於多批", "多配一些備用，用不完再倒掉", "每做一批就換新鈣液，結果較準", "用剩的紅液加水稀釋後倒掉"],
         "answer": 0, "explain": "鈣液中的鈣遠多於每批所需，可重複使用；事先估量能從源頭減少廢液。"},
    ],
}

# v6：高階 senior（S1–S10）。中繼只收 grade elem|junior、題號 E/J，故遊戲上傳成 grade "junior"、
# event＝HL-STATION-2026-1127-CAVIAR-SR、題號 S→J（S3→J3）。索引鍵用上傳後題號，src_id 為遊戲原題號。
CAVIAR_SR_BANK = {
    "junior": [
        {"id": "J1", "src_id": "S1", "facet": "知識", "pre": True,
         "q": "為什麼 Ca²⁺ 能使海藻酸鈉成膠，Na⁺ 卻不能？",
         "options": ["Ca²⁺ 為二價，可同時配位兩條鏈的 G 嵌段", "Ca²⁺ 半徑遠大於 Na⁺，能填滿鏈間空隙", "Ca²⁺ 與羧基形成共價酯鍵，Na⁺ 不能", "Ca²⁺ 使 pH 下降，羧基質子化而沉澱"],
         "answer": 0, "explain": "一價 Na⁺ 只能中和單一羧基；二價 Ca²⁺ 可橋接兩條鏈形成交聯點（Ca²⁺ 與 Na⁺ 半徑相近，且為離子配位而非共價鍵）。"},
        {"id": "J2", "src_id": "S2", "facet": "探究", "pre": True,
         "q": "要探討 CaCl₂ 濃度對膜厚的影響，下列設計何者最恰當？",
         "options": ["固定其他條件，只改 CaCl₂ 濃度，每組重複三次", "同時改變 CaCl₂ 濃度與浸泡時間，以減少組數", "每個濃度只做一顆，改用高倍顯微鏡精確量測", "固定 CaCl₂ 濃度，改變海藻酸鈉濃度並量膜厚"],
         "answer": 0, "explain": "自變項為 CaCl₂ 濃度、應變項為膜厚，其餘為控制變項；重複可估計變異。"},
        {"id": "J3", "src_id": "S3", "facet": "態度", "pre": True,
         "q": "有人說海藻酸鈉與氯化鈣本來就是食品添加物，實驗做的晶球可以吃。你的看法？",
         "options": ["不可食用：試劑與器材都非食品級", "可以吃：成分相同，就等同食品級", "沖掉表面鈣液後，就可以安心食用", "少量試吃一顆驗證口感，應無大礙"],
         "answer": 0, "explain": "化學名稱相同不等於食品級；試劑純度、器材與實驗環境都未符合食品衛生要求。"},
        {"id": "J4", "src_id": "S4", "facet": "知識", "pre": False,
         "q": "Mg²⁺ 與 Ca²⁺ 同為二價，為何 Mg²⁺ 幾乎無法使海藻酸成膠？",
         "options": ["Mg²⁺ 水合殼緊密，對 G 嵌段親和力低", "Mg²⁺ 電荷密度低，與羧基的吸引太弱", "Mg²⁺ 半徑太大，無法嵌入蛋盒空穴", "Mg²⁺ 與海藻酸立刻生成不溶沉澱"],
         "answer": 0, "explain": "Mg²⁺ 半徑小、水合作用強，不易脫去水合殼進入 G 嵌段的配位空穴，故對海藻酸的選擇性遠低於 Ca²⁺。"},
        {"id": "J5", "src_id": "S5", "facet": "知識", "pre": False,
         "q": "海藻酸的 G 嵌段比例提高，鈣凝膠的性質通常會怎樣？",
         "options": ["交聯區增多，凝膠較硬但較脆", "交聯區減少，凝膠較軟較有彈性", "只影響溶液黏度，不影響凝膠", "M 嵌段才是交聯區，故強度下降"],
         "answer": 0, "explain": "蛋盒交聯主要發生在 G 嵌段；高 G 凝膠剛性高、偏脆，高 M 凝膠較軟、較有彈性。"},
        {"id": "J6", "src_id": "S6", "facet": "行動", "pre": False,
         "q": "剩餘的 2% 海藻酸鈉紅液，最恰當的處理方式是？",
         "options": ["加入廢鈣液使其凝膠化，瀝乾後當固體廢棄物", "以大量清水稀釋後倒入排水孔，因可生物分解", "加熱濃縮減少體積後，再倒入排水孔", "與廢鈣液混合後，一起沖入排水孔"],
         "answer": 0, "explain": "海藻酸鈉在管路中遇硬水的 Ca²⁺ 會結膠堵塞；先凝膠化再以固體處理最穩當。"},
        {"id": "J7", "src_id": "S7", "facet": "探究", "pre": False,
         "q": "若膜厚受擴散控制（δ∝√t），浸泡 60 秒得膜厚 δ；要得到 2δ 約需浸泡多久？",
         "options": ["240 秒", "120 秒", "85 秒", "3600 秒"],
         "answer": 0, "explain": "δ∝√t，膜厚加倍需時間變 4 倍：60 × 4 = 240 秒。"},
        {"id": "J8", "src_id": "S8", "facet": "態度", "pre": False,
         "q": "評估以海藻酸鈣膜取代一次性塑膠包裝，下列哪種想法最周全？",
         "options": ["比較原料、能耗、保存到廢棄的全生命週期", "只要材料可生物分解，就一定比塑膠環保", "只看廢棄後能否在海中分解，就足以判斷", "只要成本比塑膠低，就值得全面推廣取代"],
         "answer": 0, "explain": "環境效益要看生命週期整體：原料、能耗、保存性與廢棄處理都要納入。"},
        {"id": "J9", "src_id": "S9", "facet": "知識", "pre": False,
         "q": "在 2% 海藻酸鈉液中加入少量 NaCl，黏度通常會怎樣？",
         "options": ["下降：鹽遮蔽電荷，鏈間排斥減弱而捲曲", "上升：Na⁺ 在鏈之間形成交聯點", "不變：Na⁺ 本來就是它的抗衡離子", "上升：離子強度增加使鏈更加伸展"],
         "answer": 0, "explain": "聚電解質效應：離子強度提高會遮蔽 –COO⁻ 之間的靜電排斥，鏈收縮、流體力學體積變小，黏度下降。"},
        {"id": "J10", "src_id": "S10", "facet": "行動", "pre": False,
         "q": "以海藻酸鈣珠吸附含 Cu²⁺ 廢水後，用過的珠子應如何處置？",
         "options": ["視為含重金屬廢棄物集中處理，或脫附再生", "材料可生物分解，可直接掩埋或堆肥", "曬乾後當作一般垃圾丟棄即可", "用清水沖洗後，珠子與洗液倒入排水孔"],
         "answer": 0, "explain": "重金屬被濃縮在珠子裡並未消失，必須依有害廢棄物處理或以酸脫附回收，不能隨可分解材料一起丟。"},
    ],
}

# 題庫依活動切換：key＝活動代碼（default＝其他所有活動，即墨玉題庫）
QUESTION_BANKS = {BANK_DEFAULT: QUESTION_BANK, EVENT_CAVIAR: CAVIAR_BANK, EVENT_CAVIAR_SR: CAVIAR_SR_BANK}
BANK_LABEL = {BANK_DEFAULT: "default（墨玉／蛇紋石題庫：環教研討會、墨玉護衛隊等）",
              EVENT_CAVIAR: f"{EVENT_CAVIAR}（{EVENT_PRESETS[EVENT_CAVIAR]}）",
              EVENT_CAVIAR_SR: f"{EVENT_CAVIAR_SR}（{EVENT_PRESETS[EVENT_CAVIAR_SR]}）"}
# v6：程度顯示（版本／年級欄）。人工魚子醬：elem→初階、junior→中階；-SR 活動一律高階；其他活動維持國小／國中
LEVEL_BY_BANK = {EVENT_CAVIAR: {"elem": "初階", "junior": "中階"},
                 EVENT_CAVIAR_SR: {"elem": "高階", "junior": "高階", "": "高階"}}
LEVEL_ORDER = ["國小", "國中", "初階", "中階", "高階"]


def level_label(grade, bank=BANK_DEFAULT) -> str:
    """grade（elem／junior）＋題庫 key → 顯示用程度（國小／國中／初階／中階／高階）。"""
    g = grade or ""
    m = LEVEL_BY_BANK.get(bank or BANK_DEFAULT)
    if m is not None:
        return m.get(g, g)
    return GRADE_LABEL.get(g, g)


def split_org(org) -> tuple[str, str]:
    """org「身分｜單位」→（身分, 單位）；沒有「｜」時身分留空、單位＝原值。"""
    s = _to_text(org).strip()
    if ORG_SEP in s:
        a, b = s.split(ORG_SEP, 1)
        return a.strip(), b.strip()
    return "", s


def display_qid(q: dict) -> str:
    """題號顯示：高階題附遊戲原題號，例如 J3（S3）。"""
    return q["id"] + (f"（{q['src_id']}）" if q.get("src_id") else "")


def _make_index(bank: dict) -> dict:
    return {q["id"]: dict(q, grade=g) for g, qs in bank.items() for q in qs}


QUESTION_INDEXES = {k: _make_index(b) for k, b in QUESTION_BANKS.items()}
QUESTION_INDEX = QUESTION_INDEXES[BANK_DEFAULT]           # 相容舊程式：default 題庫
PRE_IDS = {q["id"] for q in QUESTION_INDEX.values() if q.get("pre")}


def event_code(text) -> str:
    """下拉選項「代碼｜顯示名」或顯示名 → 活動代碼；其他字串原樣（去頭尾空白）。"""
    s = _to_text(text).strip()
    if EVENT_SEP in s:
        s = s.split(EVENT_SEP, 1)[0].strip()
    for code, name in EVENT_PRESETS.items():
        if s == name:
            return code
    return s


def bank_key_for_event(event) -> str:
    """活動代碼 → 題庫 key（去頭尾空白、不分大小寫；找不到＝default）。問卷正解表也用同一組 key。"""
    ev = event_code(event).lower()
    for k in QUESTION_BANKS:
        if k != BANK_DEFAULT and k.lower() == ev:
            return k
    return BANK_DEFAULT


def bank_index(event_or_key) -> dict:
    k = event_or_key if event_or_key in QUESTION_INDEXES else bank_key_for_event(event_or_key)
    return QUESTION_INDEXES[k]


def bank_pre_ids(key: str) -> set:
    return {q["id"] for q in QUESTION_INDEXES.get(key, QUESTION_INDEX).values() if q.get("pre")}

# ---- v2 題目（與 feedback/index.html 的 SECTIONS 同步）
# 知識題正解表：只放在本工具，不放在公開問卷網頁。
ANSWER_KEY = {"k1": "B", "k2": "C", "k3": "A"}
KNOWLEDGE = [
    ("k1", "K1 微米化的主要好處"),
    ("k2", "K2 補進晶格空位的離子"),
    ("k3", "K3 符合綠色化學的做法"),
]
FACETS = [  # (代碼, 面向名, [(欄位, 標籤)…], (簡答欄位, 簡答標籤))
    ("k", "環境知識", KNOWLEDGE, ("k_open", "K 簡答：學到的新知識")),
    ("a", "環境態度", [("a1", "A1 閒置石材可再利用"),
                     ("a2", "A2 認同綠色化學做法"),
                     ("a3", "A3 珍惜花蓮在地資源")], ("a_open", "A 簡答：看法的改變")),
    ("i", "行動意向", [("i1", "I1 垃圾分類與回收"),
                     ("i2", "I2 廢液廢棄物妥善處理"),
                     ("i3", "I3 分享再利用與綠色化學")], ("i_open", "I 簡答：想採取的行動")),
    ("s", "科學探究", [("s1", "S1 假設需實驗證據驗證"),
                     ("s2", "S2 對儀器找證據更感興趣"),
                     ("s3", "S3 想探究 Mg²⁺ 補晶格")], ("s_open", "S 簡答：最想實驗的問題")),
]
LIKERT_V2 = [k for code, _, items, _ in FACETS if code != "k" for k, _ in items]
OPENS_V2 = [f[3] for f in FACETS]

# v5：人工魚子醬回饋表（caviar/feedback；欄位同 webar-feedback-v2，題目不同）。正解只放本工具。
CAVIAR_ANSWER_KEY = {"k1": "B", "k2": "C", "k3": "A"}
CAVIAR_KNOWLEDGE = [
    ("k1", "K1 扣住海藻酸鈉長鏈形成薄膜的離子"),
    ("k2", "K2 讓液滴收縮成圓球的力量"),
    ("k3", "K3 海藻酸鈉萃取自哪一類生物"),
]
CAVIAR_FACETS = [
    ("k", "環境知識", CAVIAR_KNOWLEDGE, ("k_open", "K 簡答：記得的科學觀念")),
    ("a", "環境態度", [("a1", "A1 海裡藻類是值得珍惜的資源"),
                     ("a2", "A2 用水做實驗的綠色化學很重要"),
                     ("a3", "A3 科學遊戲有趣、想再玩")], ("a_open", "A 簡答：態度與想法")),
    ("i", "行動意向", [("i1", "I1 實驗廢液分類處理不亂倒"),
                     ("i2", "I2 減少一次性塑膠包裝"),
                     ("i3", "I3 分享晶球科學給家人朋友")], ("i_open", "I 簡答：想採取的行動")),
    ("s", "科學探究", [("s1", "S1 用實驗和觀察驗證想法"),
                     ("s2", "S2 改變一個條件再比較就是實驗"),
                     ("s3", "S3 更想查證「為什麼會這樣」")], ("s_open", "S 簡答：想探究的問題")),
]
# 回饋問卷題組依活動切換（key 與 QUESTION_BANKS 相同；找不到活動＝default）
FEEDBACK_SETS = {
    BANK_DEFAULT: {"answer": ANSWER_KEY, "knowledge": KNOWLEDGE, "facets": FACETS},
    EVENT_CAVIAR: {"answer": CAVIAR_ANSWER_KEY, "knowledge": CAVIAR_KNOWLEDGE, "facets": CAVIAR_FACETS},
}
FEEDBACK_SETS[EVENT_CAVIAR_SR] = FEEDBACK_SETS[EVENT_CAVIAR]   # v6：高階沿用人工魚子醬回饋問卷題組

# v7.1：學生版課後問卷（feedback/student.html；欄位同 webar-feedback-v2，題目改學生用語，題幹「上完這堂課後，我…」）。
# 正解同 default。研究用活動代碼（GAME-／CTRL- 開頭、CTRL-TEST、STUDY-GAME、STUDENT-TEST）的問卷用這一組。
BANK_STUDENT = "student"
STUDENT_ANSWER_KEY = {"k1": "B", "k2": "C", "k3": "A"}
STUDENT_KNOWLEDGE = [
    ("k1", "K1 把墨玉（蛇紋石）磨成很細的微米粉，最主要的好處是什麼？"),
    ("k2", "K2 加入花蓮外海的深層海水後，哪一種離子被設定為最適合補進蛇紋石晶格的空位？"),
    ("k3", "K3 配製反應液時，下列哪一個做法最符合「綠色化學」？"),
]
STUDENT_FACETS = [
    ("k", "環境知識", STUDENT_KNOWLEDGE, ("k_open", "K 簡答：學到的一件新事情")),
    ("a", "環境態度", [("a1", "A1 沒有人要的石頭（像墨玉）也可能是可以再利用的資源"),
                     ("a2", "A2 做實驗時應該先選用水，少用有毒的溶劑和強酸"),
                     ("a3", "A3 花蓮的在地資源值得珍惜和好好利用")], ("a_open", "A 簡答：想法的改變")),
    ("i", "行動意向", [("i1", "I1 願意做好垃圾分類和資源回收"),
                     ("i2", "I2 願意把廢液、廢棄物分類收好"),
                     ("i3", "I3 願意和家人、朋友分享在地資源再利用的想法")], ("i_open", "I 簡答：想做的環境行動")),
    ("s", "科學探究", [("s1", "S1 更了解「假設」要靠證據來檢查"),
                     ("s2", "S2 對用儀器找證據的探究方法更有興趣"),
                     ("s3", "S3 想進一步了解或動手探究「把鎂離子補進晶格」")], ("s_open", "S 簡答：最想用實驗弄清楚的問題")),
]
STUDENT_STEM = "上完這堂課後，我…"
FEEDBACK_SETS[BANK_STUDENT] = {"answer": STUDENT_ANSWER_KEY, "knowledge": STUDENT_KNOWLEDGE, "facets": STUDENT_FACETS}
BANK_LABEL[BANK_STUDENT] = "學生版課後問卷（研究用活動代碼 GAME-／CTRL-／CTRL-TEST／STUDY-GAME／STUDENT-TEST）"
STUDENT_DEFAULT_EVENT = "STUDENT-TEST"                       # 學生問卷單獨開、沒帶活動代碼時
RESEARCH_DEFAULT_EVENTS = ("CTRL-TEST", "STUDY-GAME", STUDENT_DEFAULT_EVENT)
RESEARCH_EVENT_PREFIXES = ("GAME-", "CTRL-")

# v7.2：學生版課後問卷（遊戲班）科技接受度 TAM 六題（選填；1–5 整數；改編自 Davis, 1989；題目文字為草稿）
TAM_FACETS = [  # (代碼, 構面名, 英文縮寫, [(欄位, 標籤)…], CSV 平均欄名)
    ("pe", "知覺易用性", "PEOU", [("pe1", "PE1 我覺得這個 WebAR 遊戲很容易操作"),
                                ("pe2", "PE2 我很快就學會怎麼玩這個遊戲"),
                                ("pe3", "PE3 遊戲裡的說明和提示我看得懂")], "peou_mean"),
    ("pu", "知覺有用性", "PU", [("pu1", "PU1 這個遊戲幫助我了解看不見的晶格和離子"),
                              ("pu2", "PU2 用這個遊戲學習，比只聽講解更容易懂"),
                              ("pu3", "PU3 我覺得這個遊戲對學習自然科學有幫助")], "pu_mean"),
]
TAM_ITEMS = [it for _, _, _, items, _ in TAM_FACETS for it in items]
TAM_KEYS = [k for k, _ in TAM_ITEMS]
TAM_SOURCE = "改編自 Davis（1989）科技接受模式；題目文字為草稿"


def _tam_int(v):
    """TAM 單題：1–5 整數（接受 4、4.0、"4"）才有效，其他回傳 None。"""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
        if not v:
            return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f or not f.is_integer() or not 1 <= f <= 5:
        return None
    return int(f)


def parse_tam(raw: dict) -> tuple[dict | None, str]:
    """原始 TAM 鍵 → (六題數值 dict 或 None, 註記)。
    完全沒有（或全為空值）＝(None, "")；六題齊全且皆為 1–5 整數＝(dict, "")；
    其他（不齊、越界、非整數）＝(None, 說明)，該份 TAM 六題留空，整份問卷照常保留。"""
    raw = raw or {}
    given = {k: raw[k] for k in TAM_KEYS
             if k in raw and raw[k] is not None and not (isinstance(raw[k], str) and not raw[k].strip())}
    if not given:
        return None, ""
    vals = {k: _tam_int(v) for k, v in given.items()}
    missing = [k for k in TAM_KEYS if k not in given]
    bad = [f"{k}={given[k]}" for k in TAM_KEYS if k in given and vals[k] is None]
    if not missing and not bad:
        return vals, ""
    parts = []
    if missing:
        parts.append("缺 " + "、".join(missing))
    if bad:
        parts.append("非 1–5 整數：" + "、".join(bad))
    return None, "科技接受度題不完整或無效（" + "；".join(parts) + "），六題留空"


def is_research_event(event, extra_codes=()) -> bool:
    """活動代碼是否屬於研究（不分大小寫）：GAME-／CTRL- 開頭、CTRL-TEST／STUDY-GAME／STUDENT-TEST，
    或等於 extra_codes（本次研究紀錄出現的活動代碼）中任一個。"""
    ev = _to_text(event).strip().upper()
    if not ev:
        return False
    if ev in RESEARCH_DEFAULT_EVENTS or ev.startswith(RESEARCH_EVENT_PREFIXES):
        return True
    return ev in {_to_text(c).strip().upper() for c in extra_codes if _to_text(c).strip()}


def infer_group_grade(event) -> tuple[str, str]:
    """由活動代碼推斷（組別, 學段）：第一段 GAME→game、CTRL→control（STUDY-GAME→game）；
    第二段 E→elem、J→junior。推不出來的部分回傳空字串。"""
    parts = _to_text(event).strip().upper().split("-")
    group = {"GAME": "game", "CTRL": "control"}.get(parts[0], "")
    if parts[0] == "STUDY" and len(parts) > 1 and parts[1] == "GAME":
        group = "game"
    grade = {"E": "elem", "J": "junior"}.get(parts[1], "") if len(parts) > 1 else ""
    return group, grade


def feedback_key_for_event(event) -> str:
    """回饋問卷題組 key：研究用活動代碼＝學生版；其他依活動題庫（找不到＝default）。"""
    if is_research_event(event_code(event)):
        return BANK_STUDENT
    return bank_key_for_event(event)


def feedback_set(event_or_key) -> dict:
    k = event_or_key if event_or_key in FEEDBACK_SETS else feedback_key_for_event(event_or_key)
    return FEEDBACK_SETS[k]


def answer_key_for(event) -> dict:
    return feedback_set(event)["answer"]


def knowledge_for(event) -> list:
    return feedback_set(event)["knowledge"]

# ---- v1 舊欄位（2026/10/22–10/28 的回覆；保留原欄位）
V1_FIELDS = [
    ("role", "v1 身分"),
    ("role_other", "v1 身分_其他"),
    ("teach_level", "v1 任教階段"),
    ("played", "v1 遊玩程度"),
    ("device", "v1 使用裝置"),
    ("q1_clear", "v1 Q1 說明清楚易懂"),
    ("q2_fun", "v1 Q2 遊戲有趣"),
    ("q3_easy", "v1 Q3 AR 操作容易"),
    ("q4_mechanism", "v1 Q4 更理解離子交換機制"),
    ("q5_feedback_useful", "v1 Q5 前後測與回饋有幫助"),
    ("q6_use_in_class", "v1 Q6 願意在課堂試用"),
    ("best_part", "v1 最喜歡的部分"),
    ("suggest", "v1 建議"),
    ("fit_level", "v1 適合年段"),
    ("contact_ok", "v1 願意收到邀請"),
    ("contact", "v1 聯絡 email"),
]
LIKERT_V1 = [k for k, _ in V1_FIELDS if k.startswith("q") and k[1].isdigit()]
ROLES = ["國小教師", "國中教師", "高中教師", "大專教師", "研究生", "大學生", "其他"]

# 彙整欄位順序：v2 為主（第一欄檔名），v1 原欄位附在右側
FIELDS = [("file", "檔名"), ("ver", "版本"), ("schema", "schema"),
          ("submitted_at", "填答時間"), ("event", "活動")]
for _code, _name, _items, _open in FACETS:
    for _k, _lab in _items:
        FIELDS.append((_k, _lab))
        if _code == "k":
            FIELDS.append((_k + "_ok", _lab.split()[0] + " 答對(1/0)"))
    if _code == "k":
        FIELDS.append(("k_score", "知識題答對數(0–3)"))
    FIELDS.append(_open)
FIELDS.append(("ua", "瀏覽器 UA"))
FIELDS.extend(V1_FIELDS)
NUMERIC = set(LIKERT_V2) | set(LIKERT_V1)
LABELS = dict(FIELDS)


class FetchError(Exception):
    """可顯示給使用者的友善錯誤。"""


# ---------------------------------------------------------------- 設定檔
def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def load_config() -> dict:
    p = app_dir() / "config.json"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_config(dest: str, game_window: int | None = None, event: str | None = None) -> None:
    # 只記憶目的資料夾、遊戲重複判定分鐘數與最後選的活動；絕不寫入 token
    p = app_dir() / "config.json"
    data = {"dest": dest}
    old = load_config()
    rd = old.get("research_dest")                       # v7.1：研究目的資料夾另存，這裡原樣保留
    if isinstance(rd, str) and rd.strip():
        data["research_dest"] = rd.strip()
    if game_window is None:
        game_window = old.get("game_window")
    if isinstance(game_window, int) and not isinstance(game_window, bool) and 1 <= game_window <= 720:
        data["game_window"] = game_window
    if event is None:
        event = old.get("event")
    if isinstance(event, str) and event.strip() and len(event) <= 80:
        data["event"] = event.strip()
    try:
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    except OSError:
        pass


def research_dest_from(cfg: dict) -> str:
    """config → 研究目的資料夾；舊 config 沒有 research_dest（或型別不對、空白）時用預設值。"""
    v = cfg.get("research_dest") if isinstance(cfg, dict) else None
    return v.strip() if isinstance(v, str) and v.strip() else DEFAULT_RESEARCH_DEST


def save_research_dest(path: str) -> None:
    """只更新 config.json 的 research_dest；dest、game_window、event 等既有鍵原樣保留（絕不寫入 token）。"""
    p = app_dir() / "config.json"
    data = load_config()
    data = {k: v for k, v in data.items() if "token" not in k.lower()}
    s = _to_text(path).strip()
    if s:
        data["research_dest"] = s
    else:
        data.pop("research_dest", None)
    try:
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


# ---------------------------------------------------------------- 網路
def _headers(token: str | None) -> dict:
    h = {"Accept": "application/vnd.github+json",
         "User-Agent": "fetch-feedback/" + VERSION,
         "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        h["Authorization"] = "Bearer " + token.strip()
    return h


def _check_response(r: requests.Response) -> None:
    if r.status_code == 200:
        return
    if r.status_code == 401:
        raise FetchError("Token 無效或已過期（401）。公開 repo 可把 Token 欄留空再試。")
    if r.status_code in (403, 429):
        remain = r.headers.get("X-RateLimit-Remaining")
        reset = r.headers.get("X-RateLimit-Reset")
        if remain == "0" or r.status_code == 429:
            when = ""
            if reset and reset.isdigit():
                when = datetime.fromtimestamp(int(reset)).strftime("%H:%M")
                when = f"，約 {when} 後恢復"
            raise FetchError("GitHub 未登入查詢次數已達上限（每小時 60 次）"
                             f"{when}。可在「GitHub Token」欄填入 token 後再試。")
        raise FetchError(f"GitHub 拒絕存取（{r.status_code}）。若有填 Token，請確認權限。")
    raise FetchError(f"GitHub 回應異常（HTTP {r.status_code}）。")


def list_remote(token: str | None = None, session=None, api_url: str = API_URL) -> list[dict]:
    """列出遠端資料夾（預設 responses；遊戲用 GAME_API_URL）內的 .json 檔（name, download_url, size）。
    資料夾尚不存在（404）視為 0 筆。"""
    s = session or requests
    items: dict[str, dict] = {}
    page = 1
    while True:
        try:
            r = s.get(api_url, headers=_headers(token),
                      params={"per_page": 100, "page": page}, timeout=TIMEOUT)
        except requests.RequestException as e:
            raise FetchError(f"網路連線失敗，請確認網路後再試。（{type(e).__name__}）")
        if r.status_code == 404:
            return []
        _check_response(r)
        try:
            data = r.json()
        except ValueError:
            raise FetchError("GitHub 回傳內容無法解析。")
        if not isinstance(data, list):
            return []
        new = 0
        for it in data:
            name = it.get("name", "")
            if it.get("type") == "file" and name.endswith(".json") and name not in items:
                items[name] = {"name": name, "download_url": it.get("download_url"),
                               "size": it.get("size", 0)}
                new += 1
        # contents API 一次最多回 1000 筆、不一定支援分頁；沒有新檔名就停止
        if len(data) < 100 or new == 0 or page >= 50:
            break
        page += 1
    return sorted(items.values(), key=lambda x: x["name"])


def local_names(dest: Path, subdir: str = JSON_SUBDIR) -> set[str]:
    names = set()
    for sub in (dest / subdir, dest / subdir / BAD_SUBDIR):
        if sub.is_dir():
            names.update(p.name for p in sub.glob("*.json"))
    return names


def download_new(dest: Path, remote: list[dict], token: str | None = None,
                 log=print, session=None, subdir: str = JSON_SUBDIR) -> tuple[int, int]:
    """只下載本機沒有的檔案到 dest\\subdir（預設 json；遊戲用 game_json）。回傳（成功數, 壞檔數）。"""
    s = session or requests
    jdir = dest / subdir
    jdir.mkdir(parents=True, exist_ok=True)
    have = local_names(dest, subdir)
    ok = bad = 0
    for it in remote:
        name = it["name"]
        if name in have:
            continue
        if not SAFE_NAME.match(name) or not it.get("download_url"):
            log(f"略過不合規檔名：{name}")
            continue
        try:
            r = s.get(it["download_url"], headers=_headers(token), timeout=TIMEOUT)
            _check_response(r)
        except requests.RequestException as e:
            log(f"下載失敗 {name}：{type(e).__name__}（下次會重試）")
            continue
        raw = r.content
        try:
            obj = json.loads(raw.decode("utf-8-sig"))
            if not isinstance(obj, dict):
                raise ValueError("不是物件")
            (jdir / name).write_bytes(raw)
            ok += 1
            log(f"已下載 {name}")
        except (ValueError, UnicodeDecodeError) as e:
            bdir = jdir / BAD_SUBDIR
            bdir.mkdir(exist_ok=True)
            (bdir / name).write_bytes(raw)
            bad += 1
            log(f"⚠ 壞檔（JSON 無法解析，已另存 {subdir}\\{BAD_SUBDIR}\\）：{name}（{e}）")
    return ok, bad


# ---------------------------------------------------------------- 彙整
def _version(obj: dict) -> str:
    sc = obj.get("schema")
    if sc == SCHEMA_V2:
        return "v2"
    if sc in (None, "", SCHEMA_V1):
        return "v1"
    return "未知"


def _to_score(v):
    if isinstance(v, bool):
        return ""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return ""
    if 1 <= f <= 5:
        return int(f) if f.is_integer() else f
    return ""


def _to_text(v) -> str:
    if v is None:
        return ""
    return v if isinstance(v, str) else str(v)


def load_records(jdir: Path, log=print) -> list[dict]:
    """讀取所有 JSON；v1、v2 都轉成同一組欄位（缺的欄位為空字串）。"""
    rows = []
    if not jdir.is_dir():
        return rows
    for p in sorted(jdir.glob("*.json")):
        try:
            obj = json.loads(p.read_text(encoding="utf-8-sig"))
            if not isinstance(obj, dict):
                raise ValueError("不是物件")
        except (OSError, ValueError) as e:
            log(f"⚠ 略過壞檔 {p.name}：{e}")
            continue
        ver = _version(obj)
        if ver == "未知":
            log(f"注意：{p.name} 的 schema 為 {obj.get('schema')}，仍嘗試彙整")
        rec = {k: "" for k, _ in FIELDS}
        rec["file"] = p.name
        rec["ver"] = ver
        for k in ("schema", "submitted_at", "event", "ua"):
            rec[k] = _to_text(obj.get(k))
        rec["_bank"] = feedback_key_for_event(rec["event"])    # v5：依活動選問卷題組（v7.1：研究代碼＝學生版）
        akey = FEEDBACK_SETS[rec["_bank"]]["answer"]
        if ver in ("v2", "未知"):
            score = 0
            answered = False
            for k, _ in KNOWLEDGE:
                a = _to_text(obj.get(k)).strip().upper()
                a = a if a in ("A", "B", "C", "D") else ""
                rec[k] = a
                if a:
                    answered = True
                    rec[k + "_ok"] = 1 if a == akey[k] else 0
                    score += rec[k + "_ok"]
            rec["k_score"] = score if answered else ""
            for k in LIKERT_V2:
                rec[k] = _to_score(obj.get(k))
            for k, _ in OPENS_V2:
                rec[k] = _to_text(obj.get(k)).strip()
            # v7.2：學生版 TAM 選填鍵（原值暫存於私有鍵；不屬 FIELDS，一般回饋問卷輸出不變）
            rec["_tam_raw"] = {k: obj[k] for k in TAM_KEYS if k in obj}
        if ver in ("v1", "未知"):
            for k, _ in V1_FIELDS:
                rec[k] = _to_score(obj.get(k)) if k in LIKERT_V1 else _to_text(obj.get(k))
        rows.append(rec)
    rows.sort(key=lambda r: (r.get("submitted_at") or "", r["file"]))
    return rows


def _mean(vals: list) -> float | None:
    return round(sum(vals) / len(vals), 2) if vals else None


def _feedback_labels(bank: str) -> dict:
    """題組 → {欄位: 標籤}（知識題、答對欄、量表、簡答）。"""
    out = {}
    for code, _, items, (ok, olab) in FEEDBACK_SETS[bank]["facets"]:
        for k, lab in items:
            out[k] = lab
            if code == "k":
                out[k + "_ok"] = lab.split()[0] + " 答對(1/0)"
        out[ok] = olab
    return out


def _row_bank(r: dict) -> str:
    return r.get("_bank") or BANK_DEFAULT


def field_labels(rows: list[dict]) -> list[tuple[str, str]]:
    """CSV／XLSX「回覆」表頭：v2 列只有一種題組→用該題組標籤；混合多個活動題組→「K1（依活動題目）」。"""
    banks = {_row_bank(r) for r in rows if r.get("ver") != "v1"}
    if not banks or banks == {BANK_DEFAULT}:
        return list(FIELDS)
    if len(banks) == 1:
        labs = _feedback_labels(next(iter(banks)))
        return [(k, labs.get(k, lab)) for k, lab in FIELDS]
    labs = _feedback_labels(BANK_DEFAULT)
    out = []
    for k, lab in FIELDS:
        if k in labs and not k.endswith("_ok"):
            first = lab.split()[0]
            lab = first + (" 簡答" if "簡答" in lab else "") + "（依活動題目）"
        out.append((k, lab))
    return out


def _feedback_group(v2: list[dict], fs: dict) -> dict:
    akey = fs["answer"]
    knowledge = {}
    for k, _ in fs["knowledge"]:
        ans = [r[k] for r in v2 if r.get(k)]
        correct = sum(1 for a in ans if a == akey[k])
        knowledge[k] = {"answer": akey[k], "n": len(ans), "correct": correct,
                        "rate": round(correct / len(ans), 4) if ans else None,
                        "dist": {c: ans.count(c) for c in "ABCD"}}
    scores = [r["k_score"] for r in v2 if isinstance(r.get("k_score"), int)]
    likert = {}
    facets = {}
    for code, name, items, _ in fs["facets"]:
        if code == "k":
            continue
        pool = []
        for k, _ in items:
            vals = [r[k] for r in v2 if isinstance(r.get(k), (int, float))]
            likert[k] = (_mean(vals), len(vals))
            pool.extend(vals)
        facets[code] = (_mean(pool), len(pool))
    return {"n": len(v2), "knowledge": knowledge, "k_score_mean": (_mean(scores), len(scores)),
            "likert": likert, "facets": facets}


def compute_stats(rows: list[dict]) -> dict:
    v2_keys = [k for k, _ in KNOWLEDGE] + LIKERT_V2
    v2 = [r for r in rows if r["ver"] == "v2"
          or (r["ver"] == "未知" and any(r.get(k) != "" for k in v2_keys))]
    v1 = [r for r in rows if r["ver"] == "v1"]
    # v5：依活動題組分組統計（題目不同不可混算）；頂層 knowledge／likert／facets＝default 題組（相容舊版）
    banks = [b for b in FEEDBACK_SETS if any(_row_bank(r) == b for r in v2)] or [BANK_DEFAULT]
    groups = {b: _feedback_group([r for r in v2 if _row_bank(r) == b], FEEDBACK_SETS[b]) for b in banks}
    base = groups.get(BANK_DEFAULT) or _feedback_group(
        [r for r in v2 if _row_bank(r) == BANK_DEFAULT], FEEDBACK_SETS[BANK_DEFAULT])
    v1_means = {}
    for k in LIKERT_V1:
        vals = [r[k] for r in v1 if isinstance(r.get(k), (int, float))]
        v1_means[k] = (_mean(vals), len(vals))
    roles = {r: 0 for r in ROLES}
    for r in v1:
        role = r.get("role") or "（未填）"
        roles[role] = roles.get(role, 0) + 1
    opens = []  # (檔名, 填答時間, 版本, 面向, 題目, 內容)
    for r in rows:
        for code, name, _, (k, lab) in FEEDBACK_SETS[_row_bank(r)]["facets"]:
            if r.get(k):
                opens.append((r["file"], r["submitted_at"], r["ver"], name, lab, r[k]))
        if r["ver"] == "v1":
            for k in ("best_part", "suggest"):
                if r.get(k):
                    opens.append((r["file"], r["submitted_at"], "v1", "v1 開放題", LABELS[k], r[k]))
    return {"total": len(rows), "n_v2": len(v2), "n_v1": len(v1),
            "knowledge": base["knowledge"], "k_score_mean": base["k_score_mean"],
            "likert": base["likert"], "facets": base["facets"],
            "banks": banks, "groups": groups,
            "v1_means": v1_means, "roles": roles, "opens": opens}


def _csv_safe(v):
    # 防 CSV／Excel 公式注入（公開問卷的開放題）
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + v
    return v


def write_csv(rows: list[dict], path: Path) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow([f"{lab}({k})" for k, lab in field_labels(rows)])
        for r in rows:
            w.writerow([_csv_safe(r.get(k, "")) for k, _ in FIELDS])


def _style_header(cells, hfont, hfill):
    for c in cells:
        c.font, c.fill = hfont, hfill
        c.alignment = Alignment(wrap_text=True, vertical="center")


def _as_text(ws_row):
    for c in ws_row:
        if isinstance(c.value, str) and c.value.startswith("="):
            c.data_type = "s"  # 以文字保存，不當公式


def _bank_suffix(stats: dict, bank: str) -> str:
    """統計表區段標題的活動後綴：只有 default 題組時不加（與舊版相同）。"""
    if stats.get("banks", [BANK_DEFAULT]) == [BANK_DEFAULT]:
        return ""
    return "｜" + BANK_LABEL.get(bank, bank)


def write_xlsx(rows: list[dict], stats: dict, path: Path) -> None:
    wb = Workbook()
    hfont = Font(name=FONT_NAME, bold=True, color="FFFFFF")
    hfill = PatternFill("solid", fgColor="0B1F3A")
    sfill = PatternFill("solid", fgColor="1C7293")
    bfont = Font(name=FONT_NAME)

    # 回覆
    ws = wb.active
    ws.title = "回覆"
    ws.append([f"{lab}({k})" for k, lab in field_labels(rows)])
    _style_header(ws[1], hfont, hfill)
    for r in rows:
        ws.append([r.get(k, "") for k, _ in FIELDS])
        for c in ws[ws.max_row]:
            c.font = bfont
        _as_text(ws[ws.max_row])
    wide = {"file": 30, "submitted_at": 26, "ua": 40, "best_part": 40, "suggest": 40, "contact": 26,
            "event": 22}
    for k, _ in OPENS_V2:
        wide[k] = 40
    for i, (k, _) in enumerate(FIELDS, 1):
        ws.column_dimensions[get_column_letter(i)].width = wide.get(k, 14)
    ws.freeze_panes = "C2"

    # 統計
    st = wb.create_sheet("統計")
    hdr_rows = []

    def hdr(*vals):
        st.append(list(vals))
        hdr_rows.append(st.max_row)

    banks = stats.get("banks", [BANK_DEFAULT])
    groups = stats.get("groups") or {BANK_DEFAULT: {
        "n": stats["n_v2"], "knowledge": stats["knowledge"], "k_score_mean": stats["k_score_mean"],
        "likert": stats["likert"], "facets": stats["facets"]}}
    hdr("項目", "數值", "有效筆數", "", "", "", "")
    st.append(["總回覆數", stats["total"], ""])
    st.append(["v2 回覆數（四面向問卷）", stats["n_v2"], ""])
    if banks != [BANK_DEFAULT]:
        for b in banks:
            st.append([f"　其中 {BANK_LABEL.get(b, b)}", groups[b]["n"], ""])
    st.append(["v1 回覆數（舊版問卷）", stats["n_v1"], ""])
    st.append([])
    for b in banks:
        g, fs, sfx = groups[b], FEEDBACK_SETS[b], _bank_suffix(stats, b)
        hdr("v2 環境知識題" + sfx, "正解", "作答數", "答對數", "答對率", "選項分布 A/B/C/D", "")
        for k, lab in fs["knowledge"]:
            kn = g["knowledge"][k]
            st.append([lab, kn["answer"], kn["n"], kn["correct"],
                       kn["rate"] if kn["rate"] is not None else "—",
                       " / ".join(f"{c}:{kn['dist'][c]}" for c in "ABCD")])
            if kn["rate"] is not None:
                st.cell(st.max_row, 5).number_format = "0.0%"
        m, n = g["k_score_mean"]
        st.append(["平均答對題數（0–3）", m if m is not None else "—", n])
        st.append([])
        hdr("v2 量表題（1–5）" + sfx, "平均", "有效筆數", "", "", "", "")
        for code, name, items, _ in fs["facets"]:
            if code == "k":
                continue
            fm, fn = g["facets"][code]
            st.append([f"【{name}】面向平均", fm if fm is not None else "—", fn])
            st.cell(st.max_row, 1).font = Font(name=FONT_NAME, bold=True)
            for k, lab in items:
                im, inn = g["likert"][k]
                st.append(["　" + lab, im if im is not None else "—", inn])
        st.append([])
    hdr("v1 舊版 Q1–Q6（1–5）", "平均", "有效筆數", "", "", "", "")
    for k in LIKERT_V1:
        im, inn = stats["v1_means"][k]
        st.append([LABELS[k], im if im is not None else "—", inn])
    st.append([])
    hdr("v1 身分", "人數", "", "", "", "", "")
    for role, cnt in stats["roles"].items():
        st.append([role, cnt, ""])
    st.append([])
    st.append(["面向平均＝該面向三題所有有效作答的平均。答對率＝答對數／作答數。"])
    st.append(["知識題正解與題目依「活動」欄切換題組（人工魚子醬 HL-STATION-2026-1127-CAVIAR 用晶球題組，"
               "研究用活動代碼 GAME-／CTRL-／CTRL-TEST／STUDY-GAME／STUDENT-TEST 用學生版課後問卷題組，"
               "其他活動用 default 題組）；不同題組分開統計。"])
    for row in st.iter_rows():
        for c in row:
            if c.font is None or not c.font.bold:
                c.font = bfont
    for rno in hdr_rows:
        for c in st[rno]:
            c.font, c.fill = hfont, (hfill if rno == hdr_rows[0] else sfill)
    for col, w in zip("ABCDEFG", (34, 12, 10, 10, 10, 26, 4)):
        st.column_dimensions[col].width = w

    # 簡答
    op = wb.create_sheet("簡答")
    op.append(["檔名", "填答時間", "版本", "面向", "題目", "內容"])
    _style_header(op[1], hfont, hfill)
    for rec in stats["opens"]:
        op.append(list(rec))
        for c in op[op.max_row]:
            c.font = bfont
            c.alignment = Alignment(wrap_text=True, vertical="top")
        _as_text(op[op.max_row])
    for col, w in zip("ABCDEF", (30, 26, 8, 12, 24, 60)):
        op.column_dimensions[col].width = w
    op.freeze_panes = "A2"
    wb.save(path)


def summary_lines(stats: dict) -> list[str]:
    out = [f"總回覆 {stats['total']} 筆（v2 {stats['n_v2']}、v1 {stats['n_v1']}）"]
    if stats["n_v2"]:
        banks = stats.get("banks", [BANK_DEFAULT])
        groups = stats.get("groups") or {BANK_DEFAULT: stats}
        for b in banks:
            g, fs = groups[b], FEEDBACK_SETS[b]
            pre = "" if banks == [BANK_DEFAULT] else f"［{BANK_LABEL.get(b, b)}，{g['n']} 筆］"
            rates = []
            for k, lab in fs["knowledge"]:
                kn = g["knowledge"][k]
                rates.append(f"{k.upper()} {kn['correct']}/{kn['n']}" if kn["n"] else f"{k.upper()} —")
            out.append(pre + "知識題答對：" + "、".join(rates))
            parts = []
            for code, name, _, _ in fs["facets"]:
                if code == "k":
                    continue
                fm, _ = g["facets"][code]
                parts.append(f"{name} {fm if fm is not None else '—'}")
            out.append(pre + "面向平均：" + "、".join(parts))
        out.append(f"簡答 {sum(1 for o in stats['opens'] if o[2] != 'v1')} 則")
    return out


def aggregate(dest: Path, log=print) -> tuple[int, dict]:
    """把 dest\\json\\ 全部 JSON 彙整成 CSV 與 XLSX。回傳（筆數, 統計）。"""
    rows = load_records(dest / JSON_SUBDIR, log=log)
    stats = compute_stats(rows)
    try:
        write_csv(rows, dest / CSV_NAME)
    except PermissionError:
        raise FetchError(f"無法寫入 {CSV_NAME}，可能正在 Excel 中開啟，請關閉後再試。")
    try:
        write_xlsx(rows, stats, dest / XLSX_NAME)
    except PermissionError:
        raise FetchError(f"無法寫入 {XLSX_NAME}，可能正在 Excel 中開啟，請關閉後再試。")
    return len(rows), stats


def run_fetch(dest: Path, token: str | None = None, log=print) -> dict:
    """完整流程：列遠端 → 下載新檔 → 彙整。"""
    dest.mkdir(parents=True, exist_ok=True)
    log("連線 GitHub 查詢回覆清單…")
    remote = list_remote(token)
    log(f"GitHub 上共有 {len(remote)} 筆回覆")
    ok, bad = download_new(dest, remote, token, log=log)
    log(f"本次新下載 {ok} 筆" + (f"，壞檔 {bad} 筆" if bad else ""))
    n, stats = aggregate(dest, log=log)
    log(f"彙整完成：{n} 筆 → {CSV_NAME}、{XLSX_NAME}")
    for line in summary_lines(stats):
        log(line)
    return {"remote": len(remote), "new": ok, "bad": bad, "total": n, "stats": stats}


def append_log_file(dest: Path, line: str) -> None:
    try:
        dest.mkdir(parents=True, exist_ok=True)
        with open(dest / LOG_NAME, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def cli_aggregate(dest: Path) -> int:
    """不互動模式：只重新彙整本機 json（不連網），結果寫入 彙整結果.txt。"""
    lines = [f"{APP_TITLE} v{VERSION}　{datetime.now():%Y-%m-%d %H:%M:%S}　--aggregate {dest}"]
    try:
        n, stats = aggregate(dest, log=lines.append)
        lines.append(f"彙整完成：{n} 筆 → {CSV_NAME}、{XLSX_NAME}")
        lines.extend(summary_lines(stats))
        code = 0
    except Exception as e:  # 不互動模式也不得崩潰
        lines.append(f"✖ 彙整失敗：{type(e).__name__}: {e}")
        code = 1
    try:
        dest.mkdir(parents=True, exist_ok=True)
        (dest / SUMMARY_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        code = 2
    if sys.stdout is not None:
        try:
            print("\n".join(lines))
        except (OSError, UnicodeEncodeError):
            pass
    return code


# ---------------------------------------------------------------- v3 遊戲前後測
def _game_int(v, lo: int, hi: int):
    """整數且在 [lo, hi] 內才採用；布林、小數、字串數字以外一律空白。"""
    if isinstance(v, bool):
        return ""
    if isinstance(v, str) and v.strip().lstrip("-").isdigit():
        v = int(v.strip())
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, int) and lo <= v <= hi:
        return v
    return ""


def _game_num(v, lo: float, hi: float):
    if isinstance(v, bool):
        return ""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return ""
    if lo <= f <= hi:
        return int(f) if f.is_integer() else round(f, 2)
    return ""


def parse_game_time(v) -> datetime | None:
    """ISO 8601 字串 → 台北時間 aware datetime；無時區者視為台北時間；無法解析回傳 None。"""
    if not isinstance(v, str) or not v.strip():
        return None
    s = v.strip()
    if s.endswith(("Z", "z")):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ_TPE)
    return dt.astimezone(TZ_TPE)


def _to_tpe(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=TZ_TPE) if dt.tzinfo is None else dt.astimezone(TZ_TPE)


def _norm_answers(v, index: dict | None = None) -> list[dict]:
    """題目陣列 → [{id, facet, pick, text, correct}]；非物件元素保留空位以維持題序。
    index＝該紀錄活動的題庫索引（v5；預設 default 題庫）。"""
    index = QUESTION_INDEX if index is None else index
    out = []
    if not isinstance(v, list):
        return out
    for it in v:
        a = {"id": "", "facet": "", "pick": "", "text": "", "correct": ""}
        if isinstance(it, dict):
            a["id"] = _to_text(it.get("id")).strip()
            q = index.get(a["id"])
            a["facet"] = _to_text(it.get("facet")).strip() or (q["facet"] if q else "")
            a["pick"] = _game_int(it.get("pick"), 0, 3)
            if q and a["pick"] != "" and a["pick"] < len(q["options"]):
                a["text"] = q["options"][a["pick"]]
            c = it.get("correct")
            if isinstance(c, bool):
                a["correct"] = 1 if c else 0
            elif q and a["pick"] != "":
                a["correct"] = 1 if a["pick"] == q["answer"] else 0
        out.append(a)
    return out


def _score(answers: list[dict], only_ids: set | None = None):
    vals = [a["correct"] for a in answers if a["correct"] != ""
            and (only_ids is None or a["id"] in only_ids)]
    return sum(vals) if vals else ""


def _add_note(rec: dict, msg: str) -> None:
    rec["note"] = (rec["note"] + "；" + msg) if rec.get("note") else msg


def load_game_records(jdir: Path, log=print) -> list[dict]:
    """讀取 game_json 內全部 JSON，正規化成固定欄位（缺漏或型別不對者為空白，不崩潰）。"""
    recs = []
    if not jdir.is_dir():
        return recs
    for p in sorted(jdir.glob("*.json")):
        try:
            obj = json.loads(p.read_text(encoding="utf-8-sig"))
            if not isinstance(obj, dict):
                raise ValueError("不是物件")
        except (OSError, ValueError) as e:
            log(f"⚠ 略過壞檔 {p.name}：{e}")
            continue
        if obj.get("schema") not in GAME_SCHEMAS:
            log(f"注意：{p.name} 的 schema 為 {obj.get('schema')}，仍嘗試讀取")
        r = {"file": p.name, "note": "", "dup": False, "dup_reason": "",
             "dup_minutes": "", "dup_base": ""}
        for k in ("schema", "event", "pid", "sid", "grade", "mode", "client_time", "ua", "commit"):
            r[k] = _to_text(obj.get(k)).strip()
        canon = next((c for c in EVENT_PRESETS if c.lower() == r["event"].lower()), None)
        if canon and canon != r["event"]:                     # 大小寫不同的預設活動代碼 → 統一寫法
            r["event"] = canon
        r["bank"] = bank_key_for_event(r["event"])            # v5：依活動選題庫（找不到＝default）
        index = QUESTION_INDEXES[r["bank"]]
        # v4：webar-game-v2 多的玩家資料（v1 紀錄沒有這些鍵 → 空白）
        r["age"] = _game_int(obj.get("age"), 3, 120)
        g = _to_text(obj.get("gender")).strip()
        r["gender"] = g if g in GENDERS else ""
        r["org"] = _to_text(obj.get("org")).strip()[:60]
        r["role"], r["unit"] = split_org(r["org"])            # v6：「身分｜單位」拆欄
        r["hero"] = _to_text(obj.get("hero")).strip()[:20]
        r["submitted_raw"] = _to_text(obj.get("submitted_at")).strip()
        r["submitted_at"] = parse_game_time(obj.get("submitted_at"))
        if r["submitted_at"] is None:
            _add_note(r, "submitted_at 無法解析")
            log(f"注意：{p.name} 的 submitted_at（{r['submitted_raw'] or '空白'}）無法解析")
        phase = _to_text(obj.get("phase")).strip().lower()
        if phase not in PHASE_LABEL:
            m = re.search(r"_(pre|post)_", p.name)
            phase = m.group(1) if m else ""
            _add_note(r, f"phase 欄位不明，{'依檔名判為 ' + phase if phase else '無法判定'}")
        r["phase"] = phase
        if r["grade"] not in GRADE_LABEL:
            r["grade"] = ""
        if r["mode"] not in MODE_LABEL:
            r["mode"] = ""
        r["pre"] = _norm_answers(obj.get("pre"), index)
        r["post"] = _norm_answers(obj.get("post"), index)
        if not r["grade"]:  # 由題號推回版本
            for a in r["pre"] + r["post"]:
                q = index.get(a["id"])
                if q:
                    r["grade"] = q["grade"]
                    break
        r["level"] = level_label(r["grade"], r["bank"])        # v6：初階／中階／高階（其他活動＝國小／國中）
        r["preScore"] = _game_int(obj.get("preScore"), 0, N_PRE)
        r["postSame3"] = _game_int(obj.get("postSame3"), 0, N_PRE)
        r["postScore"] = _game_int(obj.get("postScore"), 0, N_POST)
        stars = obj.get("stars")
        r["stars"] = [_game_int(x, 0, 3) for x in stars] if isinstance(stars, list) else []
        r["totalStars"] = _game_int(obj.get("totalStars"), 0, 3 * N_STAGES)
        if r["totalStars"] == "" and any(x != "" for x in r["stars"]):
            r["totalStars"] = sum(x for x in r["stars"] if x != "")
        fac = obj.get("facets")
        fac = fac if isinstance(fac, dict) else {}
        r["facets"] = {f: _game_num(fac.get(f), 0, 100) for f in GAME_FACETS}
        recs.append(r)
    recs.sort(key=_game_sort_key)
    return recs


def _game_sort_key(r: dict):
    t = r.get("submitted_at")
    return (t is None, t.timestamp() if t else 0, r["file"])


def filter_by_time(records: list[dict], start: datetime | None = None,
                   end: datetime | None = None) -> list[dict]:
    """以 submitted_at 篩選（閉區間；naive 視為台北時間）。有設起或迄時，時間無法解析者不納入。"""
    start, end = _to_tpe(start), _to_tpe(end)
    if start is None and end is None:
        return list(records)
    out = []
    for r in records:
        t = r.get("submitted_at")
        if t is None:
            continue
        if start is not None and t < start:
            continue
        if end is not None and t > end:
            continue
        out.append(r)
    return out


def filter_by_event(records: list[dict], event: str | None = None) -> list[dict]:
    """依活動代碼篩選（去頭尾空白、不分大小寫）；None／空白／「全部」＝不篩選。
    v6：指定 HL-STATION-2026-1127-CAVIAR 時一併納入 -SR（高階）；直接指定 -SR 則只取高階。"""
    ev = event_code(event)
    if not ev or ev == EVENT_ALL:
        return list(records)
    wanted = {ev.lower()}
    for k, fam in EVENT_FAMILY.items():
        if k.lower() == ev.lower():
            wanted |= {c.lower() for c in fam}
    return [r for r in records if (r.get("event") or "").strip().lower() in wanted]


def event_filter_text(event) -> str:
    """篩選活動的顯示文字（含子活動時加註）。"""
    ev = event_code(event)
    if not ev or ev == EVENT_ALL:
        return EVENT_ALL
    for k, fam in EVENT_FAMILY.items():
        if k.lower() == ev.lower():
            return f"{k}（含 {'、'.join(c for c in fam if c != k)} 高階）"
    return ev


def age_band(age) -> str:
    """年齡 → 年齡帶（≤12／13–18／19–64／≥65）；空白或非整數回傳空字串。"""
    if not isinstance(age, int) or isinstance(age, bool):
        return ""
    if age <= 12:
        return AGE_BANDS[0]
    if age <= 18:
        return AGE_BANDS[1]
    if age <= 64:
        return AGE_BANDS[2]
    return AGE_BANDS[3]


def dedupe_records(records: list[dict], window_minutes: float = DEDUP_MINUTES_DEFAULT
                   ) -> tuple[list[dict], list[dict]]:
    """同一玩家（pid）同一階段（前測／後測）在 window 分鐘內的後續紀錄判為重複。
    每組依時間排序；與「最近一筆被保留」的紀錄相差 < window 者略過，否則視為再玩一次並成為新基準。
    缺 pid 或缺時間者一律保留並標註。回傳（保留, 略過）。"""
    kept, dropped = [], []
    groups: dict[tuple, list[dict]] = {}
    for r in records:
        r["dup"], r["dup_reason"], r["dup_minutes"], r["dup_base"] = False, "", "", ""
        if not r.get("pid"):
            _add_note(r, "缺 pid，無法判定重複，保留")
            kept.append(r)
        elif r.get("submitted_at") is None:
            _add_note(r, "缺時間，無法判定重複，保留")
            kept.append(r)
        else:
            groups.setdefault((r["pid"], r.get("phase", "")), []).append(r)
    for (pid, phase), rs in groups.items():
        rs.sort(key=_game_sort_key)
        base = None
        for r in rs:
            if base is not None:
                diff = (r["submitted_at"] - base["submitted_at"]).total_seconds() / 60
                if diff < window_minutes:
                    r["dup"] = True
                    r["dup_minutes"] = round(diff, 1)
                    r["dup_base"] = base["file"]
                    r["dup_reason"] = (f"同一玩家 {window_minutes:g} 分鐘內重複"
                                       f"（{PHASE_LABEL.get(phase, phase or '階段不明')}），已略過")
                    dropped.append(r)
                    continue
            kept.append(r)
            base = r
    kept.sort(key=_game_sort_key)
    dropped.sort(key=_game_sort_key)
    return kept, dropped


def pair_plays(kept: list[dict]) -> list[dict]:
    """以 sid 配對前測與後測，一次遊玩一筆。同 sid 依時間：前測開新一局，後測接到最近一局尚無後測者；
    找不到前測的後測自成一局（前測答案取後測紀錄內的 pre 陣列）。"""
    by_sid: dict[str, list[dict]] = {}
    for r in kept:
        if r.get("phase") not in PHASE_LABEL:
            continue
        by_sid.setdefault(r.get("sid") or ("（無 sid）" + r["file"]), []).append(r)
    plays = []
    for sid, rs in by_sid.items():
        rs.sort(key=_game_sort_key)
        open_plays: list[dict] = []
        for r in rs:
            if r["phase"] == "pre":
                pl = {"pre_rec": r, "post_rec": None}
                open_plays.append(pl)
                plays.append(pl)
            else:
                target = next((pl for pl in reversed(open_plays) if pl["post_rec"] is None), None)
                if target is None:
                    target = {"pre_rec": None, "post_rec": r}
                    plays.append(target)
                else:
                    target["post_rec"] = r
    out = []
    for pl in plays:
        pre, post = pl["pre_rec"], pl["post_rec"]
        first = pre or post
        notes = []
        if pre is not None:
            pre_ans = pre["pre"]
        else:
            pre_ans = post["pre"]
            notes.append("無前測紀錄（前測取自後測紀錄）")
        if post is None:
            notes.append("未完成後測（玩到一半）")
        for r in (pre, post):
            if r is not None and r.get("note"):
                notes.append(f"{PHASE_LABEL[r['phase']]}：{r['note']}")
        post_ans = post["post"] if post else []
        pre_score = _score(pre_ans)
        if pre_score == "" and pre is not None:
            pre_score = pre["preScore"]
        bank = (pre or post).get("bank") or BANK_DEFAULT
        same_ids = {a["id"] for a in pre_ans if a["id"]} or bank_pre_ids(bank)
        same3 = _score(post_ans, same_ids) if post else ""
        if post and same3 == "":
            same3 = post["postSame3"]
        post_score = _score(post_ans) if post else ""
        if post and post_score == "":
            post_score = post["postScore"]
        gain = same3 - pre_score if isinstance(same3, int) and isinstance(pre_score, int) else ""
        pick = lambda k: (pre or {}).get(k) or (post or {}).get(k) or ""  # noqa: E731
        out.append({
            "pid": pick("pid"), "sid": first.get("sid", ""), "grade": pick("grade"), "mode": pick("mode"),
            "event": pick("event"), "bank": (pre or post).get("bank") or BANK_DEFAULT,
            "age": pick("age"), "gender": pick("gender"), "org": pick("org"), "hero": pick("hero"),
            "role": split_org(pick("org"))[0], "unit": split_org(pick("org"))[1],
            "level": level_label(pick("grade"), (pre or post).get("bank") or BANK_DEFAULT),
            "pre_time": pre["submitted_at"] if pre else None,
            "post_time": post["submitted_at"] if post else None,
            "pre_file": pre["file"] if pre else "", "post_file": post["file"] if post else "",
            "pre_rec": pre, "post_rec": post, "pre_answers": pre_ans, "post_answers": post_ans,
            "pre_score": pre_score, "post_same3": same3, "post_score": post_score, "gain": gain,
            "stars": post["stars"] if post else [], "total_stars": post["totalStars"] if post else "",
            "facets": post["facets"] if post else {}, "commit": post["commit"] if post else "",
            "ua": (post or pre).get("ua", ""), "complete": pre is not None and post is not None,
            "note": "；".join(notes), "_t": first,
        })
    out.sort(key=lambda pl: _game_sort_key(pl["_t"]))
    for i, pl in enumerate(out, 1):
        pl["no"] = i
    return out


def _player_key(pl: dict) -> str:
    return pl["pid"] or ("sid:" + pl["sid"])


def compute_game_stats(all_n: int, in_range: list[dict], kept: list[dict], dropped: list[dict],
                       pairs: list[dict], meta: dict) -> dict:
    def ppl(cond):
        return len({_player_key(p) for p in pairs if cond(p)})
    pre_scores = [p["pre_score"] for p in pairs if isinstance(p["pre_score"], int)]
    same3 = [p["post_same3"] for p in pairs if p["post_rec"] and isinstance(p["post_same3"], int)]
    post5 = [p["post_score"] for p in pairs if p["post_rec"] and isinstance(p["post_score"], int)]
    gains = [p["gain"] for p in pairs if isinstance(p["gain"], int)]
    stars = [p["total_stars"] for p in pairs if isinstance(p["total_stars"], int)]
    # v5：每題作答依題庫分段（同題號在不同活動是不同題目）
    q_banks = [b for b in QUESTION_BANKS if any((p.get("bank") or BANK_DEFAULT) == b for p in pairs)]
    if not q_banks:
        q_banks = [bank_key_for_event(meta.get("event_text", ""))]
    per_q = {}
    for bank in q_banks:
        per_q[bank] = _per_question([p for p in pairs if (p.get("bank") or BANK_DEFAULT) == bank],
                                    QUESTION_INDEXES[bank])
    facets = {}
    for f in GAME_FACETS:
        vals = [p["facets"].get(f) for p in pairs if p["post_rec"]]
        vals = [v for v in vals if isinstance(v, (int, float)) and v != ""]
        facets[f] = (_mean(vals), len(vals))
    # v4：依活動分組（預設活動排前面，其餘依代碼排序，空白＝（未填））
    presets = list(EVENT_PRESETS)

    def ev_order(e):
        return (0, presets.index(e), "") if e in presets else (1, 0, e)
    def group(ps):
        return {
            "people": len({_player_key(p) for p in ps}), "plays": len(ps),
            "complete": sum(1 for p in ps if p["complete"]),
            "pre_mean": _mean([p["pre_score"] for p in ps if isinstance(p["pre_score"], int)]),
            "same3_mean": _mean([p["post_same3"] for p in ps
                                 if p["post_rec"] and isinstance(p["post_same3"], int)]),
            "gain_mean": _mean([p["gain"] for p in ps if isinstance(p["gain"], int)]),
            "post5_mean": _mean([p["post_score"] for p in ps
                                 if p["post_rec"] and isinstance(p["post_score"], int)]),
        }
    events: dict[str, dict] = {}
    for ev in sorted({p["event"] or NO_VALUE for p in pairs}, key=ev_order):
        events[ev] = group([p for p in pairs if (p["event"] or NO_VALUE) == ev])
    # v6：依程度分組（國小／國中／初階／中階／高階；空白＝（未填））

    def lv_of(p):
        return p.get("level") or level_label(p.get("grade"), p.get("bank")) or NO_VALUE

    def lv_order(lv):
        return (0, LEVEL_ORDER.index(lv), "") if lv in LEVEL_ORDER else (1, 0, lv)
    levels: dict[str, dict] = {}
    for lv in sorted({lv_of(p) for p in pairs}, key=lv_order):
        levels[lv] = group([p for p in pairs if lv_of(p) == lv])
    # v4：年齡帶／性別分布（人數，pid 去重；同一人多次遊玩取第一次的資料）
    first_by_player: dict[str, dict] = {}
    for p in pairs:
        first_by_player.setdefault(_player_key(p), p)
    age_people = {b: 0 for b in AGE_BANDS + [NO_VALUE]}
    gender_people = {g: 0 for g in GENDERS + [NO_VALUE]}
    for p in first_by_player.values():
        age_people[age_band(p.get("age")) or NO_VALUE] += 1
        gender_people[p.get("gender") or NO_VALUE] += 1
    ages = [p["age"] for p in first_by_player.values()
            if isinstance(p.get("age"), int) and not isinstance(p.get("age"), bool)]
    return {
        "event_filter": meta.get("event_text", EVENT_ALL),
        "event_filter_text": event_filter_text(meta.get("event_text", EVENT_ALL)),
        "events": events, "levels": levels, "age_people": age_people, "gender_people": gender_people,
        "age_mean": (_mean(ages), len(ages)),
        "range": meta.get("range_text", "不限"), "window": meta.get("window", DEDUP_MINUTES_DEFAULT),
        "local": all_n, "in_range": len(in_range), "kept": len(kept), "dropped": len(dropped),
        "n_pre": sum(1 for r in kept if r.get("phase") == "pre"),
        "n_post": sum(1 for r in kept if r.get("phase") == "post"),
        "players": len({r["pid"] for r in kept if r.get("pid")}),
        "plays": len(pairs), "complete": sum(1 for p in pairs if p["complete"]),
        "pre_only": sum(1 for p in pairs if p["post_rec"] is None),
        "post_only": sum(1 for p in pairs if p["pre_rec"] is None),
        "grade_people": {g: ppl(lambda p, g=g: p["grade"] == g) for g in GRADE_LABEL},
        "level_people": {lv: d["people"] for lv, d in levels.items()} or {lab: 0 for lab in GRADE_LABEL.values()},
        "mode_people": {m: ppl(lambda p, m=m: p["mode"] == m) for m in MODE_LABEL},
        "pre_mean": (_mean(pre_scores), len(pre_scores)),
        "same3_mean": (_mean(same3), len(same3)),
        "gain_mean": (_mean(gains), len(gains)),
        "post5_mean": (_mean(post5), len(post5)),
        "stars_mean": (_mean(stars), len(stars)),
        "per_q": per_q, "q_banks": q_banks, "facets": facets,
    }


def _per_question(pairs: list[dict], index: dict) -> dict:
    per_q = {}
    for qid in index:
        d = {"pre_n": 0, "pre_ok": 0, "post_n": 0, "post_ok": 0}
        for p in pairs:
            for side, ans in (("pre", p["pre_answers"]), ("post", p["post_answers"])):
                for a in ans:
                    if a["id"] == qid and a["correct"] != "":
                        d[side + "_n"] += 1
                        d[side + "_ok"] += a["correct"]
        d["pre_rate"] = round(d["pre_ok"] / d["pre_n"], 4) if d["pre_n"] else None
        d["post_rate"] = round(d["post_ok"] / d["post_n"], 4) if d["post_n"] else None
        per_q[qid] = d
    return per_q


def _xl_time(dt: datetime | None):
    return dt.astimezone(TZ_TPE).replace(tzinfo=None) if dt else ""


def _safe_row(vals: list) -> list:
    return [_csv_safe(v) if isinstance(v, str) else v for v in vals]


def _ans_cols(ans: list[dict], n: int, with_index: bool) -> list:
    out = []
    for i in range(n):
        a = ans[i] if i < len(ans) else {"id": "", "pick": "", "text": "", "correct": ""}
        out += [a["id"], a["pick"], a["text"], a["correct"]] if with_index else \
               [a["id"], a["text"], a["correct"]]
    return out


def _ans_hdr(prefix: str, n: int, with_index: bool) -> list[str]:
    out = []
    for i in range(1, n + 1):
        out += [f"{prefix}Q{i} 題號"] + ([f"{prefix}Q{i} 選項索引"] if with_index else []) + \
               [f"{prefix}Q{i} 選項文字", f"{prefix}Q{i} 答對(1/0)"]
    return out


def write_game_xlsx(kept: list[dict], dropped: list[dict], pairs: list[dict], stats: dict,
                    path: Path, meta: dict | None = None) -> None:
    meta = meta or {}
    wb = Workbook()
    hfont = Font(name=FONT_NAME, bold=True, color="FFFFFF")
    hfill = PatternFill("solid", fgColor="0B1F3A")
    sfill = PatternFill("solid", fgColor="1C7293")
    bfont = Font(name=FONT_NAME)
    tfmt = "yyyy-mm-dd hh:mm:ss"

    def sheet(ws, headers, rows, widths, time_cols=(), freeze="A2", wrap_cols=()):
        ws.append(headers)
        _style_header(ws[1], hfont, hfill)
        for vals in rows:
            ws.append(_safe_row(vals))
            for c in ws[ws.max_row]:
                c.font = bfont
                if c.column in time_cols and c.value != "":
                    c.number_format = tfmt
                if c.column in wrap_cols:
                    c.alignment = Alignment(wrap_text=True, vertical="top")
            _as_text(ws[ws.max_row])
        for i, _ in enumerate(headers, 1):
            ws.column_dimensions[get_column_letter(i)].width = widths.get(i, 12)
        ws.freeze_panes = freeze

    def gl(d):                     # v6：程度顯示（初階／中階／高階；其他活動＝國小／國中）
        return d.get("level") or level_label(d.get("grade"), d.get("bank") or BANK_DEFAULT)

    def ml(m):
        return MODE_LABEL.get(m, m)

    def fac_cols(fac):
        return [fac.get(f, "") if isinstance(fac, dict) else "" for f in GAME_FACETS]

    def stars_text(st):
        return ",".join("" if x == "" else str(x) for x in st)

    def player_cols(d):
        return [d.get("event", ""), d.get("age", ""), d.get("gender", ""), d.get("org", ""),
                d.get("role", ""), d.get("unit", ""), d.get("hero", "")]

    # 1 玩家彙整
    ws = wb.active
    ws.title = "玩家彙整"
    h = (["序號", "pid（玩家代碼）", "sid（遊玩代碼）", "版本", "模式"] + PLAYER_HDR + ["前測時間", "後測時間"]
         + _ans_hdr("前測", N_PRE, False) + ["前測答對數(0–3)"]
         + _ans_hdr("後測", N_POST, False)
         + ["後測同3題答對數(0–3)", "後測答對數(0–5)", "進步（後測同3題−前測）", "八關星數", "總星數(0–24)"]
         + [f"{f}%" for f in GAME_FACETS] + ["小行動承諾", "備註", "前測檔名", "後測檔名", "瀏覽器 UA"])
    rows = []
    for p in pairs:
        rows.append([p["no"], p["pid"], p["sid"], gl(p), ml(p["mode"])] + player_cols(p)
                    + [_xl_time(p["pre_time"]), _xl_time(p["post_time"])]
                    + _ans_cols(p["pre_answers"], N_PRE, False) + [p["pre_score"]]
                    + (_ans_cols(p["post_answers"], N_POST, False) if p["post_rec"] else [""] * (3 * N_POST))
                    + [p["post_same3"], p["post_score"], p["gain"], stars_text(p["stars"]), p["total_stars"]]
                    + fac_cols(p["facets"]) + [p["commit"], p["note"], p["pre_file"], p["post_file"], p["ua"]])
    npl = len(PLAYER_HDR)
    t1 = 6 + npl                      # 前測時間欄
    widths = {1: 6, 2: 15, 3: 15, 4: 7, 5: 10}
    widths.update(dict(zip(range(6, 6 + npl), PLAYER_WIDTHS)))
    widths.update({t1: 19, t1 + 1: 19})
    a0 = t1 + 2                       # 第一個作答欄
    for i in range(a0, a0 + 3 * N_PRE + 1 + 3 * N_POST):
        widths[i] = 8 if (i - a0) % 3 != 1 else 22
    base = a0 + 3 * N_PRE + 1 + 3 * N_POST
    widths.update({base + 3: 12, base + 3 + 1: 14})
    widths.update({len(h) - 4: 28, len(h) - 3: 30, len(h) - 2: 32, len(h) - 1: 32, len(h): 40})
    sheet(ws, h, rows, widths, time_cols=(t1, t1 + 1), freeze="D2")

    # 2 前測、3 後測
    def rec_head(r):
        return [r["file"], _xl_time(r["submitted_at"]) or r["submitted_raw"], r["pid"], r["sid"],
                gl(r), ml(r["mode"])] + player_cols(r)
    hh = ["檔名", "上傳時間", "pid", "sid", "版本", "模式"] + PLAYER_HDR
    pw = dict(zip(range(7, 7 + len(PLAYER_HDR)), PLAYER_WIDTHS))
    pre_recs = [r for r in kept if r.get("phase") == "pre"]
    post_recs = [r for r in kept if r.get("phase") == "post"]
    prh = hh + _ans_hdr("", N_PRE, True) + ["答對數(0–3)", "備註"]
    sheet(wb.create_sheet("前測"), prh,
          [rec_head(r) + _ans_cols(r["pre"], N_PRE, True)
           + [_score(r["pre"]) if _score(r["pre"]) != "" else r["preScore"], r["note"]] for r in pre_recs],
          {1: 34, 2: 19, 3: 15, 4: 15, **pw, len(prh): 30}, time_cols=(2,), freeze="C2")
    post_rows = []
    for r in post_recs:
        same_ids = {a["id"] for a in r["pre"] if a["id"]} or bank_pre_ids(r.get("bank") or BANK_DEFAULT)
        s3 = _score(r["post"], same_ids)
        s5 = _score(r["post"])
        post_rows.append(rec_head(r) + _ans_cols(r["post"], N_POST, True)
                         + [s3 if s3 != "" else r["postSame3"], s5 if s5 != "" else r["postScore"],
                            stars_text(r["stars"]), r["totalStars"]] + fac_cols(r["facets"])
                         + [r["commit"], r["note"]])
    ph = (hh + _ans_hdr("", N_POST, True) + ["同3題答對數(0–3)", "答對數(0–5)", "八關星數", "總星數(0–24)"]
          + [f"{f}%" for f in GAME_FACETS] + ["小行動承諾", "備註"])
    sheet(wb.create_sheet("後測"), ph, post_rows,
          {1: 34, 2: 19, 3: 15, 4: 15, **pw, len(ph) - 1: 28, len(ph): 30}, time_cols=(2,), freeze="C2")

    # 4 已略過(重複)
    sheet(wb.create_sheet("已略過(重複)"),
          ["檔名", "上傳時間", "pid", "sid", "階段", "基準筆檔名", "與基準筆差(分鐘)", "原因", "活動"],
          [[r["file"], _xl_time(r["submitted_at"]), r["pid"], r["sid"],
            PHASE_LABEL.get(r["phase"], r["phase"]), r["dup_base"], r["dup_minutes"], r["dup_reason"],
            r.get("event", "")]
           for r in dropped],
          {1: 34, 2: 19, 3: 15, 4: 15, 5: 7, 6: 34, 7: 12, 8: 40, 9: 22}, time_cols=(2,))

    # 5 統計
    st = wb.create_sheet("統計")
    hdr_rows = []

    def hdr(*vals):
        st.append(list(vals))
        hdr_rows.append(st.max_row)

    def mv(pair):
        m, n = pair
        return [m if m is not None else "—", n]

    hdr("項目", "數值", "有效筆數", "", "", "", "")
    st.append(["篩選區間（台北時間）", stats["range"], ""])
    st.append(["篩選活動", stats.get("event_filter_text") or stats.get("event_filter", EVENT_ALL), ""])
    st.append(["重複判定（分鐘）", stats["window"], ""])
    st.append(["本機遊戲紀錄總筆數", stats["local"], ""])
    st.append(["原始筆數（區間內）", stats["in_range"], ""])
    st.append(["保留筆數", stats["kept"], ""])
    st.append(["　其中前測", stats["n_pre"], ""])
    st.append(["　其中後測", stats["n_post"], ""])
    st.append(["略過筆數（重複）", stats["dropped"], ""])
    st.append(["玩家數（pid 去重）", stats["players"], ""])
    st.append(["遊玩次數（配對後）", stats["plays"], ""])
    st.append(["完整遊玩數（有前測也有後測）", stats["complete"], ""])
    st.append(["　只有前測（玩到一半）", stats["pre_only"], ""])
    st.append(["　只有後測（前測未上傳）", stats["post_only"], ""])
    lv_people = stats.get("level_people") or {GRADE_LABEL[g]: n for g, n in stats["grade_people"].items()}
    for lab, n in lv_people.items():           # v6：依程度（人工魚子醬＝初階／中階／高階）
        st.append([f"{lab}版人數" if lab in GRADE_LABEL.values() else f"{lab}人數", n, ""])
    for m, lab in MODE_LABEL.items():
        st.append([f"{lab}模式人數", stats["mode_people"][m], ""])
    st.append(["前測平均答對（0–3）"] + mv(stats["pre_mean"]))
    st.append(["後測同 3 題平均答對（0–3）"] + mv(stats["same3_mean"]))
    st.append(["平均進步（後測同3題−前測）"] + mv(stats["gain_mean"]))
    st.append(["後測 5 題平均答對（0–5）"] + mv(stats["post5_mean"]))
    st.append(["平均總星數（0–24）"] + mv(stats["stars_mean"]))
    st.append([])
    hdr("依活動分組", "人數（pid 去重）", "遊玩次數", "完整遊玩", "前測平均(0–3)", "後測同3題平均(0–3)",
        "平均進步", "後測5題平均(0–5)")
    for ev, d in stats["events"].items():
        st.append([ev, d["people"], d["plays"], d["complete"]]
                  + [d[k] if d[k] is not None else "—"
                     for k in ("pre_mean", "same3_mean", "gain_mean", "post5_mean")])
    st.append([])
    hdr("依程度分組", "人數（pid 去重）", "遊玩次數", "完整遊玩", "前測平均(0–3)", "後測同3題平均(0–3)",
        "平均進步", "後測5題平均(0–5)")
    for lv, d in stats.get("levels", {}).items():
        st.append([lv, d["people"], d["plays"], d["complete"]]
                  + [d[k] if d[k] is not None else "—"
                     for k in ("pre_mean", "same3_mean", "gain_mean", "post5_mean")])
    st.append([])
    hdr("年齡帶分布", "人數（pid 去重）", "", "", "", "", "", "")
    for b, n in stats["age_people"].items():
        st.append([f"年齡 {b}" if b != NO_VALUE else f"年齡{NO_VALUE}", n, ""])
    st.append(["平均年齡"] + mv(stats["age_mean"]))
    st.append([])
    hdr("性別分布", "人數（pid 去重）", "", "", "", "", "", "")
    for g, n in stats["gender_people"].items():
        st.append([f"性別 {g}" if g != NO_VALUE else f"性別{NO_VALUE}", n, ""])
    st.append([])
    hdr("四面向平均", "平均 %", "有效筆數", "", "", "", "")
    for f in GAME_FACETS:
        st.append([f"{FACET_NAMES_GAME.get(f, f)}（{f}）"] + mv(stats["facets"][f]))
    st.append([])
    q_banks = stats.get("q_banks", [BANK_DEFAULT])
    for bank in q_banks:
        sfx = "" if q_banks == [BANK_DEFAULT] else "｜" + BANK_LABEL.get(bank, bank)
        hdr("每題作答" + sfx, "版本", "前測作答數", "前測答對率", "後測作答數", "後測答對率", "面向")
        for qid, d in stats["per_q"][bank].items():
            q = QUESTION_INDEXES[bank][qid]
            st.append([display_qid(q) + ("（前測題）" if q.get("pre") else ""), level_label(q["grade"], bank),
                       d["pre_n"], d["pre_rate"] if d["pre_rate"] is not None else "—",
                       d["post_n"], d["post_rate"] if d["post_rate"] is not None else "—", q["facet"]])
            for col in (4, 6):
                if isinstance(st.cell(st.max_row, col).value, float):
                    st.cell(st.max_row, col).number_format = "0.0%"
        st.append([])
    st.append(["人數以 pid 去重（無 pid 者以 sid 計）。答對率＝答對數／作答數。進步只計有前測答案也有後測的遊玩（含前測取自後測紀錄者）。"])
    st.append(["年齡、性別、學校／單位、主角只有新遊戲（webar-game-v2）才有；舊遊戲（v1）紀錄計入「（未填）」。"
               "年齡帶／性別以每位玩家第一次遊玩的資料計。"])
    st.append([f"重複判定：同一 pid、同一階段，與前一筆保留紀錄相差未滿 {stats['window']} 分鐘者略過；"
               "超過則視為再玩一次。"])
    st.append([f"產生時間：{meta.get('generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}　"
               f"{APP_TITLE} v{VERSION}"])
    for row in st.iter_rows():
        for c in row:
            c.font = bfont
    for rno in hdr_rows:
        for c in st[rno]:
            c.font, c.fill = hfont, (hfill if rno == hdr_rows[0] else sfill)
    for col, w in zip("ABCDEFGH", (34, 26, 12, 12, 14, 18, 10, 16)):
        st.column_dimensions[col].width = w

    # 6 題目對照
    qrows = []
    for bank in stats.get("q_banks", [BANK_DEFAULT]):   # v5：只列本次匯出用到的活動題庫，並標明活動
        for g, qs in QUESTION_BANKS[bank].items():
            for q in qs:
                opts = list(q["options"]) + [""] * (4 - len(q["options"]))
                qrows.append([display_qid(q), level_label(g, bank), q["facet"], "是" if q.get("pre") else "否",
                              q["q"]] + opts[:4] + [q["explain"], BANK_LABEL.get(bank, bank)])
    sheet(wb.create_sheet("題目對照"),
          ["id", "版本", "面向", "是否前測題", "題目", "選項A（索引0＝正解）", "選項B（索引1）",
           "選項C（索引2）", "選項D（索引3）", "解說", "活動（題庫）"], qrows,
          {1: 6, 2: 7, 3: 7, 4: 10, 5: 50, 6: 26, 7: 18, 8: 18, 9: 18, 10: 44, 11: 40},
          wrap_cols=(5, 10, 11), freeze="B2")
    wb.save(path)


PLAYER_HDR = ["活動", "年齡", "性別", "學校／單位", "身分", "單位", "主角"]   # v6：org 拆「身分」「單位」
PLAYER_WIDTHS = (22, 6, 8, 24, 10, 20, 11)
FACET_NAMES_GAME = {"知識": "環境知識", "態度": "環境態度", "行動": "行動意向", "探究": "科學探究"}


def parse_user_time(s: str, is_end: bool = False) -> datetime | None:
    """解析使用者輸入「YYYY-MM-DD HH:MM」（亦接受 :SS 或只填日期）→ 台北時間；空白回傳 None。
    迄時間只到分鐘時，含該分鐘整分（到 :59.999999）；只填日期時，迄＝當天 23:59:59。格式錯誤丟 ValueError。"""
    s = (s or "").strip().replace("/", "-").replace("T", " ")
    if not s:
        return None
    for fmt, pad in (("%Y-%m-%d %H:%M:%S", timedelta(0)),
                     ("%Y-%m-%d %H:%M", timedelta(seconds=59, microseconds=999999)),
                     ("%Y-%m-%d", timedelta(days=1) - timedelta(microseconds=1))):
        try:
            dt = datetime.strptime(s, fmt)
        except ValueError:
            continue
        if is_end:
            dt += pad
        return dt.replace(tzinfo=TZ_TPE)
    raise ValueError(f"時間格式錯誤：「{s}」，請用 YYYY-MM-DD HH:MM（例：2026-10-31 09:00）")


def _range_text(start: datetime | None, end: datetime | None) -> str:
    a = start.strftime("%Y-%m-%d %H:%M") if start else "不限"
    b = end.strftime("%Y-%m-%d %H:%M") if end else "不限"
    return "不限" if not start and not end else f"{a} ～ {b}"


def run_game_export(dest: Path, xlsx_path: Path, start: datetime | None = None,
                    end: datetime | None = None, window: float = DEDUP_MINUTES_DEFAULT,
                    token: str | None = None, log=print, offline: bool = False,
                    session=None, event: str | None = None) -> dict:
    """遊戲前後測：下載新檔到 dest\\game_json → 讀取 → 時間篩選 → 去重 → 配對 → 統計 → 寫 xlsx。"""
    dest = Path(dest)
    xlsx_path = Path(xlsx_path)
    dest.mkdir(parents=True, exist_ok=True)
    remote_n = ok = bad = None
    if offline:
        log("離線模式：不連網，只讀本機 game_json")
    else:
        log("連線 GitHub 查詢遊戲前後測清單…")
        remote = list_remote(token, session, api_url=GAME_API_URL)
        remote_n = len(remote)
        log(f"GitHub 上共有 {remote_n} 筆遊戲紀錄")
        ok, bad = download_new(dest, remote, token, log=log, session=session, subdir=GAME_JSON_SUBDIR)
        log(f"本次新下載 {ok} 筆" + (f"，壞檔 {bad} 筆" if bad else ""))
    recs = load_game_records(dest / GAME_JSON_SUBDIR, log=log)
    ev = event_code(event)
    ev = "" if ev == EVENT_ALL else ev
    in_range = filter_by_event(filter_by_time(recs, start, end), ev)
    kept, dropped = dedupe_records(in_range, window)
    pairs = pair_plays(kept)
    meta = {"range_text": _range_text(_to_tpe(start), _to_tpe(end)), "window": window,
            "event_text": ev or EVENT_ALL,
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    stats = compute_game_stats(len(recs), in_range, kept, dropped, pairs, meta)
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        write_game_xlsx(kept, dropped, pairs, stats, xlsx_path, meta)
    except PermissionError:
        raise FetchError(f"無法寫入 {xlsx_path.name}，可能正在 Excel 中開啟，請關閉後再試。")
    res = {"remote": remote_n, "new": ok, "bad": bad, "local": len(recs),
           "in_range": len(in_range), "kept": len(kept), "dropped": len(dropped),
           "players": stats["players"], "plays": stats["plays"], "complete": stats["complete"],
           "path": str(xlsx_path), "stats": stats}
    for line in game_summary_lines(res):
        log(line)
    return res


def game_summary_lines(res: dict) -> list[str]:
    st = res["stats"]
    out = []
    if res.get("remote") is not None:
        out.append(f"GitHub 上 {res['remote']} 筆、本次新下載 {res['new']} 筆"
                   + (f"、壞檔 {res['bad']} 筆" if res.get("bad") else ""))
    out.append(f"本機遊戲紀錄 {res['local']} 筆；篩選區間：{st['range']}；"
               f"活動：{st.get('event_filter_text') or st.get('event_filter', EVENT_ALL)}；"
               f"區間內 {res['in_range']} 筆")
    out.append(f"重複判定 {st['window']:g} 分鐘：保留 {res['kept']} 筆、略過重複 {res['dropped']} 筆")
    out.append(f"玩家數 {res['players']} 人；遊玩 {res['plays']} 次，其中完整遊玩（有前有後）{res['complete']} 次")

    def m(pair):
        return "—" if pair[0] is None else f"{pair[0]}"
    out.append(f"前測平均答對 {m(st['pre_mean'])}／3、後測同 3 題 {m(st['same3_mean'])}／3、"
               f"平均進步 {m(st['gain_mean'])}、後測 5 題 {m(st['post5_mean'])}／5")
    for ev, d in st.get("events", {}).items():
        out.append(f"　活動 {ev}：{d['people']} 人、遊玩 {d['plays']} 次、完整 {d['complete']} 次")
    for lv, d in st.get("levels", {}).items():
        out.append(f"　程度 {lv}：{d['people']} 人、遊玩 {d['plays']} 次、完整 {d['complete']} 次")
    out.append(f"輸出：{res['path']}")
    return out


def cli_game_export(argv: list[str]) -> int:
    """不互動模式：--game-export <dest> <xlsx> [--from ..] [--to ..] [--window N] [--event 代碼] [--offline]。"""
    lines = [f"{APP_TITLE} v{VERSION}　{datetime.now():%Y-%m-%d %H:%M:%S}　--game-export "
             + " ".join(argv)]
    dest = Path(argv[0]) if argv else Path(".")
    code = 0
    try:
        if len(argv) < 2:
            raise FetchError("用法：--game-export <資料夾> <輸出.xlsx> [--from \"YYYY-MM-DD HH:MM\"]"
                             " [--to \"YYYY-MM-DD HH:MM\"] [--window 30] [--event 活動代碼] [--offline]")
        xlsx = Path(argv[1])
        opts = {"--from": "", "--to": "", "--window": str(DEDUP_MINUTES_DEFAULT), "--event": ""}
        offline = False
        i = 2
        while i < len(argv):
            a = argv[i]
            if a == "--offline":
                offline = True
                i += 1
            elif a in opts and i + 1 < len(argv):
                opts[a] = argv[i + 1]
                i += 2
            else:
                raise FetchError(f"無法辨識的參數：{a}")
        try:
            start = parse_user_time(opts["--from"])
            end = parse_user_time(opts["--to"], is_end=True)
        except ValueError as e:
            raise FetchError(str(e))
        try:
            window = float(opts["--window"])
        except ValueError:
            raise FetchError(f"--window 必須是數字（分鐘），收到：{opts['--window']}")
        if not 0 < window <= 720:
            raise FetchError("--window 必須介於 1–720 分鐘")
        window = int(window) if window.is_integer() else window
        run_game_export(dest, xlsx, start, end, window, None, log=lines.append, offline=offline,
                        event=opts["--event"])
        lines.append("匯出完成")
    except FetchError as e:
        lines.append(f"✖ 匯出失敗：{e}")
        code = 1
    except Exception as e:  # 不互動模式也不得崩潰
        lines.append(f"✖ 匯出失敗：{type(e).__name__}: {e}")
        code = 1
    try:
        dest.mkdir(parents=True, exist_ok=True)
        (dest / GAME_SUMMARY_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        code = 2
    if sys.stdout is not None:
        try:
            print("\n".join(lines))
        except (OSError, UnicodeEncodeError):
            pass
    return code


# ---------------------------------------------------------------- v7：研究用前後測（feedback/test，webar-test-v1）
# 遊戲 repo 的研究設計：遊戲班（play.html／ar.html?study=1，group=game）與對照班（test/，group=control）
# 課前、課後各做同一份整份 10 題（墨玉題庫 E1–E10／J1–J10，題目順序固定、選項洗牌），後測後選一項行動承諾。
# 態度題（facet＝態度：E3、E7、J3、J8）不計對錯（中繼寫 correct=null），其餘 8 題計分。
TEST_REMOTE_DIR = "feedback/test"
TEST_API_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{TEST_REMOTE_DIR}"
TEST_JSON_SUBDIR = "test_json"
SCHEMA_TEST = "webar-test-v1"
RESEARCH_SUMMARY_NAME = "研究用前後測_匯出結果.txt"
RESEARCH_N = 10
RESEARCH_BANK = QUESTION_BANK                     # 與遊戲 repo js/content.js 的 BANK 相同（測試會比對）
RESEARCH_INDEX = QUESTION_INDEX
ATTITUDE_FACET = "態度"
ATTITUDE_IDS = {g: [q["id"] for q in qs if q["facet"] == ATTITUDE_FACET] for g, qs in RESEARCH_BANK.items()}
SCORED_IDS = {g: [q["id"] for q in qs if q["facet"] != ATTITUDE_FACET] for g, qs in RESEARCH_BANK.items()}
RESEARCH_MAX = {g: len(v) for g, v in SCORED_IDS.items()}            # 8
GROUP_LABEL = {"game": "遊戲班", "control": "對照班"}
GROUP_ALIASES = {"game": "game", "遊戲班": "game", "遊戲": "game",
                 "control": "control", "對照班": "control", "對照": "control"}
GRADE_ALIASES = {"elem": "elem", "國小": "elem", "國小版": "elem", "junior": "junior", "國中": "junior", "國中版": "junior"}
RESEARCH_MODE_LABEL = {"ar": "AR", "play": "免相機", "test": "只有測驗（對照班）"}
RESEARCH_EVENT_PRESETS = {"CTRL-TEST": "對照班預設", "STUDY-GAME": "遊戲班研究模式預設"}
# 遊戲 repo js/content.js 的 ENDING.commits（行動承諾四選一；commitPick＝索引）
COMMITS = ["做好垃圾分類回收", "珍惜在地資源，不浪費", "跟家人分享今天學到的事", "隨手關燈、節約用水"]


def norm_group(v) -> str:
    """遊戲班／對照班／game／control → game|control；全部或空白 → ""；其他丟 ValueError。"""
    s = _to_text(v).strip()
    if not s or s == EVENT_ALL:
        return ""
    g = GROUP_ALIASES.get(s) or GROUP_ALIASES.get(s.lower())
    if not g:
        raise ValueError(f"組別必須是 遊戲班／對照班（game／control），收到：{s}")
    return g


def norm_grade(v) -> str:
    s = _to_text(v).strip()
    if not s or s == EVENT_ALL:
        return ""
    g = GRADE_ALIASES.get(s) or GRADE_ALIASES.get(s.lower())
    if not g:
        raise ValueError(f"版本必須是 國小／國中（elem／junior），收到：{s}")
    return g


def ua_summary(ua) -> str:
    """瀏覽器 UA → 「裝置／瀏覽器」短摘要（UA 已被中繼截到 120 字，可能不完整）。"""
    s = _to_text(ua)
    if not s.strip():
        return ""
    dev = ("iPad" if "iPad" in s else "iPhone" if "iPhone" in s else "Android" if "Android" in s
           else "Chromebook" if "CrOS" in s else "Windows" if "Windows" in s
           else "Mac" if "Macintosh" in s or "Mac OS" in s else "Linux" if "Linux" in s else "其他")
    br = ("LINE" if "Line/" in s else "Facebook" if ("FBAN" in s or "FBAV" in s) else "Edge" if "Edg/" in s
          else "Firefox" if ("Firefox/" in s or "FxiOS" in s) else "Chrome" if ("Chrome/" in s or "CriOS" in s)
          else "Safari" if "Safari/" in s else "")
    return dev + (f"／{br}" if br else "")


def research_answers(v, grade: str) -> tuple[dict, list[str]]:
    """題目陣列 → {題號: {id, facet, pick, text, correct}}（correct：計分題 1/0；態度題 ""）＋警告訊息。
    正解與是否計分一律依本工具題庫重算（中繼已重算過，這裡再保險一次）。"""
    out: dict = {}
    warn: list[str] = []
    if not isinstance(v, list):
        return out, warn
    ids = {q["id"] for q in RESEARCH_BANK.get(grade, [])}
    for it in v:
        if not isinstance(it, dict):
            continue
        qid = _to_text(it.get("id")).strip()
        q = RESEARCH_INDEX.get(qid)
        if not q or (ids and qid not in ids):
            warn.append(f"題號 {qid or '空白'} 不屬於{GRADE_LABEL.get(grade, '此')}版")
            continue
        pick = _game_int(it.get("pick"), 0, 3)
        scored = q["facet"] != ATTITUDE_FACET
        out[qid] = {"id": qid, "facet": q["facet"], "pick": pick,
                    "text": q["options"][pick] if pick != "" else "",
                    "correct": (1 if pick == q["answer"] else 0) if (scored and pick != "") else ""}
    return out, warn


def research_total(ans: dict, grade: str):
    """8 題計分題答對數；一題都沒有時回傳空白。"""
    vals = [ans[i]["correct"] for i in SCORED_IDS.get(grade, []) if i in ans and ans[i]["correct"] != ""]
    return sum(vals) if vals else ""


def load_research_records(jdir: Path, log=print) -> list[dict]:
    """讀取 test_json 內全部 JSON（schema webar-test-v1）；缺漏或型別不對者留空並註記，不崩潰。"""
    recs = []
    if not jdir.is_dir():
        return recs
    for p in sorted(jdir.glob("*.json")):
        try:
            obj = json.loads(p.read_text(encoding="utf-8-sig"))
            if not isinstance(obj, dict):
                raise ValueError("不是物件")
        except (OSError, ValueError) as e:
            log(f"⚠ 略過壞檔 {p.name}：{e}")
            continue
        r = {"file": p.name, "note": ""}
        if obj.get("schema") != SCHEMA_TEST:
            _add_note(r, f"schema 為 {obj.get('schema')}")
            log(f"注意：{p.name} 的 schema 為 {obj.get('schema')}，仍嘗試讀取")
        for k in ("event", "pid", "sid", "client_time", "ua", "commit"):
            r[k] = _to_text(obj.get(k)).strip()
        r["group"] = _to_text(obj.get("group")).strip()
        if r["group"] not in GROUP_LABEL:
            _add_note(r, f"組別不明（{r['group'] or '空白'}）")
            r["group"] = ""
        r["grade"] = _to_text(obj.get("grade")).strip()
        if r["grade"] not in GRADE_LABEL:
            _add_note(r, "版本不明")
            r["grade"] = ""
        r["mode"] = _to_text(obj.get("mode")).strip()
        phase = _to_text(obj.get("phase")).strip().lower()
        if phase not in PHASE_LABEL:
            m = re.search(r"_(pre|post)_", p.name)
            phase = m.group(1) if m else ""
            _add_note(r, f"phase 欄位不明，{'依檔名判為 ' + phase if phase else '無法判定'}")
        r["phase"] = phase
        r["submitted_at"] = parse_game_time(obj.get("submitted_at"))
        if r["submitted_at"] is None:
            _add_note(r, "submitted_at 無法解析")
        r["pre"], w1 = research_answers(obj.get("pre"), r["grade"])
        r["post"], w2 = research_answers(obj.get("post"), r["grade"])
        for w in w1 + w2:
            _add_note(r, w)
        stars = obj.get("stars")
        r["stars"] = [_game_int(x, 0, 3) for x in stars] if isinstance(stars, list) else []
        if r["group"] == "game" and r["phase"] == "post" and len(r["stars"]) != 8:
            _add_note(r, "遊戲班後測缺八關星數")
        r["totalStars"] = sum(x for x in r["stars"] if x != "") if any(x != "" for x in r["stars"]) else ""
        r["restarts"] = _game_int(obj.get("restarts"), 0, 99) if r["group"] == "game" else ""
        cp = _game_int(obj.get("commitPick"), 0, 3)
        r["commitPick"] = cp
        if cp != "" and not r["commit"]:
            r["commit"] = COMMITS[cp]
        recs.append(r)
    recs.sort(key=_game_sort_key)
    return recs


def filter_research(records: list[dict], event: str = "", group: str = "", grade: str = "") -> list[dict]:
    out = filter_by_event(records, event) if event else list(records)
    if group:
        out = [r for r in out if r["group"] == group]
    if grade:
        out = [r for r in out if r["grade"] == grade]
    return out


def dedupe_research(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """同一 sid＋階段有多筆：留 submitted_at 最早的一筆（時間無法解析者排最後），其餘列入已略過。
    缺 sid 的紀錄無法配對，一律保留並註記。"""
    kept, dropped, first = [], [], {}
    for r in sorted(records, key=_game_sort_key):
        if not r["sid"] or not r["phase"]:
            _add_note(r, "缺 sid 或階段，無法判定重複")
            kept.append(r)
            continue
        key = (r["sid"], r["phase"])
        if key in first:
            d = dict(r)
            d["base_file"] = first[key]["file"]
            d["reason"] = f"同一 sid＋{PHASE_LABEL[r['phase']]}重複上傳（保留最早一筆）"
            dropped.append(d)
            continue
        first[key] = r
        kept.append(r)
    return kept, dropped


def pair_students(kept: list[dict]) -> list[dict]:
    """以 sid 配對前測與後測，一個 sid 一列。後測檔內帶有完整前測作答：沒有獨立前測檔時改用它並註記來源。"""
    by: dict = {}
    order = []
    for r in kept:
        key = r["sid"] or ("(無 sid) " + r["file"])
        if key not in by:
            by[key] = {"pre": None, "post": None}
            order.append(key)
        slot = r["phase"] if r["phase"] in ("pre", "post") else "pre"
        if by[key][slot] is None:
            by[key][slot] = r
    out = []
    for key in order:
        pre, post = by[key]["pre"], by[key]["post"]
        base = post or pre
        notes = []
        s = {"sid": base["sid"], "pid": base["pid"], "event": base["event"], "group": base["group"],
             "grade": base["grade"], "mode": base["mode"], "ua": base["ua"],
             "pre_rec": pre, "post_rec": post, "pre_time": pre["submitted_at"] if pre else None,
             "post_time": post["submitted_at"] if post else None,
             "pre_file": pre["file"] if pre else "", "post_file": post["file"] if post else ""}
        if pre and post:
            for k in ("pid", "group", "grade", "event"):
                if pre[k] != post[k]:
                    notes.append(f"前後測 {k} 不一致（前測 {pre[k] or '空白'}／後測 {post[k] or '空白'}）")
        if pre and pre["pre"]:
            s["pre"], s["pre_source"] = pre["pre"], "前測檔"
            if post and post["pre"] and {k: v["pick"] for k, v in post["pre"].items()} != \
                    {k: v["pick"] for k, v in pre["pre"].items()}:
                notes.append("後測檔內的前測作答與前測檔不同（以前測檔為準）")
        elif post and post["pre"]:
            s["pre"], s["pre_source"] = post["pre"], "後測檔內的前測作答"
            notes.append("缺獨立前測檔，前測作答取自後測檔")
        else:
            s["pre"], s["pre_source"] = {}, ""
            notes.append("無前測作答")
        s["post"] = post["post"] if post else {}
        s["completed"] = bool(post and post["post"])
        if not s["completed"]:
            notes.append("未完成後測")
        g = s["grade"]
        s["pre_total"] = research_total(s["pre"], g)
        s["post_total"] = research_total(s["post"], g) if s["completed"] else ""
        s["gain"] = (s["post_total"] - s["pre_total"]) if (s["pre_total"] != "" and s["post_total"] != "") else ""
        s["commit"] = post["commit"] if post else ""
        s["commitPick"] = post["commitPick"] if post else ""
        s["stars"] = post["stars"] if (post and s["group"] == "game") else []
        s["totalStars"] = post["totalStars"] if (post and s["group"] == "game") else ""
        s["restarts"] = post["restarts"] if (post and s["group"] == "game") else \
            (pre["restarts"] if (pre and s["group"] == "game") else "")
        for r in (pre, post):
            if r and r.get("note"):
                notes.append(f"{PHASE_LABEL.get(r['phase'], '紀錄')}檔：{r['note']}")
        s["note"] = "；".join(notes)
        out.append(s)
    def first_time(s):
        t = s["pre_time"] or s["post_time"]
        return (t is None, t.timestamp() if t else 0, s["sid"])
    out.sort(key=first_time)
    return out


def _gkey(s: dict) -> tuple:
    return (s["group"], s["grade"], s["event"])


def compute_research_stats(all_n: int, in_range: list[dict], kept: list[dict], dropped: list[dict],
                           students: list[dict], meta: dict) -> dict:
    def mean(vals):
        v = [x for x in vals if x != ""]
        return (round(sum(v) / len(v), 2), len(v)) if v else (None, 0)

    groups: dict = {}
    for s in students:
        groups.setdefault(_gkey(s), []).append(s)
    gorder = sorted(groups, key=lambda k: (["game", "control", ""].index(k[0]) if k[0] in ("game", "control", "") else 9,
                                          ["elem", "junior", ""].index(k[1]) if k[1] in ("elem", "junior", "") else 9, k[2]))
    gstats = {}
    for k in gorder:
        ss = groups[k]
        grade = k[1]
        comp = [s for s in ss if s["completed"]]
        d = {"students": len(ss), "with_pre": sum(1 for s in ss if s["pre"]), "complete": len(comp),
             "pre_mean": mean([s["pre_total"] for s in ss]),
             "post_mean": mean([s["post_total"] for s in comp]),
             "pre_mean_complete": mean([s["pre_total"] for s in comp]),
             "gain_mean": mean([s["gain"] for s in comp]), "items": {}, "att": {}, "commits": [0, 0, 0, 0],
             "stars_mean": mean([s["totalStars"] for s in comp]) if k[0] == "game" else (None, 0)}
        for qid in SCORED_IDS.get(grade, []):
            pv = [s["pre"][qid]["correct"] for s in ss if qid in s["pre"] and s["pre"][qid]["correct"] != ""]
            qv = [s["post"][qid]["correct"] for s in comp if qid in s["post"] and s["post"][qid]["correct"] != ""]
            d["items"][qid] = ((round(sum(pv) / len(pv), 3) if pv else None, len(pv)),
                               (round(sum(qv) / len(qv), 3) if qv else None, len(qv)))
        for qid in ATTITUDE_IDS.get(grade, []):
            pre_c, post_c = [0, 0, 0, 0], [0, 0, 0, 0]
            for s in ss:
                p = s["pre"].get(qid, {}).get("pick", "")
                if p != "":
                    pre_c[p] += 1
            for s in comp:
                p = s["post"].get(qid, {}).get("pick", "")
                if p != "":
                    post_c[p] += 1
            d["att"][qid] = (pre_c, post_c)
        for s in comp:
            if s["commitPick"] != "":
                d["commits"][s["commitPick"]] += 1
        gstats[k] = d
    return {"range": meta.get("range_text", "不限"), "filters": meta.get("filters_text", ""),
            "generated": meta.get("generated", ""), "local": all_n, "in_range": len(in_range),
            "kept": len(kept), "dropped": len(dropped), "students": len(students),
            "complete": sum(1 for s in students if s["completed"]),
            "incomplete": sum(1 for s in students if not s["completed"]),
            "pre_from_post": sum(1 for s in students if s["pre_source"] == "後測檔內的前測作答"),
            "groups": gstats, "group_order": gorder}


def _grp_text(k: tuple) -> str:
    return f"{GROUP_LABEL.get(k[0], '（組別不明）')}｜{GRADE_LABEL.get(k[1], '（版本不明）')}｜{k[2] or '（無活動代碼）'}"


ANALYSIS_GRADES = (("elem", "分析用_國小elem"), ("junior", "分析用_國中junior"))


def analysis_columns(grade: str) -> list[str]:
    sc = SCORED_IDS[grade]
    at = ATTITUDE_IDS[grade]
    return (["row", "sid", "pid", "event", "group", "group_code", "grade", "mode", "completed", "pre_from_post",
             "pre_total", "post_total", "gain"]
            + [f"pre_{q}" for q in sc] + [f"post_{q}" for q in sc]
            + [f"att{i + 1}_pre" for i in range(len(at))] + [f"att{i + 1}_post" for i in range(len(at))]
            + ["commit"] + [f"stars{i}" for i in range(1, 9)] + ["total_stars", "restarts"])


def analysis_rows(students: list[dict], grade: str) -> list[list]:
    """分析用數值表（jamovi）：只含該版本學生；缺值為 None（xlsx 空白、CSV 空字串）。
    group_code：遊戲班 1、對照班 0；completed、pre_from_post：1/0；att＝態度題原始選項索引 0–3；commit＝承諾索引 0–3。"""
    rows = []
    sc, at = SCORED_IDS[grade], ATTITUDE_IDS[grade]
    nz = lambda v: None if v == "" else v  # noqa: E731
    for s in [x for x in students if x["grade"] == grade]:
        st = list(s["stars"]) + [""] * (8 - len(s["stars"])) if s["group"] == "game" else [""] * 8
        rows.append([len(rows) + 1, s["sid"], s["pid"], s["event"], s["group"] or None,
                     {"game": 1, "control": 0}.get(s["group"]), s["grade"], s["mode"] or None,
                     1 if s["completed"] else 0, 1 if s["pre_source"] == "後測檔內的前測作答" else 0,
                     nz(s["pre_total"]), nz(s["post_total"]), nz(s["gain"])]
                    + [nz(s["pre"].get(q, {}).get("correct", "")) for q in sc]
                    + [nz(s["post"].get(q, {}).get("correct", "")) for q in sc]
                    + [nz(s["pre"].get(q, {}).get("pick", "")) for q in at]
                    + [nz(s["post"].get(q, {}).get("pick", "")) for q in at]
                    + [nz(s["commitPick"])] + [nz(x) for x in st[:8]]
                    + [nz(s["totalStars"]), nz(s["restarts"])])
    return rows


def write_analysis_csv(students: list[dict], grade: str, path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(analysis_columns(grade))
        for row in analysis_rows(students, grade):
            w.writerow(["" if v is None else _csv_safe(v) if isinstance(v, str) else v for v in row])


def write_research_xlsx(students: list[dict], dropped: list[dict], stats: dict, path: Path,
                        surveys: list[dict] | None = None, survey_stats: dict | None = None) -> None:
    wb = Workbook()
    hfont = Font(name=FONT_NAME, bold=True, color="FFFFFF")
    hfill = PatternFill("solid", fgColor="0B1F3A")
    sfill = PatternFill("solid", fgColor="1C7293")
    bfont = Font(name=FONT_NAME)
    tfmt = "yyyy-mm-dd hh:mm:ss"

    def sheet(ws, headers, rows, widths, time_cols=(), freeze="A2", wrap_cols=(), keep_none=False):
        ws.append(headers)
        _style_header(ws[1], hfont, hfill)
        for vals in rows:
            ws.append(_safe_row(vals) if not keep_none else
                      [_csv_safe(v) if isinstance(v, str) else v for v in vals])
            for c in ws[ws.max_row]:
                c.font = bfont
                if c.column in time_cols and c.value not in ("", None):
                    c.number_format = tfmt
                if c.column in wrap_cols:
                    c.alignment = Alignment(wrap_text=True, vertical="top")
            _as_text(ws[ws.max_row])
        for i, _ in enumerate(headers, 1):
            ws.column_dimensions[get_column_letter(i)].width = widths.get(i, 12)
        ws.freeze_panes = freeze

    # 1 學生彙整
    hdr = ["序號", "活動代碼", "組別", "版本", "pid", "sid", "前測時間", "後測時間", "作答模式"]
    for ph in ("前測", "後測"):
        for i in range(1, RESEARCH_N + 1):
            hdr += [f"{ph}Q{i} 題號", f"{ph}Q{i} 選項索引", f"{ph}Q{i} 選項文字", f"{ph}Q{i} 對錯(1/0；態度題—)"]
    hdr += ["前測總分(8題)", "後測總分(8題)", "進步分數",
            "態度題1（E3／J3）前測選擇", "態度題1 後測選擇", "態度題2（E7／J8）前測選擇", "態度題2 後測選擇",
            "行動承諾"] + [f"第{i}關星數" for i in range(1, 9)] + ["總星數", "restarts（重闖次數）",
                                                              "裝置摘要", "完成後測", "前測作答來源", "資料來源註記",
                                                              "前測檔名", "後測檔名", "UA"]
    rows = []
    for n, s in enumerate(students, 1):
        g = s["grade"]
        row = [n, s["event"], GROUP_LABEL.get(s["group"], ""), GRADE_LABEL.get(g, ""), s["pid"], s["sid"],
               _xl_time(s["pre_time"]), _xl_time(s["post_time"]), RESEARCH_MODE_LABEL.get(s["mode"], s["mode"])]
        qs = RESEARCH_BANK.get(g, [])
        for ans in (s["pre"], s["post"]):
            for i in range(RESEARCH_N):
                q = qs[i] if i < len(qs) else None
                a = ans.get(q["id"]) if q else None
                if a:
                    mark = "—" if a["facet"] == ATTITUDE_FACET else a["correct"]
                    row += [a["id"], a["pick"], a["text"], mark]
                else:
                    row += ["", "", "", ""]
        att = ATTITUDE_IDS.get(g, [])
        atext = lambda ans, i: ans.get(att[i], {}).get("text", "") if i < len(att) else ""  # noqa: E731
        st = list(s["stars"]) + [""] * (8 - len(s["stars"])) if s["group"] == "game" else [""] * 8
        row += [s["pre_total"], s["post_total"], s["gain"], atext(s["pre"], 0), atext(s["post"], 0),
                atext(s["pre"], 1), atext(s["post"], 1), s["commit"]] + st[:8] + \
               [s["totalStars"], s["restarts"], ua_summary(s["ua"]), "是" if s["completed"] else "否（未完成後測）",
                s["pre_source"], s["note"], s["pre_file"], s["post_file"], s["ua"]]
        rows.append(row)
    widths = {1: 6, 2: 20, 3: 8, 4: 6, 5: 14, 6: 14, 7: 19, 8: 19, 9: 16}
    base = 10 + RESEARCH_N * 8
    for i, w in enumerate([12, 12, 9, 22, 22, 22, 22, 24] + [7] * 8 + [8, 10, 18, 14, 18, 44, 30, 30, 50]):
        widths[base + i] = w
    sheet(wb.active, hdr, rows, widths, time_cols=(7, 8), freeze="G2", wrap_cols=(base + 21,))
    wb.active.title = "學生彙整"

    # 2 分析用（數值）：國小、國中分兩張（題號不同，避免同一欄混到不同題目）
    for grade, name in ANALYSIS_GRADES:
        cols = analysis_columns(grade)
        sheet(wb.create_sheet(name), cols, analysis_rows(students, grade),
              {1: 5, 2: 14, 3: 14, 4: 18}, keep_none=True, freeze="C2")

    # 3 統計
    st = wb.create_sheet("統計")
    hdr_rows = []

    def h(*vals):
        st.append(list(vals))
        hdr_rows.append(st.max_row)

    h("項目", "數值")
    for k, v in [("篩選區間（上傳時間）", stats["range"]), ("篩選條件", stats["filters"] or "不篩選"),
                 ("本機研究紀錄總筆數", stats["local"]), ("篩選後筆數", stats["in_range"]),
                 ("保留筆數", stats["kept"]), ("略過（同 sid＋階段重複）", stats["dropped"]),
                 ("學生數（sid）", stats["students"]), ("完成前後測", stats["complete"]),
                 ("未完成後測", stats["incomplete"]), ("前測作答取自後測檔", stats["pre_from_post"]),
                 ("產生時間", stats["generated"])]:
        st.append([k, v])
    st.append([])
    h("組別｜版本｜活動代碼", "學生數", "前測人數", "完成前後測人數", "前測平均(全部)", "完成者前測平均",
      "後測平均", "平均進步", "平均總星數")
    m = lambda p: "" if p[0] is None else p[0]  # noqa: E731
    for k in stats["group_order"]:
        d = stats["groups"][k]
        st.append([_grp_text(k), d["students"], d["with_pre"], d["complete"], m(d["pre_mean"]),
                   m(d["pre_mean_complete"]), m(d["post_mean"]), m(d["gain_mean"]), m(d["stars_mean"])])
    for k in stats["group_order"]:
        d = stats["groups"][k]
        qs = {q["id"]: q for q in RESEARCH_BANK.get(k[1], [])}
        st.append([])
        h(f"逐題答對率｜{_grp_text(k)}", "面向", "前測答對率", "前測作答數", "後測答對率（完成者）", "後測作答數")
        for qid, (pv, qv) in d["items"].items():
            st.append([f"{qid} {qs[qid]['q']}", qs[qid]["facet"], m(pv), pv[1], m(qv), qv[1]])
        st.append([])
        h(f"態度題選項人數｜{_grp_text(k)}", "選項", "前測人數", "後測人數（完成者）")
        for qid, (pc, qc) in d["att"].items():
            for i, o in enumerate(qs[qid]["options"]):
                st.append([f"{qid} {qs[qid]['q']}" if i == 0 else "", f"{'ABCD'[i]}（索引{i}）{o}", pc[i], qc[i]])
        st.append([])
        h(f"行動承諾分布（完成者）｜{_grp_text(k)}", "人數")
        for i, c in enumerate(COMMITS):
            st.append([f"{i}：{c}", d["commits"][i]])
    for row in st.iter_rows():
        for c in row:
            c.font = bfont
            if isinstance(c.value, str):
                c.value = _csv_safe(c.value)
    for rno in hdr_rows:
        for c in st[rno]:
            c.font, c.fill = hfont, (hfill if rno == hdr_rows[0] else sfill)
    for col, w in zip("ABCDEFGHI", (52, 16, 12, 16, 16, 16, 12, 12, 12)):
        st.column_dimensions[col].width = w

    # 3.5 v7.1：學生版課後問卷（班級層級；沒有資料也建表）
    surveys = surveys or []
    _write_survey_sheets(wb, surveys, survey_stats or compute_survey_stats(surveys), hfont, hfill, sfill, bfont)

    # 4 已略過（重複）
    sheet(wb.create_sheet("已略過（重複）"),
          ["檔名", "上傳時間", "sid", "pid", "階段", "組別", "版本", "活動代碼", "保留的檔名", "原因"],
          [[d["file"], _xl_time(d["submitted_at"]), d["sid"], d["pid"], PHASE_LABEL.get(d["phase"], d["phase"]),
            GROUP_LABEL.get(d["group"], ""), GRADE_LABEL.get(d["grade"], ""), d["event"], d.get("base_file", ""),
            d.get("reason", "")] for d in dropped],
          {1: 32, 2: 19, 3: 14, 4: 14, 5: 6, 6: 8, 7: 6, 8: 20, 9: 32, 10: 34}, time_cols=(2,))

    # 5 題目對照
    qrows = []
    for g, qs in RESEARCH_BANK.items():
        for q in qs:
            opts = list(q["options"]) + [""] * (4 - len(q["options"]))
            scored = q["facet"] != ATTITUDE_FACET
            qrows.append([q["id"], GRADE_LABEL[g], q["facet"], "是" if scored else "否（態度題，只記選擇）",
                          q["q"]] + opts[:4] + [q["options"][q["answer"]] if scored else "（無標準答案）",
                                                q["answer"] if scored else "", q["explain"]])
    sheet(wb.create_sheet("題目對照"),
          ["題號", "版本", "面向", "是否計分", "題目", "選項A（索引0）", "選項B（索引1）", "選項C（索引2）",
           "選項D（索引3）", "正解", "正解索引", "解說"], qrows,
          {1: 6, 2: 6, 3: 6, 4: 18, 5: 48, 6: 22, 7: 18, 8: 18, 9: 18, 10: 22, 11: 8, 12: 40},
          wrap_cols=(5, 12), freeze="B2")
    wb.save(path)


# ---------------------------------------------------------------- v7.1：學生版課後問卷（研究班級，feedback/responses）
UNKNOWN_LABEL = "未知"
SURVEY_CSV_SUFFIX = "_課後問卷_分析用.csv"
SURVEY_LIKERT = [k for code, _, items, _ in STUDENT_FACETS if code != "k" for k, _ in items]
SURVEY_FACETS = [(code, name, [k for k, _ in items]) for code, name, items, _ in STUDENT_FACETS if code != "k"]
SURVEY_MEAN_COLS = {"a": "attitude_mean", "i": "action_mean", "s": "inquiry_mean"}
SURVEY_NONE_TEXT = "尚無課後問卷"
SURVEY_CLASS_NOTE = ("課後問卷不記名、沒有 sid，與前後測之間沒有個人層級的對應，"
                     "只能依活動代碼（班級）與組別、學段做班級層級比較。")


def _group_text(g: str) -> str:
    return GROUP_LABEL.get(g, UNKNOWN_LABEL)


def _grade_text(g: str) -> str:
    return GRADE_LABEL.get(g, UNKNOWN_LABEL)


def research_event_map(recs: list[dict]) -> dict:
    """研究紀錄 → {event 小寫: (group, grade)}；同一 event 有多種值時取筆數最多者，空值不計。"""
    cnt: dict = {}
    for r in recs:
        ev = _to_text(r.get("event")).strip().lower()
        if not ev:
            continue
        d = cnt.setdefault(ev, {"group": {}, "grade": {}})
        for k in ("group", "grade"):
            if r.get(k):
                d[k][r[k]] = d[k].get(r[k], 0) + 1
    return {ev: tuple(max(d[k], key=d[k].get) if d[k] else "" for k in ("group", "grade"))
            for ev, d in cnt.items()}


def survey_group_grade(event, emap: dict) -> tuple[str, str, str]:
    """問卷 event → (group, grade, 依據)。先看同 event 的研究紀錄，缺的部分再由活動代碼推斷；都推不出來＝空字串。"""
    g, d = emap.get(_to_text(event).strip().lower(), ("", ""))
    ig, idg = infer_group_grade(event)
    basis = []
    if g or d:
        basis.append("研究紀錄")
    if (not g and ig) or (not d and idg):
        basis.append("代碼推斷")
    g, d = g or ig, d or idg
    if not g or not d:
        basis.append("部分未知" if (g or d) else "無法判定")
    return g, d, "＋".join(basis)


def _fmean(vals: list):
    return round(sum(vals) / len(vals), 3) if vals else ""


def _fsd(vals: list):
    """樣本標準差（n−1）；不足 2 筆回傳空白。"""
    if len(vals) < 2:
        return ""
    m = sum(vals) / len(vals)
    return round((sum((x - m) ** 2 for x in vals) / (len(vals) - 1)) ** 0.5, 3)


def load_survey_records(jdir: Path, research_recs: list[dict], codes=(), log=print) -> list[dict]:
    """讀取 json\\ 內回饋問卷，只留屬於研究的（is_research_event；codes＝本次篩選後研究紀錄的活動代碼），
    並補上組別、學段、填答時間（台北時間）、每份三面向平均。v1 舊版問卷一律不納入。"""
    emap = research_event_map(research_recs)
    out = []
    for r in load_records(jdir, log=log):
        if r.get("ver") == "v1" or not is_research_event(r.get("event"), codes):
            continue
        g, d, basis = survey_group_grade(r["event"], emap)
        s = {"file": r["file"], "event": _to_text(r["event"]).strip(), "group": g, "grade": d, "basis": basis,
             "submitted_raw": r.get("submitted_at", ""), "submitted_at": parse_game_time(r.get("submitted_at")),
             "ua": r.get("ua", ""), "k_score": r.get("k_score", "")}
        for k, _ in STUDENT_KNOWLEDGE:
            s[k] = r.get(k, "")
            s[k + "_ok"] = r.get(k + "_ok", "") if s[k] else ""
        for k in SURVEY_LIKERT:
            s[k] = r.get(k, "")
        for code, _, ks in SURVEY_FACETS:
            s[code + "_mean"] = _fmean([s[k] for k in ks if isinstance(s[k], (int, float))])
        for _, _, _, (ok, _) in STUDENT_FACETS:
            s[ok] = r.get(ok, "")
        # v7.2：TAM 六題（齊全且有效才填；不齊或越界留空並註記）
        tam, note = parse_tam(r.get("_tam_raw"))
        s["tam_ok"] = tam is not None
        s["tam_note"] = note
        for k in TAM_KEYS:
            s[k] = tam[k] if tam else ""
        for code, _, _, items, _ in TAM_FACETS:
            s[code + "_mean"] = _fmean([tam[k] for k, _ in items]) if tam else ""
        if note:
            log(f"注意：{r['file']} {note}")
        out.append(s)
    out.sort(key=_game_sort_key)
    return out


def filter_surveys(rows: list[dict], start=None, end=None, event: str = "", group: str = "",
                   grade: str = "") -> list[dict]:
    """與研究紀錄相同的篩選：起迄時間、活動（不分大小寫）、組別、學段（組別／學段未知者在指定篩選時不納入）。"""
    out = filter_by_event(filter_by_time(rows, start, end), event) if event else filter_by_time(rows, start, end)
    if group:
        out = [r for r in out if r["group"] == group]
    if grade:
        out = [r for r in out if r["grade"] == grade]
    return out


def _survey_order_key(k: tuple):
    gi = {"game": 0, "control": 1}.get(k[0], 2)
    di = {"elem": 0, "junior": 1}.get(k[1], 2)
    return (gi, di) + tuple(x.lower() for x in k[2:])


def _survey_block(rows: list[dict]) -> dict:
    d = {"n": len(rows), "k": {}, "items": {}, "facets": {}}
    for k, _ in STUDENT_KNOWLEDGE:
        oks = [r[k + "_ok"] for r in rows if r.get(k + "_ok") in (0, 1)]
        d["k"][k] = (round(sum(oks) / len(oks), 4) if oks else "", len(oks), sum(oks))
    ks = [r["k_score"] for r in rows if isinstance(r.get("k_score"), int)]
    d["k_score"] = (_fmean(ks), len(ks))
    for k in SURVEY_LIKERT:
        v = [r[k] for r in rows if isinstance(r.get(k), (int, float))]
        d["items"][k] = (_fmean(v), _fsd(v), len(v))
    for code, _, _ in SURVEY_FACETS:
        v = [r[code + "_mean"] for r in rows if isinstance(r.get(code + "_mean"), (int, float))]
        d["facets"][code] = (_fmean(v), _fsd(v), len(v))
    # v7.2：科技接受度（只計六題齊全有效的問卷；構面以每份問卷的構面平均計算）
    tam_rows = [r for r in rows if r.get("tam_ok")]
    t = {"n": len(tam_rows), "items": {}, "facets": {}}
    for k in TAM_KEYS:
        v = [r[k] for r in tam_rows]
        t["items"][k] = (_fmean(v), _fsd(v), len(v))
    for code, _, _, _, _ in TAM_FACETS:
        v = [r[code + "_mean"] for r in tam_rows]
        t["facets"][code] = (_fmean(v), _fsd(v), len(v))
    d["tam"] = t
    return d


def compute_survey_stats(rows: list[dict]) -> dict:
    """依「組別｜學段｜活動代碼」與「組別｜學段」分組：份數、知識題答對率、九題與三面向平均／標準差。
    面向平均與標準差以「每份問卷的面向平均（該面向有效題目的平均）」計算。"""
    by: dict = {}
    merged: dict = {}
    for r in rows:
        by.setdefault((r["group"], r["grade"], r["event"]), []).append(r)
        merged.setdefault((r["group"], r["grade"]), []).append(r)
    order = sorted(by, key=_survey_order_key)
    morder = sorted(merged, key=_survey_order_key)
    count = {"game": 0, "control": 0, "": 0}
    for r in rows:
        count[r["group"] if r["group"] in count else ""] += 1
    return {"n": len(rows), "by_group": count, "groups": {k: _survey_block(by[k]) for k in order}, "order": order,
            "merged": {k: _survey_block(merged[k]) for k in morder}, "merged_order": morder,
            "all": _survey_block(rows),
            "tam_n": sum(1 for r in rows if r.get("tam_ok")),                 # v7.2
            "tam_invalid": sum(1 for r in rows if r.get("tam_note"))}


def _survey_key_text(k: tuple) -> str:
    return "｜".join([_group_text(k[0]), _grade_text(k[1])] + [x or "（無活動代碼）" for x in k[2:]])


def survey_count_text(st: dict) -> str:
    c = st["by_group"]
    return (f"課後問卷 {st['n']} 份（遊戲班 {c['game']}、對照班 {c['control']}"
            + (f"、組別未知 {c['']}" if c[""] else "") + "）")


def tam_count_text(st: dict) -> str:
    """v7.2：「其中含科技接受度題 N 份」（有不完整／無效者另註）。"""
    n, bad = st.get("tam_n", 0), st.get("tam_invalid", 0)
    return f"其中含科技接受度題 {n} 份" + (f"（另 {bad} 份 TAM 不完整或無效，已留空）" if bad else "")


def survey_columns() -> list[str]:
    return (["row", "event", "group", "group_code", "grade", "submitted_at"]
            + [x for k, _ in STUDENT_KNOWLEDGE for x in (k, k + "_correct")] + ["k_score"]
            + SURVEY_LIKERT + [SURVEY_MEAN_COLS[c] for c, _, _ in SURVEY_FACETS]
            + TAM_KEYS + [col for _, _, _, _, col in TAM_FACETS] + ["file"])   # v7.2：TAM 欄


def survey_analysis_rows(rows: list[dict]) -> list[list]:
    """jamovi 用：一列一份；缺值為 None；group／grade 推不出來＝unknown；group_code 遊戲班 1、對照班 0。"""
    out = []
    nz = lambda v: None if v == "" else v  # noqa: E731
    for i, r in enumerate(rows, 1):
        t = r["submitted_at"]
        out.append([i, r["event"], r["group"] or "unknown", {"game": 1, "control": 0}.get(r["group"]),
                     r["grade"] or "unknown", t.strftime("%Y-%m-%d %H:%M:%S") if t else (r["submitted_raw"] or None)]
                    + [x for k, _ in STUDENT_KNOWLEDGE for x in (nz(r[k]), nz(r[k + "_ok"]))] + [nz(r["k_score"])]
                    + [nz(r[k]) for k in SURVEY_LIKERT] + [nz(r[c + "_mean"]) for c, _, _ in SURVEY_FACETS]
                    + [nz(r.get(k, "")) for k in TAM_KEYS] + [nz(r.get(c + "_mean", "")) for c, _, _, _, _ in TAM_FACETS]
                    + [r["file"]])
    return out


def write_survey_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(survey_columns())
        for row in survey_analysis_rows(rows):
            w.writerow(["" if v is None else _csv_safe(v) if isinstance(v, str) else v for v in row])


def _write_survey_sheets(wb, surveys: list[dict], sst: dict, hfont, hfill, sfill, bfont) -> None:
    """xlsx「課後問卷」（一列一份）與「課後問卷統計」兩張工作表；沒有資料時寫「尚無課後問卷」。"""
    tfmt = "yyyy-mm-dd hh:mm:ss"
    ws = wb.create_sheet("課後問卷")
    hdr = ["序號", "活動代碼", "組別", "學段", "填答時間"]
    for k, lab in STUDENT_KNOWLEDGE:
        hdr += [f"{lab.split()[0]} 作答", f"{lab.split()[0]} 對錯(1/0；正解 {STUDENT_ANSWER_KEY[k]})"]
    hdr += ["知識答對數(0–3)"] + [lab for code, _, items, _ in STUDENT_FACETS if code != "k" for _, lab in items]
    hdr += [f"{name}平均" for _, name, _ in SURVEY_FACETS]
    hdr += [lab for _, lab in TAM_ITEMS] + [f"{name}平均" for _, name, _, _, _ in TAM_FACETS]   # v7.2：TAM
    hdr += [olab for _, _, _, (_, olab) in STUDENT_FACETS] + ["裝置摘要", "組別／學段依據", "科技接受度註記", "檔名"]
    ws.append(hdr)
    _style_header(ws[1], hfont, hfill)
    wrap_cols = {i for i, h in enumerate(hdr, 1) if "簡答" in h or h == "科技接受度註記"}
    if not surveys:
        ws.append([SURVEY_NONE_TEXT])
    for n, r in enumerate(surveys, 1):
        row = [n, r["event"], _group_text(r["group"]), _grade_text(r["grade"]),
               _xl_time(r["submitted_at"]) if r["submitted_at"] else r["submitted_raw"]]
        for k, _ in STUDENT_KNOWLEDGE:
            row += [r[k], r[k + "_ok"]]
        row += [r["k_score"]] + [r[k] for k in SURVEY_LIKERT] + [r[c + "_mean"] for c, _, _ in SURVEY_FACETS]
        row += [r.get(k, "") for k in TAM_KEYS] + [r.get(c + "_mean", "") for c, _, _, _, _ in TAM_FACETS]
        row += [r[ok] for _, _, _, (ok, _) in STUDENT_FACETS]
        row += [ua_summary(r["ua"]), r["basis"], r.get("tam_note", ""), r["file"]]
        ws.append(_safe_row(row))
        for c in ws[ws.max_row]:
            c.font = bfont
            if c.column == 5 and isinstance(c.value, datetime):
                c.number_format = tfmt
            if c.column in wrap_cols:
                c.alignment = Alignment(wrap_text=True, vertical="top")
        _as_text(ws[ws.max_row])
    for i, h in enumerate(hdr, 1):
        w = (6 if i == 1 else 20 if i == 2 else 19 if i == 5 else 36 if "簡答" in h else 30 if i == len(hdr)
             else 28 if h == "科技接受度註記" else 12)
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "C2"

    st = wb.create_sheet("課後問卷統計")
    hdr_rows = []

    def h(*vals):
        st.append(list(vals))
        hdr_rows.append(st.max_row)

    cols = ["份數"] + [f"{lab.split()[0]} 答對率" for _, lab in STUDENT_KNOWLEDGE] + ["知識答對數平均"]
    for code, name, items, _ in STUDENT_FACETS:
        if code == "k":
            continue
        for _, lab in items:
            cols += [f"{lab.split()[0]} 平均", f"{lab.split()[0]} 標準差"]
    cols += [x for _, name, _ in SURVEY_FACETS for x in (f"{name}平均", f"{name}標準差")]

    def block_row(label, d):
        row = [label, d["n"]] + [d["k"][k][0] for k, _ in STUDENT_KNOWLEDGE] + [d["k_score"][0]]
        for k in SURVEY_LIKERT:
            row += list(d["items"][k][:2])
        for code, _, _ in SURVEY_FACETS:
            row += list(d["facets"][code][:2])
        st.append(row)
        for i in range(3, 6):
            if isinstance(st.cell(st.max_row, i).value, float):
                st.cell(st.max_row, i).number_format = "0.0%"

    h("項目", "內容")
    st.append(["說明", SURVEY_CLASS_NOTE])
    st.append(["份數", survey_count_text(sst)])
    st.append(["題組", BANK_LABEL[BANK_STUDENT] + f"；題幹「{STUDENT_STEM}」"])
    st.append(["計算方式", "答對率＝答對數／作答數；平均與標準差（樣本標準差 n−1，不足 2 份留白）只計有效作答；"
                          "面向平均與標準差以每份問卷的面向平均（該面向三題中有效題目的平均）計算。"])
    st.append([])
    if not surveys:
        st.append([SURVEY_NONE_TEXT])
    else:
        h("組別｜學段｜活動代碼", *cols)
        for k in sst["order"]:
            block_row(_survey_key_text(k), sst["groups"][k])
        st.append([])
        h("組別｜學段（合併各班）", *cols)
        for k in sst["merged_order"]:
            block_row(_survey_key_text(k), sst["merged"][k])
        block_row("全部", sst["all"])
    # v7.2：科技接受度（僅遊戲班作答）；只列有 TAM 作答的分組
    st.append([])
    h("科技接受度（僅遊戲班作答）", "內容")
    st.append(["說明", f"TAM 六題（{TAM_SOURCE}）只出現在遊戲班的學生版課後問卷；六題齊全且皆為 1–5 整數才計入，"
                       "不完整或無效者在「課後問卷」的「科技接受度註記」欄標示。構面平均與標準差以每份問卷的構面平均"
                       "（該構面三題平均）計算；樣本標準差 n−1，不足 2 份留白。"])
    st.append(["份數", tam_count_text(sst)])
    tcols = ["問卷份數", "含科技接受度份數"]
    for _, lab in TAM_ITEMS:
        tcols += [f"{lab.split()[0]} 平均", f"{lab.split()[0]} 標準差"]
    tcols += [x for _, name, abbr, _, _ in TAM_FACETS for x in (f"{name}（{abbr}）平均", f"{name}（{abbr}）標準差")]

    def tam_row(label, d):
        t = d["tam"]
        row = [label, d["n"], t["n"]]
        for k in TAM_KEYS:
            row += list(t["items"][k][:2])
        for code, _, _, _, _ in TAM_FACETS:
            row += list(t["facets"][code][:2])
        st.append(row)

    if not sst.get("tam_n"):
        st.append(["尚無科技接受度作答"])
    else:
        h("組別｜學段｜活動代碼", *tcols)
        for k in sst["order"]:
            if sst["groups"][k]["tam"]["n"]:
                tam_row(_survey_key_text(k), sst["groups"][k])
        st.append([])
        h("組別｜學段（合併各班）", *tcols)
        for k in sst["merged_order"]:
            if sst["merged"][k]["tam"]["n"]:
                tam_row(_survey_key_text(k), sst["merged"][k])
        tam_row("全部", sst["all"])
    st.append([])
    h("題號", "題目（學生版課後問卷）", "正解")
    for code, name, items, (ok, olab) in STUDENT_FACETS:
        for k, lab in items:
            st.append([k, f"【{name}】{lab}", STUDENT_ANSWER_KEY.get(k, "（1–5 量表）")])
        st.append([ok, f"【{name}】{olab}", "（簡答）"])
    for code, name, abbr, items, _ in TAM_FACETS:                          # v7.2
        for k, lab in items:
            st.append([k, f"【科技接受度－{name}（{abbr}）】{lab}", "（1–5 量表；僅遊戲班）"])
    st.append(["", f"科技接受度題：{TAM_SOURCE}。", ""])
    for row in st.iter_rows():
        for c in row:
            c.font = bfont
            if isinstance(c.value, str):
                c.value = _csv_safe(c.value)
    for rno in hdr_rows:
        for c in st[rno]:
            c.font, c.fill = hfont, (hfill if rno == hdr_rows[0] else sfill)
            c.alignment = Alignment(wrap_text=True, vertical="center")
    st.column_dimensions["A"].width = 40
    st.column_dimensions["B"].width = 14
    for i in range(3, len(cols) + 3):
        st.column_dimensions[get_column_letter(i)].width = 11
    st.freeze_panes = "B2"


def research_default_name(start: datetime | None, end: datetime | None, now: datetime | None = None) -> str:
    """預設檔名：研究用前後測_<起>至<迄>_匯出<時間>.xlsx（未設區間＝全部）。"""
    now = now or datetime.now()
    a = start.strftime("%Y%m%d-%H%M") if start else "不限"
    b = end.strftime("%Y%m%d-%H%M") if end else "不限"
    rng = "全部" if not start and not end else f"{a}至{b}"
    return f"研究用前後測_{rng}_匯出{now:%Y%m%d-%H%M}.xlsx"


def analysis_csv_paths(xlsx_path: Path) -> dict:
    return {g: xlsx_path.with_name(f"{xlsx_path.stem}_分析用_{g}.csv") for g, _ in ANALYSIS_GRADES}


def survey_csv_path(xlsx_path: Path) -> Path:
    return xlsx_path.with_name(f"{xlsx_path.stem}{SURVEY_CSV_SUFFIX}")


def run_research_export(dest: Path, xlsx_path: Path, start: datetime | None = None,
                        end: datetime | None = None, token: str | None = None, log=print,
                        offline: bool = False, session=None, event: str | None = None,
                        group: str | None = None, grade: str | None = None) -> dict:
    """研究用前後測：下載新檔到 dest\\test_json → 讀取 → 篩選 → sid＋階段去重 → sid 配對 → 統計 → 寫 xlsx＋CSV。"""
    dest = Path(dest)
    xlsx_path = Path(xlsx_path)
    dest.mkdir(parents=True, exist_ok=True)
    try:
        grp = norm_group(group)
        grd = norm_grade(grade)
    except ValueError as e:
        raise FetchError(str(e))
    remote_n = ok = bad = None
    sremote_n = sok = None
    if offline:
        log("離線模式：不連網，只讀本機 test_json（前後測）與 json（課後問卷）")
    else:
        log("連線 GitHub 查詢研究用前後測清單（feedback/test）…")
        remote = list_remote(token, session, api_url=TEST_API_URL)
        remote_n = len(remote)
        if remote_n == 0:
            log("GitHub 上尚無研究資料（feedback/test 尚未建立或是空的）。")
        else:
            log(f"GitHub 上共有 {remote_n} 筆研究紀錄")
        ok, bad = download_new(dest, remote, token, log=log, session=session, subdir=TEST_JSON_SUBDIR)
        log(f"本次新下載 {ok} 筆" + (f"，壞檔 {bad} 筆" if bad else ""))
        # v7.1：學生版課後問卷與成人版共用 feedback/responses；下載到研究資料夾的 json\（失敗不影響前後測匯出）
        log("連線 GitHub 查詢回饋問卷清單（feedback/responses，挑出學生版課後問卷）…")
        try:
            sremote = list_remote(token, session, api_url=API_URL)
            sremote_n = len(sremote)
            sok, sbad = download_new(dest, sremote, token, log=log, session=session, subdir=JSON_SUBDIR)
            log(f"回饋問卷 GitHub 上 {sremote_n} 筆、本次新下載 {sok} 筆" + (f"，壞檔 {sbad} 筆" if sbad else ""))
        except FetchError as e:
            log(f"⚠ 回饋問卷下載失敗，改用本機 json 既有檔案：{e}")
    recs = load_research_records(dest / TEST_JSON_SUBDIR, log=log)
    if not recs:
        log("尚無研究資料：本機 test_json 沒有任何紀錄，仍輸出空白格式的 Excel。")
    ev = event_code(event)
    ev = "" if ev == EVENT_ALL else ev
    in_range = filter_research(filter_by_time(recs, start, end), ev, grp, grd)
    kept, dropped = dedupe_research(in_range)
    students = pair_students(kept)
    filt = "；".join(x for x in [f"活動 {ev}" if ev else "", f"組別 {GROUP_LABEL[grp]}" if grp else "",
                                 f"版本 {GRADE_LABEL[grd]}" if grd else ""] if x)
    meta = {"range_text": _range_text(_to_tpe(start), _to_tpe(end)), "filters_text": filt,
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    stats = compute_research_stats(len(recs), in_range, kept, dropped, students, meta)
    # v7.1：課後問卷（研究活動代碼＋同樣的時間／活動／組別／學段篩選）
    codes = {r["event"] for r in in_range if r.get("event")}
    surveys = filter_surveys(load_survey_records(dest / JSON_SUBDIR, recs, codes, log=lambda m: None),
                             start, end, ev, grp, grd)
    sst = compute_survey_stats(surveys)
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    csvs = analysis_csv_paths(xlsx_path)
    scsv = survey_csv_path(xlsx_path)
    try:
        write_research_xlsx(students, dropped, stats, xlsx_path, surveys, sst)
        for g, p in csvs.items():
            write_analysis_csv(students, g, p)
        write_survey_csv(surveys, scsv)
    except PermissionError as e:
        raise FetchError(f"無法寫入 {Path(e.filename or xlsx_path).name}，可能正在 Excel 中開啟，請關閉後再試。")
    res = {"remote": remote_n, "new": ok, "bad": bad, "local": len(recs), "in_range": len(in_range),
           "kept": len(kept), "dropped": len(dropped), "students": stats["students"],
           "complete": stats["complete"], "path": str(xlsx_path), "csv": {g: str(p) for g, p in csvs.items()},
           "stats": stats, "survey_remote": sremote_n, "survey_new": sok, "surveys": len(surveys),
           "survey_stats": sst, "survey_csv": str(scsv)}
    for line in research_summary_lines(res):
        log(line)
    return res


def research_summary_lines(res: dict) -> list[str]:
    st = res["stats"]
    out = []
    if res.get("remote") is not None:
        out.append(f"GitHub 上 {res['remote']} 筆、本次新下載 {res['new']} 筆"
                   + (f"、壞檔 {res['bad']} 筆" if res.get("bad") else ""))
    if res["local"] == 0:
        out.append("尚無研究資料（本機 test_json 0 筆）")
    out.append(f"本機研究紀錄 {res['local']} 筆；篩選區間：{st['range']}；篩選：{st['filters'] or '不篩選'}；"
               f"篩選後 {res['in_range']} 筆")
    out.append(f"保留 {res['kept']} 筆、略過重複 {res['dropped']} 筆；學生 {res['students']} 人，"
               f"完成前後測 {res['complete']} 人、未完成後測 {st['incomplete']} 人、前測取自後測檔 {st['pre_from_post']} 人")
    for k in st["group_order"]:
        d = st["groups"][k]
        mm = lambda p: "—" if p[0] is None else f"{p[0]}"  # noqa: E731
        out.append(f"　{_grp_text(k)}：{d['students']} 人、完成 {d['complete']} 人；前測平均 {mm(d['pre_mean'])}／8、"
                   f"後測平均 {mm(d['post_mean'])}／8、平均進步 {mm(d['gain_mean'])}")
    sst = res.get("survey_stats")
    if sst is not None:
        if res.get("survey_remote") is not None:
            out.append(f"回饋問卷 GitHub 上 {res['survey_remote']} 筆、本次新下載 {res['survey_new']} 筆（含成人版，已排除）")
        out.append(survey_count_text(sst) + "；" + tam_count_text(sst) + "；與前後測無個人層級對應，只做班級層級比較")
        for k in sst["order"]:
            d = sst["groups"][k]
            fm = "、".join(f"{name} {d['facets'][c][0] if d['facets'][c][0] != '' else '—'}" for c, name, _ in SURVEY_FACETS)
            t = d.get("tam") or {"n": 0}
            tm = ("；科技接受度 {} 份：".format(t["n"]) + "、".join(
                f"{name} {t['facets'][c][0]}" for c, name, _, _, _ in TAM_FACETS)) if t["n"] else ""
            out.append(f"　{_survey_key_text(k)}：{d['n']} 份；知識答對數平均 "
                       f"{d['k_score'][0] if d['k_score'][0] != '' else '—'}／3；{fm}{tm}")
    out.append(f"輸出：{res['path']}")
    for g, p in res.get("csv", {}).items():
        out.append(f"CSV（{GRADE_LABEL[g]}）：{p}")
    if res.get("survey_csv"):
        out.append(f"CSV（課後問卷）：{res['survey_csv']}")
    return out


def cli_research_export(argv: list[str]) -> int:
    """不互動模式：--research-export <dest> <xlsx> [--from ..] [--to ..] [--event 代碼]
    [--group 遊戲班|對照班|game|control] [--grade 國小|國中|elem|junior] [--offline]。"""
    lines = [f"{APP_TITLE} v{VERSION}　{datetime.now():%Y-%m-%d %H:%M:%S}　--research-export " + " ".join(argv)]
    dest = Path(argv[0]) if argv else Path(".")
    code = 0
    try:
        if len(argv) < 2:
            raise FetchError("用法：--research-export <資料夾> <輸出.xlsx> [--from \"YYYY-MM-DD HH:MM\"]"
                             " [--to \"YYYY-MM-DD HH:MM\"] [--event 活動代碼] [--group 遊戲班|對照班]"
                             " [--grade 國小|國中] [--offline]")
        xlsx = Path(argv[1])
        opts = {"--from": "", "--to": "", "--event": "", "--group": "", "--grade": ""}
        offline = False
        i = 2
        while i < len(argv):
            a = argv[i]
            if a == "--offline":
                offline = True
                i += 1
            elif a in opts and i + 1 < len(argv):
                opts[a] = argv[i + 1]
                i += 2
            else:
                raise FetchError(f"無法辨識的參數：{a}")
        try:
            start = parse_user_time(opts["--from"])
            end = parse_user_time(opts["--to"], is_end=True)
        except ValueError as e:
            raise FetchError(str(e))
        run_research_export(dest, xlsx, start, end, None, log=lines.append, offline=offline,
                            event=opts["--event"], group=opts["--group"], grade=opts["--grade"])
        lines.append("匯出完成")
    except FetchError as e:
        lines.append(f"✖ 匯出失敗：{e}")
        code = 1
    except Exception as e:  # 不互動模式也不得崩潰
        lines.append(f"✖ 匯出失敗：{type(e).__name__}: {e}")
        code = 1
    try:
        dest.mkdir(parents=True, exist_ok=True)
        (dest / RESEARCH_SUMMARY_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        code = 2
    if sys.stdout is not None:
        try:
            print("\n".join(lines))
        except (OSError, UnicodeEncodeError):
            pass
    return code


# ---------------------------------------------------------------- 視窗
def main() -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from tkinter.scrolledtext import ScrolledText

    root = tk.Tk()
    root.title(f"{APP_TITLE}  v{VERSION}")
    root.geometry("780x840")
    root.minsize(660, 740)
    f_norm = (FONT_NAME, 11)
    f_bold = (FONT_NAME, 12, "bold")
    style = ttk.Style()
    style.configure(".", font=f_norm)
    style.configure("Big.TButton", font=f_bold, padding=6)
    style.configure("TLabelframe.Label", font=f_bold, foreground="#065A82")

    cfg = load_config()
    dest_var = tk.StringVar(value=cfg.get("dest") or DEFAULT_DEST)
    token_var = tk.StringVar()  # 只在記憶體
    status_var = tk.StringVar()
    game_status_var = tk.StringVar()
    gw = cfg.get("game_window")
    gw = gw if isinstance(gw, int) and not isinstance(gw, bool) and 1 <= gw <= 720 else DEDUP_MINUTES_DEFAULT
    win_var = tk.StringVar(value=str(gw))
    from_var = tk.StringVar()
    to_var = tk.StringVar()
    def preset_text(code: str) -> str:
        return f"{code}{EVENT_SEP}{EVENT_PRESETS[code]}" if code in EVENT_PRESETS else code
    ev0 = cfg.get("event") if isinstance(cfg.get("event"), str) else ""
    event_var = tk.StringVar(value=preset_text(ev0) if ev0 and ev0 != EVENT_ALL else EVENT_ALL)
    q: queue.Queue = queue.Queue()

    frm = ttk.Frame(root, padding=12)
    frm.pack(fill="both", expand=True)
    frm.columnconfigure(1, weight=1)

    ttk.Label(frm, text="WebAR 回饋問卷（v2 四面向＋v1 舊回覆）：rlirdo/serpentine-webar / feedback/responses",
              font=f_bold).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
    ttk.Label(frm, text="目的資料夾").grid(row=1, column=0, sticky="w")
    ttk.Entry(frm, textvariable=dest_var, font=f_norm).grid(row=1, column=1, sticky="ew", padx=6)

    def browse():
        d = filedialog.askdirectory(initialdir=dest_var.get() or str(Path.home()))
        if d:
            dest_var.set(os.path.normpath(d))
            save_config(dest_var.get())
            refresh_count()

    ttk.Button(frm, text="瀏覽…", command=browse).grid(row=1, column=2)
    ttk.Label(frm, text="GitHub Token").grid(row=2, column=0, sticky="w", pady=6)
    ttk.Entry(frm, textvariable=token_var, show="●", font=f_norm).grid(row=2, column=1, sticky="ew", padx=6)
    ttk.Label(frm, text="（選填，不存檔）", foreground="#64748B").grid(row=2, column=2, sticky="w")

    bar = ttk.Frame(frm)
    bar.grid(row=3, column=0, columnspan=3, sticky="ew", pady=6)
    btn_dl = ttk.Button(bar, text="下載新問卷", style="Big.TButton")
    btn_dl.pack(side="left")
    btn_open = ttk.Button(bar, text="開啟資料夾", style="Big.TButton")
    btn_open.pack(side="left", padx=8)
    ttk.Label(bar, textvariable=status_var, font=f_bold, foreground="#065A82").pack(side="left", padx=12)
    ttk.Label(bar, textvariable=game_status_var, font=f_bold, foreground="#2E7D5B").pack(side="left")

    prog = ttk.Progressbar(frm, mode="determinate", value=0)
    prog.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(2, 6))
    logbox = ScrolledText(frm, height=12, font=(FONT_NAME, 10), state="disabled", wrap="word")
    logbox.grid(row=5, column=0, columnspan=3, sticky="nsew")
    frm.rowconfigure(5, weight=1)

    # ---- v7：下方改為兩個分頁（原遊戲前後測區塊原封不動放在第一頁；研究用前後測在第二頁）
    nb = ttk.Notebook(frm)
    nb.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(10, 0))
    tab_game = ttk.Frame(nb, padding=(0, 6, 0, 0))
    tab_res = ttk.Frame(nb, padding=(0, 6, 0, 0))
    tab_game.columnconfigure(0, weight=1)
    tab_res.columnconfigure(0, weight=1)
    nb.add(tab_game, text="  WebAR 遊戲前後測  ")
    nb.add(tab_res, text="  研究用前後測（遊戲班／對照班）  ")

    # ---- v3：WebAR 遊戲前後測
    gf = ttk.LabelFrame(tab_game, text="WebAR 遊戲前後測（feedback/game；舊遊戲 v1＋墨玉護衛隊／人工魚子醬 v2）", padding=10)
    gf.grid(row=0, column=0, sticky="ew")
    gf.columnconfigure(1, weight=1)
    gf.columnconfigure(3, weight=1)
    ttk.Label(gf, text="起").grid(row=0, column=0, sticky="w")
    ttk.Entry(gf, textvariable=from_var, font=f_norm, width=18).grid(row=0, column=1, sticky="ew", padx=6)
    ttk.Label(gf, text="迄").grid(row=0, column=2, sticky="w")
    ttk.Entry(gf, textvariable=to_var, font=f_norm, width=18).grid(row=0, column=3, sticky="ew", padx=6)

    def set_today():
        d = datetime.now().strftime("%Y-%m-%d")
        from_var.set(d + " 00:00")
        to_var.set(d + " 23:59")

    def clear_range():
        from_var.set("")
        to_var.set("")

    ttk.Button(gf, text="今天", command=set_today).grid(row=0, column=4, padx=(6, 0))
    ttk.Button(gf, text="全部清空", command=clear_range).grid(row=0, column=5, padx=(6, 0))
    ttk.Label(gf, text="格式 YYYY-MM-DD HH:MM（台北時間），留空＝不限；迄含該分鐘。",
              foreground="#64748B").grid(row=1, column=0, columnspan=6, sticky="w", pady=(4, 6))
    ttk.Label(gf, text="重複判定").grid(row=2, column=0, sticky="w")
    wrow = ttk.Frame(gf)
    wrow.grid(row=2, column=1, columnspan=5, sticky="w", padx=6)
    ttk.Spinbox(wrow, from_=1, to=720, increment=1, textvariable=win_var, width=6,
                font=f_norm).pack(side="left")
    ttk.Label(wrow, text="分鐘內，同一玩家代碼的第二筆前測／後測略過（只取第一次）",
              foreground="#64748B").pack(side="left", padx=6)
    ttk.Label(gf, text="活動").grid(row=3, column=0, sticky="w", pady=(6, 0))
    erow = ttk.Frame(gf)
    erow.grid(row=3, column=1, columnspan=5, sticky="w", padx=6, pady=(6, 0))
    ev_box = ttk.Combobox(erow, textvariable=event_var, width=40, font=f_norm,
                          values=[EVENT_ALL] + [preset_text(c) for c in EVENT_PRESETS])
    ev_box.pack(side="left")
    ttk.Label(erow, text="可下拉選或自行輸入活動代碼；「全部」＝不篩選",
              foreground="#64748B").pack(side="left", padx=6)

    def on_event_change(*_):
        # v5：選到有專屬資料夾的活動（人工魚子醬）時，若目的資料夾仍是預設或空白，自動建議（可再改）
        code = event_code(event_var.get())
        sug = next((v for k, v in EVENT_DEFAULT_DEST.items() if k.lower() == code.lower()), None)
        cur = os.path.normpath(dest_var.get().strip()) if dest_var.get().strip() else ""
        if sug and (not cur or cur == os.path.normpath(DEFAULT_DEST)):
            dest_var.set(sug)
            ui_log(f"活動 {code}：目的資料夾自動建議為 {sug}（可按「瀏覽…」更改）")
            refresh_count()

    ev_box.bind("<<ComboboxSelected>>", on_event_change)
    btn_game = ttk.Button(gf, text="下載並匯出 Excel…", style="Big.TButton")
    btn_game.grid(row=4, column=0, columnspan=6, sticky="w", pady=(8, 0))

    # ---- v7：研究用前後測（feedback/test，遊戲班 group=game／對照班 group=control）
    rf = ttk.LabelFrame(tab_res, text="研究用前後測（feedback/test；遊戲班研究模式＋對照班測驗頁，各 10 題）", padding=10)
    rf.grid(row=0, column=0, sticky="ew")
    rf.columnconfigure(1, weight=1)
    rf.columnconfigure(3, weight=1)
    rfrom_var, rto_var = tk.StringVar(), tk.StringVar()
    revent_var = tk.StringVar(value=EVENT_ALL)
    rgroup_var = tk.StringVar(value=EVENT_ALL)
    rgrade_var = tk.StringVar(value=EVENT_ALL)
    rdest_var = tk.StringVar(value=research_dest_from(cfg))
    research_status_var = tk.StringVar()
    ttk.Label(rf, text="起").grid(row=0, column=0, sticky="w")
    ttk.Entry(rf, textvariable=rfrom_var, font=f_norm, width=18).grid(row=0, column=1, sticky="ew", padx=6)
    ttk.Label(rf, text="迄").grid(row=0, column=2, sticky="w")
    ttk.Entry(rf, textvariable=rto_var, font=f_norm, width=18).grid(row=0, column=3, sticky="ew", padx=6)

    def r_today():
        d = datetime.now().strftime("%Y-%m-%d")
        rfrom_var.set(d + " 00:00")
        rto_var.set(d + " 23:59")

    ttk.Button(rf, text="今天", command=r_today).grid(row=0, column=4, padx=(6, 0))
    ttk.Button(rf, text="全部清空", command=lambda: (rfrom_var.set(""), rto_var.set(""))).grid(row=0, column=5, padx=(6, 0))
    ttk.Label(rf, text="依上傳時間篩選，格式同上（留空＝不限）。同一 sid 前測／後測重複上傳時留最早一筆。",
              foreground="#64748B").grid(row=1, column=0, columnspan=6, sticky="w", pady=(4, 6))
    ttk.Label(rf, text="活動").grid(row=2, column=0, sticky="w")
    rerow = ttk.Frame(rf)
    rerow.grid(row=2, column=1, columnspan=5, sticky="w", padx=6)
    ttk.Combobox(rerow, textvariable=revent_var, width=30, font=f_norm,
                 values=[EVENT_ALL] + [f"{c}{EVENT_SEP}{n}" for c, n in RESEARCH_EVENT_PRESETS.items()]
                 ).pack(side="left")
    ttk.Label(rerow, text="可自行輸入班級活動代碼；「全部」＝不篩選", foreground="#64748B").pack(side="left", padx=6)
    ttk.Label(rf, text="組別").grid(row=3, column=0, sticky="w", pady=(6, 0))
    rgrow = ttk.Frame(rf)
    rgrow.grid(row=3, column=1, columnspan=5, sticky="w", padx=6, pady=(6, 0))
    ttk.Combobox(rgrow, textvariable=rgroup_var, width=8, font=f_norm, state="readonly",
                 values=[EVENT_ALL, "遊戲班", "對照班"]).pack(side="left")
    ttk.Label(rgrow, text="版本").pack(side="left", padx=(14, 6))
    ttk.Combobox(rgrow, textvariable=rgrade_var, width=6, font=f_norm, state="readonly",
                 values=[EVENT_ALL, "國小", "國中"]).pack(side="left")
    # v7.1：研究專用目的資料夾（與上方研討會回饋問卷的目的資料夾分開；記在 config.json 的 research_dest）
    ttk.Label(rf, text="研究資料夾").grid(row=5, column=0, sticky="w", pady=(8, 0))
    rdrow = ttk.Frame(rf)
    rdrow.grid(row=5, column=1, columnspan=5, sticky="ew", padx=6, pady=(8, 0))
    rdrow.columnconfigure(0, weight=1)
    ttk.Entry(rdrow, textvariable=rdest_var, font=f_norm).grid(row=0, column=0, sticky="ew")

    def browse_research():
        d = filedialog.askdirectory(initialdir=rdest_var.get() or str(Path.home()))
        if d:
            rdest_var.set(os.path.normpath(d))
            save_research_dest(rdest_var.get())
            refresh_count()

    def open_research_dir():
        d = Path(rdest_var.get().strip() or DEFAULT_RESEARCH_DEST)
        try:
            d.mkdir(parents=True, exist_ok=True)
            os.startfile(str(d))
        except OSError as e:
            messagebox.showwarning(APP_TITLE, f"無法開啟資料夾：{e}")

    ttk.Button(rdrow, text="瀏覽…", command=browse_research).grid(row=0, column=1, padx=(6, 0))
    ttk.Button(rdrow, text="開啟", command=open_research_dir).grid(row=0, column=2, padx=(6, 0))
    ttk.Label(rf, text="前後測（test_json）、學生版課後問卷（json）、匯出的 Excel／CSV／摘要都放這裡；與上方回饋問卷資料夾分開。",
              foreground="#64748B").grid(row=6, column=0, columnspan=6, sticky="w", pady=(2, 0))
    rbrow = ttk.Frame(rf)
    rbrow.grid(row=7, column=0, columnspan=6, sticky="w", pady=(8, 0))
    btn_res = ttk.Button(rbrow, text="下載並匯出研究用 Excel…", style="Big.TButton")
    btn_res.pack(side="left")
    ttk.Label(rbrow, textvariable=research_status_var, font=f_bold, foreground="#2E7D5B").pack(side="left", padx=12)

    def ui_log(msg: str):
        line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
        logbox.configure(state="normal")
        logbox.insert("end", line + "\n")
        logbox.see("end")
        logbox.configure(state="disabled")
        return line

    def refresh_count():
        n = len(list((Path(dest_var.get()) / JSON_SUBDIR).glob("*.json"))) \
            if (Path(dest_var.get()) / JSON_SUBDIR).is_dir() else 0
        status_var.set(f"本機目前 {n} 筆")
        gdir = Path(dest_var.get()) / GAME_JSON_SUBDIR
        gn = len(list(gdir.glob("*.json"))) if gdir.is_dir() else 0
        game_status_var.set(f"遊戲紀錄本機 {gn} 筆")
        tdir = Path(rdest_var.get().strip() or DEFAULT_RESEARCH_DEST) / TEST_JSON_SUBDIR
        tn = len(list(tdir.glob("*.json"))) if tdir.is_dir() else 0
        research_status_var.set(f"研究資料本機 {tn} 筆" if tn else "研究資料本機 0 筆（尚無研究資料）")

    def worker(dest: Path, token: str):
        def log(m):
            q.put(("log", m))
        try:
            res = run_fetch(dest, token or None, log=log)
            q.put(("done", res))
        except FetchError as e:
            q.put(("error", str(e)))
        except Exception as e:  # 不得崩潰
            q.put(("error", f"發生未預期錯誤：{type(e).__name__}: {e}"))

    def game_worker(dest: Path, xlsx: Path, start, end, window, token: str, event: str):
        def log(m):
            q.put(("log", m))
        try:
            res = run_game_export(dest, xlsx, start, end, window, token or None, log=log, event=event)
            q.put(("game_done", res))
        except FetchError as e:
            q.put(("error", str(e)))
        except Exception as e:  # 不得崩潰
            q.put(("error", f"發生未預期錯誤：{type(e).__name__}: {e}"))

    def research_worker(dest: Path, xlsx: Path, start, end, token: str, event: str, group: str, grade: str):
        # v7.1：研究分頁的日誌與摘要檔寫到研究目的資料夾
        lines = [f"{APP_TITLE} v{VERSION}　{datetime.now():%Y-%m-%d %H:%M:%S}　研究用前後測匯出（視窗）"]

        def log(m):
            lines.append(m)
            q.put(("rlog", m))
        try:
            res = run_research_export(dest, xlsx, start, end, token or None, log=log, event=event,
                                      group=group, grade=grade)
            lines.append("匯出完成")
            q.put(("research_done", res))
        except FetchError as e:
            lines.append(f"✖ 匯出失敗：{e}")
            q.put(("rerror", str(e)))
        except Exception as e:  # 不得崩潰
            lines.append(f"✖ 匯出失敗：{type(e).__name__}: {e}")
            q.put(("rerror", f"發生未預期錯誤：{type(e).__name__}: {e}"))
        try:
            (dest / RESEARCH_SUMMARY_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError:
            pass

    def set_busy(busy: bool):
        st = "disabled" if busy else "normal"
        btn_dl.configure(state=st)
        btn_game.configure(state=st)
        btn_res.configure(state=st)
        if busy:
            prog.configure(mode="indeterminate")
            prog.start(12)

    def poll():
        try:
            while True:
                kind, payload = q.get_nowait()
                dest = Path(dest_var.get())
                rdest = Path(rdest_var.get().strip() or DEFAULT_RESEARCH_DEST)
                if kind == "log":
                    append_log_file(dest, ui_log(payload))
                    continue
                if kind == "rlog":
                    append_log_file(rdest, ui_log(payload))
                    continue
                if kind == "rerror":
                    dest = rdest
                prog.stop()
                prog.configure(mode="determinate", value=100 if kind in ("done", "game_done", "research_done") else 0)
                set_busy(False)
                if kind == "done":
                    total = payload["total"]
                    status_var.set(f"目前 {total} 筆（本次新增 {payload['new']} 筆）")
                    if payload["remote"] == 0:
                        append_log_file(dest, ui_log("目前 0 筆：GitHub 上尚無回覆。"))
                elif kind == "game_done":
                    refresh_count()
                    if payload.get("remote") == 0:
                        append_log_file(dest, ui_log("GitHub 上尚無遊戲紀錄（feedback/game 尚未建立）。"))
                    if messagebox.askyesno(APP_TITLE, "匯出完成：\n" + payload["path"]
                                           + f"\n\n保留 {payload['kept']} 筆、略過重複 {payload['dropped']} 筆、"
                                           f"玩家 {payload['players']} 人。\n\n要現在開啟 Excel 嗎？"):
                        try:
                            os.startfile(payload["path"])
                        except OSError as e:
                            messagebox.showwarning(APP_TITLE, f"無法開啟檔案：{e}")
                elif kind == "research_done":
                    refresh_count()
                    head = "尚無研究資料（GitHub 上還沒有 feedback/test）。已輸出空白格式的檔案：\n" \
                        if payload["local"] == 0 else "匯出完成：\n"
                    sst = payload.get("survey_stats")
                    stext = ("\n" + survey_count_text(sst) + "，" + tam_count_text(sst)
                             + "（只能做班級層級比較）") if sst else ""
                    if messagebox.askyesno(APP_TITLE, head + payload["path"]
                                           + f"\n\n學生 {payload['students']} 人（完成前後測 {payload['complete']} 人）、"
                                           f"略過重複 {payload['dropped']} 筆；" + stext
                                           + "\n分析用 CSV（國小、國中、課後問卷）已另存於同資料夾。"
                                           "\n\n要現在開啟 Excel 嗎？"):
                        try:
                            os.startfile(payload["path"])
                        except OSError as e:
                            messagebox.showwarning(APP_TITLE, f"無法開啟檔案：{e}")
                else:
                    append_log_file(dest, ui_log("✖ " + payload))
                    messagebox.showwarning(APP_TITLE, payload)
        except queue.Empty:
            pass
        root.after(150, poll)

    def on_download():
        d = dest_var.get().strip()
        if not d:
            messagebox.showinfo(APP_TITLE, "請先選擇目的資料夾。")
            return
        save_config(d)
        set_busy(True)
        threading.Thread(target=worker, args=(Path(d), token_var.get().strip()),
                         daemon=True).start()

    def on_game():
        d = dest_var.get().strip()
        if not d:
            messagebox.showinfo(APP_TITLE, "請先選擇目的資料夾。")
            return
        try:
            start = parse_user_time(from_var.get())
            end = parse_user_time(to_var.get(), is_end=True)
        except ValueError as e:
            messagebox.showwarning(APP_TITLE, str(e))
            return
        if start and end and start > end:
            messagebox.showwarning(APP_TITLE, "「起」時間晚於「迄」時間，請重新輸入。")
            return
        try:
            window = int(win_var.get().strip())
            if not 1 <= window <= 720:
                raise ValueError
        except ValueError:
            messagebox.showwarning(APP_TITLE, "重複判定請輸入 1–720 的整數分鐘。")
            return
        try:
            Path(d).mkdir(parents=True, exist_ok=True)
        except OSError as e:
            messagebox.showwarning(APP_TITLE, f"無法建立目的資料夾：{e}")
            return
        out = filedialog.asksaveasfilename(
            title="匯出遊戲前後測 Excel", initialdir=d,
            initialfile=f"遊戲前後測_{datetime.now():%Y%m%d-%H%M}.xlsx",
            defaultextension=".xlsx", filetypes=[("Excel 活頁簿", "*.xlsx")])
        if not out:
            return
        ev = event_code(event_var.get()) or EVENT_ALL
        save_config(d, window, ev)
        ui_log(f"遊戲前後測匯出：區間 {_range_text(start, end)}；活動 {ev}；重複判定 {window} 分鐘")
        set_busy(True)
        threading.Thread(target=game_worker,
                         args=(Path(d), Path(os.path.normpath(out)), start, end, window,
                               token_var.get().strip(), ev), daemon=True).start()

    def on_research():
        d = rdest_var.get().strip()                    # v7.1：研究專用目的資料夾
        if not d:
            messagebox.showinfo(APP_TITLE, "請先選擇研究資料夾。")
            return
        try:
            start = parse_user_time(rfrom_var.get())
            end = parse_user_time(rto_var.get(), is_end=True)
            grp = norm_group(rgroup_var.get())
            grd = norm_grade(rgrade_var.get())
        except ValueError as e:
            messagebox.showwarning(APP_TITLE, str(e))
            return
        if start and end and start > end:
            messagebox.showwarning(APP_TITLE, "「起」時間晚於「迄」時間，請重新輸入。")
            return
        try:
            Path(d).mkdir(parents=True, exist_ok=True)
        except OSError as e:
            messagebox.showwarning(APP_TITLE, f"無法建立目的資料夾：{e}")
            return
        out = filedialog.asksaveasfilename(
            title="匯出研究用前後測 Excel（另存分析用 CSV）", initialdir=d,
            initialfile=research_default_name(start, end),
            defaultextension=".xlsx", filetypes=[("Excel 活頁簿", "*.xlsx")])
        if not out:
            return
        ev = event_code(revent_var.get()) or EVENT_ALL
        save_research_dest(d)
        ui_log(f"研究用前後測匯出（研究資料夾 {d}）：區間 {_range_text(start, end)}；活動 {ev}；"
               f"組別 {GROUP_LABEL.get(grp, EVENT_ALL)}；版本 {GRADE_LABEL.get(grd, EVENT_ALL)}")
        set_busy(True)
        threading.Thread(target=research_worker,
                         args=(Path(d), Path(os.path.normpath(out)), start, end, token_var.get().strip(),
                               ev, grp, grd), daemon=True).start()

    def on_open():
        d = Path(dest_var.get())
        try:
            d.mkdir(parents=True, exist_ok=True)
            os.startfile(str(d))
        except OSError as e:
            messagebox.showwarning(APP_TITLE, f"無法開啟資料夾：{e}")

    btn_dl.configure(command=on_download)
    btn_open.configure(command=on_open)
    btn_game.configure(command=on_game)
    btn_res.configure(command=on_research)
    ui_log("研究用前後測（v7）：切到下方「研究用前後測」分頁，可依時間、活動、組別、版本篩選後匯出 Excel 與分析用 CSV。")
    ui_log("v7.1：研究分頁有自己的「研究資料夾」；匯出時一併下載學生版課後問卷（活動代碼 GAME-／CTRL-…），"
           "加「課後問卷」「課後問卷統計」工作表與課後問卷 CSV。")
    ui_log("v7.2：遊戲班課後問卷的科技接受度六題（PE1–PE3 易用性、PU1–PU3 有用性）一併匯出，"
           "統計表多「科技接受度（僅遊戲班作答）」區，CSV 多 pe1–pu3、peou_mean、pu_mean。")
    ui_log("按「下載新問卷」從 GitHub 撈取回覆；只下載本機沒有的新檔。")
    ui_log("遊戲前後測：設定起迄時間、重複判定分鐘數與活動後，按「下載並匯出 Excel…」。")
    ui_log("題庫與問卷正解依紀錄的活動自動切換（人工魚子醬 HL-STATION-2026-1127-CAVIAR 用晶球題庫；"
           "選人工魚子醬時一併納入 -SR 高階玩家）。")
    refresh_count()
    root.after(150, poll)
    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--aggregate":
        sys.exit(cli_aggregate(Path(sys.argv[2])))
    if len(sys.argv) >= 2 and sys.argv[1] == "--game-export":
        sys.exit(cli_game_export(sys.argv[2:]))
    if len(sys.argv) >= 2 and sys.argv[1] == "--research-export":
        sys.exit(cli_research_export(sys.argv[2:]))
    main()
