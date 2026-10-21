/**
 * WebAR 遊戲回饋問卷 中繼（Google Apps Script 網頁應用程式）
 * 流程：問卷網頁 POST（text/plain JSON）→ doPost → 驗證欄位 → GitHub Contents API
 *       寫入 rlirdo/serpentine-webar 的 feedback/responses/<name>.json
 *       （選用）同時 append 一列到 Google Sheet。
 *
 * 指令碼屬性（專案設定 → 指令碼屬性）：
 *   GITHUB_TOKEN  必填。fine-grained token，只授權 serpentine-webar、Contents: Read and write。
 *   SHEET_ID      要收 email 就必須設定。私人 Google 試算表 ID；空白則不寫試算表，email 直接丟棄。
 *
 * ★ 隱私：寫入 GitHub（公開 repo）的 JSON 一律 contact=""（保留 contact_ok）；
 *   email 只寫入 SHEET_ID 指定的私人試算表。SHEET_ID 未設時 email 丟棄，回應 contact_saved:false。
 *
 * ★ token 只放在指令碼屬性，絕不寫在本檔、網頁或 repo 裡。
 */

var REPO_OWNER = 'rlirdo';
var REPO_NAME = 'serpentine-webar';
var RESP_DIR = 'feedback/responses';
var SCHEMA = 'webar-feedback-v1';

var CHOICES = {
  role: ['國小教師', '國中教師', '高中教師', '大專教師', '研究生', '大學生', '其他'],
  teach_level: ['國小', '國中', '高中', '大專', '不適用'],
  played: ['完整玩完', '玩了一部分', '只看示範'],
  device: ['iPhone', 'Android', '平板', '電腦', '其他'],
  fit_level: ['國小高年級', '國中', '高中', '皆可', '皆不適合'],
  contact_ok: ['願意', '不願意']
};
var LIKERT = ['q1_clear', 'q2_fun', 'q3_easy', 'q4_mechanism', 'q5_feedback_useful', 'q6_use_in_class'];
// 欄位順序固定（下載 exe 依此解析）
var FIELDS = ['schema', 'submitted_at', 'event', 'role', 'role_other', 'teach_level', 'played', 'device']
  .concat(LIKERT)
  .concat(['best_part', 'suggest', 'fit_level', 'contact_ok', 'contact', 'ua']);

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

    var email = rec.contact;   // 只留在記憶體，供私人試算表使用
    var ordered = {};
    FIELDS.forEach(function (k) { ordered[k] = rec[k]; });
    ordered.contact = '';      // 公開 repo 絕不寫入 email
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

    var sheetRow = {};
    FIELDS.forEach(function (k) { sheetRow[k] = ordered[k]; });
    sheetRow.contact = email;
    var saved = appendSheet_(sheetRow, name);
    var out = { ok: true, name: name };
    if (email) out.contact_saved = saved;   // 有填 email 才回報是否已存入私人試算表
    return json_(out);
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
  var r = { schema: SCHEMA, event: str_(d.event, 40) || 'SEET2026-A155-07' };
  var keys = Object.keys(CHOICES);
  for (var i = 0; i < keys.length; i++) {
    var k = keys[i];
    if (CHOICES[k].indexOf(d[k]) < 0) return { error: '欄位 ' + k + ' 選項不正確' };
    r[k] = d[k];
  }
  for (var j = 0; j < LIKERT.length; j++) {
    var q = LIKERT[j];
    var v = parseInt(d[q], 10);
    if (!(v >= 1 && v <= 5)) return { error: '欄位 ' + q + ' 必須是 1–5' };
    r[q] = v;
  }
  r.role_other = r.role === '其他' ? str_(d.role_other, 40) : '';
  r.best_part = str_(d.best_part, 500);
  r.suggest = str_(d.suggest, 500);
  if (!r.best_part || !r.suggest) return { error: '開放題不可空白' };
  r.contact = r.contact_ok === '願意' ? str_(d.contact, 120) : '';
  if (r.contact && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(r.contact)) return { error: 'Email 格式不正確' };
  r.ua = str_(d.ua, 120);
  return r;
}

/** 寫入私人試算表（含 email）；成功回 true。SHEET_ID 未設或失敗回 false。 */
function appendSheet_(rec, name) {
  var id = PropertiesService.getScriptProperties().getProperty('SHEET_ID');
  if (!id) return false;
  try {
    var sh = SpreadsheetApp.openById(id).getSheets()[0];
    if (sh.getLastRow() === 0) sh.appendRow(['file'].concat(FIELDS));
    sh.appendRow([name].concat(FIELDS.map(function (k) { return rec[k]; })));
    return true;
  } catch (err) {
    console.error('Sheet 寫入失敗：' + err);  // 試算表失敗不影響 GitHub 已寫入的結果
    return false;
  }
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
