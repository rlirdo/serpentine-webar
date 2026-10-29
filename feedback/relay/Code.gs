/**
 * WebAR 遊戲回饋問卷 中繼（Google Apps Script 網頁應用程式）
 *
 * ★ v2：2026/10/29 改版（schema webar-feedback-v2：環境知識／環境態度／行動意向／科學探究
 *   四面向 × 各 3 題選擇＋1 題簡答）。貼上本檔後「需重新部署為新版本」：
 *   部署 → 管理部署作業 → 鉛筆（編輯）→ 版本選「新版本」→ 部署。
 *   不要按「新增部署作業」，否則 /exec 網址會改變、問卷 config.js 也得跟著改。
 *
 * 流程：問卷網頁 POST（text/plain JSON）→ doPost → 白名單驗證 → GitHub Contents API
 *       寫入 rlirdo/serpentine-webar 的 feedback/responses/<YYYYMMDD-HHMMSS_6碼>.json
 *
 * 指令碼屬性（專案設定 → 指令碼屬性）：
 *   GITHUB_TOKEN  必填。fine-grained token，只授權 serpentine-webar、Contents: Read and write。
 *   （v1 的 SHEET_ID 已不再使用：v2 不蒐集 email、身分、裝置，留著也不會被讀取。）
 *
 * ★ token 只放在指令碼屬性，絕不寫在本檔、網頁或 repo 裡。
 */

var REPO_OWNER = 'rlirdo';
var REPO_NAME = 'serpentine-webar';
var RESP_DIR = 'feedback/responses';
var SCHEMA = 'webar-feedback-v2';
var DEFAULT_EVENT = 'SEET2026-A155-07';
var OPEN_MAX = 300;

var MC = ['k1', 'k2', 'k3'];                       // 環境知識：四選一，只收 A–D
var MC_CHOICES = ['A', 'B', 'C', 'D'];
var LIKERT = ['a1', 'a2', 'a3', 'i1', 'i2', 'i3', 's1', 's2', 's3'];   // 態度／行動／探究：1–5 整數
var OPENS = ['k_open', 'a_open', 'i_open', 's_open'];                 // 簡答：可空，截 300 字
// 欄位順序固定（撈取工具依此解析）
var FIELDS = ['schema', 'submitted_at', 'event',
  'k1', 'k2', 'k3', 'k_open',
  'a1', 'a2', 'a3', 'a_open',
  'i1', 'i2', 'i3', 'i_open',
  's1', 's2', 's3', 's_open',
  'ua'];

function doPost(e) {
  try {
    var raw = (e && e.postData && e.postData.contents) || '';
    if (!raw || raw.length > 20000) return json_({ ok: false, error: '內容為空或過大' });
    var input = JSON.parse(raw);
    if (!input || input.schema !== SCHEMA) return json_({ ok: false, error: 'schema 不符' });

    var rec = clean_(input);
    if (rec.error) return json_({ ok: false, error: rec.error });

    var tz = 'Asia/Taipei';
    var now = new Date();
    rec.submitted_at = Utilities.formatDate(now, tz, "yyyy-MM-dd'T'HH:mm:ss") + '+08:00';  // 以伺服器時間為準
    var name = Utilities.formatDate(now, tz, 'yyyyMMdd-HHmmss') + '_' + rand6_();

    var token = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
    if (!token) return json_({ ok: false, error: '中繼尚未設定 GITHUB_TOKEN' });

    var ordered = {};
    FIELDS.forEach(function (k) { ordered[k] = rec[k]; });
    var body = JSON.stringify(ordered, null, 2) + '\n';

    var url = 'https://api.github.com/repos/' + REPO_OWNER + '/' + REPO_NAME +
      '/contents/' + RESP_DIR + '/' + name + '.json';
    var resp = UrlFetchApp.fetch(url, {
      method: 'put',
      contentType: 'application/json',
      headers: {
        Authorization: 'Bearer ' + token,
        Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
      },
      payload: JSON.stringify({
        message: 'feedback: ' + name,
        content: Utilities.base64Encode(body, Utilities.Charset.UTF_8)
      }),
      muteHttpExceptions: true
    });
    var code = resp.getResponseCode();
    if (code !== 201 && code !== 200) {
      console.error('GitHub API ' + code + ': ' + resp.getContentText().slice(0, 300));
      return json_({ ok: false, error: 'GitHub 寫入失敗（' + code + '）' });
    }
    return json_({ ok: true, name: name });
  } catch (err) {
    console.error(err);
    return json_({ ok: false, error: '伺服器錯誤：' + (err && err.message ? err.message : err) });
  }
}

/** 瀏覽器直接開 /exec 網址時的健康檢查 */
function doGet() {
  var hasToken = !!PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
  return json_({ ok: true, service: 'webar-feedback-relay', schema: SCHEMA, token_set: hasToken });
}

/** 只保留白名單欄位、檢查選項與分數、截斷字串長度 */
function clean_(d) {
  var r = { schema: SCHEMA, event: str_(d.event, 40) || DEFAULT_EVENT };
  for (var i = 0; i < MC.length; i++) {
    var k = MC[i];
    if (MC_CHOICES.indexOf(d[k]) < 0) return { error: '欄位 ' + k + ' 必須是 A–D' };
    r[k] = d[k];
  }
  for (var j = 0; j < LIKERT.length; j++) {
    var q = LIKERT[j];
    var raw = d[q];
    var v = (typeof raw === 'number' || (typeof raw === 'string' && /^\s*\d+\s*$/.test(raw))) ? Number(raw) : NaN;
    if (!(v >= 1 && v <= 5 && Math.floor(v) === v)) return { error: '欄位 ' + q + ' 必須是 1–5 的整數' };
    r[q] = v;
  }
  for (var m = 0; m < OPENS.length; m++) r[OPENS[m]] = str_(d[OPENS[m]], OPEN_MAX);
  r.ua = str_(d.ua, 120);
  return r;
}

function str_(s, n) { return (s === undefined || s === null) ? '' : String(s).trim().slice(0, n); }

function rand6_() {
  var c = 'abcdefghijklmnopqrstuvwxyz0123456789', s = '';
  for (var i = 0; i < 6; i++) s += c.charAt(Math.floor(Math.random() * c.length));
  return s;
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
