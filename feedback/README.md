# WebAR 遊戲回饋問卷（feedback/）

第 36 屆環境教育學術暨實務交流國際研討會　壁報 A155-07 的玩後回饋問卷。
網址：<https://rlirdo.github.io/serpentine-webar/feedback/>

**目前版本：schema `webar-feedback-v2`（2026/10/29 改版）**——環境知識、環境態度、行動意向、科學探究
四面向，每面向 3 題選擇（必填）＋1 題簡答（選填），共 16 題；不蒐集身分、裝置與 email。

## 檔案

| 路徑 | 用途 |
|---|---|
| `index.html` | 問卷網頁（手機優先、單頁、不記名） |
| `student.html` | 學生版課後問卷（研究用兩班；同 schema，靠 `event` 區分班別，見下方「學生版課後問卷」） |
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

## 研究用整份 10 題前後測（schema `webar-test-v1`，2026/11/25 新增；對照班＋遊戲班研究模式）

兩組共用 `js/study.js`（題目順序、洗牌、計分、態度題、上傳欄位、補傳佇列都一樣）：
- **對照班** `group=control`：`test/index.html`（下節）。`mode` 固定 `test`，不可帶星數。
- **遊戲班研究模式** `group=game`：`play.html?study=1&grade=elem|junior&event=活動代碼`（`ar.html` 同參數）。
  第一關前考 10 題、第八關後再考 10 題（作答時不顯示對錯與面向標籤），行動承諾後上傳 `phase=post`；
  `mode` 為 `ar|play`，後測另帶 `stars`（8 個 1–3 整數，必填）、`totalStars`（中繼重算）、`restarts`（闖關途中重新整理後從第 1 關重闖的次數）。
  研究模式**不會**另送 `webar-game-v1`。沒帶 `study=1` 時遊戲行為與 `webar-game-v1` 上傳完全不變。
- 兩組都寫入 `test/`。欄位順序：`schema, submitted_at, event, group, pid, sid, phase, grade, mode, client_time, pre, post,
  preScore, postScore, maxScore, stars, totalStars, restarts, commit, commitPick, ua`（對照班的 `stars` 為 `[]`、`totalStars`／`restarts` 為空字串）。

## 對照班只有測驗（schema `webar-test-v1`，2026/11/25 新增）

`test/index.html`（網址 `…/serpentine-webar/test/?grade=elem|junior&event=活動代碼`）給研究的對照班用：不玩遊戲，
課前、課後各做同一份**整份 10 題**（國小 E1–E10、國中 J1–J10，題目固定 1→10、選項洗牌、作答時不顯示對錯），
後測後選一項行動承諾（`js/content.js` 的 `ENDING.commits`）。前測做完送 `phase=pre`、全部做完送 `phase=post`；
上傳失敗留在手機 localStorage 佇列，下次開頁或回到線上時自動補傳。
中繼（`relay/Code.gs` v5）寫入 **`test/`**（不是 `game/`），檔名 `<YYYYMMDD-HHMMSS>_<pre|post>_<6碼>.json`，
所以撈取工具現有的遊戲彙整不會讀到。**中繼需重新部署為新版本才會收這個 schema。**

```json
{
  "schema": "webar-test-v1", "submitted_at": "2026-11-25T13:00:00+08:00", "event": "CTRL-TEST（或網址 event 參數）",
  "group": "control", "pid": "匿名代碼 12 碼（與遊戲共用 serpentineWebAR.pid）", "sid": "本次代碼 12 碼（前測與後測相同）",
  "phase": "pre | post", "grade": "elem | junior", "mode": "test", "client_time": "裝置時間 ISO",
  "pre":  [{"id": "E1", "facet": "知識", "pick": 0, "correct": true}, "…共 10 題，依題號排序；態度題 correct 為 null"],
  "post": ["phase=post 時同樣 10 題；pre 時為 []"],
  "preScore": 4, "postScore": 8, "maxScore": 8,
  "stars": [], "totalStars": "", "restarts": "",
  "commit": "行動承諾文字", "commitPick": 1, "ua": "瀏覽器 UA 截短 120 字"
}
```

- 組別：`schema`＝`webar-test-v1`、`group`＝`control`、`mode`＝`test` 三者都表示對照班；遊戲班仍是 `webar-game-v1`（`game/`）。
- 計分只算 8 題：態度題（國小 E3、E7；國中 J3、J8）`correct` 一律 `null`，中繼重算 `preScore`／`postScore`。
- `pick`、`commitPick` 都是原始索引（題目正解一律索引 0）。配對前後測用 `sid`（同一次作答）；`pid` 在「下一位同學」時會換新。

## 學生版課後問卷（`student.html`，2026/11/25 新增；研究用兩班）

網址：`https://rlirdo.github.io/serpentine-webar/feedback/student.html?event=活動代碼`

- 給研究的對照班與遊戲班在**後測之後**填，入口在對照班 `test/` 完成頁與遊戲班研究模式（`?study=1`）結果頁的
  〔📝 填課後問卷（約 3 分鐘）〕，按鈕會帶上該次測驗的活動代碼（例 `CTRL-E-20261201`、`GAME-E-20261201`），
  以固定名稱的另一個分頁開啟，原完成頁／結果頁的〔下一位同學〕流程不受影響。
- `event` 取自網址 `?event=`，只接受英數、底線、連字號、最多 40 字；沒帶或不合法時為 `STUDENT-TEST`。
- **沿用 schema `webar-feedback-v2` 與同樣 16 個欄位**，所以學生版回覆同樣寫入 `responses/`；
  **班別與學段靠 `event` 區分**（`CTRL-*`＝對照班、`GAME-*`＝遊戲班、`-E-`／`-J-`＝國小／國中；成人版固定 `SEET2026-A155-07`）。
- 題目四部分與欄位對應同上表，題幹改為「上完這堂課後…」並改寫成學生用語；知識題 k1–k3 的選項順序與正解和成人版相同。
- **TAM 科技接受度 6 題（2026/11/26 新增，只給遊戲班）**：共同 16 題之後多「五、對這個遊戲的看法」6 題（必填、題號 17–22、五點量表 1–5），
  改編自 Davis（1989），題目為草稿、待專家審查。對照班填問卷時還沒玩遊戲，不作答，所以兩班在共同 16 題的作答條件相同。

  | 欄位 | 構念 | 題目 |
  |---|---|---|
  | `pe1` | 知覺易用性 | 我覺得這個 WebAR 遊戲很容易操作。 |
  | `pe2` | 知覺易用性 | 我很快就學會怎麼玩這個遊戲。 |
  | `pe3` | 知覺易用性 | 遊戲裡的說明和提示我看得懂。 |
  | `pu1` | 知覺有用性 | 這個遊戲幫助我了解看不見的晶格和離子。 |
  | `pu2` | 知覺有用性 | 用這個遊戲學習，比只聽講解更容易懂。 |
  | `pu3` | 知覺有用性 | 我覺得這個遊戲對學習自然科學有幫助。 |

  - 是否顯示：網址參數 `group=game|control` 優先；沒帶時由 `event` 推斷（`GAME-` 開頭或 `STUDY-GAME` → 遊戲班；其餘含 `CTRL-*`、`CTRL-TEST`、`STUDENT-TEST` → 不顯示），不分大小寫。
    入口已自動帶上：遊戲班結果頁 `&group=game`、對照班完成頁 `&group=control`。
  - 遊戲班的 JSON 在 `s_open` 之後、`ua` 之前多 `pe1,pe2,pe3,pu1,pu2,pu3`（1–5 整數）；非遊戲班的 JSON 與改版前完全相同（沒有這 6 個鍵）。
  - **需要中繼 v6**（`relay/Code.gs`，重新部署為新版本）。v5 的白名單會把這 6 欄靜靜丟掉，其餘 16 題照常寫入。
    v6 規則：6 欄都沒給＝與 v5 相同；給了任何一欄就 6 欄都必須是 1–5 整數，否則整筆回錯誤。
- 不蒐集姓名、班級、座號、學校、email；**沒有 Email 備援**。上傳失敗時作答先存在手機 localStorage
  （`serpentineWebAR.studentFeedback.pending.v1`），畫面提供〔再傳一次〕，下次開頁或回到線上時也會自動補傳。
- 共用手機：送出成功後按〔下一位同學填寫〕清空表單，活動代碼與班別（group）不變；不顯示「已填過」提示。

## 舊版 v1（2026/10/22–10/28）

`responses/` 內 schema 為 `webar-feedback-v1` 的檔案保留不動，欄位為：
`role, role_other, teach_level, played, device, q1_clear…q6_use_in_class（1–5）, best_part, suggest, fit_level, contact_ok, contact（一律空字串）, ua`。
撈取工具會同時讀 v1 與 v2，彙整表以 v2 欄位為主並標示版本。

## 隱私

v2 不蒐集姓名、學號、學校、email、身分與裝置；只記錄作答、送出時間與截短的瀏覽器版本。
本 repo 為公開 repo，`responses/` 內容任何人都看得到。
