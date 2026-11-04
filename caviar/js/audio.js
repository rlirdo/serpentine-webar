// 純 WebAudio 合成：每關 8 小節五聲音階 chiptune BGM 迴圈＋音效（無音檔）。
// 靜音狀態存在 localStorage caviarSquad.muted。iOS 需在使用者手勢內呼叫 unlock()。
// 測試掛鉤：window.__audio.log（每次播放的名稱與時間）、window.__audio.state()。
const MUTE_KEY = "caviarSquad.muted";
const PENTA = [0, 2, 4, 7, 9];
// 每關（與結果頁）不同調、不同速度：root＝MIDI 音高
const SONGS = [
  { root: 62, bpm: 132, seed: 11, wave: "square" },   // 1 七星潭 D
  { root: 57, bpm: 144, seed: 23, wave: "square" },   // 2 球磨 A
  { root: 65, bpm: 120, seed: 37, wave: "triangle" }, // 3 實驗室 F
  { root: 60, bpm: 126, seed: 41, wave: "square" },   // 4 攪拌 C
  { root: 55, bpm: 108, seed: 53, wave: "triangle" }, // 5 深層海水 G
  { root: 64, bpm: 150, seed: 67, wave: "square" },   // 6 離心 E
  { root: 58, bpm: 116, seed: 71, wave: "triangle" }, // 7 烘箱 Bb
  { root: 63, bpm: 124, seed: 89, wave: "square" },   // 8 量測 Eb
  { root: 60, bpm: 100, seed: 97, wave: "triangle" }, // 9 選單／測驗 C（較慢）
];
const mtof = (m) => 440 * Math.pow(2, (m - 69) / 12);
function rng(seed) { let s = seed >>> 0 || 1; return () => { s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; }; }
function compose(song) {
  const r = rng(song.seed * 7919);
  const mel = [];
  let deg = 5;
  for (let i = 0; i < 64; i++) {
    const strong = i % 8 === 0;
    if (!strong && r() < 0.22) { mel.push(null); continue; }
    deg += Math.round((r() - 0.5) * 4);
    deg = Math.max(0, Math.min(10, deg));
    if (i % 16 === 15) deg = 5; // 每兩小節回到主音
    mel.push(12 * Math.floor(deg / 5) + PENTA[deg % 5]);
  }
  const prog = [0, 9, 5, 7, 0, 9, 7, 0]; // 八小節和聲根音
  return { mel, prog };
}

export function createAudio() {
  let ctx = null, master = null, noiseBuf = null;
  let muted = false;
  try { muted = localStorage.getItem(MUTE_KEY) === "1"; } catch (e) { /* 無痕模式 */ }
  const log = [];
  const mark = (name) => { log.push({ name, t: Math.round(performance.now()) }); if (log.length > 3000) log.splice(0, 1000); };
  let bgm = null; // { idx, song, seq, step, next, timer }
  let lastTick = 0;

  function ensure() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      try { ctx = new AC(); } catch (e) { return null; }
      master = ctx.createGain();
      master.gain.value = muted ? 0 : 0.9;
      master.connect(ctx.destination);
      const n = Math.floor(ctx.sampleRate * 0.5);
      noiseBuf = ctx.createBuffer(1, n, ctx.sampleRate);
      const d = noiseBuf.getChannelData(0);
      for (let i = 0; i < n; i++) d[i] = Math.random() * 2 - 1;
    }
    if (ctx.state === "suspended") { try { ctx.resume(); } catch (e) { /* ignore */ } }
    return ctx;
  }
  function tone(freq, dur, { type = "square", vol = 0.1, slide = 0, at = 0, delay = 0 } = {}) {
    const c = ensure();
    if (!c) return;
    const t = (at || c.currentTime) + delay;
    const o = c.createOscillator();
    const g = c.createGain();
    o.type = type;
    o.frequency.setValueAtTime(freq, t);
    if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(30, freq + slide), t + dur);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + 0.008);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g).connect(master);
    o.start(t);
    o.stop(t + dur + 0.03);
  }
  function noise(dur, vol = 0.1, hp = 1000, at = 0) {
    const c = ensure();
    if (!c || !noiseBuf) return;
    const t = at || c.currentTime;
    const s = c.createBufferSource();
    s.buffer = noiseBuf;
    const f = c.createBiquadFilter();
    f.type = "highpass";
    f.frequency.value = hp;
    const g = c.createGain();
    g.gain.setValueAtTime(vol, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    s.connect(f).connect(g).connect(master);
    s.start(t);
    s.stop(t + dur + 0.02);
  }

  // ---------- BGM 序列器（lookahead 排程） ----------
  function schedule() {
    if (!bgm || !ctx) return;
    const eighth = 60 / bgm.song.bpm / 2;
    while (bgm.next < ctx.currentTime + 0.15) {
      const i = bgm.step % 64, t = bgm.next, s = bgm.song;
      const m = bgm.seq.mel[i];
      if (m != null) tone(mtof(s.root + m), eighth * 0.9, { type: s.wave, vol: 0.045, at: t });
      if (i % 4 === 0) {
        const root = s.root - 24 + bgm.seq.prog[Math.floor(i / 8)];
        tone(mtof(root + (i % 8 === 4 ? 7 : 0)), eighth * 1.8, { type: "triangle", vol: 0.09, at: t });
      }
      if (i % 2 === 1) noise(0.04, 0.025, 6000, t);
      if (i % 8 === 0) noise(0.09, 0.05, 300, t);
      bgm.step++;
      bgm.next += eighth;
    }
  }
  function bgmStart(idx) {
    if (bgm && bgm.idx === idx) return;
    bgmStop();
    const c = ensure();
    mark(`bgm:${idx}`);
    if (!c) return;
    const song = SONGS[Math.max(0, Math.min(SONGS.length - 1, idx))];
    bgm = { idx, song, seq: compose(song), step: 0, next: c.currentTime + 0.08, timer: 0 };
    bgm.timer = setInterval(schedule, 30);
    schedule();
  }
  function bgmStop() { if (bgm) { clearInterval(bgm.timer); bgm = null; } }

  const sfx = {
    tap() { tone(660, 0.06, { type: "triangle", vol: 0.12 }); },
    collect() { tone(988, 0.07, { vol: 0.08 }); tone(1319, 0.1, { vol: 0.08, delay: 0.06 }); },
    bonus() { tone(784, 0.07, { vol: 0.08 }); tone(1047, 0.07, { vol: 0.08, delay: 0.06 }); tone(1568, 0.12, { vol: 0.07, delay: 0.12 }); },
    hurt() { tone(196, 0.25, { type: "sawtooth", vol: 0.08, slide: -90 }); noise(0.15, 0.08, 500); },
    rescue() { [523, 659, 784, 1047, 1319].forEach((f, k) => tone(f, 0.14, { type: "triangle", vol: 0.1, delay: k * 0.07 })); },
    harmony() { [392, 523, 659, 784].forEach((f, k) => { tone(f, 0.9, { type: "triangle", vol: 0.06, delay: k * 0.05 }); tone(f * 2, 0.6, { type: "square", vol: 0.02, delay: 0.1 + k * 0.05 }); }); noise(0.6, 0.04, 2000); },
    star(i = 0) { tone(1047 + i * 262, 0.16, { type: "square", vol: 0.07 }); },
    tick() { tone(1800, 0.018, { type: "square", vol: 0.025 }); },
    good() { tone(660, 0.1, { vol: 0.08 }); tone(880, 0.14, { vol: 0.08, delay: 0.09 }); },
    bad() { tone(220, 0.22, { type: "square", vol: 0.06, slide: -80 }); },
    fanfare() {
      // 小號式：鋸齒波＋短促滑音
      const seq = [[523, 0, 0.14], [523, 0.15, 0.1], [523, 0.27, 0.1], [698, 0.4, 0.45], [880, 0.88, 0.2], [784, 1.1, 0.2], [1047, 1.33, 0.7]];
      seq.forEach(([f, d, l]) => { tone(f * 0.995, l, { type: "sawtooth", vol: 0.07, delay: d, slide: 4 }); tone(f / 2, l, { type: "triangle", vol: 0.06, delay: d }); });
    },
  };

  const api = {
    log,
    get muted() { return muted; },
    unlock() { ensure(); mark("unlock"); },
    toggle() {
      muted = !muted;
      try { localStorage.setItem(MUTE_KEY, muted ? "1" : "0"); } catch (e) { /* ignore */ }
      if (master && ctx) master.gain.setTargetAtTime(muted ? 0 : 0.9, ctx.currentTime, 0.02);
      mark(muted ? "mute" : "unmute");
      return muted;
    },
    bgm(idx) { bgmStart(idx); },
    bgmStop() { if (bgm) mark("bgm:stop"); bgmStop(); },
    play(name, arg) {
      if (name === "tick") { const now = performance.now(); if (now - lastTick < 45) return; lastTick = now; }
      mark(name);
      if (sfx[name]) { try { sfx[name](arg); } catch (e) { /* ignore */ } }
    },
    state() { return ctx ? ctx.state : "none"; },
  };
  window.__audio = { log, state: api.state, get bgm() { return bgm ? bgm.idx : null; } };
  try {
    document.addEventListener("visibilitychange", () => {
      if (!ctx) return;
      if (document.hidden) ctx.suspend().catch(() => {}); else ctx.resume().catch(() => {});
    });
  } catch (e) { /* ignore */ }
  return api;
}
