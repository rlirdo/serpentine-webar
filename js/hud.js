// DOM 疊層：關卡進度條（8 格）、對話框、按鈕、星星、能量條、提示、全螢幕對話框、製作者字樣。
import { CREDIT, LEVELS } from "./content.js";

const h = (tag, cls, html) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html != null) e.innerHTML = html;
  return e;
};

export function createHud({ audio } = {}) {
  if (!document.getElementById("credit")) {
    const c = h("div", null, CREDIT);
    c.id = "credit";
    document.body.appendChild(c);
  }
  const root = h("div");
  root.id = "hud";
  root.innerHTML = `
    <div class="hud-top">
      <div class="lvl-chip">墨玉晶格修復任務</div>
      <div class="stars-total" title="星星">★ <span>0</span></div>
      <button class="icon-btn mute" aria-label="音效開關">🔊</button>
      <div class="progress">${LEVELS.map((l, i) => `<div class="cell" title="${l.name}">${i + 1}</div>`).join("")}</div>
    </div>
    <div class="energy"><span>小晶能量</span><div class="bar"><i></i></div></div>
    <div class="float-tip"></div>
    <div class="toast"></div>
    <div class="panel hidden">
      <div class="speaker"><span class="ava"></span><span class="who">墨玉小晶</span></div>
      <div class="say"></div>
      <div class="meter"><div class="lab"><span class="ml"></span><span class="mr"></span></div><div class="track"><i></i></div></div>
      <div class="btns"></div>
    </div>
    <div class="modal-wrap"><div class="modal"></div></div>`;
  document.body.appendChild(root);
  const $ = (s) => root.querySelector(s);
  const el = {
    chip: $(".lvl-chip"), stars: $(".stars-total span"), mute: $(".mute"), cells: [...root.querySelectorAll(".cell")],
    energy: $(".energy"), energyBar: $(".energy .bar i"), floatTip: $(".float-tip"), toast: $(".toast"),
    panel: $(".panel"), say: $(".say"), who: $(".who"), meter: $(".meter"), ml: $(".meter .ml"), mr: $(".meter .mr"),
    mbar: $(".meter .track i"), btns: $(".btns"), modalWrap: $(".modal-wrap"), modal: $(".modal"),
  };

  // 自動通關（?autoplay=1）用：遊戲在每個等待輸入的時刻登記一個動作
  const ap = { label: "boot", action: null, seq: 0 };
  const setAP = (label, action) => { ap.label = label; ap.action = action; ap.seq++; };

  const syncMute = () => { el.mute.textContent = audio && audio.muted ? "🔇" : "🔊"; };
  el.mute.addEventListener("click", () => { if (audio) { audio.toggle(); syncMute(); } });
  syncMute();

  let toastTimer = 0;
  const hud = {
    root, el, ap, setAP,
    setTitle(text) { el.chip.textContent = text; },
    setProgress(current, doneCount) {
      el.cells.forEach((c, i) => {
        c.classList.toggle("done", i < doneCount);
        c.classList.toggle("now", i === current);
      });
    },
    setStars(n) { el.stars.textContent = n; },
    setEnergy(show, v = 0) {
      el.energy.classList.toggle("show", !!show);
      el.energyBar.style.width = Math.round(Math.max(0, Math.min(1, v)) * 100) + "%";
    },
    toast(text, { ms = 2200, warn = false } = {}) {
      el.toast.textContent = text;
      el.toast.classList.toggle("warn", warn);
      el.toast.classList.add("show");
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => el.toast.classList.remove("show"), ms);
    },
    floatTip(show, text = "") {
      el.floatTip.textContent = text;
      el.floatTip.classList.toggle("show", !!show);
    },
    showPanel(show = true) { el.panel.classList.toggle("hidden", !show); },
    say(html, { who = "墨玉小晶" } = {}) {
      hud.showPanel(true);
      el.who.textContent = who;
      el.say.innerHTML = html;
      el.say.classList.remove("fadein");
      void el.say.offsetWidth;
      el.say.classList.add("fadein");
    },
    meter(show, label = "", value = 0, right = "") {
      el.meter.classList.toggle("show", !!show);
      if (!show) return;
      el.ml.textContent = label;
      el.mr.textContent = right;
      el.mbar.style.width = Math.round(Math.max(0, Math.min(1, value)) * 100) + "%";
    },
    // list: [{label, cls, onClick, hold:{down, up}}]
    buttons(list = [], { grid = false } = {}) {
      el.btns.innerHTML = "";
      el.btns.classList.toggle("grid", grid);
      return list.map((b) => {
        const btn = h("button", "btn " + (b.cls || ""), b.label);
        btn.type = "button";
        if (b.onClick) btn.addEventListener("click", (e) => { if (!btn.disabled) { audio && audio.tap(); b.onClick(e, btn); } });
        if (b.hold) {
          const down = (e) => { e.preventDefault(); btn.classList.add("pressed"); b.hold.down(); };
          const up = () => { if (btn.classList.contains("pressed")) { btn.classList.remove("pressed"); b.hold.up(); } };
          btn.addEventListener("pointerdown", down);
          btn.addEventListener("pointerup", up);
          btn.addEventListener("pointerleave", up);
          btn.addEventListener("pointercancel", up);
          btn.addEventListener("contextmenu", (e) => e.preventDefault());
        }
        el.btns.appendChild(btn);
        return btn;
      });
    },
    // 顯示一句話＋一顆按鈕，按下後 resolve
    next(html, { label = "下一步 ▶", cls = "", ap: apLabel = "next" } = {}) {
      return new Promise((res) => {
        hud.say(html);
        const [b] = hud.buttons([{ label, cls, onClick: () => res() }]);
        setAP(apLabel, () => b.click());
      });
    },
    // 對話框內的選項按鈕，resolve 為索引
    choose(html, labels, { grid = false, ap: apLabel = "choose", apPick = 0, cls = "alt" } = {}) {
      return new Promise((res) => {
        hud.say(html);
        const bs = hud.buttons(labels.map((l, i) => ({ label: l, cls, onClick: () => res(i) })), { grid });
        setAP(apLabel, () => bs[typeof apPick === "function" ? apPick() : apPick].click());
      });
    },
    clearButtons() { el.btns.innerHTML = ""; },
    modal(html) {
      el.modal.innerHTML = html;
      el.modalWrap.classList.add("show");
      el.modalWrap.scrollTop = 0;
      return el.modal;
    },
    closeModal() { el.modalWrap.classList.remove("show"); el.modal.innerHTML = ""; },
  };
  return hud;
}
