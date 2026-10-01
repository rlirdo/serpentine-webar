// 視覺特效小工具：補間動畫、文字貼圖 Sprite、粒子（≤150）、遠紅外波紋。
import * as THREE from "three";

// 文字貼圖放大倍率（手機上 3D 文字至少約 18px）
export const LABEL_BOOST = 1.4;
export const FONT = '"Microsoft JhengHei","PingFang TC","Noto Sans TC","Heiti TC",sans-serif';

export const ease = {
  linear: (k) => k,
  outCubic: (k) => 1 - Math.pow(1 - k, 3),
  inCubic: (k) => k * k * k,
  inOutSine: (k) => -(Math.cos(Math.PI * k) - 1) / 2,
  outBack: (k) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); },
  outElastic: (k) => (k === 0 || k === 1 ? k : Math.pow(2, -10 * k) * Math.sin((k * 10 - 0.75) * (2 * Math.PI) / 3) + 1),
};

// 以遊戲時鐘驅動的補間（headless 與實機同步）
export class Tweens {
  constructor() { this.list = []; this.time = 0; }
  add(duration, fn, e = ease.inOutSine) {
    return new Promise((resolve) => {
      this.list.push({ t: 0, d: Math.max(0.001, duration), fn, e, resolve });
      fn(0);
    });
  }
  wait(sec) { return this.add(sec, () => {}); }
  update(dt) {
    this.time += dt;
    for (let i = this.list.length - 1; i >= 0; i--) {
      const tw = this.list[i];
      tw.t += dt;
      const k = Math.min(1, tw.t / tw.d);
      tw.fn(tw.e(k), k);
      if (k >= 1) { this.list.splice(i, 1); tw.resolve(); }
    }
  }
  clear() { this.list.forEach((tw) => tw.resolve()); this.list = []; }
}

export function canvasTexture(w, h, draw) {
  const c = document.createElement("canvas");
  c.width = w; c.height = h;
  const g = c.getContext("2d");
  draw(g, w, h);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 2;
  return tex;
}

let _glow = null;
export function glowTexture() {
  if (_glow) return _glow;
  _glow = canvasTexture(64, 64, (g, w) => {
    const r = g.createRadialGradient(w / 2, w / 2, 0, w / 2, w / 2, w / 2);
    r.addColorStop(0, "rgba(255,255,255,1)");
    r.addColorStop(0.25, "rgba(255,255,255,.75)");
    r.addColorStop(1, "rgba(255,255,255,0)");
    g.fillStyle = r;
    g.fillRect(0, 0, w, w);
  });
  return _glow;
}

export function glowSprite(color, size, opacity = 0.8) {
  const m = new THREE.SpriteMaterial({ map: glowTexture(), color, transparent: true, opacity,
    blending: THREE.AdditiveBlending, depthWrite: false });
  const s = new THREE.Sprite(m);
  s.scale.setScalar(size);
  return s;
}

// 文字貼圖：自動依字寬決定比例；height 為本地座標高度
export function makeLabel(text, { height = 0.07, color = "#fff", bg = "rgba(11,31,58,.82)", border = null,
  weight = 800, px = 56, pad = 18, radius = 22, depthTest = false } = {}) {
  height *= LABEL_BOOST;
  const lines = String(text).split("\n");
  const meas = document.createElement("canvas").getContext("2d");
  meas.font = `${weight} ${px}px ${FONT}`;
  const tw = Math.max(...lines.map((l) => meas.measureText(l).width));
  const W = Math.ceil(tw + pad * 2), H = Math.ceil(px * 1.3 * lines.length + pad * 1.2);
  const tex = canvasTexture(W, H, (g) => {
    if (bg) {
      g.fillStyle = bg;
      roundRect(g, 2, 2, W - 4, H - 4, radius);
      g.fill();
      if (border) { g.lineWidth = 4; g.strokeStyle = border; g.stroke(); }
    }
    g.font = `${weight} ${px}px ${FONT}`;
    g.fillStyle = color;
    g.textAlign = "center";
    g.textBaseline = "middle";
    lines.forEach((l, i) => g.fillText(l, W / 2, pad * 0.6 + px * 1.3 * (i + 0.5)));
  });
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest, depthWrite: false });
  const s = new THREE.Sprite(mat);
  s.scale.set(height * (W / H), height, 1);
  s.renderOrder = 20;
  s.userData.aspect = W / H;
  return s;
}

export function roundRect(g, x, y, w, h, r) {
  g.beginPath();
  g.moveTo(x + r, y);
  g.arcTo(x + w, y, x + w, y + h, r);
  g.arcTo(x + w, y + h, x, y + h, r);
  g.arcTo(x, y + h, x, y, r);
  g.arcTo(x, y, x + w, y, r);
  g.closePath();
}

// 粒子系統（單一 draw call，上限 150）
export class Particles extends THREE.Points {
  constructor(max = 150) {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(max * 3), 3));
    geo.setAttribute("pcolor", new THREE.BufferAttribute(new Float32Array(max * 3), 3));
    geo.setAttribute("psize", new THREE.BufferAttribute(new Float32Array(max), 1));
    geo.setAttribute("palpha", new THREE.BufferAttribute(new Float32Array(max), 1));
    const mat = new THREE.ShaderMaterial({
      uniforms: { uPx: { value: 300 }, uMap: { value: glowTexture() } },
      vertexShader: `
        attribute vec3 pcolor; attribute float psize; attribute float palpha;
        uniform float uPx; varying vec3 vC; varying float vA;
        void main(){ vC=pcolor; vA=palpha; vec4 mv=modelViewMatrix*vec4(position,1.0);
          gl_PointSize = clamp(psize*uPx/max(0.0001,-mv.z), 0.0, 96.0); gl_Position=projectionMatrix*mv; }`,
      fragmentShader: `
        uniform sampler2D uMap; varying vec3 vC; varying float vA;
        void main(){ vec4 t=texture2D(uMap, gl_PointCoord); gl_FragColor=vec4(vC, vA*t.a); }`,
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    });
    super(geo, mat);
    this.frustumCulled = false;
    this.renderOrder = 30;
    this.max = max;
    this.p = [];
    for (let i = 0; i < max; i++) this.p.push({ alive: false, pos: new THREE.Vector3(), vel: new THREE.Vector3(), life: 0, age: 0, size: 0.02, col: new THREE.Color(), g: 0, drag: 0 });
    this._tmp = new THREE.Vector3();
  }
  emit({ pos, count = 10, color = "#ffffff", speed = 0.3, dir = null, spread = 1, size = 0.03, life = 0.8, gravity = 0, drag = 1.5, jitter = 0 }) {
    const col = new THREE.Color(color);
    let n = 0;
    for (const q of this.p) {
      if (n >= count) break;
      if (q.alive) continue;
      q.alive = true; q.age = 0; q.life = life * (0.7 + Math.random() * 0.6);
      q.pos.copy(pos);
      if (jitter) q.pos.add(new THREE.Vector3((Math.random() - .5) * jitter, (Math.random() - .5) * jitter, (Math.random() - .5) * jitter));
      const v = new THREE.Vector3(Math.random() - .5, Math.random() - .5, Math.random() - .5).normalize();
      if (dir) v.multiplyScalar(spread).add(dir).normalize();
      q.vel.copy(v).multiplyScalar(speed * (0.5 + Math.random() * 0.7));
      q.size = size * (0.6 + Math.random() * 0.8);
      q.col.copy(col).offsetHSL(0, 0, (Math.random() - .5) * 0.15);
      q.g = gravity; q.drag = drag;
      n++;
    }
  }
  update(dt, uPx) {
    this.material.uniforms.uPx.value = uPx;
    const P = this.geometry.attributes.position.array, C = this.geometry.attributes.pcolor.array,
      S = this.geometry.attributes.psize.array, A = this.geometry.attributes.palpha.array;
    this.p.forEach((q, i) => {
      if (q.alive) {
        q.age += dt;
        if (q.age >= q.life) q.alive = false;
        q.vel.y -= q.g * dt; // 卡片座標 y 朝上（畫面上方），重力往 -y
        q.vel.multiplyScalar(Math.exp(-q.drag * dt));
        q.pos.addScaledVector(q.vel, dt);
      }
      const k = q.alive ? q.age / q.life : 1;
      P[i * 3] = q.pos.x; P[i * 3 + 1] = q.pos.y; P[i * 3 + 2] = q.pos.z;
      C[i * 3] = q.col.r; C[i * 3 + 1] = q.col.g; C[i * 3 + 2] = q.col.b;
      S[i] = q.alive ? q.size * (1 - k * 0.5) : 0;
      A[i] = q.alive ? Math.min(1, (1 - k) * 1.6) : 0;
    });
    for (const k of ["position", "pcolor", "psize", "palpha"]) this.geometry.attributes[k].needsUpdate = true;
  }
  clear() { this.p.forEach((q) => { q.alive = false; }); }
  get alive() { return this.p.filter((q) => q.alive).length; }
}

// 遠紅外波紋（橘紅色、朝向鏡頭的擴散圓環）
export class Ripples extends THREE.Group {
  constructor(n = 12) {
    super();
    const geo = new THREE.RingGeometry(0.86, 1, 56);
    this.pool = [];
    for (let i = 0; i < n; i++) {
      const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: 0xef6c3c, transparent: true, opacity: 0,
        blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
      m.visible = false;
      m.renderOrder = 25;
      this.add(m);
      this.pool.push({ m, age: 0, life: 1, r0: 0.1, r1: 0.5, a: 0.8 });
    }
    this._cam = new THREE.Vector3();
  }
  emit(center, { r0 = 0.12, r1 = 0.55, life = 1.4, alpha = 0.85, color = 0xef6c3c } = {}) {
    const q = this.pool.find((p) => !p.m.visible) || this.pool[0];
    q.m.visible = true; q.m.position.copy(center); q.age = 0; q.life = life; q.r0 = r0; q.r1 = r1; q.a = alpha;
    q.m.material.color.set(color);
  }
  update(dt, camera) {
    camera.getWorldPosition(this._cam);
    for (const q of this.pool) {
      if (!q.m.visible) continue;
      q.age += dt;
      const k = q.age / q.life;
      if (k >= 1) { q.m.visible = false; continue; }
      const r = q.r0 + (q.r1 - q.r0) * ease.outCubic(k);
      q.m.scale.setScalar(r);
      q.m.material.opacity = q.a * (1 - k);
      q.m.lookAt(this._cam);
    }
  }
}

export function disposeTree(obj) {
  obj.traverse((o) => {
    if (o.geometry && !o.geometry.userData.shared) o.geometry.dispose();
    if (o.material) {
      const ms = Array.isArray(o.material) ? o.material : [o.material];
      ms.forEach((m) => { if (m.map && !m.map.userData.shared && m.map !== _glow) m.map.dispose(); m.dispose(); });
    }
  });
}
