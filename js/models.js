// 遊戲中的 3D 道具（全部程式繪製）：石塊、球磨罐、晶格、燒瓶、T 微胞、離子、離心機、烘箱、光譜儀。
import * as THREE from "three";
import { canvasTexture, glowSprite, makeLabel, FONT, roundRect } from "./fx.js";

let _stoneTex = null;
export function stoneTexture() {
  if (_stoneTex) return _stoneTex;
  _stoneTex = canvasTexture(256, 256, (g, w, h) => {
    g.fillStyle = "#2b6b4f"; g.fillRect(0, 0, w, h);
    let s = 11;
    const r = () => ((s = (s * 16807) % 2147483647) / 2147483647);
    for (let i = 0; i < 420; i++) {
      g.fillStyle = r() < 0.55 ? `rgba(10,40,30,${0.3 + r() * 0.5})` : `rgba(150,210,170,${0.2 + r() * 0.35})`;
      g.beginPath(); g.ellipse(r() * w, r() * h, 1 + r() * 6, 1 + r() * 4, r() * 3, 0, 7); g.fill();
    }
  });
  _stoneTex.wrapS = _stoneTex.wrapT = THREE.RepeatWrapping;
  _stoneTex.userData.shared = true;
  return _stoneTex;
}

export function stoneMaterial(extra = {}) {
  return new THREE.MeshStandardMaterial({ map: stoneTexture(), flatShading: true, roughness: 0.6, metalness: 0.05, ...extra });
}

// 不規則石塊（頂點雜訊，以位置雜湊保持接縫一致）
export function makeRock(r = 0.2, seed = 1) {
  const geo = new THREE.IcosahedronGeometry(1, 1);
  const p = geo.attributes.position;
  const v = new THREE.Vector3();
  for (let i = 0; i < p.count; i++) {
    v.fromBufferAttribute(p, i);
    const n = Math.sin(v.x * 7.1 + seed) * Math.cos(v.y * 5.3 - seed) + Math.sin(v.z * 6.7 + seed * 2);
    v.multiplyScalar(1 + n * 0.12).multiply(new THREE.Vector3(1.15, 0.85, 0.9));
    p.setXYZ(i, v.x, v.y, v.z);
  }
  geo.computeVertexNormals();
  const m = new THREE.Mesh(geo, stoneMaterial());
  m.scale.setScalar(r);
  return m;
}

// 晶格表面（蜂巢格：Mg 位與 Si 位兩種節點；6 個空位）
export function makeLattice() {
  const group = new THREE.Group();
  const a = 0.082;
  const nodes = [];
  const nodeIdx = new Map();
  const bonds = new Map();
  const key = (x, y) => `${Math.round(x * 500)},${Math.round(y * 500)}`;
  const addNode = (x, y, sub) => {
    const k = key(x, y);
    if (!nodeIdx.has(k)) { nodeIdx.set(k, nodes.length); nodes.push({ x, y, sub }); }
    return nodeIdx.get(k);
  };
  for (let i = 0; i < 7; i++) {
    for (let j = 0; j < 4; j++) {
      const cx = i * 1.5 * a - 0.37, cy = j * Math.sqrt(3) * a + (i % 2) * Math.sqrt(3) / 2 * a - 0.27;
      const ids = [];
      for (let k = 0; k < 6; k++) {
        const ang = (Math.PI / 3) * k;
        ids.push(addNode(cx + a * Math.cos(ang), cy + a * Math.sin(ang), k % 2));
      }
      for (let k = 0; k < 6; k++) {
        const A = ids[k], B = ids[(k + 1) % 6];
        bonds.set(A < B ? `${A}-${B}` : `${B}-${A}`, [Math.min(A, B), Math.max(A, B)]);
      }
    }
  }
  // 背板
  const plate = new THREE.Mesh(new THREE.PlaneGeometry(1.0, 0.74),
    new THREE.MeshBasicMaterial({ map: canvasTexture(400, 296, (g, w, h) => {
      const gr = g.createLinearGradient(0, 0, w, h);
      gr.addColorStop(0, "rgba(11,31,58,.82)"); gr.addColorStop(1, "rgba(6,90,130,.7)");
      g.fillStyle = gr; roundRect(g, 4, 4, w - 8, h - 8, 26); g.fill();
      g.strokeStyle = "rgba(167,243,208,.7)"; g.lineWidth = 4; g.stroke();
    }), transparent: true, depthWrite: false }));
  plate.position.set(0.02, -0.02, -0.03);
  group.add(plate);
  const cap = makeLabel("蛇紋石表面 Mg₃Si₂O₅(OH)₄（示意）", { height: 0.05, bg: "rgba(46,125,91,.92)" });
  cap.position.set(0.02, -0.43, 0.02);
  group.add(cap);

  // 空位（Mg 位中挑 6 個分散的位置）
  const wanted = [[-0.28, 0.13], [0.02, 0.2], [0.3, 0.12], [-0.22, -0.17], [0.08, -0.12], [0.33, -0.2]];
  const vacSet = new Set();
  wanted.forEach(([x, y]) => {
    let best = -1, bd = 1e9;
    nodes.forEach((n, i) => {
      if (n.sub !== 0 || vacSet.has(i)) return;
      const d = (n.x - x) ** 2 + (n.y - y) ** 2;
      if (d < bd) { bd = d; best = i; }
    });
    vacSet.add(best);
  });
  const mgGeo = new THREE.SphereGeometry(0.028, 16, 12);
  const siGeo = new THREE.SphereGeometry(0.021, 12, 10);
  const mgCount = nodes.filter((n, i) => n.sub === 0 && !vacSet.has(i)).length;
  const siCount = nodes.filter((n) => n.sub === 1).length;
  const mgMesh = new THREE.InstancedMesh(mgGeo, new THREE.MeshStandardMaterial({ color: 0x22d3c5, roughness: 0.35, emissive: 0x0b5f58, emissiveIntensity: 0.4 }), mgCount);
  const siMesh = new THREE.InstancedMesh(siGeo, new THREE.MeshStandardMaterial({ color: 0xdbe7ef, roughness: 0.4 }), siCount);
  const mtx = new THREE.Matrix4();
  let im = 0, is = 0;
  nodes.forEach((n, i) => {
    mtx.makeTranslation(n.x, n.y, 0);
    if (n.sub === 0 && !vacSet.has(i)) mgMesh.setMatrixAt(im++, mtx);
    if (n.sub === 1) siMesh.setMatrixAt(is++, mtx);
  });
  group.add(mgMesh, siMesh);

  // 鍵（細圓柱，個別顏色）
  const bondList = [...bonds.values()];
  const bondGeo = new THREE.CylinderGeometry(0.0075, 0.0075, 1, 6);
  const bondMesh = new THREE.InstancedMesh(bondGeo, new THREE.MeshBasicMaterial({ color: 0xffffff }), bondList.length);
  const up = new THREE.Vector3(0, 1, 0), q = new THREE.Quaternion(), s = new THREE.Vector3(), pos = new THREE.Vector3();
  const OK = new THREE.Color(0x7cc8b8), BROKEN = new THREE.Color(0x6b3b3b), LIT = new THREE.Color(0xb6ffe6);
  bondList.forEach(([A, B], i) => {
    const na = nodes[A], nb = nodes[B];
    const d = new THREE.Vector3(nb.x - na.x, nb.y - na.y, 0);
    const len = d.length();
    q.setFromUnitVectors(up, d.normalize());
    pos.set((na.x + nb.x) / 2, (na.y + nb.y) / 2, 0);
    s.set(1, len, 1);
    mtx.compose(pos, q, s);
    bondMesh.setMatrixAt(i, mtx);
    const broken = vacSet.has(A) || vacSet.has(B);
    bondMesh.setColorAt(i, broken ? BROKEN : OK);
  });
  bondMesh.instanceColor.needsUpdate = true;
  group.add(bondMesh);

  // 空位標記（發亮缺口）
  const vacancies = [...vacSet].map((ni) => {
    const n = nodes[ni];
    const ring = new THREE.Mesh(new THREE.RingGeometry(0.03, 0.042, 32),
      new THREE.MeshBasicMaterial({ color: 0xffd36b, transparent: true, opacity: 0.95, side: THREE.DoubleSide, depthWrite: false }));
    ring.position.set(n.x, n.y, 0.004);
    const glow = glowSprite(0xffc94d, 0.16, 0.85);
    glow.position.set(n.x, n.y, 0.01);
    const filler = new THREE.Mesh(mgGeo, new THREE.MeshStandardMaterial({ color: 0x5ff5e6, emissive: 0x22d3c5, emissiveIntensity: 0.9 }));
    filler.position.set(n.x, n.y, 0);
    filler.visible = false;
    group.add(ring, glow, filler);
    const bondIds = bondList.map((b, i) => (b[0] === ni || b[1] === ni ? i : -1)).filter((i) => i >= 0);
    return { node: ni, pos: new THREE.Vector3(n.x, n.y, 0), ring, glow, filler, bondIds, filled: false };
  });
  const api = {
    group, nodes, vacancies, bondMesh,
    show(v) { vacancies.forEach((x) => { x.ring.visible = v && !x.filled; x.glow.visible = v && !x.filled; }); },
    fill(i) {
      const vac = vacancies[i];
      vac.filled = true; vac.ring.visible = false; vac.glow.visible = false; vac.filler.visible = true;
      vac.bondIds.forEach((b) => bondMesh.setColorAt(b, LIT));
      bondMesh.instanceColor.needsUpdate = true;
    },
    get filledCount() { return vacancies.filter((v) => v.filled).length; },
    update(t) {
      vacancies.forEach((v, i) => {
        if (v.filled) { v.filler.scale.setScalar(1 + 0.08 * Math.sin(t * 4 + i)); return; }
        const k = 0.5 + 0.5 * Math.sin(t * 5 + i);
        v.glow.material.opacity = 0.45 + 0.5 * k;
        v.ring.scale.setScalar(0.9 + 0.25 * k);
      });
    },
  };
  return api;
}

// 圓底燒瓶（Lathe）＋可調液面
export function makeFlask() {
  const group = new THREE.Group();
  const R = 0.17;
  const pts = [];
  for (let i = 0; i <= 20; i++) {
    const a = -Math.PI / 2 + (i / 20) * (Math.PI * 0.86);
    pts.push(new THREE.Vector2(Math.cos(a) * R + 0.0005, Math.sin(a) * R));
  }
  pts.push(new THREE.Vector2(0.045, R * 1.08), new THREE.Vector2(0.045, R * 1.9), new THREE.Vector2(0.058, R * 1.95));
  const glass = new THREE.Mesh(new THREE.LatheGeometry(pts, 40), new THREE.MeshStandardMaterial({
    color: 0xd9f2ff, transparent: true, opacity: 0.28, roughness: 0.05, metalness: 0.1, side: THREE.DoubleSide, depthWrite: false }));
  glass.renderOrder = 5;
  const rim = new THREE.Mesh(new THREE.TorusGeometry(0.058, 0.008, 8, 32), new THREE.MeshStandardMaterial({ color: 0xe8f7ff }));
  rim.rotation.x = Math.PI / 2;
  rim.position.y = R * 1.95;
  const liquidMat = new THREE.MeshStandardMaterial({ color: 0x7fd3ff, transparent: true, opacity: 0.6, roughness: 0.2,
    emissive: 0x0a3b5c, emissiveIntensity: 0.3, depthWrite: false, side: THREE.DoubleSide });
  const liquid = new THREE.Mesh(new THREE.BufferGeometry(), liquidMat);
  liquid.renderOrder = 4;
  liquid.visible = false;
  group.add(liquid, glass, rim);
  const api = {
    group, glass, liquid, R, level: 0,
    setLevel(h) { // 0..1（佔球體高度比例）
      api.level = h;
      liquid.visible = h > 0.01;
      if (!liquid.visible) return;
      const r = R * 0.94;
      const top = -r + 2 * r * Math.min(0.92, h);
      const lp = [];
      for (let i = 0; i <= 16; i++) {
        const y = -r + (top + r) * (i / 16);
        lp.push(new THREE.Vector2(Math.sqrt(Math.max(0, r * r - y * y)) + 0.0005, y));
      }
      lp.push(new THREE.Vector2(0.0001, top));
      liquid.geometry.dispose();
      liquid.geometry = new THREE.LatheGeometry(lp, 36);
    },
  };
  return api;
}

// T 微胞：疏水核＋外圈親水小尾
const _micelleTail = new THREE.SphereGeometry(1, 8, 6);
_micelleTail.userData.shared = true;
export function makeMicelle(r = 0.035) {
  const g = new THREE.Group();
  const core = new THREE.Mesh(new THREE.SphereGeometry(r * 0.62, 16, 12), new THREE.MeshStandardMaterial({ color: 0xf2a541, emissive: 0x7a4410, emissiveIntensity: 0.4, roughness: 0.5 }));
  g.add(core);
  const tailMat = new THREE.MeshStandardMaterial({ color: 0x9ad8ff, emissive: 0x1c7293, emissiveIntensity: 0.35 });
  const n = 14;
  for (let i = 0; i < n; i++) {
    const y = 1 - (i / (n - 1)) * 2, rad = Math.sqrt(1 - y * y), th = i * 2.399;
    const dir = new THREE.Vector3(Math.cos(th) * rad, y, Math.sin(th) * rad);
    const head = new THREE.Mesh(_micelleTail, tailMat);
    head.scale.setScalar(r * 0.2);
    head.position.copy(dir).multiplyScalar(r);
    g.add(head);
  }
  return g;
}

// 離子：發光球＋化學式標籤；附較大的隱形點擊範圍
export function makeIon(kind) {
  const isMg = kind === "Mg";
  const g = new THREE.Group();
  g.userData.kind = kind;
  const r = isMg ? 0.042 : 0.064;
  const col = isMg ? 0x22d3c5 : 0x2f8f4e;
  const ball = new THREE.Mesh(new THREE.SphereGeometry(r, 20, 14), new THREE.MeshStandardMaterial({ color: col, emissive: col, emissiveIntensity: 0.45, roughness: 0.3 }));
  g.add(ball);
  const glow = glowSprite(isMg ? 0x5ff5e6 : 0x8fe3a5, r * 4.2, 0.55);
  g.add(glow);
  const lab = makeLabel(isMg ? "Mg²⁺" : "Ca²⁺", { height: 0.045, bg: isMg ? "rgba(6,90,130,.9)" : "rgba(20,83,45,.92)" });
  lab.position.set(0, r + 0.035, 0.01);
  g.add(lab);
  const hit = new THREE.Mesh(new THREE.SphereGeometry(isMg ? 0.095 : 0.1, 8, 6), new THREE.MeshBasicMaterial({ visible: false }));
  g.add(hit);
  g.userData.r = r;
  g.userData.ball = ball;
  return g;
}

export function makeFe() {
  const g = new THREE.Group();
  const ball = new THREE.Mesh(new THREE.SphereGeometry(0.026, 16, 12), new THREE.MeshStandardMaterial({ color: 0xffc940, emissive: 0xc98a12, emissiveIntensity: 0.6, metalness: 0.4, roughness: 0.25 }));
  g.add(ball, glowSprite(0xffd76a, 0.11, 0.6));
  return g;
}

// 瓶子（試劑）
export function makeBottle(label, color = 0xffffff) {
  const g = new THREE.Group();
  const body = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.13, 20), new THREE.MeshStandardMaterial({ color, transparent: true, opacity: 0.85, roughness: 0.2 }));
  const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.035, 0.05, 16), body.material);
  neck.position.y = 0.09;
  const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.023, 0.023, 0.025, 16), new THREE.MeshStandardMaterial({ color: 0x334155 }));
  cap.position.y = 0.125;
  const lab = makeLabel(label, { height: 0.045 });
  lab.position.set(0, -0.11, 0.06);
  g.add(body, neck, cap, lab);
  return g;
}

// 光譜圖（canvas 動態重畫）
export function makeChart() {
  const W = 640, H = 400;
  const c = document.createElement("canvas");
  c.width = W; c.height = H;
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(0.84, 0.525), new THREE.MeshBasicMaterial({ map: tex, transparent: true }));
  const g = c.getContext("2d");
  const frame = (title, xl) => {
    g.clearRect(0, 0, W, H);
    g.fillStyle = "rgba(245,249,250,.97)"; roundRect(g, 4, 4, W - 8, H - 8, 26); g.fill();
    g.strokeStyle = "#1c7293"; g.lineWidth = 6; g.stroke();
    g.fillStyle = "#0b1f3a"; g.font = `800 38px ${FONT}`; g.textAlign = "left"; g.fillText(title, 26, 52);
    g.strokeStyle = "#94a3b8"; g.lineWidth = 3;
    g.beginPath(); g.moveTo(60, 80); g.lineTo(60, 330); g.lineTo(W - 30, 330); g.stroke();
    g.fillStyle = "#475569"; g.font = `700 28px ${FONT}`; g.fillText(xl, 66, 370);
    g.fillStyle = "#b45309"; g.font = `800 24px ${FONT}`; g.textAlign = "right"; g.fillText("簡化示意圖，非真實數據", W - 24, 372);
  };
  const api = {
    mesh,
    ftir(progress) {
      frame("FTIR 光譜（示意）", "波數 →");
      const x0 = 62, x1 = W - 34;
      const f = (u) => 110 + 30 * Math.sin(u * 9) * 0.1 + 150 * Math.exp(-((u - 0.18) ** 2) / 0.0006) + 190 * Math.exp(-((u - 0.7) ** 2) / 0.003) + 60 * Math.exp(-((u - 0.82) ** 2) / 0.0015);
      g.strokeStyle = "#065a82"; g.lineWidth = 5; g.beginPath();
      const n = Math.floor(200 * progress);
      for (let i = 0; i <= n; i++) {
        const u = i / 200, x = x0 + (x1 - x0) * u, y = 100 + f(u) * 0.95;
        if (i === 0) g.moveTo(x, y); else g.lineTo(x, Math.min(325, y));
      }
      g.stroke();
      g.textAlign = "center"; g.font = `800 30px ${FONT}`;
      if (progress > 0.25) { g.fillStyle = "#2e7d5b"; g.fillText("–OH", x0 + (x1 - x0) * 0.18 + 52, 300); }
      if (progress > 0.75) { g.fillStyle = "#2e7d5b"; g.fillText("Si–O", x0 + (x1 - x0) * 0.7 - 62, 300); }
      tex.needsUpdate = true;
    },
    emission(mode, progress = 1) {
      frame("4–14 微米 遠紅外放射（示意）", "波長 4 → 14 微米");
      const x0 = 62, x1 = W - 34;
      const curve = (amp, color, dash) => {
        g.setLineDash(dash ? [16, 10] : []);
        g.strokeStyle = color; g.lineWidth = 6; g.beginPath();
        const n = Math.floor(160 * progress);
        for (let i = 0; i <= n; i++) {
          const u = i / 160, x = x0 + (x1 - x0) * u;
          const y = 320 - amp * (Math.exp(-((u - 0.45) ** 2) / 0.09)) - 12;
          if (i === 0) g.moveTo(x, y); else g.lineTo(x, y);
        }
        g.stroke(); g.setLineDash([]);
      };
      curve(120, mode === "before" ? "#ef6c3c" : "rgba(239,108,60,.35)", false);
      g.font = `800 30px ${FONT}`; g.textAlign = "left";
      g.fillStyle = mode === "before" ? "#c2410c" : "rgba(194,65,12,.45)"; g.fillText("修復前", 76, 205);
      if (mode === "after") {
        curve(200, "#e11d48", true);
        g.fillStyle = "#be123c"; g.fillText("修復後（預期）", x0 + (x1 - x0) * 0.5, 104);
      }
      tex.needsUpdate = true;
    },
  };
  return api;
}

export function labelPanel(text, opts) { return makeLabel(text, opts); }
