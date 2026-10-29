# 回饋問卷中繼設定說明（Apps Script ＋ GitHub Token）

> ⚠️ **最重要的一句：token 不要貼給任何人，包含 Claude。**
> token 只貼在兩個地方：GitHub 產生它的那一頁（看一次就關掉）、Apps Script 的「指令碼屬性」。
> 不要貼進對話、Email、LINE、任何檔案或 repo。

## ★ 2026/10/29 v2 改版後必做：重新部署為「新版本」

問卷已改為 schema `webar-feedback-v2`（環境知識、環境態度、行動意向、科學探究四面向 × 各 3 題選擇＋1 題簡答，
不再蒐集身分、裝置與 email）。中繼的白名單（`SCHEMA`、欄位檢查）寫在 `Code.gs` 裡，
**Apps Script 上還是舊版 v1 時，新問卷送出會被擋下（回應「schema 不符」）**，所以一定要重新部署：

1. 開啟 <https://script.google.com/> → 專案 `WebAR回饋問卷中繼`。
2. 編輯器內 `Code.gs` 全選（Ctrl+A）刪除 → 貼上本 repo 新版 `feedback/relay/Code.gs` 全文 → 儲存（Ctrl+S）。
3. 右上 **部署** → **管理部署作業** → 選原本那個網頁應用程式 → 右上 **鉛筆（編輯）**。
4. 「版本」下拉選 **新版本**（說明可填 `v2 2026/10/29`）→ **部署**。
   **不要**按「新增部署作業」，否則 `/exec` 網址會改變，`config.js` 就得跟著改。
5. 檢查：瀏覽器打開原本的 `/exec` 網址，應看到 `"schema":"webar-feedback-v2"` 與 `"token_set":true`。
6. 指令碼屬性 `GITHUB_TOKEN` 不用動；`SHEET_ID` v2 已不使用，可留可刪。

> 以下步驟 1–6 為 v1 首次建置時的完整說明（token、部署、測試、換 token），v2 沿用同一個專案與網址。
> 其中「步驟 1.5 私人試算表／email」與步驟 5 的 email 測試在 v2 已不適用。

---

整體流程：問卷網頁 → 送到你的 Apps Script 網頁應用程式 → Apps Script 用 token 把一筆 JSON 寫進
`rlirdo/serpentine-webar` 的 `feedback/responses/`。網頁本身完全不知道 token。

預計時間：約 15 分鐘。需要：GitHub 帳號 rlirdo、Google 帳號（建議用 gms.ndhu.edu.tw 或常用 Gmail）。

---

## 步驟 1　建立 GitHub fine-grained token（只開最小權限）

1. 用瀏覽器登入 GitHub（rlirdo）。
2. 右上角大頭貼 → **Settings**。
3. 左側選單拉到最下面 → **Developer settings**。
4. 左側 **Personal access tokens** → **Fine-grained tokens** → 右上綠色按鈕 **Generate new token**。
   （畫面若要求再輸入一次密碼或驗證碼，請自己輸入。）
5. 填寫表單：
   | 欄位 | 填什麼 |
   |---|---|
   | Token name | `webar-feedback-relay` |
   | Description（選填） | `SEET 壁報回饋問卷中繼，只寫 feedback/responses` |
   | Resource owner | `rlirdo` |
   | Expiration | **90 days**（下拉選 90 days） |
   | Repository access | 選 **Only select repositories** → 下拉勾選 **serpentine-webar**（只勾這一個） |
6. 往下到 **Permissions** → **Repository permissions** → 找到 **Contents** → 右邊下拉改成 **Read and write**。
   - 其他權限一律維持 **No access**。（GitHub 會自動把 **Metadata: Read-only** 設為必選，這是正常的。）
7. 最下方按 **Generate token**。
8. 畫面出現一串 `github_pat_` 開頭的文字 → 按旁邊的複製圖示。
   **這串只會顯示這一次**。先不要關分頁，直接進行步驟 2，把它貼到 Apps Script。

## 步驟 1.5　建立私人 Google 試算表並取得 ID（要收 email 就必須做）

> 為了隱私，填答者留下的 email **不會**寫進公開的 GitHub repo，只會寫進這份私人試算表。
> 沒有設定 `SHEET_ID` 的話，email 會被直接丟棄（問卷其他內容照常存到 GitHub），填答者會看到「目前未啟用 email 收集」。

1. 開新分頁到 <https://sheets.google.com/> → 左上 **空白試算表**（＋）。
2. 左上「未命名的試算表」改名為 `WebAR回饋問卷_私人_含email`。
3. 看瀏覽器網址列，形如 `https://docs.google.com/spreadsheets/d/1AbC…xyz/edit#gid=0`，
   `/d/` 和 `/edit` 中間那一長串（例：`1AbC…xyz`）就是 **試算表 ID** → 選取並複製，步驟 2 會用到。
4. 右上 **共用** → 確認「一般存取權」是 **限制**（只有你自己能開）→ 不要加任何人 → 完成。
   **不要**改成「知道連結的任何人」。
5. 試算表內容不用動；第一筆回覆進來時程式會自動寫標題列（第一欄 `file` 是對應的 GitHub JSON 檔名）。
   之後請用**同一個 Google 帳號**做步驟 2、3，Apps Script 才有權限寫這份試算表。

## 步驟 2　建立 Apps Script 專案並放入 token

1. 開新分頁到 <https://script.google.com/> → 左上 **新專案**。
2. 左上「未命名的專案」點一下 → 改名為 `WebAR回饋問卷中繼` → **重新命名**。
3. 編輯器裡預設有 `function myFunction() {}`：全選（Ctrl+A）刪掉。
4. 打開本 repo 的 `feedback/relay/Code.gs`（GitHub 網頁上點檔名 → 右上 **Copy raw file** 圖示），
   貼到編輯器 → 按上方磁碟圖示 **儲存專案**（或 Ctrl+S）。
5. 左側齒輪 **專案設定** → 拉到最下方 **指令碼屬性** → **新增指令碼屬性**：
   | 屬性 | 值 |
   |---|---|
   | `GITHUB_TOKEN` | 貼上步驟 1 複製的 `github_pat_…` |
   | `SHEET_ID`（要收 email 就必須設定） | 貼上步驟 1.5 複製的試算表 ID。不設定＝email 一律丟棄 |
6. 按 **儲存指令碼屬性**。
7. 回到 GitHub 那個顯示 token 的分頁 → 可以關掉了。之後不需要再看到這串 token。

## 步驟 3　部署成網頁應用程式

1. 回到編輯器（左側 `< >` 圖示）→ 右上藍色 **部署** → **新增部署作業**。
2. 「選取類型」旁的齒輪 → 勾 **網頁應用程式**。
3. 設定：
   | 欄位 | 選什麼 |
   |---|---|
   | 說明 | `v1` |
   | 執行身分 | **我（你的 Google 帳號）** |
   | 具有存取權的使用者 | **所有人** |
4. 按 **部署**。
5. 第一次會跳 **授權存取權** → 選你的 Google 帳號 →
   若出現「Google 尚未驗證這個應用程式」：點左下 **進階** → **前往 WebAR回饋問卷中繼（不安全）** → **允許**。
   （這是你自己寫的腳本，要求的權限是「連線到外部服務」與「試算表」，用來呼叫 GitHub 與寫試算表。）
6. 出現「網頁應用程式」網址，形如 `https://script.google.com/macros/s/AKfycb…/exec` → 按 **複製**。
7. 檢查：把這個網址貼到瀏覽器網址列打開，應該看到
   `{"ok":true,"service":"webar-feedback-relay","schema":"webar-feedback-v2","token_set":true}`（v1 時期為 `webar-feedback-v1`）。
   若 `token_set` 是 `false`，回到步驟 2 檢查屬性名稱是否完全是 `GITHUB_TOKEN`。

> 這個 `/exec` 網址**不是秘密**（它會公開放在網頁裡），可以貼給 Claude 代改設定檔。

## 步驟 4　把網址貼到 `feedback/config.js` 並 push

`feedback/config.js` 目前是：

```js
window.FEEDBACK_ENDPOINT = "";
```

改成（換成你的網址）：

```js
window.FEEDBACK_ENDPOINT = "https://script.google.com/macros/s/AKfycb…/exec";
```

做法擇一：
- **請 Claude 代改**：把 `/exec` 網址貼給 Claude，說「把回饋問卷網址改成這個並 push」。Claude 只改這一行。
- **自己在 GitHub 網頁改**：repo → `feedback/config.js` → 右上鉛筆 → 改好 → **Commit changes**。

約 1–3 分鐘後 GitHub Pages 更新完成。

## 步驟 5　測試一筆

1. 手機或電腦打開 <https://rlirdo.github.io/serpentine-webar/feedback/>（若還看到「回饋系統設定中」黃框，按重新整理或等 1–2 分鐘）。
2. 填一份測試問卷（建議「建議」欄寫「測試」）→ **送出回饋** → 應看到「感謝您的回饋！」。
3. 到 GitHub repo → `feedback/responses/` → 應該多一個 `YYYYMMDD-HHMMSS_xxxxxx.json`，
   commit 訊息為 `feedback: YYYYMMDD-HHMMSS_xxxxxx`。打開它確認 `"contact": ""`（email 不會出現在 repo）。
4. 再測一份「願意」並填自己的 email：
   - 有設 `SHEET_ID`：私人試算表多一列，`contact` 欄有 email；感謝畫面**沒有**黃色提醒。
   - 沒設 `SHEET_ID`：感謝畫面出現「目前未啟用 email 收集」，email 沒被保存。
5. 測試檔可以在 GitHub 網頁上刪掉（點檔案 → 右上 `…` → **Delete file**），或保留並在分析時排除。

送出失敗時看哪裡：Apps Script 編輯器左側 **執行作業**（列表圖示）→ 點最近一筆 `doPost` 看錯誤訊息。
常見原因：
| 訊息 | 處理 |
|---|---|
| `GitHub 寫入失敗（401）` | token 貼錯或過期 → 重做步驟 1、2 |
| `GitHub 寫入失敗（403）` 或 `（404）` | token 沒勾 serpentine-webar，或 Contents 不是 Read and write |
| `中繼尚未設定 GITHUB_TOKEN` | 屬性名稱拼錯 |
| 有填 email 卻出現「目前未啟用 email 收集」 | `SHEET_ID` 沒設、ID 貼錯，或試算表不是用部署 Apps Script 的同一個帳號建立 |
| 網頁顯示「送出失敗（Failed to fetch）」 | 步驟 3 存取權不是「所有人」，或 config.js 網址貼錯（要以 `/exec` 結尾） |

## 步驟 6　到期前更換 token（每 90 天）

1. GitHub 到期前 7 天會寄信提醒。
2. 依步驟 1 再產生一把新 token（或在原 token 頁按 **Regenerate token**）。
3. Apps Script → **專案設定** → **指令碼屬性** → `GITHUB_TOKEN` → **編輯** → 貼上新值 → 儲存。
4. **不需要重新部署**，`/exec` 網址不變，config.js 也不用改。
5. 回 GitHub 把舊 token 刪除（Fine-grained tokens 列表 → 舊的 → **Delete**）。

## 修改 Code.gs 之後

若之後改了 Code.gs，要 **部署 → 管理部署作業 → 鉛筆（編輯）→ 版本選「新版本」→ 部署**，
這樣網址才會維持不變。若誤按「新增部署作業」會得到新網址，就要重做步驟 4。

## 研討會結束後

活動結束（例如 2026/11 底）若不再收問卷：
- Apps Script → **部署 → 管理部署作業 → 封存**，或
- 直接到 GitHub 刪除 token。網頁會顯示送出失敗並提供 Email 備援。
