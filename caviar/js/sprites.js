// 像素圖集（晶球護衛隊：只換占位配色）：assets/sprites.png ＋ assets/sprites.json（{"scale":1,"frames":{name:{x,y,w,h}}}）。
// 圖集不存在或某個名稱缺漏時，以純色像素占位繪製，不報錯；圖集日後出現不必改程式。
const DEFAULT_SIZE = (name) => {
  if (name.startsWith("hero_")) return [24, 32];
  if (name.startsWith("mate_")) return [24, 24];
  if (name.startsWith("haz_ball") || name.startsWith("haz_wave")) return [24, 24];
  if (name.startsWith("tile_")) return [32, 32];
  if (name === "ui_wheel") return [160, 160];
  if (name === "ui_harmony") return [32, 32];
  return [16, 16];
};
const BAND_COLOR = { kid: "#f2b134", teen: "#2E7D5B", adult: "#f1f5f9", elder: "#b7893f" };
const MATE_COLOR = ["#8a6a1f", "#f3e6c8", "#ff9a6a", "#3d8fd6", "#1c5fa8", "#e0304a", "#c86ad8", "#5fd39a"];
const ITEM_COLOR = {
  kelp: "#8a6a1f", trash: "#7cc4e8", powder: "#f3e6c8", h2o: "#8fd3ff", ca: "#3d8fd6", drop: "#e0304a",
  bead: "#ff6a8a", hard: "#c84a6a", cell: "#5fd39a", ink: "#ff9f43", filter: "#4fb0e0", pack: "#e8c547",
};
const HAZ_COLOR = {
  wave: "#2d8fd5", fisheye: "#d8c8a0", bubble: "#cfefff", mg: "#22d3c5", vapor: "#b0c4d0", na: "#9b59d0",
  high: "#c99a3e", tail: "#b0304a", flat: "#e05a6a", burst: "#ff8a8a", bottle: "#9fd8ff",
};
const TILE_COLOR = [
  null,
  ["#cfd3cf", "#b9bfbb", "#5b6a72"], // 1 七星潭礫石灘
  ["#8a6440", "#9a7450", "#3a2a1a"], // 2 粉末工坊木桌
  ["#7a1f2e", "#8a2a3a", "#3a0b16"], // 3 紅液燒杯
  ["#b8e0f2", "#a0d2ea", "#0d3b5c"], // 4 藍色鈣液（淺色，讓深藍 Ca²⁺ 看得清楚）
  ["#2a2f5a", "#343a6a", "#141830"], // 5 滴球工坊
  ["#f2f5f4", "#e3ece8", "#2E7D5B"], // 6 實驗桌（高度尺）
  ["#1d5f7a", "#246f8c", "#0b2f3d"], // 7 清水洗盆
  ["#3b2a5c", "#45326b", "#1d1430"], // 8 仿生應用館
];

export function createSprites(base = "assets/") {
  let img = null;
  let frames = {};
  let ready = false;
  let source = "fallback";
  let titleImg = null;

  async function load() {
    try {
      const r = await fetch(base + "sprites.json", { cache: "no-cache" });
      if (!r.ok) throw new Error("no atlas");
      const j = await r.json();
      const im = new Image();
      await new Promise((res, rej) => { im.onload = res; im.onerror = rej; im.src = base + "sprites.png"; });
      img = im;
      frames = (j && j.frames) || {};
      source = "atlas";
      // 標題圖只有在圖集存在時才載（同一位代理產出）
      await new Promise((res) => {
        const t = new Image();
        t.onload = () => { titleImg = t; res(); };
        t.onerror = () => res();
        t.src = base + "title.png";
      });
    } catch (e) {
      img = null; frames = {}; source = "fallback";
    }
    ready = true;
    return source;
  }

  const has = (name) => !!(img && frames[name]);
  const size = (name) => { const f = frames[name]; if (img && f) return [f.w, f.h]; return DEFAULT_SIZE(name); };

  // 純色像素占位（在目前座標系以 1 單位＝1 像素畫）
  function fallback(ctx, name, x, y, w, h) {
    const p = name.split("_");
    const kind = p[0];
    ctx.save();
    if (kind === "tile") {
      const s = Number(String(p[1]).slice(1)) || 1;
      const k = { a: 0, b: 1, c: 2 }[p[2]] || 0;
      ctx.fillStyle = (TILE_COLOR[s] || TILE_COLOR[1])[k];
      ctx.fillRect(x, y, w, h);
      ctx.fillStyle = "rgba(0,0,0,.10)";
      if (k === 2) {
        for (let i = 0; i < 4; i++) ctx.fillRect(x, y + i * 8, w, 2);
        ctx.fillStyle = "rgba(255,255,255,.18)"; ctx.fillRect(x + 2, y + 2, 4, 4);
      } else {
        ctx.fillRect(x, y, w, 1); ctx.fillRect(x, y, 1, h);
        if (k === 1) { ctx.fillRect(x + 8, y + 10, 3, 3); ctx.fillRect(x + 20, y + 22, 2, 2); }
      }
    } else if (kind === "hero") {
      const band = p[1], sx = p[2], fr = Number(p[3]) || 0;
      ctx.fillStyle = "rgba(0,0,0,.25)"; ctx.fillRect(x + 4, y + h - 3, w - 8, 3);
      ctx.fillStyle = BAND_COLOR[band] || "#ddd"; ctx.fillRect(x + 6, y + 13, 12, 12);
      ctx.fillStyle = "#1E293B"; ctx.fillRect(x + 7 + (fr ? 1 : 0), y + 25, 4, 5); ctx.fillRect(x + 13 - (fr ? 1 : 0), y + 25, 4, 5);
      ctx.fillStyle = "#f6cfa6"; ctx.fillRect(x + 6, y + 3, 12, 10);
      ctx.fillStyle = sx === "f" ? "#5b3a29" : sx === "m" ? "#2b2b2b" : "#6b4f8a"; ctx.fillRect(x + 5, y + 2, 14, 3);
      if (band === "kid" || band === "elder") { ctx.fillStyle = band === "kid" ? "#1C7293" : "#e8c66a"; ctx.fillRect(x + 3, y + 1, 18, 3); }
      ctx.fillStyle = "#0B1F3A"; ctx.fillRect(x + 13, y + 7, 2, 2); ctx.fillRect(x + 16, y + 7, 2, 2);
    } else if (kind === "mate") {
      const i = Math.max(0, (Number(p[1]) || 1) - 1), fr = Number(p[2]) || 0;
      ctx.fillStyle = MATE_COLOR[i]; ctx.fillRect(x + 4, y + 4 + fr, 16, 16 - fr);
      ctx.fillRect(x + 6, y + 2 + fr, 12, 20 - fr);
      ctx.fillStyle = "#fff"; ctx.fillRect(x + 8, y + 9, 3, 3); ctx.fillRect(x + 14, y + 9, 3, 3);
      ctx.fillStyle = "#0B1F3A"; ctx.fillRect(x + 9, y + 10, 2, 2); ctx.fillRect(x + 15, y + 10, 2, 2);
    } else if (kind === "item" || kind === "haz") {
      const t = p[1], fr = Number(p[2]) || 0;
      const col = (kind === "item" ? ITEM_COLOR : HAZ_COLOR)[t] || "#ccc";
      ctx.fillStyle = "rgba(0,0,0,.25)"; ctx.fillRect(x + 2, y + h - 2, w - 4, 2);
      ctx.fillStyle = col;
      const m = fr ? 1 : 2;
      ctx.fillRect(x + m, y + m + 1, w - 2 * m, h - 2 * m - 2);
      if (kind === "haz") { ctx.fillStyle = "#b91c1c"; ctx.fillRect(x + w / 2 - 1, y + 3, 2, h - 9); ctx.fillRect(x + w / 2 - 1, y + h - 5, 2, 2); }
      else { ctx.fillStyle = "rgba(255,255,255,.7)"; ctx.fillRect(x + 4, y + 4, 3, 3); }
    } else if (kind === "ui") {
      const t = p.slice(1).join("_");
      if (t === "star_on" || t === "star_off") {
        ctx.fillStyle = t === "star_on" ? "#ffd23f" : "#55606e";
        ctx.fillRect(x + 6, y + 1, 4, 14); ctx.fillRect(x + 1, y + 6, 14, 4); ctx.fillRect(x + 3, y + 3, 10, 10);
      } else if (t === "heart") {
        ctx.fillStyle = "#ef4444"; ctx.fillRect(x + 2, y + 3, 5, 6); ctx.fillRect(x + 9, y + 3, 5, 6); ctx.fillRect(x + 3, y + 8, 10, 4); ctx.fillRect(x + 6, y + 12, 4, 2);
      } else if (t.startsWith("lattice")) {
        ctx.fillStyle = t.endsWith("full") ? "#22d3c5" : "#1e293b"; ctx.fillRect(x + 2, y + 2, 12, 12);
        ctx.fillStyle = "#7ef0b4"; ctx.fillRect(x + 2, y + 2, 12, 1); ctx.fillRect(x + 2, y + 13, 12, 1); ctx.fillRect(x + 2, y + 2, 1, 12); ctx.fillRect(x + 13, y + 2, 1, 12);
      } else if (t === "harmony") {
        ctx.fillStyle = "#7ef0b4"; ctx.fillRect(x + 6, y + 6, 20, 20); ctx.fillStyle = "#0B1F3A"; ctx.fillRect(x + 12, y + 12, 8, 8);
      } else { ctx.fillStyle = "#ccc"; ctx.fillRect(x, y, w, h); }
    } else { ctx.fillStyle = "#f0f"; ctx.fillRect(x, y, w, h); }
    ctx.restore();
  }

  // 以左上角 (x,y) 畫一張圖；scale 為整數倍；flip＝水平鏡射
  function draw(ctx, name, x, y, { scale = 1, flip = false, alpha = 1 } = {}) {
    const [w, h] = size(name);
    const dw = w * scale, dh = h * scale;
    ctx.save();
    if (alpha !== 1) ctx.globalAlpha *= alpha;
    if (flip) { ctx.translate(x + dw, y); ctx.scale(-1, 1); x = 0; y = 0; }
    const f = img && frames[name];
    if (f) ctx.drawImage(img, f.x, f.y, f.w, f.h, x, y, dw, dh);
    else { ctx.translate(x, y); if (scale !== 1) ctx.scale(scale, scale); fallback(ctx, name, 0, 0, w, h); }
    ctx.restore();
  }
  // 置中畫（座標為中心點），自動取整數像素
  function drawC(ctx, name, cx, cy, opts = {}) {
    const [w, h] = size(name);
    const s = opts.scale || 1;
    draw(ctx, name, Math.round(cx - (w * s) / 2), Math.round(cy - (h * s) / 2), opts);
  }
  // 給 DOM 用的小畫布（HUD 頭像、主角預覽）
  function toCanvas(name, scale = 2, cls = "pix") {
    const [w, h] = size(name);
    const c = document.createElement("canvas");
    c.width = w * scale; c.height = h * scale;
    c.className = cls;
    const ctx = c.getContext("2d");
    ctx.imageSmoothingEnabled = false;
    draw(ctx, name, 0, 0, { scale });
    return c;
  }

  return {
    load, has, size, draw, drawC, toCanvas,
    get ready() { return ready; }, get source() { return source; }, get title() { return titleImg; },
    get image() { return img; },
    get count() { return Object.keys(frames).length; },
  };
}
