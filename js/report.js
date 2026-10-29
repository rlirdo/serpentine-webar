// 前後測作答匿名上傳（2026/10/29 新增，schema webar-game-v1）
// 流程：前測做完→送一筆 phase=pre；整局結束→送一筆 phase=post（含前測＋後測＋星數）。
// 中繼網址取自 feedback/config.js 的 window.FEEDBACK_ENDPOINT（與回饋問卷共用同一個 Apps Script）。
// 不蒐集姓名、學號、email；pid 只是本裝置隨機產生的 12 碼代碼，用來在撈取端判斷 30 分鐘內重複作答。
// 任何失敗（離線、中繼未部署、無痕模式）都靜默略過，絕不影響遊戲流程。
const PID_KEY = "serpentineWebAR.pid";
const SCHEMA = "webar-game-v1";
const EVENT = "SEET2026-A155-07";

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
  } catch (e) { return rand(12); } // 無痕模式：每次載入新代碼
}

export function createReporter({ mode, enabled = true } = {}) {
  const pid = playerId();
  const sid = rand(12);
  const endpoint = () => (typeof window !== "undefined" && window.FEEDBACK_ENDPOINT) || "";
  const sent = [];

  function build(phase, S, R) {
    const ans = (arr) => (arr || []).map((r) => ({ id: r.id, facet: r.facet, pick: r.pick, correct: !!r.correct }));
    const post = phase === "post";
    return {
      schema: SCHEMA,
      submitted_at: "",        // 由中繼以伺服器時間填入
      event: EVENT,
      pid, sid, phase,
      grade: S.grade, mode: mode || "play",
      client_time: new Date().toISOString(),
      pre: ans(S.pre),
      post: post ? ans(S.post) : [],
      preScore: (S.pre || []).filter((r) => r.correct).length,
      postSame3: post && R ? R.postSame : "",
      postScore: post && R ? R.postScore : "",
      stars: post ? S.stars.slice() : [],
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
      // text/plain 避免 CORS preflight；keepalive 讓結果頁被關掉時也能送完
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
