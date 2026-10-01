// 自動通關（?autoplay=1）：由測試腳本經 CDP 呼叫 window.__ap.step() 一步步觸發互動。
export function installAutoplay(hud, game) {
  const errors = [];
  const origErr = console.error.bind(console);
  console.error = (...a) => { errors.push(a.map(String).join(" ")); origErr(...a); };
  window.addEventListener("error", (e) => errors.push(String(e.message || e)));
  window.addEventListener("unhandledrejection", (e) => errors.push("unhandledrejection: " + String(e.reason)));
  window.__ap = {
    get label() { return hud.ap.label; },
    get seq() { return hud.ap.seq; },
    get ready() { return !!hud.ap.action; },
    errors,
    step() {
      const a = hud.ap.action;
      if (!a) return false;
      hud.ap.action = null;
      a();
      return true;
    },
    // 版面檢查：製作者字樣存在、可見、在最上層；文字是否超出視窗或容器
    check() {
      const out = { credit: false, creditTop: false, overflow: [] };
      const c = document.getElementById("credit");
      if (c) {
        const r = c.getBoundingClientRect();
        const cs = getComputedStyle(c);
        out.credit = c.textContent.trim() === "NDHU自資系游豐兆製作" && r.width > 0 && cs.visibility !== "hidden" && cs.display !== "none"
          && r.right <= innerWidth + 0.5 && r.bottom <= innerHeight + 0.5 && r.left >= 0 && r.top >= 0;
        const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        // 字樣 pointer-events:none，elementFromPoint 會穿過它；改以 z-index 判斷
        out.creditTop = Number(cs.zIndex) >= 2147483647;
        out.creditRect = [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)];
        out.under = top ? (top.className || top.tagName) : null;
        // 與按鈕重疊檢查
        out.btnOverlap = [...document.querySelectorAll("#hud button, #hud .btn, a.btn")].filter((b) => {
          // 以可見範圍判斷（捲動容器外被裁掉的部分不算）
          const q0 = b.getBoundingClientRect();
          if (!q0.width || getComputedStyle(b).visibility === "hidden") return false;
          const q = { left: q0.left, right: q0.right, top: q0.top, bottom: q0.bottom };
          for (let p = b.parentElement; p; p = p.parentElement) {
            const ov = getComputedStyle(p).overflowY;
            if (ov === "auto" || ov === "scroll" || ov === "hidden") {
              const pr = p.getBoundingClientRect();
              q.top = Math.max(q.top, pr.top); q.bottom = Math.min(q.bottom, pr.bottom);
              q.left = Math.max(q.left, pr.left); q.right = Math.min(q.right, pr.right);
            }
          }
          if (q.bottom <= q.top || q.right <= q.left) return false;
          return !(q.right <= r.left || q.left >= r.right || q.bottom <= r.top || q.top >= r.bottom);
        }).map((b) => b.textContent.trim().slice(0, 20));
      }
      const vis = (el) => { const s = getComputedStyle(el); return s.display !== "none" && s.visibility !== "hidden" && el.getClientRects().length > 0; };
      document.querySelectorAll("#hud .say, #hud .btn, #hud .lvl-chip, #hud .toast.show, #hud .modal .opt, #hud .modal .q, #hud .meter .lab, #hud .cmp span").forEach((el) => {
        if (!vis(el)) return;
        const r = el.getBoundingClientRect();
        const scroller = el.closest(".panel, .modal-wrap");
        const inScroll = scroller && scroller.scrollHeight > scroller.clientHeight + 1;
        const outX = r.left < -0.5 || r.right > innerWidth + 0.5;
        const outY = !inScroll && (r.top < -0.5 || r.bottom > innerHeight + 0.5);
        const clipped = el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).overflowX !== "visible" && !el.classList.contains("lvl-chip");
        if (outX || outY || clipped) out.overflow.push({ cls: el.className, text: el.textContent.trim().slice(0, 24), rect: [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)], clipped });
      });
      const chip = document.querySelector("#hud .lvl-chip");
      if (chip && chip.scrollWidth > chip.clientWidth + 1) out.overflow.push({ cls: "lvl-chip(ellipsis)", text: chip.textContent });
      return out;
    },
  };
}
