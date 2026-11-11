// 方向盤：觸控／滑鼠按住拖曳旋轉；指針（金色標記）的絕對角度＝主角前進方向（0＝正上方，順時針為正）。
// 鍵盤：方向鍵／WASD 指定方向（方向盤會轉過去），空白鍵＝煞車。煞車按鈕按住停止。
const TAU = Math.PI * 2;
export const wrap = (a) => { a = (a + Math.PI) % TAU; if (a < 0) a += TAU; return a - Math.PI; };

export function createWheel({ canvas, brakeBtn, sprites, audio }) {
  let angle = Math.PI / 2; // 一開始朝右
  let drawn = NaN;
  let drag = null; // { id, p0, a0 }
  let brakeHeld = false, brakeKey = false;
  const keys = new Set();
  let size = 160, dpr = 1;
  let tickAcc = 0;
  let enabled = false;
  let manualAt = 0;
  const ctx = canvas.getContext("2d");

  function layout() {
    const W = innerWidth, H = innerHeight;
    size = Math.round(Math.max(150, Math.min(W * 0.4, H * 0.3, 300)));
    dpr = Math.min(3, window.devicePixelRatio || 1);
    canvas.style.width = size + "px";
    canvas.style.height = size + "px";
    canvas.width = Math.round(size * dpr);
    canvas.height = Math.round(size * dpr);
    drawn = NaN;
    render();
  }

  function rotateBy(d) {
    if (!d) return;
    angle = wrap(angle + d);
    tickAcc += Math.abs(d);
    if (tickAcc > 0.26) { tickAcc = 0; audio && audio.play("tick"); }
  }
  const ptrAngle = (e) => {
    const r = canvas.getBoundingClientRect();
    const dx = e.clientX - (r.left + r.width / 2), dy = e.clientY - (r.top + r.height / 2);
    return Math.atan2(dx, -dy);
  };
  canvas.addEventListener("pointerdown", (e) => {
    if (!enabled) return;
    e.preventDefault();
    try { canvas.setPointerCapture(e.pointerId); } catch (er) { /* ignore */ }
    drag = { id: e.pointerId, last: ptrAngle(e) };
    manualAt = performance.now();
  });
  canvas.addEventListener("pointermove", (e) => {
    if (!drag || e.pointerId !== drag.id) return;
    e.preventDefault();
    const a = ptrAngle(e);
    rotateBy(wrap(a - drag.last));
    drag.last = a;
    manualAt = performance.now();
  });
  const end = (e) => { if (drag && e.pointerId === drag.id) drag = null; };
  canvas.addEventListener("pointerup", end);
  canvas.addEventListener("pointercancel", end);
  canvas.addEventListener("lostpointercapture", end);

  if (brakeBtn) {
    const on = (e) => { e.preventDefault(); brakeHeld = true; brakeBtn.classList.add("on"); };
    const off = () => { brakeHeld = false; brakeBtn.classList.remove("on"); };
    brakeBtn.addEventListener("pointerdown", on);
    ["pointerup", "pointercancel", "pointerleave"].forEach((t) => brakeBtn.addEventListener(t, off));
  }
  const KEYMAP = { ArrowUp: [0, -1], KeyW: [0, -1], ArrowDown: [0, 1], KeyS: [0, 1], ArrowLeft: [-1, 0], KeyA: [-1, 0], ArrowRight: [1, 0], KeyD: [1, 0] };
  window.addEventListener("keydown", (e) => {
    if (!enabled) return;
    const t = e.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA")) return;
    if (KEYMAP[e.code]) { keys.add(e.code); e.preventDefault(); manualAt = performance.now(); }
    if (e.code === "Space") { brakeKey = true; e.preventDefault(); }
  });
  window.addEventListener("keyup", (e) => {
    keys.delete(e.code);
    if (e.code === "Space") brakeKey = false;
  });
  window.addEventListener("blur", () => { keys.clear(); brakeKey = false; brakeHeld = false; });

  // 轉向指定角度（每秒最多 rate 弧度）
  function steerTo(target, dt, rate = 7) {
    const d = wrap(target - angle);
    const m = rate * dt;
    rotateBy(Math.abs(d) <= m ? d : Math.sign(d) * m);
  }

  function update(dt) {
    if (keys.size) {
      let x = 0, y = 0;
      keys.forEach((k) => { x += KEYMAP[k][0]; y += KEYMAP[k][1]; });
      if (x || y) steerTo(Math.atan2(x, -y), dt, 9);
    }
    render();
  }

  function render() {
    if (drawn === angle) return;
    drawn = angle;
    const S = canvas.width;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, S, S);
    ctx.imageSmoothingEnabled = false;
    ctx.translate(S / 2, S / 2);
    ctx.rotate(angle);
    if (sprites && sprites.has("ui_wheel")) {
      const [w] = sprites.size("ui_wheel");
      const k = S / w;
      ctx.scale(k, k);
      sprites.draw(ctx, "ui_wheel", -w / 2, -w / 2);
    } else {
      // 純色像素風方向盤（深藍輪圈＋金色指針）
      const R = S / 2 - 2;
      const u = Math.max(2, Math.round(S / 80));
      ctx.lineWidth = u * 5;
      ctx.strokeStyle = "#0B1F3A"; ctx.beginPath(); ctx.arc(0, 0, R - u * 3, 0, TAU); ctx.stroke();
      ctx.lineWidth = u * 2;
      ctx.strokeStyle = "#1C7293"; ctx.beginPath(); ctx.arc(0, 0, R - u * 3, 0, TAU); ctx.stroke();
      ctx.fillStyle = "#0B1F3A";
      for (const a of [0, 2.1, -2.1]) { ctx.save(); ctx.rotate(a); ctx.fillRect(-u * 1.5, -R + u * 5, u * 3, R - u * 5); ctx.restore(); }
      ctx.fillStyle = "#065A82"; ctx.beginPath(); ctx.arc(0, 0, R * 0.26, 0, TAU); ctx.fill();
      ctx.fillStyle = "#5FA98A"; ctx.fillRect(-u * 2, -u * 2, u * 4, u * 4);
      // 金色指針（正上方）
      ctx.fillStyle = "#C99A3E";
      ctx.beginPath(); ctx.moveTo(0, -R - 1); ctx.lineTo(u * 4, -R + u * 7); ctx.lineTo(-u * 4, -R + u * 7); ctx.closePath(); ctx.fill();
      ctx.fillStyle = "#ffe08a"; ctx.fillRect(-u, -R + u * 2, u * 2, u * 3);
    }
  }

  window.addEventListener("resize", layout);
  layout();
  return {
    get angle() { return angle; },
    set angle(v) { angle = wrap(v); },
    get brake() { return brakeHeld || brakeKey; },
    get dragging() { return !!drag; },
    get size() { return size; },
    get manualRecently() { return performance.now() - manualAt < 600; },
    setEnabled(v) { enabled = !!v; if (!v) { drag = null; keys.clear(); brakeHeld = false; brakeKey = false; } },
    steerTo, rotateBy, update, layout, render,
  };
}
