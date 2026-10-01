// WebAudio 合成短音效（不使用音檔）。靜音狀態只存在本機瀏覽器。
export function createAudio() {
  let ctx = null;
  let muted = false;
  try { muted = localStorage.getItem("serpentineWebAR.muted") === "1"; } catch (e) { /* 無痕模式 */ }
  let hum = null;

  const ensure = () => {
    if (muted) return null;
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ctx = new AC();
    }
    if (ctx.state === "suspended") ctx.resume();
    return ctx;
  };
  // 單音
  const tone = (freq, dur = 0.12, { type = "sine", vol = 0.18, slide = 0, delay = 0 } = {}) => {
    const c = ensure();
    if (!c) return;
    const t = c.currentTime + delay;
    const o = c.createOscillator();
    const g = c.createGain();
    o.type = type;
    o.frequency.setValueAtTime(freq, t);
    if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(30, freq + slide), t + dur);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g).connect(c.destination);
    o.start(t);
    o.stop(t + dur + 0.02);
  };
  const noise = (dur = 0.2, vol = 0.15, hp = 800) => {
    const c = ensure();
    if (!c) return;
    const n = Math.floor(c.sampleRate * dur);
    const buf = c.createBuffer(1, n, c.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / n);
    const s = c.createBufferSource();
    s.buffer = buf;
    const f = c.createBiquadFilter();
    f.type = "highpass";
    f.frequency.value = hp;
    const g = c.createGain();
    g.gain.value = vol;
    s.connect(f).connect(g).connect(c.destination);
    s.start();
  };

  return {
    get muted() { return muted; },
    toggle() {
      muted = !muted;
      try { localStorage.setItem("serpentineWebAR.muted", muted ? "1" : "0"); } catch (e) { /* ignore */ }
      if (muted) this.humStop();
    },
    unlock() { ensure(); },
    tap() { tone(660, 0.06, { type: "triangle", vol: 0.12 }); },
    good() { tone(660, 0.12); tone(880, 0.14, { delay: 0.1 }); tone(1320, 0.18, { delay: 0.2, vol: 0.12 }); },
    bad() { tone(220, 0.22, { type: "square", vol: 0.07, slide: -80 }); },
    crack() { noise(0.18, 0.25, 1200); tone(140, 0.12, { type: "square", vol: 0.06 }); },
    drop() { tone(900, 0.18, { slide: -600, vol: 0.14 }); },
    pop() { tone(520, 0.08, { type: "triangle", slide: 400, vol: 0.14 }); },
    whoosh() { noise(0.35, 0.12, 400); },
    star(i = 0) { tone(990 + i * 220, 0.16, { type: "triangle", vol: 0.12 }); },
    fanfare() { [523, 659, 784, 1047].forEach((f, i) => tone(f, 0.22, { delay: i * 0.12, vol: 0.13, type: "triangle" })); },
    humStart(freq = 90) {
      const c = ensure();
      if (!c || hum) return;
      const o = c.createOscillator();
      const g = c.createGain();
      o.type = "sawtooth";
      o.frequency.value = freq;
      g.gain.value = 0.035;
      o.connect(g).connect(c.destination);
      o.start();
      hum = { o, g };
    },
    humPitch(f) { if (hum && ctx) hum.o.frequency.setTargetAtTime(f, ctx.currentTime, 0.1); },
    humStop() { if (hum) { try { hum.o.stop(); } catch (e) { /* ignore */ } hum = null; } },
  };
}
