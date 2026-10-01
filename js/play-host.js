// 無相機主機：一般 three.js 場景（輕微自動擺動＋可拖曳旋轉），掛同一個 stage。
import * as THREE from "three";
import { createGame } from "./game.js";
import { createHud } from "./hud.js";
import { createAudio } from "./audio.js";
import { installAutoplay } from "./autoplay.js";
import { fitInfo } from "./layout.js";

const params = new URLSearchParams(location.search);
const autoplay = params.get("autoplay") === "1";
const view = document.getElementById("view");

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: autoplay });
renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
renderer.outputColorSpace = THREE.SRGBColorSpace;
view.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, 1, 0.05, 50);
const root = new THREE.Group();
scene.add(root);
const stage = new THREE.Group();
root.add(stage);

// 任務卡底板（讓無相機模式也看得到「卡片」）
const tex = new THREE.TextureLoader().load("assets/target.png");
tex.colorSpace = THREE.SRGBColorSpace;
const card = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: tex, transparent: true, opacity: 0.55 }));
card.position.z = -0.03;
root.add(card);
const frame = new THREE.Mesh(new THREE.RingGeometry(0.69, 0.72, 4, 1), new THREE.MeshBasicMaterial({ color: 0x5fa98a, transparent: true, opacity: 0.6 }));
frame.rotation.z = Math.PI / 4;
frame.position.z = -0.025;
root.add(frame);

function fit() {
  const w = window.innerWidth, h = window.innerHeight;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  const { need, cx: px, cy: py } = fitInfo(w, h);
  const tanH = Math.tan((camera.fov * Math.PI) / 360);
  const d = (need * h) / (2 * tanH);
  const pxPerUnit = h / (2 * d * tanH);
  const cx = -(px - w / 2) / pxPerUnit;
  const cy = -(h / 2 - py) / pxPerUnit;
  camera.position.set(cx, cy, d);
  camera.lookAt(cx, cy, 0);
  camera.updateProjectionMatrix();
}
fit();
window.addEventListener("resize", fit);

// 拖曳旋轉（小角度），放開後慢慢回正
let drag = null, yaw = 0, pitch = 0;
view.addEventListener("pointerdown", (e) => { drag = { x: e.clientX, y: e.clientY, yaw, pitch }; });
window.addEventListener("pointermove", (e) => {
  if (!drag) return;
  yaw = Math.max(-0.8, Math.min(0.8, drag.yaw + (e.clientX - drag.x) * 0.006));
  pitch = Math.max(-0.5, Math.min(0.5, drag.pitch + (e.clientY - drag.y) * 0.004));
});
window.addEventListener("pointerup", () => { drag = null; });

const audio = createAudio();
const hud = createHud({ audio });
const apGrade = params.get("grade") === "junior" ? "junior" : "elem"; // 自動通關選哪一版
const game = createGame({ stage, camera, renderer, hud, host: { mode: "play", inputEl: view, audio, autoplay, apGrade } });
if (autoplay) installAutoplay(hud, game);

const clock = new THREE.Clock();
let t = 0;
renderer.setAnimationLoop(() => {
  const dt = Math.min(0.05, clock.getDelta());
  t += dt;
  if (!drag) { yaw *= 1 - Math.min(1, dt * 1.5); pitch *= 1 - Math.min(1, dt * 1.5); }
  const sway = autoplay ? 0 : 1;
  root.rotation.y = yaw + Math.sin(t * 0.45) * 0.14 * sway;
  root.rotation.x = -0.12 + pitch + Math.sin(t * 0.33) * 0.04 * sway;
  game.update(dt, t);
  renderer.render(scene, camera);
});
game.start();
