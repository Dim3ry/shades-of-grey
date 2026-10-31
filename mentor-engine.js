// ===== mentor-engine.js: the Mentor answer engine (X6a, no screen) =====
// Turns what a person typed (or a starter question) into an answer made only from our own entries and the colour rules.
// No AI model, no server, no network, nothing stored. It draws nothing. Same input, same output.
//
// How it is shared: loaded as a plain script just before app.js (after guides-data.js and mentor-data.js). It adds ONE name to the page,
// MinifolioMentor.
// The test file loads the very same file in Node. mentorAnswer(text, context) is MinifolioMentor.mentorAnswer.
//
// context:
//   index   the Guides loader index (knowledgeIndex() in app.js): { entries: [ { key, kind, category, title, summary, body, keywords } ] }
//   paints  every paint that may be suggested, the person's own first or flagged (status "owned" or "low"); the colour rules do the rest
//   tips    the Mentor tips (MENTOR_TIPS), for their suggested colours. Optional, falls back to the page's MENTOR_TIPS
//   colour  the colour maths (MinifolioColour). Optional, falls back to the page's
//   ideas   optional: ideas(baseHex, part) returning [ { wanted, relation, hit } ], so the screen can hand over its own Picker code
//   data    optional: the extra words (MENTOR_DATA from mentor-data.js). Falls back to the page's MENTOR_DATA; with none, the
//           engine works from the entries alone, as before
// Returns { kind: "answer" | "colour" | "none", lead, sources: [ { type, key, label, colour? } ] (up to 3), picks?, suggestions? }.
//
// X8b: what was added, and why. All of it is plain word counting, still no AI model. Each part only uses MENTOR_DATA if it is there.
//  (a) Extra keywords. MENTOR_DATA.keywords gives keyword phrases per entry key. Recipes and basing tips have no keywords of their own
//      (only their group, which counts as a summary word), so this is how "old bronze" finds Aged bronze. They score like any keyword.
//  (b) Synonyms. MENTOR_DATA.synonyms is a list of groups, the canonical word or phrase first. Every variant in the question and in the
//      entries is read as its canonical ("color" -> "colour", "slap chop" -> "drybrush and tint"), longest first, whole words only.
//      The colour path reads the same words, so "green putty" or "white spirit" is not taken for a colour question.
//  (c) Rare words count for more. Each word's points are multiplied by a weight from how many entries use it (in a title, summary,
//      keyword or phrase): about WEIGHT.ref entries counts as before (1), fewer counts up to WEIGHT.max, more counts down to WEIGHT.min.
//      So "verdigris" settles an answer where "layer" or "colour" alone cannot. This works with or without MENTOR_DATA.
//  (d) Phrase bank. MENTOR_DATA.phrases lists about ten ways people ask for each entry. The question is compared with every phrase
//      (shared words over all words, rare words counting more, so the same words give 1) and the entry's best phrase adds up to
//      ASK.points. Below ASK.floor it adds nothing, so a single shared word in a long phrase does not pile up.
//      Also new: a word of an entry's keyword phrase counts on its own (SCORE.keywordWord), even when the whole phrase is not asked.
//  (e) Quick lead. MENTOR_DATA.quick holds a one- or two-line answer for most phrases. When the best source matched one of its phrases
//      at ASK.strong or more, the lead is that phrase's answer (plus "Also see" if it still fits in two sentences). Otherwise the
//      lead is made exactly as before. A starter question uses MENTOR_DATA.starters the same way.
//  (f) THRESHOLD, COVER_BONUS, RELATIVE_KEEP, the X6a SCORE numbers and the "none" answer are unchanged. Two things keep "none" honest now
//      that there are far more words to match: words found nowhere in the entries make every score smaller (UNSEEN_POWER), and chat
//      words ("hi", "was", "thanks") joined FILLER so they never count as unknown. That power is scaled down for an index with few
//      different words (UNSEEN_VOCAB), where everyday words are often missing. The new numbers (WEIGHT, ASK, UNSEEN_POWER,
//      keywordWord) were tuned on half of a 1,900-question test set and measured on the other half, with the rule that no more
//      questions about other things (a 40-question list) may get an answer than before.
(function (root) {
  "use strict";

  // How sure it must be to answer. A keyword phrase match is worth 10 or more by itself, so one clear phrase passes. Title words are
  // worth 3, summary words 2 and body words 1 (at most 3), so three title and summary words together (a loose but real match) also
  // pass, as does a question whose every word is found in an entry that has one in its title (plus COVER_BONUS). One shared everyday word never does. Below it the answer is "none" with suggestions.
  // X8b: each of those points is now times the word's weight (c), so this holds for words of ordinary rarity; a rare word counts a
  // little more, and one shared everyday word counts less than before.
  const THRESHOLD = 8;
  const COVER_BONUS = 5;       // every word asked is found in an entry's title, summary or keywords, and one of them is in its title
  const RELATIVE_KEEP = 0.5;   // a further source must score at least this share of the best one
  const MAX_SOURCES = 3;
  // X8b: keywordWord is new: a word of a keyword phrase counts on its own, like a title word, even when the whole phrase is not asked.
  // The other numbers, THRESHOLD and COVER_BONUS are X6a's, unchanged (see (f) at the top).
  const SCORE = { phrase: 10, phraseExtra: 2, title: 3, summary: 2, body: 1, bodyCap: 3, keywordWord: 3 };
  // X8b (c): a word's weight. ref: a word in this many entries counts 1. min and max: the least and most a word can count.
  // phraseMin: a whole keyword phrase never counts less than this share of its points, however common its words.
  const WEIGHT = { ref: 8, min: 0.4, max: 1.2, phraseMin: 0.6 };
  // X8b (d), (e): the phrase bank. A match below floor adds nothing; from floor up to 1 (the same words) it adds 0 up to points, so the
  // very phrase passes THRESHOLD on its own, while a half match (common on questions about other things) adds little. A match of
  // strong or more earns the quick lead.
  const ASK = { points: 10, floor: 0.5, strong: 0.6 };
  // X8b (f): words found nowhere in the entries (not even in a body) make every score smaller: it is multiplied by the known words'
  // share of the question's weight, to this power (0 turns it off). "what time is it in tokyo" no longer passes on "time" alone.
  const UNSEEN_POWER = 3;
  // X8b (f): an unknown word only says "about something else" once the entries hold enough everyday words. A small index (a few
  // guides with short bodies, or only recipes and basing tips, which have no body) misses words like "use" or "mean", so the power
  // grows with the number of different words in the entries and is full from this many on. The app's index with the knowledge base
  // has about 4,000; the 216-entry test index (13 guides plus 137 recipes and 60 basing tips) has about 640.
  const UNSEEN_VOCAB = 3000;

  // ---------- words ----------
  const FILLER = new Set(("a an the i me my we you your our it its is are am be do does did can could should would will to of for on in at " +
    "by with and or but if so how what why when where which who please help about get got make some any this that these those there just " +
    "really very want need like tell show know whats hows go goes going colour colours color colors paint painting painted model miniature mini figure " +
    // X8b: chat and joining words, so the unseen-word rule (f) never counts them against a question ("hi, I was wondering about primer")
    "was were been being has have had im ive id dont doesnt didnt cant wont isnt hi hello hey thanks thank cheers wondering wondered anyone " +
    "someone guys lol ok okay yes also too than then from into as thing things way ways best good").split(" "));
  // "with" and "for" are filler, but the colour path needs "base coat" and "goes with"; it reads the raw words, not the filtered ones.

  // Plurals and -ing / -ed endings count alike: washes, wash, washing, washed -> "wash"; glazing, glazed, glaze -> "glaz".
  function stem(w) {
    if (w.length <= 3) return w;
    if (w.endsWith("ies") && w.length > 4) w = w.slice(0, -3) + "y";
    else if (/(ches|shes|sses|xes|zes)$/.test(w)) w = w.slice(0, -2);
    else if (w.endsWith("s") && !/(ss|us|is)$/.test(w)) w = w.slice(0, -1);
    if (w.endsWith("ing") && w.length > 5) w = w.slice(0, -3);
    else if (w.endsWith("ed") && w.length > 4) w = w.slice(0, -2);
    if (/([^aeiou])\1$/.test(w) && w.length > 3 && !/(ll|ss)$/.test(w)) w = w.slice(0, -1);   // thinn -> thin
    if (w.endsWith("e") && w.length > 3) w = w.slice(0, -1);
    if (w.length > 4 && w.endsWith("y") && !/[aeiou]y$/.test(w)) w = w.slice(0, -1);   // rusty -> rust, muddy -> mud
    if (/([^aeiou])\1$/.test(w) && w.length > 3 && !/(ll|ss)$/.test(w)) w = w.slice(0, -1);
    return w;
  }
  const rawWords = (text) => String(text == null ? "" : text).toLowerCase().replace(/[^a-z0-9']+/g, " ").replace(/'/g, "").split(" ").filter(Boolean);
  // The meaningful stems of some text, filler left out, in order.
  const tokens = (text) => rawWords(text).filter((w) => !FILLER.has(w)).map(stem);

  // X8b (b): synonyms. The groups are read once into a table: first word of a variant -> [ [variant words], [canonical words] ], longest
  // first. swap() walks the words and replaces the longest variant that starts at each word.
  const synCache = new WeakMap();
  function synonymTable(data) {
    const groups = data && Array.isArray(data.synonyms) ? data.synonyms : null;
    if (!groups) return null;
    let table = synCache.get(groups);
    if (table) return table;
    table = new Map();
    for (const g of groups) {
      if (!Array.isArray(g) || g.length < 2) continue;
      const to = rawWords(g[0]);
      for (const v of g.slice(1)) {
        const from = rawWords(v);
        if (!from.length) continue;
        if (!table.has(from[0])) table.set(from[0], []);
        table.get(from[0]).push([from, to]);
      }
    }
    for (const list of table.values()) list.sort((x, y) => y[0].length - x[0].length);
    synCache.set(groups, table);
    return table;
  }
  function swap(words, table) {
    if (!table) return words;
    const out = [];
    for (let i = 0; i < words.length;) {
      const list = table.get(words[i]);
      const hit = list && list.find(([from]) => from.every((w, j) => words[i + j] === w));
      if (hit) { out.push(...hit[1]); i += hit[0].length; } else { out.push(words[i]); i++; }
    }
    return out;
  }
  // The words of some text with synonyms read as their canonical, and its meaningful stems.
  const wordsOf = (text, table) => swap(rawWords(text), table);
  const stemsOf = (text, table) => wordsOf(text, table).filter((w) => !FILLER.has(w)).map(stem);

  // One-letter slips: a word not found anywhere is read as the one known word a single edit away (a missing, extra, wrong or swapped letter).
  function oneAway(a, b) {
    if (a === b) return true;
    const la = a.length, lb = b.length;
    if (Math.abs(la - lb) > 1) return false;
    let i = 0;
    while (i < la && i < lb && a[i] === b[i]) i++;
    if (la === lb) {
      if (a.slice(i + 1) === b.slice(i + 1)) return true;                        // one wrong letter
      return a[i] === b[i + 1] && a[i + 1] === b[i] && a.slice(i + 2) === b.slice(i + 2);   // two swapped
    }
    return la > lb ? a.slice(i + 1) === b.slice(i) : b.slice(i + 1) === a.slice(i);   // one missing or extra
  }

  // ---------- the colour words, the part words ----------
  // Colour words the wheel and the colour rules already use, each with a plain middle-of-the-family colour to start from.
  const COLOUR_WORDS = {
    red: ["red", "#b3262c"], pink: ["pink", "#d9738c"], orange: ["orange", "#d9742a"], brown: ["brown", "#6e4a2a"], peach: ["orange", "#e8a67a"],
    yellow: ["yellow", "#e4c32a"], mustard: ["yellow", "#c49a1c"], bone: ["yellow", "#d8cfa8"], green: ["green", "#2f8a45"], olive: ["green", "#6b7a2c"],
    lime: ["green", "#8bc34a"], teal: ["blue", "#1f8a8a"], blue: ["blue", "#2a5fb3"], navy: ["blue", "#1c2f66"], purple: ["purple", "#6a3a9a"],
    violet: ["purple", "#7a4fc4"], lavender: ["purple", "#a58fd0"], white: ["white", "#f2f2f0"], grey: ["grey", "#808080"], gray: ["grey", "#808080"],
    black: ["black", "#14141a"], gold: ["metallic", "#c9a227"], silver: ["metallic", "#b4b8bd"], bronze: ["metallic", "#8c6a3a"],
  };
  const COLOUR_LAB_NAME = { red: "Red", orange: "Orange", yellow: "Yellow", green: "Green", blue: "Blue", purple: "Purple", white: "Whites", grey: "Greys", black: "Blacks", metallic: "Metallics" };
  // Part words and their plain synonyms. The four parts are the Mentor tips' own.
  const PART_WORDS = {
    armour: "armour", armor: "armour", plate: "armour", plating: "armour", hull: "armour", shell: "armour", cloak: "armour", robe: "armour",
    eye: "eyes", eyes: "eyes", glow: "eyes", lens: "eyes", visor: "eyes", lamp: "eyes", gem: "eyes",
    weapon: "weapon", blade: "weapon", sword: "weapon", gun: "weapon", axe: "weapon", spear: "weapon", hammer: "weapon", barrel: "weapon", staff: "weapon",
    base: "base", basing: "base", ground: "base", soil: "base", terrain: "base", rim: "base", groundwork: "base",
  };
  const PART_NAME = { armour: "armour", eyes: "eyes", weapon: "the weapon", base: "the base" };
  // How each part picks colours: the same picks and boosts as the Picker (COLOUR_ROLES in app.js: armour, glow, weapon, base).
  const PART_ROLE = {
    armour: { boost: { s: 0.35, l: [0.3, 0.65] }, picks: ["analogous0", "analogous1", "light"] },
    eyes: { boost: { s: 0.85, l: [0.55, 0.65] }, picks: ["complementary", "split0", "split1"] },
    weapon: { boost: { s: 0.3, l: [0.35, 0.6] }, picks: ["mid", "dark", "analogous1"] },
    base: { boost: { s: 0.2, l: [0.2, 0.4] }, picks: ["dark", "mid", "analogous0"] },
  };
  const NEUTRAL_ACCENT_HUES = [25, 195, 330];   // the Picker's accents for a colour with no hue: orange, cyan, pink
  const SOFT = new Set(Object.keys(PART_WORDS).map((w) => stem(w)));   // part words: a lone one in a question never makes an entry fit
  const NOT_A_PART = new Set(["coat", "colour", "color", "layer"]);   // "base coat", "base colour": a technique, not the base of the model

  // ---------- the entries, read once per index (and per MENTOR_DATA) ----------
  const cache = new WeakMap();
  function prepared(entries, data) {
    const was = cache.get(entries);
    if (was && was.data === data) return was.hit;
    const syn = synonymTable(data);
    const extraKeys = (data && data.keywords) || {};
    const asked = (data && data.phrases) || {};
    const vocab = new Set();
    const df = new Map();   // X8b (c): how many entries use each word
    const rows = entries.map((e) => {
      // A recipe's or basing tip's only keyword is its group (metal, ground, ...): a heading, not a topic, so it counts as a summary word.
      const isGroup = e.kind === "detail" || e.kind === "basing";
      const own = isGroup ? [] : (e.keywords || []);
      const extra = Array.isArray(extraKeys[e.key]) ? extraKeys[e.key] : [];   // X8b (a)
      const row = {
        e,
        title: new Set(stemsOf(e.title, syn)), summary: new Set(stemsOf(e.summary + (isGroup ? " " + (e.keywords || []).join(" ") : ""), syn)),
        body: new Set(stemsOf((e.body || []).join(" "), syn)),
        phrases: [...own, ...extra].map((k) => stemsOf(k, syn)).filter((t) => t.length && !(e.kind === "tip" && t.length === 1 && SOFT.has(t[0]))),
        // X8b (d): the phrase bank, each phrase as its set of words; at keeps each phrase's place, for its quick answer
        ask: e.kind === "starter" || !Array.isArray(asked[e.key]) ? [] : asked[e.key].map((p, at) => ({ words: [...new Set(stemsOf(p, syn))], at })).filter((p) => p.words.length),
        starter: e.kind === "starter" ? stemsOf(e.title, syn) : null,
      };
      if (e.kind !== "starter") {
        const used = new Set([...row.title, ...row.summary]);
        for (const p of row.phrases) for (const w of p) used.add(w);
        for (const p of row.ask) for (const w of p.words) used.add(w);
        for (const w of used) { vocab.add(w); df.set(w, (df.get(w) || 0) + 1); }
      }
      return row;
    });
    // X8b (c): the weight of each word. Unknown words (only in a body, or nowhere) count as rare.
    const n = Math.max(1, rows.filter((r) => r.e.kind !== "starter").length);
    const ref = Math.log(1 + n / Math.min(WEIGHT.ref, n));
    const weights = new Map();
    for (const [w, d] of df) weights.set(w, Math.min(WEIGHT.max, Math.max(WEIGHT.min, Math.log(1 + n / d) / ref)));
    const rare = Math.min(WEIGHT.max, Math.max(WEIGHT.min, Math.log(1 + n) / ref));
    const weightOf = (w) => weights.get(w) || rare;
    // a keyword phrase counts by the average weight of its words, but never below WEIGHT.phraseMin
    for (const r of rows) r.keywordWords = new Set(r.phrases.flat());
    for (const r of rows) r.phraseWeight = r.phrases.map((p) => Math.max(WEIGHT.phraseMin, p.reduce((t, w) => t + weightOf(w), 0) / p.length));
    // X8b (d): which phrases use each word, and each phrase's size (its words' weights squared, added up, square-rooted)
    const askIndex = new Map();
    rows.forEach((r, i) => r.ask.forEach((p, j) => {
      p.size = Math.sqrt(p.words.reduce((t, w) => t + weightOf(w) ** 2, 0));
      for (const w of p.words) { if (!askIndex.has(w)) askIndex.set(w, []); askIndex.get(w).push([i, j]); }
    }));
    const seen = new Set(vocab);   // X8b (f): every word in any entry, bodies too
    for (const r of rows) for (const w of r.body) seen.add(w);
    const unseenPower = UNSEEN_POWER * Math.min(1, seen.size / UNSEEN_VOCAB);   // X8b (f)
    const hit = { rows, vocab: [...vocab].sort(), weightOf, askIndex, syn, seen, unseenPower };
    cache.set(entries, { data, hit });
    return hit;
  }

  // Words not known anywhere are read as the nearest known word one slip away (alphabetical on a tie, so it is repeatable).
  function fixTypos(words, vocabList) {
    const known = new Set(vocabList);
    return words.map((w) => {
      if (known.has(w) || w.length < 5) return w;
      for (const v of vocabList) if (v[0] === w[0] && oneAway(w, v)) return v;
      return w;
    });
  }

  function scoreRow(row, q, weightOf) {
    let score = 0, phrases = 0;
    row.phrases.forEach((p, i) => {
      // X8b (c): times the phrase's weight (worked out once, in prepared)
      if (p.every((w) => q.has(w))) { score += (SCORE.phrase + SCORE.phraseExtra * (p.length - 1)) * row.phraseWeight[i]; phrases++; }
    });
    let body = 0;
    for (const w of q) {
      const wt = weightOf(w);
      if (row.title.has(w)) score += SCORE.title * wt;
      if (row.summary.has(w)) score += SCORE.summary * wt;
      if (row.keywordWords.has(w)) score += SCORE.keywordWord * wt;   // X8b
      if (row.body.has(w)) body += SCORE.body * wt;
    }
    let all = q.size > 0, inTitle = false;
    for (const w of q) {
      if (row.title.has(w)) inTitle = true;
      if (!SOFT.has(w) && !(row.title.has(w) || row.summary.has(w) || row.phrases.some((p) => p.includes(w)))) all = false;
    }
    if (all && inTitle) score += COVER_BONUS;
    return score + Math.min(body, SCORE.bodyCap);
  }

  // X8b (d): the best phrase of every entry that shares a word with the question: { row number: [match 0 to 1, phrase place] }.
  // The match is the shared words' weights squared over both sizes (a cosine), so the same words give 1 and extra words on either side lower it.
  function askMatches(q, prep) {
    const best = new Map();
    if (!prep.askIndex.size) return best;
    let qSize = 0;
    for (const w of q) qSize += prep.weightOf(w) ** 2;
    qSize = Math.sqrt(qSize);
    const shared = new Map();
    for (const w of q) {
      const wt2 = prep.weightOf(w) ** 2;
      for (const [i, j] of prep.askIndex.get(w) || []) { const k = i * 1000 + j; shared.set(k, (shared.get(k) || 0) + wt2); }
    }
    for (const [k, num] of shared) {
      const i = Math.floor(k / 1000), p = prep.rows[i].ask[k % 1000];
      const m = num / (p.size * qSize);
      const was = best.get(i);
      if (!was || m > was[0]) best.set(i, [m, p.at]);
    }
    return best;
  }

  // ---------- the answer text: short templates and the entries' own summaries ----------
  const KIND_TYPE = { guide: "guide", detail: "recipe", basing: "basing", tip: "tip" };
  const sentence = (s) => { s = String(s || "").trim(); return s && !/[.!?]$/.test(s) ? s + "." : s; };
  const firstSentence = (s) => { const m = String(s || "").match(/^.*?[.!?](\s|$)/); return (m ? m[0] : String(s || "")).trim(); };
  const upper = (s) => s.charAt(0).toUpperCase() + s.slice(1);
  const source = (e) => ({ type: KIND_TYPE[e.kind], key: e.key, label: e.title });
  function leadFor(e) {
    if (e.kind === "tip") return sentence(firstSentence((e.body || [])[0]) || e.title);
    if (e.kind === "detail" || e.kind === "basing") return sentence(`${e.title}: ${e.summary}`.replace(/: $/, ""));
    return sentence(e.summary || e.title);
  }

  // X8b (e): a quick answer for a hit, when its best phrase matched at ASK.strong or more and that phrase has one ("" if not).
  function quickLead(hit, data) {
    if (!data || !data.quick || !(hit.match >= ASK.strong)) return "";
    const list = data.quick[hit.e.key];
    const text = Array.isArray(list) && typeof list[hit.at] === "string" ? list[hit.at].trim() : "";
    return text ? sentence(text) : "";
  }
  const fitsTwoSentences = (s) => (s.match(/[.!?](\s|$)/g) || []).length <= 2 && s.length <= 260;

  // The best entries for some words. Returns { hits: [ { e, score } ] sorted best first, starter }.
  function lookup(text, index, dropColours, data) {
    const prep = prepared(index.entries, data);
    const { rows, vocab } = prep;
    const words = wordsOf(text, prep.syn);   // X8b (b): synonyms read as their canonical first
    const q0 = (dropColours ? words.filter((w) => !COLOUR_WORDS[w] && w !== "sea") : words).filter((w) => !FILLER.has(w)).map(stem);
    const asked = new Set(fixTypos(q0, vocab));
    // A starter question (the same words, or all but one) goes straight to its targets.
    let starter = null;
    for (const r of rows) {
      if (!r.starter || !r.starter.length || !q0.length) continue;
      const same = r.starter.length === asked.size && r.starter.every((w) => asked.has(w));
      if (same) { starter = r.e; break; }
    }
    const hits = [];
    const ask = askMatches(asked, prep);   // X8b (d)
    let all = 0, known = 0;   // X8b (f)
    for (const w of asked) { const wt = prep.weightOf(w); all += wt; if (prep.seen.has(w)) known += wt; }
    const unseen = all ? (known / all) ** prep.unseenPower : 1;
    rows.forEach((r, i) => {
      if (r.e.kind === "starter") return;
      const [match, at] = ask.get(i) || [0, -1];
      const score = unseen * (scoreRow(r, asked, prep.weightOf) + (match >= ASK.floor ? ASK.points * (match - ASK.floor) / (1 - ASK.floor) : 0));
      if (score > 0) hits.push({ e: r.e, score, match, at });
    });
    // best first; a tie keeps the index order (the sort is stable)
    hits.sort((a, b) => b.score - a.score);
    return { hits, starter, asked, rows };
  }

  function suggestionsFor(found, index) {
    const out = [];
    const starters = index.entries.filter((e) => e.kind === "starter");
    const overlap = (e) => { const t = tokens(e.title); return t.filter((w) => found.asked.has(w)).length; };
    const ranked = starters.map((e, i) => ({ e, n: overlap(e), i })).sort((a, b) => b.n - a.n || a.i - b.i);
    for (const s of ranked) if (out.length < 3) out.push({ text: s.e.title, key: s.e.key });
    for (const h of found.hits) {
      if (out.length >= 3) break;
      if (!out.some((o) => o.key === h.e.key)) out.push({ text: h.e.title, key: h.e.key });
    }
    return out;
  }

  // ---------- colour questions ----------
  function wantedColour(C, baseHex, role, pick, slot) {
    const h = C.harmonies(baseHex);
    if (pick === "dark" || pick === "mid" || pick === "light") return { hex: h.neutrals[{ dark: 0, mid: 1, light: 2 }[pick]], relation: pick };
    let hex, relation;
    if (!h.hueMeaningful) {
      hex = C.hslToHex(NEUTRAL_ACCENT_HUES[slot % NEUTRAL_ACCENT_HUES.length], 0.8, 0.5);
      relation = "accent";
    } else {
      hex = { complementary: h.complementary, split0: h.split[0], split1: h.split[1], analogous0: h.analogous[0], analogous1: h.analogous[1] }[pick];
      relation = pick.replace(/\d$/, "");
    }
    const hsl = C.hexToHsl(hex);
    return { hex: C.hslToHex(hsl.h, Math.max(hsl.s, role.boost.s), Math.min(role.boost.l[1], Math.max(role.boost.l[0], hsl.l))), relation };
  }

  // A catalogue is thousands of paints, and the colour rule scores every one. For a big list only the paints nearest the wanted colour
  // by a plain Lab sum (60 of any kind, 30 of the person's own) go to the real rule, which keeps the answer quick and the same.
  const labCache = new WeakMap();
  function shortlist(C, wanted, paints) {
    if (paints.length <= 150) return paints;
    let labs = labCache.get(paints);
    if (!labs) { labs = paints.map((p) => (C.canMatch(p) ? C.hexToLab(p.colour) : null)); labCache.set(paints, labs); }
    const t = C.hexToLab(wanted);
    if (!t) return paints;
    // one pass, keeping only the nearest few (a long list rarely changes the short ones): near for any paint, mine for the person's own
    const near = [], mine = [];
    const put = (list, cap, i, d) => {
      if (list.length === cap && d >= list[cap - 1].d) return;
      let at = list.length;
      while (at > 0 && list[at - 1].d > d) at--;
      list.splice(at, 0, { i, d });
      if (list.length > cap) list.pop();
    };
    for (let i = 0; i < paints.length; i++) {
      const l = labs[i];
      if (!l) continue;
      const d = (l.L - t.L) ** 2 + (l.a - t.a) ** 2 + (l.b - t.b) ** 2;
      put(near, 60, i, d);
      if (C.haveIt(paints[i])) put(mine, 30, i, d);
    }
    const keep = new Set([...near, ...mine].map((n) => n.i));
    return paints.filter((_, i) => keep.has(i));
  }

  // The paints that may be mixed: owned, and with a colour that is more than a guide (no metallics, washes, inks or materials).
  function colourPicks(C, baseHex, part, paints, ideas) {
    const role = PART_ROLE[part];
    let found;
    if (typeof ideas === "function") {
      found = ideas(baseHex, part) || [];
    } else {
      found = [];
      const skip = [baseHex];
      let slot = 0;
      for (const pick of role.picks) {
        const w = wantedColour(C, baseHex, role, pick, slot);
        if (!["dark", "mid", "light"].includes(pick)) slot++;
        const hit = C.suggestPaint(w.hex, shortlist(C, w.hex, paints), { exclude: skip.slice() });
        if (!hit) continue;
        skip.push(hit.paint.colour);
        found.push({ wanted: w.hex, relation: w.relation, hit });
      }
    }
    const mixable = paints.filter((p) => C.haveIt(p) && C.canMatch(p) && !C.isRoughColour(p));
    return found.slice(0, 3).map((f) => {
      const p = f.hit.paint;
      const pick = { part, relation: f.relation, wanted: f.wanted, paint: { brand: p.brand || "", name: p.name || "", colour: p.colour }, owned: !!f.hit.owned,
        fit: C.fitLabel(f.hit) };
      if (f.hit.quality === "poor" && mixable.length > 1) {
        const b = C.blendSuggestions(f.wanted, mixable, { single: f.hit.distance, limit: 1 })[0];
        if (b) pick.blend = { ratio: b.ratio, colour: b.colour, a: { name: b.a.paint.name, brand: b.a.paint.brand || "", parts: b.a.parts }, b: { name: b.b.paint.name, brand: b.b.paint.brand || "", parts: b.b.parts } };
      }
      return pick;
    });
  }

  function tipsFor(tipList, part, family) {
    const has = (t) => String(t.colour || "").toLowerCase().split(/[^a-z]+/).includes(family);
    const all = tipList.filter((t) => t && t.part === part && !t.sample);   // sample tips only show the format, never an answer
    return [...all.filter(has), ...all.filter((t) => !has(t))];
  }

  // Reads the colour and part words out of the raw words. A part word right after a colour word ("blue armour") belongs to that colour;
  // the part the person is asking about is the first one that does not.
  function readColourQuestion(text, syn) {
    const w = wordsOf(text, syn);   // X8b (b): "green putty" is putty, not a green question
    const colours = [];
    const parts = [];
    for (let i = 0; i < w.length; i++) {
      let word = w[i];
      if (word === "sea" && w[i + 1] === "green") { word = "green"; i++; }   // "sea green" is one colour
      if (COLOUR_WORDS[word]) colours.push({ word, at: i });
      else if (PART_WORDS[word] && !(word === "base" && NOT_A_PART.has(w[i + 1]))) parts.push({ part: PART_WORDS[word], at: i, owned: i > 0 && !!COLOUR_WORDS[w[i - 1]] });
    }
    return { colours, parts };
  }

  function colourAnswer(C, ctx, read) {
    const target = read.parts.find((p) => !p.owned) || read.parts[0] || null;
    const owner = read.parts.find((p) => p.owned && p !== target);
    const ownerColour = owner && read.colours.find((c) => c.at === owner.at - 1);
    const baseWord = (ownerColour || read.colours[0]).word;
    const [group, hex] = COLOUR_WORDS[baseWord];
    const source0 = { type: "colour-lab", key: "wheel:" + group, label: "Colour Lab: " + (COLOUR_LAB_NAME[group] || upper(group)), colour: hex };
    const h = C.harmonies(hex);
    if (!target) {
      // a colour on its own: what goes with it
      const fam = (x) => C.colourFamily(x);
      const named = upper(baseWord);
      const side = [...new Set(h.analogous.map(fam))].filter((f) => f !== baseWord && !f.endsWith(" " + baseWord));
      const lead = h.hueMeaningful
        ? `${named} stands out most against ${fam(h.complementary)}` + (side.length ? ` and sits calmly beside ${side.join(" and ")}.` : ".")
        : `${named} is neutral, so almost any colour works beside it.`;
      return { kind: "colour", lead, sources: [source0] };
    }
    const paints = Array.isArray(ctx.paints) ? ctx.paints : [];
    const picks = colourPicks(C, hex, target.part, paints, ctx.ideas);
    const sources = [source0];
    const tipList = Array.isArray(ctx.tips) ? ctx.tips : (typeof root.MENTOR_TIPS === "undefined" ? [] : root.MENTOR_TIPS);
    for (const t of tipsFor(tipList, target.part, baseWord)) {
      if (sources.length >= MAX_SOURCES) break;
      sources.push({ type: "tip", key: t.key, label: `Tip: ${t.part}, ${t.colour}` });
    }
    const names = picks.map((p) => C.colourFamily(p.wanted)).filter((f, i, a) => f && a.indexOf(f) === i);
    const list = names.length > 1 ? names.slice(0, -1).join(", ") + " and " + names[names.length - 1] : names[0] || "";
    let lead = list ? `For ${PART_NAME[target.part]} with ${baseWord}, try ${list}.` : `Here are the closest ideas for ${PART_NAME[target.part]} with ${baseWord}.`;
    if (picks.some((p) => p.owned)) lead += " Paints you own come first.";
    return { kind: "colour", lead, sources, picks };
  }

  // ---------- the one function ----------
  function mentorAnswer(text, context) {
    const ctx = context || {};
    const index = ctx.index && Array.isArray(ctx.index.entries) ? ctx.index : { entries: [] };
    const C = ctx.colour || root.MinifolioColour;
    // X8b: the extra words, if any (the context's own, else the page's MENTOR_DATA from mentor-data.js)
    const data = ctx.data !== undefined ? ctx.data : (typeof MENTOR_DATA === "undefined" ? null : MENTOR_DATA);
    const found = lookup(text, index, false, data);
    const read = readColourQuestion(text, prepared(index.entries, data).syn);

    // a starter question maps straight to its targets
    if (found.starter) {
      const targets = [];
      for (const key of (found.starter.related || [])) {
        const e = index.entries.find((x) => x.key === key && x.kind !== "starter");
        if (e && targets.length < MAX_SOURCES) targets.push(e);
      }
      const quick = data && data.starters && typeof data.starters[found.starter.key] === "string" ? data.starters[found.starter.key] : "";   // X8b (e)
      if (targets.length) return { kind: "answer", lead: quick ? sentence(quick) : leadFor(targets[0]), sources: targets.map(source) };
    }

    // a colour and a part: paint picks from the colour rules (a colour with no part waits for an entry that fits better)
    if (C && read.colours.length && read.parts.length) return colourAnswer(C, ctx, read);

    // a colour with no part: the colour rules answer, unless the other words in the question fit an entry on their own
    if (C && read.colours.length && lookup(text, index, true, data).hits.filter((h) => h.score >= THRESHOLD).length === 0) return colourAnswer(C, ctx, read);

    const top = found.hits[0];
    if (top && top.score >= THRESHOLD) {
      const keep = found.hits.filter((h) => h.score >= THRESHOLD && h.score >= top.score * RELATIVE_KEEP).slice(0, MAX_SOURCES);
      // X8b (e): the quick answer of the phrase the best source matched, if it matched strongly; else the entry's own words
      const quick = quickLead(keep[0], data);
      let lead = quick || leadFor(keep[0].e);
      const also = keep.length > 1 ? ` Also see ${keep[1].e.title}.` : "";
      if (also && (!quick || fitsTwoSentences(lead + also))) lead += also;
      return { kind: "answer", lead, sources: keep.map((h) => source(h.e)) };
    }
    return { kind: "none", lead: "I could not find that in Guides yet. These are close.", sources: [], suggestions: suggestionsFor(found, index) };
  }

  const api = { mentorAnswer, THRESHOLD, tokens, stem };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.MinifolioMentor = api;
})(typeof window !== "undefined" ? window : globalThis);
