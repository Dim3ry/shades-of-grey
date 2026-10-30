// The checks for mentor-engine.js (X6a). Run by tests/test_v101_mentor_engine.py, or on its own:  node tests/mentor_engine_check.js
// Prints one JSON list of { name, ok, detail }. The index is built by the app's own loader, cut out of app.js and run here.
const fs = require("fs"), path = require("path"), vm = require("vm");
const ROOT = path.join(__dirname, "..");
const read = (f) => fs.readFileSync(path.join(ROOT, f), "utf8");
const out = [];
const check = (name, ok, detail) => out.push({ name, ok: !!ok, detail: ok ? "" : JSON.stringify(detail) });

const sandbox = { console, Math, JSON };
sandbox.globalThis = sandbox; sandbox.window = sandbox;
vm.createContext(sandbox);
for (const f of ["colour.js", "detail-recipes.js", "basing-tips.js", "mentor-engine.js"]) vm.runInContext(read(f) + (f.endsWith("-tips.js") || f === "detail-recipes.js" ? "" : ""), sandbox, { filename: f });
// const lists are not on the global object in a vm, so read them back by name
const lists = vm.runInContext("({ DETAIL_RECIPES, BASING_TIPS })", sandbox);
const app = read("app.js");
const a = app.indexOf("function makeKnowledgeIndex"), b = app.indexOf("let knowledgeCache");
vm.runInContext(app.slice(a, b), sandbox);
const makeIndex = sandbox.makeKnowledgeIndex;
const M = sandbox.MinifolioMentor, C = sandbox.MinifolioColour;
const fx = JSON.parse(read("tests/mentor_engine_fixture.json"));
const parts = [{ key: "armour", name: "Armour" }, { key: "eyes", name: "Eyes" }, { key: "weapon", name: "Weapon" }, { key: "base", name: "Base" }];
const index = makeIndex({ guides: fx.guides, recipes: lists.DETAIL_RECIPES, basing: lists.BASING_TIPS, tips: fx.tips, parts, starters: fx.starters });

// a small paint box: some owned, some not
const P = (name, colour, status) => ({ brand: "Test", name, colour, status });
const catalogue = [
  P("Deep Blue", "#1f3a66"), P("Sky Blue", "#6f93c9"), P("Orange Glow", "#e07a1f"), P("Pale Yellow", "#e8dc8a"), P("Bright Red", "#c8321e"),
  P("Leaf Green", "#3c8a3c"), P("Dark Grey", "#3a3d42"), P("Mid Grey", "#7b7f85"), P("Light Grey", "#c4c7cc"), P("Sand", "#cdbd94"),
  P("Dark Brown", "#4a3320"), P("Violet", "#6a3a9a"), P("Bone", "#d8cfa8"), P("Teal", "#1f8a8a"), P("Black", "#14141a"), P("White", "#f2f2f0"),
];
const paints = catalogue.map((p) => Object.assign({}, p));
const ctx = (extra) => Object.assign({ index, paints, tips: fx.tips, colour: C }, extra || {});

// ---- 1. the table of questions ----
const rows = fx.questions.map(([q, want, kind]) => {
  const r = M.mentorAnswer(q, ctx());
  const first = r.sources[0];
  const ok = r.kind === kind && (want === "colour" ? first && first.type === "colour-lab" : want === "none" ? r.sources.length === 0 && r.suggestions.length > 0 : first && first.key === want);
  return { q, want, kind, got: r.kind, first: first ? first.key : null, ok };
});
const groups = [
  ["guide phrases", 0, 13], ["plurals and endings", 13, 19], ["typos and wrong names", 19, 26], ["filler and capitals", 26, 28],
  ["starter questions", 28, 31], ["detail recipes and basing tips", 31, 38], ["colour questions", 38, 45], ["no answer", 45, 50],
];
check("the table has at least 40 questions", rows.length >= 40, rows.length);
for (const [name, from, to] of groups) {
  const bad = rows.slice(from, to).filter((r) => !r.ok);
  check(`questions: ${name} (${to - from})`, bad.length === 0, bad);
}
const answered = rows.filter((r) => r.kind === "answer" && r.ok).length;
check("every question that should answer, answers with its expected first source", answered === rows.filter((r) => r.kind === "answer").length, answered);

// ---- 2. shape and sources ----
const all = fx.questions.map(([q]) => M.mentorAnswer(q, ctx()));
check("at most 3 sources, each with type, key and label", all.every((r) => r.sources.length <= 3 && r.sources.every((s) => s.type && s.key && s.label)), all.filter((r) => r.sources.length > 3));
check("source types are only the allowed ones", all.every((r) => r.sources.every((s) => ["guide", "colour-lab", "recipe", "basing", "tip"].includes(s.type))), 1);
check("a recipe answer names the kind of source", M.mentorAnswer("how do I paint rust", ctx()).sources[0].type === "recipe" && M.mentorAnswer("snow", ctx()).sources[0].type === "basing", 1);
check("the none answer gives up to 3 suggestions, each with text and key", all.filter((r) => r.kind === "none").every((r) => r.suggestions.length >= 1 && r.suggestions.length <= 3 && r.suggestions.every((s) => s.text && s.key)), 1);
check("a one-word weak match is not enough (the threshold)", M.mentorAnswer("recesses deep", ctx()).kind === "answer" && M.mentorAnswer("how tall is a tree", ctx()).kind === "none", 1);

// ---- 3. the colour path ----
const blue = M.mentorAnswer("what colour armour goes with blue", ctx());
check("colour + part: picks, a Colour Lab source first, then the matching tip", blue.picks.length === 3 && blue.sources[0].type === "colour-lab" && blue.sources[0].colour && blue.sources[1].type === "tip" && blue.sources[1].key === "tip-blue-armour", blue);
check("each pick has a wanted colour, a paint, a fit and whether it is owned", blue.picks.every((p) => /^#[0-9a-f]{6}$/.test(p.wanted) && p.paint.name && p.fit && typeof p.owned === "boolean"), blue.picks);
const eyes = M.mentorAnswer("red eyes on blue armour", ctx());
check("two parts: the part that belongs to a colour is the base, the other is asked about", eyes.picks.every((p) => p.part === "eyes") && /eyes with blue/.test(eyes.lead), eyes.lead);
check("base coat is a technique, not the base of the model", M.mentorAnswer("what is a base coat for blue", ctx()).picks === undefined, 1);
check("a colour on its own: what goes with it, from the colour rules", /^Blue stands out most against \w+/.test(M.mentorAnswer("what goes with blue", ctx()).lead) && M.mentorAnswer("green", ctx()).sources[0].key === "wheel:green", M.mentorAnswer("green", ctx()));
check("a neutral colour on its own says so", /neutral/.test(M.mentorAnswer("grey", ctx()).lead), M.mentorAnswer("grey", ctx()).lead);
check("a strong entry beats a lone colour word", M.mentorAnswer("blue glaze", ctx()).sources[0].key === "glazing", M.mentorAnswer("blue glaze", ctx()));
// owned first
const plainPick = blue.picks[0].paint;
const shifted = Object.assign({}, paints.find((p) => p.name === plainPick.name), { name: "Own Copy", colour: C.hslToHex(C.hexToHsl(plainPick.colour).h + 4, C.hexToHsl(plainPick.colour).s, C.hexToHsl(plainPick.colour).l), status: "owned" });
const ownedCtx = ctx({ paints: paints.concat([shifted]) });
const ownedRun = M.mentorAnswer("what colour armour goes with blue", ownedCtx);
check("owned paints come first: a near-fit paint you own beats a slightly closer paint you do not", ownedRun.picks[0].paint.name === "Own Copy" && ownedRun.picks[0].owned && / Paints you own come first\.$/.test(ownedRun.lead), ownedRun.picks[0]);
check("with nothing owned, the lead does not claim owned paints", !/own come first/.test(blue.lead), blue.lead);
// a poor fit with a better blend
const tiny = [P("Blue A", "#0d407f", "owned"), P("Yellow A", "#fbb81c", "owned"), P("White A", "#f2f2f0", "owned"), P("Black A", "#14141a", "owned")];
const blendPicks = M.mentorAnswer("red eyes", ctx({ paints: tiny })).picks;
check("a poor fit can come with a blend of owned paints", blendPicks.some((p) => p.blend && p.blend.ratio && p.blend.a.name && p.blend.b.name), blendPicks);
check("the Picker's own code can be handed in (ideas hook)", (() => {
  const r = M.mentorAnswer("red eyes on blue armour", ctx({ ideas: () => [{ wanted: "#ff0000", relation: "complementary", hit: { paint: paints[4], quality: "good", owned: false, distance: 1 } }] }));
  return r.picks.length === 1 && r.picks[0].paint.name === "Bright Red";
})(), 1);

// ---- 4. repeatable ----
const again = fx.questions.map(([q]) => M.mentorAnswer(q, ctx()));
check("the same question gives the same answer", JSON.stringify(all) === JSON.stringify(again), 1);
const reversedPaints = ctx({ paints: paints.slice().reverse() });
check("paint order does not change the picks", JSON.stringify(M.mentorAnswer("blue armour", ctx()).picks) === JSON.stringify(M.mentorAnswer("blue armour", reversedPaints).picks), 1);
// a tie goes to the entry that comes first in the index
const twin = (key) => ({ key, kind: "guide", category: "techniques", title: "Twin entry", summary: "A twin entry about stipple.", body: [], related: [], keywords: ["stipple"], credit: null });
const tied = M.mentorAnswer("stipple", { index: { entries: [twin("b-twin"), twin("a-twin")] }, paints: [], colour: C });
check("a tie goes to the entry that comes first in the index", tied.sources.map((s) => s.key).join() === "b-twin,a-twin", tied.sources);

// ---- 5. text: built only from entries and templates ----
const entryText = new Set(index.entries.flatMap((e) => [e.title, e.summary, ...(e.body || []), `${e.title}: ${e.summary}`]));
const answers = all.filter((r) => r.kind === "answer");
const fromEntries = answers.every((r) => r.lead.split(/(?<=\.)\s/).every((s) => [...entryText].some((t) => t.includes(s.replace(/\.$/, ""))) || /^Also see /.test(s)));
check("an answer's lead is an entry's own words or the 'Also see' template", fromEntries, answers.filter((r) => !r.lead).length);
const BAD = /—|–|great question|sorry|unfortunately|as an ai|\bgames workshop\b|\bcitadel\b|\bvallejo\b|\bchaos\b|\bimperial\b|\blegion\b|\bcrusade\b|\bthe mentor\b|<|>/i;
const templates = [...all.map((r) => r.lead), ...fx.questions.map(([q]) => M.mentorAnswer(q, ownedCtx).lead)];
check("no filler, em dashes, brand or faction words in anything it says", templates.every((t) => !BAD.test(t)), templates.filter((t) => BAD.test(t)));
check("every lead is one or two short sentences", templates.every((t) => (t.match(/[.!?](\s|$)/g) || []).length <= 2 && t.length <= 260 && t.length > 0), templates.filter((t) => t.length > 260));
const src = read("mentor-engine.js");
check("the engine never touches storage, the network or the page", !/\b(localStorage|sessionStorage|indexedDB|fetch\s*\(|XMLHttpRequest|WebSocket|sendBeacon|document\.|navigator\.|eval\s*\(|new Function)/.test(src), 1);
check("the engine file has no brand or faction words", !/games workshop|citadel|vallejo|army painter|\bchaos\b|\bimperial\b|\blegion\b|\bcrusade\b|space marine|\bork\b|\beldar\b|\btyranid/i.test(src), 1);

// ---- 6. speed: 500 entries, a slow processor is about 6 times slower than this one ----
const big = [];
const wordsA = ["warm", "cool", "stone", "leaf", "ember", "frost", "dust", "coal", "river", "amber", "slate", "mist", "bark", "clay", "iron", "salt", "moss", "ash", "pine", "reed"];
for (let i = 0; i < 500; i++) {
  const w = (n) => wordsA[(i * 7 + n * 3) % wordsA.length], v = (n) => wordsA[(i * 11 + n) % wordsA.length];
  big.push({ key: "e" + i, kind: "guide", category: "techniques", title: `${w(0)} ${v(1)} ${w(2)}`, summary: `How to work ${w(1)} and ${v(2)} areas on a ${w(3)} surface.`,
    body: [`Step one for ${w(0)}.`, `Step two for ${v(0)} and ${v(1)}.`, `Step three for ${w(2)}.`], related: [], keywords: [`${w(0)} ${v(1)}`, `${w(1)} ${v(2)}`, w(2), `${v(0)} finish`, `${w(3)} look`, `${v(3)} tone`], credit: null });
}
const bigCtx = { index: { entries: big }, paints: [], colour: C };
M.mentorAnswer("warm stone", bigCtx);   // the first call reads the entries once
const qs = ["how do I do a warm stone look", "ember frost finish", "what is a slate surface", "asdf qwerty", "moss and ash tone", "river clay"];
const times = [];
for (let n = 0; n < 60; n++) { const t = process.hrtime.bigint(); M.mentorAnswer(qs[n % qs.length], bigCtx); times.push(Number(process.hrtime.bigint() - t) / 1e6); }
times.sort((x, y) => x - y);
const worst = times[times.length - 1], median = times[Math.floor(times.length / 2)];
const t0 = process.hrtime.bigint(); const fresh = { index: { entries: big.map((e) => Object.assign({}, e)) }, paints: [], colour: C }; M.mentorAnswer("warm stone", fresh); const firstCall = Number(process.hrtime.bigint() - t0) / 1e6;
// the colour path with a full catalogue of about 4000 paints
const catBig = []; for (let i = 0; i < 4000; i++) catBig.push({ brand: "T", name: "P" + i, colour: "#" + ((i * 2654435 + 1234567) % 0xffffff).toString(16).padStart(6, "0"), status: i % 40 === 0 ? "owned" : "" });
const c0 = process.hrtime.bigint(); M.mentorAnswer("red eyes on blue armour", { index, paints: catBig, tips: fx.tips, colour: C }); const colourMs = Number(process.hrtime.bigint() - c0) / 1e6;
console.error(JSON.stringify({ median_ms: +median.toFixed(3), worst_ms: +worst.toFixed(3), first_call_ms: +firstCall.toFixed(2), colour_path_4000_paints_ms: +colourMs.toFixed(2) }));
check("a question against 500 entries is quick (median of 60 under 5 ms here; the 30 ms slow-processor number is measured by hand)", median < 5, { median, worst });
check("the colour path with a 4000-paint catalogue is quick too (under 60 ms here)", colourMs < 60, colourMs);
console.log(JSON.stringify({ out, rows, speed: { median, worst, firstCall, colourMs } }));
