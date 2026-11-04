/**
 * WebAR 遊戲回饋問卷＋遊戲前後測作答 中繼（Google Apps Script 網頁應用程式）
 *
 * ★ v3：2026/10/29 晚間新增 schema webar-game-v1（遊戲內前測／後測作答，寫入 feedback/game/）。
 *   貼上本檔後同樣「需重新部署為新版本」（步驟同下）。/exec 網址不變。
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
var GAME_SCHEMA = 'webar-game-v1';
var GAME_DIR = 'feedback/game';
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
    if (!input || (input.schema !== SCHEMA && input.schema !== GAME_SCHEMA)) return json_({ ok: false, error: 'schema 不符' });
    var isGame = input.schema === GAME_SCHEMA;

    var rec = isGame ? cleanGame_(input) : clean_(input);
    if (rec.error) return json_({ ok: false, error: rec.error });

    var tz = 'Asia/Taipei';
    var now = new Date();
    rec.submitted_at = Utilities.formatDate(now, tz, "yyyy-MM-dd'T'HH:mm:ss") + '+08:00';  // 以伺服器時間為準
    var name = Utilities.formatDate(now, tz, 'yyyyMMdd-HHmmss') + (isGame ? '_' + rec.phase : '') + '_' + rand6_();

    var token = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
    if (!token) return json_({ ok: false, error: '中繼尚未設定 GITHUB_TOKEN' });

    var ordered = {};
    (isGame ? GAME_FIELDS : FIELDS).forEach(function (k) { ordered[k] = rec[k]; });
    var body = JSON.stringify(ordered, null, 2) + '\n';

    var url = 'https://api.github.com/repos/' + REPO_OWNER + '/' + REPO_NAME +
      '/contents/' + (isGame ? GAME_DIR : RESP_DIR) + '/' + name + '.json';
    var resp = UrlFetchApp.fetch(url, {
      method: 'put',
      contentType: 'application/json',
      headers: {
        Authorization: 'Bearer ' + token,
        Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
      },
      payload: JSON.stringify({
        message: (isGame ? 'game: ' : 'feedback: ') + name,
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
  return json_({ ok: true, service: 'webar-feedback-relay', schema: SCHEMA, schemas: [SCHEMA, GAME_SCHEMA], token_set: hasToken });
}

// ---------------------------------------------------------------- 遊戲前後測（webar-game-v1）
// 欄位順序固定（撈取工具依此解析）
var GAME_FIELDS = ['schema', 'submitted_at', 'event', 'pid', 'sid', 'phase', 'grade', 'mode', 'client_time',
  'pre', 'post', 'preScore', 'postSame3', 'postScore', 'stars', 'totalStars', 'facets', 'commit', 'ua'];
var GAME_FACETS = ['知識', '態度', '行動', '探究'];
var ID_RE = /^[EJ](10|[1-9])$/;   // 國小 E1–E10、國中 J1–J10
var CODE_RE = /^[a-z0-9]{12}$/;

/** 只保留白名單欄位、檢查題號／選項／分數範圍、截斷字串 */
function cleanGame_(d) {
  var r = { schema: GAME_SCHEMA, event: str_(d.event, 40) || DEFAULT_EVENT };
  if (!CODE_RE.test(String(d.pid || ''))) return { error: 'pid 格式不符' };
  if (!CODE_RE.test(String(d.sid || ''))) return { error: 'sid 格式不符' };
  r.pid = d.pid; r.sid = d.sid;
  if (d.phase !== 'pre' && d.phase !== 'post') return { error: 'phase 必須是 pre 或 post' };
  r.phase = d.phase;
  if (d.grade !== 'elem' && d.grade !== 'junior') return { error: 'grade 必須是 elem 或 junior' };
  r.grade = d.grade;
  r.mode = (d.mode === 'ar' || d.mode === 'play') ? d.mode : 'play';
  r.client_time = str_(d.client_time, 40);
  var isPost = r.phase === 'post';
  var pre = answers_(d.pre, 3);
  if (pre.error) return { error: '前測 ' + pre.error };
  r.pre = pre.list;
  if (isPost) {
    var post = answers_(d.post, 5);
    if (post.error) return { error: '後測 ' + post.error };
    r.post = post.list;
  } else {
    r.post = [];
  }
  r.preScore = r.pre.filter(function (a) { return a.correct; }).length;
  if (isPost) {
    var preIds = r.pre.map(function (a) { return a.id; });
    r.postSame3 = r.post.filter(function (a) { return a.correct && preIds.indexOf(a.id) >= 0; }).length;
    r.postScore = r.post.filter(function (a) { return a.correct; }).length;
    var stars = Array.isArray(d.stars) ? d.stars : [];
    if (stars.length !== 8) return { error: 'stars 必須是 8 個整數' };
    r.stars = [];
    for (var i = 0; i < 8; i++) {
      var sv = Number(stars[i]);
      if (!(sv >= 0 && sv <= 3 && Math.floor(sv) === sv)) return { error: 'stars 必須是 0–3 的整數' };
      r.stars.push(sv);
    }
    r.totalStars = r.stars.reduce(function (a, b) { return a + b; }, 0);
    r.facets = {};
    var fin = (d.facets && typeof d.facets === 'object') ? d.facets : {};
    GAME_FACETS.forEach(function (f) {
      var fv = Number(fin[f]);
      r.facets[f] = (fv >= 0 && fv <= 100) ? Math.round(fv) : '';
    });
    r.commit = str_(d.commit, 80);
  } else {
    r.postSame3 = ''; r.postScore = ''; r.stars = []; r.totalStars = ''; r.facets = {}; r.commit = '';
  }
  r.ua = str_(d.ua, 120);
  return r;
}

/** 檢查作答陣列：長度固定、題號合規、pick 0–3、correct 布林 */
function answers_(arr, n) {
  if (!Array.isArray(arr) || arr.length !== n) return { error: '作答必須是 ' + n + ' 題' };
  var out = [];
  for (var i = 0; i < n; i++) {
    var a = arr[i] || {};
    if (!ID_RE.test(String(a.id || ''))) return { error: '題號不合規' };
    var pick = Number(a.pick);
    if (!(pick >= 0 && pick <= 3 && Math.floor(pick) === pick)) return { error: 'pick 必須是 0–3' };
    out.push({ id: a.id, facet: GAME_FACETS.indexOf(a.facet) >= 0 ? a.facet : '',
      pick: pick, correct: a.correct === true || a.correct === 'true' });
  }
  return { list: out };
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
