# vendor/ 第三方函式庫（離線版，頁面不依賴 CDN）

| 套件 | 版本 | 檔案 | 授權 | 來源（npm 官方發行檔，經 jsdelivr 下載） |
|---|---|---|---|---|
| three.js | 0.160.1（r160） | `three/three.module.js`、`three/addons/renderers/CSS3DRenderer.js` | MIT（`three/LICENSE`） | `https://cdn.jsdelivr.net/npm/three@0.160.1/build/three.module.js`、`.../examples/jsm/renderers/CSS3DRenderer.js` |
| es-module-shims | 1.10.1 | `es-module-shims.js` | MIT（`es-module-shims.LICENSE`） | `https://cdn.jsdelivr.net/npm/es-module-shims@1.10.1/dist/es-module-shims.js` |
| mind-ar（image tracking，three 版＋編譯器） | 1.2.5 | `mindar/mindar-image-three.prod.js`、`mindar/mindar-image.prod.js`、`mindar/controller-mGt1s8dJ.js`、`mindar/ui-fBadYuor.js` | MIT（`mindar/LICENSE`） | `https://cdn.jsdelivr.net/npm/mind-ar@1.2.5/dist/…` |

下載日期：2026/10/01。

## 版本相容說明
- mind-ar 1.2.5 的 `package.json` 宣告 `peerDependencies: three >= 0.136.0`。
- 但 `mindar-image-three.prod.js` 以 ES module `import { …, sRGBEncoding, … } from "three"` 並設定 `renderer.outputEncoding`；`sRGBEncoding` 在 three r162 起移除，因此選用 **r160（0.160.1）**：仍匯出 `sRGBEncoding`，且 `outputEncoding` 設定會自動轉為 `outputColorSpace`（只出現一次 console 警告，不影響功能）。
- 另需 `three/addons/renderers/CSS3DRenderer.js`，同樣取自 0.160.1。
- iOS Safari 15–16.3 不支援 importmap，`play.html`／`ar.html` 先載入 es-module-shims（polyfill；原生支援的瀏覽器不做事）。
- 頁面以 importmap 對應：`"three": "./vendor/three/three.module.js"`、`"three/addons/": "./vendor/three/addons/"`。
- `mindar-image.prod.js` 匯出 `Compiler`（供 `tools/compile.html` 編譯 `assets/targets.mind`）。
- 未收錄 face tracking 用的 `controller-d1-OMKPY.js`（本專案不需要）。
- MindAR 的 Web Worker 以 base64 內嵌於 controller 檔內，離線可用；tfjs 不需另外下載模型。
