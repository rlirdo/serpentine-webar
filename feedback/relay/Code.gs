/**
 * WebAR 遊戲回饋問卷＋遊戲前後測作答 中繼（Google Apps Script 網頁應用程式）
 *
 * ★ v6：2026/11/26 學生版課後問卷（feedback/student.html）遊戲班多 6 題 TAM（科技接受度）：
 *   webar-feedback-v2 多收 6 個「選填」欄位 pe1,pe2,pe3（知覺易用性）、pu1,pu2,pu3（知覺有用性），1–5 整數。
 *   6 個都沒給（undefined／null／空字串）時，行為與輸出和 v5 完全相同（輸出不含這些鍵）；
 *   只要給了其中任何一個，6 個都必須是 1–5 整數，否則回錯誤；通過時依固定順序寫在 s_open 之後、ua 之前。
 *   doGet 健康檢查多回 version: 6 與 feedback_optional。webar-game-v1、webar-game-v2、webar-test-v1 的行為完全不變。
 *   貼上本檔後「需重新部署為新版本」：部署 → 管理部署作業 → 鉛筆（編輯）→ 版本選「新版本」→ 部署。
 *   不可按「新增部署作業」（/exec 網址會改變）。未重新部署前，TAM 6 題會被 v5 白名單靜靜丟掉，其餘 16 題照常寫入。
 * ★ v5：2026/11/25 新增 schema webar-test-v1（研究用整份 10 題前後測，兩組共用）：
 *   group='control'：對照班「只有測驗」頁 test/index.html，不玩遊戲，mode 固定 'test'，不可帶星數；
 *   group='game'：遊戲研究模式 play.html／ar.html?study=1，mode 為 ar|play，後測必帶八關星數（1–3）與 restarts。
 *   兩組都是課前、課後各做同一份整份 10 題，後測後選一項行動承諾；研究模式不另送 webar-game-v1。
 *   寫入 feedback/test/（不是 feedback/game/，撈取工具的遊戲彙整不受影響），檔名 yyyyMMdd-HHmmss_<phase>_<6碼>.json。
 *   webar-game-v1、webar-game-v2、webar-feedback-v2 的行為完全不變。
 *   貼上本檔後「需重新部署為新版本」：部署 → 管理部署作業 → 鉛筆（編輯）→ 版本選「新版本」→ 部署。
 *   不可按「新增部署作業」（/exec 網址會改變）。未重新部署前，對照班頁面的上傳會被回「schema 不符」，
 *   資料留在學生手機的補傳佇列，重新部署後學生再開頁面才會補傳。
 * ★ v4：2026/11/04 新增 schema webar-game-v2（新遊戲「墨玉護衛隊：花蓮綠晶行動」，方向盤版
 *   mode='drive'；多收 age 年齡 3–120／gender 性別（男、女、其他、不透露）／org 學校或單位 ≤60 字／
 *   hero 主角 id ≤20 字）。同樣寫入 feedback/game/，檔名 yyyyMMdd-HHmmss_<phase>_<6碼>.json。
 *   webar-game-v1 與 webar-feedback-v2 的行為完全不變。
 *   貼上本檔後「需重新部署為新版本」：部署 → 管理部署作業 → 鉛筆（編輯）→ 版本選「新版本」→ 部署。
 *   不可按「新增部署作業」（/exec 網址會改變，兩個遊戲與問卷的 config.js 都得跟著改）。
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
var GAME_SCHEMA_V2 = 'webar-game-v2';
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
// v6：學生版遊戲班的 TAM 6 題（選填；有給就 6 題都要 1–5 整數），寫在 s_open 之後、ua 之前
var TAM = ['pe1', 'pe2', 'pe3', 'pu1', 'pu2', 'pu3'];
var FIELDS_TAM = FIELDS.slice(0, FIELDS.length - 1).concat(TAM, ['ua']);
var RELAY_VERSION = 6;

function doPost(e) {
  try {
    var raw = (e && e.postData && e.postData.contents) || '';
    if (!raw || raw.length > 20000) return json_({ ok: false, error: '內容為空或過大' });
    var input = JSON.parse(raw);
    if (!input || (input.schema !== SCHEMA && input.schema !== GAME_SCHEMA && input.schema !== GAME_SCHEMA_V2 && input.schema !== TEST_SCHEMA)) return json_({ ok: false, error: 'schema 不符' });
    var isTest = input.schema === TEST_SCHEMA;
    var isV2 = input.schema === GAME_SCHEMA_V2;
    var isGame = input.schema === GAME_SCHEMA || isV2 || isTest;   // isGame：檔名帶 phase

    var rec = isTest ? cleanTest_(input) : (isV2 ? cleanGameV2_(input) : (isGame ? cleanGame_(input) : clean_(input)));
    if (rec.error) return json_({ ok: false, error: rec.error });

    var tz = 'Asia/Taipei';
    var now = new Date();
    rec.submitted_at = Utilities.formatDate(now, tz, "yyyy-MM-dd'T'HH:mm:ss") + '+08:00';  // 以伺服器時間為準
    var name = Utilities.formatDate(now, tz, 'yyyyMMdd-HHmmss') + (isGame ? '_' + rec.phase : '') + '_' + rand6_();

    var token = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
    if (!token) return json_({ ok: false, error: '中繼尚未設定 GITHUB_TOKEN' });

    var ordered = {};
    (isTest ? TEST_FIELDS : (isV2 ? GAME_FIELDS_V2 : (isGame ? GAME_FIELDS : fieldsFor_(rec)))).forEach(function (k) { ordered[k] = rec[k]; });
    var body = JSON.stringify(ordered, null, 2) + '\n';

    var url = 'https://api.github.com/repos/' + REPO_OWNER + '/' + REPO_NAME +
      '/contents/' + (isTest ? TEST_DIR : (isGame ? GAME_DIR : RESP_DIR)) + '/' + name + '.json';
    var resp = UrlFetchApp.fetch(url, {
      method: 'put',
      contentType: 'application/json',
      headers: {
        Authorization: 'Bearer ' + token,
        Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
      },
      payload: JSON.stringify({
        message: (isTest ? 'test: ' : (isGame ? 'game: ' : 'feedback: ')) + name,
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
  return json_({ ok: true, service: 'webar-feedback-relay', schema: SCHEMA, schemas: [SCHEMA, GAME_SCHEMA, GAME_SCHEMA_V2, TEST_SCHEMA], token_set: hasToken,
    version: RELAY_VERSION, feedback_optional: TAM.slice() });
}

// ---------------------------------------------------------------- 對照班只有測驗（webar-test-v1）
var TEST_SCHEMA = 'webar-test-v1';
var TEST_DIR = 'feedback/test';
var DEFAULT_TEST_EVENT = 'CTRL-TEST';
var TEST_N = 10;
var DEFAULT_STUDY_EVENT = 'STUDY-GAME';
var TEST_GROUPS = ['control', 'game'];             // control＝對照班測驗頁；game＝遊戲研究模式（?study=1）
var TEST_ATTITUDE = ['E3', 'E7', 'J3', 'J8'];      // 態度題：不計對錯（correct 一律寫 null）
// 欄位順序固定（撈取工具依此解析）
var TEST_FIELDS = ['schema', 'submitted_at', 'event', 'group', 'pid', 'sid', 'phase', 'grade', 'mode', 'client_time',
  'pre', 'post', 'preScore', 'postScore', 'maxScore', 'stars', 'totalStars', 'restarts', 'commit', 'commitPick', 'ua'];

/** 對照班與遊戲班研究模式：前測／後測各 10 題，題號須依版本由 1 到 10 排好；分數只算 8 題計分題（伺服器重算）。
 *  group=game：mode 為 ar|play；後測必帶 8 關星數（1–3 整數）；restarts＝中途重新整理後從第 1 關重闖的次數。
 *  group=control：mode 一律 test，不可帶星數。 */
function cleanTest_(d) {
  if (TEST_GROUPS.indexOf(d.group) < 0) return { error: 'group 必須是 control 或 game' };
  var isGameGroup = d.group === 'game';
  var r = { schema: TEST_SCHEMA, event: str_(d.event, 40) || (isGameGroup ? DEFAULT_STUDY_EVENT : DEFAULT_TEST_EVENT) };
  r.group = d.group;
  var hasStars = Array.isArray(d.stars) ? d.stars.length > 0 : (d.stars !== undefined && d.stars !== null && d.stars !== '');
  if (!isGameGroup && hasStars) return { error: '對照班不可帶 stars' };
  if (!CODE_RE.test(String(d.pid || ''))) return { error: 'pid 格式不符' };
  if (!CODE_RE.test(String(d.sid || ''))) return { error: 'sid 格式不符' };
  r.pid = d.pid; r.sid = d.sid;
  if (d.phase !== 'pre' && d.phase !== 'post') return { error: 'phase 必須是 pre 或 post' };
  r.phase = d.phase;
  if (d.grade !== 'elem' && d.grade !== 'junior') return { error: 'grade 必須是 elem 或 junior' };
  r.grade = d.grade;
  r.mode = isGameGroup ? ((d.mode === 'ar' || d.mode === 'play') ? d.mode : 'play') : 'test';
  r.client_time = str_(d.client_time, 40);
  var isPost = r.phase === 'post';
  r.stars = []; r.totalStars = ''; r.restarts = '';
  if (isGameGroup) {
    if (isPost) {
      if (!Array.isArray(d.stars) || d.stars.length !== 8) return { error: 'stars 必須是 8 個整數' };
      for (var s = 0; s < 8; s++) {
        var sv = d.stars[s];
        if (!(typeof sv === 'number' && sv >= 1 && sv <= 3 && Math.floor(sv) === sv)) return { error: 'stars 必須是 1–3 的整數' };
        r.stars.push(sv);
      }
      r.totalStars = r.stars.reduce(function (a, b) { return a + b; }, 0);
    } else if (hasStars) {
      return { error: '前測不可帶 stars' };
    }
    var rs = Number(d.restarts);
    r.restarts = (typeof d.restarts === 'number' && rs >= 0 && rs <= 99 && Math.floor(rs) === rs) ? rs : 0;
  }
  var pre = testAnswers_(d.pre, r.grade);
  if (pre.error) return { error: '前測 ' + pre.error };
  r.pre = pre.list;
  if (isPost) {
    var post = testAnswers_(d.post, r.grade);
    if (post.error) return { error: '後測 ' + post.error };
    r.post = post.list;
  } else {
    r.post = [];
  }
  var score = function (list) { return list.filter(function (a) { return a.correct === true; }).length; };
  r.preScore = score(r.pre);
  r.postScore = isPost ? score(r.post) : '';
  r.maxScore = TEST_N - 2;
  if (isPost) {
    var cpRaw = d.commitPick;
    var cp = (typeof cpRaw === 'number' || (typeof cpRaw === 'string' && /^\s*\d+\s*$/.test(cpRaw))) ? Number(cpRaw) : NaN;
    if (!(cp >= 0 && cp <= 3 && Math.floor(cp) === cp)) return { error: 'commitPick 必須是 0–3' };
    r.commitPick = cp;
    r.commit = str_(d.commit, 80);
  } else {
    r.commitPick = ''; r.commit = '';
  }
  r.ua = str_(d.ua, 120);
  return r;
}

/** 10 題、題號依序 E1–E10 或 J1–J10、pick 0–3；態度題 correct=null，其餘為布林 */
function testAnswers_(arr, grade) {
  if (!Array.isArray(arr) || arr.length !== TEST_N) return { error: '作答必須是 ' + TEST_N + ' 題' };
  var prefix = grade === 'junior' ? 'J' : 'E';
  var out = [];
  for (var i = 0; i < TEST_N; i++) {
    var a = arr[i] || {};
    var id = prefix + (i + 1);
    if (String(a.id || '') !== id) return { error: '第 ' + (i + 1) + ' 題題號必須是 ' + id };
    var pick = Number(a.pick);
    if (!(pick >= 0 && pick <= 3 && Math.floor(pick) === pick)) return { error: 'pick 必須是 0–3' };
    var att = TEST_ATTITUDE.indexOf(id) >= 0;
    out.push({ id: id, facet: GAME_FACETS.indexOf(a.facet) >= 0 ? a.facet : '',
      pick: pick, correct: att ? null : (a.correct === true || a.correct === 'true') });
  }
  return { list: out };
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

// ---------------------------------------------------------------- 新遊戲方向盤版（webar-game-v2）
// 欄位順序固定（撈取工具依此解析）
var GAME_FIELDS_V2 = ['schema', 'submitted_at', 'event', 'pid', 'sid', 'phase', 'grade', 'mode', 'client_time',
  'age', 'gender', 'org', 'hero',
  'pre', 'post', 'preScore', 'postSame3', 'postScore', 'stars', 'totalStars', 'facets', 'commit', 'ua'];
var DEFAULT_EVENT_V2 = 'HL-STATION-2026-1127';   // 2026/11/27 花蓮火車站科普展示
var GENDERS = ['男', '女', '其他', '不透露'];

/** 沿用 v1 全部驗證，再加年齡／性別／單位／主角；mode 另允許 drive */
function cleanGameV2_(d) {
  var r = cleanGame_(d);
  if (r.error) return r;
  r.schema = GAME_SCHEMA_V2;
  r.event = str_(d.event, 40) || DEFAULT_EVENT_V2;
  r.mode = (d.mode === 'drive' || d.mode === 'ar' || d.mode === 'play') ? d.mode : 'drive';
  var ageRaw = d.age;
  var age = (typeof ageRaw === 'number' || (typeof ageRaw === 'string' && /^\s*\d+\s*$/.test(ageRaw))) ? Number(ageRaw) : NaN;
  r.age = (age >= 3 && age <= 120 && Math.floor(age) === age) ? age : '';
  r.gender = GENDERS.indexOf(String(d.gender || '').trim()) >= 0 ? String(d.gender).trim() : '';
  r.org = str_(d.org, 60);
  r.hero = str_(d.hero, 20);
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
  // v6：TAM 6 題選填。全部沒給 → 不加任何鍵（輸出同 v5）；給了任何一題 → 6 題都要 1–5 整數
  var hasTam = TAM.some(function (t) { return d[t] !== undefined && d[t] !== null && d[t] !== ''; });
  if (hasTam) {
    for (var t = 0; t < TAM.length; t++) {
      var tk = TAM[t];
      var traw = d[tk];
      var tv = (typeof traw === 'number' || (typeof traw === 'string' && /^\s*\d+\s*$/.test(traw))) ? Number(traw) : NaN;
      if (!(tv >= 1 && tv <= 5 && Math.floor(tv) === tv)) return { error: '欄位 ' + tk + ' 必須是 1–5 的整數（TAM 6 題須一起作答）' };
      r[tk] = tv;
    }
  }
  r.ua = str_(d.ua, 120);
  return r;
}

/** webar-feedback-v2 的輸出欄位：有 TAM 才用 FIELDS_TAM，否則與 v5 相同 */
function fieldsFor_(rec) { return rec.pe1 !== undefined ? FIELDS_TAM : FIELDS; }

function str_(s, n) { return (s === undefined || s === null) ? '' : String(s).trim().slice(0, n); }

function rand6_() {
  var c = 'abcdefghijklmnopqrstuvwxyz0123456789', s = '';
  for (var i = 0; i < 6; i++) s += c.charAt(Math.floor(Math.random() * c.length));
  return s;
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
