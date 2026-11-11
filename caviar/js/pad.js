// 白色圓形觸控盤（取代舊版轉盤操作）：手指按在圓盤內，「圓心→手指」的方向就是主角前進方向
// （上方往上、下方往下、左往左、右往右，斜向亦可；0＝正上方，順時針為正）。
// 圓心 12% 半徑內為死區；手指放開、或滑出圓盤外（距圓心 > 半徑 ×1.12）主角立刻停止，滑回圓盤內可繼續。
// 鍵盤：方向鍵／WASD 按住移動、放開停止。自動測試以 setAuto(heading) 駕駛。
const TAU = Math.PI * 2;
export const wrap = (a) => { a = (a + Math.PI) % TAU; if (a < 0) a += TAU; return a - Math.PI; };

export function createPad({ el, knob, audio }) {
  let angle = Math.PI / 2; // 一開始朝右
  let ptr = null; // { id, inside }
  let auto = null;
  let enabled = false;
  const keys = new Set();
  let R = 80, cx = 0, cy = 0;

  function layout() {
    const r = el.getBoundingClientRect();
    R = r.width / 2 || 80;
    cx = r.left + r.width / 2; cy = r.top + r.height / 2;
  }
  function setKnob(dx, dy) {
    if (!knob) return;
    knob.style.transform = `translate(calc(-50% + ${dx.toFixed(1)}px), calc(-50% + ${dy.toFixed(1)}px))`;
  }
  function track(e) {
    layout();
    const dx = e.clientX - cx, dy = e.clientY - cy, d = Math.hypot(dx, dy);
    if (d > R * 1.12) { ptr.inside = false; setKnob(0, 0); el.classList.remove("on"); return; }
    if (d < R * 0.12) { ptr.inside = false; setKnob(dx, dy); el.classList.add("on"); return; }
    ptr.inside = true;
    angle = Math.atan2(dx, -dy);
    const k = Math.min(1, (R * 0.78) / d);
    setKnob(dx * k, dy * k);
    el.classList.add("on");
  }
  el.addEventListener("pointerdown", (e) => {
    if (!enabled) return;
    e.preventDefault();
    try { el.setPointerCapture(e.pointerId); } catch (er) { /* ignore */ }
    ptr = { id: e.pointerId, inside: false };
    track(e);
    if (audio) audio.play("tick");
  });
  el.addEventListener("pointermove", (e) => {
    if (!ptr || e.pointerId !== ptr.id) return;
    e.preventDefault();
    track(e);
  });
  const end = (e) => {
    if (ptr && e.pointerId === ptr.id) { ptr = null; setKnob(0, 0); el.classList.remove("on"); }
  };
  ["pointerup", "pointercancel", "lostpointercapture"].forEach((t) => el.addEventListener(t, end));
  el.addEventListener("contextmenu", (e) => e.preventDefault());

  const KEYMAP = { ArrowUp: [0, -1], KeyW: [0, -1], ArrowDown: [0, 1], KeyS: [0, 1], ArrowLeft: [-1, 0], KeyA: [-1, 0], ArrowRight: [1, 0], KeyD: [1, 0] };
  window.addEventListener("keydown", (e) => {
    if (!enabled) return;
    const t = e.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT")) return;
    if (KEYMAP[e.code]) { keys.add(e.code); e.preventDefault(); }
  });
  window.addEventListener("keyup", (e) => { keys.delete(e.code); });
  window.addEventListener("blur", () => { keys.clear(); });
  window.addEventListener("resize", layout);

  function keyVec() {
    let x = 0, y = 0;
    keys.forEach((k) => { x += KEYMAP[k][0]; y += KEYMAP[k][1]; });
    return [x, y];
  }
  // 每幀呼叫：決定 angle 與 active
  function update() {
    if (ptr) return;
    const [x, y] = keyVec();
    if (x || y) { angle = Math.atan2(x, -y); setKnob(x * R * 0.55, y * R * 0.55); return; }
    if (auto != null) { angle = auto; setKnob(Math.sin(auto) * R * 0.55, -Math.cos(auto) * R * 0.55); return; }
    setKnob(0, 0);
  }
  function isActive() {
    if (!enabled) return false;
    if (ptr) return ptr.inside;
    const [x, y] = keyVec();
    if (x || y) return true;
    return auto != null;
  }

  layout();
  return {
    get angle() { return angle; },
    set angle(v) { angle = wrap(v); },
    get active() { return isActive(); },
    get touching() { return !!ptr; },
    setAuto(h) { auto = h == null ? null : wrap(h); },
    setEnabled(v) { enabled = !!v; if (!v) { ptr = null; keys.clear(); auto = null; setKnob(0, 0); el.classList.remove("on"); } },
    update, layout,
  };
}
