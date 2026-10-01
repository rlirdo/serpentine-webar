# 自我測試報告（階段一）

- 測試日期：2026/10/01
- 環境：Windows 11、Python 3.13、Google Chrome（headless=new，`--use-angle=swiftshader` 軟體 WebGL）、websocket-client 1.8.0（CDP）
- 函式庫：three.js 0.160.1、mind-ar 1.2.5（image-tracking three 版），版本相容說明見 `vendor/README.md`
- 所有指令都在 repo 根目錄執行，並設 `PYTHONUTF8=1`。本機伺服器只綁 127.0.0.1（`tools/devserver.py`）。
- 原始截圖（PNG）留在本機 `tools/shots/`，**不進 git**；repo 只收縮圖總表 `tools/shots/sheets/*.jpg`。重跑下列指令就能重新產生。

## 1. `.mind` 編譯 — 通過

```
PYTHONUTF8=1 python tools/compile_mind.py
```
- 流程：`tools/devserver.py`（http.server）→ headless Chrome 開 `tools/compile.html` → 用 `vendor/mindar/mindar-image.prod.js` 的 `Compiler.compileImageTargets()` 編譯 `assets/target.png`（1200×1200）→ `exportData()` → 以 `fetch POST /__save?path=assets/targets.mind` 回存。
- 結果：`assets/targets.mind` 共 929,767 bytes，編譯約 4–5 秒，進度回報 4% → 100%，事件為 `done`。
- 任務卡重新產生：`python tools/make_target.py [石料照片路徑]`。石料照片挑選無人物、無車牌、無門牌的石面特寫，裁切並縮圖成 `assets/serpentine_closeup.jpg`，已清掉 EXIF。

## 2. AR 假相機自我測試 — 通過（實際取得 targetFound）

```
PYTHONUTF8=1 python tools/selftest_ar.py
```
- 假影片：`tools/out/fake_cam.y4m`（640×480、10 fps、18 秒、YUV420；放在 .gitignore 內）。任務卡經透視變形合成到木紋桌面上，四角座標為 (150,52)(502,74)(544,440)(108,418)，**卡片約佔畫面 47%**，每幀另加 ±2 px 手持晃動。
  - 0–7 秒：有卡片
  - 7–11 秒：卡片移出畫面（只剩桌面）
  - 11–18 秒：卡片回到畫面
- Chrome 參數：`--use-fake-device-for-media-stream --use-fake-ui-for-media-stream --use-file-for-fake-video-capture=tools/out/fake_cam.y4m`，開啟 `ar.html?selftest=1`。
- 頁面回報（POST /__report）的實測結果，取自最後一輪：

| 事件 | 頁面時間 | 內容 |
|---|---|---|
| started | 1.7 s | video 640×480 |
| **targetFound** | **2.0 s** | 已完成首幀渲染後才回報（等兩幀）；mode=track，holderVisible=true，stage 投影到 NDC (0.02, 0.06)，位於畫面中央 |
| targetLost | 7.3 s | 卡片移出 |
| **floatMode**（懸浮模式） | 8.2 s | 遺失超過 0.5 s 後，stage 改掛到相機前方；NDC (-0.40, -0.08) 在可視範圍內（位置偏左，避開右側對話框）；HUD 顯示「懸浮模式」提示 |
| **reattached**（重新貼回卡片） | 11.9 s | mode=track，NDC (0.03, 0.05) |

- 頁面例外：0 筆。
- 截圖（已逐張看過）：`tools/shots/ar_01_targetFound.png`、`ar_02_targetLost.png`（正在過渡到懸浮位置）、`ar_03_floatMode.png`、`ar_04_reattached.png`、`ar_05_after.png`。總表：`tools/shots/sheets/ar_overview.jpg`。
- 看圖確認：小晶貼在卡片上方，懸浮時改到畫面左側，不被對話框遮住，提示文字完整；每張右下都有「NDHU自資系游豐兆製作」。
- 結果檔：`tools/out/selftest_ar.json`

## 3. 自動通關測試 — 通過（兩種規定視窗，加測手機橫向）

```
PYTHONUTF8=1 python tools/autoplay_test.py all        # 手機直向 390×844（觸控模擬）＋桌機 1280×720，國小版
PYTHONUTF8=1 python tools/autoplay_test.py landscape  # 加測：手機橫向 844×390，國中版
```
- 做法：開 `play.html?autoplay=1`。遊戲在每個等待輸入的時刻登記一個動作（`hud.setAP`），測試腳本透過 CDP 呼叫 `window.__ap.step()`，逐步觸發和真人相同的事件：DOM 按鈕 `click()`、按住鍵用 `pointerdown`／`pointerup`、3D 物件先把座標投影到螢幕再走同一條 raycast 點擊路徑。
- 每個狀態都用 CDP `Page.captureScreenshot` 截圖，並呼叫 `__ap.check()` 檢查：製作者字樣存在、內容正確、在視窗內、z-index 為 2147483647、可見範圍不與任何按鈕重疊；對話文字、按鈕、題目、選項、量表標籤沒有超出視窗或被裁切。
- 刻意走的錯誤路徑（用來驗證回饋）：前測前 2 題答錯、第 3 題答對；第 3 關先選「有機溶劑」；第 5 關先點 Ca²⁺；第 6 關先選「倒進水槽」；第 7 關先選「200 °C」。後測全對。

| 視窗 | 截圖張數 | 抵達結果頁 | console error | 製作者字樣問題 | 出界／裁切 | 耗時 |
|---|---|---|---|---|---|---|
| 手機直向 390×844 | **81** | 是 | 0 | 0 | 0 | 115 s |
| 桌機 1280×720 | **81** | 是 | 0 | 0 | 0 | 136 s |
| 手機橫向 844×390（加測，國中版） | 81 | 是 | 0 | 0 | 0 | 112 s |

- 流程涵蓋：開場 4 句 → 選年級 → 前測說明 → 前測 3 題 → 第 1–8 關（每關有開場、互動中各步、完成星等＋環境小語）→ 後測說明 → 後測 5 題（含答後詳解）→ 行動承諾 → 結果頁（上半部＋捲到底）。
- 結果頁實測：前測 1/3 → 後測同題 3/3，後測全部 5/5，四面向長條、證書與「再玩一次」「給老師看」都正常顯示。localStorage 寫入一筆紀錄（見 `tools/out/autoplay_*.json` 的 `saved_record`）。
- 截圖：`tools/shots/mobile_01_intro-1.png` … `mobile_81_result-bottom.png`、`desktop_01…81`、`landscape_01…81`。總表：`tools/shots/sheets/{mobile,desktop,landscape}_overview.jpg`。
- **逐張看圖後修正的問題**（修完已重跑全部測試，上表為最後一輪結果）：
  1. 3D 文字貼圖的寬高比被 popIn 動畫改成 1:1，標籤被壓扁、無法閱讀 → 縮放改為以原始比例為基準。
  2. 手機上 3D 文字太小 → 標籤整體放大 1.4 倍，光譜圖改為 0.84×0.525 單位、字級加大。
  3. 遠紅外波紋太大，蓋住第 8 關光譜圖 → 縮小半徑並降低透明度。
  4. 第 1 關的「粗粉」原本用圓錐表示，看起來像葉子 → 改成淺色粉堆並加標籤。
  5. 第 4 關的 Fe³⁺ 錨定後在第 5 關消失 → 錨定後改掛到晶格上，第 5 關仍看得到。
  6. 第 5 關滴管與標籤貼近頂部進度條 → 位置下移。
  7. 結果頁「給老師看」按鈕捲動時與右下製作者字樣重疊 → 對話框底部留出字樣高度。
  8. 桌機上 3D 場景偏小，且被置中的對話框蓋住燒瓶 → 寬螢幕與矮橫向螢幕改把對話框放右側，3D 場景放進左側可用區域（`js/layout.js`，play 與 AR 懸浮模式共用）。
  9. 數個 HUD 小字原本只有 13–15 px → 全部提高到 16 px 以上（例外：製作者字樣維持 13 px，符合規格「≥12 px」）。

### 一般頁面（附帶檢查）
```
PYTHONUTF8=1 python tools/pages_shots.py
```
- 檢查 `index.html`、`card.html`、`teacher.html`（預先寫入一筆示範紀錄），各在 390×844 與 1280×720 截圖：製作者字樣全部存在，position 為 fixed、z-index 最高，無水平出界，頁面例外 0。截圖：`tools/shots/page_*.png`，總表 `tools/shots/sheets/page_overview.jpg`。
- 任務卡 PNG 右下、列印 PDF（`assets/target_print.pdf`）右下都有製作者字樣。PDF 預覽圖已人工看過。

## 4. 全文檢索 — 通過

```
PYTHONUTF8=1 python tools/grep_check.py
```
- 檢查範圍：30 個文字檔，略過 `vendor/`、`tools/out/`、`tools/shots/`、`.git/`。
- 檢查項目：引擎名稱、舊稱呼、廠商名、人名稱呼、原料來源的禁用敘述、身體功效宣稱字眼，以及所有 http(s) 網址（只允許部署網址 `https://rlirdo.github.io/serpentine-webar/` 和本機 127.0.0.1／localhost）。
- 結果：0 筆命中。禁用詞清單在腳本內以 Unicode 碼位存放，避免腳本本身被自己檢出。
- 頁面完全不載入外部資源：three、MindAR、es-module-shims 都放在 `vendor/`；字型用系統字型；音效用 WebAudio 即時合成。

## 已知限制（未驗證或無法在本機驗證）
- 尚未在 iOS Safari、Android Chrome 實機上測試相機、觸控與效能。headless 用的是 SwiftShader 軟體繪圖，GPU 差異與實際幀率未測。
- AR 測試只用一種合成影片（固定透視、室內均勻光線）。真實紙卡在反光、低光、小角度下的辨識率要靠實機驗證。
- iOS 15–16.3 不支援 importmap，已加入 es-module-shims（polyfill），但未經實機驗證。
- 音效（WebAudio）在 headless 只確認沒有錯誤，無法聽實際聲音。
- QR 碼指向階段二才會部署的 `https://rlirdo.github.io/serpentine-webar/`，部署前掃描會打不開。
- `assets/target.png` 約 2.2 MB（為了保留追蹤特徵點，沒有壓縮），手機首次載入會稍慢。

---

# 自我測試報告（階段二：GitHub Pages 部署與 exe 啟動器）

- 測試日期：2026/10/01；環境同階段一（Windows 11、Python 3.13、Chrome headless=new＋SwiftShader）。
- 測試腳本已改成可指定網址：`tools/autoplay_test.py [視窗] --base URL --tag 名稱`、`tools/selftest_ar.py --base URL --tag 名稱`。
  - 指定 `--base` 時不起本機 devserver；AR 測試改用 CDP `Fetch` 攔截頁面送出的 `/__report`（線上與 exe 伺服器都沒有這個端點），頁面程式不需修改。
  - 通關測試另以 CDP `Network.requestWillBeSent` 記錄頁面發出的每一個請求，列出 base 以外的外部請求。

## 5. 線上部署（https://rlirdo.github.io/serpentine-webar/）— 通過

- 公開 repo：<https://github.com/rlirdo/serpentine-webar>。GitHub Pages 的來源設為 main 分支根目錄，強制 HTTPS。
- 推送後約 46 秒，首頁回應 200。以 HTTPS 逐一請求 21 個主要檔案，全部 200，類型如下：
  - html：`text/html`
  - js：`application/javascript`
  - `assets/targets.mind`（929,767 bytes）：`application/octet-stream`
  - vendor 內 three／MindAR／es-module-shims 都取得成功
- **線上自動通關**：`play.html?autoplay=1`，桌機 1280×720，國小版。
  - 結果：81 個畫面，抵達結果頁，耗時 135 s。console error 0，製作者字樣問題 0，出界 0。
  - 請求共 18 筆：`rlirdo.github.io` 17 筆、`blob:` 1 筆。外部請求 0 筆。
- **線上 AR 假相機**：`ar.html?selftest=1`。
  - 2.1 s 取得 **targetFound**（已完成首幀渲染）；之後依序出現 floatMode（在可視範圍內）、reattached。
  - 頁面例外 0。截圖：`tools/shots/online_ar_*.png`。
- **QR 解碼**：`tools/verify_qr.py`，用 OpenCV `QRCodeDetector` 解碼；PDF 先用 PyMuPDF 轉成 300 dpi 點陣再解碼。`assets/qr.png` 與 `assets/target_print.pdf` 第 1 頁都解出 `https://rlirdo.github.io/serpentine-webar/`。

## 6. exe 啟動器（launcher/）— 通過

- 建置：
  ```
  python -m PyInstaller --noconfirm --clean --distpath launcher/dist --workpath launcher/build launcher/build.spec
  ```
  - 產出 onefile、無主控台的 `SerpentineWebAR.exe`，再改名為 `墨玉晶格修復任務WebAR.exe`。
  - 遊戲網頁完整打包在 exe 內的 `web/`；圖示由 `assets/icon.png` 轉成 ico。
- **精簡環境 `--selftest`**：
  - 條件：把 exe 複製到另一個資料夾；PATH 只有 `C:\Windows\System32;C:\Windows`，沒有任何 PYTHON* 變數。
  - 結果：exit code 0。29 個檢查項目全部 OK：28 個檔案都是 200 且 MIME 正確（.js 為 `text/javascript`、.mind 為 `application/octet-stream`），根目錄 `/` 也回 200。
  - log 寫在 exe 同層。`--version` 的 exit code 為 0。
- **實際啟動 `--no-browser`**：伺服器在 127.0.0.1:8731（優先固定埠）。
  - 啟動頁 `launcher.html`：
    - 1280×720 與 1920×1080 都剛好一頁，沒有捲動，也沒有水平出界。
    - 任務卡圖與 QR 都載入成功。任務卡寬 484／772 px，QR 寬 151／227 px。
    - 製作者字樣在視窗內、z-index 最高，不與按鈕重疊。截圖已看過。
  - 通關 `play.html?autoplay=1`（1280×720）：81 個畫面，抵達結果頁，console error 0。
  - AR `ar.html?selftest=1`：1.7 s targetFound，之後出現 floatMode、reattached，例外 0。
  - 控制視窗：截圖看過標題、目前網址、〔重新開啟頁面〕〔結束遊戲〕，右下有製作者字樣。
  - 結束：送 WM_CLOSE 給控制視窗，等同按 X。bootloader exit code 0；之後 tasklist 查無同名行程，原埠不再回應。
- **斷網情境（電腦版不得有外部請求）**：
  - 瀏覽器端：play.html 通關全程 18 筆請求，`127.0.0.1:8731` 17 筆、`blob:` 1 筆，外部請求 0 筆。啟動頁的外部請求也是 0 筆。
  - 伺服器端：launcher.log 記錄 46 筆 http 請求，來源全部是 127.0.0.1。

## 已知限制（階段二）

- exe 沒有數位簽章，首次執行會出現 SmartScreen 警告（使用說明已寫處理方式）。
- 作答紀錄依瀏覽器 origin 分開存放。exe 優先使用 8731 埠，被占用時會改用其他埠，這時候就看不到先前的紀錄。
- 線上版與 exe 都只在 headless Chrome 測試，仍未在實體手機上測試。
