# WebAR 遊戲回饋問卷（feedback/）

第 36 屆環境教育學術暨實務交流國際研討會　壁報 A155-07 的玩後回饋問卷。
網址：<https://rlirdo.github.io/serpentine-webar/feedback/>

## 檔案

| 路徑 | 用途 |
|---|---|
| `index.html` | 問卷網頁（手機優先、單頁、不記名） |
| `config.js` | 中繼網址 `window.FEEDBACK_ENDPOINT`；空字串＝尚未啟用，改用 Email 備援（811554006@gms.ndhu.edu.tw） |
| `relay/Code.gs` | Google Apps Script 中繼：收 POST → 驗證 → GitHub Contents API 寫入 `responses/` |
| `relay/設定說明_AppsScript與GitHubToken.md` | 建 token、部署 Apps Script、填網址、測試、換 token 的逐步說明 |
| `responses/` | 每筆回覆一個 JSON：`YYYYMMDD-HHMMSS_<6碼>.json`（台北時間） |

## 資料流程

```
問卷網頁 ──POST text/plain JSON──▶ Apps Script（doPost）──PUT Contents API──▶ feedback/responses/*.json
                                       └─（選用）append 一列到 Google Sheet
```

- GitHub token 只存在 Apps Script 的「指令碼屬性」`GITHUB_TOKEN`，**不在網頁、不在 repo**。
- 網頁用 `Content-Type: text/plain` 送出，避免 CORS preflight。
- 防灌水：隱藏 honeypot 欄位、所有題目必填檢查、送出鍵 5 秒內只接受一次；中繼端再做白名單欄位與選項檢查、字串截斷。
- 本機 localStorage 記「已填過」只做提醒，仍可再填一份。

## 回覆 JSON 格式（schema `webar-feedback-v1`，欄位順序固定）

```json
{
  "schema": "webar-feedback-v1",
  "submitted_at": "2026-10-31T10:21:05+08:00",
  "event": "SEET2026-A155-07",
  "role": "國小教師|國中教師|高中教師|大專教師|研究生|大學生|其他",
  "role_other": "",
  "teach_level": "國小|國中|高中|大專|不適用",
  "played": "完整玩完|玩了一部分|只看示範",
  "device": "iPhone|Android|平板|電腦|其他",
  "q1_clear": 1, "q2_fun": 1, "q3_easy": 1, "q4_mechanism": 1, "q5_feedback_useful": 1, "q6_use_in_class": 1,
  "best_part": "字串",
  "suggest": "字串",
  "fit_level": "國小高年級|國中|高中|皆可|皆不適合",
  "contact_ok": "願意|不願意",
  "contact": "選填 email（願意時才有）",
  "ua": "瀏覽器 UA 截短 120 字"
}
```

六題 1–5 分（1 非常不同意 → 5 非常同意）：

| 欄位 | 題目 |
|---|---|
| q1_clear | 遊戲說明清楚易懂 |
| q2_fun | 遊戲有趣 |
| q3_easy | AR 操作容易 |
| q4_mechanism | 透過「把 Mg²⁺ 補進晶格」，我更理解離子交換機制 |
| q5_feedback_useful | 前後測與即時回饋對教學有幫助 |
| q6_use_in_class | 我願意在自己的課堂試用 |

`submitted_at` 以 Apps Script 伺服器時間（Asia/Taipei）覆寫。

## 隱私

不蒐集姓名、學號、學校名稱。Email 為選填，只在填答者選「願意」時記錄，用途僅限後續教學包試用邀請。
注意：本 repo 為公開 repo，`responses/` 內容任何人都看得到；若在意 Email 公開，可在活動後將含 Email 的回覆移出 repo。
