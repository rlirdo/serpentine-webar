// 遊戲核心：狀態機、八關、前後測評量。與主機（AR／無相機）無關。
// export function createGame({ stage, camera, renderer, hud, host })
//   stage   ：THREE.Group，以任務卡寬度為 1 單位（卡片在 XY 平面、z 朝鏡頭）
//   host    ：{ mode: "ar" | "play", inputEl, audio, autoplay }
import * as THREE from "three";
import { BANK, CREDIT, ENDING, FACETS, FACET_NAMES, GRADE_ASK, GRADE_LABEL, INTRO, LEVELS, STORE_KEY, TITLE } from "./content.js";
import { Tweens, ease, makeLabel, glowSprite, Particles, Ripples, disposeTree } from "./fx.js";
import { Xiaojing } from "./character.js";
import { makeRock, stoneMaterial, makeLattice, makeFlask, makeMicelle, makeIon, makeFe, makeBottle, makeChart } from "./models.js";

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const HOME = V(-0.38, 0.33, 0.34), HOME_S = 0.15;
const CENTER = V(0, 0.04, 0.38), CENTER_S = 0.3;
const rand = (a, b) => a + Math.random() * (b - a);
const shuffle = (arr) => { const a = [...arr]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const starsHtml = (n) => `<span class="big-stars">${"★".repeat(n)}<span class="off">${"★".repeat(3 - n)}</span></span>`;

export function createGame({ stage, camera, renderer, hud, host }) {
  const audio = host.audio;
  const tw = new Tweens();
  const wait = (s) => tw.wait(s);
  const S = { grade: "elem", pre: [], post: [], stars: Array(8).fill(0), commit: null, level: -1, irRate: 0, irTimer: 0 };
  const T = (x) => (x == null ? "" : typeof x === "string" ? x : x[S.grade] || x.elem);
  let updaters = [];
  const onUpdate = (fn) => { updaters.push(fn); return fn; };

  // ---------- 場景 ----------
  const hemi = new THREE.HemisphereLight(0xe6fbff, 0x1d3b33, 1.6);
  const dir = new THREE.DirectionalLight(0xffffff, 2.2);
  dir.position.set(0.6, 0.9, 1.4);
  stage.add(hemi, dir, dir.target);
  const xj = new Xiaojing();
  xj.position.copy(CENTER);
  xj.scale.setScalar(0.001);
  stage.add(xj);
  const lab = new THREE.Group(); // 每關的道具
  const keep = new THREE.Group(); // 跨關保留（晶格、燒瓶）
  stage.add(lab, keep);
  const particles = new Particles(150);
  const ripples = new Ripples(12);
  stage.add(particles, ripples);
  const persist = {};
  const _v = new THREE.Vector3();
  const _size = new THREE.Vector2();

  const xjWorldCenter = () => xj.localToWorld(xj.body.position.clone());
  const xjStagePos = () => stage.worldToLocal(xjWorldCenter());
  const burst = (pos, color, count = 24, o = {}) => particles.emit({ pos, count, color, speed: 0.5, size: 0.035, life: 0.9, ...o });

  function moveXj(pos, s, dur = 0.8) {
    const p0 = xj.position.clone(), s0 = xj.scale.x;
    return tw.add(dur, (k) => { xj.position.lerpVectors(p0, pos, k); xj.scale.setScalar(s0 + (s - s0) * k); }, ease.inOutSine);
  }
  function hop(obj = xj, h = 0.05) {
    const y0 = obj.position.y;
    return tw.add(0.45, (k) => { obj.position.y = y0 + Math.sin(k * Math.PI) * h; }, ease.linear);
  }
  function shake(obj, amp = 0.02, dur = 0.4) {
    const x0 = obj.position.x;
    return tw.add(dur, (k) => { obj.position.x = x0 + Math.sin(k * 40) * amp * (1 - k); }, ease.linear);
  }
  // 以物件原始比例（例如文字貼圖的寬高比）為基準縮放
  const baseScale = (obj) => obj.userData.bs || (obj.userData.bs = obj.scale.clone());
  function popIn(obj, s = 1, dur = 0.5) {
    const b = baseScale(obj);
    obj.scale.copy(b).multiplyScalar(0.001);
    return tw.add(dur, (k) => obj.scale.copy(b).multiplyScalar(Math.max(0.001, s * k)), ease.outBack);
  }
  function popOut(obj, dur = 0.35) { const s0 = obj.scale.clone(); return tw.add(dur, (k) => obj.scale.copy(s0).multiplyScalar(Math.max(0.001, 1 - k)), ease.inCubic); }
  function irBurst(n = 3, strong = 1) {
    const c = xjStagePos();
    for (let i = 0; i < n; i++) setTimeout(() => ripples.emit(c, { r0: 0.1, r1: 0.32 + 0.14 * strong, life: 1.3, alpha: 0.4 + 0.3 * strong }), i * 180);
  }

  // ---------- 點擊（raycast） ----------
  const raycaster = new THREE.Raycaster();
  let taps = [];
  const onTap = (obj, fn) => taps.push({ obj, fn });
  const offTap = (obj) => { taps = taps.filter((t) => t.obj !== obj); };
  const visibleDeep = (o) => { while (o) { if (!o.visible) return false; o = o.parent; } return true; };
  function tapAt(ndc) {
    if (!taps.length) return false;
    raycaster.setFromCamera(ndc, camera);
    const objs = taps.map((t) => t.obj).filter(visibleDeep);
    const hits = raycaster.intersectObjects(objs, true);
    for (const h of hits) {
      let o = h.object;
      while (o && !taps.find((t) => t.obj === o)) o = o.parent;
      const t = o && taps.find((x) => x.obj === o);
      if (t) { t.fn(o); return true; }
    }
    return false;
  }
  // 自動通關：把物件投影到螢幕後走同一條 raycast 路徑
  function apTap(obj) {
    stage.updateMatrixWorld(true);
    obj.getWorldPosition(_v).project(camera);
    if (!tapAt(new THREE.Vector2(_v.x, _v.y))) {
      const t = taps.find((x) => x.obj === obj);
      console.warn("autoplay: raycast miss, direct call", obj.name);
      if (t) t.fn(obj);
    }
  }
  if (host.inputEl) {
    let down = null;
    host.inputEl.addEventListener("pointerdown", (e) => { down = { x: e.clientX, y: e.clientY, t: performance.now() }; audio.unlock(); });
    host.inputEl.addEventListener("pointerup", (e) => {
      if (!down) return;
      const d = Math.hypot(e.clientX - down.x, e.clientY - down.y);
      if (d < 14 && performance.now() - down.t < 800) {
        const r = host.inputEl.getBoundingClientRect();
        tapAt(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1));
      }
      down = null;
    });
  }

  function clearLab() {
    taps = [];
    updaters = [];
    [...lab.children].forEach((c) => { lab.remove(c); disposeTree(c); });
    hud.meter(false);
  }

  // ---------- 開場 ----------
  async function intro() {
    hud.setTitle(TITLE);
    hud.setProgress(-1, 0);
    await wait(0.2);
    audio.fanfare();
    xj.setFace("happy");
    burst(CENTER.clone(), "#7ef0b4", 40, { speed: 0.7 });
    await tw.add(0.8, (k) => xj.scale.setScalar(Math.max(0.001, CENTER_S * k)), ease.outBack);
    xj.position.copy(CENTER);
    for (let i = 0; i < INTRO.length; i++) {
      xj.setFace(INTRO[i].face);
      if (i === 3) { hop(); burst(CENTER.clone(), "#ffd76a", 20); }
      await hud.next(INTRO[i].text, { ap: `intro-${i + 1}` });
    }
    const g = await hud.choose(GRADE_ASK, ["國小版（五、六年級）", "國中版"], { ap: "grade", apPick: host.apGrade === "junior" ? 1 : 0, cls: "gold" });
    S.grade = g === 1 ? "junior" : "elem";
    if (hud.speech) hud.speech.setGrade(S.grade); // 語速：國小版 0.95、國中版 1.05
    hud.toast(`已選擇${GRADE_LABEL[S.grade]}`);
    xj.setFace("normal");
    await hud.next("出發前，先做 3 題小測驗，看看你現在知道多少。答錯沒關係！", { label: "開始前測 ▶", cls: "gold", ap: "pre-intro" });
  }

  // ---------- 測驗 ----------
  function askOne(kind, i, n, q) {
    return new Promise((resolve) => {
      const order = shuffle([0, 1, 2, 3]);
      const isPre = kind === "pre";
      const m = hud.modal(`
        <div class="kicker">${isPre ? "前測" : "後測"} ${i + 1} / ${n}${isPre ? "・答錯沒關係" : ""}</div>
        <div class="q">${q.q}<span class="facet-chip">${FACET_NAMES[q.facet]}</span></div>
        <div class="opts">${order.map((o, k) => `<button class="opt" data-o="${o}"><b>${"ABCD"[k]}</b>${q.options[o]}</button>`).join("")}</div>
        <div class="after"></div>`, {
        // 語音：題目＋四個選項（A、…；B、…）
        speech: `${isPre ? "前測" : "後測"}第 ${i + 1} 題。${q.q}\n${order.map((o, k) => `${"ABCD"[k]}、${q.options[o]}`).join("；")}。`,
      });
      const btns = [...m.querySelectorAll(".opt")];
      let done = false;
      btns.forEach((b) => b.addEventListener("click", () => {
        if (done) return;
        done = true;
        const o = Number(b.dataset.o);
        const correct = o === q.answer;
        (isPre ? S.pre : S.post).push({ id: q.id, facet: q.facet, correct });
        if (isPre) {
          b.classList.add("picked");
          audio.tap();
          setTimeout(() => resolve(), 450);
          hud.setAP(`${kind}-q${i + 1}-picked`, null);
        } else {
          btns.forEach((x) => { if (Number(x.dataset.o) === q.answer) x.classList.add("right"); });
          if (!correct) b.classList.add("wrong");
          correct ? audio.good() : audio.bad();
          const after = m.querySelector(".after");
          after.innerHTML = `<div class="explain">${correct ? "✔ 答對了！" : "✘ 再想想："}${q.explain}</div>
            <div class="row"><button class="btn gold nextq">${i + 1 < n ? "下一題 ▶" : "完成 ▶"}</button></div>`;
          if (hud.speech) hud.speech.speak(`${correct ? "✔ 答對了！" : "✘ 再想想："}${q.explain}`, { kind: "explain" });
          const nb = after.querySelector(".nextq");
          nb.addEventListener("click", () => resolve());
          hud.setAP(`${kind}-q${i + 1}-explain`, () => nb.click());
        }
      }));
      // 自動通關：前測前兩題故意答錯、第三題答對；後測全對（用來檢查進步比較畫面）
      hud.setAP(`${kind}-q${i + 1}`, () => {
        const wantRight = !isPre || i === 2;
        const pick = btns.find((b) => (Number(b.dataset.o) === q.answer) === wantRight);
        pick.click();
      });
    });
  }
  async function quiz(kind) {
    const bank = BANK[S.grade];
    const pre = bank.filter((q) => q.pre);
    let qs = pre;
    if (kind === "post") {
      const act = shuffle(bank.filter((q) => !q.pre && q.facet === "行動"))[0];
      const other = shuffle(bank.filter((q) => !q.pre && q.facet !== "行動"))[0];
      qs = [...pre, act, other];
    }
    hud.showPanel(false);
    for (let i = 0; i < qs.length; i++) await askOne(kind, i, qs.length, qs[i]);
    hud.closeModal();
  }

  // ---------- 關卡框架 ----------
  async function level(i) {
    const L = LEVELS[i];
    S.level = i;
    hud.setTitle(`第 ${i + 1} 關・${L.name}`);
    hud.setProgress(i, i);
    clearLab();
    if (xj.position.distanceTo(HOME) > 0.01) await moveXj(HOME, HOME_S, 0.7);
    xj.setFace(S.irRate > 0 ? "happy" : i === 0 ? "normal" : "normal");
    await hud.next(`<b>${L.step}</b><span class="sub">${L.intro.map(T).join("<br>")}</span>`, { label: "開始 ▶", cls: "gold", ap: `L${i + 1}-intro` });
    const mistakes = await LEVEL_FNS[i](L);
    const stars = Math.max(1, 3 - mistakes);
    S.stars[i] = stars;
    hud.setStars(S.stars.reduce((a, b) => a + b, 0));
    hud.setProgress(i, i + 1);
    hud.meter(false);
    xj.setFace("happy");
    hop();
    burst(xjStagePos(), "#ffd76a", 30, { speed: 0.6 });
    for (let k = 0; k < stars; k++) setTimeout(() => audio.star(k), 200 + k * 180);
    await hud.next(`<b>第 ${i + 1} 關完成！</b>${starsHtml(stars)}<span class="sub">${T(L.learn)}</span><span class="tip">🌱 環境小語：${L.tip}</span>`,
      { label: i < 7 ? "下一關 ▶" : "前往後測 ▶", cls: "gold", ap: `L${i + 1}-done`,
        speech: `第 ${i + 1} 關完成！得到 ${stars} 顆星。\n${T(L.learn)}\n環境小語：${L.tip}` });
  }

  // ---------- 第 1 關：切割／顎碎／粉碎 ----------
  function L1(L) {
    return new Promise((resolve) => {
      const W = V(0.1, -0.06, 0.16);
      let phase = 0, busy = false;
      let pieces = new THREE.Group();
      lab.add(pieces);
      const rock = makeRock(0.22, 2);
      rock.position.copy(W);
      pieces.add(rock);
      popIn(rock, 0.22, 0.6);
      onUpdate((dt) => { if (phase === 0) rock.rotation.y += dt * 0.4; });
      const area = ["小", "變大", "更大", "超大！"];
      hud.say(`${L.hint}`);
      hud.meter(true, "露出來的表面積", 0.1, area[0]);
      const register = () => {
        taps = [];
        onTap(pieces, hit);
        hud.setAP(`L1-tap${phase + 1}`, () => apTap(pieces.children[0]));
      };
      async function hit() {
        if (busy || phase >= 3) return;
        busy = true; phase++;
        audio.crack();
        burst(W.clone(), "#9fd9b8", 30, { speed: 0.8, size: 0.03, gravity: 0.6 });
        xj.setFace("surprised");
        shake(pieces, 0.03, 0.3);
        await wait(0.3);
        const old = pieces;
        lab.remove(old); disposeTree(old);
        pieces = new THREE.Group();
        lab.add(pieces);
        if (phase === 1) {
          for (let k = 0; k < 4; k++) {
            const s = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.06, 0.26), stoneMaterial());
            s.position.copy(W);
            s.rotation.set(rand(-0.15, 0.15), rand(-0.4, 0.4), rand(-0.1, 0.1));
            pieces.add(s);
            const ty = W.y + (k - 1.5) * 0.11;
            tw.add(0.5, (e) => { s.position.y = W.y + (ty - W.y) * e; }, ease.outBack);
          }
        } else if (phase === 2) {
          for (let k = 0; k < 14; k++) {
            const c = makeRock(rand(0.035, 0.05), k + 3);
            const tx = W.x + rand(-0.26, 0.26), ty = W.y + rand(-0.18, 0.16);
            c.position.copy(W);
            c.rotation.set(rand(0, 3), rand(0, 3), 0);
            pieces.add(c);
            tw.add(0.55, (e) => { c.position.x = W.x + (tx - W.x) * e; c.position.y = W.y + (ty - W.y) * e; }, ease.outBack);
          }
        } else {
          const pile = new THREE.Mesh(new THREE.SphereGeometry(0.22, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2), stoneMaterial({ flatShading: false, color: 0xbfe8cf }));
          pile.scale.set(1, 0.55, 0.8);
          pile.position.set(W.x, W.y - 0.12, W.z);
          pieces.add(pile);
          popIn(pile, 1, 0.5);
          const pl = makeLabel("粗粉", { height: 0.06, bg: "rgba(46,125,91,.92)" });
          pl.position.set(W.x, W.y + 0.06, W.z + 0.15);
          pieces.add(pl);
          particles.emit({ pos: W.clone(), count: 40, color: "#7fbf9a", speed: 0.4, size: 0.022, life: 1.4, gravity: 0.25, jitter: 0.25 });
        }
        hud.meter(true, "露出來的表面積", [0.1, 0.35, 0.65, 1][phase], area[phase]);
        hud.toast(L.phases[phase - 1]);
        await wait(0.6);
        xj.setFace("happy");
        busy = false;
        if (phase >= 3) { hud.clearButtons(); await wait(0.6); resolve(0); return; }
        register();
      }
      hud.buttons([{ label: "敲碎！", cls: "gold", onClick: hit }]);
      register();
    });
  }

  // ---------- 第 2 關：球磨微米化 ----------
  function L2(L) {
    return new Promise((resolve) => {
      const W = V(0.1, -0.04, 0.12);
      const mill = new THREE.Group();
      mill.position.copy(W);
      lab.add(mill);
      const disk = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.3, 0.03, 48), new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.5, roughness: 0.4 }));
      disk.rotation.x = Math.PI / 2;
      mill.add(disk);
      const sun = new THREE.Group();
      sun.position.z = 0.03;
      mill.add(sun);
      const jars = [];
      for (let j = 0; j < 2; j++) {
        const jar = new THREE.Group();
        const ang = j * Math.PI;
        jar.position.set(Math.cos(ang) * 0.15, Math.sin(ang) * 0.15, 0.06);
        const shell = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.11, 0.12, 32, 1, true), new THREE.MeshStandardMaterial({ color: 0xdff6ff, transparent: true, opacity: 0.3, side: THREE.DoubleSide, depthWrite: false }));
        shell.rotation.x = Math.PI / 2;
        const lid = new THREE.Mesh(new THREE.TorusGeometry(0.11, 0.012, 8, 32), new THREE.MeshStandardMaterial({ color: 0xcbd5e1, metalness: 0.7, roughness: 0.3 }));
        lid.position.z = 0.06;
        jar.add(shell, lid);
        const balls = [];
        for (let b = 0; b < 5; b++) {
          const ball = new THREE.Mesh(new THREE.SphereGeometry(0.022, 12, 10), new THREE.MeshStandardMaterial({ color: 0xe2e8f0, metalness: 0.9, roughness: 0.15 }));
          jar.add(ball); balls.push(ball);
        }
        const grains = new THREE.InstancedMesh(new THREE.DodecahedronGeometry(0.014), stoneMaterial(), 14);
        jar.add(grains);
        jar.userData = { balls, grains, seeds: Array.from({ length: 14 }, () => [rand(0, 6.28), rand(0.02, 0.085), rand(-0.04, 0.04)]) };
        sun.add(jar); jars.push(jar);
      }
      popIn(mill, 1, 0.5);
      let prog = 0, holding = false, speed = 0, done = false;
      const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), sc = new THREE.Vector3(), p = new THREE.Vector3();
      const sizeText = (k) => (k < 0.34 ? "粗粉" : k < 0.67 ? "細粉" : k < 1 ? "更細的粉" : "約 2–4 微米！");
      hud.say(L.hint);
      hud.meter(true, "粒徑", 0, "粗粉");
      onUpdate((dt, t) => {
        if (holding && !done) prog = Math.min(1, prog + dt / 2.6);
        speed += ((holding ? 9 : 0) - speed) * Math.min(1, dt * 3);
        sun.rotation.z += speed * dt * 0.6;
        jars.forEach((jar, ji) => {
          jar.rotation.z -= speed * dt * 1.4;
          jar.userData.balls.forEach((b, bi) => {
            const a = t * (2 + speed) + bi * 1.3 + ji;
            const r = 0.06 + 0.02 * Math.sin(t * 7 + bi);
            b.position.set(Math.cos(a) * r, Math.sin(a) * r, Math.sin(bi + t * 3) * 0.03);
          });
          const gsize = 1 - prog * 0.75;
          jar.userData.seeds.forEach(([a, r, z], gi) => {
            const aa = a + t * (0.5 + speed * 0.4);
            p.set(Math.cos(aa) * r, Math.sin(aa) * r, z);
            sc.setScalar(gsize);
            m4.compose(p, q, sc);
            jar.userData.grains.setMatrixAt(gi, m4);
          });
          jar.userData.grains.instanceMatrix.needsUpdate = true;
        });
        if (holding && Math.random() < 0.5) particles.emit({ pos: W.clone().add(V(rand(-0.25, 0.25), rand(-0.25, 0.25), 0.1)), count: 1, color: "#fff3b0", speed: 0.6, size: 0.02, life: 0.3 });
        if (holding) audio.humPitch(80 + speed * 25);
        hud.meter(true, "粒徑", prog, sizeText(prog));
        if (prog >= 1 && !done) { done = true; finish(); }
      });
      const [hb] = hud.buttons([{ label: "按住〔轉動球磨罐〕", cls: "gold", hold: {
        down: () => { if (!done) { holding = true; audio.humStart(80); xj.setFace("excited"); } },
        up: () => { holding = false; audio.humStop(); if (!done) xj.setFace("normal"); },
      } }]);
      hud.setAP("L2-hold", () => {
        hb.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
        const iv = setInterval(() => { if (done) { clearInterval(iv); hb.dispatchEvent(new PointerEvent("pointerup", { bubbles: true })); } }, 100);
      });
      async function finish() {
        holding = false;
        audio.humStop();
        audio.good();
        hud.clearButtons();
        hud.toast("磨好了！約 2–4 微米");
        await wait(0.6);
        await popOut(mill, 0.4);
        // 放大到晶格表面
        const lat = makeLattice();
        persist.lattice = lat;
        lat.group.position.set(0.02, -0.07, 0.1);
        keep.add(lat.group);
        hud.toast("放大看看粉末表面……");
        await popIn(lat.group, 0.86, 0.7);
        lat.vacancies.forEach((v, i) => setTimeout(() => { audio.pop(); burst(lat.group.localToWorld(v.pos.clone()).applyMatrix4(new THREE.Matrix4().copy(stage.matrixWorld).invert()), "#ffd36b", 8, { speed: 0.3, size: 0.03 }); }, i * 150));
        const tag = makeLabel("發亮缺口＝晶格空位", { height: 0.055, bg: "rgba(201,154,62,.95)", color: "#0b1f3a" });
        tag.position.set(0.1, 0.33, 0.2);
        lab.add(tag);
        popIn(tag, 1, 0.4);
        onUpdate((dt, t) => lat.update(t));
        xj.setFace("surprised");
        await hud.next(`${T(L.learn)}`, { ap: "L2-learn" });
        resolve(0);
      }
    });
  }

  // ---------- 第 3 關：配製反應液 ----------
  function L3(L) {
    return new Promise((resolve) => {
      if (persist.lattice) persist.lattice.group.visible = false;
      const flask = makeFlask();
      persist.flask = flask;
      flask.group.position.set(0.05, -0.12, 0.16);
      keep.add(flask.group);
      popIn(flask.group, 1.05, 0.5);
      const inside = new THREE.Group();
      flask.group.add(inside);
      persist.inside = inside;
      let got = 0, wrong = 0, busy = false;
      const colors = { water: 0x7fd3ff, micelle: 0xffffff, fe: 0xffd27a, organic: 0xd8b4fe, acid: 0xfca5a5 };
      const opts = L.options;
      onUpdate((dt, t) => {
        inside.children.forEach((c, i) => {
          if (!c.userData.orbit) return;
          const [a, r, y, sp] = c.userData.orbit;
          c.position.set(Math.cos(a + t * sp) * r, y + Math.sin(t * 2 + i) * 0.01, Math.sin(a + t * sp) * r);
          c.rotation.y += dt;
        });
      });
      const pick = async (o, btn) => {
        if (busy || btn.disabled) return;
        busy = true;
        btn.disabled = true;
        const bottle = makeBottle(o.label.split("（")[0], colors[o.id]);
        bottle.position.set(0.32, 0.2, 0.2);
        lab.add(bottle);
        await popIn(bottle, 1, 0.35);
        if (o.ok) {
          btn.classList.add("right");
          await tw.add(0.4, (k) => { bottle.rotation.z = k * 1.9; bottle.position.x = 0.32 - k * 0.14; }, ease.outCubic);
          for (let k = 0; k < 6; k++) setTimeout(() => particles.emit({ pos: V(0.15, 0.19, 0.2), count: 4, color: o.id === "fe" ? "#ffcf5a" : o.id === "micelle" ? "#ffe9c2" : "#8fd8ff", speed: 0.15, dir: V(-0.6, -1, 0), spread: 0.3, size: 0.03, life: 0.7, gravity: 0.9 }), k * 70);
          audio.drop();
          await wait(0.5);
          got++;
          flask.setLevel(0.25 + got * 0.17);
          if (o.id === "fe") flask.liquid.material.color.set(0xf6c15a);
          if (o.id === "micelle") {
            for (let k = 0; k < 6; k++) {
              const mc = makeMicelle(0.032);
              mc.userData.orbit = [k * 1.05, 0.07 + (k % 2) * 0.03, -0.08 + (k % 3) * 0.04, 0.6 + k * 0.05];
              inside.add(mc);
            }
            const tagM = makeLabel("T 微胞", { height: 0.045 });
            tagM.position.set(-0.24, -0.02, 0.24);
            lab.add(tagM);
          }
          if (o.id === "fe") {
            for (let k = 0; k < 5; k++) {
              const fe = makeFe();
              fe.scale.setScalar(0.8);
              fe.userData.orbit = [k * 1.3 + 0.5, 0.09, -0.04 + (k % 2) * 0.05, -0.8];
              fe.userData.fe = true;
              inside.add(fe);
            }
            const tagF = makeLabel("Fe³⁺", { height: 0.045, bg: "rgba(201,154,62,.95)", color: "#0b1f3a" });
            tagF.position.set(-0.24, -0.1, 0.24);
            lab.add(tagF);
          }
          audio.good();
          xj.setFace("happy");
          hud.say(`✔ ${T(o.msg)}<span class="sub">已選對 ${got} / 3</span>`);
          await popOut(bottle, 0.3);
        } else {
          wrong++;
          btn.classList.add("wrong");
          const x = makeLabel("✘", { height: 0.1, bg: "rgba(224,87,75,.95)", px: 72 });
          x.position.set(0.32, 0.2, 0.3);
          lab.add(x);
          audio.bad();
          xj.setFace("worried");
          shake(bottle, 0.03, 0.5);
          shake(flask.group, 0.015, 0.5);
          particles.emit({ pos: V(0.32, 0.2, 0.2), count: 16, color: "#ff6b5b", speed: 0.5, size: 0.03, life: 0.6 });
          hud.say(`✘ ${T(o.msg)}<span class="sub">再選選看（已選對 ${got} / 3）</span>`);
          await wait(0.9);
          await popOut(bottle, 0.3);
          lab.remove(x); disposeTree(x);
        }
        lab.remove(bottle); disposeTree(bottle);
        busy = false;
        if (got >= 3) {
          hud.clearButtons();
          hud.toast("反應液完成！");
          await wait(0.8);
          resolve(wrong);
        } else regAP();
      };
      hud.say(L.hint);
      const btns = hud.buttons(opts.map((o) => ({ label: o.label, cls: "alt", onClick: (e, b) => pick(o, b) })), { grid: true });
      // 自動通關：先試一個錯的（有機溶劑），再依序選對
      const apOrder = ["organic", "water", "micelle", "fe"];
      let apK = 0;
      const regAP = () => {
        const id = apOrder[apK];
        hud.setAP(`L3-pick-${id || "x"}`, () => { apK++; btns[opts.findIndex((o) => o.id === id)].click(); });
      };
      regAP();
    });
  }

  // ---------- 第 4 關：投粉＋攪拌 ----------
  function L4(L) {
    return new Promise((resolve) => {
      const flask = persist.flask, inside = persist.inside;
      const N = 22;
      const grains = new THREE.InstancedMesh(new THREE.DodecahedronGeometry(0.016), stoneMaterial(), N);
      grains.visible = false;
      inside.add(grains);
      const clump = Array.from({ length: N }, () => V(rand(-0.035, 0.035), -0.09 + rand(-0.025, 0.03), rand(-0.035, 0.035)));
      const spread = Array.from({ length: N }, (_, i) => { const a = i * 2.4, r = 0.03 + (i % 5) * 0.022; return V(Math.cos(a) * r, -0.1 + (i % 4) * 0.045, Math.sin(a) * r); });
      let disp = 0, stir = 0, swirl = 0, dropped = 0;
      const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), one = V(1, 1, 1), p = V(0, 0, 0);
      onUpdate((dt, t) => {
        swirl = Math.max(0, swirl - dt * 1.2);
        if (!grains.visible) return;
        for (let i = 0; i < N; i++) {
          p.lerpVectors(clump[i], spread[i], disp);
          const a = swirl * 3 + t * 0.2 * disp;
          const x = p.x * Math.cos(a) - p.z * Math.sin(a), z = p.x * Math.sin(a) + p.z * Math.cos(a);
          const yy = dropped < 1 ? 0.45 - (0.45 - p.y) * dropped : p.y;
          m4.compose(V(x, yy + Math.sin(t * 2 + i) * 0.004 * disp, z), q, one);
          grains.setMatrixAt(i, m4);
        }
        grains.instanceMatrix.needsUpdate = true;
        flask.liquid.rotation.y += swirl * dt * 6;
        inside.children.forEach((c) => { if (c.userData.orbit) c.userData.orbit[3] = 0.6 + swirl * 4; });
      });
      hud.say(L.hintDrop);
      const doDrop = async () => {
        if (grains.visible) return;
        hud.clearButtons();
        grains.visible = true;
        audio.whoosh();
        particles.emit({ pos: flask.group.position.clone().add(V(0, 0.42, 0.05)), count: 30, color: "#5fa98a", speed: 0.1, dir: V(0, -1, 0), spread: 0.2, size: 0.03, life: 0.9, gravity: 1.2 });
        await tw.add(0.9, (k) => { dropped = k; }, ease.inCubic);
        dropped = 1;
        xj.setFace("worried");
        hud.toast("粉末黏成一團了！", { warn: true });
        hud.say(`${L.hintStir}`);
        hud.meter(true, "分散度", 0, "0 / 5");
        const [sb] = hud.buttons([{ label: "攪拌！", cls: "gold", onClick: doStir }]);
        hud.setAP("L4-stir1", () => sb.click());
      };
      let stirring = false;
      async function doStir(e, btn) {
        if (stirring || stir >= 5) return;
        stirring = true;
        stir++;
        swirl = 1;
        audio.whoosh();
        particles.emit({ pos: flask.group.position.clone().add(V(0, 0.02, 0.15)), count: 10, color: "#bfe9ff", speed: 0.3, size: 0.025, life: 0.6 });
        const d0 = disp;
        await tw.add(0.55, (k) => { disp = d0 + (stir / 5 - d0) * k; }, ease.outCubic);
        hud.meter(true, "分散度", stir / 5, `${stir} / 5`);
        xj.setFace(stir >= 3 ? "happy" : "normal");
        stirring = false;
        if (stir < 5) { hud.setAP(`L4-stir${stir + 1}`, () => btn.click()); return; }
        hud.clearButtons();
        hud.toast("粉末散開了！（潤濕・分散）");
        await wait(0.7);
        await anchorScene();
      }
      async function anchorScene() {
        // 放大到粉末表面：Fe³⁺ 錨定、T 微胞包覆
        await tw.add(0.6, (k) => { flask.group.position.x = 0.05 + k * 0.33; flask.group.scale.setScalar(1.05 - k * 0.55); }, ease.inOutSine);
        const lat = persist.lattice;
        lat.group.visible = true;
        lat.show(true);
        lat.group.position.set(-0.06, -0.02, 0.1);
        await popIn(lat.group, 0.74, 0.6);
        onUpdate((dt, t) => lat.update(t));
        const sites = [[-0.25, 0.02], [-0.05, -0.2], [0.17, 0.05], [0.3, -0.12]];
        const labels = [["≡Mg–OH", -0.3, 0.3], ["≡Si–OH", 0.16, 0.3]];
        labels.forEach(([txt, x, y]) => {
          const l = makeLabel(txt, { height: 0.05, bg: "rgba(28,114,147,.95)" });
          l.position.set(x, y, 0.22);
          lab.add(l);
          popIn(l, 1, 0.4);
        });
        audio.pop();
        for (let k = 0; k < sites.length; k++) {
          const fe = makeFe();
          const from = flask.group.position.clone().add(V(0, 0.02, 0.1));
          const to = V(-0.06 + sites[k][0] * 0.74, -0.02 + sites[k][1] * 0.74, 0.14);
          fe.position.copy(from);
          lab.add(fe);
          tw.add(0.7, (e) => { fe.position.lerpVectors(from, to, e); fe.position.z += Math.sin(e * Math.PI) * 0.15; }, ease.inOutSine).then(() => {
            burst(to, "#ffd76a", 10, { speed: 0.3 }); audio.pop();
            stage.updateMatrixWorld(true);
            lat.group.attach(fe); // 錨定在晶格上，第 5 關仍看得到
          });
          await wait(0.25);
        }
        const mc = makeMicelle(0.07);
        mc.position.set(-0.4, -0.38, 0.2);
        lab.add(mc);
        popIn(mc, 1, 0.5);
        onUpdate((dt) => { mc.rotation.y += dt; });
        const tg = makeLabel("T 微胞：疏水核＋親水小尾", { height: 0.045 });
        tg.position.set(-0.14, -0.5, 0.24);
        lab.add(tg);
        await wait(0.8);
        xj.setFace("excited");
        hud.toast(T(L.anchor));
        await hud.next(`${T(L.anchor)}`, { ap: "L4-anchor" });
        await popOut(flask.group, 0.3);
        flask.group.visible = false;
        resolve(0);
      }
      const [db] = hud.buttons([{ label: "投入墨玉微米粉", cls: "gold", onClick: doDrop }]);
      hud.setAP("L4-drop", () => db.click());
    });
  }

  // ---------- 第 5 關：DSW 滴定（核心） ----------
  function L5(L) {
    return new Promise((resolve) => {
      const lat = persist.lattice;
      lat.group.visible = true;
      lat.group.position.set(0.0, -0.12, 0.08);
      lat.group.scale.setScalar(0.9);
      lat.show(true);
      onUpdate((dt, t) => lat.update(t));
      hud.setEnergy(true, 0.1);
      xj.setEnergy(0.15);
      xj.setFace("sleepy");
      // 滴管
      const drop = new THREE.Group();
      drop.position.set(0.12, 0.36, 0.3);
      const tube = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.2, 16), new THREE.MeshStandardMaterial({ color: 0xdff6ff, transparent: true, opacity: 0.55 }));
      const fluid = new THREE.Mesh(new THREE.CylinderGeometry(0.016, 0.016, 0.16, 16), new THREE.MeshStandardMaterial({ color: 0x1c7293, emissive: 0x065a82, emissiveIntensity: 0.6 }));
      const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.042, 16, 12), new THREE.MeshStandardMaterial({ color: 0x1e3a5f }));
      bulb.position.y = 0.12;
      const tip = new THREE.Mesh(new THREE.ConeGeometry(0.02, 0.05, 16), tube.material);
      tip.rotation.x = Math.PI; tip.position.y = -0.12;
      const dl = makeLabel("深層海水 DSW", { height: 0.045, bg: "rgba(6,90,130,.95)" });
      dl.position.set(0.17, 0.05, 0.02);
      drop.add(tube, fluid, bulb, tip, dl);
      lab.add(drop);
      popIn(drop, 1, 0.4);
      const ions = [];
      let filled = 0, caTaps = 0, flying = false, finished = false, firstCaTried = false;
      const lw = (v) => lat.group.localToWorld(v.clone());
      const toStage = (w) => stage.worldToLocal(w);
      onUpdate((dt, t) => {
        ions.forEach((ion, i) => {
          if (ion.userData.busy) return;
          const b = ion.userData.base;
          ion.position.set(b.x + Math.sin(t * 0.9 + i * 1.7) * 0.03, b.y + Math.sin(t * 1.4 + i) * 0.025, b.z);
        });
      });
      const spawn = (kind, x, y) => {
        const ion = makeIon(kind);
        ion.userData.base = V(x, y, 0.3);
        ion.position.copy(ion.userData.base);
        lab.add(ion);
        popIn(ion, 1, 0.4);
        ions.push(ion);
        onTap(ion, () => tapIon(ion));
      };
      const slots = [[-0.28, 0.12], [-0.1, 0.2], [0.24, 0.2], [0.36, 0.06], [-0.18, -0.02], [0.02, 0.06], [0.2, -0.04], [-0.34, -0.1]];
      const freeSlot = () => {
        const used = ions.map((i) => i.userData.base);
        return shuffle(slots).find(([x, y]) => !used.some((u) => Math.abs(u.x - x) < 0.05 && Math.abs(u.y - y) < 0.05));
      };
      const doDrop = async () => {
        if (finished) return;
        if (ions.length >= 7) { hud.toast("先把漂浮的 Mg²⁺ 送進空位吧！"); regAP(); return; }
        const d = new THREE.Mesh(new THREE.SphereGeometry(0.025, 12, 10), new THREE.MeshStandardMaterial({ color: 0x38bdf8, emissive: 0x0369a1, emissiveIntensity: 0.6, transparent: true, opacity: 0.9 }));
        d.position.set(0.12, 0.22, 0.3);
        lab.add(d);
        audio.drop();
        await tw.add(0.45, (k) => { d.position.y = 0.22 - k * 0.14; d.scale.set(1 - k * 0.2, 1 + k * 0.4, 1); }, ease.inCubic);
        burst(d.position.clone(), "#7dd3fc", 18, { speed: 0.5, size: 0.025 });
        lab.remove(d); disposeTree(d);
        const kinds = ["Mg", "Mg", "Ca"];
        kinds.forEach((k) => { const s = freeSlot(); if (s) spawn(k, s[0], s[1]); });
        await wait(0.45);
        regAP();
      };
      async function tapIon(ion) {
        if (flying || finished || ion.userData.busy) return;
        const vac = lat.vacancies.find((v) => !v.filled);
        if (!vac) return;
        flying = true;
        ion.userData.busy = true;
        const from = ion.position.clone();
        const to = toStage(lw(vac.pos)).add(V(0, 0, 0.02));
        if (ion.userData.kind === "Ca") {
          caTaps++;
          firstCaTried = true;
          audio.bad();
          await tw.add(0.4, (k) => { ion.position.lerpVectors(from, to, k * 0.7); }, ease.outCubic);
          burst(ion.position.clone(), "#ff9b7a", 10, { speed: 0.4 });
          ion.userData.ball.scale.set(1.25, 0.8, 1);
          await tw.add(0.45, (k) => { ion.position.lerpVectors(from, to, 0.7 * (1 - k)); ion.userData.ball.scale.set(1.25 - 0.25 * k, 0.8 + 0.2 * k, 1); }, ease.outBack);
          hud.toast(L.caMsg, { warn: true, ms: 2600 });
          xj.setFace("worried");
          hud.say(`${L.caMsg}<span class="sub">已補好 ${filled} / 6</span>`);
          ion.userData.busy = false;
          flying = false;
          await wait(0.3);
          regAP();
          return;
        }
        // Mg²⁺ → 空位
        audio.whoosh();
        await tw.add(0.6, (k) => { ion.position.lerpVectors(from, to, k); ion.position.z += Math.sin(k * Math.PI) * 0.12; ion.scale.setScalar(1 - k * 0.3); }, ease.inOutSine);
        offTap(ion);
        ions.splice(ions.indexOf(ion), 1);
        lab.remove(ion); disposeTree(ion);
        lat.fill(lat.vacancies.indexOf(vac));
        filled++;
        audio.good();
        burst(to, "#5ff5e6", 26, { speed: 0.6 });
        particles.emit({ pos: to.clone(), count: 8, color: "#ffffff", speed: 0.9, size: 0.02, life: 0.5 });
        const e = filled / 6;
        xj.setEnergy(0.15 + 0.85 * e);
        xj.glowBoost = 1;
        hud.setEnergy(true, 0.1 + 0.9 * e);
        hud.meter(true, "晶格修復", e, `${filled} / 6`);
        xj.setFace(e < 0.34 ? "normal" : e < 0.67 ? "happy" : "excited");
        if (e >= 0.5) irBurst(1, e);
        hud.toast(`${L.filled}（${filled} / 6）`);
        hud.say(`${L.hint}<span class="sub">已補好 ${filled} / 6</span>`);
        flying = false;
        if (filled >= 6) { finished = true; await finish(); return; }
        if (!ions.some((i) => i.userData.kind === "Mg")) hud.toast(L.needMore);
        await wait(0.2);
        regAP();
      }
      async function finish() {
        hud.clearButtons();
        S.irRate = 1;
        await wait(0.4);
        ions.forEach((i) => popOut(i, 0.3));
        await moveXj(V(-0.3, 0.26, 0.4), 0.2, 0.6);
        xj.setFace("excited");
        audio.fanfare();
        irBurst(6, 1);
        burst(xjStagePos(), "#ef6c3c", 40, { speed: 0.8 });
        const stamp = makeLabel("工作假設・待驗證", { height: 0.06, bg: "rgba(239,108,60,.95)" });
        stamp.position.set(0.22, 0.32, 0.36);
        lab.add(stamp);
        popIn(stamp, 1, 0.5);
        await hud.next(`<b>${L.done}</b><span class="honest">${T(L.honesty)}</span>`, { ap: "L5-honesty" });
        lat.group.visible = false;
        resolve(Math.max(0, caTaps - 1));
      }
      hud.say(`${L.hint}<span class="sub">已補好 0 / 6</span>`);
      hud.meter(true, "晶格修復", 0, "0 / 6");
      const [dropBtn] = hud.buttons([{ label: "💧 滴一滴深層海水", cls: "alt", onClick: doDrop }]);
      // 自動通關：沒有離子先滴；第一次先點一顆 Ca²⁺（測試提示），之後點 Mg²⁺
      const regAP = () => {
        if (finished) return;
        const mg = ions.find((i) => i.userData.kind === "Mg" && !i.userData.busy);
        const ca = ions.find((i) => i.userData.kind === "Ca" && !i.userData.busy);
        if (!firstCaTried && ca && filled >= 1) hud.setAP(`L5-tapCa`, () => apTap(ca));
        else if (mg) hud.setAP(`L5-tapMg${filled + 1}`, () => apTap(mg));
        else hud.setAP(`L5-drop${filled}`, () => dropBtn.click());
      };
      regAP();
    });
  }

  // ---------- 第 6 關：離心＋洗滌 ----------
  function L6(L) {
    return new Promise((resolve) => {
      const W = V(-0.07, -0.08, 0.12);
      const cf = new THREE.Group();
      cf.position.copy(W);
      lab.add(cf);
      const base = new THREE.Mesh(new THREE.CylinderGeometry(0.27, 0.29, 0.06, 48), new THREE.MeshStandardMaterial({ color: 0xe2e8f0, roughness: 0.5 }));
      base.rotation.x = Math.PI / 2;
      const well = new THREE.Mesh(new THREE.CircleGeometry(0.24, 48), new THREE.MeshStandardMaterial({ color: 0x1e293b }));
      well.position.z = 0.031;
      const rotor = new THREE.Group();
      rotor.position.z = 0.05;
      const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.03, 20), new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.7 }));
      hub.rotation.x = Math.PI / 2;
      rotor.add(hub);
      const tubes = [];
      const saltGeo = new THREE.SphereGeometry(0.007, 6, 5);
      const saltMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
      for (let k = 0; k < 4; k++) {
        const t = new THREE.Group();
        t.rotation.z = k * Math.PI / 2;
        const glass = new THREE.Mesh(new THREE.CylinderGeometry(0.026, 0.026, 0.17, 16), new THREE.MeshStandardMaterial({ color: 0xdff6ff, transparent: true, opacity: 0.35, depthWrite: false }));
        glass.rotation.z = Math.PI / 2; glass.position.x = 0.13;
        const mix = new THREE.Mesh(new THREE.CylinderGeometry(0.022, 0.022, 0.15, 12), new THREE.MeshStandardMaterial({ color: 0x6fae8d, transparent: true, opacity: 0.85 }));
        mix.rotation.z = Math.PI / 2; mix.position.x = 0.13;
        const sed = new THREE.Mesh(new THREE.CylinderGeometry(0.023, 0.023, 0.05, 12), new THREE.MeshStandardMaterial({ color: 0x1f6b47 }));
        sed.rotation.z = Math.PI / 2; sed.position.x = 0.19; sed.visible = false;
        const salts = [];
        for (let s = 0; s < 4; s++) { const sm = new THREE.Mesh(saltGeo, saltMat); sm.position.set(0.07 + s * 0.022, (s % 2 ? 1 : -1) * 0.008, 0.026); sm.visible = false; t.add(sm); salts.push(sm); }
        t.add(glass, mix, sed);
        rotor.add(t);
        tubes.push({ t, mix, sed, salts });
      }
      cf.add(base, well, rotor);
      popIn(cf, 1, 0.5);
      // 廢液收集桶
      const bucket = new THREE.Group();
      bucket.position.set(0.34, -0.24, 0.14);
      const bglass = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.07, 0.18, 24, 1, true), new THREE.MeshStandardMaterial({ color: 0xfef3c7, transparent: true, opacity: 0.35, side: THREE.DoubleSide, depthWrite: false }));
      const bliq = new THREE.Mesh(new THREE.CylinderGeometry(0.072, 0.066, 1, 24), new THREE.MeshStandardMaterial({ color: 0xcbd5e1, transparent: true, opacity: 0.8 }));
      bliq.scale.y = 0.001; bliq.position.y = -0.09;
      const bl = makeLabel("廢液收集桶", { height: 0.042, bg: "rgba(201,154,62,.95)", color: "#0b1f3a" });
      bl.position.set(0, -0.14, 0.09);
      bucket.add(bglass, bliq, bl);
      lab.add(bucket);
      popIn(bucket, 1, 0.5);
      let spin = 0, spun = false, washes = 0, busy = false, wrong = 0;
      onUpdate((dt) => { rotor.rotation.z -= spin * dt; });
      hud.say(L.hintSpin);
      hud.meter(true, "鹽分", 1, "很多");
      const doSpin = async () => {
        if (spun || busy) return;
        busy = true;
        hud.clearButtons();
        audio.humStart(120);
        xj.setFace("surprised");
        await tw.add(0.8, (k) => { spin = k * 26; audio.humPitch(120 + k * 300); }, ease.inCubic);
        for (let k = 0; k < 8; k++) { particles.emit({ pos: W.clone().add(V(rand(-0.2, 0.2), rand(-0.2, 0.2), 0.08)), count: 2, color: "#e0f2fe", speed: 0.6, size: 0.02, life: 0.4 }); await wait(0.12); }
        tubes.forEach((tb) => { tb.mix.material.color.set(0xd6f1ff); tb.mix.material.opacity = 0.4; tb.sed.visible = true; tb.salts.forEach((s) => { s.visible = true; }); });
        await tw.add(0.9, (k) => { spin = 26 * (1 - k); audio.humPitch(420 - k * 300); }, ease.outCubic);
        audio.humStop();
        spin = 0;
        spun = true;
        xj.setFace("happy");
        hud.toast(L.spun);
        const tag = makeLabel("粉末沉在外側、上面是水", { height: 0.042 });
        tag.position.set(-0.02, 0.22, 0.24);
        lab.add(tag);
        hud.say(`${L.spun}<span class="sub">${L.hintWash}</span>`);
        const [wb] = hud.buttons([{ label: "洗滌（加水再離心）", cls: "gold", onClick: doWash }]);
        hud.setAP("L6-wash1", () => wb.click());
        busy = false;
      };
      async function askWaste() {
        const k = await hud.choose("洗下來的廢液要倒去哪裡？", ["倒進水槽沖掉", "倒進廢液收集桶"], { ap: "L6-waste", apPick: () => (wrong === 0 ? 0 : 1) });
        if (k === 0) {
          wrong++;
          audio.bad();
          xj.setFace("worried");
          hud.toast("不行！廢液會污染水源，要收集處理。", { warn: true, ms: 2600 });
          return askWaste();
        }
        audio.good();
        return true;
      }
      async function doWash(e, btn) {
        if (busy || washes >= 3) return;
        busy = true;
        hud.clearButtons();
        if (washes === 0) await askWaste();
        washes++;
        audio.whoosh();
        rotor.rotation.z += 0.3;
        await tw.add(0.5, (k) => { spin = Math.sin(k * Math.PI) * 18; }, ease.linear);
        spin = 0;
        tubes.forEach((tb) => tb.salts.forEach((s, i) => { s.visible = i < [4, 2, 1, 0][washes]; }));
        for (let k = 0; k < 5; k++) particles.emit({ pos: W.clone().add(V(0.15, 0.05, 0.12)), count: 3, color: "#cbd5e1", speed: 0.5, dir: V(1, 0.4, 0), spread: 0.3, size: 0.025, life: 0.6, gravity: 0.6 });
        await tw.add(0.5, (k) => { bliq.scale.y = Math.max(0.001, (washes - 1 + k) / 3 * 0.15); bliq.position.y = -0.09 + bliq.scale.y / 2; }, ease.outCubic);
        hud.meter(true, "鹽分", 1 - washes / 3, ["很多", "變少", "很少", "洗乾淨了"][washes]);
        hud.toast(washes < 3 ? `洗滌 ${washes} / 3：鹽變少了` : L.waste, { ms: 2600 });
        busy = false;
        if (washes < 3) {
          hud.say(`${L.hintWash}<span class="sub">已洗 ${washes} / 3</span>`);
          const [wb] = hud.buttons([{ label: "洗滌（加水再離心）", cls: "gold", onClick: doWash }]);
          hud.setAP(`L6-wash${washes + 1}`, () => wb.click());
        } else {
          xj.setFace("happy");
          await hud.next(`${L.waste}`, { ap: "L6-waste-done" });
          resolve(wrong);
        }
      }
      const [sb] = hud.buttons([{ label: "離心！", cls: "gold", onClick: doSpin }]);
      hud.setAP("L6-spin", () => sb.click());
    });
  }

  // ---------- 第 7 關：乾燥 ----------
  function L7(L) {
    return new Promise((resolve) => {
      const oven = new THREE.Group();
      oven.position.set(0.06, -0.1, 0.12);
      lab.add(oven);
      const box = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.36, 0.2), new THREE.MeshStandardMaterial({ color: 0x475569, roughness: 0.5, metalness: 0.3 }));
      const win = new THREE.Mesh(new THREE.PlaneGeometry(0.32, 0.22), new THREE.MeshStandardMaterial({ color: 0x0f172a, emissive: 0xff7a2f, emissiveIntensity: 0, transparent: true, opacity: 0.85 }));
      win.position.set(-0.04, -0.01, 0.101);
      const tray = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.03, 0.02), stoneMaterial());
      tray.position.set(-0.04, -0.08, 0.105);
      let disp = makeLabel("-- °C", { height: 0.06, bg: "rgba(15,23,42,.95)", color: "#7ef0b4", px: 60 });
      disp.position.set(0.19, 0.09, 0.12);
      oven.add(box, win, tray, disp);
      const ol = makeLabel("烘箱", { height: 0.045 });
      ol.position.set(0.19, -0.05, 0.12);
      oven.add(ol);
      popIn(oven, 1, 0.5);
      const setDisp = (txt, color) => { oven.remove(disp); disposeTree(disp); disp = makeLabel(txt, { height: 0.06, bg: "rgba(15,23,42,.95)", color, px: 60 }); disp.position.set(0.19, 0.09, 0.12); oven.add(disp); };
      let wrong = 0, busy = false, heat = 0;
      onUpdate((dt, t) => { win.material.emissiveIntensity = heat * (0.85 + 0.15 * Math.sin(t * 12)); });
      const opts = L.options;
      const run = async (o, btn) => {
        if (busy || btn.disabled) return;
        busy = true;
        [...hud.el.btns.children].forEach((b) => { b.disabled = true; });
        if (o.id === "low") {
          btn.classList.add("right");
          setDisp("50 °C", "#ffd76a");
          await tw.add(0.6, (k) => { heat = k * 0.45; }, ease.outCubic);
          const clock = makeLabel("0 小時", { height: 0.06, bg: "rgba(255,255,255,.95)", color: "#0b1f3a" });
          clock.position.set(0.06, 0.24, 0.3);
          lab.add(clock);
          for (let h = 6; h <= 48; h += 6) {
            await wait(0.18);
            lab.remove(clock.userData.cur || clock);
            const c2 = makeLabel(`${h} 小時`, { height: 0.06, bg: "rgba(255,255,255,.95)", color: "#0b1f3a" });
            c2.position.copy(clock.position);
            lab.add(c2);
            clock.userData.cur = c2;
            particles.emit({ pos: V(rand(-0.1, 0.1), 0.12, 0.25), count: 2, color: "#e2f3ff", speed: 0.15, dir: V(0, 1, 0), spread: 0.2, size: 0.03, life: 1 });
            hud.meter(true, "乾燥時間", h / 48, `${h} 小時`);
          }
          audio.good();
          burst(V(0.02, -0.18, 0.25), "#7ef0b4", 20, { speed: 0.4 });
          xj.setFace("excited");
          hud.say(`✔ ${T(o.msg)}`);
          await wait(0.8);
          await hud.next(`✔ ${T(o.msg)}`, { ap: "L7-ok" });
          resolve(wrong);
          return;
        }
        wrong++;
        btn.classList.add("wrong");
        audio.bad();
        xj.setFace("worried");
        if (o.id === "hot") {
          setDisp("200 °C", "#ff5b5b");
          await tw.add(0.4, (k) => { heat = k * 1.6; }, ease.outCubic);
          shake(oven, 0.02, 0.8);
          for (let k = 0; k < 5; k++) { particles.emit({ pos: V(0.02, -0.1, 0.25), count: 5, color: "#ff5b3b", speed: 0.7, size: 0.03, life: 0.5 }); await wait(0.12); }
        } else {
          const sunS = glowSprite(0xffd34d, 0.3, 0.95);
          sunS.position.set(0.32, 0.3, 0.3);
          lab.add(sunS);
          const cal = makeLabel("1 月", { height: 0.06, bg: "rgba(255,255,255,.95)", color: "#9a3412" });
          cal.position.set(-0.12, 0.25, 0.3);
          lab.add(cal);
          for (let mth = 2; mth <= 12; mth += 2) {
            await wait(0.12);
            lab.remove(cal.userData.cur || cal);
            const c2 = makeLabel(`${mth} 月`, { height: 0.06, bg: "rgba(255,255,255,.95)", color: "#9a3412" });
            c2.position.copy(cal.position); lab.add(c2); cal.userData.cur = c2;
          }
          particles.emit({ pos: V(0.02, -0.05, 0.25), count: 24, color: "#9ca3af", speed: 0.3, size: 0.03, life: 1.2, jitter: 0.3 });
          xj.setFace("sleepy");
          await wait(0.6);
          lab.remove(sunS); lab.remove(cal.userData.cur || cal);
        }
        hud.toast(T(o.msg), { warn: true, ms: 2800 });
        hud.say(`✘ ${T(o.msg)}<span class="sub">再選一次！</span>`);
        await tw.add(0.4, (k) => { heat = heat * (1 - k); }, ease.linear);
        heat = 0;
        setDisp("-- °C", "#7ef0b4");
        [...hud.el.btns.children].forEach((b) => { if (!b.classList.contains("wrong")) b.disabled = false; });
        busy = false;
        regAP();
      };
      hud.say(L.hint);
      const btns = hud.buttons(opts.map((o) => ({ label: o.label, cls: "alt", onClick: (e, b) => run(o, b) })));
      // 自動通關：先選 200 °C（測錯誤回饋），再選正確
      const order = ["hot", "low"];
      let k = 0;
      const regAP = () => { const id = order[k]; hud.setAP(`L7-${id}`, () => { k++; btns[opts.findIndex((o) => o.id === id)].click(); }); };
      regAP();
    });
  }

  // ---------- 第 8 關：表徵分析 ----------
  function L8(L) {
    return new Promise((resolve) => {
      const chart = makeChart();
      chart.mesh.position.set(0.07, 0.05, 0.16);
      lab.add(chart.mesh);
      chart.ftir(0);
      popIn(chart.mesh, 1, 0.5);
      const inst = new THREE.Group();
      inst.position.set(0.06, -0.3, 0.14);
      const body = new THREE.Mesh(new THREE.BoxGeometry(0.44, 0.13, 0.16), new THREE.MeshStandardMaterial({ color: 0x1c7293, roughness: 0.4, metalness: 0.3 }));
      const sample = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.015, 24), stoneMaterial());
      sample.rotation.x = Math.PI / 2; sample.position.set(0, 0.0, 0.09);
      const beam = new THREE.Mesh(new THREE.CylinderGeometry(0.006, 0.006, 0.4, 8), new THREE.MeshBasicMaterial({ color: 0xff3b3b, transparent: true, opacity: 0 }));
      beam.rotation.z = Math.PI / 2; beam.position.set(0, 0, 0.1);
      const il = makeLabel("FTIR 光譜儀", { height: 0.045 });
      il.position.set(0, -0.1, 0.1);
      inst.add(body, sample, beam, il);
      lab.add(inst);
      popIn(inst, 1, 0.5);
      let mode = null, ftirDone = false, seen = new Set();
      onUpdate((dt, t) => {
        if (mode === "before" && Math.random() < dt * 0.8) ripples.emit(xjStagePos(), { r0: 0.05, r1: 0.15, life: 1.6, alpha: 0.3 });
        if (mode === "after" && Math.random() < dt * 3.2) ripples.emit(xjStagePos(), { r0: 0.06, r1: 0.24, life: 1.2, alpha: 0.85 });
      });
      const doFtir = async () => {
        if (ftirDone) return;
        hud.clearButtons();
        audio.humStart(300);
        await tw.add(0.3, (k) => { beam.material.opacity = k * 0.9; }, ease.linear);
        await tw.add(1.6, (k) => { chart.ftir(k); beam.material.opacity = 0.6 + 0.3 * Math.sin(k * 30); }, ease.linear);
        audio.humStop();
        beam.material.opacity = 0;
        ftirDone = true;
        audio.good();
        xj.setFace("happy");
        hud.say(`${T(L.ftirDone)}<span class="sub">${L.hintCompare}</span>`);
        showCompare();
      };
      const showCompare = () => {
        const bs = hud.buttons([
          { label: "修復前", cls: "alt", onClick: () => view("before") },
          { label: "修復後（預期）", cls: "fir", onClick: () => view("after") },
        ]);
        if (seen.size >= 2) {
          const nb = document.createElement("button");
          nb.className = "btn gold"; nb.textContent = "看懂了 ▶";
          nb.addEventListener("click", finish);
          hud.el.btns.appendChild(nb);
          hud.setAP("L8-understood", () => nb.click());
        } else hud.setAP(`L8-view-${seen.has("before") ? "after" : "before"}`, () => bs[seen.has("before") ? 1 : 0].click());
      };
      async function view(m) {
        mode = m;
        seen.add(m);
        await tw.add(0.8, (k) => chart.emission(m, k), ease.outCubic);
        if (m === "after") { xj.setFace("excited"); for (let i = 0; i < 3; i++) setTimeout(() => ripples.emit(xjStagePos(), { r0: 0.06, r1: 0.26, life: 1.1, alpha: 0.9 }), i * 160); } else xj.setFace("normal");
        hud.say(`${m === "before" ? L.before : L.after}<span class="honest">${T(L.honesty)}</span>`);
        showCompare();
      }
      async function finish() {
        hud.clearButtons();
        mode = null;
        await hud.next(`<b>${T(L.learn)}</b><span class="honest">${T(L.honesty)}</span>`, { ap: "L8-honesty" });
        resolve(0);
      }
      hud.say(L.hintFtir);
      const [fb] = hud.buttons([{ label: "FTIR 檢查", cls: "gold", onClick: doFtir }]);
      hud.setAP("L8-ftir", () => fb.click());
    });
  }

  const LEVEL_FNS = [L1, L2, L3, L4, L5, L6, L7, L8];

  // ---------- 結尾 ----------
  async function commitment() {
    hud.showPanel(false);
    return new Promise((resolve) => {
      const m = hud.modal(`<div class="kicker">行動承諾</div><div class="q">${ENDING.commitAsk}</div>
        <div class="opts">${ENDING.commits.map((c, i) => `<button class="opt" data-i="${i}"><b>${i + 1}</b>${c}</button>`).join("")}</div>`,
      { speech: `${ENDING.commitAsk}\n${ENDING.commits.map((c, i) => `${i + 1}、${c}`).join("；")}。` });
      const bs = [...m.querySelectorAll(".opt")];
      bs.forEach((b) => b.addEventListener("click", () => {
        S.commit = ENDING.commits[Number(b.dataset.i)];
        b.classList.add("right");
        audio.good();
        setTimeout(resolve, 400);
        hud.setAP("commit-picked", null);
      }));
      hud.setAP("commit", () => bs[2].click());
    });
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
      if (f === "探究") v = (v + Math.min(1, S.stars[7] / 3)) / 2;
      facets[f] = Math.round(v * 100);
    });
    return { preScore, postSame, postScore, facets, stars: S.stars.reduce((a, b) => a + b, 0) };
  }

  function saveRecord(R) {
    const rec = {
      time: new Date().toISOString(), grade: S.grade, stars: S.stars, totalStars: R.stars,
      pre: S.pre, post: S.post, preScore: R.preScore, postSame3: R.postSame, postScore: R.postScore,
      facets: R.facets, commit: S.commit, mode: host.mode, autoplay: !!host.autoplay,
    };
    try {
      const arr = JSON.parse(localStorage.getItem(STORE_KEY) || "[]");
      arr.push(rec);
      localStorage.setItem(STORE_KEY, JSON.stringify(arr));
    } catch (e) { console.warn("無法寫入本機紀錄", e); }
  }

  function showResult() {
    const R = computeResult();
    saveRecord(R);
    hud.setTitle("任務完成！");
    hud.setProgress(-1, 8);
    hud.showPanel(false);
    xj.setFace("excited");
    moveXj(CENTER, CENTER_S, 0.8);
    irBurst(4, 1);
    audio.fanfare();
    const d = new Date();
    const date = `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")}`;
    const bar = (v, max, color) => `<div class="track"><i style="width:${Math.round((v / max) * 100)}%;background:${color}"></i></div>`;
    const m = hud.modal(`
      <div class="kicker">RESULT · 結果</div>
      <div class="cert">
        <div class="seal">修復師</div>
        <svg width="54" height="64" viewBox="0 0 54 64" aria-hidden="true"><polygon points="27,2 50,18 50,46 27,62 4,46 4,18" fill="#2e8b57" stroke="#0b2e1f" stroke-width="2"/><polygon points="27,2 50,18 27,24 4,18" fill="#3fa56b"/><circle cx="19" cy="34" r="4" fill="#0b1f3a"/><circle cx="35" cy="34" r="4" fill="#0b1f3a"/><path d="M20 44 Q27 50 34 44" stroke="#0b1f3a" stroke-width="3" fill="none"/></svg>
        <h3>墨玉修復師證書</h3>
        <div class="en">Serpentine Lattice Repair Certificate</div>
        <div class="stars">★ ${R.stars} / 24</div>
        <p>恭喜你完成墨玉晶格修復任務的八個實驗步驟！</p>
        <p class="small">${date}・${GRADE_LABEL[S.grade]}</p>
        <p class="small">我的小行動：${S.commit || "—"}</p>
        <p class="small">${CREDIT}</p>
      </div>
      <div class="sec-title">前測 → 後測（同樣 3 題）</div>
      <div class="cmp">
        <span>前測</span>${bar(R.preScore, 3, "#94a3b8")}<b>${R.preScore} / 3</b>
        <span>後測</span>${bar(R.postSame, 3, "#2e7d5b")}<b>${R.postSame} / 3</b>
        <span>後測全部</span>${bar(R.postScore, 5, "#1c7293")}<b>${R.postScore} / 5</b>
      </div>
      <div class="sec-title">四個面向</div>
      <div class="cmp">${FACETS.map((f) => `<span>${FACET_NAMES[f]}</span>${bar(R.facets[f], 100, { 知識: "#1c7293", 態度: "#2e7d5b", 行動: "#c99a3e", 探究: "#ef6c3c" }[f])}<b>${R.facets[f]}%</b>`).join("")}</div>
      <div class="explain">${ENDING.honesty}</div>
      <p class="small">可以截圖保存證書。成績只存在這台裝置，不會上傳。</p>
      <div class="row"><button class="btn alt again">再玩一次</button><a class="btn gold" href="teacher.html">給老師看</a></div>`, {
      // 語音：結果頁摘要（星數與一句恭喜）＋工作假設提醒
      speech: `恭喜你完成墨玉晶格修復任務的八個實驗步驟！\n你一共得到 ${R.stars} 顆星，滿分是 24 顆。\n前測答對 ${R.preScore} 題，後測同樣的 3 題答對 ${R.postSame} 題。\n${ENDING.honesty}`,
    });
    m.querySelector(".again").addEventListener("click", () => location.reload());
    hud.setAP("result", null);
  }

  async function run() {
    try {
      await intro();
      await quiz("pre");
      for (let i = 0; i < 8; i++) await level(i);
      clearLab();
      keep.visible = false;
      S.level = 8;
      xj.setEnergy(1);
      await moveXj(CENTER, 0.24, 0.6);
      await hud.next(ENDING.postIntro, { label: "開始後測 ▶", cls: "gold", ap: "post-intro" });
      await quiz("post");
      await commitment();
      hud.closeModal();
      showResult();
    } catch (e) {
      console.error(e);
      hud.say("糟糕，出了一點問題，請重新整理頁面再試一次。");
    }
  }

  // ---------- 每幀更新 ----------
  let started = false;
  function update(dt, t) {
    dt = Math.min(0.05, dt);
    tw.update(dt);
    xj.update(dt, t, camera);
    updaters.forEach((fn) => fn(dt, t));
    if (S.irRate > 0 && S.level !== 7) {
      S.irTimer -= dt;
      if (S.irTimer <= 0) { S.irTimer = 1.4; ripples.emit(xjStagePos(), { r0: 0.08, r1: 0.3, life: 1.6, alpha: 0.35 }); }
    }
    stage.updateMatrixWorld();
    renderer.getDrawingBufferSize(_size);
    const sc = new THREE.Vector3().setFromMatrixScale(stage.matrixWorld).x;
    particles.update(dt, _size.y * 0.5 * camera.projectionMatrix.elements[5] * sc);
    ripples.update(dt, camera);
  }

  return {
    update,
    start() { if (!started) { started = true; run(); } },
    get started() { return started; },
    state: S,
    xj,
  };
}
