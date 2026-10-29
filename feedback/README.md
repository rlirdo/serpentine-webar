# WebAR 遊戲回饋問卷（feedback/）

第 36 屆環境教育學術暨實務交流國際研討會　壁報 A155-07 的玩後回饋問卷。
網址：<https://rlirdo.github.io/serpentine-webar/feedback/>

**目前版本：schema `webar-feedback-v2`（2026/10/29 改版）**——環境知識、環境態度、行動意向、科學探究
四面向，每面向 3 題選擇（必填）＋1 題簡答（選填），共 16 題；不蒐集身分、裝置與 email。

## 檔案

| 路徑 | 用途 |
|---|---|
| `index.html` | 問卷網頁（手機優先、單頁、不記名） |
| `config.js` | 中繼網址 `window.FEEDBACK_ENDPOINT`；空字串＝尚未啟用，改用 Email 備援（811554006@gms.ndhu.edu.tw） |
| `relay/Code.gs` | Google Apps Script 中繼：收 POST → 白名單驗證 → GitHub Contents API 寫入 `responses/` |
| `relay/設定說明_AppsScript與GitHubToken.md` | 建 token、部署 Apps Script、**v2 改版後重新部署**、測試、換 token 的逐步說明 |
| `responses/` | 每筆回覆一個 JSON：`YYYYMMDD-HHMMSS_<6碼>.json`（台北時間）；v1 與 v2 回覆並存 |
| `game/` | 遊戲前後測作答，每筆一個 JSON：`YYYYMMDD-HHMMSS_<pre\|post>_<6碼>.json`（2026/10/29 起） |

## 資料流程

```
問卷網頁 ──POST text/plain JSON──▶ Apps Script（doPost）──PUT Contents API──▶ feedback/responses/*.json
```

- GitHub token 只存在 Apps Script 的「指令碼屬性」`GITHUB_TOKEN`，**不在網頁、不在 repo**。
- 網頁用 `Content-Type: text/plain` 送出，避免 CORS preflight。
- 防灌水：隱藏 honeypot 欄位、必填檢查、送出鍵 5 秒內只接受一次；中繼端再做白名單欄位與選項檢查、字串截斷。
- 本機 localStorage 記「已填過」只做提醒，仍可再填一份。
- 中繼只接受目前的 schema；改版 Code.gs 後必須在 Apps Script **以「新版本」重新部署**（網址不變）。

## 回覆 JSON 格式（schema `webar-feedback-v2`，欄位順序固定）

```json
{
  "schema": "webar-feedback-v2",
  "submitted_at": "2026-10-31T10:21:05+08:00",
  "event": "SEET2026-A155-07",
  "k1": "A|B|C|D", "k2": "A|B|C|D", "k3": "A|B|C|D", "k_open": "字串（可空，≤300 字）",
  "a1": 1, "a2": 1, "a3": 1, "a_open": "",
  "i1": 1, "i2": 1, "i3": 1, "i_open": "",
  "s1": 1, "s2": 1, "s3": 1, "s_open": "",
  "ua": "瀏覽器 UA 截短 120 字"
}
```

| 題號 | 欄位 | 面向 | 題目 | 作答 |
|---|---|---|---|---|
| 1 | k1 | 環境知識 | 把墨玉（蛇紋石）磨成約 2–4 微米微米粉的最主要好處 | A–D |
| 2 | k2 | 環境知識 | DSW 中最適合補進蛇紋石晶格空位的離子 | A–D |
| 3 | k3 | 環境知識 | 配製反應液時最符合綠色化學的做法 | A–D |
| 4 | k_open | 環境知識 | 這個遊戲讓您學到的一個新知識 | 簡答（選填） |
| 5 | a1 | 環境態度 | 閒置石材也可能是值得再利用的資源 | 1–5 |
| 6 | a2 | 環境態度 | 認同優先用水、避免有毒溶劑與強酸的綠色化學 | 1–5 |
| 7 | a3 | 環境態度 | 花蓮在地資源值得珍惜與善加利用 | 1–5 |
| 8 | a_open | 環境態度 | 對閒置石材或在地資源的看法改變 | 簡答（選填） |
| 9 | i1 | 行動意向 | 願意做好垃圾分類與資源回收 | 1–5 |
| 10 | i2 | 行動意向 | 願意分類收集並妥善處理廢液、廢棄物 | 1–5 |
| 11 | i3 | 行動意向 | 願意分享在地資源再利用與綠色化學觀念 | 1–5 |
| 12 | i_open | 行動意向 | 想採取的環境行動 | 簡答（選填） |
| 13 | s1 | 科學探究 | 更理解工作假設需由實驗證據驗證 | 1–5 |
| 14 | s2 | 科學探究 | 對用儀器（FTIR）找證據更感興趣 | 1–5 |
| 15 | s3 | 科學探究 | 想進一步探究 Mg²⁺ 補進晶格這類問題 | 1–5 |
| 16 | s_open | 科學探究 | 最想用實驗弄清楚的一個問題 | 簡答（選填） |

量表 1–5：1 非常不同意、2 不同意、3 普通、4 同意、5 非常同意。完整題幹與選項見 `index.html` 的 `SECTIONS`。
知識題的正解表不放在本公開 repo，由主持人的撈取工具計分。
`submitted_at` 以 Apps Script 伺服器時間（Asia/Taipei）覆寫。

## 遊戲前後測作答（schema `webar-game-v1`，2026/10/29 新增）

遊戲本身（`ar.html`／`play.html`，程式在 `js/report.js`）在**前測做完**與**整局結束**時各送一筆到同一個中繼，
中繼寫入 `game/<YYYYMMDD-HHMMSS>_<pre|post>_<6碼>.json`。自動通關測試（`?autoplay=1`）不上傳。

```json
{
  "schema": "webar-game-v1", "submitted_at": "2026-10-31T10:21:05+08:00", "event": "SEET2026-A155-07",
  "pid": "匿名玩家代碼 12 碼（存在玩家裝置 localStorage；無痕模式每次新產生）",
  "sid": "本局代碼 12 碼（前測與後測相同）",
  "phase": "pre | post", "grade": "elem | junior", "mode": "ar | play", "client_time": "裝置時間 ISO",
  "pre":  [{"id": "E1", "facet": "知識", "pick": 0, "correct": true}, "…共 3 題"],
  "post": ["phase=post 時 5 題（同 3 題＋行動 1 題＋其他 1 題）；pre 時為 []"],
  "preScore": 2, "postSame3": 2, "postScore": 3,
  "stars": [3, 2, 3, 1, 3, 3, 2, 3], "totalStars": 20,
  "facets": {"知識": 100, "態度": 50, "行動": 75, "探究": 60},
  "commit": "小行動承諾（≤80 字）", "ua": "瀏覽器 UA 截短 120 字"
}
```

- `pick` 是題庫 `js/content.js` `BANK` 內的**原始選項索引**（0–3；正解一律索引 0，畫面上會洗牌）。
- 撈取工具以 `pid` 判斷重複：同一玩家代碼 30 分鐘內的第二筆前測／後測略過，只取第一次；超過 30 分鐘視為再玩一次。
- 不蒐集姓名、學號、學校、email；pid 是隨機代碼，無法回推身分。

## 舊版 v1（2026/10/22–10/28）

`responses/` 內 schema 為 `webar-feedback-v1` 的檔案保留不動，欄位為：
`role, role_other, teach_level, played, device, q1_clear…q6_use_in_class（1–5）, best_part, suggest, fit_level, contact_ok, contact（一律空字串）, ua`。
撈取工具會同時讀 v1 與 v2，彙整表以 v2 欄位為主並標示版本。

## 隱私

v2 不蒐集姓名、學號、學校、email、身分與裝置；只記錄作答、送出時間與截短的瀏覽器版本。
本 repo 為公開 repo，`responses/` 內容任何人都看得到。
