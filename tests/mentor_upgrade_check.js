// The checks for the X8b additions to mentor-engine.js (extra keywords, synonyms, rare words, phrase bank, quick lead) and their data
// file, mentor-data.js. Run by tests/test_v105_mentor_words.py, or on its own:  node tests/mentor_upgrade_check.js
// Prints one JSON list of { name, ok, detail }. Most checks use a few small made-up entries and a made-up MENTOR_DATA, handed in as
// context.data, so they test the engine and not the content. The rest load the real mentor-data.js.
// X8b: moved here from knowledge-base/upgrade/. It reads the fixture from tests/.
const fs = require("fs"), path = require("path"), vm = require("vm");
const ROOT = process.env.MINIFOLIO_ROOT || (fs.existsSync(path.join(__dirname, "..", "app.js")) ? path.join(__dirname, "..") : path.join(__dirname, "..", ".."));   // in tests/ the repo is one up; in knowledge-base/upgrade/ it is two up
const read = (f) => fs.readFileSync(path.join(ROOT, f), "utf8");
const out = [];
const check = (name, ok, detail) => out.push({ name, ok: !!ok, detail: ok ? "" : JSON.stringify(detail) });

const sandbox = { console, Math, JSON };
sandbox.globalThis = sandbox; sandbox.window = sandbox;
vm.createContext(sandbox);
for (const f of ["colour.js", "detail-recipes.js", "basing-tips.js", "mentor-data.js", "mentor-engine.js"]) vm.runInContext(read(f), sandbox, { filename: f });
const lists = vm.runInContext("({ DETAIL_RECIPES, BASING_TIPS, MENTOR_DATA })", sandbox);
const D = lists.MENTOR_DATA;
const app = read("app.js");
vm.runInContext(app.slice(app.indexOf("function makeKnowledgeIndex"), app.indexOf("let knowledgeCache")), sandbox);
const M = sandbox.MinifolioMentor, C = sandbox.MinifolioColour;
const fx = JSON.parse(read("tests/mentor_engine_fixture.json"));
const parts = [{ key: "armour", name: "Armour" }, { key: "eyes", name: "Eyes" }, { key: "weapon", name: "Weapon" }, { key: "base", name: "Base" }];
const index = sandbox.makeKnowledgeIndex({ guides: fx.guides, recipes: lists.DETAIL_RECIPES, basing: lists.BASING_TIPS, tips: fx.tips, parts, starters: fx.starters });
const ctx = (extra) => Object.assign({ index, paints: [], tips: fx.tips, colour: C }, extra || {});
const ask = (q, extra) => M.mentorAnswer(q, ctx(extra));

// small made-up entries, for checks that are about the engine, not the content
const G = (key, title, summary, keywords, body) => ({ key, kind: "guide", category: "techniques", title, summary, body: body || [], related: [], keywords: keywords || [], credit: null });
const mini = (entries, data, q) => M.mentorAnswer(q, { index: { entries }, paints: [], colour: C, data });

// ---- 1. the data file ----
const isList = (v) => Array.isArray(v), isMap = (v) => v && typeof v === "object" && !Array.isArray(v);
check("mentor-data.js defines MENTOR_DATA with keywords, synonyms, phrases, quick and starters",
  isMap(D) && isMap(D.keywords) && isList(D.synonyms) && isMap(D.phrases) && isMap(D.quick) && isMap(D.starters), Object.keys(D || {}));
const BAD = /—|–|great question|sorry|unfortunately|as an ai|\bgames workshop\b|\bcitadel\b|\bvallejo\b|\bchaos\b|\bimperial\b|\blegion\b|\bcrusade\b|\bthe mentor\b|<|>/i;
const answers = [...Object.values(D.quick).flat(), ...Object.values(D.starters)].filter(Boolean);
check("every quick answer is one or two short sentences with no filler, dashes, brand or faction words",
  answers.every((a) => !BAD.test(a) && a.length <= 260 && (a.match(/[.!?](\s|$)/g) || []).length <= 2 && !/^See:/.test(a)), answers.filter((a) => BAD.test(a) || a.length > 260).slice(0, 3));
check("each entry's quick answers line up with its phrases (never more answers than phrases)",
  Object.entries(D.quick).every(([k, qs]) => isList(D.phrases[k]) && qs.length <= D.phrases[k].length), Object.keys(D.quick).filter((k) => !D.phrases[k]).slice(0, 3));
const variants = D.synonyms.flatMap((g) => g.slice(1));
check("every synonym group has a canonical and at least one variant, and a variant is in one group only",
  D.synonyms.every((g) => isList(g) && g.length >= 2 && g.every((x) => typeof x === "string" && x)) && new Set(variants).size === variants.length, variants.length);
const dataSrc = read("mentor-data.js");
check("the data file is plain data: no code, storage, network or angle brackets",
  !/\bfunction\b|=>|\b(localStorage|sessionStorage|indexedDB|fetch|XMLHttpRequest|WebSocket|document|navigator|eval)\b|<|>/.test(dataSrc.replace(/^\/\/.*$/gm, "")), 1);
check("the data file stays under 1 MB", dataSrc.length < 1e6, dataSrc.length);

// ---- 2. (a) extra keywords: recipes and basing tips found by words that are not in their name or summary ----
const fangs = ask("how do I paint fangs"), magma = ask("magma"), patina = ask("statue patina");
check("a recipe is found by one of its extra keywords (fangs -> Teeth)", fangs.kind === "answer" && (fangs.sources[0] || {}).key === "teeth" && (fangs.sources[0] || {}).type === "recipe", fangs.sources);
check("a basing tip is found by one of its extra keywords (magma -> Lava)", magma.kind === "answer" && (magma.sources[0] || {}).key === "lava" && (magma.sources[0] || {}).type === "basing", magma.sources);
check("a two-word extra keyword works too (statue patina -> Verdigris)", patina.kind === "answer" && (patina.sources[0] || {}).key === "verdigris", patina.sources);
check("without MENTOR_DATA those words find nothing (data: null turns every extra off)", ask("how do I paint fangs", { data: null }).kind === "none", ask("how do I paint fangs", { data: null }).sources);

// ---- 3. (b) synonyms ----
const putty = [G("putty", "Two-part putty", "Mix the two parts evenly and sculpt it once it firms up.", ["two-part putty", "sculpting putty"]), G("other", "Edge highlights", "Thin lines of a light colour on raised edges.", ["edge highlight"])];
const synData = { synonyms: [["two-part putty", "green stuff", "green putty"], ["wet palette", "stay wet tray"]] };
const gs = mini(putty, synData, "how do I use green stuff");
check("a variant in the question is read as its canonical (green stuff -> two-part putty)", gs.kind === "answer" && (gs.sources[0] || {}).key === "putty", gs);
check("so a variant with a colour word in it is not taken for a colour question", gs.kind !== "colour" && mini(putty, { synonyms: [] }, "how do I use green stuff").kind === "colour", gs.kind);
const pal = [G("wp", "Keeping paint wet", "A stay wet tray keeps paint workable for hours.", []), G("x", "Varnish", "Seal the model when it is done.", [])];
check("a variant in an entry is found by the canonical in a question", mini(pal, synData, "wet palette").sources.some((s) => s.key === "wp") && mini(pal, { synonyms: [] }, "wet palette").kind === "none", mini(pal, synData, "wet palette"));
check("a synonym only swaps whole words", mini(pal, { synonyms: [["glaze", "pal"]] }, "wet palette").kind === mini(pal, { synonyms: [] }, "wet palette").kind, 1);

// ---- 4. (c) rare words count for more ----
// two entries with the same two words in mirrored places (a tie before X8b, which the first in the index won); "layer" is in 12 entries
const many = [G("layerA", "Layer basics", "How to layer verdigris.", ["layer"]), G("vg", "Verdigris streaks", "Green streaks to layer under bronze.", ["verdigris"])];
for (let i = 0; i < 10; i++) many.push(G("layer" + i, "Layer step " + "abcdefghij"[i], "Layer it up over the base coat.", []));
const rare = mini(many, {}, "layer verdigris");
check("a rare word outweighs a common one (verdigris beats layer, though each entry has both)", rare.kind === "answer" && (rare.sources[0] || {}).key === "vg", rare.sources);
check("a lone title word shared by most entries no longer passes the threshold on its own (step is in 10 of 12 titles)", mini(many, {}, "step").kind === "none" && mini(many, {}, "verdigris").kind === "answer", [mini(many, {}, "step").kind, mini(many, {}, "verdigris").kind]);

// ---- 5. (d) the phrase bank and (e) the quick lead ----
const rings = [G("tide", "Wash tide marks", "Fix the pale edges a wash can leave when it dries.", ["tide marks"]), G("prime", "Priming", "A thin even primer coat.", ["primer"]), G("glaze", "Glazing", "Thin translucent layers to shift a colour.", ["glaze"])];
const bank = { phrases: { tide: ["my wash dried in rings", "wash left blotches", "shade pooled and dried with edges"] }, quick: { tide: ["Rewet the rings with clean water or a thin coat of the same wash and draw the excess off with a damp brush.", ""] } };
const r1 = mini(rings, bank, "my wash dried in rings");
const r1plain = mini(rings, {}, "my wash dried in rings");
check("the phrase bank finds an entry its own words do not", r1.kind === "answer" && (r1.sources[0] || {}).key === "tide" && r1plain.kind === "none", [r1.sources, r1plain.kind]);
check("a strong phrase match leads with that phrase's quick answer", r1.lead === bank.quick.tide[0], r1.lead);
const r2 = mini(rings, bank, "wash left blotches");
check("a phrase with no quick answer keeps the entry's own lead", (r2.sources[0] || {}).key === "tide" && r2.lead === "Fix the pale edges a wash can leave when it dries.", r2.lead);
const r3 = mini(rings, bank, "wash tide marks and rings");   // shares 2 of 3 words with a phrase: a match of about 0.58
check("a loose phrase match keeps the entry's own lead", (r3.sources[0] || {}).key === "tide" && r3.lead.indexOf("Rewet") === -1, r3);
const two = { phrases: bank.phrases, quick: { tide: ["Rewet it. Then draw the excess off."] } };
const glazeToo = [...rings, G("tide2", "Tide marks on glazes", "Glazes can leave marks too.", ["tide marks"])];
const r4 = mini(glazeToo, two, "my wash dried in rings tide marks");
check("'Also see' is added to a quick lead only if the lead stays within two sentences", (r4.lead.match(/[.!?](\s|$)/g) || []).length <= 2, r4.lead);
const st = fx.starters[0];
const startData = { starters: { [st.key]: "Start with one model and three colours." } };
const r5 = M.mentorAnswer(st.text, { index, paints: [], colour: C, data: startData });
check("a starter question can lead with its own quick answer", r5.kind === "answer" && r5.lead === "Start with one model and three colours.", r5);
// built with --no-quick, quick and starters are empty: every lead must then be made as before X8b (the entry's own words, plus "Also see")
const noQuick = Object.assign({}, D, { quick: {}, starters: {} });
const sentence = (x) => { x = String(x || "").trim(); return x && !/[.!?]$/.test(x) ? x + "." : x; };
const ownLead = (e) => e.kind === "tip" ? sentence((String((e.body || [])[0] || "").match(/^.*?[.!?](\s|$)/) || [String((e.body || [])[0] || "")])[0].trim() || e.title)
  : e.kind === "detail" || e.kind === "basing" ? sentence(`${e.title}: ${e.summary}`.replace(/: $/, "")) : sentence(e.summary || e.title);
const KIND = { guide: "guide", recipe: "detail", basing: "basing", tip: "tip" };
const sameWords = (a, b) => { const x = new Set(M.tokens(a)), y = new Set(M.tokens(b)); return x.size === y.size && [...x].every((w) => y.has(w)); };
const nqBad = [...fx.questions.map(([q]) => q), ...fx.starters.map((x) => x.text)].map((q) => {
  const r = ask(q, { data: noQuick }), isStarter = fx.starters.some((x) => sameWords(x.text, q));   // a starter's lead has no "Also see"
  if (r.kind !== "answer") return null;
  const es = r.sources.map((x) => index.entries.find((e) => e.key === x.key && e.kind === KIND[x.type]));
  const want = ownLead(es[0]) + (!isStarter && es.length > 1 ? ` Also see ${es[1].title}.` : "");
  return r.lead === want ? null : { q, lead: r.lead, want };
}).filter(Boolean);
check("with quick and starters empty (built with --no-quick), every lead is the entry's own words, as before", nqBad.length === 0, nqBad.slice(0, 3));
check("context.data wins over the page's MENTOR_DATA", ask("how do I paint fangs", { data: {} }).kind === "none" && ask("how do I paint fangs").kind === "answer", 1);

// ---- 6. (f) the none answer ----
const off = ["what time is it in tokyo", "what is quantum computing", "recommend a good film for tonight", "how do I write a cover letter"];
const offRuns = off.map((q) => ask(q));
check("questions about other things still get the none answer, with MENTOR_DATA on the page", offRuns.every((r) => r.kind === "none" && r.suggestions.length), offRuns.map((r, i) => [off[i], r.kind]));
// X8b: the unknown-word rule is at full strength only once the entries hold about 3,000 different words (UNSEEN_VOCAB), so these
// checks add one entry whose body holds 3,000 made-up words; with the three small entries alone the rule is almost off.
const wide = [...rings, G("wide", "Word list", "", [], [Array.from({ length: 3000 }, (_, i) => "zz" + i.toString(36)).join(" ")])];
const glazeQ = mini(wide, {}, "glaze"), glazeOdd = mini(wide, {}, "glaze qwxz plughy");
check("words found nowhere make an answer less sure (the same match with two unknown words scores lower)", glazeQ.kind === "answer" && glazeOdd.kind === "none", [glazeQ.kind, glazeOdd.kind]);
const smallOdd = mini(rings, {}, "glaze qwxz plughy");
check("in an index with few different words, unknown words count for little (it misses everyday words too)", smallOdd.kind === "answer" && (smallOdd.sources[0] || {}).key === "glaze", smallOdd);

// ---- 7. the same shape, the same answer ----
const shapes = fx.questions.map(([q]) => ask(q));
const allowed = new Set(["kind", "lead", "sources", "picks", "suggestions"]);
check("the answer has the same shape as before (no new fields)", shapes.every((r) => Object.keys(r).every((k) => allowed.has(k))), shapes.map((r) => Object.keys(r)).find((k) => k.some((x) => !allowed.has(x))));
check("the same question gives the same answer with MENTOR_DATA", JSON.stringify(shapes) === JSON.stringify(fx.questions.map(([q]) => ask(q))), 1);
// Two rows answer differently once MENTOR_DATA is on the page, on purpose and in the open:
//  - "muddy ground": both mud (George's original tip) and dry-mud-ground (X8's) are right. Without the data his check finds
//    dry-mud-ground first (the fixture says so since X8); with the data's phrases it finds mud.
//  - "how tall is a tree": the data's phrase bank knows "tree" from the scenery guides, so it answers trees-from-twigs instead of none.
//    That is a near-miss answer to an off-topic question, the kind the pack's report counts (17 of 40 off-topic questions answer).
const WITH_DATA = { "muddy ground": ["answer", ["mud", "dry-mud-ground"]], "how tall is a tree": ["answer", ["trees-from-twigs"]] };
const table = fx.questions.filter(([, , kind]) => kind !== "colour").map(([q, want, kind]) => {
  const r = ask(q); const first = r.sources[0];
  const alt = WITH_DATA[q];
  const ok = alt ? r.kind === alt[0] && first && alt[1].includes(first.key)
                 : r.kind === kind && (want === "none" ? r.sources.length === 0 : first && first.key === want);
  return { q, ok, got: first ? first.key : r.kind };
});
check("with MENTOR_DATA on the page, the X6a question table still leads to the same first sources (two rows named above differ on purpose)", table.every((r) => r.ok), table.filter((r) => !r.ok));

// ---- 8. speed with the full phrase bank: one stub entry per MENTOR_DATA key (about 800), all their phrases ----
const stubs = Object.keys(D.phrases).map((k) => G(k, k.replace(/-/g, " "), "", D.keywords[k] || []));
const sctx = { index: { entries: stubs }, paints: [], colour: C };
const t0 = process.hrtime.bigint(); M.mentorAnswer("how do I thin my paint", sctx); const firstCall = Number(process.hrtime.bigint() - t0) / 1e6;
const qs = ["how do I thin my paint", "my wash dried in rings", "green stuff gaps", "what is zenithal priming", "asdf qwerty", "how to paint gold armour trim", "snow base", "kolinsky brush worth it"];
const times = [];
for (let n = 0; n < 64; n++) { const t = process.hrtime.bigint(); M.mentorAnswer(qs[n % qs.length], sctx); times.push(Number(process.hrtime.bigint() - t) / 1e6); }
times.sort((x, y) => x - y);
const median = times[times.length >> 1];
console.error(JSON.stringify({ entries: stubs.length, first_call_ms: +firstCall.toFixed(1), median_ms: +median.toFixed(3), worst_ms: +times[times.length - 1].toFixed(2) }));
check("a question against about 800 entries and their phrase bank is quick (median of 64 under 8 ms here)", median < 8, median);
check("reading the entries and the phrase bank the first time is quick too (under 600 ms here)", firstCall < 600, firstCall);
console.log(JSON.stringify({ out, speed: { median, firstCall } }));
