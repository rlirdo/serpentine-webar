// 語音導覽（2.1.0，2026/10/30：數字一律轉中文，避免「第 2 題」唸成「第兩題」）：只用瀏覽器內建 Web Speech API（speechSynthesis），不載入音檔、不連外部服務。
// - 畫面文字不變；送去唸之前先 normalizeForSpeech() 把化學符號、縮寫、標點轉成可唸的中文。
// - 新的對話文字出現時先 cancel() 舊語音；提示框（toast）排在後面唸，不打斷。
// - 沒有 speechSynthesis 或沒有中文語音時靜默降級，只在 HUD 顯示一次小提示，不丟例外、不卡流程。
// - 測試掛鉤：window.__speech.log 記錄每一次 speak() 的原文與正規化結果（自動通關檢查用）。

const KEY = "serpentineWebAR.voice";

// ---------------------------------------------------------------- 正規化
// 依序套用（先長後短：化學式 → 離子 → 官能基 → 縮寫 → 符號）。
const RULES = [
  // 換行＝句子結束（最先處理，避免後面規則的空白比對把換行吃掉）
  [/[ \t]*\n+[ \t]*/g, "。"],
  // 重複說法先合併（避免「純水 水」「蛇紋石 蛇紋石」「深層海水深層海水」）
  [/純水\s*H₂O/g, "純水"],
  [/蛇紋石\s*Mg₃Si₂O₅\(OH\)₄/g, "蛇紋石"],
  [/Mg₃Si₂O₅\(OH\)₄/g, "蛇紋石"],
  [/深層海水\s*[（(]\s*DSW\s*[）)]/g, "深層海水"],
  [/深層海水\s*DSW/g, "深層海水"],
  [/石材（塊）/g, "石材塊"],
  // 官能基與化學鍵（要在離子與破折號之前）
  [/≡\s*Mg\s*[–-]\s*OH/g, "鎂氫氧基"],
  [/≡\s*Si\s*[–-]\s*OH/g, "矽氫氧基"],
  [/[–-]\s*OH\b/g, "氫氧基"],
  [/Si\s*[–-]\s*O\b/g, "矽氧鍵"],
  // 離子
  [/Mg\s*²⁺/g, "鎂離子"],
  [/Ca\s*²⁺/g, "鈣離子"],
  [/Fe\s*³⁺/g, "鐵離子"],
  [/Fe\s*²⁺/g, "亞鐵離子"],
  [/Na\s*⁺/g, "鈉離子"],
  [/K\s*⁺/g, "鉀離子"],
  [/Cl\s*⁻/g, "氯離子"],
  [/H₂O/g, "水"],
  // 縮寫（逐字母唸）
  [/DSW/g, "深層海水"],
  [/FTIR/g, "F T I R"],
  [/XRD/g, "X R D"],
  [/XPS/g, "X P S"],
  [/\bSEM\b/g, "S E M"],
  [/\bAR\b/g, "A R"],
  // 單位
  [/\s*°\s*C/g, " 度"],
  [/\s*[μµ]m(?![A-Za-z])/g, " 微米"],
  [/(^|[^A-Za-z\s])\s*nm(?![A-Za-z])/g, "$1 奈米"],
  [/(^|[^A-Za-z\s])\s*mL(?![A-Za-z])/g, "$1 毫升"],
  [/(^|[^A-Za-z\s])\s*cm(?![A-Za-z])/g, "$1 公分"],
  [/(^|[^A-Za-z\s])\s*mm(?![A-Za-z])/g, "$1 毫米"],
  [/(^|[^A-Za-z\s])\s*kHz(?![A-Za-z])/g, "$1 千赫"],
  [/(^|[^A-Za-z\s])\s*rpm(?![A-Za-z])/g, "$1 轉"],
  [/(\d+(?:\.\d+)?)\s*[%％]/g, "百分之$1"],
  [/(\d)\.(\d)/g, "$1點$2"],
  // 數字區間與分數
  [/(\d)\s*[–~～-]\s*(\d)/g, "$1到$2"],
  // 進度數字：「已補好 2 / 6」→「已補好2格，共6格」等
  [/已補好\s*(\d+)\s*[/／]\s*(\d+)/g, "已補好$1格，共$2格"],
  [/補好一格！\s*[（(]\s*(\d+)\s*[/／]\s*(\d+)\s*[）)]/g, "補好一格！"],
  [/已選對\s*(\d+)\s*[/／]\s*(\d+)/g, "已選對$1瓶，共$2瓶"],
  [/已洗\s*(\d+)\s*[/／]\s*(\d+)/g, "已洗$1次，共$2次"],
  [/洗滌\s*(\d+)\s*[/／]\s*(\d+)/g, "洗滌第$1次，共$2次"],
  [/(\d+)\s*[/／]\s*(\d+)/g, "$1，共$2"],
  // 加號（例如「離心＋洗滌」）
  [/\s*[＋+]\s*/g, "加"],
  // 箭頭、間隔號、斜線、破折號、刪節號
  [/\s*[→⇒➜]\s*/g, "，變成"],
  [/\s*[・·•]\s*/g, "、"],
  [/\s*[／/]\s*/g, "、"],
  [/\s*(——|—|–)\s*/g, "，"],
  [/\s*(……|…|⋯)+\s*/g, "，"],
  // 勾叉：答對答錯回饋
  [/✔\s*(?=答對)/g, ""],
  [/✘\s*(?=再想想)/g, ""],
  [/[✔✓]\s*/g, "答對了！"],
  [/[✘✗×]\s*/g, "不對喔！"],
  // 星號、表情符號、變體選擇字元
  [/[★☆]/g, ""],
  [/\p{Extended_Pictographic}/gu, ""],
  [/[\uFE0E\uFE0F\u200D]/g, ""],
  // 括號：去掉括號、保留內文（全形圓括號前加停頓）
  [/[〔〕【】「」『』《》〈〉"“”'‘’\[\]]/g, " "],
  [/\s*[（(]\s*/g, "，"],
  [/\s*[）)]\s*/g, ""],
  // 半形標點轉全形
  [/\s*,\s*/g, "，"],
  [/\s*!\s*/g, "！"],
  [/\s*\?\s*/g, "？"],
  [/\s*;\s*/g, "；"],
  [/\s*:\s*/g, "："],
];

// ---------------------------------------------------------------- 數字 → 中文（2.1.0）
// TTS 直接唸阿拉伯數字時，「第 2 題」會唸成「第兩題」，「2到4」也可能唸成「兩到四」。
// 因此在送去唸之前把所有數字轉成中文：序數（第二、二到四、百分之二、清單編號二、）用「二」；
// 數量（兩題、兩顆星、兩百度、兩次）用「兩」；小數逐位唸（零點五）。
const DIG = "零一二三四五六七八九";
function cnInt(n, { liang = false } = {}) {
  n = Number(n);
  if (!Number.isFinite(n) || n < 0) return String(n);
  if (n === 0) return "零";
  if (n === 2 && liang) return "兩";
  if (n < 10) return DIG[n];
  if (n < 20) return "十" + (n % 10 ? DIG[n % 10] : "");
  if (n < 100) return DIG[Math.floor(n / 10)] + "十" + (n % 10 ? DIG[n % 10] : "");
  if (n < 1000) {
    const h = Math.floor(n / 100), r = n % 100;
    const hs = (h === 2 && liang ? "兩" : DIG[h]) + "百";
    if (!r) return hs;
    if (r < 10) return hs + "零" + DIG[r];
    return hs + cnInt(r, { liang });
  }
  if (n < 10000) {
    const t = Math.floor(n / 1000), r = n % 1000;
    const ts = (t === 2 && liang ? "兩" : DIG[t]) + "千";
    if (!r) return ts;
    if (r < 100) return ts + "零" + cnInt(r, { liang });
    return ts + cnInt(r, { liang });
  }
  return [...String(n)].map((d) => DIG[Number(d)]).join(""); // 更大的數逐位唸
}
function cnDigits(str) { return [...String(str)].map((d) => DIG[Number(d)]).join(""); }
const NUM_RULES = [
  // 小數：先把「3點5」（由上面的規則產生）或「3.5」轉成「三點五」
  [/(\d+)[點.](\d+)/g, (m, a, b) => cnInt(a) + "點" + cnDigits(b)],
  // 序數：第 N（題、關、步、次…）一律「第二」
  [/第\s*(\d+)/g, (m, a) => "第" + cnInt(a)],
  // 百分之 N、區間 N到M：用「二」
  [/百分之\s*(\d+)/g, (m, a) => "百分之" + cnInt(a)],
  [/(\d+)\s*到\s*(\d+)/g, (m, a, b) => cnInt(a) + "到" + cnInt(b)],
  // 清單編號「1、」「2、」（句首或標點後）：用「二」
  [/(^|[\s，。；！？：])(\d+)、/g, (m, pre, a) => pre + cnInt(a) + "、"],
  // 其餘：數量，2 唸「兩」（兩題、兩顆星、兩百度、兩次）
  [/\d+/g, (m) => cnInt(m, { liang: true })],
];
export function numbersToChinese(s) {
  let out = String(s);
  for (const [re, to] of NUM_RULES) out = out.replace(re, to);
  return out;
}

const PUNCT = "，。！？、；：";
function tidy(s) {
  return s
    .replace(/[ \t\u3000]+/g, " ")
    .replace(/([，、；：])\s*(?=[，、；：。！？])/g, "") // 「，。」→「。」
    .replace(/([。！？])\s*[，、；：。]+/g, "$1") // 「！，」→「！」
    .replace(/^[\s，、；：。]+/, "")
    .replace(/[\s，、；：]+$/, "")
    .replace(/\s*([，。！？、；：])\s*/g, "$1")
    // 中文字之間不留空白（TTS 會在空白處停頓，「第二 題」會唸得斷斷續續）
    .replace(/([㐀-䶿一-鿿])[ 　]+(?=[㐀-䶿一-鿿])/g, "$1")
    .trim();
}

// 允許留下的字元：中日韓漢字、數字、單一英文字母（逐字母唸）、空白、中文標點
const ALLOWED = /^[\u3400-\u4DBF\u4E00-\u9FFF0-9A-Za-z \u3000，。！？、；：]$/u;
export function speechResidue(s) {
  const bad = [];
  for (const ch of s) if (!ALLOWED.test(ch)) bad.push(ch);
  const words = s.match(/[A-Za-z]{2,}/g) || [];
  return [...bad, ...words];
}

// sweep=true（執行時）：最後再把任何殘留符號刪掉，確保不唸出怪聲；檢查工具用 sweep=false 才看得到殘留。
export function normalizeForSpeech(text, { sweep = true } = {}) {
  let s = String(text == null ? "" : text);
  for (const [re, to] of RULES) s = s.replace(re, to);
  s = numbersToChinese(s);
  s = tidy(s);
  if (sweep) {
    s = [...s].map((ch) => (ALLOWED.test(ch) ? ch : " ")).join("");
    s = tidy(s);
  }
  return s;
}

// HTML 片段 → 純文字；<br>、區塊結尾視為句子分隔
export function htmlToSpeechText(html) {
  const s = String(html == null ? "" : html)
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/(b|span|div|p|li|h\d)>/gi, "\n")
    .replace(/<[^>]*>/g, "");
  let out = s;
  try {
    const ta = document.createElement("textarea");
    ta.innerHTML = s;
    out = ta.value;
  } catch (e) { /* 非瀏覽器環境 */ }
  return out.split("\n").map((x) => x.trim()).filter(Boolean).join("\n");
}

// 依句號／驚嘆號／問號切段；過長再依逗號切（避開 Chrome 長句中斷）
export function splitSentences(s, max = 60) {
  // 不用 lookbehind（iOS 16.3 以前的 Safari 不支援，會讓整個模組載入失敗）
  const parts = (s.match(/[^。！？；]+[。！？；]*|[。！？；]+/g) || []).map((x) => x.trim()).filter(Boolean);
  const out = [];
  for (const p of parts) {
    if (p.length <= max) { out.push(p); continue; }
    let buf = "";
    for (const seg of p.match(/[^，、：]+[，、：]*|[，、：]+/g) || []) {
      if (buf && (buf + seg).length > max) { out.push(buf); buf = ""; }
      buf += seg;
    }
    if (buf) out.push(buf);
  }
  return out;
}

// ---------------------------------------------------------------- 語音引擎
export function createSpeech() {
  const synth = (() => { try { return window.speechSynthesis || null; } catch (e) { return null; } })();
  const UttCtor = (() => { try { return window.SpeechSynthesisUtterance || null; } catch (e) { return null; } })();
  const supported = !!(synth && UttCtor && typeof synth.speak === "function");
  let enabled = true;
  try { enabled = localStorage.getItem(KEY) !== "0"; } catch (e) { /* 無痕模式 */ }
  let rate = 0.95;
  let voice = null;
  let voiceState = supported ? "unknown" : "unsupported"; // unknown | zh | none | unsupported
  let unlocked = false;
  let gen = 0;
  let pending = [];
  let flushTimer = 0;
  let lastReplace = { norm: "", at: 0 };
  const alive = []; // 保留 utterance 參照，避免被回收後 onend 不觸發
  const listeners = { novoice: [] };
  const log = [];
  let warned = false;

  const langOf = (v) => String((v && v.lang) || "").replace(/_/g, "-").toLowerCase();
  const isTW = (v) => /^(zh-tw|cmn-hant-tw|zh-hant-tw|cmn-tw)/.test(langOf(v));
  const isZh = (v) => { const l = langOf(v); return (l.startsWith("zh") || l.startsWith("cmn")) && !l.startsWith("zh-hk") && !l.includes("yue"); };

  function pickVoice() {
    if (!supported) return;
    let vs = [];
    try { vs = synth.getVoices() || []; } catch (e) { vs = []; }
    if (!vs.length) return; // 清單還沒載入（Chrome 會之後觸發 voiceschanged）
    const local = (v) => v.localService !== false;
    voice = vs.find((v) => isTW(v) && local(v)) || vs.find((v) => isZh(v) && local(v))
      || vs.find((v) => isTW(v)) || vs.find((v) => isZh(v)) || null;
    const prev = voiceState;
    voiceState = voice ? "zh" : "none";
    if (voiceState === "none" && prev !== "none") noVoice();
  }
  function noVoice() {
    if (warned) return;
    warned = true;
    listeners.novoice.forEach((fn) => { try { fn(); } catch (e) { /* ignore */ } });
  }

  if (supported) {
    pickVoice();
    try {
      if (synth.addEventListener) synth.addEventListener("voiceschanged", pickVoice);
      else synth.onvoiceschanged = pickVoice;
    } catch (e) { /* ignore */ }
    // 有些裝置清單永遠是空的：不判定為沒有語音，照樣用 lang 嘗試；唸失敗再提示。
  }

  const testVolume = () => (typeof window.__speechTestVolume === "number" ? window.__speechTestVolume : 1);
  const activated = () => {
    try {
      const ua = navigator.userActivation;
      return !ua || ua.hasBeenActive || unlocked;
    } catch (e) { return true; }
  };

  function cancel() {
    gen++;
    clearTimeout(flushTimer);
    pending = [];
    if (!supported) return;
    try { synth.cancel(); } catch (e) { /* ignore */ }
  }

  function makeUtt(text) {
    const u = new UttCtor(text);
    u.lang = "zh-TW";
    u.rate = rate;
    u.pitch = 1;
    u.volume = testVolume();
    if (voice) { try { u.voice = voice; } catch (e) { /* 測試替身不是真的 SpeechSynthesisVoice */ } }
    u.onend = u.onerror = (ev) => {
      const i = alive.indexOf(u);
      if (i >= 0) alive.splice(i, 1);
      if (ev && ev.type === "error" && /language-unavailable|voice-unavailable|synthesis-unavailable/.test(String(ev.error))) noVoice();
    };
    return u;
  }

  function playChunks(chunks, myGen) {
    if (!supported || !enabled || voiceState === "none" || !activated()) return false;
    try {
      if (synth.paused) synth.resume();
      for (const c of chunks) {
        if (myGen !== gen) return true;
        const u = makeUtt(c);
        alive.push(u);
        if (alive.length > 40) alive.shift();
        synth.speak(u);
      }
      return true;
    } catch (e) {
      return false;
    }
  }

  function flush() {
    flushTimer = 0;
    const items = pending;
    pending = [];
    if (!items.length) return;
    const replace = items.some((it) => it.mode === "replace");
    // 同一時間送來的多段（例如提示框＋對話）合併；被別段包含的重複段落略過
    const uniq = [];
    for (const it of items) {
      if (!it.norm) continue;
      if (uniq.some((u) => u.norm.includes(it.norm))) continue;
      for (let k = uniq.length - 1; k >= 0; k--) if (it.norm.includes(uniq[k].norm)) uniq.splice(k, 1);
      uniq.push(it);
    }
    if (!uniq.length) return;
    const joined = uniq.map((u) => u.norm).join("。").replace(/([。！？])。/g, "$1");
    const now = performance.now();
    let speaking = false;
    try { speaking = supported && (synth.speaking || synth.pending); } catch (e) { /* ignore */ }
    // 同一句話在還沒唸完時又被送來（例如先 say 再 next 同一句）：不重頭唸
    if (replace && joined === lastReplace.norm && speaking && now - lastReplace.at < 15000) return;
    if (replace) {
      lastReplace = { norm: joined, at: now };
      gen++;
      if (supported) { try { synth.cancel(); } catch (e) { /* ignore */ } }
    }
    const myGen = gen;
    const chunks = splitSentences(joined);
    // cancel 後稍等再 speak（Safari 立刻 speak 偶爾會被吞掉）
    const go = () => playChunks(chunks, myGen);
    if (replace && supported) setTimeout(go, 60); else go();
  }

  // text：顯示的純文字或 HTML；opts.html=true 時先轉純文字；opts.say 可指定另外的唸法
  function speak(text, { html = false, mode = "replace", say = null, kind = "say" } = {}) {
    const raw = html ? htmlToSpeechText(text) : String(text == null ? "" : text);
    const src = say != null ? String(say) : raw;
    const norm = normalizeForSpeech(src);
    const entry = { i: log.length, t: Math.round(performance.now()), kind, mode, raw, src, norm, pre: normalizeForSpeech(src, { sweep: false }), enabled, voiceState, activated: activated() };
    log.push(entry);
    if (log.length > 3000) log.splice(0, 1000);
    if (!norm) return;
    if (!enabled || !supported) return;
    pending.push({ norm, mode });
    if (!flushTimer) flushTimer = setTimeout(flush, 30);
  }

  // 第一次使用者手勢時呼叫：唸一個極短的空白 utterance，解鎖 iOS／Android 的語音播放
  // iOS 只認 touchend／click 這類手勢；前 3 次手勢都補唸一次空白 utterance，確保至少一次落在被認可的手勢裡
  let unlockTries = 0;
  function unlock() {
    if (!supported || unlockTries >= 3) return;
    unlockTries++;
    unlocked = true;
    if (synth.speaking || synth.pending) return; // 正在唸：已經解鎖，不要打斷
    try {
      const u = new UttCtor(" ");
      u.volume = 0;
      u.lang = "zh-TW";
      alive.push(u);
      synth.speak(u);
    } catch (e) { /* ignore */ }
    if (voiceState === "unknown") pickVoice();
  }

  const api = {
    get supported() { return supported; },
    get enabled() { return enabled; },
    get voiceState() { return voiceState; },
    get voiceName() { return voice ? `${voice.name} (${voice.lang})` : ""; },
    get rate() { return rate; },
    log,
    speak,
    cancel,
    unlock,
    pickVoice,
    setGrade(g) { rate = g === "junior" ? 1.05 : 0.95; },
    setEnabled(on) {
      enabled = !!on;
      try { localStorage.setItem(KEY, enabled ? "1" : "0"); } catch (e) { /* ignore */ }
      if (!enabled) cancel();
    },
    toggle() { api.setEnabled(!enabled); return enabled; },
    onNoVoice(fn) {
      listeners.novoice.push(fn);
      if (warned) { try { fn(); } catch (e) { /* ignore */ } }
    },
    // 沒有 speechSynthesis 也當作「沒有中文語音」提示一次
    checkUnsupported() { if (!supported) noVoice(); },
  };

  // 離開頁面或切到背景時停止
  try {
    document.addEventListener("visibilitychange", () => { if (document.hidden) cancel(); });
    window.addEventListener("pagehide", cancel);
    window.addEventListener("beforeunload", cancel);
  } catch (e) { /* ignore */ }

  // 第一個使用者點擊（開始鈕／下一步）就解鎖
  try {
    const once = () => { unlock(); };
    ["touchend", "click", "keydown"].forEach((t) => document.addEventListener(t, once, { capture: true, passive: true }));
  } catch (e) { /* ignore */ }

  window.__speech = {
    log, normalize: normalizeForSpeech, residue: speechResidue, html: htmlToSpeechText,
    state: () => ({ supported, enabled, voiceState, voice: voice ? { name: voice.name, lang: voice.lang, local: voice.localService } : null, rate, unlocked, activated: activated(), speaking: supported ? !!synth.speaking : false }),
  };
  return api;
}
