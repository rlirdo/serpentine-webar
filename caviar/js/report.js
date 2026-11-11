// 前後測作答匿名上傳（schema webar-game-v2；欄位順序固定，中繼 GAME_FIELDS_V2 與撈取工具依此）
// 中繼網址取自 feedback/config.js 的 window.FEEDBACK_ENDPOINT。不記名；pid 只是本裝置隨機 12 碼。
// 任何失敗都靜默略過，絕不影響遊戲流程；?autoplay=1 時不上傳。
const PID_KEY = "caviarSquad.pid";
const SCHEMA = "webar-game-v2";
const EVENT = "HL-STATION-2026-1127-CAVIAR"; // 同日同站墨玉護衛隊為 HL-STATION-2026-1127，以後綴區分
const EVENT_SR = EVENT + "-SR"; // 高階（中繼只收 elem／junior，高階以 event 後綴區分）
// 上傳相容：中繼只接受 grade elem／junior、題號 /^[EJ](10|[1-9])$/
export function uploadGrade(tier) { return tier === "elem" ? "elem" : "junior"; }
export function uploadEvent(tier) { return tier === "senior" ? EVENT_SR : EVENT; }
export function uploadId(id) { return String(id || "").replace(/^S/, "J"); }
export function uploadOrg(role, org) {
  const r = String(role || "").trim(), o = String(org || "").trim();
  return (r ? `${r}｜${o}` : o).slice(0, 60); // 有身分時一律帶分隔號（單位空白也帶），撈取工具才能拆欄
}
export const GENDER_SET = ["男", "女", "其他", "不透露"];

function rand(n) {
  const c = "abcdefghijklmnopqrstuvwxyz0123456789";
  let s = "";
  try {
    const a = new Uint8Array(n);
    crypto.getRandomValues(a);
    for (let i = 0; i < n; i++) s += c[a[i] % c.length];
  } catch (e) {
    for (let i = 0; i < n; i++) s += c[Math.floor(Math.random() * c.length)];
  }
  return s;
}
function playerId() {
  try {
    let v = localStorage.getItem(PID_KEY);
    if (!v || !/^[a-z0-9]{12}$/.test(v)) { v = rand(12); localStorage.setItem(PID_KEY, v); }
    return v;
  } catch (e) { return rand(12); }
}
function cleanAge(a) {
  const n = parseInt(a, 10);
  return Number.isFinite(n) && n >= 3 && n <= 120 ? n : "";
}

export function createReporter({ enabled = true } = {}) {
  const pid = playerId();
  const sid = rand(12);
  const endpoint = () => (typeof window !== "undefined" && window.FEEDBACK_ENDPOINT) || "";
  const sent = [];

  function build(phase, S, R) {
    const ans = (arr) => (arr || []).map((r) => ({ id: uploadId(r.id), facet: r.facet, pick: r.pick, correct: !!r.correct }));
    const post = phase === "post";
    return {
      schema: SCHEMA,
      submitted_at: "",
      event: uploadEvent(S.grade),
      pid, sid, phase,
      grade: uploadGrade(S.grade), mode: "drive",
      client_time: new Date().toISOString(),
      age: cleanAge(S.age),
      gender: GENDER_SET.includes(S.gender) ? S.gender : "不透露",
      org: uploadOrg(S.role, S.org),
      hero: String(S.hero || "").slice(0, 20),
      pre: ans(S.pre),
      post: post ? ans(S.post) : [],
      preScore: (S.pre || []).filter((r) => r.correct).length,
      postSame3: post && R ? R.postSame : "",
      postScore: post && R ? R.postScore : "",
      stars: post ? S.stars.map((x) => Math.max(0, Math.min(3, x | 0))) : [],
      totalStars: post && R ? R.stars : "",
      facets: post && R ? R.facets : {},
      commit: post ? String(S.commit || "").slice(0, 80) : "",
      ua: String(navigator.userAgent || "").slice(0, 120),
    };
  }

  async function send(phase, S, R) {
    const rec = build(phase, S, R);
    sent.push(rec);
    const url = endpoint();
    if (!enabled || !url) return { ok: false, skipped: true };
    try {
      const r = await fetch(url, { method: "POST", headers: { "Content-Type": "text/plain;charset=UTF-8" },
        body: JSON.stringify(rec), keepalive: true });
      const j = await r.json().catch(() => ({}));
      if (!j.ok) console.warn("作答上傳未成功：", j.error || r.status);
      return j;
    } catch (e) {
      console.warn("作答上傳失敗（離線或中繼未啟用）", e);
      return { ok: false, error: String(e) };
    }
  }
  return { pid, sid, send, sent, build };
}
