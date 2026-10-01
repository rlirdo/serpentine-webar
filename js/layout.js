// 版面：回傳 3D 場景可用的螢幕區域（扣掉上方進度條、對話框與製作者字樣），與 css/style.css 的媒體查詢一致。
export function freeRect(w, h) {
  const side = w > h && (h < 520 || w >= 900); // 矮橫向手機或寬螢幕：對話框在右側
  const top = side && h < 520 ? 78 : w < 600 ? 96 : 84;
  if (side) {
    const panelW = h < 520 ? w * 0.44 : Math.min(440, w * 0.4);
    return { x0: 0, x1: w - panelW - 16, y0: top, y1: h - 30, side };
  }
  const bottom = Math.min(h * 0.42, w < 600 ? 250 : 210);
  return { x0: 0, x1: w, y0: top, y1: h - bottom - 30, side };
}

// 讓 stage（1 單位＝任務卡寬）放進可用區域：回傳每像素需要的 stage 單位數與區域中心
export function fitInfo(w, h) {
  const r = freeRect(w, h);
  const fw = r.x1 - r.x0, fh = Math.max(120, r.y1 - r.y0);
  return { need: Math.max(1.22 / fh, 1.12 / fw), cx: (r.x0 + r.x1) / 2, cy: (r.y0 + r.y1) / 2 };
}
