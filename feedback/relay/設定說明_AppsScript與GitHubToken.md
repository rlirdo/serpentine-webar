# 回饋問卷中繼設定說明（Apps Script ＋ GitHub Token）

> ⚠️ **最重要的一句：token 不要貼給任何人，包含 Claude。**
> token 只貼在兩個地方：GitHub 產生它的那一頁（看一次就關掉）、Apps Script 的「指令碼屬性」。
> 不要貼進對話、Email、LINE、任何檔案或 repo。

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
   | `SHEET_ID`（選填） | 若要同步一份 Google 試算表：新建試算表，網址 `https://docs.google.com/spreadsheets/d/<這一段>/edit` 中間那段就是 ID；不需要就不要加這一列 |
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
   `{"ok":true,"service":"webar-feedback-relay","schema":"webar-feedback-v1","token_set":true}`。
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
   commit 訊息為 `feedback: YYYYMMDD-HHMMSS_xxxxxx`。
4. 測試檔可以在 GitHub 網頁上刪掉（點檔案 → 右上 `…` → **Delete file**），或保留並在分析時排除。

送出失敗時看哪裡：Apps Script 編輯器左側 **執行作業**（列表圖示）→ 點最近一筆 `doPost` 看錯誤訊息。
常見原因：
| 訊息 | 處理 |
|---|---|
| `GitHub 寫入失敗（401）` | token 貼錯或過期 → 重做步驟 1、2 |
| `GitHub 寫入失敗（403）` 或 `（404）` | token 沒勾 serpentine-webar，或 Contents 不是 Read and write |
| `中繼尚未設定 GITHUB_TOKEN` | 屬性名稱拼錯 |
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
