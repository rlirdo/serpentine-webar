// 玩家資料 → 主角 id 與單位徽章（不記名：只用年齡帶、性別、單位關鍵字）
export const HEROES = [
  { band: "kid", name: "小小晶球師", intro: "戴著海浪漁夫帽、握著紅色滴管瓶，最愛看液滴變成圓球。" },
  { band: "teen", name: { f: "晶球少女", m: "晶球少年", n: "晶球少年少女" }, intro: "穿著東華綠 T 恤、戴護目鏡，準備好滴出第一顆晶球！" },
  { band: "adult", name: "綠色化學研究員", intro: "白色實驗衣上別著綠燒瓶徽章，用水做實驗、廢液分類處理。" },
  { band: "elder", name: "資深採藻人", intro: "戴草帽、背著藻籃，最懂花蓮海邊的褐藻。" },
];
export const SEX = ["f", "m", "n"];
export const HERO_IDS = HEROES.flatMap((h) => SEX.map((s) => `${h.band}_${s}`)); // 12 位

export function bandOf(age, org = "") {
  const a = Number(age);
  if (age !== "" && age != null && Number.isFinite(a)) {
    if (a <= 12) return "kid";
    if (a <= 18) return "teen";
    if (a <= 64) return "adult";
    return "elder";
  }
  const o = String(org || "");
  if (o.includes("國小")) return "kid";
  if (o.includes("國中") || o.includes("高中")) return "teen";
  if (o.includes("大學")) return "adult";
  return "adult";
}
export function sexOf(gender) { return gender === "女" ? "f" : gender === "男" ? "m" : "n"; }
export function heroFor(age, gender, org) { return `${bandOf(age, org)}_${sexOf(gender)}`; }
export function heroInfo(id) {
  const [band, s] = String(id).split("_");
  const h = HEROES.find((x) => x.band === band) || HEROES[2];
  const name = typeof h.name === "string" ? h.name : h.name[s] || h.name.n;
  return { id, band, sex: s, name, intro: h.intro };
}
// 年齡 ≤12 → 國小版；年齡空白而單位含「國小」→ 國小版
export function gradeFor(age, org) {
  const a = Number(age);
  if (age !== "" && age != null && Number.isFinite(a)) return a <= 12 ? "elem" : "junior";
  return String(org || "").includes("國小") ? "elem" : "junior";
}
// 單位關鍵字徽章
export function badgesFor(org) {
  const o = String(org || "");
  const out = [];
  if (o.includes("東華")) out.push({ id: "ndhu", label: "NDHU", color: "#2E7D5B" });
  if (o.includes("國小")) out.push({ id: "elem", label: "國小", color: "#1C7293" });
  if (o.includes("國中") || o.includes("高中")) out.push({ id: "teen", label: o.includes("高中") ? "高中" : "國中", color: "#065A82" });
  if (o.includes("大學")) out.push({ id: "uni", label: "大學", color: "#C99A3E" });
  return out;
}
