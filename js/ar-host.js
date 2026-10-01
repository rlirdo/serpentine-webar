// MindAR 影像追蹤主機：追蹤到任務卡時 stage 貼在卡片上；遺失 >0.5 秒改為「懸浮模式」掛在相機前方。
import * as THREE from "three";
import { MindARThree } from "../vendor/mindar/mindar-image-three.prod.js";
import { createGame } from "./game.js";
import { createHud } from "./hud.js";
import { createAudio } from "./audio.js";
import { fitInfo } from "./layout.js";

const params = new URLSearchParams(location.search);
const selftest = params.get("selftest") === "1";
const container = document.getElementById("ar");
const t0 = performance.now();
const report = (o) => {
  if (!selftest) return;
  try { fetch("/__report", { method: "POST", body: JSON.stringify({ ...o, ms: Math.round(performance.now() - t0) }) }); } catch (e) { /* ignore */ }
};
if (selftest) {
  window.addEventListener("error", (e) => report({ event: "error", message: String(e.message) }));
  window.addEventListener("unhandledrejection", (e) => report({ event: "error", message: "unhandledrejection: " + String(e.reason) }));
}

const mindar = new MindARThree({
  container,
  imageTargetSrc: "assets/targets.mind",
  uiLoading: "#ar-loading",
  uiScanning: "#ar-scanning",
  uiError: "#ar-error",
});
const { renderer, scene, camera } = mindar;
renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
const anchor = mindar.addAnchor(0);

const holder = new THREE.Group();
holder.matrixAutoUpdate = false;
holder.visible = false;
scene.add(holder);
const stage = new THREE.Group();
holder.add(stage);

const audio = createAudio();
const hud = createHud({ audio });
hud.showPanel(false);
const game = createGame({ stage, camera, renderer, hud, host: { mode: "ar", inputEl: container, audio } });

// ---- 追蹤狀態 ----
const st = { tracked: false, everFound: false, lostAt: 0, mode: "scan", lastScale: 1000, reported: {} };
window.__arState = st;
const cur = { p: new THREE.Vector3(), q: new THREE.Quaternion(), s: new THREE.Vector3(1, 1, 1) };
const tgt = { p: new THREE.Vector3(), q: new THREE.Quaternion(), s: new THREE.Vector3(1, 1, 1) };
const tiltQ = new THREE.Quaternion().setFromEuler(new THREE.Euler(-0.22, 0, 0));
let snapNext = true;

function begin() {
  if (!game.started) game.start();
  const skip = document.getElementById("ar-skip");
  if (skip) skip.remove();
}
anchor.onTargetFound = () => {
  st.tracked = true;
  if (!st.everFound) {
    st.everFound = true;
    snapNext = true;
    document.getElementById("ar-scanning").classList.add("off"); // 之後由懸浮模式提示取代掃描框
    begin();
    st.pendingFoundReport = 2; // 等兩幀渲染後回報
  } else if (st.mode === "float") {
    st.pendingReattach = 24; // 約 0.4 秒（平滑過渡完成）後回報
  }
};
anchor.onTargetLost = () => {
  st.tracked = false;
  st.lostAt = performance.now();
  report({ event: "targetLost" });
};

// 掃描逾時：提供直接懸浮玩
setTimeout(() => {
  if (st.everFound) return;
  const b = document.getElementById("ar-skip");
  if (b) b.style.display = "flex";
}, 8000);
document.getElementById("ar-skip-btn").addEventListener("click", () => {
  st.everFound = true;
  st.lostAt = 0;
  snapNext = true;
  begin();
  document.getElementById("ar-scanning").classList.add("off");
});

// 懸浮模式：把 stage 放在相機前方、畫面上「沒被對話框蓋住」的區域中央（與 play.html 相同的版面邏輯）
function floatPose() {
  const s = st.lastScale;
  const w = container.clientWidth || window.innerWidth, h = container.clientHeight || window.innerHeight;
  const { need, cx, cy } = fitInfo(w, h);
  const tanV = Math.tan((camera.fov * Math.PI) / 360);
  const D = (s * h * need) / (2 * tanV);
  const pxPerWorld = h / (2 * D * tanV);
  tgt.p.set((cx - w / 2) / pxPerWorld, (h / 2 - cy) / pxPerWorld, -D);
  tgt.q.copy(tiltQ);
  tgt.s.setScalar(s);
}

const ndc = new THREE.Vector3();
const clock = new THREE.Clock();
let t = 0;
mindar.start().then(() => {
  report({ event: "started", video: [mindar.video.videoWidth, mindar.video.videoHeight] });
}).catch((e) => {
  report({ event: "error", message: "camera start failed: " + String(e) });
  document.getElementById("ar-loading").classList.add("hidden");
  document.getElementById("ar-error").classList.remove("hidden");
});

renderer.setAnimationLoop(() => {
  const dt = Math.min(0.05, clock.getDelta());
  t += dt;
  const now = performance.now();
  let mode = st.mode;
  if (st.tracked) {
    anchor.group.matrix.decompose(tgt.p, tgt.q, tgt.s);
    st.lastScale = tgt.s.x;
    mode = "track";
  } else if (st.everFound && now - st.lostAt > 500) {
    floatPose();
    mode = "float";
  }
  if (mode !== st.mode) {
    const prev = st.mode;
    st.mode = mode;
    hud.floatTip(mode === "float", "懸浮模式：把相機對準任務卡，小晶會回到卡片上");
    if (mode === "float") st.pendingFloatReport = 20; // 約 0.3 秒後（過渡穩定）回報
    if (prev === "float" && mode === "track") hud.toast("找到任務卡了！");
  }
  if (st.everFound) {
    const k = snapNext ? 1 : 1 - Math.exp(-dt * (mode === "track" ? 14 : 5));
    snapNext = false;
    cur.p.lerp(tgt.p, k);
    cur.q.slerp(tgt.q, k);
    cur.s.lerp(tgt.s, k);
    holder.matrix.compose(cur.p, cur.q, cur.s);
    holder.matrixWorldNeedsUpdate = true;
    holder.visible = true;
  }
  game.update(dt, t);
  renderer.render(scene, camera);

  // ---- 自我測試回報 ----
  if (selftest) {
    const info = () => {
      stage.getWorldPosition(ndc).project(camera);
      return { mode: st.mode, holderVisible: holder.visible, stageNdc: [+ndc.x.toFixed(3), +ndc.y.toFixed(3), +ndc.z.toFixed(3)], scale: +cur.s.x.toFixed(2), canvas: [renderer.domElement.width, renderer.domElement.height] };
    };
    if (st.pendingFoundReport && --st.pendingFoundReport === 0) report({ event: "targetFound", firstFrameRendered: true, ...info() });
    if (st.pendingFloatReport && --st.pendingFloatReport === 0) report({ event: "floatMode", ...info() });
    if (st.pendingReattach && st.mode === "track" && --st.pendingReattach === 0) report({ event: "reattached", ...info() });
  }
});
