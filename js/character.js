// 墨玉小晶：墨綠色蛇紋石晶體（六角柱＋上下錐）＋會轉向鏡頭的表情貼圖。
import * as THREE from "three";
import { canvasTexture, glowSprite } from "./fx.js";

function serpentineTexture() {
  // 墨玉斑點紋理（程式繪製）
  return canvasTexture(256, 256, (g, w, h) => {
    g.fillStyle = "#1d7a4c";
    g.fillRect(0, 0, w, h);
    let seed = 7;
    const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    for (let i = 0; i < 260; i++) {
      const x = rnd() * w, y = rnd() * h, r = 2 + rnd() * 9;
      g.fillStyle = rnd() < 0.5 ? `rgba(8,48,30,${0.35 + rnd() * 0.4})` : `rgba(140,230,180,${0.15 + rnd() * 0.3})`;
      g.beginPath();
      g.ellipse(x, y, r * (1 + rnd()), r, rnd() * 3, 0, Math.PI * 2);
      g.fill();
    }
    g.strokeStyle = "rgba(200,255,225,.25)";
    g.lineWidth = 2;
    for (let i = 0; i < 6; i++) {
      g.beginPath();
      g.moveTo(rnd() * w, 0);
      g.bezierCurveTo(rnd() * w, h * 0.3, rnd() * w, h * 0.6, rnd() * w, h);
      g.stroke();
    }
  });
}

function drawFace(g, W, expr, blink) {
  g.clearRect(0, 0, W, W);
  const cx = W / 2, ey = W * 0.42, dx = W * 0.2;
  g.lineCap = "round";
  g.lineJoin = "round";
  const ink = "#0b1f3a";
  const eyeOpen = (x, { pupil = 0.5, star = false, small = false } = {}) => {
    const rx = W * 0.085, ry = W * 0.105;
    g.fillStyle = "#fff";
    g.strokeStyle = ink;
    g.lineWidth = W * 0.022;
    g.beginPath(); g.ellipse(x, ey, rx, ry, 0, 0, Math.PI * 2); g.fill(); g.stroke();
    g.fillStyle = ink;
    const pr = small ? rx * 0.35 : rx * pupil * 1.25;
    g.beginPath(); g.ellipse(x, ey + ry * 0.12, pr, pr * 1.15, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#fff";
    g.beginPath(); g.arc(x - pr * 0.35, ey - pr * 0.25, pr * 0.38, 0, Math.PI * 2); g.fill();
    if (star) {
      g.fillStyle = "#ffe08a";
      g.beginPath(); g.arc(x + pr * 0.4, ey + pr * 0.45, pr * 0.22, 0, Math.PI * 2); g.fill();
    }
  };
  const eyeArc = (x, up = true) => {
    g.strokeStyle = ink; g.lineWidth = W * 0.035;
    g.beginPath();
    if (up) g.arc(x, ey + W * 0.03, W * 0.075, Math.PI * 1.1, Math.PI * 1.9);
    else g.arc(x, ey - W * 0.03, W * 0.075, Math.PI * 0.1, Math.PI * 0.9);
    g.stroke();
  };
  const blush = () => {
    g.fillStyle = "rgba(255,140,150,.55)";
    [-1, 1].forEach((s) => { g.beginPath(); g.ellipse(cx + s * W * 0.3, ey + W * 0.15, W * 0.07, W * 0.04, 0, 0, Math.PI * 2); g.fill(); });
  };
  const my = W * 0.68;
  if (blink && expr !== "happy") { eyeArc(cx - dx, false); eyeArc(cx + dx, false); }
  else if (expr === "happy") { eyeArc(cx - dx); eyeArc(cx + dx); }
  else if (expr === "sleepy") {
    g.strokeStyle = ink; g.lineWidth = W * 0.035;
    [-1, 1].forEach((s) => { g.beginPath(); g.moveTo(cx + s * dx - W * 0.07, ey + W * 0.02); g.lineTo(cx + s * dx + W * 0.07, ey + W * 0.02); g.stroke(); });
  } else if (expr === "surprised") { eyeOpen(cx - dx, { small: true }); eyeOpen(cx + dx, { small: true }); }
  else if (expr === "excited") { eyeOpen(cx - dx, { pupil: 0.62, star: true }); eyeOpen(cx + dx, { pupil: 0.62, star: true }); }
  else { eyeOpen(cx - dx); eyeOpen(cx + dx); }

  if (expr === "worried") {
    g.strokeStyle = ink; g.lineWidth = W * 0.03;
    [-1, 1].forEach((s) => { g.beginPath(); g.moveTo(cx + s * dx - s * W * 0.08, ey - W * 0.15); g.lineTo(cx + s * dx + s * W * 0.06, ey - W * 0.2); g.stroke(); });
    g.fillStyle = "#7dd3fc";
    g.beginPath(); g.moveTo(cx + W * 0.36, ey - W * 0.12); g.quadraticCurveTo(cx + W * 0.42, ey, cx + W * 0.36, ey + W * 0.02);
    g.quadraticCurveTo(cx + W * 0.3, ey, cx + W * 0.36, ey - W * 0.12); g.fill();
  }
  if (expr === "happy" || expr === "excited") blush();

  g.strokeStyle = ink; g.fillStyle = "#7a1f2b"; g.lineWidth = W * 0.03;
  g.beginPath();
  if (expr === "happy" || expr === "excited") {
    g.moveTo(cx - W * 0.12, my - W * 0.03);
    g.quadraticCurveTo(cx, my + W * 0.16, cx + W * 0.12, my - W * 0.03);
    g.closePath(); g.fill(); g.stroke();
  } else if (expr === "surprised") {
    g.ellipse(cx, my, W * 0.05, W * 0.065, 0, 0, Math.PI * 2); g.fill(); g.stroke();
  } else if (expr === "worried") {
    g.moveTo(cx - W * 0.09, my + W * 0.02);
    g.quadraticCurveTo(cx - W * 0.045, my - W * 0.03, cx, my + W * 0.01);
    g.quadraticCurveTo(cx + W * 0.045, my + W * 0.05, cx + W * 0.09, my); g.stroke();
  } else if (expr === "sleepy") {
    g.moveTo(cx - W * 0.05, my); g.lineTo(cx + W * 0.05, my); g.stroke();
    g.fillStyle = "#cfe8ff"; g.font = `800 ${W * 0.13}px sans-serif`; g.fillText("z", cx + W * 0.3, ey - W * 0.14);
  } else {
    g.arc(cx, my - W * 0.04, W * 0.09, Math.PI * 0.15, Math.PI * 0.85); g.stroke();
  }
}

export class Xiaojing extends THREE.Group {
  constructor() {
    super();
    this.name = "xiaojing";
    this.body = new THREE.Group();
    this.add(this.body);
    const tex = serpentineTexture();
    this.mat = new THREE.MeshStandardMaterial({ map: tex, color: 0xffffff, flatShading: true, roughness: 0.32,
      metalness: 0.12, emissive: new THREE.Color(0x1aa865), emissiveIntensity: 0.1 });
    const R = 0.42;
    const parts = [
      [new THREE.CylinderGeometry(R, R, 0.62, 6), 0],
      [new THREE.ConeGeometry(R, 0.46, 6), 0.54],
      [new THREE.ConeGeometry(R, 0.4, 6), -0.51],
    ];
    const edgeMat = new THREE.LineBasicMaterial({ color: 0xc8ffe2, transparent: true, opacity: 0.55 });
    parts.forEach(([geo, y], i) => {
      const m = new THREE.Mesh(geo, this.mat);
      m.position.y = y;
      if (i === 2) m.rotation.z = Math.PI;
      m.userData.xj = true;
      this.body.add(m);
      const e = new THREE.LineSegments(new THREE.EdgesGeometry(geo), edgeMat);
      e.position.copy(m.position); e.rotation.copy(m.rotation);
      this.body.add(e);
    });
    this.aura = glowSprite(0x4ade80, 2.0, 0.15);
    this.aura.renderOrder = -1;
    this.add(this.aura);
    this.heat = glowSprite(0xef6c3c, 2.6, 0);
    this.heat.renderOrder = -1;
    this.add(this.heat);

    this.faceCanvas = document.createElement("canvas");
    this.faceCanvas.width = this.faceCanvas.height = 256;
    this.faceTex = new THREE.CanvasTexture(this.faceCanvas);
    this.faceTex.colorSpace = THREE.SRGBColorSpace;
    this.face = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.faceTex, transparent: true, depthWrite: false }));
    this.face.scale.setScalar(0.7);
    this.face.renderOrder = 10;
    this.add(this.face);

    this.expr = "";
    this.blinkT = 2;
    this.blinking = false;
    this.energy = 0.15;
    this.glowBoost = 0;
    this.bob = 0;
    this.offset = new THREE.Vector3();
    this.spin = 0.4;
    this._cam = new THREE.Vector3();
    this.setFace("normal");
    this.setEnergy(0.15);
  }
  setFace(expr) {
    if (expr === this.expr && !this._dirty) return;
    this.expr = expr;
    drawFace(this.faceCanvas.getContext("2d"), 256, expr, this.blinking);
    this.faceTex.needsUpdate = true;
  }
  setEnergy(v) {
    this.energy = Math.max(0, Math.min(1, v));
    const dim = new THREE.Color(0x6b8a7a), bright = new THREE.Color(0xffffff);
    this.mat.color.copy(dim).lerp(bright, this.energy);
  }
  update(dt, t, camera) {
    this.body.rotation.y += dt * this.spin;
    this.body.position.set(this.offset.x, this.offset.y + Math.sin(t * 2.1) * 0.06, this.offset.z);
    const e = this.energy;
    const pulse = 0.5 + 0.5 * Math.sin(t * 3);
    this.mat.emissiveIntensity = 0.05 + e * 0.45 + this.glowBoost * 0.6 + pulse * 0.08 * e;
    this.aura.material.opacity = 0.12 + e * 0.35 + this.glowBoost * 0.3;
    this.aura.position.copy(this.body.position);
    this.heat.material.opacity = Math.max(0, (e - 0.6) * 1.1) * (0.6 + 0.4 * pulse);
    this.heat.position.copy(this.body.position);
    this.glowBoost = Math.max(0, this.glowBoost - dt * 0.8);
    // 眨眼
    this.blinkT -= dt;
    if (this.blinkT <= 0) {
      this.blinking = !this.blinking;
      this.blinkT = this.blinking ? 0.12 : 2 + Math.random() * 2.5;
      this._dirty = true; this.setFace(this.expr); this._dirty = false;
    }
    // 表情貼圖永遠朝向鏡頭
    camera.getWorldPosition(this._cam);
    this.worldToLocal(this._cam);
    const dir = this._cam.sub(this.body.position).normalize();
    this.face.position.copy(this.body.position).addScaledVector(dir, 0.5);
    this.face.position.y += 0.02;
  }
}
