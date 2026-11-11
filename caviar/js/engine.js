// Canvas 2D 俯視引擎（晶球護衛隊沿用墨玉護衛隊引擎；只改 CFG／ITEM_LABEL／地圖裝飾）：32 px 地磚地圖、鏡頭跟隨、實體、碰撞、隊友環繞吸附、和聲共振、自動駕駛（autoplay）。白色圓盤操作：brake＝手指不在圓盤上（停止）。
// 世界座標＝1× 像素；繪製時以整數倍 zoom 放大（devicePixelRatio 納入），imageSmoothingEnabled=false。
import { wrap } from "./pad.js";

const TILE = 32;
const TAU = Math.PI * 2;
// 晶球護衛隊八關（機制沿用墨玉護衛隊引擎：goal／need／locked=stir／lattice／rounds／bonus／sea）
export const CFG = [
  { tiles: 1, goal: 12, goods: ["item_kelp"], maxOn: 5, bonus: { type: "item_trash", n: 4 }, haz: [{ t: "haz_wave", n: 4, move: "wave", speed: 70 }], sea: 3 },
  { tiles: 2, goal: 6, goods: ["item_powder"], maxOn: 3, locked: true, haz: [{ t: "haz_fisheye", n: 5, move: "drift", speed: 25, slow: true }] },
  { tiles: 3, goal: 9, need: { item_h2o: 5, item_powder: 4 }, maxOn: 5, haz: [{ t: "haz_bubble", n: 6, move: "drift", speed: 30 }] },
  { tiles: 4, goal: 12, goods: ["item_ca"], maxOn: 5, haz: [{ t: "haz_mg", n: 5, move: "drift", speed: 30 }, { t: "haz_vapor", n: 3, move: "drift", speed: 18 }] },
  { tiles: 5, goal: 6, goods: ["item_ca"], maxOn: 4, haz: [{ t: "haz_na", n: 6, move: "drift", speed: 30 }, { t: "haz_high", n: 2, move: "static" }], lattice: 6 },
  { tiles: 6, goal: 9, goods: ["item_drop"], maxOn: 4, haz: [{ t: "haz_tail", n: 4, move: "drift", speed: 26 }, { t: "haz_flat", n: 3, move: "bounce", speed: 60 }] },
  { tiles: 7, goal: 10, goods: ["item_bead"], maxOn: 5, rounds: 2, perRound: 5, bonus: { type: "item_hard", n: 3 }, haz: [{ t: "haz_burst", n: 5, move: "drift", speed: 22 }] },
  { tiles: 8, goal: 12, need: { item_cell: 3, item_ink: 3, item_filter: 3, item_pack: 3 }, maxOn: 5, haz: [{ t: "haz_bottle", n: 5, move: "static" }] },
];
export const ITEM_LABEL = {
  item_kelp: "褐藻", item_trash: "塑膠垃圾", item_powder: "粉末", item_h2o: "水分子", item_ca: "Ca²⁺", item_drop: "液滴",
  item_bead: "晶球", item_hard: "硬球", item_cell: "細胞膜", item_ink: "墨水", item_filter: "淨水", item_pack: "包裝",
};
export function starsFor(hits) { return hits === 0 ? 3 : hits <= 2 ? 2 : hits <= 4 ? 1 : 0; }

function rngOf(seed) { let s = (seed * 2654435761) >>> 0 || 7; return () => { s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; }; }

export function createEngine({ canvas, sprites, onEvent = () => {} }) {
  const ctx = canvas.getContext("2d", { alpha: false });
  let cssW = 0, cssH = 0, dpr = 1, zoom = 1, viewW = 0, viewH = 0;
  let L = null; // 目前關卡狀態
  let t = 0;
  const rand = Math.random;

  function resize() {
    cssW = innerWidth; cssH = innerHeight;
    dpr = Math.min(3, window.devicePixelRatio || 1);
    canvas.width = Math.round(cssW * dpr);
    canvas.height = Math.round(cssH * dpr);
    canvas.style.width = cssW + "px";
    canvas.style.height = cssH + "px";
    const ratio = Math.max(1, Math.min(2, Math.min(cssW, cssH) / 240));
    zoom = Math.max(1, Math.round(dpr * ratio));
    viewW = canvas.width / zoom; viewH = canvas.height / zoom;
  }
  window.addEventListener("resize", resize);
  resize();

  // ---------- 地圖預繪 ----------
  function buildMap(idx, cfg) {
    const cols = 26, rows = 26;
    const W = cols * TILE, H = rows * TILE;
    const off = document.createElement("canvas");
    off.width = W; off.height = H;
    const g = off.getContext("2d");
    g.imageSmoothingEnabled = false;
    const r = rngOf(idx + 3);
    const s = cfg.tiles;
    for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) {
      const edge = x === 0 || y === 0 || x === cols - 1 || y === rows - 1;
      let k = edge ? "c" : r() < 0.1 ? "b" : "a";
      if (!edge && cfg.sea && y <= cfg.sea) k = "b";
      sprites.draw(g, `tile_s${s}_${k}`, x * TILE, y * TILE);
    }
    const cx = W / 2, cy = H / 2;
    g.save();
    if (idx === 0) { // 海浪線
      g.fillStyle = "rgba(255,255,255,.55)";
      for (let x = TILE; x < W - TILE; x += 4) g.fillRect(x, (cfg.sea + 1) * TILE + Math.round(Math.sin(x / 18) * 3), 3, 2);
    } else if (idx === 1) { // 攪拌漩渦
      g.strokeStyle = "rgba(255,230,200,.22)"; g.lineWidth = 2;
      for (let k = 0; k < 3; k++) { g.beginPath(); for (let a = 0; a < 18; a += 0.05) { const rr = 10 + a * 18; g.lineTo(cx + Math.cos(a + k * 2.1) * rr, cy + Math.sin(a + k * 2.1) * rr); } g.stroke(); }
    } else if (idx === 2) { // 熱水蒸氣
      g.strokeStyle = "rgba(255,255,255,.18)"; g.lineWidth = 2;
      for (let k = 0; k < 14; k++) { const sx = TILE + r() * (W - 2 * TILE), sy = TILE + r() * (H - 2 * TILE); g.beginPath(); for (let j = 0; j < 30; j++) g.lineTo(sx + Math.sin(j / 4) * 5, sy - j * 2); g.stroke(); }
    } else if (idx === 3) { // 鈣液亮點
      g.fillStyle = "rgba(200,235,255,.30)";
      for (let k = 0; k < 120; k++) { const bx = TILE + r() * (W - 2 * TILE), by = TILE + r() * (H - 2 * TILE); g.fillRect(bx, by, 2, 2); }
    } else if (idx === 4) { // 蛋盒格線＋滴管
      g.strokeStyle = "rgba(255,255,255,.12)"; g.lineWidth = 2;
      for (let x = TILE * 2; x < W - TILE; x += TILE * 3) { g.beginPath(); for (let y = TILE; y < H - TILE; y += 4) g.lineTo(x + Math.sin(y / 20) * 6, y); g.stroke(); }
      g.fillStyle = "rgba(201,154,62,.6)"; g.fillRect(TILE, TILE * 3, W - 2 * TILE, 6);
    } else if (idx === 5) { // 高度尺（3 cm 標線）
      g.strokeStyle = "rgba(255,255,255,.22)"; g.lineWidth = 2;
      for (let y = TILE * 2; y < H - TILE; y += TILE * 2) { g.beginPath(); g.moveTo(TILE, y); g.lineTo(TILE + 18, y); g.stroke(); g.beginPath(); g.moveTo(W - TILE - 18, y); g.lineTo(W - TILE, y); g.stroke(); }
    } else if (idx === 6) { // 計時圈
      g.strokeStyle = "rgba(255,255,255,.20)"; g.lineWidth = 2;
      for (let rr = 40; rr < W / 2; rr += 64) { g.beginPath(); g.arc(cx, cy, rr, 0, TAU); g.stroke(); }
    } else if (idx === 7) { // 展館光帶
      g.strokeStyle = "rgba(255,215,140,.25)"; g.lineWidth = 2;
      for (let k = 0; k < 4; k++) { g.beginPath(); for (let x = TILE; x < W - TILE; x += 4) g.lineTo(x, TILE * (4 + k * 6) + Math.sin(x / 50 + k) * 10); g.stroke(); }
    }
    g.restore();
    return { off, W, H, cols, rows };
  }

  // ---------- 關卡 ----------
  function start(idx, { heroId, mates = [], seed = 0 }) {
    const cfg = CFG[idx];
    const map = buildMap(idx, cfg);
    t = 0;
    L = {
      idx, cfg, map, heroId,
      hero: { x: map.W / 2, y: map.H / 2, heading: Math.PI / 2, speed: 125, kbx: 0, kby: 0, inv: 0, slow: 0, walk: 0, flip: false, lastH: Math.PI / 2 },
      mates: mates.map((m, i) => ({ id: m, ang: (i / Math.max(1, mates.length)) * TAU, x: 0, y: 0 })),
      goods: [], haz: [], fx: [], texts: [], rescue: null,
      count: 0, per: {}, bonus: 0, hits: 0, round: 0, roundGot: 0,
      phase: "collect", harmonyUsed: false, doneAt: 0, finished: false,
      brake: false, ap: { target: null, since: 0, ban: new Map() }, seed,
    };
    if (cfg.need) Object.keys(cfg.need).forEach((k) => { L.per[k] = 0; });
    // 危險物（離主角起點 ≥140）
    for (const h of cfg.haz) {
      for (let k = 0; k < h.n; k++) {
        let x, y;
        if (h.move === "ring") {
          const a = (k / h.n) * TAU + 0.25, rr = k % 2 ? 150 : 250;
          x = map.W / 2 + Math.cos(a) * rr; y = map.H / 2 + Math.sin(a) * rr;
        } else {
          let tries = 0;
          do { x = TILE * 1.5 + rand() * (map.W - TILE * 3); y = TILE * 1.5 + rand() * (map.H - TILE * 3); tries++; }
          while (tries < 50 && Math.hypot(x - L.hero.x, y - L.hero.y) < 140);
        }
        if (h.move === "wave") { y = TILE * (cfg.sea + 2) + rand() * (map.H - TILE * (cfg.sea + 4)); }
        const [w] = sprites.size(h.t);
        const a = rand() * TAU, sp = h.speed || 0;
        L.haz.push({ type: h.t, move: h.move, x, y, r: w >= 24 ? 11 : 8, vx: h.move === "wave" ? (k % 2 ? sp : -sp) : Math.cos(a) * sp, vy: h.move === "wave" ? 0 : Math.sin(a) * sp, sp, slow: !!h.slow, ph: rand() * TAU });
      }
    }
    if (cfg.bonus) for (let k = 0; k < cfg.bonus.n; k++) spawnGood(cfg.bonus.type, true);
    if (cfg.rounds) L.round = 1;
    fillGoods();
    emit("progress");
  }

  function emit(type, extra = {}) { onEvent({ type, ...extra, state: snapshot() }); }
  function snapshot() {
    if (!L) return null;
    return { idx: L.idx, count: L.count, goal: L.cfg.goal, per: { ...L.per }, need: L.cfg.need || null, bonus: L.bonus, hits: L.hits,
      stars: starsFor(L.hits), phase: L.phase, round: L.round, rounds: L.cfg.rounds || 0, harmonyUsed: L.harmonyUsed,
      team: 1 + L.mates.length, onMap: L.goods.filter((g) => !g.bonus).length };
  }

  function freeSpot(minR, maxR) {
    const { W, H } = L.map;
    for (let tries = 0; tries < 80; tries++) {
      const a = rand() * TAU, rr = minR + rand() * (maxR - minR);
      const x = L.hero.x + Math.cos(a) * rr, y = L.hero.y + Math.sin(a) * rr;
      if (x < TILE + 14 || y < TILE + 14 || x > W - TILE - 14 || y > H - TILE - 14) continue;
      if (L.cfg.sea && y < TILE * (L.cfg.sea + 1.5)) continue;
      if (L.haz.some((h) => Math.hypot(h.x - x, h.y - y) < h.r + 30)) continue;
      if (L.goods.some((g) => Math.hypot(g.x - x, g.y - y) < 26)) continue;
      return [x, y];
    }
    return [L.hero.x + 60, L.hero.y];
  }
  function spawnGood(type, bonus = false) {
    const [x, y] = bonus ? freeSpot(80, 280) : freeSpot(60, 190);
    L.goods.push({ type, x, y, r: 9, bonus, pull: false, locked: !bonus && !!L.cfg.locked, stir: 0, born: t, ph: rand() * TAU });
  }
  function neededTypes() {
    const cfg = L.cfg;
    if (cfg.need) {
      const out = [];
      for (const [k, n] of Object.entries(cfg.need)) {
        const left = n - (L.per[k] || 0) - L.goods.filter((g) => g.type === k).length;
        for (let i = 0; i < left; i++) out.push(k);
      }
      return out;
    }
    return null;
  }
  function fillGoods() {
    if (L.phase !== "collect") return;
    const cfg = L.cfg;
    const on = L.goods.filter((g) => !g.bonus).length;
    let remain;
    if (cfg.rounds) remain = cfg.perRound - L.roundGot - on;
    else remain = cfg.goal - L.count - on;
    let room = Math.min(cfg.maxOn - on, remain);
    if (cfg.need) {
      const pool = neededTypes();
      while (room-- > 0 && pool.length) spawnGood(pool.splice(Math.floor(rand() * pool.length), 1)[0]);
      return;
    }
    while (room-- > 0) spawnGood(cfg.goods[0]);
  }

  function puff(x, y, color, n = 10, sp = 60) {
    for (let k = 0; k < n; k++) { const a = rand() * TAU, v = sp * (0.4 + rand()); L.fx.push({ x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, life: 0.5 + rand() * 0.3, color }); }
  }
  function floatText(x, y, text, color = "#ffe08a") { L.texts.push({ x, y, text, color, life: 0.9 }); }

  function collect(g) {
    L.goods.splice(L.goods.indexOf(g), 1);
    if (g.bonus) {
      L.bonus++;
      puff(g.x, g.y, "#bfe9ff", 8);
      floatText(g.x, g.y - 10, "+加分");
      emit("bonus", { item: g.type });
      return;
    }
    L.count++;
    if (L.cfg.need) L.per[g.type] = (L.per[g.type] || 0) + 1;
    puff(g.x, g.y, "#7ef0b4", 10);
    floatText(g.x, g.y - 10, "+1");
    emit("collect", { item: g.type });
    if (L.cfg.rounds) {
      L.roundGot++;
      if (L.roundGot >= L.cfg.perRound && L.round < L.cfg.rounds) {
        L.round++; L.roundGot = 0;
        emit("round", { round: L.round - 1 });
      }
    }
    if (L.count >= L.cfg.goal) toRescue();
    else fillGoods();
  }

  function toRescue() {
    L.phase = "rescue";
    for (const g of L.goods) if (!g.bonus) puff(g.x, g.y, "#ffffff", 4, 30);
    L.goods = L.goods.filter((g) => g.bonus);
    const h = L.hero;
    const { W, H } = L.map;
    let x = h.x + Math.sin(h.heading) * 110, y = h.y - Math.cos(h.heading) * 110;
    x = Math.max(TILE + 30, Math.min(W - TILE - 30, x));
    y = Math.max(TILE * ((L.cfg.sea || 0) + 1.5), Math.min(H - TILE - 30, y));
    L.rescue = { x, y, r: 14, mate: L.idx + 1 };
    emit("goal");
  }

  function hurt(hz) {
    const h = L.hero;
    L.hits++;
    h.inv = 1.2;
    let dx = h.x - hz.x, dy = h.y - hz.y;
    const d = Math.hypot(dx, dy) || 1;
    dx /= d; dy /= d;
    if (hz.move === "wave") { dx = Math.sign(hz.vx) || 1; dy = 0.3; }
    const k = hz.move === "wave" ? 260 : 170;
    h.kbx = dx * k; h.kby = dy * k;
    if (hz.slow) h.slow = 1.5;
    puff(h.x, h.y, "#ff6b5a", 12, 80);
    emit("hurt", { haz: hz.type });
  }

  function harmony() {
    if (!L || L.phase !== "collect" || L.harmonyUsed || L.mates.length < 1) return false;
    L.harmonyUsed = true;
    for (const g of L.goods) { if (!g.bonus) { g.locked = false; g.pull = true; } }
    L.fx.push({ ring: true, x: L.hero.x, y: L.hero.y, r: 10, life: 0.9 });
    L.fx.push({ ring: true, x: L.hero.x, y: L.hero.y, r: 2, life: 1.2 });
    emit("harmony");
    return true;
  }

  // ---------- 每幀更新 ----------
  function update(dt, heading, brake) {
    if (!L) return;
    dt = Math.min(0.05, dt);
    t += dt;
    const h = L.hero, cfg = L.cfg, { W, H } = L.map;
    h.heading = heading;
    L.brake = brake;
    if (L.phase !== "done") {
      const sp = brake ? 0 : h.speed * (h.slow > 0 ? 0.5 : 1);
      let vx = Math.sin(heading) * sp + h.kbx, vy = -Math.cos(heading) * sp + h.kby;
      if (cfg.current) { // 離心盤旋轉水流（順時針切向推力）
        const dx = h.x - W / 2, dy = h.y - H / 2, d = Math.hypot(dx, dy) || 1;
        vx += (-dy / d) * cfg.current; vy += (dx / d) * cfg.current;
      }
      const ox = h.x, oy = h.y;
      h.x += vx * dt; h.y += vy * dt;
      const decay = Math.exp(-5 * dt);
      h.kbx *= decay; h.kby *= decay;
      h.x = Math.max(TILE + 10, Math.min(W - TILE - 10, h.x));
      h.y = Math.max(TILE + 12, Math.min(H - TILE - 12, h.y));
      h.inv = Math.max(0, h.inv - dt);
      h.slow = Math.max(0, h.slow - dt);
      if (sp > 0) h.walk += dt;
      const sx = Math.sin(heading);
      if (Math.abs(sx) > 0.15 && sp > 0) h.flip = sx < 0;
      h.moved = brake ? 0 : Math.hypot(h.x - ox, h.y - oy);
    } else h.moved = 0;
    // 第 2 關：在結塊粉團 80 px 內移動（來回走或繞圈）就能攪散：累積量＝移動距離／40＋方向變化量
    const dH = brake ? 0 : Math.min(0.5, Math.abs(wrap(heading - h.lastH)));
    if (!brake) h.lastH = heading;
    if (cfg.locked && L.phase === "collect" && h.moved > 0) {
      for (const g of L.goods) {
        if (!g.locked) continue;
        if (Math.hypot(g.x - h.x, g.y - h.y) < 80) {
          g.stir += h.moved / 40 + dH;
          if (g.stir >= 5.0) { g.locked = false; puff(g.x, g.y, "#bff7d8", 14, 70); emit("stir"); }
        }
      }
    }
    // 隊友環繞＋吸附
    const n = L.mates.length;
    L.mates.forEach((m, i) => {
      const a = t * 1.8 + (i / Math.max(1, n)) * TAU;
      const rr = 30 + (n > 4 ? 6 * (i % 2) : 0);
      m.x = h.x + Math.cos(a) * rr; m.y = h.y + Math.sin(a) * rr * 0.8;
      for (const g of L.goods) {
        if (g.pull || g.locked) continue;
        if (Math.hypot(g.x - m.x, g.y - m.y) < 44) g.pull = true;
      }
    });
    // 收集物
    for (const g of [...L.goods]) {
      if (g.pull) {
        const dx = h.x - g.x, dy = h.y - g.y, d = Math.hypot(dx, dy) || 1;
        const v = Math.min(d / dt, 330);
        g.x += (dx / d) * v * dt; g.y += (dy / d) * v * dt;
      }
      if (!g.locked && Math.hypot(g.x - h.x, g.y - h.y) < (g.pull ? 14 : 19)) collect(g);
    }
    // 危險物
    for (const z of L.haz) {
      if (z.move === "wave") {
        z.x += z.vx * dt;
        if (z.x < TILE - 20) z.x = W - TILE + 20; else if (z.x > W - TILE + 20) z.x = TILE - 20;
      } else if (z.move === "bounce" || z.move === "drift") {
        if (z.move === "drift") { const a = Math.atan2(z.vy, z.vx) + Math.sin(t * 0.7 + z.ph) * 0.6 * dt; z.vx = Math.cos(a) * z.sp; z.vy = Math.sin(a) * z.sp; }
        z.x += z.vx * dt; z.y += z.vy * dt;
        if (z.x < TILE + z.r || z.x > W - TILE - z.r) { z.vx = -z.vx; z.x = Math.max(TILE + z.r, Math.min(W - TILE - z.r, z.x)); }
        if (z.y < TILE + z.r || z.y > H - TILE - z.r) { z.vy = -z.vy; z.y = Math.max(TILE + z.r, Math.min(H - TILE - z.r, z.y)); }
      }
      if (L.phase !== "done" && h.inv <= 0 && Math.hypot(z.x - h.x, z.y - h.y) < z.r + 9) hurt(z);
    }
    // 救出隊友
    if (L.phase === "rescue" && L.rescue && Math.hypot(L.rescue.x - h.x, L.rescue.y - h.y) < L.rescue.r + 12) {
      L.phase = "done";
      L.doneAt = t;
      const m = L.rescue.mate;
      L.mates.push({ id: m, ang: 0, x: L.rescue.x, y: L.rescue.y });
      L.fx.push({ ring: true, x: L.rescue.x, y: L.rescue.y, r: 4, life: 0.9 });
      puff(L.rescue.x, L.rescue.y, "#ffd76a", 22, 90);
      L.rescue = null;
      emit("rescued", { mate: m });
    }
    if (L.phase === "done" && !L.finished && t - L.doneAt > 1.1) {
      L.finished = true;
      emit("finish", { hits: L.hits, stars: starsFor(L.hits), bonus: L.bonus });
    }
    // 特效
    for (const f of L.fx) { f.life -= dt; if (f.ring) f.r += 260 * dt; else { f.x += f.vx * dt; f.y += f.vy * dt; f.vx *= 0.92; f.vy *= 0.92; } }
    L.fx = L.fx.filter((f) => f.life > 0);
    for (const s of L.texts) { s.life -= dt; s.y -= 24 * dt; }
    L.texts = L.texts.filter((s) => s.life > 0);
  }

  // ---------- 繪製 ----------
  function render() {
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = "#0B1F3A";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    if (!L) return;
    const h = L.hero, { W, H, off } = L.map;
    let camX = W <= viewW ? (W - viewW) / 2 : Math.max(0, Math.min(W - viewW, h.x - viewW / 2));
    let camY = H <= viewH ? (H - viewH) / 2 : Math.max(0, Math.min(H - viewH, h.y - viewH * 0.44));
    camX = Math.round(camX); camY = Math.round(camY);
    ctx.setTransform(zoom, 0, 0, zoom, -camX * zoom, -camY * zoom);
    ctx.drawImage(off, 0, 0);
    const fr = (ph = 0) => Math.floor(t * 4 + ph) % 2;
    const inView = (x, y, m = 40) => x > camX - m && x < camX + viewW + m && y > camY - m && y < camY + viewH + m;
    // 收集物
    for (const g of L.goods) {
      if (!inView(g.x, g.y)) continue;
      const name = `${g.type}_${fr(g.ph)}`;
      const bob = Math.round(Math.sin(t * 4 + g.ph) * 1.5);
      if (g.locked) {
        // 團聚：三顆疊在一起＋攪拌進度圈
        sprites.drawC(ctx, name, g.x - 4, g.y + 2, { alpha: 0.85 });
        sprites.drawC(ctx, name, g.x + 4, g.y + 1, { alpha: 0.85 });
        sprites.drawC(ctx, name, g.x, g.y - 4);
        ctx.strokeStyle = "rgba(255,255,255,.35)"; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(g.x, g.y, 30, 0, TAU); ctx.stroke();
        ctx.strokeStyle = "#ffd76a";
        ctx.beginPath(); ctx.arc(g.x, g.y, 30, -Math.PI / 2, -Math.PI / 2 + Math.min(1, g.stir / 5) * TAU); ctx.stroke();
      } else {
        const alpha = L.cfg.faint ? 0.45 + 0.4 * (0.5 + 0.5 * Math.sin(t * 5 + g.ph)) : 1;
        sprites.drawC(ctx, name, g.x, g.y + bob, { alpha });
      }
    }
    // 救援泡泡
    if (L.rescue) {
      const r = L.rescue;
      const pr = 18 + Math.round(Math.sin(t * 5) * 2);
      ctx.fillStyle = "rgba(255,215,106,.18)"; ctx.beginPath(); ctx.arc(r.x, r.y, pr, 0, TAU); ctx.fill();
      ctx.strokeStyle = "#ffd76a"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(r.x, r.y, pr, 0, TAU); ctx.stroke();
      sprites.drawC(ctx, `mate_${r.mate}_${fr()}`, r.x, r.y);
    }
    // 危險物
    for (const z of L.haz) {
      if (!inView(z.x, z.y)) continue;
      sprites.drawC(ctx, `${z.type}_${fr(z.ph)}`, z.x, z.y, { flip: z.vx < 0 });
    }
    // 隊友（在主角後方者先畫）
    const behind = L.mates.filter((m) => m.y <= h.y), front = L.mates.filter((m) => m.y > h.y);
    for (const m of behind) sprites.drawC(ctx, `mate_${m.id}_${fr(m.id)}`, m.x, m.y);
    // 主角
    if (!(h.inv > 0 && Math.floor(t * 12) % 2)) {
      const step = L.brake ? 0 : Math.floor(h.walk * 7) % 2;
      ctx.fillStyle = "rgba(0,0,0,.25)"; ctx.fillRect(Math.round(h.x - 8), Math.round(h.y + 12), 16, 3);
      sprites.drawC(ctx, `hero_${L.heroId}_${step}`, h.x, h.y - 2, { flip: h.flip });
    }
    for (const m of front) sprites.drawC(ctx, `mate_${m.id}_${fr(m.id)}`, m.x, m.y);
    // 前進方向小箭頭
    ctx.fillStyle = "rgba(255,224,138,.9)";
    const ax = h.x + Math.sin(h.heading) * 24, ay = h.y - Math.cos(h.heading) * 24;
    ctx.fillRect(Math.round(ax - 2), Math.round(ay - 2), 4, 4);
    // 特效
    for (const f of L.fx) {
      if (f.ring) {
        ctx.strokeStyle = `rgba(126,240,180,${Math.max(0, f.life)})`; ctx.lineWidth = 3;
        ctx.beginPath(); ctx.arc(f.x, f.y, f.r, 0, TAU); ctx.stroke();
        for (let k = 0; k < 16; k++) { const a = (k / 16) * TAU + t; ctx.fillStyle = "#ffd76a"; ctx.fillRect(Math.round(f.x + Math.cos(a) * f.r) - 2, Math.round(f.y + Math.sin(a) * f.r) - 2, 4, 4); }
      } else {
        ctx.globalAlpha = Math.max(0, Math.min(1, f.life * 2));
        ctx.fillStyle = f.color; ctx.fillRect(Math.round(f.x) - 1, Math.round(f.y) - 1, 3, 3);
        ctx.globalAlpha = 1;
      }
    }
    // 浮動文字（以螢幕像素畫，避免文字被放大糊掉）
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    const fs = Math.round(14 * dpr);
    ctx.font = `bold ${fs}px "Microsoft JhengHei", "PingFang TC", sans-serif`;
    ctx.textAlign = "center";
    for (const s of L.texts) {
      const sx = (s.x - camX) * zoom, sy = (s.y - camY) * zoom;
      ctx.globalAlpha = Math.max(0, Math.min(1, s.life * 2));
      ctx.fillStyle = "#0B1F3A"; ctx.fillText(s.text, sx + dpr, sy + dpr);
      ctx.fillStyle = s.color; ctx.fillText(s.text, sx, sy);
    }
    ctx.globalAlpha = 1;
    // 畫面外目標指示箭頭
    const tg = nearestTarget();
    if (tg) {
      const sx = (tg.x - camX) * zoom, sy = (tg.y - camY) * zoom;
      const m = 26 * dpr;
      const top = 120 * dpr, bottom = canvas.height - 40 * dpr;
      if (sx < 0 || sy < top || sx > canvas.width || sy > bottom) {
        const hx = (h.x - camX) * zoom, hy = (h.y - camY) * zoom;
        const a = Math.atan2(sy - hy, sx - hx);
        const px = Math.max(m, Math.min(canvas.width - m, sx)), py = Math.max(top, Math.min(bottom - m, sy));
        ctx.save(); ctx.translate(px, py); ctx.rotate(a);
        ctx.fillStyle = L.phase === "rescue" ? "#ffd76a" : "#7ef0b4";
        const u = 3 * dpr;
        ctx.beginPath(); ctx.moveTo(4 * u, 0); ctx.lineTo(-2 * u, -3 * u); ctx.lineTo(-2 * u, 3 * u); ctx.closePath(); ctx.fill();
        ctx.restore();
      }
    }
  }

  // ---------- 自動駕駛 ----------
  function nearestTarget() {
    if (!L) return null;
    if (L.phase === "rescue") return L.rescue;
    if (L.phase !== "collect") return null;
    const h = L.hero;
    let best = null, bd = 1e9;
    for (const g of L.goods) {
      if (g.pull) continue;
      if (L.ap.ban.has(g) && L.ap.ban.get(g) > t) continue;
      const d = Math.hypot(g.x - h.x, g.y - h.y) * (g.bonus ? 1.25 : 1);
      if (d < bd) { bd = d; best = g; }
    }
    return best;
  }
  // 右上箭頭指標用：收集階段＝最近的待收集物（不含加分物）；救援階段＝隊友泡泡
  function pointerTarget() {
    if (!L) return null;
    const h = L.hero;
    if (L.phase === "rescue" && L.rescue) return { x: L.rescue.x, y: L.rescue.y, sprite: `mate_${L.rescue.mate}`, kind: "rescue", dx: L.rescue.x - h.x, dy: L.rescue.y - h.y };
    if (L.phase !== "collect") return null;
    let best = null, bd = 1e9;
    for (const g of L.goods) {
      if (g.bonus || g.pull) continue;
      const d = Math.hypot(g.x - h.x, g.y - h.y);
      if (d < bd) { bd = d; best = g; }
    }
    return best ? { x: best.x, y: best.y, sprite: best.type, kind: "collect", dx: best.x - h.x, dy: best.y - h.y } : null;
  }
  function apDecide() {
    if (!L || L.phase === "done") return null;
    const h = L.hero, { W, H } = L.map;
    const tg = nearestTarget();
    if (tg !== L.ap.target) { L.ap.target = tg; L.ap.since = t; }
    if (tg && t - L.ap.since > 5 && L.phase === "collect") { L.ap.ban.set(tg, t + 3); L.ap.target = null; } // 卡住就換目標
    const wantHarmony = L.phase === "collect" && !L.harmonyUsed && L.mates.length >= 1
      && L.goods.filter((g) => !g.bonus && !g.pull).length >= Math.min(3, L.cfg.maxOn);
    let vx = 0, vy = 0, dist = 0;
    if (tg) {
      dist = Math.hypot(tg.x - h.x, tg.y - h.y) || 1;
      if (tg.locked && dist < 60) { // 繞著粉團走：切線方向＋把半徑拉回 ~38 px
        const ux = (tg.x - h.x) / dist, uy = (tg.y - h.y) / dist;
        const k = (dist - 38) / 30;
        const cx = -uy + ux * k, cy = ux + uy * k;
        return { circle: true, heading: Math.atan2(cx, -cy), harmony: wantHarmony, target: tg, dist };
      }
      vx = (tg.x - h.x) / dist; vy = (tg.y - h.y) / dist;
    } else { vx = W / 2 - h.x; vy = H / 2 - h.y; const d = Math.hypot(vx, vy) || 1; vx /= d; vy /= d; }
    for (const z of L.haz) {
      const dx = h.x - z.x, dy = h.y - z.y, d = Math.hypot(dx, dy) || 1;
      if (d > 80) continue;
      if (tg && d > dist + 20) continue;
      const ahead = -(dx * vx + dy * vy) / d; // 危險物在前進方向上
      if (ahead < -0.2 && d > 30) continue;
      const w = ((80 - d) / 80) * 1.9;
      vx += (dx / d) * w; vy += (dy / d) * w;
    }
    const m = 46;
    if (h.x < TILE + m) vx += 0.8; if (h.x > W - TILE - m) vx -= 0.8;
    if (h.y < TILE + m) vy += 0.8; if (h.y > H - TILE - m) vy -= 0.8;
    return { heading: Math.atan2(vx, -vy), harmony: wantHarmony, target: tg, dist };
  }

  return {
    start, update, render, resize, harmony, apDecide, snapshot, pointerTarget,
    get level() { return L; },
    get zoom() { return zoom; },
    get view() { return { cssW, cssH, dpr, zoom, viewW, viewH }; },
    stop() { L = null; },
  };
}
