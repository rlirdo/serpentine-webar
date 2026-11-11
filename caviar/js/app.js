// 晶球護衛隊：幻彩人工魚子醬大冒險——畫面流程（2.0：白色圓形觸控盤、三程度、圖例、分數表、目標指標）
// 開場 → 玩家資料（含身分）→ 主角與程度確認 → 圖例 → 前測 3 題（上傳 pre）→ 八關（對話→駕駛→結算→救出隊友）
// → 後測 5 題 → 行動承諾 → 結果（上傳 post）→ 回饋問卷
import * as C from "./content.js";
import { createSprites } from "./sprites.js";
import { createAudio } from "./audio.js";
import { createSpeech } from "./speech.js";
import { createPad } from "./pad.js";
import { createEngine, CFG, ITEM_LABEL } from "./engine.js";
import { HERO_IDS, heroFor, heroInfo, tierFor, badgesFor } from "./profile.js";
import { createReporter } from "./report.js";

// ---------------------------------------------------------------- 內容（代理 A 的 content.js；缺項時用後備值）
const { CREDIT, TITLE, TITLE_EN, STORE_KEY, PROFILE_NOTE, GENDERS, MATES, LEVELS, SAFETY, SAFETY_LEVELS, ENDING, FACETS, FACET_NAMES } = C;
const VERSION = C.VERSION || "2.0.0";
const TIERS = ["elem", "junior", "senior"];
const GRADE_LABEL = Object.assign({ elem: "初階", junior: "中階", senior: "高階" }, C.GRADE_LABEL && C.GRADE_LABEL.senior ? C.GRADE_LABEL : {});
const GRADE_DESC = Object.assign({ elem: "國小程度", junior: "國中・高中程度", senior: "大學・研究所程度" }, C.GRADE_DESC || {});
const ROLES = C.ROLES || ["國小學生", "國中學生", "高中職學生", "大學生", "研究生", "教師", "一般民眾"];
const CONTROL_HELP = C.CONTROL_HELP || "按住下方白色圓盤：按上半部往上、下半部往下、左邊往左、右邊往右；手指離開圓盤，主角就停下來。右上角的箭頭永遠指向下一個目標。隊伍有兩人以上時，每關可以按一次「和聲共振」。";
const OLD_CTRL = /方向盤|煞車/; // 舊版操作字樣（後備用）
const INTRO = (C.INTRO || []).map((t) => (typeof t === "string" && OLD_CTRL.test(t) ? "按住下面的白色圓盤，往哪邊按就往哪邊跑，一路救出八位夥伴吧！" : t));
const BANK = C.BANK || {};
const bankFor = (g) => BANK[g] || BANK.junior || BANK.elem || [];
const HAZ_LABEL = { haz_wave: "大浪", haz_fisheye: "魚眼結塊", haz_bubble: "氣泡", haz_mg: "鎂離子", haz_vapor: "水氣", haz_na: "鈉離子",
  haz_high: "太高的落點", haz_tail: "太低拖尾", haz_flat: "太高摔扁", haz_burst: "破球", haz_bottle: "塑膠瓶" };
const LEGEND = Array.isArray(C.LEGEND) && C.LEGEND.length === 8 ? C.LEGEND : CFG.map((cfg) => ({
  collect: (cfg.need ? Object.keys(cfg.need) : cfg.goods).map((k) => ({ sprite: k, name: ITEM_LABEL[k] || k })),
  bonus: cfg.bonus ? [{ sprite: cfg.bonus.type, name: ITEM_LABEL[cfg.bonus.type] || "加分物" }] : [],
  avoid: [...new Set(cfg.haz.map((h) => h.t))].map((k) => ({ sprite: k, name: HAZ_LABEL[k] || k })),
}));

const qs = new URLSearchParams(location.search);
const AUTOPLAY = qs.get("autoplay") === "1";
const AP_TIER = TIERS.includes(qs.get("tier")) ? qs.get("tier") : "elem";
const AP_FILL = { elem: { age: "10", role: "國小學生" }, junior: { age: "15", role: "高中職學生" }, senior: { age: "22", role: "大學生" } }[AP_TIER];
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const shuffle = (arr) => { const a = [...arr]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const sprites = createSprites("assets/");
const audio = createAudio();
const speech = createSpeech();
const reporter = createReporter({ enabled: !AUTOPLAY });
const engine = createEngine({ canvas: $("game"), sprites, onEvent: (e) => onGameEvent(e) });
const pad = createPad({ el: $("pad"), knob: $("padKnob"), audio });

const S = { grade: "elem", tier: "elem", age: "", gender: "", role: "", org: "", hero: "", badges: [], pre: [], post: [], stars: Array(8).fill(0),
  bonus: 0, commit: null, mates: [], level: -1, score: 0, levelScores: Array(8).fill(0) };
const T = (v) => (v && typeof v === "object" && !Array.isArray(v) ? v[S.grade] || v.junior || v.elem || "" : v);
const mateName = (i) => T(MATES[i].name);
const SCORE = { collect: 10, bonus: 20, hurt: -5, star: 30 };

// ---------------------------------------------------------------- 自動測試掛鉤
const AP = { screen: "boot", seq: 0, action: null, errors: [], levelTimes: [], playing: false, info: null, manual: false, hazStash: null };
function setScreen(name, action = null) { AP.screen = name; AP.seq++; AP.action = action; }
window.addEventListener("error", (e) => AP.errors.push(String(e.message || e)));
window.addEventListener("unhandledrejection", (e) => AP.errors.push(String(e.reason)));

// ---------------------------------------------------------------- 畫面工具
const screenEl = $("screen"), panelEl = $("panel");
function speakPanel(extra = "") {
  const parts = [...panelEl.querySelectorAll("[data-speak]")].map((el) => el.textContent.trim()).filter(Boolean);
  const text = [...parts, extra].filter(Boolean).join("\n");
  if (text) speech.speak(text, { kind: "panel" });
}
function show(html, { name, clear = false, action = null } = {}) {
  screenEl.classList.remove("hidden");
  screenEl.classList.toggle("clear", clear);
  panelEl.innerHTML = html;
  panelEl.scrollTop = 0;
  setScreen(name, action);
  speakPanel();
}
function hidePanel() { screenEl.classList.add("hidden"); panelEl.innerHTML = ""; }
function waitClick(el) { return new Promise((res) => el.addEventListener("click", () => { audio.play("tap"); res(el); }, { once: true })); }
function frame(name, scale, cls = "pix") { return sprites.toCanvas(name, scale, cls); }
function put(sel, canvas) { const el = panelEl.querySelector(sel); if (el) el.replaceWith(canvas); }

let toastTimer = 0, lastToastAt = 0;
function toast(text, { cls = "", speak = true, force = false } = {}) {
  const now = performance.now();
  if (!force && now - lastToastAt < 2200) return;
  lastToastAt = now;
  const el = $("toast");
  el.textContent = text;
  el.className = `toast show ${cls}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.className = "toast"; }, 2600);
  if (speak) speech.speak(text, { kind: "toast", mode: "queue" });
}

// ---------------------------------------------------------------- 系統鈕
function syncSys() {
  const m = $("muteBtn"), v = $("voiceBtn");
  m.textContent = audio.muted ? "🔇" : "🔊";
  m.classList.toggle("off", audio.muted);
  v.textContent = speech.enabled ? "🗣️ 語音開" : "🗣️ 語音關";
  v.classList.toggle("off", !speech.enabled);
}
$("muteBtn").addEventListener("click", () => { audio.toggle(); audio.play("tap"); syncSys(); });
$("voiceBtn").addEventListener("click", () => { speech.toggle(); audio.play("tap"); syncSys(); });
speech.onNoVoice(() => { if (speech.supported) toast("這台裝置沒有中文語音，請看畫面文字。", { speak: false, force: true }); });
syncSys();

// ---------------------------------------------------------------- 圖例
function legendItems(list, detail) {
  return (list || []).map((it) => detail
    ? `<div class="lg-det"><i class="lg-ic" data-sp="${esc(it.sprite)}"></i><div><b>${esc(T(it.name))}</b>${it.note ? `<span class="lg-note">${esc(T(it.note))}</span>` : ""}</div></div>`
    : `<span class="lg-item"><i class="lg-ic" data-sp="${esc(it.sprite)}"></i>${esc(T(it.name))}</span>`).join(detail ? "" : "、");
}
function legendBlock(i, detail = false) {
  const g = LEGEND[i] || {};
  const line = (cls, tag, list) => (list && list.length
    ? `<div class="lg-line ${cls}" data-speak><span class="lg-tag">${tag}</span><div class="lg-items">${legendItems(list, detail)}</div></div>` : "");
  return `${line("get", "要收集", g.collect)}${line("plus", "加分", g.bonus)}${line("avoid", "要避開", g.avoid)}`;
}
function fillLegendIcons() {
  panelEl.querySelectorAll("i.lg-ic").forEach((el) => {
    const c = frame(`${el.dataset.sp}_0`, 2, "pix lg-ic");
    el.replaceWith(c);
  });
}

// ---------------------------------------------------------------- HUD
function renderTeam() {
  const el = $("team");
  el.innerHTML = "";
  el.appendChild(frame(`hero_${S.hero}_0`, 1, "hero-head"));
  S.mates.forEach((m) => el.appendChild(frame(`mate_${m}_0`, 1, "mate-head")));
  S.badges.forEach((b) => { const s = document.createElement("span"); s.className = "badge"; s.style.background = b.color; s.textContent = b.label; el.appendChild(s); });
}
function renderLevels(i) {
  $("levels").innerHTML = LEVELS.map((L, k) => `<span class="${k < i ? "done" : k === i ? "now" : ""}">${k + 1}</span>`).join("");
}
function totalStars() { return S.stars.reduce((a, b) => a + b, 0); }
function renderScore() { $("scoreBoard").textContent = `第 ${Math.max(0, S.level) + 1} 關　累積 ${S.score} 分`; }
function updateHudH() {
  const top = document.querySelector(".hud-top");
  if (top && top.offsetHeight) $("hud").style.setProperty("--hud-h", `${top.offsetHeight}px`);
}
window.addEventListener("resize", updateHudH);
let lastHud = "";
function renderHud(st) {
  if (!st) return;
  const L = LEVELS[st.idx], cfg = CFG[st.idx];
  let text, frac;
  if (st.phase === "rescue") { text = `收集完成！去救出${mateName(st.idx)}`; frac = 1; }
  else if (st.phase === "done") { text = `救出${mateName(st.idx)}了！`; frac = 1; }
  else if (st.need) {
    text = Object.keys(st.need).map((k) => `${ITEM_LABEL[k].replace(" 粉", "")} ${st.per[k] || 0}/${st.need[k]}`).join("・");
    frac = st.count / st.goal;
  } else if (st.rounds) { text = `${T(L.goal)} 第 ${st.round}/${st.rounds} 輪・${st.count}/${st.goal}`; frac = st.count / st.goal; }
  else if (cfg.lattice) { text = `蛋盒空穴 已填 ${st.count}/${st.goal}`; frac = st.count / st.goal; }
  else { text = `${T(L.goal)} ${st.count}/${st.goal}`; frac = st.count / st.goal; }
  if (st.idx === 0 && st.bonus) text += `・垃圾 ${st.bonus}`;
  if (st.idx === 6 && st.bonus) text += `・硬球 ${st.bonus}`;
  const key = [text, frac, st.stars, st.idx, st.harmonyUsed, st.team, st.phase, totalStars(), S.score].join("|");
  if (key === lastHud) return;
  lastHud = key;
  $("goalText").textContent = text;
  $("goalFill").style.width = `${Math.round(frac * 100)}%`;
  $("lvlChip").textContent = T(L.name);
  renderScore();
  $("starsTotal").textContent = `★ ${totalStars()}`;
  const hearts = $("hearts");
  hearts.innerHTML = "";
  for (let k = 0; k < 3; k++) { const c = frame("ui_heart", 1); if (k >= st.stars) c.classList.add("off"); hearts.appendChild(c); }
  const lat = $("lattice");
  lat.classList.toggle("hidden", !cfg.lattice);
  if (cfg.lattice) { lat.innerHTML = '<span class="lat-label">蛋盒空穴</span>'; for (let k = 0; k < cfg.lattice; k++) lat.appendChild(frame(k < st.count ? "ui_lattice_full" : "ui_lattice_empty", 1)); }
  const hb = $("harmonyBtn");
  const can = st.team >= 2 && !st.harmonyUsed && st.phase === "collect";
  hb.disabled = !can;
  hb.classList.toggle("ready", can);
  updateHudH();
}

// 右上常駐目標指標：圓形底＋三角箭頭，指向最近的目標（目標在畫面內也顯示）
let ptrSprite = "", ptrAngle = NaN;
function updatePointer() {
  const el = $("pointer");
  const tg = engine.pointerTarget();
  el.classList.toggle("idle", !tg);
  if (!tg) return;
  el.classList.toggle("rescue", tg.kind === "rescue");
  const a = Math.atan2(tg.dy, tg.dx);
  if (Math.abs(a - ptrAngle) > 0.01) { ptrAngle = a; $("ptrArrow").style.transform = `rotate(${a.toFixed(3)}rad)`; }
  if (tg.sprite !== ptrSprite) {
    ptrSprite = tg.sprite;
    const box = $("ptrIcon");
    box.innerHTML = "";
    box.appendChild(frame(`${tg.sprite}_0`, 2));
  }
}

// ---------------------------------------------------------------- 遊戲事件與計分
let levelDone = null;
function addScore(n) { S.score = Math.max(0, S.score + n); }
function onGameEvent(e) {
  const L = LEVELS[e.state ? e.state.idx : 0];
  switch (e.type) {
    case "collect": addScore(SCORE.collect); audio.play("collect"); break;
    case "bonus": addScore(SCORE.bonus); audio.play("bonus"); toast(T(L.bonus) || "加分！", { cls: "good" }); break;
    case "hurt": addScore(SCORE.hurt); audio.play("hurt"); toast(T(L.haz), { cls: "warn", force: true }); break;
    case "stir": audio.play("good"); toast(T(L.stir) || "攪散了！", { cls: "good" }); break;
    case "round": audio.play("good"); toast(`${T(L.round)}（${e.round}/${CFG[e.state.idx].rounds}）`, { cls: "good", force: true }); break;
    case "goal": audio.play("star", 2); toast(`收集完成！快去救出${mateName(e.state.idx)}！`, { cls: "good", force: true }); break;
    case "harmony": audio.play("harmony"); toast("和聲共振！所有正確物件飛過來了！", { cls: "good", force: true }); break;
    case "rescued": audio.play("rescue"); S.mates.push(e.mate); renderTeam(); break;
    case "finish": if (levelDone) { const f = levelDone; levelDone = null; f(e); } break;
    default: break;
  }
  renderHud(e.state);
}
$("harmonyBtn").addEventListener("click", () => { engine.harmony(); });

// ---------------------------------------------------------------- 主迴圈
let lastT = performance.now();
let fpsAcc = 0, fpsN = 0, fps = 0;
function loop(now) {
  const dt = Math.min(0.05, (now - lastT) / 1000);
  lastT = now;
  fpsAcc += dt; fpsN++;
  if (fpsAcc >= 1) { fps = Math.round(fpsN / fpsAcc); fpsAcc = 0; fpsN = 0; }
  try {
    if (AP.playing) {
      if (AUTOPLAY) apTick(dt);
      pad.update(dt);
      engine.update(dt, pad.angle, !pad.active);
      updatePointer();
    }
    engine.render();
  } catch (err) { AP.errors.push(String(err && err.stack || err)); }
  requestAnimationFrame(loop);
}

function apTick() {
  if (AP.manual) { AP.info = { manual: true }; return AP.info; }
  const d = engine.apDecide();
  AP.info = d ? { target: d.target ? [Math.round(d.target.x), Math.round(d.target.y)] : null, dist: Math.round(d.dist || 0), circle: !!d.circle } : null;
  if (!d) { pad.setAuto(null); return AP.info; }
  if (d.harmony && !$("harmonyBtn").disabled) $("harmonyBtn").click();
  pad.setAuto(d.heading);
  return AP.info;
}

// ---------------------------------------------------------------- 各畫面
async function titleScreen() {
  const art = sprites.title ? `<img class="title-art" src="assets/title.png" alt="紅色液滴落入藍色鈣液、變成幻彩晶球的像素風標題圖">` : `<canvas class="title-art" id="titleArt" width="320" height="180"></canvas>`;
  show(`<div class="kicker">PIXEL SCIENCE GAME · 花蓮科普列車</div>
    ${art}
    <h1 data-speak>${TITLE}</h1>
    <div class="en">${TITLE_EN}</div>
    <p class="say small" data-speak>按住下方的白色圓盤，跟海藻小藻一起把褐藻變成會爆汁的幻彩晶球，救出八位夥伴！</p>
    <p class="note" data-speak>提醒：遊戲和實驗做出來的晶球都是實驗品，不可食用。</p>
    <div class="row"><button class="btn gold" id="go">▶ 開始遊戲</button></div>
    <p class="small">不記名・會有音效與語音導覽，可按右上角關閉。v${esc(VERSION)}</p>`, { name: "title", clear: true, action: () => $("go").click() });
  if (!sprites.title) drawTitleArt($("titleArt"));
  await waitClick($("go"));
  audio.unlock();
  speech.unlock();
  audio.bgm(8);
}
function drawTitleArt(c) {
  if (!c) return;
  const g = c.getContext("2d");
  g.imageSmoothingEnabled = false;
  for (let y = 0; y < 6; y++) for (let x = 0; x < 10; x++) sprites.draw(g, y < 3 ? "tile_s4_a" : "tile_s5_a", x * 32, y * 32);
  sprites.draw(g, "mate_1_0", 148, 96, { scale: 2 });
  sprites.draw(g, `hero_kid_f_0`, 90, 108, { scale: 2 });
  sprites.draw(g, `hero_adult_m_0`, 210, 108, { scale: 2, flip: true });
}

async function introScreen() {
  let n = 0;
  const html = () => `<div class="kicker">OPENING · 開場</div>
    <div class="speaker"><canvas id="spk"></canvas><div class="lines">${INTRO.slice(0, n + 1).map((t, k) => `<p ${k === n ? "data-speak" : ""}>${esc(T(t))}</p>`).join("")}</div></div>
    <div class="row"><button class="btn ghost" id="skip">跳過</button><button class="btn gold" id="next">${n + 1 < INTRO.length ? "下一句 ▶" : "我準備好了 ▶"}</button></div>`;
  for (;;) {
    show(html(), { name: `intro-${n + 1}`, action: () => $("next").click() });
    put("#spk", frame("mate_1_0", 3));
    const r = await Promise.race([waitClick($("next")).then(() => "next"), waitClick($("skip")).then(() => "skip")]);
    if (r === "skip" || ++n >= INTRO.length) break;
  }
}

async function profileScreen() {
  const fill = () => {
    $("age").value = AP_FILL.age;
    $("role").value = AP_FILL.role;
    panelEl.querySelector('[data-g="女"]').click();
    $("org").value = AP_TIER === "elem" ? "測試國小" : AP_TIER === "junior" ? "測試高中" : "東華大學";
    $("ok").click();
  };
  show(`<div class="kicker">PLAYER · 玩家資料</div>
    <h2 data-speak>先告訴我一點點關於你的事</h2>
    <p class="note" data-speak>${esc(T(PROFILE_NOTE))}</p>
    <div class="form">
      <label class="f" for="age">年齡<span class="req">必填</span></label>
      <input id="age" type="number" inputmode="numeric" min="3" max="120" placeholder="例如：10">
      <label class="f" for="role">身分<span class="req">必填</span></label>
      <select id="role"><option value="">請選擇身分</option>${ROLES.map((r) => `<option value="${esc(r)}">${esc(r)}</option>`).join("")}</select>
      <label class="f">性別<span class="req">必填</span></label>
      <div class="seg" id="gender">${GENDERS.map((g) => `<button type="button" data-g="${g}">${g}</button>`).join("")}</div>
      <label class="f" for="org">就讀學校或服務單位<span class="opt-tag">選填</span></label>
      <input id="org" type="text" maxlength="60" placeholder="例如：○○國小、○○公司、自由參加" autocomplete="off">
      <div class="err" id="err" role="alert"></div>
    </div>
    <div class="row"><button class="btn gold" id="ok">確定 ▶</button></div>`, { name: "profile", action: fill });
  let gender = "";
  panelEl.querySelectorAll("#gender button").forEach((b) => b.addEventListener("click", () => {
    gender = b.dataset.g;
    panelEl.querySelectorAll("#gender button").forEach((x) => x.classList.toggle("on", x === b));
    audio.play("tap");
  }));
  for (;;) {
    await waitClick($("ok"));
    const raw = $("age").value.trim();
    const age = parseInt(raw, 10);
    const role = $("role").value;
    const org = $("org").value.trim().slice(0, 60);
    let err = "";
    if (!raw || !/^[0-9]{1,3}$/.test(raw) || age < 3 || age > 120) err = "請輸入 3 到 120 之間的年齡數字。";
    else if (!ROLES.includes(role)) err = "請選擇你的身分。";
    else if (!gender) err = "請選一個性別選項（可以選不透露）。";
    if (err) {
      $("err").textContent = err; audio.play("bad"); speech.speak(err, { kind: "err" });
      setScreen("profile-err", fill);
      continue;
    }
    const tier = tierFor(age, role);
    Object.assign(S, { age, gender, role, org, tier, grade: tier, badges: badgesFor(org) });
    S.hero = heroFor(age, gender, org);
    speech.setGrade(S.grade);
    return;
  }
}

async function heroScreen() {
  let idx = HERO_IDS.indexOf(S.hero);
  if (idx < 0) idx = 0;
  const auto = idx;
  let cur = S.tier;
  for (;;) {
    const h = heroInfo(HERO_IDS[idx]);
    show(`<div class="kicker">HERO · 主角與程度確認</div>
      <h2 data-speak>${idx === auto ? "依照你的資料，主角是：" : "換一位主角："}</h2>
      <div class="hero-card"><canvas id="hc"></canvas><div>
        <div class="name" data-speak>${esc(h.name)}</div>
        <div class="say small" data-speak>${esc(h.intro)}</div>
        <div>${S.badges.map((b) => `<span class="badge" style="background:${b.color}">${esc(b.label)}</span>`).join("")}</div>
      </div></div>
      <div class="tier-box">
        <div class="tier-sug" data-speak>建議程度：${esc(GRADE_LABEL[S.tier])}（${esc(GRADE_DESC[S.tier])}）</div>
        <div class="small">題目和闖關說明會依程度調整，也可以自己改選：</div>
        <div class="seg tiers" id="tiers">${TIERS.map((g) => `<button type="button" data-t="${g}" class="${g === cur ? "on" : ""}"><b>${esc(GRADE_LABEL[g])}</b><small>${esc(GRADE_DESC[g]).replace(/・/g, "・<wbr>")}</small></button>`).join("")}</div>
      </div>
      <p class="small">可以按「換一位」，在 12 位主角之間切換（${idx + 1}/12）。</p>
      <div class="row"><button class="btn ghost" id="swap">換一位</button><button class="btn gold" id="ok">就決定是你 ▶</button></div>`,
    { name: "hero", action: () => $("ok").click() });
    put("#hc", frame(`hero_${h.id}_0`, 4));
    panelEl.querySelectorAll("#tiers button").forEach((b) => b.addEventListener("click", () => {
      cur = b.dataset.t;
      panelEl.querySelectorAll("#tiers button").forEach((x) => x.classList.toggle("on", x === b));
      audio.play("tap");
      speech.speak(`${GRADE_LABEL[cur]}，${GRADE_DESC[cur]}`, { kind: "toast" });
    }));
    const r = await Promise.race([waitClick($("ok")).then(() => "ok"), waitClick($("swap")).then(() => "swap")]);
    if (r === "ok") {
      S.hero = h.id;
      S.grade = cur;
      speech.setGrade(S.grade);
      return;
    }
    idx = (idx + 1) % HERO_IDS.length;
  }
}

async function legendScreen() {
  const pages = [[0, 1, 2, 3], [4, 5, 6, 7]];
  for (let p = 0; p < pages.length; p++) {
    show(`<div class="kicker">LEGEND · 圖例介紹 ${p + 1}/${pages.length}</div>
      <h2 data-speak>${p === 0 ? "出發前，先認識每一關要收集和要避開的東西" : "後面四關的圖例"}</h2>
      <div class="legend">${pages[p].map((i) => `<div class="lg-row"><div class="lg-head" data-speak>第 ${i + 1} 關　${esc(T(LEVELS[i].name))}</div>${legendBlock(i)}</div>`).join("")}</div>
      <div class="row"><button class="btn gold" id="next">${p + 1 < pages.length ? "下一頁 ▶" : "開始前測 ▶"}</button></div>`,
    { name: `legend-${p + 1}`, action: () => $("next").click() });
    fillLegendIcons();
    await waitClick($("next"));
  }
}

// ---------- 測驗 ----------
function askOne(kind, i, n, q) {
  return new Promise((resolve) => {
    const order = shuffle([0, 1, 2, 3]);
    const isPre = kind === "pre";
    show(`<div class="kicker">${isPre ? "前測" : "後測"} ${i + 1} / ${n}${isPre ? "・答錯沒關係" : ""}・${esc(GRADE_LABEL[S.grade])}</div>
      <div class="q"><span data-speak>${esc(T(q.q))}</span><span class="facet-chip">${FACET_NAMES[q.facet]}</span></div>
      <div class="opts">${order.map((o, k) => `<button class="opt" data-o="${o}" data-speak><b>${"ABCD"[k]}</b>${esc(T(q.options[o]))}</button>`).join("")}</div>
      <div class="after"></div>`, { name: `${kind}-q${i + 1}`, action: () => btns[0].click() });
    const btns = [...panelEl.querySelectorAll(".opt")];
    let done = false;
    btns.forEach((b) => b.addEventListener("click", () => {
      if (done) return;
      done = true;
      const o = Number(b.dataset.o);
      const correct = o === q.answer;
      (isPre ? S.pre : S.post).push({ id: q.id, facet: q.facet, pick: o, correct });
      if (isPre) {
        b.classList.add("picked");
        audio.play("tap");
        setScreen(`${kind}-q${i + 1}-picked`, null);
        setTimeout(resolve, 450);
      } else {
        btns.forEach((x) => { if (Number(x.dataset.o) === q.answer) x.classList.add("right"); });
        if (!correct) b.classList.add("wrong");
        audio.play(correct ? "good" : "bad");
        const after = panelEl.querySelector(".after");
        const ex = T(q.explain);
        after.innerHTML = `<div class="explain" data-speak>${correct ? "✔ 答對了！" : "✘ 再想想："}${esc(ex)}</div>
          <div class="row"><button class="btn gold nextq">${i + 1 < n ? "下一題 ▶" : "完成 ▶"}</button></div>`;
        speech.speak(`${correct ? "✔ 答對了！" : "✘ 再想想："}${ex}`, { kind: "explain" });
        const nb = after.querySelector(".nextq");
        nb.addEventListener("click", () => { audio.play("tap"); resolve(); }, { once: true });
        setScreen(`${kind}-q${i + 1}-explain`, () => nb.click());
      }
    }));
  });
}
async function quiz(kind) {
  const bank = bankFor(S.grade);
  const pre = bank.filter((q) => q.pre);
  let list = pre;
  if (kind === "post") {
    const act = shuffle(bank.filter((q) => !q.pre && q.facet === "行動"))[0];
    const other = shuffle(bank.filter((q) => !q.pre && q.facet !== "行動"))[0];
    list = [...pre, act, other].filter(Boolean);
  }
  for (let i = 0; i < list.length; i++) await askOne(kind, i, list.length, list[i]);
}

// ---------- 關卡 ----------
function curveSvg() {
  // 第 7 關：膜厚 δ∝√t 簡化示意（擴散控制；60 s 薄膜、180 s 二次熟化）
  const X = (sec) => 30 + sec * 1.3, Y = (sec) => 112 - Math.sqrt(sec) * 6.4;
  const pts = Array.from({ length: 41 }, (_, j) => { const sec = j * 5; return `${X(sec).toFixed(1)},${Y(sec).toFixed(1)}`; }).join(" ");
  return `<svg class="curve" viewBox="0 0 320 140" role="img" aria-label="膜厚隨浸泡時間變化的簡化示意曲線">
    <line x1="30" y1="112" x2="300" y2="112" stroke="#94a3b8" stroke-width="1"/>
    <line x1="30" y1="112" x2="30" y2="10" stroke="#94a3b8" stroke-width="1"/>
    <polyline points="${pts}" fill="none" stroke="#7ef0b4" stroke-width="3"/>
    <circle cx="${X(60)}" cy="${Y(60).toFixed(1)}" r="5" fill="#ff7a8a"/><circle cx="${X(180)}" cy="${Y(180).toFixed(1)}" r="5" fill="#ffd23a"/>
    <text x="${X(60) - 14}" y="${Y(60) + 20}" fill="#ffb0b8" font-size="12">60 秒</text><text x="${X(180) - 20}" y="${Y(180) + 20}" fill="#ffe08a" font-size="12">180 秒</text>
    <text x="36" y="22" fill="#cbd5e1" font-size="12">膜厚（簡化示意）</text><text x="236" y="132" fill="#cbd5e1" font-size="12">浸泡時間</text>
  </svg>`;
}

async function level(i) {
  const L = LEVELS[i];
  S.level = i;
  renderLevels(i);
  lastHud = "";
  engine.start(i, { heroId: S.hero, mates: S.mates.slice(), seed: i });
  $("hud").classList.remove("hidden");
  renderHud(engine.snapshot());
  // 關卡前對話（含本關圖例；第 1 關附操作說明）
  const first = i === 0;
  show(`<div class="kicker">STAGE ${i + 1} · ${esc(T(L.step))}</div>
    <h2 data-speak>第 ${i + 1} 關／${esc(T(L.name))}</h2>
    <div class="speaker"><canvas id="spk"></canvas><div class="lines">${L.intro.map((x) => `<p data-speak>${esc(T(x))}</p>`).join("")}</div></div>
    <div class="legend one">${legendBlock(i, true)}</div>
    <div class="rescued"><canvas id="mt"></canvas><div class="small" data-speak>這一關要救出：${esc(mateName(i))}。${esc(T(MATES[i].desc))}</div></div>
    ${first ? `<p class="note" data-speak>${esc(T(CONTROL_HELP))}</p>` : ""}
    <div class="row"><button class="btn gold" id="go">出發 ▶</button></div>`, { name: `L${i + 1}-intro`, action: () => $("go").click() });
  put("#spk", frame(i === 0 ? "mate_1_0" : `mate_${i}_0`, 3));
  put("#mt", frame(`mate_${i + 1}_0`, 2));
  fillLegendIcons();
  await waitClick($("go"));
  hidePanel();
  // 駕駛
  audio.bgm(i);
  const scoreAt = S.score;
  pad.angle = Math.PI / 2;
  pad.setEnabled(true);
  $("controls").classList.remove("hidden");
  $("pointer").classList.remove("hidden");
  ptrSprite = ""; ptrAngle = NaN;
  updateHudH();
  pad.layout();
  updatePointer();
  const t0 = performance.now();
  const fin = new Promise((res) => { levelDone = res; });
  AP.playing = true;
  setScreen(`L${i + 1}-play`, null);
  toast(`${T(L.goalToast) || `收集${T(L.goal)}`}，避開危險物！`, { force: true });
  const r = await fin;
  AP.playing = false;
  AP.manual = false;
  pad.setEnabled(false);
  $("controls").classList.add("hidden");
  $("pointer").classList.add("hidden");
  S.stars[i] = r.stars;
  S.bonus += r.bonus || 0;
  addScore(r.stars * SCORE.star);
  const lvScore = S.score - scoreAt;
  S.levelScores[i] = lvScore;
  AP.levelTimes.push({ level: i + 1, seconds: Math.round((performance.now() - t0) / 100) / 10, hits: r.hits, stars: r.stars, bonus: r.bonus,
    score: lvScore, total: S.score, before: scoreAt });
  lastHud = "";
  renderHud(engine.snapshot());
  // 結算
  audio.bgm(8);
  for (let k = 0; k < r.stars; k++) setTimeout(() => audio.play("star", k), 250 + k * 200);
  const safe = SAFETY_LEVELS.includes(i);
  show(`<div class="kicker">STAGE ${i + 1} CLEAR · 結算</div>
    <h2 data-speak>第 ${i + 1} 關完成！得到 ${r.stars} 顆星</h2>
    <div class="stars-row">${[0, 1, 2].map((k) => `<canvas class="st${k}"></canvas>`).join("")}</div>
    <div class="score-sum"><div data-speak><span>本關得分</span><b>${lvScore} 分</b></div><div data-speak><span>累積總分</span><b>${S.score} 分</b></div></div>
    <p class="small">計分：收集 1 個 +10、加分物 +20、碰到危險物 −5、過關再加 星數×30（本關 +${r.stars * SCORE.star}）。</p>
    ${r.hits ? `<p class="small" data-speak>這關碰到危險物 ${r.hits} 次。</p>` : `<p class="small" data-speak>完全沒碰到危險物，太厲害了！</p>`}
    ${L.bonusLabel && r.bonus ? `<p class="small" data-speak>你還撿到 ${r.bonus} 個${esc(T(L.bonusLabel))}！</p>` : ""}
    <div class="rescued"><canvas id="mt"></canvas><div data-speak>救出${esc(mateName(i))}，加入隊伍！</div></div>
    ${i === 6 ? curveSvg() : ""}
    <p class="learn" data-speak>學到什麼：${esc(T(L.learn))}</p>
    <span class="tip" data-speak>🌱 環境小語：${esc(T(L.tip))}</span>
    ${safe ? `<div class="honesty" data-speak>安全提醒：${esc(T(SAFETY))}</div>` : ""}
    <div class="row"><button class="btn gold" id="go">${i < 7 ? "下一關 ▶" : "前往後測 ▶"}</button></div>`, { name: `L${i + 1}-done`, action: () => $("go").click() });
  [0, 1, 2].forEach((k) => put(`.st${k}`, frame(k < r.stars ? "ui_star_on" : "ui_star_off", 3)));
  put("#mt", frame(`mate_${i + 1}_0`, 2));
  await waitClick($("go"));
}

// ---------- 行動承諾、結果 ----------
async function commitment() {
  const commits = ENDING.commits.map((c) => T(c));
  show(`<div class="kicker">ACTION · 行動承諾</div>
    <div class="q" data-speak>${esc(T(ENDING.commitAsk))}</div>
    <div class="opts">${commits.map((c, i) => `<button class="opt" data-i="${i}" data-speak><b>${i + 1}</b>${esc(c)}</button>`).join("")}</div>`,
  { name: "commit", action: () => panelEl.querySelector(".opt").click() });
  const b = await Promise.race([...panelEl.querySelectorAll(".opt")].map((x) => waitClick(x)));
  S.commit = commits[Number(b.dataset.i)];
  b.classList.add("picked");
  setScreen("commit-picked", null);
  await sleep(400);
}
function computeResult() {
  const preIds = S.pre.map((r) => r.id);
  const preScore = S.pre.filter((r) => r.correct).length;
  const postSame = S.post.filter((r) => preIds.includes(r.id) && r.correct).length;
  const postScore = S.post.filter((r) => r.correct).length;
  const facets = {};
  FACETS.forEach((f) => {
    const rs = S.post.filter((r) => r.facet === f);
    let v = rs.length ? rs.filter((r) => r.correct).length / rs.length : 0;
    if (f === "行動") v = (v + (S.commit ? 1 : 0)) / 2;
    if (f === "探究") v = (v + Math.min(1, S.stars[7] / 3)) / 2; // 第 8 關星數（沿用既有算法）
    facets[f] = Math.round(v * 100);
  });
  return { preScore, postSame, postScore, facets, stars: totalStars(), score: S.score };
}
function saveRecord(R) {
  try {
    const arr = JSON.parse(localStorage.getItem(STORE_KEY) || "[]");
    arr.push({ time: new Date().toISOString(), grade: S.grade, tier: S.tier, role: S.role, age: S.age, gender: S.gender, hero: S.hero, stars: S.stars, totalStars: R.stars,
      score: S.score, levelScores: S.levelScores, preScore: R.preScore, postSame3: R.postSame, postScore: R.postScore, facets: R.facets, commit: S.commit, autoplay: AUTOPLAY });
    while (arr.length > 200) arr.shift();
    localStorage.setItem(STORE_KEY, JSON.stringify(arr));
  } catch (e) { /* 無痕模式 */ }
}
function showResult() {
  const R = computeResult();
  saveRecord(R);
  reporter.send("post", S, R);
  $("hud").classList.add("hidden");
  audio.bgmStop();
  audio.play("fanfare");
  const d = new Date();
  const date = `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")}`;
  const bar = (v, max, color) => `<div class="track"><i style="width:${Math.round((v / max) * 100)}%;background:${color}"></i></div>`;
  const h = heroInfo(S.hero);
  show(`<div class="kicker">RESULT · 結果</div>
    <div class="cert">
      <div class="team-photo"><canvas id="hc"></canvas><div id="mates" class="mate-row"></div></div>
      <h2 data-speak>晶球護衛隊任務完成！</h2>
      <div class="big" data-speak>總分 ${S.score} 分</div>
      <div class="small" data-speak>★ ${R.stars} / 24・程度：${esc(GRADE_LABEL[S.grade])}（${esc(GRADE_DESC[S.grade])}）</div>
      <p class="small">${date}・主角：${esc(h.name)}</p>
      <p class="small">各關得分：${S.levelScores.map((v, k) => `第${k + 1}關 ${v}`).join("、")}</p>
      <p class="small">我的小行動：${esc(S.commit || "—")}</p>
      <p class="small">${CREDIT}</p>
    </div>
    <div class="sec-title">前測 → 後測（同樣 3 題）</div>
    <div class="cmp">
      <span>前測</span>${bar(R.preScore, 3, "#94a3b8")}<b data-speak>前測 ${R.preScore} / 3</b>
      <span>後測</span>${bar(R.postSame, 3, "#2e7d5b")}<b data-speak>後測 ${R.postSame} / 3</b>
      <span>後測全部</span>${bar(R.postScore, 5, "#1c7293")}<b>${R.postScore} / 5</b>
    </div>
    <div class="sec-title">四個面向</div>
    <div class="cmp">${FACETS.map((f) => `<span>${FACET_NAMES[f]}</span>${bar(R.facets[f], 100, { 知識: "#1c7293", 態度: "#2e7d5b", 行動: "#c99a3e", 探究: "#ef6c3c" }[f])}<b>${R.facets[f]}%</b>`).join("")}</div>
    <div class="honesty" data-speak>${esc(T(ENDING.safety))}</div>
    <p class="small">可以截圖保存。作答結果會以不記名方式上傳作研究統計。</p>
    <div class="row"><a class="btn gold" id="fb" href="feedback/">📝 填回饋問卷</a><button class="btn alt" id="again">再玩一次</button></div>`, { name: "result", action: null });
  put("#hc", frame(`hero_${S.hero}_0`, 3));
  const mc = $("mates");
  S.mates.forEach((m) => mc.appendChild(frame(`mate_${m}_0`, 2)));
  $("again").addEventListener("click", () => location.reload());
  return R;
}

// ---------------------------------------------------------------- 主流程
async function run() {
  try {
    setScreen("loading", null);
    await Promise.race([sprites.load(), sleep(4000)]);
    requestAnimationFrame(loop);
    await titleScreen();
    await introScreen();
    await profileScreen();
    await heroScreen();
    renderTeam();
    await legendScreen();
    await quiz("pre");
    reporter.send("pre", S);
    for (let i = 0; i < 8; i++) await level(i);
    $("hud").classList.add("hidden");
    show(`<div class="kicker">POST TEST · 後測</div><p class="say" data-speak>${esc(T(ENDING.postIntro))}</p>
      <div class="row"><button class="btn gold" id="go">開始後測 ▶</button></div>`, { name: "post-intro", action: () => $("go").click() });
    await waitClick($("go"));
    await quiz("post");
    await commitment();
    window.__result = showResult();
  } catch (e) {
    console.error(e);
    AP.errors.push(String(e && e.stack || e));
    show(`<p class="say" data-speak>糟糕，出了一點問題，請重新整理頁面再試一次。</p>`, { name: "error" });
  }
}

// ---------------------------------------------------------------- __ap
function vis(el) { const s = getComputedStyle(el); return s.display !== "none" && s.visibility !== "hidden" && el.getClientRects().length > 0; }
const keyOf = (s) => String(s || "").replace(/[^0-9A-Za-z㐀-鿿]/g, "");
const rectOf = (el) => { const r = el.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)]; };
const inViewRect = (r) => r.left >= 0 && r.right <= innerWidth + 0.5 && r.top >= 0 && r.bottom <= innerHeight + 0.5;
const overlap = (a, b) => !(a.right <= b.left || a.left >= b.right || a.bottom <= b.top || a.top >= b.bottom);
if (AUTOPLAY) {
  window.__ap = {
    get ready() { return AP.screen !== "boot" && AP.screen !== "loading"; },
    get errors() { return AP.errors; },
    get levelTimes() { return AP.levelTimes; },
    get fps() { return fps; },
    state() { return { screen: AP.screen, seq: AP.seq, waiting: !!AP.action, playing: AP.playing, level: S.level, hud: engine.snapshot(), sprites: sprites.source, ap: AP.info, score: S.score }; },
    info() {
      return { version: VERSION, apTier: AP_TIER, grade: S.grade, tier: S.tier, role: S.role, hasSenior: !!BANK.senior, legendN: Array.isArray(C.LEGEND) ? C.LEGEND.length : 0,
        hasControlHelp: !!C.CONTROL_HELP, hasRoles: !!C.ROLES, bankIds: bankFor(S.grade).map((q) => q.id) };
    },
    step() {
      if (AP.playing) return apTick(1 / 15);
      const a = AP.action;
      if (!a) return false;
      AP.action = null;
      a();
      return true;
    },
    reporter: () => reporter.sent,
    // 測試用：把主角移到第一個危險物上，驗證扣血、說明提示與語音
    forceHit() {
      const L = engine.level;
      if (!L || !L.haz.length || L.phase === "done") return false;
      const z = L.haz.reduce((a, b) => (Math.hypot(b.x - L.hero.x, b.y - L.hero.y) < Math.hypot(a.x - L.hero.x, a.y - L.hero.y) ? b : a));
      L.hero.x = z.x; L.hero.y = z.y; L.hero.inv = 0;
      return z.type;
    },
    // 真實觸控測試用：暫停自動駕駛（並暫時移走危險物，避免被撞退干擾位置量測）
    manual(on) {
      AP.manual = !!on;
      pad.setAuto(null);
      const L = engine.level;
      if (!L) return false;
      if (on) {
        if (!AP.hazStash) { AP.hazStash = L.haz; L.haz = []; }
        L.hero.kbx = 0; L.hero.kby = 0; L.hero.slow = 0;
        L.hero.x = L.map.W / 2; L.hero.y = L.map.H / 2; // 置中，避免碰到地圖邊界
      } else if (AP.hazStash) { L.haz = AP.hazStash; AP.hazStash = null; }
      return true;
    },
    heroPos() { const L = engine.level; return L ? { x: L.hero.x, y: L.hero.y, active: pad.active } : null; },
    padRect() { const r = $("pad").getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2, r: r.width / 2 }; },
    toast: () => { const t = document.querySelector("#toast.show"); return t ? t.textContent : ""; },
    S: () => JSON.parse(JSON.stringify(S)),
    speechCheck() {
      const log = (window.__speech && window.__speech.log) || [];
      const pieces = [];
      if (!screenEl.classList.contains("hidden")) panelEl.querySelectorAll("[data-speak]").forEach((el) => { if (vis(el) && keyOf(el.textContent)) pieces.push({ kind: "panel", text: el.textContent }); });
      const t = document.querySelector("#toast.show");
      if (t && keyOf(t.textContent)) pieces.push({ kind: "toast", text: t.textContent });
      const keys = log.map((e) => keyOf(e.raw));
      const missing = pieces.filter((p) => !keys.some((k) => k.includes(keyOf(p.text))));
      return { pieces: pieces.length, missing: missing.map((p) => ({ kind: p.kind, text: p.text.trim().slice(0, 40) })), logLen: log.length };
    },
    check() {
      const out = { credit: false, creditTop: false, overflow: [], btnOverlap: [] };
      const c = $("credit");
      if (c) {
        const r = c.getBoundingClientRect();
        const cs = getComputedStyle(c);
        out.credit = c.textContent.trim() === CREDIT && r.width > 0 && cs.visibility !== "hidden" && cs.display !== "none"
          && r.right <= innerWidth + 0.5 && r.bottom <= innerHeight + 0.5 && r.left >= 0 && r.top >= 0;
        out.creditTop = Number(cs.zIndex) >= 2147483647;
        out.creditRect = rectOf(c);
        out.btnOverlap = [...document.querySelectorAll("button, .btn, #pad, #pointer")].filter((b) => {
          if (!vis(b)) return false;
          const q0 = b.getBoundingClientRect();
          const q = { left: q0.left, right: q0.right, top: q0.top, bottom: q0.bottom };
          for (let p = b.parentElement; p; p = p.parentElement) {
            const ov = getComputedStyle(p).overflowY;
            if (ov === "auto" || ov === "scroll" || ov === "hidden") {
              const pr = p.getBoundingClientRect();
              q.top = Math.max(q.top, pr.top); q.bottom = Math.min(q.bottom, pr.bottom);
              q.left = Math.max(q.left, pr.left); q.right = Math.min(q.right, pr.right);
            }
          }
          if (q.bottom <= q.top || q.right <= q.left) return false;
          return overlap(q, r);
        }).map((b) => (b.id || b.textContent.trim()).slice(0, 20));
      }
      document.querySelectorAll("[data-speak], .btn, .opt, .lvl-chip, .goal-text, .toast.show, .icon-btn, .ctl, .seg button, .cmp span, .cmp b, .score-board, .ptr-label, .lg-head, .lg-line, .tier-sug").forEach((el) => {
        if (!vis(el)) return;
        const r = el.getBoundingClientRect();
        const scroller = el.closest(".panel");
        const inScroll = scroller && scroller.scrollHeight > scroller.clientHeight + 1;
        const outX = r.left < -0.5 || r.right > innerWidth + 0.5;
        const outY = !inScroll && (r.top < -0.5 || r.bottom > innerHeight + 0.5);
        const clipped = el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).overflowX !== "visible";
        if (outX || outY || clipped) out.overflow.push({ cls: String(el.className || el.tagName), text: el.textContent.trim().slice(0, 24), rect: rectOf(el), clipped });
      });
      const sysR = $("sys").getBoundingClientRect();
      const p = $("pad");
      out.pad = vis(p) ? (() => { const r = p.getBoundingClientRect(); return { visible: true, size: Math.round(r.width), inView: inViewRect(r), rect: rectOf(p) }; })() : { visible: false };
      const pt = $("pointer");
      out.pointer = vis(pt) && !$("hud").classList.contains("hidden") ? (() => {
        const r = pt.getBoundingClientRect();
        const toastEl = document.querySelector("#toast.show");
        return { visible: true, inView: inViewRect(r), rect: rectOf(pt), overSys: overlap(r, sysR), overHud: overlap(r, document.querySelector(".hud-top").getBoundingClientRect()),
          overToast: toastEl ? overlap(r, toastEl.getBoundingClientRect()) : false, overPad: vis(p) ? overlap(r, p.getBoundingClientRect()) : false,
          hasIcon: !!$("ptrIcon").querySelector("canvas"), angle: ptrAngle };
      })() : { visible: false };
      const sb = $("scoreBoard");
      out.score = vis(sb) && !$("hud").classList.contains("hidden") ? (() => {
        const r = sb.getBoundingClientRect();
        return { visible: true, text: sb.textContent, inView: inViewRect(r), rect: rectOf(sb), overSys: overlap(r, sysR), left: r.left < innerWidth / 2 && r.top < 80 };
      })() : { visible: false };
      return out;
    },
  };
}

run();
