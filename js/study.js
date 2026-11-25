// 研究用整份 10 題測驗的共用邏輯（2026/11/25）：對照班測驗頁 test/test.js 與遊戲研究模式（game.js，?study=1）共用。
// 題目順序固定 1→10、選項洗牌、作答時不顯示對錯、態度題不計分（correct=null）、上傳 schema webar-test-v1。
// 對照班 group=control（mode=test）；遊戲班 group=game（mode=ar|play，後測另帶八關星數）。
// 狀態與補傳佇列存在 localStorage；無痕模式或被封鎖時退回記憶體，流程照常。
// 不蒐集姓名、學號、性別；pid 與遊戲共用 serpentineWebAR.pid（本裝置隨機 12 碼）。
import { BANK, ENDING } from "./content.js";

export const SCHEMA = "webar-test-v1";
export const N = 10;
export const ATTITUDE = "態度";
export const DEFAULT_EVENT = { control: "CTRL-TEST", game: "STUDY-GAME" };
export const STATE_KEY = { control: "serpentineWebAR.ctrlTest.state.v1", game: "serpentineWebAR.studyGame.state.v1" };
const PID_KEY = "serpentineWebAR.pid";                 // 與 js/report.js 相同
const QUEUE_KEY = "serpentineWebAR.study.queue.v1";    // 兩組共用一個補傳佇列
const OLD_QUEUE_KEY = "serpentineWebAR.ctrlTest.queue.v1";

export const shuffle = (arr) => { const a = [...arr]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
export function rand(n) {
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

// ---------- localStorage ----------
const mem = {};
export const store = {
  get(k) { try { const v = localStorage.getItem(k); return v === null ? (mem[k] ?? null) : v; } catch (e) { return mem[k] ?? null; } },
  set(k, v) { mem[k] = v; try { localStorage.setItem(k, v); } catch (e) { /* 記憶體保底 */ } },
  del(k) { delete mem[k]; try { localStorage.removeItem(k); } catch (e) { /* 略過 */ } },
};
export const readJSON = (k, d) => { try { const v = store.get(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } };

export function playerId(fresh = false) {
  let v = store.get(PID_KEY);
  if (fresh || !v || !/^[a-z0-9]{12}$/.test(v)) { v = rand(12); store.set(PID_KEY, v); }
  return v;
}

// ---------- 網址參數：?grade=elem|junior（沿用遊戲既有參數名）、?event=活動代碼、?study=1（遊戲研究模式） ----------
export function readParams(search = location.search) {
  const p = new URLSearchParams(search);
  return {
    study: p.get("study") === "1",
    grade: ["elem", "junior"].includes(p.get("grade")) ? p.get("grade") : "",
    event: /^[A-Za-z0-9_-]{1,40}$/.test(p.get("event") || "") ? p.get("event") : "",
  };
}

// ---------- 狀態 ----------
export const loadState = (group) => { const s = readJSON(STATE_KEY[group], null); return s && typeof s === "object" && s.stage ? s : null; };
export const saveState = (group, st) => store.set(STATE_KEY[group], JSON.stringify(st));
export const clearState = (group) => store.del(STATE_KEY[group]);
export const makeOrders = () => Array.from({ length: N }, () => shuffle([0, 1, 2, 3]));

/** 新的一次作答（前測從第 1 題開始） */
export function newSession(group, { grade, event, mode }) {
  const st = {
    group, stage: "pre", grade, event: event || DEFAULT_EVENT[group],
    mode: group === "control" ? "test" : (mode === "ar" ? "ar" : "play"),
    pid: playerId(), sid: rand(12), startedAt: new Date().toISOString(),
    pre: [], post: [], orders: { pre: makeOrders(), post: [] }, commitPick: null,
  };
  if (group === "game") { st.stars = Array(8).fill(0); st.restarts = 0; }
  saveState(group, st);
  return st;
}
/** 進入後測：選項重新洗牌 */
export function startPost(st) {
  if (!st.orders.post || st.orders.post.length !== N) st.orders.post = makeOrders();
  st.post = [];
  st.stage = "post";
}

// ---------- 題目與計分 ----------
export const questions = (grade) => BANK[grade];
export const isScored = (q) => q.facet !== ATTITUDE;
export const maxScore = (grade) => questions(grade).filter(isScored).length; // 8
export const scoreOf = (list) => list.filter((a) => a.correct === true).length;
/** 一題作答紀錄：pick 為題庫原始選項索引；態度題 correct=null */
export const answer = (q, pick) => ({ id: q.id, facet: q.facet, pick, correct: isScored(q) ? pick === q.answer : null });
/** 下一題的題目與洗牌順序；做完回傳 null */
export function nextQuestion(st, phase) {
  const i = st[phase].length;
  if (i >= N) return null;
  return { i, q: questions(st.grade)[i], order: st.orders[phase][i] };
}

// ---------- 上傳紀錄（欄位與 Code.gs TEST_FIELDS 一致） ----------
export function buildRecord(st, phase) {
  const ans = (arr) => arr.map((a) => ({ id: a.id, facet: a.facet, pick: a.pick, correct: a.correct }));
  const post = phase === "post";
  const game = st.group === "game";
  const stars = game && post ? st.stars.slice() : [];
  return {
    schema: SCHEMA, submitted_at: "", event: st.event, group: st.group,
    pid: st.pid, sid: st.sid, phase, grade: st.grade, mode: game ? st.mode : "test",
    client_time: new Date().toISOString(),
    pre: ans(st.pre), post: post ? ans(st.post) : [],
    preScore: scoreOf(st.pre), postScore: post ? scoreOf(st.post) : "", maxScore: maxScore(st.grade),
    stars, totalStars: stars.length ? stars.reduce((a, b) => a + b, 0) : "",
    restarts: game ? (st.restarts || 0) : "",
    commit: post ? String(ENDING.commits[st.commitPick] || "").slice(0, 80) : "",
    commitPick: post ? st.commitPick : "",
    ua: String(navigator.userAgent || "").slice(0, 120),
  };
}

// ---------- 補傳佇列 ----------
function migrateOldQueue() {
  const old = readJSON(OLD_QUEUE_KEY, null);
  if (!Array.isArray(old)) return;
  if (old.length) store.set(QUEUE_KEY, JSON.stringify([...readJSON(QUEUE_KEY, []), ...old]));
  store.del(OLD_QUEUE_KEY);
}
migrateOldQueue();
export const queue = () => readJSON(QUEUE_KEY, []);
const setQueue = (q) => store.set(QUEUE_KEY, JSON.stringify(q));
export function enqueue(rec) {
  const q = queue().filter((x) => !(x.rec.sid === rec.sid && x.rec.phase === rec.phase)); // 同一次同階段只留最新
  q.push({ rec, tries: 0, lastError: "" });
  setQueue(q);
}

let flushing = false;
const listeners = new Set();
export const net = { lastOk: null };
export const onNetChange = (fn) => { listeners.add(fn); fn(status()); };
export const status = () => ({ pending: queue().length, lastOk: net.lastOk });
const notify = () => listeners.forEach((fn) => fn(status()));

/** 依序送出佇列；成功（中繼回 ok:true）才移出，失敗留著下次再送 */
export async function flush() {
  if (flushing) return;
  const url = String((typeof window !== "undefined" && window.FEEDBACK_ENDPOINT) || "").trim();
  const q = queue();
  if (!q.length) { notify(); return; }
  if (!url) { net.lastOk = false; notify(); return; }
  flushing = true;
  for (const item of q) {
    let ok = false, err = "";
    try {
      // text/plain 避免 CORS preflight（同 js/report.js）
      const r = await fetch(url, { method: "POST", headers: { "Content-Type": "text/plain;charset=UTF-8" },
        body: JSON.stringify(item.rec), keepalive: true });
      const j = await r.json().catch(() => ({}));
      ok = j.ok === true;
      if (!ok) err = String(j.error || `HTTP ${r.status}`);
    } catch (e) { err = String(e && e.message ? e.message : e); }
    const cur = queue(); // 重讀再改，避免和同時新加入的紀錄互相覆蓋
    const idx = cur.findIndex((x) => x.rec.sid === item.rec.sid && x.rec.phase === item.rec.phase && x.rec.client_time === item.rec.client_time);
    if (ok) { if (idx >= 0) cur.splice(idx, 1); }
    else if (idx >= 0) { cur[idx].tries += 1; cur[idx].lastError = err.slice(0, 120); console.warn("作答上傳未成功，已存在本機：", err); }
    setQueue(cur);
    net.lastOk = ok;
  }
  flushing = false;
  notify();
  if (queue().some((x) => x.tries === 0)) setTimeout(flush, 0); // 送的途中又有新紀錄進來
}

let autoInstalled = false;
/** 開頁補傳＋回到線上／回到前景時補傳＋每 30 秒重試 */
export function installAutoFlush() {
  if (autoInstalled) return;
  autoInstalled = true;
  window.addEventListener("online", flush);
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") flush(); });
  setInterval(() => { if (queue().length) flush(); }, 30000);
  flush();
}
/** 遊戲研究模式：補傳＋以 hud.toast 提示上傳狀態（失敗時「已先存在這支手機」，補傳成功時「已上傳」） */
export function installStudyUpload(hud) {
  let prev = null;
  onNetChange((s) => {
    const key = `${s.pending}|${s.lastOk}`;
    if (key === prev) return;
    const first = prev === null;
    prev = key;
    if (s.pending && s.lastOk === false) hud.toast(netText(s), { warn: true, ms: 5000, speak: false });
    else if (!first && !s.pending && s.lastOk === true) hud.toast("✔ 作答已上傳。", { ms: 2500, speak: false });
  });
  installAutoFlush();
}
export const netText = (s) => (s.pending ? `📱 有 ${s.pending} 筆作答已先存在這支手機，連上網路後會自動補傳。` : s.lastOk === true ? "✔ 作答已上傳。" : "");
