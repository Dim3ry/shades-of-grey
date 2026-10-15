// The checks for colour.js (Coach 1: the colour engine). Run by tests/test_colour_engine.py,
// or on its own:  node tests/colour_engine_check.js
// Every check compares against an answer worked out independently (colour theory, or a published
// test table), not against what the code happens to return.
const fs = require("fs");
const path = require("path");
const C = require(path.join(__dirname, "..", "colour.js"));

let passed = 0;
const failures = [];
function check(name, ok, detail) {
  if (ok) passed++; else failures.push(name + (detail === undefined ? "" : "  -> " + JSON.stringify(detail)));
}
const near = (a, b, tol) => Math.abs(a - b) <= tol;
const hueGap = (a, b) => { const d = Math.abs(a - b) % 360; return Math.min(d, 360 - d); };
const H = (hex) => C.hexToHsl(hex);

// ---- 1. Reading and writing colours ----
check("hexToRgb basic", JSON.stringify(C.hexToRgb("#1e3a8a")) === "[30,58,138]");
check("hexToRgb capitals", JSON.stringify(C.hexToRgb("#FFAA00")) === "[255,170,0]");
for (const bad of ["", "#fff", "1e3a8a", "#12345g", null, undefined, 42, "#1234567"]) {
  check("hexToRgb rejects " + String(bad), C.hexToRgb(bad) === null);
  check("hexToHsl rejects " + String(bad), C.hexToHsl(bad) === null);
  check("harmonies rejects " + String(bad), C.harmonies(bad) === null);
}
// Known hue/saturation/lightness values from colour theory
const known = [
  ["#ff0000", 0, 1, 0.5], ["#00ff00", 120, 1, 0.5], ["#0000ff", 240, 1, 0.5],
  ["#ffff00", 60, 1, 0.5], ["#00ffff", 180, 1, 0.5], ["#ff00ff", 300, 1, 0.5],
  ["#000000", 0, 0, 0], ["#ffffff", 0, 0, 1], ["#808080", 0, 0, 0.502],
  ["#800000", 0, 1, 0.251],
];
for (const [hex, h, s, l] of known) {
  const got = H(hex);
  check("hexToHsl " + hex, near(got.h, h, 0.5) && near(got.s, s, 0.01) && near(got.l, l, 0.01), got);
}
check("blue #1e3a8a hue about 224", near(H("#1e3a8a").h, 224, 1), H("#1e3a8a"));
check("hslToHex red", C.hslToHex(0, 1, 0.5) === "#ff0000");
check("hslToHex wraps negative and large hues", C.hslToHex(-120, 1, 0.5) === "#0000ff" && C.hslToHex(480, 1, 0.5) === "#00ff00");
check("hslToHex clamps", C.hslToHex(0, 5, 0.5) === "#ff0000" && C.hslToHex(0, 1, 9) === "#ffffff" && C.hslToHex(0, 1, -2) === "#000000");
// Round trip over a spread of colours
let worstRound = 0;
for (let r = 0; r < 256; r += 17) for (let g = 0; g < 256; g += 17) for (let b = 0; b < 256; b += 17) {
  const hex = C.rgbToHex(r, g, b);
  const c = H(hex);
  const back = C.hexToRgb(C.hslToHex(c.h, c.s, c.l));
  worstRound = Math.max(worstRound, Math.abs(back[0] - r), Math.abs(back[1] - g), Math.abs(back[2] - b));
}
check("hex -> hsl -> hex round trip within 1", worstRound <= 1, worstRound);

// ---- 2. Colour distance (CIEDE2000) against published test data ----
// Pairs 1-3 and 21 are from Sharma, Wu & Dalal (2005), the paper that defines the formula.
const sharma = [
  [{ L: 50, a: 2.6772, b: -79.7751 }, { L: 50, a: 0, b: -82.7485 }, 2.0425],
  [{ L: 50, a: 3.1571, b: -77.2803 }, { L: 50, a: 0, b: -82.7485 }, 2.8615],
  [{ L: 50, a: 2.8361, b: -74.0200 }, { L: 50, a: 0, b: -82.7485 }, 3.4412],
  [{ L: 50, a: 2.5, b: 0 }, { L: 50, a: 0, b: -2.5 }, 4.3065],
  [{ L: 50, a: 2.5, b: 0 }, { L: 73, a: 25, b: -18 }, 27.1492],
  [{ L: 50, a: 2.5, b: 0 }, { L: 61, a: -5, b: 29 }, 22.8977],
  [{ L: 60.2574, a: -34.0099, b: 36.2677 }, { L: 60.4626, a: -34.1751, b: 39.4387 }, 1.2644],
  [{ L: 2.0776, a: 0.0795, b: -1.1350 }, { L: 0.9033, a: -0.0636, b: -0.5514 }, 0.9082],
];
sharma.forEach(([p, q, want], i) => {
  const got = C.labDistance(p, q);
  check("Sharma pair " + (i + 1), near(got, want, 0.0002), { got, want });
  check("Sharma pair " + (i + 1) + " is symmetric", near(C.labDistance(q, p), got, 0.0002));
});
check("distance of a colour to itself is 0", C.colourDistance("#1e3a8a", "#1e3a8a") === 0);
check("black vs white is about 100", near(C.colourDistance("#000000", "#ffffff"), 100, 0.5), C.colourDistance("#000000", "#ffffff"));
check("distance bad input -> null", C.colourDistance("nope", "#ffffff") === null && C.colourDistance("#fff", null) === null);
check("red vs green far apart", C.colourDistance("#ff0000", "#00ff00") > 50);
check("two near blues are close", C.colourDistance("#1e3a8a", "#1f3b8b") < 1);
check("near blue is closer than orange", C.colourDistance("#1e3a8a", "#2a4a9a") < C.colourDistance("#1e3a8a", "#e08020"));
// Lab known values (white is L 100, black is 0)
const white = C.hexToLab("#ffffff"), black = C.hexToLab("#000000"), red = C.hexToLab("#ff0000");
check("Lab of white", near(white.L, 100, 0.05) && near(white.a, 0, 0.05) && near(white.b, 0, 0.05), white);
check("Lab of black", near(black.L, 0, 0.05), black);
check("Lab of red (53.24, 80.09, 67.20)", near(red.L, 53.24, 0.1) && near(red.a, 80.09, 0.2) && near(red.b, 67.20, 0.2), red);

// ---- 3. Harmonies: the pairs everyone knows ----
const blue = C.harmonies("#0000ff");
check("blue's opposite is yellow", blue.complementary === "#ffff00", blue.complementary);
check("red's opposite is cyan", C.harmonies("#ff0000").complementary === "#00ffff");
check("green's opposite is magenta", C.harmonies("#00ff00").complementary === "#ff00ff");
const red100 = C.harmonies("#ff0000");
check("red neighbours are orange-ish and pink-ish", red100.analogous.includes("#ff8000") && red100.analogous.includes("#ff0080"), red100.analogous);
check("red triad is green and blue", red100.triad.includes("#00ff00") && red100.triad.includes("#0000ff"), red100.triad);
// Painter's blue: opposite should be orange
const navy = C.harmonies("#2255cc");
check("a mid blue's opposite is orange", C.colourFamily(navy.complementary) === "orange", [navy.complementary, C.colourFamily(navy.complementary)]);
// Every harmony is the right angle round the wheel, with the same saturation and lightness
let angleBad = 0;
for (const base of ["#1e3a8a", "#c01411", "#52b244", "#b69fcc", "#f4874e", "#7658a5", "#038c67", "#d1a570"]) {
  const b = H(base), h = C.harmonies(base);
  const test = (hex, angle) => {
    const c = H(hex);
    if (hueGap(c.h, b.h + angle) > 2.5 || !near(c.s, b.s, 0.03) || !near(c.l, b.l, 0.03)) angleBad++;
  };
  test(h.complementary, 180);
  test(h.analogous[0], -30); test(h.analogous[1], 30);
  test(h.split[0], 150); test(h.split[1], 210);
  test(h.triad[0], 120); test(h.triad[1], 240);
}
check("all harmony angles are right, same saturation and lightness", angleBad === 0, angleBad);
check("opposite of opposite is the original (within 1 step)",
  C.colourDistance(C.harmonies(C.harmonies("#7658a5").complementary).complementary, "#7658a5") < 2);
// Neutrals
const n = C.harmonies("#1e3a8a").neutrals;
check("three neutrals: dark, mid, light", n.length === 3 && H(n[0]).l < 0.2 && near(H(n[1]).l, 0.5, 0.05) && H(n[2]).l > 0.85, n);
check("neutrals stay faint (saturation 0.15 or less)", n.every((c) => H(c).s <= 0.16), n.map((c) => H(c).s));
check("neutrals lean towards the base hue", n.every((c) => hueGap(H(c).h, H("#1e3a8a").h) < 8), n);
// Hue meaning
check("blue hue is meaningful", C.harmonies("#1e3a8a").hueMeaningful === true);
check("grey hue is not meaningful", C.harmonies("#808080").hueMeaningful === false);
check("near-black hue is not meaningful", C.harmonies("#0a0a14").hueMeaningful === false);
check("near-white hue is not meaningful", C.harmonies("#f8f8ff").hueMeaningful === false);
check("grey still gives full lists", C.harmonies("#808080").analogous.length === 2 && C.harmonies("#808080").triad.length === 2);
check("harmonies keeps the base (lower-cased)", C.harmonies("#1E3A8A").base === "#1e3a8a");
check("every harmony colour is a valid #rrggbb", (() => {
  const h = C.harmonies("#c01411");
  return [h.complementary, ...h.analogous, ...h.split, ...h.triad, ...h.neutrals].every(C.isHex);
})());

// ---- 4. Plain-English names ----
const fam = {
  "#ff0000": "red", "#00c000": "green", "#006000": "dark green", "#2255cc": "blue", "#ffff00": "yellow", "#ff8000": "orange",
  "#8040c0": "purple", "#000000": "near-black", "#ffffff": "near-white", "#808080": "grey",
  "#303030": "dark grey", "#c8c8c8": "light grey", "#5b4923": "brown", "#7d1f1f": "dark red", "#ffb0b0": "pale red",
};
for (const [hex, want] of Object.entries(fam)) check("colourFamily " + hex, C.colourFamily(hex) === want, C.colourFamily(hex));
check("colourFamily bad input", C.colourFamily("x") === null);

// ---- 5. Nearest paint ----
const P = (name, colour, extra) => Object.assign({ brand: "Test", name, colour }, extra || {});
const paints = [
  P("Navy", "#1e3a8a", { status: "owned" }),
  P("Sky", "#58c1cd"),
  P("Fire Orange", "#f4874e", { owned: true }),
  P("Pale Orange", "#f5a87a"),
  P("Blood", "#7d1f1f", { status: "wishlist" }),
  P("Moss", "#486c25", { status: "low" }),
  P("Untouched", "#808080"),
  P("Sand", "#bb9662", { status: "empty" }),
  P("Basing Grit", "#c8b878", { type: "material" }),
  P("Broken", "not a colour"),
  P("Gold Leaf Metallic", "#d3b587", { status: "owned" }),
];
// Exact colour comes back first with distance 0
const exact = C.nearestPaints("#58c1cd", paints, { ownedFirst: false });
check("exact colour found first", exact[0].paint.name === "Sky" && exact[0].distance === 0 && exact[0].quality === "good" && exact[0].confidence === 1, exact[0]);
check("default limit is 3", C.nearestPaints("#58c1cd", paints).length === 3);
check("limit is respected", C.nearestPaints("#58c1cd", paints, { limit: 2 }).length === 2 && C.nearestPaints("#58c1cd", paints, { limit: 50 }).length <= paints.length);
check("bad limit falls back to 3", C.nearestPaints("#58c1cd", paints, { limit: -4 }).length === 3 && C.nearestPaints("#58c1cd", paints, { limit: "x" }).length === 3);
// Owned first
const ownedFirst = C.nearestPaints("#58c1cd", paints, { limit: 8 });
const flags = ownedFirst.map((e) => e.owned);
check("owned paints come before unowned ones", flags.indexOf(false) === -1 || !flags.slice(flags.indexOf(false)).includes(true), flags);
check("Sky (not owned) is not first when ownedFirst is on", ownedFirst[0].owned === true && ownedFirst[0].paint.name !== "Sky", ownedFirst[0].paint.name);
check("within the owned group, nearer comes first",
  ownedFirst.filter((e) => e.owned).every((e, i, a) => i === 0 || a[i - 1].distance <= e.distance));
check("Owned, Running low and old owned:true all count; wishlist/empty don't",
  C.haveIt(paints[0]) && C.haveIt(paints[5]) && C.haveIt(paints[2]) && !C.haveIt(paints[4]) && !C.haveIt(paints[7]) && !C.haveIt(paints[1]));
check("status beats the old owned flag", C.haveIt({ status: "empty", owned: true }) === false);
// Things that can't be matched
const everything = C.nearestPaints("#808080", paints, { limit: 50, ownedFirst: false }).map((e) => e.paint.name);
check("untouched grey, materials and broken colours are skipped",
  !everything.includes("Untouched") && !everything.includes("Basing Grit") && !everything.includes("Broken"), everything);
check("everything else is kept", everything.length === 8, everything);
// Exclude list
const excl = C.nearestPaints("#58c1cd", paints, { ownedFirst: false, exclude: ["#58C1CD"] });
check("exclude skips that colour (any capitals)", !excl.some((e) => e.paint.name === "Sky"));
// Duplicates: the user's copy and the built-in copy of the same paint
const dup = C.nearestPaints("#1e3a8a", [P("Navy", "#1e3a8a"), P("Navy", "#1e3a8a", { status: "owned" })], { limit: 5 });
check("same paint listed twice appears once, owned copy kept", dup.length === 1 && dup[0].owned === true, dup);
// Quality and honesty about poor matches
const reds = [P("Red A", "#c01411"), P("Red B", "#7d1f1f")];
const poor = C.nearestPaints("#52b244", reds)[0];
check("a green asked of a list of reds is a poor match with low confidence", poor.quality === "poor" && poor.confidence < 0.3, poor);
const close = C.nearestPaints("#58c1cd", [P("Slightly off", "#5fc5d0")])[0];
check("a slightly off colour is good", close.quality === "good" && close.confidence > 0.8, close);
check("quality steps are in order", (() => {
  const q = (d, r) => C.judgeMatch(d, r).quality;
  return q(0) === "good" && q(6) === "good" && q(6.1) === "close" && q(15) === "close" && q(15.1) === "poor" && q(100) === "poor";
})());
check("confidence goes down as distance goes up and never leaves 0..1", (() => {
  let last = 2;
  for (const d of [0, 2, 5, 10, 20, 39, 40, 80, 500]) {
    const c = C.judgeMatch(d, false).confidence;
    if (c > last || c < 0 || c > 1) return false;
    last = c;
  }
  return true;
})());
// Rough colours (metallics, Contrast, washes)
check("metallic by name counts as rough", C.isRoughColour(P("Retributor Armour Gold", "#d3b587")) && C.isRoughColour(P("Leadbelcher Metallic", "#888888")));
check("contrast / wash by type or name counts as rough",
  C.isRoughColour(P("Baal Red", "#a00", { type: "contrast" })) && C.isRoughColour(P("Nuln Oil Wash", "#222222")) && C.isRoughColour(P("Speedpaint Blue", "#2255cc")));
check("ordinary paints are not rough", !C.isRoughColour(P("Macragge Blue", "#0d407f")) && !C.isRoughColour(P("Mephiston Red", "#9a1115")) && !C.isRoughColour(null));
check("rough paints are judged more loosely", C.judgeMatch(7, true).quality === "good" && C.judgeMatch(7, false).quality === "close");
const roughMatch = C.nearestPaints("#d3b587", [P("Gold Leaf Metallic", "#d3b587")])[0];
check("a rough match is flagged approximate, even when exact", roughMatch.approximate === true && roughMatch.distance === 0, roughMatch);
check("an ordinary match is not flagged approximate", C.nearestPaints("#58c1cd", [P("Sky", "#58c1cd")])[0].approximate === false);
// Convenience helpers
check("closestOwned ignores unowned paints", C.closestOwned("#58c1cd", paints).owned === true && C.closestOwned("#58c1cd", paints).paint.name !== "Sky");
check("closestAny finds the true nearest", C.closestAny("#58c1cd", paints).paint.name === "Sky");
check("closestOwned is null when you own nothing", C.closestOwned("#58c1cd", [P("Sky", "#58c1cd")]) === null);
// Never throws
for (const [w, l] of [["nope", paints], [null, paints], ["#fff", paints], ["#58c1cd", null], ["#58c1cd", "paints"], ["#58c1cd", []], ["#58c1cd", [null, undefined, 5, {}]]]) {
  let out, threw = false;
  try { out = C.nearestPaints(w, l); } catch (e) { threw = true; }
  check("nearestPaints is safe with " + JSON.stringify(w) + " / " + typeof l, !threw && Array.isArray(out) && out.length === 0, out);
}
check("closestOwned / closestAny safe with nothing", C.closestOwned("#58c1cd", null) === null && C.closestAny("zzz", null) === null);
// Does not change the lists it is given
const before = JSON.stringify(paints);
C.nearestPaints("#58c1cd", paints, { limit: 8 });
check("input list left untouched", JSON.stringify(paints) === before);

// ---- 6. Against the real catalogue in app.js ----
const appSource = fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8");
const catalogue = [...appSource.matchAll(/"([^"|\n]{2,60})\|(#[0-9a-fA-F]{6})(?:\|[^"]*)?"/g)].map((m, i) => Object.assign(P(m[1], m[2].toLowerCase()), { brand: "B" + i }));  // a unique brand each, as several brands share names like "Purple"
check("found the built-in catalogue (1000+ paints)", catalogue.length > 1000, catalogue.length);
check("every catalogue colour reads cleanly", catalogue.every((p) => C.hexToHsl(p.colour) !== null && C.harmonies(p.colour) !== null));
let selfMiss = 0, worstSelf = 0;
for (let i = 0; i < catalogue.length; i += 7) {
  const p = catalogue[i];
  const hit = C.nearestPaints(p.colour, catalogue, { limit: 1, ownedFirst: false })[0];
  if (!hit || hit.distance > 0.0001) { selfMiss++; worstSelf = Math.max(worstSelf, hit ? hit.distance : 999); }
}
check("every sampled catalogue colour finds itself at distance 0 (or an identical twin)", selfMiss === 0, { selfMiss, worstSelf });
const half = catalogue.filter((_, i) => i % 2 === 0).map((p) => Object.assign({}, p, { status: "owned" }));
const rest = catalogue.filter((_, i) => i % 2 === 1);
const mixed = half.concat(rest);
const t0 = Date.now();
for (let i = 0; i < 20; i++) C.nearestPaints(rest[i * 11].colour, mixed, { limit: 3 });
const perCall = (Date.now() - t0) / 20;
check("one nearest-paint search over the whole catalogue takes under 30 ms", perCall < 30, perCall);
// Every palette-wide harmony gets an answer from the catalogue and an honest quality label
let noAnswer = 0;
for (let i = 0; i < catalogue.length; i += 53) {
  const h = C.harmonies(catalogue[i].colour);
  for (const target of [h.complementary, ...h.analogous, ...h.split, ...h.triad, ...h.neutrals]) {
    const hit = C.nearestPaints(target, catalogue, { limit: 1, ownedFirst: false })[0];
    if (!hit || !["good", "close", "poor"].includes(hit.quality) || hit.confidence < 0 || hit.confidence > 1) noAnswer++;
  }
}
check("every harmony colour gets a labelled catalogue match", noAnswer === 0, noAnswer);
check("a real blue's opposite lands on a warm paint", (() => {
  const target = C.harmonies("#1f56a7").complementary;     // Altdorf Guard Blue
  const hit = C.nearestPaints(target, catalogue, { limit: 1, ownedFirst: false })[0];
  const fam = C.colourFamily(hit.paint.colour);
  return /orange|yellow|brown/.test(fam);
})());

// ---- 6b. "Does this scheme hang together?" (Coach 3: schemeCheck) ----
// Expected answers come from colour theory and painters' rules of thumb, worked out by hand:
// more than 3 strong colours is too many, lightest and darkest less than 30 apart is flat, and the focus is the
// strong colour furthest round the wheel from the main one.
const scheme = (list) => C.schemeCheck(list.map(([colour, uses]) => ({ colour, uses })));
const notEnough = [[], [["#0d407f", 1]], [["#0d407f", 1], ["#0D407F", 2]], [[null, 1], ["nope", 2], ["#808080", 1]], [["#808080", 1], ["#0d407f", 1]]];
for (const list of notEnough) {
  const r = scheme(list);
  check("fewer than two different colours: not enough to check " + JSON.stringify(list), r.enough === false && r.hangsTogether === false && r.flat === false, r);
}
for (const bad of [undefined, null, 42, "x", {}, [null], [{}], [{ colour: 5 }]]) {
  let r = null, threw = false;
  try { r = C.schemeCheck(bad); } catch (e) { threw = true; }
  check("schemeCheck never throws on " + JSON.stringify(bad), !threw && r && r.enough === false && Array.isArray(r.strong), r);
}
// Which colours count as strong
const strongYes = ["#0d407f", "#f4741c", "#228b22", "#7b2d8b", "#c1272d", "#fbb81c", "#6a0001"];
const strongNo = ["#7a7a7a", "#8b4513", "#0b0b0b", "#f5f5f5", "#001a33", "#9e915c", "#a7a28f", "#462f30", "#fdf2c4"];
for (const hex of strongYes) check("strong colour: " + hex, C.isStrongColour(hex) === true);
for (const hex of strongNo) check("not a strong colour (grey, brown, near-black or white, too dark, muted, too pale): " + hex, C.isStrongColour(hex) === false);
check("isStrongColour rejects non-colours", [null, "", "#12", 7].every((v) => C.isStrongColour(v) === false));
// A base, shade and highlight of one blue plus a black undercoat: one strong colour, plenty of light and dark, already focused
let r = scheme([["#0d407f", 3], ["#1f56a7", 2], ["#4c8bd1", 1], ["#0b0b0b", 1]]);
check("one blue with shades and black: 1 strong colour", r.enough && r.strong.length === 1 && r.strong[0].family.includes("blue"), r.strong);
check("...has light and dark (not flat), not too many, and hangs together", !r.flat && !r.tooManyStrong && r.hangsTogether === true, r);
check("...the blue is its own focus colour (only strong colour)", r.focusKind === "only" && r.focus.hex === r.strong[0].hex, r);
check("...its lightness range is big: black to light blue", r.lightRange > 45 && r.darkest.hex === "#0b0b0b", r);
// Blue armour with orange eyes: orange is the focus (opposite of the main blue)
r = scheme([["#0d407f", 3], ["#4c8bd1", 1], ["#f4741c", 1], ["#0b0b0b", 1]]);
check("blue and orange: 2 strong colours, blue is the main one", r.strong.length === 2 && r.dominant.family.includes("blue"), r);
check("...the orange is the suggested focus colour (an accent)", r.focusKind === "accent" && r.focus.family === "orange", r.focus);
// The focus is the strong colour furthest round the wheel from the main colour
r = scheme([["#0d407f", 3], ["#228b22", 1], ["#f4741c", 1], ["#0b0b0b", 1]]);
check("blue with green and orange: the focus is the orange, not the green (it is opposite the blue)", r.focus.family === "orange", r.focus);
// The most-used strong colour is the main one
r = scheme([["#f4741c", 1], ["#0d407f", 4], ["#0b0b0b", 1]]);
check("the colour used in most steps is the main colour", r.dominant.family.includes("blue") && r.focus.family === "orange", r);
// On a tie the colour listed first is the main one (a recipe usually starts with its main colour), whichever is more vivid
r = scheme([["#0d407f", 1], ["#f4741c", 1]]);
check("tie: blue listed first is the main colour, orange is the focus", r.dominant.family.includes("blue") && r.focus.family === "orange", r);
r = scheme([["#f4741c", 1], ["#0d407f", 1]]);
check("tie: orange listed first is the main colour, blue is the focus", r.dominant.family === "orange" && r.focus.family.includes("blue"), r);
// Hues close together are one colour; red and orange are different colours
r = scheme([["#6a0001", 2], ["#9a1115", 2], ["#d03a2e", 1], ["#0b0b0b", 1]]);
check("three reds (shade, base, highlight) count as ONE strong colour", r.strong.length === 1 && r.strong[0].uses === 5, r.strong);
r = scheme([["#c1272d", 2], ["#f4741c", 2], ["#0b0b0b", 1]]);
check("red and orange count as two strong colours", r.strong.length === 2, r.strong);
// Too many strong colours
r = scheme([["#0d407f", 3], ["#f4741c", 2], ["#228b22", 2], ["#7b2d8b", 1], ["#c1272d", 1], ["#0b0b0b", 1]]);
check("five strong colours is too many", r.strong.length === 5 && r.tooManyStrong === true && r.hangsTogether === false, r);
check("...but there is still a focus colour to suggest", r.focus !== null && r.focusKind === "accent", r);
r = scheme([["#0d407f", 3], ["#f4741c", 2], ["#228b22", 2], ["#0b0b0b", 1]]);
check("exactly three strong colours is fine", r.strong.length === 3 && r.tooManyStrong === false && r.hangsTogether === true, r);
r = scheme([["#0d407f", 3], ["#f4741c", 2], ["#228b22", 2], ["#7b2d8b", 1], ["#0b0b0b", 1]]);
check("four strong colours is too many", r.strong.length === 4 && r.tooManyStrong === true, r);
// Light and dark
r = scheme([["#3b6fb0", 2], ["#6b8fc2", 1], ["#5a7fb5", 1]]);
check("three mid blues of nearly the same lightness are flat", r.flat === true && r.lightRange < 30 && r.hangsTogether === false, r);
r = scheme([["#3b6fb0", 2], ["#f5f5f5", 1]]);
check("a mid blue with white has plenty of light and dark", r.flat === false && r.lightRange > 30, r);
r = scheme([["#7a7a7a", 1], ["#0b0b0b", 1]]);
check("neutrals count for light and dark: grey and black are not flat", r.enough && r.flat === false && r.strong.length === 0, r);
check("no strong colours: no focus colour to suggest", r.focus === null && r.focusKind === "none", r);
r = scheme([["#462f30", 2], ["#9e915c", 1], ["#a7a28f", 1], ["#0b0b0b", 1]]);
check("muted earth tones with black: calm, nothing strong, still hangs together", r.strong.length === 0 && r.hangsTogether === true, r);
// Case and uses don't matter for identity; bad uses count as 1
r = scheme([["#0D407F", 1], ["#0d407f", 1], ["#f4741c", "many"], ["#0b0b0b", -3]]);
check("capital letters are the same colour, and a bad uses number counts as one use", r.colourCount === 3 && r.strong.find((s) => s.family === "orange").uses === 1, r);

// ---- 7. It stays offline and invisible ----
const src = fs.readFileSync(path.join(__dirname, "..", "colour.js"), "utf8");
const forbidden = ["fetch(", "XMLHttpRequest", "WebSocket", "sendBeacon", "localStorage", "sessionStorage", "document.", "innerHTML", "eval(", "new Function", "importScripts", "http://", "https://"];
for (const word of forbidden) check("colour.js does not use " + word, !src.includes(word), word);
check("colour.js adds exactly one name to the page", /root\.MinifolioColour = api;/.test(src) && (src.match(/root\.[A-Za-z]+ =/g) || []).length === 1);

console.log(`colour engine: ${passed} checks passed, ${failures.length} failed`);
if (failures.length) { for (const f of failures) console.log("FAIL: " + f); process.exit(1); }
