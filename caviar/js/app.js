// 晶球護衛隊：幻彩人工魚子醬大冒險——畫面流程（由墨玉護衛隊 app.js 改寫）
// 開場 → 玩家資料 → 主角確認 → 前測 3 題（上傳 pre）→ 八關（對話→駕駛→結算→救出隊友）→ 後測 5 題 → 行動承諾 → 結果（上傳 post）→ 回饋問卷
import { CREDIT, TITLE, TITLE_EN, VERSION, STORE_KEY, INTRO, PROFILE_NOTE, GENDERS, MATES, LEVELS, SAFETY, SAFETY_LEVELS,
  ENDING, FACETS, FACET_NAMES, BANK, GRADE_LABEL } from "./content.js";
import { createSprites } from "./sprites.js";
import { createAudio } from "./audio.js";
import { createSpeech } from "./speech.js";
import { createWheel } from "./wheel.js";
import { createEngine, CFG, ITEM_LABEL, starsFor } from "./engine.js";
import { HERO_IDS, heroFor, heroInfo, gradeFor, badgesFor } from "./profile.js";
import { createReporter } from "./report.js";

const qs = new URLSearchParams(location.search);
const AUTOPLAY = qs.get("autoplay") === "1";
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const shuffle = (arr) => { const a = [...arr]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const sprites = createSprites("assets/");
const audio = createAudio();
const speech = createSpeech();
const reporter = createReporter({ enabled: !AUTOPLAY });
const engine = createEngine({ canvas: $("game"), sprites, onEvent: (e) => onGameEvent(e) });
const wheel = createWheel({ canvas: $("wheel"), brakeBtn: $("brakeBtn"), sprites, audio });

const S = { grade: "elem", age: "", gender: "", org: "", hero: "", badges: [], pre: [], post: [], stars: Array(8).fill(0),
  bonus: 0, commit: null, mates: [], level: -1 };
const T = (v) => (v && typeof v === "object" ? v[S.grade] || v.elem : v);

// ---------------------------------------------------------------- 自動測試掛鉤
const AP = { screen: "boot", seq: 0, action: null, errors: [], levelTimes: [], playing: false, info: null };
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

// ---------------------------------------------------------------- HUD
function renderTeam() {
  const el = $("team");
  el.innerHTML = "";
  const hc = frame(`hero_${S.hero}_0`, 1, "hero-head");
  el.appendChild(hc);
  S.mates.forEach((m) => el.appendChild(frame(`mate_${m}_0`, 1, "mate-head")));
  S.badges.forEach((b) => { const s = document.createElement("span"); s.className = "badge"; s.style.background = b.color; s.textContent = b.label; el.appendChild(s); });
}
function renderLevels(i) {
  $("levels").innerHTML = LEVELS.map((L, k) => `<span class="${k < i ? "done" : k === i ? "now" : ""}">${k + 1}</span>`).join("");
}
function totalStars() { return S.stars.reduce((a, b) => a + b, 0); }
let lastHud = "";
function renderHud(st) {
  if (!st) return;
  const L = LEVELS[st.idx], cfg = CFG[st.idx];
  let text, frac;
  if (st.phase === "rescue") { text = `收集完成！去救出${MATES[st.idx].name}`; frac = 1; }
  else if (st.phase === "done") { text = `救出${MATES[st.idx].name}了！`; frac = 1; }
  else if (st.need) {
    text = Object.keys(st.need).map((k) => `${ITEM_LABEL[k].replace(" 粉", "")} ${st.per[k] || 0}/${st.need[k]}`).join("・");
    frac = st.count / st.goal;
  } else if (st.rounds) { text = `${L.goal} 第 ${st.round}/${st.rounds} 輪・${st.count}/${st.goal}`; frac = st.count / st.goal; }
  else if (cfg.lattice) { text = `蛋盒空穴 已填 ${st.count}/${st.goal}`; frac = st.count / st.goal; }
  else { text = `${L.goal} ${st.count}/${st.goal}`; frac = st.count / st.goal; }
  if (st.idx === 0 && st.bonus) text += `・垃圾 ${st.bonus}`;
  if (st.idx === 6 && st.bonus) text += `・硬球 ${st.bonus}`;
  const key = [text, frac, st.stars, st.idx, st.harmonyUsed, st.team, st.phase, totalStars()].join("|");
  if (key === lastHud) return;
  lastHud = key;
  $("goalText").textContent = text;
  $("goalFill").style.width = `${Math.round(frac * 100)}%`;
  $("lvlChip").textContent = `第 ${st.idx + 1} 關／${L.name}`;
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
}

// ---------------------------------------------------------------- 遊戲事件
let levelDone = null;
function onGameEvent(e) {
  const L = LEVELS[e.state ? e.state.idx : 0];
  switch (e.type) {
    case "collect": audio.play("collect"); break;
    case "bonus": audio.play("bonus"); toast(L.bonus || "加分！", { cls: "good" }); break;
    case "hurt": audio.play("hurt"); toast(L.haz, { cls: "warn", force: true }); break;
    case "stir": audio.play("good"); toast(L.stir || "攪散了！", { cls: "good" }); break;
    case "round": audio.play("good"); toast(`${L.round}（${e.round}/${CFG[e.state.idx].rounds}）`, { cls: "good", force: true }); break;
    case "goal": audio.play("star", 2); toast(`收集完成！快去救出${MATES[e.state.idx].name}！`, { cls: "good", force: true }); break;
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
      wheel.update(dt);
      engine.update(dt, wheel.angle, wheel.brake);
    }
    engine.render();
  } catch (err) { AP.errors.push(String(err && err.stack || err)); }
  requestAnimationFrame(loop);
}

function apTick(dt) {
  const d = engine.apDecide();
  AP.info = d ? { target: d.target ? [Math.round(d.target.x), Math.round(d.target.y)] : null, dist: Math.round(d.dist || 0), circle: !!d.circle } : null;
  if (!d) return AP.info;
  if (d.harmony && !$("harmonyBtn").disabled) $("harmonyBtn").click();
  if (d.circle) wheel.rotateBy(4.2 * dt);
  else wheel.steerTo(d.heading, dt, 7);
  return AP.info;
}

// ---------------------------------------------------------------- 各畫面
async function titleScreen() {
  const art = sprites.title ? `<img class="title-art" src="assets/title.png" alt="紅色液滴落入藍色鈣液、變成幻彩晶球的像素風標題圖">` : `<canvas class="title-art" id="titleArt" width="320" height="180"></canvas>`;
  show(`<div class="kicker">PIXEL SCIENCE GAME · 花蓮科普列車</div>
    ${art}
    <h1 data-speak>${TITLE}</h1>
    <div class="en">${TITLE_EN}</div>
    <p class="say small" data-speak>握住方向盤，跟海藻小藻一起把褐藻變成會爆汁的幻彩晶球，救出八位夥伴！</p>
    <p class="note" data-speak>提醒：遊戲和實驗做出來的晶球都是實驗品，不可食用。</p>
    <div class="row"><button class="btn gold" id="go">▶ 開始遊戲</button></div>
    <p class="small">不記名・會有音效與語音導覽，可按右上角關閉。v${VERSION}</p>`, { name: "title", clear: true, action: () => $("go").click() });
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
    <div class="speaker"><canvas id="spk"></canvas><div class="lines">${INTRO.slice(0, n + 1).map((t, k) => `<p ${k === n ? "data-speak" : ""}>${esc(t)}</p>`).join("")}</div></div>
    <div class="row"><button class="btn ghost" id="skip">跳過</button><button class="btn gold" id="next">${n + 1 < INTRO.length ? "下一句 ▶" : "我準備好了 ▶"}</button></div>`;
  for (;;) {
    show(html(), { name: `intro-${n + 1}`, action: () => $("next").click() });
    put("#spk", frame("mate_1_0", 3));
    const r = await Promise.race([waitClick($("next")).then(() => "next"), waitClick($("skip")).then(() => "skip")]);
    if (r === "skip" || ++n >= INTRO.length) break;
  }
}

async function profileScreen() {
  show(`<div class="kicker">PLAYER · 玩家資料</div>
    <h2 data-speak>先告訴我一點點關於你的事</h2>
    <p class="note" data-speak>${PROFILE_NOTE}</p>
    <div class="form">
      <label class="f" for="age">年齡<span class="req">必填</span></label>
      <input id="age" type="number" inputmode="numeric" min="3" max="120" placeholder="例如：10">
      <label class="f">性別<span class="req">必填</span></label>
      <div class="seg" id="gender">${GENDERS.map((g) => `<button type="button" data-g="${g}">${g}</button>`).join("")}</div>
      <label class="f" for="org">就讀學校或服務單位<span class="opt-tag">選填</span></label>
      <input id="org" type="text" maxlength="60" placeholder="例如：○○國小、○○公司、自由參加" autocomplete="off">
      <div class="err" id="err" role="alert"></div>
    </div>
    <div class="row"><button class="btn gold" id="ok">確定 ▶</button></div>`, {
    name: "profile",
    action: () => {
      $("age").value = "10";
      panelEl.querySelector('[data-g="女"]').click();
      $("org").value = "測試國小";
      $("ok").click();
    },
  });
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
    const org = $("org").value.trim().slice(0, 60);
    let err = "";
    if (!raw || !/^[0-9]{1,3}$/.test(raw) || age < 3 || age > 120) err = "請輸入 3 到 120 之間的年齡數字。";
    else if (!gender) err = "請選一個性別選項（可以選不透露）。";
    if (err) {
      $("err").textContent = err; audio.play("bad"); speech.speak(err, { kind: "err" });
      setScreen("profile-err", () => { $("age").value = "10"; panelEl.querySelector('[data-g="女"]').click(); $("ok").click(); });
      continue;
    }
    Object.assign(S, { age, gender, org, grade: gradeFor(age, org), badges: badgesFor(org) });
    S.hero = heroFor(age, gender, org);
    speech.setGrade(S.grade);
    return;
  }
}

async function heroScreen() {
  let idx = HERO_IDS.indexOf(S.hero);
  const auto = idx;
  for (;;) {
    const h = heroInfo(HERO_IDS[idx]);
    show(`<div class="kicker">HERO · 主角確認</div>
      <h2 data-speak>${idx === auto ? "依照你的資料，主角是：" : "換一位主角："}</h2>
      <div class="hero-card"><canvas id="hc"></canvas><div>
        <div class="name" data-speak>${esc(h.name)}</div>
        <div class="say small" data-speak>${esc(h.intro)}</div>
        <div>${S.badges.map((b) => `<span class="badge" style="background:${b.color}">${esc(b.label)}</span>`).join("")}</div>
      </div></div>
      <p class="small">可以按「換一位」，在 12 位主角之間切換（${idx + 1}/12）。</p>
      <div class="row"><button class="btn ghost" id="swap">換一位</button><button class="btn gold" id="ok">就決定是你 ▶</button></div>`,
    { name: "hero", action: () => $("ok").click() });
    put("#hc", frame(`hero_${h.id}_0`, 4));
    const r = await Promise.race([waitClick($("ok")).then(() => "ok"), waitClick($("swap")).then(() => "swap")]);
    if (r === "ok") { S.hero = h.id; return; }
    idx = (idx + 1) % HERO_IDS.length;
  }
}

// ---------- 測驗 ----------
function askOne(kind, i, n, q) {
  return new Promise((resolve) => {
    const order = shuffle([0, 1, 2, 3]);
    const isPre = kind === "pre";
    show(`<div class="kicker">${isPre ? "前測" : "後測"} ${i + 1} / ${n}${isPre ? "・答錯沒關係" : ""}</div>
      <div class="q"><span data-speak>${esc(q.q)}</span><span class="facet-chip">${FACET_NAMES[q.facet]}</span></div>
      <div class="opts">${order.map((o, k) => `<button class="opt" data-o="${o}" data-speak><b>${"ABCD"[k]}</b>${esc(q.options[o])}</button>`).join("")}</div>
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
        after.innerHTML = `<div class="explain" data-speak>${correct ? "✔ 答對了！" : "✘ 再想想："}${esc(q.explain)}</div>
          <div class="row"><button class="btn gold nextq">${i + 1 < n ? "下一題 ▶" : "完成 ▶"}</button></div>`;
        speech.speak(`${correct ? "✔ 答對了！" : "✘ 再想想："}${q.explain}`, { kind: "explain" });
        const nb = after.querySelector(".nextq");
        nb.addEventListener("click", () => { audio.play("tap"); resolve(); }, { once: true });
        setScreen(`${kind}-q${i + 1}-explain`, () => nb.click());
      }
    }));
  });
}
async function quiz(kind) {
  const bank = BANK[S.grade];
  const pre = bank.filter((q) => q.pre);
  let list = pre;
  if (kind === "post") {
    const act = shuffle(bank.filter((q) => !q.pre && q.facet === "行動"))[0];
    const other = shuffle(bank.filter((q) => !q.pre && q.facet !== "行動"))[0];
    list = [...pre, act, other];
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
  renderHud(engine.snapshot());
  $("hud").classList.remove("hidden");
  // 關卡前對話
  const first = i === 0;
  show(`<div class="kicker">STAGE ${i + 1} · ${esc(L.step)}</div>
    <h2 data-speak>第 ${i + 1} 關／${esc(L.name)}</h2>
    <div class="speaker"><canvas id="spk"></canvas><div class="lines">${L.intro.map((x) => `<p data-speak>${esc(T(x))}</p>`).join("")}</div></div>
    <div class="rescued"><canvas id="mt"></canvas><div class="small" data-speak>這一關要救出：${MATES[i].name}。${MATES[i].desc}</div></div>
    ${first ? `<p class="note" data-speak>按住下面的方向盤左右轉，金色指針指到哪裡，主角就往哪裡跑；右下角按住「煞車」可以停下來。隊伍有兩人以上時，每關可以按一次「和聲共振」。</p>` : ""}
    <div class="row"><button class="btn gold" id="go">出發 ▶</button></div>`, { name: `L${i + 1}-intro`, action: () => $("go").click() });
  put("#spk", frame(i === 0 ? "mate_1_0" : `mate_${i}_0`, 3));
  put("#mt", frame(`mate_${i + 1}_0`, 2));
  await waitClick($("go"));
  hidePanel();
  // 駕駛
  audio.bgm(i);
  wheel.angle = Math.PI / 2;
  wheel.setEnabled(true);
  $("controls").classList.remove("hidden");
  wheel.layout();
  const t0 = performance.now();
  const fin = new Promise((res) => { levelDone = res; });
  AP.playing = true;
  setScreen(`L${i + 1}-play`, null);
  toast(`${L.goalToast || `收集${L.goal}`}，避開危險物！`, { force: true });
  const r = await fin;
  AP.playing = false;
  wheel.setEnabled(false);
  $("controls").classList.add("hidden");
  AP.levelTimes.push({ level: i + 1, seconds: Math.round((performance.now() - t0) / 100) / 10, hits: r.hits, stars: r.stars, bonus: r.bonus });
  S.stars[i] = r.stars;
  S.bonus += r.bonus || 0;
  renderHud(engine.snapshot());
  // 結算
  audio.bgm(8);
  for (let k = 0; k < r.stars; k++) setTimeout(() => audio.play("star", k), 250 + k * 200);
  const safe = SAFETY_LEVELS.includes(i);
  show(`<div class="kicker">STAGE ${i + 1} CLEAR · 結算</div>
    <h2 data-speak>第 ${i + 1} 關完成！得到 ${r.stars} 顆星</h2>
    <div class="stars-row">${[0, 1, 2].map((k) => `<canvas class="st${k}"></canvas>`).join("")}</div>
    ${r.hits ? `<p class="small" data-speak>這關碰到危險物 ${r.hits} 次。</p>` : `<p class="small" data-speak>完全沒碰到危險物，太厲害了！</p>`}
    ${L.bonusLabel && r.bonus ? `<p class="small" data-speak>你還撿到 ${r.bonus} 個${esc(L.bonusLabel)}！</p>` : ""}
    <div class="rescued"><canvas id="mt"></canvas><div data-speak>救出${MATES[i].name}，加入隊伍！</div></div>
    ${i === 6 ? curveSvg() : ""}
    <p class="learn" data-speak>學到什麼：${esc(T(L.learn))}</p>
    <span class="tip" data-speak>🌱 環境小語：${esc(L.tip)}</span>
    ${safe ? `<div class="honesty" data-speak>安全提醒：${SAFETY}</div>` : ""}
    <div class="row"><button class="btn gold" id="go">${i < 7 ? "下一關 ▶" : "前往後測 ▶"}</button></div>`, { name: `L${i + 1}-done`, action: () => $("go").click() });
  [0, 1, 2].forEach((k) => put(`.st${k}`, frame(k < r.stars ? "ui_star_on" : "ui_star_off", 3)));
  put("#mt", frame(`mate_${i + 1}_0`, 2));
  await waitClick($("go"));
}

// ---------- 行動承諾、結果 ----------
async function commitment() {
  show(`<div class="kicker">ACTION · 行動承諾</div>
    <div class="q" data-speak>${ENDING.commitAsk}</div>
    <div class="opts">${ENDING.commits.map((c, i) => `<button class="opt" data-i="${i}" data-speak><b>${i + 1}</b>${esc(c)}</button>`).join("")}</div>`,
  { name: "commit", action: () => panelEl.querySelector(".opt").click() });
  const b = await Promise.race([...panelEl.querySelectorAll(".opt")].map((x) => waitClick(x)));
  S.commit = ENDING.commits[Number(b.dataset.i)];
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
  return { preScore, postSame, postScore, facets, stars: totalStars() };
}
function saveRecord(R) {
  try {
    const arr = JSON.parse(localStorage.getItem(STORE_KEY) || "[]");
    arr.push({ time: new Date().toISOString(), grade: S.grade, age: S.age, gender: S.gender, hero: S.hero, stars: S.stars, totalStars: R.stars,
      preScore: R.preScore, postSame3: R.postSame, postScore: R.postScore, facets: R.facets, commit: S.commit, autoplay: AUTOPLAY });
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
      <div class="big" data-speak>★ ${R.stars} / 24</div>
      <p class="small">${date}・${GRADE_LABEL[S.grade]}・主角：${esc(h.name)}</p>
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
    <div class="honesty" data-speak>${ENDING.safety}</div>
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
    await quiz("pre");
    reporter.send("pre", S);
    for (let i = 0; i < 8; i++) await level(i);
    $("hud").classList.add("hidden");
    show(`<div class="kicker">POST TEST · 後測</div><p class="say" data-speak>${ENDING.postIntro}</p>
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
if (AUTOPLAY) {
  window.__ap = {
    get ready() { return AP.screen !== "boot" && AP.screen !== "loading"; },
    get errors() { return AP.errors; },
    get levelTimes() { return AP.levelTimes; },
    get fps() { return fps; },
    state() { return { screen: AP.screen, seq: AP.seq, waiting: !!AP.action, playing: AP.playing, level: S.level, hud: engine.snapshot(), sprites: sprites.source, ap: AP.info }; },
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
        out.creditRect = [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)];
        out.btnOverlap = [...document.querySelectorAll("button, .btn, #wheel")].filter((b) => {
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
          return !(q.right <= r.left || q.left >= r.right || q.bottom <= r.top || q.top >= r.bottom);
        }).map((b) => (b.id || b.textContent.trim()).slice(0, 20));
      }
      document.querySelectorAll("[data-speak], .btn, .opt, .lvl-chip, .goal-text, .toast.show, .icon-btn, .ctl, .seg button, .cmp span, .cmp b").forEach((el) => {
        if (!vis(el)) return;
        const r = el.getBoundingClientRect();
        const scroller = el.closest(".panel");
        const inScroll = scroller && scroller.scrollHeight > scroller.clientHeight + 1;
        const outX = r.left < -0.5 || r.right > innerWidth + 0.5;
        const outY = !inScroll && (r.top < -0.5 || r.bottom > innerHeight + 0.5);
        const clipped = el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).overflowX !== "visible";
        if (outX || outY || clipped) out.overflow.push({ cls: String(el.className || el.tagName), text: el.textContent.trim().slice(0, 24), rect: [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)], clipped });
      });
      const w = $("wheel");
      out.wheel = vis(w) ? (() => { const r = w.getBoundingClientRect(); return { visible: true, size: Math.round(r.width), inView: r.left >= 0 && r.right <= innerWidth && r.top >= 0 && r.bottom <= innerHeight }; })() : { visible: false };
      return out;
    },
  };
}

run();
