// 對照班「只有測驗」頁（2026/11/25 新增，schema webar-test-v1，group=control）
// 研究設計：對照班不玩遊戲、上一般講述課；課前、課後各做同一份整份 10 題（依版本），後測後選一項行動承諾。
// 作答時不顯示對錯、解說與面向標籤（避免變成教學或提示），全部做完才在完成頁顯示。
// 題目順序、洗牌、計分、態度題處理、上傳欄位、補傳佇列都在 ../js/study.js，與遊戲研究模式（?study=1）共用。
import { ENDING, FACET_NAMES, GRADE_LABEL } from "../js/content.js";
import * as St from "../js/study.js";

const GROUP = "control";
const $app = document.getElementById("app");
const $net = document.getElementById("net");
const $dlg = document.getElementById("dlg");
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const P = St.readParams();

let S = St.loadState(GROUP) || { stage: "start" };
const save = () => St.saveState(GROUP, S);
const MAX = () => St.maxScore(S.grade);
// 學生版課後問卷（feedback/student.html，schema webar-feedback-v2，班別靠 event 區分）。
// 開在固定名稱的另一個分頁：本頁完成畫面與〔重新開始（下一位同學）〕保持原樣；下一位同學再按時會重用同一個問卷分頁。
const SURVEY_TARGET = "serpentineStudentSurvey";
const surveyHref = (ev) => `../feedback/student.html?event=${encodeURIComponent(ev || St.DEFAULT_EVENT[GROUP])}`;

St.onNetChange((s) => {
  const t = St.netText(s);
  $net.className = t ? `status show ${s.pending ? "wait" : "ok"}` : "status";
  $net.textContent = t;
});

// ---------- 確認對話框 ----------
function confirmBox(html, yes = "確定", no = "取消") {
  return new Promise((resolve) => {
    $dlg.innerHTML = `<div class="sheet">${html}<div class="row">
      <button class="btn ghost no" style="color:var(--ink);border-color:#94a3b8">${no}</button>
      <button class="btn gold yes">${yes}</button></div></div>`;
    $dlg.classList.add("show");
    const close = (v) => { $dlg.classList.remove("show"); $dlg.innerHTML = ""; resolve(v); };
    $dlg.querySelector(".yes").addEventListener("click", () => close(true));
    $dlg.querySelector(".no").addEventListener("click", () => close(false));
  });
}

// ---------- 畫面 ----------
function render() {
  window.scrollTo(0, 0);
  const pg = document.querySelector(".page");
  if (pg) pg.scrollTop = 0;
  ({ start: viewStart, pre: viewQuiz, wait: viewWait, post: viewQuiz, commit: viewCommit, done: viewDone }[S.stage] || viewStart)();
}

function viewStart() {
  const btn = (g) => {
    const pre = P.grade === g;
    return `<button class="btn ${pre || !P.grade ? "gold" : "ghost"}" data-g="${g}" style="${pre || !P.grade ? "" : "color:var(--ink);border-color:#94a3b8"}">
      ${g === "elem" ? "國小版（五、六年級）" : "國中版"}${pre ? `<span class="tag">老師指定</span>` : ""}</button>`;
  };
  const order = P.grade === "junior" ? ["junior", "elem"] : ["elem", "junior"];
  $app.innerHTML = `<div class="sheet">
    <h2>這是上課前、上課後的小測驗，不記名，也不算成績。</h2>
    <p>上課前先做一次（10 題），上完課再做一次同樣的題目。照你現在的想法作答就好，答錯沒關係！</p>
    <p class="privacy"><b>隱私：</b>不需要輸入姓名或學號；前測、後測作答會以不記名方式上傳，只用於研究統計（不含任何個人資料）。</p>
    <div class="kick" style="margin-top:12px">請選你的版本</div>
    <div class="grade-btns">${order.map(btn).join("")}</div>
  </div>`;
  $app.querySelectorAll("[data-g]").forEach((b) => b.addEventListener("click", () => {
    S = St.newSession(GROUP, { grade: b.dataset.g, event: P.event });
    render();
  }));
}

function viewQuiz() {
  const phase = S.stage; // pre | post
  const nx = St.nextQuestion(S, phase);
  if (!nx) { finishPhase(phase); return; }
  const { i, q, order } = nx;
  // 作答中不顯示面向標籤
  $app.innerHTML = `<div class="sheet">
    <div class="kick">${phase === "pre" ? "前測（上課前）" : "後測（上課後）"}　${i + 1} / ${St.N}　・${GRADE_LABEL[S.grade]}</div>
    <div class="bar"><i style="width:${Math.round((i / St.N) * 100)}%"></i></div>
    <div class="q">${esc(q.q)}</div>
    <div class="opts">${order.map((o, k) => `<button class="opt" data-o="${o}"><b>${"ABCD"[k]}</b>${esc(q.options[o])}</button>`).join("")}</div>
    <p class="privacy" style="margin-top:12px">選好就會自動跳下一題。${phase === "pre" ? "答錯沒關係！" : ""}</p>
  </div>`;
  const btns = [...$app.querySelectorAll(".opt")];
  let done = false;
  btns.forEach((b) => b.addEventListener("click", () => {
    if (done) return;
    done = true;
    btns.forEach((x) => { x.disabled = true; });
    b.classList.add("picked"); // 不顯示對錯
    S[phase].push(St.answer(q, Number(b.dataset.o)));
    save();
    setTimeout(render, 350);
  }));
}

function finishPhase(phase) {
  if (phase === "pre") {
    St.enqueue(St.buildRecord(S, "pre")); // 先進佇列再存階段：中途被關掉，重開時會再跑一次這裡（佇列同 sid＋phase 只留一筆）
    S.stage = "wait";
    save();
    render();
    St.flush();
  } else {
    S.stage = "commit";
    save();
    render();
  }
}

function viewWait() {
  $app.innerHTML = `<div class="sheet rest">
    <div class="big">✅</div>
    <h2>前測完成！</h2>
    <p>請把手機放下，專心聽老師上課。</p>
    <p class="privacy">老師說可以做後測時，再按下面的按鈕。<br>就算關掉網頁，再打開同一個網址也會回到這裡。</p>
    <div class="row"><button class="btn alt go">開始後測 ▶</button></div>
  </div>`;
  $app.querySelector(".go").addEventListener("click", async () => {
    const ok = await confirmBox(`<h2>老師說可以開始後測了嗎？</h2><p>還沒的話請按〔還沒〕，繼續聽老師上課。</p>`, "是，開始後測", "還沒");
    if (!ok) return;
    St.startPost(S); // 選項重新洗牌
    save();
    render();
  });
}

function viewCommit() {
  $app.innerHTML = `<div class="sheet">
    <div class="kick">最後一步・行動承諾</div>
    <div class="q">${esc(ENDING.commitAsk)}</div>
    <div class="opts">${ENDING.commits.map((c, i) => `<button class="opt" data-i="${i}"><b>${i + 1}</b>${esc(c)}</button>`).join("")}</div>
    <div class="row"><button class="btn gold send" disabled>送出 ▶</button></div>
  </div>`;
  const btns = [...$app.querySelectorAll(".opt")];
  const send = $app.querySelector(".send");
  let pick = null;
  btns.forEach((b) => b.addEventListener("click", () => {
    pick = Number(b.dataset.i);
    btns.forEach((x) => x.classList.toggle("picked", x === b));
    send.disabled = false;
  }));
  send.addEventListener("click", () => {
    if (pick === null) return;
    S.commitPick = pick;
    St.enqueue(St.buildRecord(S, "post"));
    S.stage = "done";
    S.doneAt = new Date().toISOString();
    save();
    render();
    St.flush();
  });
}

function viewDone() {
  const qs = St.questions(S.grade);
  const pickText = (q, a) => (a ? `${esc(q.options[a.pick])}` : "—");
  const mark = (q, a) => (!a ? "" : !St.isScored(q) ? `<span class="me">（你的選擇）</span>` : a.correct ? `<span class="ok">✔ 答對</span>` : `<span class="no">✘ 答錯</span>`);
  const rows = qs.map((q, i) => {
    const a = S.pre[i], b = S.post[i];
    return `<div class="rv">
      <div class="rq">${i + 1}. ${esc(q.q)}<span class="facet-chip">${FACET_NAMES[q.facet]}</span></div>
      <div class="ra">前測：${pickText(q, a)} ${mark(q, a)}</div>
      <div class="ra">後測：${pickText(q, b)} ${mark(q, b)}</div>
      ${St.isScored(q) ? `<div class="ra">正確答案：<b>${esc(q.options[q.answer])}</b></div>` : `<div class="ra">這題是態度題，沒有標準答案，不算分。</div>`}
      <div class="ex">💡 ${esc(q.explain)}</div>
    </div>`;
  }).join("");
  $app.innerHTML = `<div class="sheet">
    <div class="kick">完成・${GRADE_LABEL[S.grade]}</div>
    <h2>謝謝你認真作答！</h2>
    <div class="score">
      <div><b>${St.scoreOf(S.pre)} / ${MAX()}</b><span>前測答對</span></div>
      <div><b>${St.scoreOf(S.post)} / ${MAX()}</b><span>後測答對</span></div>
    </div>
    <p class="privacy">只計算 ${MAX()} 題有標準答案的題目；2 題態度題只看你的選擇，不算對錯。</p>
    <p>我的小行動：<b>${esc(ENDING.commits[S.commitPick] || "—")}</b></p>
    <div class="row"><a class="btn gold" href="${surveyHref(S.event)}" target="${SURVEY_TARGET}">📝 填課後問卷（約 3 分鐘）</a></div>
    <p class="privacy" style="text-align:center">請先填問卷，再玩遊戲</p>
    <div class="row"><a class="btn gold" href="../index.html">🎮 現在可以玩遊戲了</a></div>
  </div>
  <div class="sheet">
    <div class="kick">每一題的解說</div>
    ${rows}
  </div>
  <div class="sheet">
    <p class="privacy">換下一位同學用這支手機時，請按下面的按鈕。</p>
    <div class="row"><button class="btn ghost again" style="color:var(--ink);border-color:#94a3b8">🔄 重新開始（下一位同學）</button></div>
  </div>`;
  $app.querySelector(".again").addEventListener("click", async () => {
    const pending = St.queue().length;
    const ok = await confirmBox(`<h2>要換下一位同學了嗎？</h2>
      <p>按〔確定〕後，這支手機上的這次作答畫面會清掉，回到開始頁。</p>
      ${pending ? `<p class="privacy">還有 ${pending} 筆作答等著上傳，會繼續保留並自動補傳。</p>` : ""}`, "確定，下一位", "取消");
    if (!ok) return;
    St.clearState(GROUP);
    St.playerId(true); // 下一位同學換一組新的匿名代碼，避免兩人共用同一 pid
    S = { stage: "start" };
    render();
  });
}

render();
St.installAutoFlush(); // 開頁就補傳之前沒送成功的紀錄
