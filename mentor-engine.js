// ===== mentor-engine.js: the Mentor answer engine (X6a, no screen) =====
// Turns what a person typed (or a starter question) into an answer made only from our own entries and the colour rules.
// No AI model, no server, no network, nothing stored. It draws nothing. Same input, same output.
//
// How it is shared: loaded as a plain script just before app.js (after guides-data.js). It adds ONE name to the page, MinifolioMentor.
// The test file loads the very same file in Node. mentorAnswer(text, context) is MinifolioMentor.mentorAnswer.
//
// context:
//   index   the Guides loader index (knowledgeIndex() in app.js): { entries: [ { key, kind, category, title, summary, body, keywords } ] }
//   paints  every paint that may be suggested, the person's own first or flagged (status "owned" or "low"); the colour rules do the rest
//   tips    the Mentor tips (MENTOR_TIPS), for their suggested colours. Optional, falls back to the page's MENTOR_TIPS
//   colour  the colour maths (MinifolioColour). Optional, falls back to the page's
//   ideas   optional: ideas(baseHex, part) returning [ { wanted, relation, hit } ], so the screen can hand over its own Picker code
// Returns { kind: "answer" | "colour" | "none", lead, sources: [ { type, key, label, colour? } ] (up to 3), picks?, suggestions? }.
(function (root) {
  "use strict";

  // How sure it must be to answer. A keyword phrase match is worth 10 or more by itself, so one clear phrase passes. Title words are
  // worth 3, summary words 2 and body words 1 (at most 3), so three title and summary words together (a loose but real match) also
  // pass, as does a question whose every word is found in an entry that has one in its title (plus COVER_BONUS). One shared everyday word never does. Below it the answer is "none" with suggestions.
  const THRESHOLD = 8;
  const COVER_BONUS = 5;       // every word asked is found in an entry's title, summary or keywords, and one of them is in its title
  const RELATIVE_KEEP = 0.5;   // a further source must score at least this share of the best one
  const MAX_SOURCES = 3;
  const SCORE = { phrase: 10, phraseExtra: 2, title: 3, summary: 2, body: 1, bodyCap: 3 };

  // ---------- words ----------
  const FILLER = new Set(("a an the i me my we you your our it its is are am be do does did can could should would will to of for on in at " +
    "by with and or but if so how what why when where which who please help about get got make some any this that these those there just " +
    "really very want need like tell show know whats hows go goes going colour colours color colors paint painting painted model miniature mini figure").split(" "));
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

  // ---------- the entries, read once per index ----------
  const cache = new WeakMap();
  function prepared(entries) {
    let hit = cache.get(entries);
    if (hit) return hit;
    const vocab = new Set();
    const rows = entries.map((e) => {
      // A recipe's or basing tip's only keyword is its group (metal, ground, ...): a heading, not a topic, so it counts as a summary word.
      const isGroup = e.kind === "detail" || e.kind === "basing";
      const row = {
        e,
        title: new Set(tokens(e.title)), summary: new Set(tokens(e.summary + (isGroup ? " " + (e.keywords || []).join(" ") : ""))),
        body: new Set(tokens((e.body || []).join(" "))),
        phrases: isGroup ? [] : (e.keywords || []).map((k) => tokens(k)).filter((t) => t.length && !(e.kind === "tip" && t.length === 1 && SOFT.has(t[0]))),
        starter: e.kind === "starter" ? tokens(e.title) : null,
      };
      for (const set of [row.title, row.summary]) for (const w of set) vocab.add(w);
      for (const p of row.phrases) for (const w of p) vocab.add(w);
      return row;
    });
    hit = { rows, vocab: [...vocab].sort() };
    cache.set(entries, hit);
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

  function scoreRow(row, q) {
    let score = 0, phrases = 0;
    for (const p of row.phrases) {
      if (p.every((w) => q.has(w))) { score += SCORE.phrase + SCORE.phraseExtra * (p.length - 1); phrases++; }
    }
    let body = 0;
    for (const w of q) {
      if (row.title.has(w)) score += SCORE.title;
      if (row.summary.has(w)) score += SCORE.summary;
      if (row.body.has(w)) body += SCORE.body;
    }
    let all = q.size > 0, inTitle = false;
    for (const w of q) {
      if (row.title.has(w)) inTitle = true;
      if (!SOFT.has(w) && !(row.title.has(w) || row.summary.has(w) || row.phrases.some((p) => p.includes(w)))) all = false;
    }
    if (all && inTitle) score += COVER_BONUS;
    return score + Math.min(body, SCORE.bodyCap);
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

  // The best entries for some words. Returns { hits: [ { e, score } ] sorted best first, starter }.
  function lookup(text, index, dropColours) {
    const { rows, vocab } = prepared(index.entries);
    const q0 = (dropColours ? rawWords(text).filter((w) => !COLOUR_WORDS[w] && w !== "sea") : rawWords(text)).filter((w) => !FILLER.has(w)).map(stem);
    const asked = new Set(fixTypos(q0, vocab));
    // A starter question (the same words, or all but one) goes straight to its targets.
    let starter = null;
    for (const r of rows) {
      if (!r.starter || !r.starter.length || !q0.length) continue;
      const same = r.starter.length === asked.size && r.starter.every((w) => asked.has(w));
      if (same) { starter = r.e; break; }
    }
    const hits = [];
    for (const r of rows) {
      if (r.e.kind === "starter") continue;
      const score = scoreRow(r, asked);
      if (score > 0) hits.push({ e: r.e, score });
    }
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
  function readColourQuestion(text) {
    const w = rawWords(text);
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
    const read = readColourQuestion(text);
    const found = lookup(text, index);

    // a starter question maps straight to its targets
    if (found.starter) {
      const targets = [];
      for (const key of (found.starter.related || [])) {
        const e = index.entries.find((x) => x.key === key && x.kind !== "starter");
        if (e && targets.length < MAX_SOURCES) targets.push(e);
      }
      if (targets.length) return { kind: "answer", lead: leadFor(targets[0]), sources: targets.map(source) };
    }

    // a colour and a part: paint picks from the colour rules (a colour with no part waits for an entry that fits better)
    if (C && read.colours.length && read.parts.length) return colourAnswer(C, ctx, read);

    // a colour with no part: the colour rules answer, unless the other words in the question fit an entry on their own
    if (C && read.colours.length && lookup(text, index, true).hits.filter((h) => h.score >= THRESHOLD).length === 0) return colourAnswer(C, ctx, read);

    const top = found.hits[0];
    if (top && top.score >= THRESHOLD) {
      const keep = found.hits.filter((h) => h.score >= THRESHOLD && h.score >= top.score * RELATIVE_KEEP).slice(0, MAX_SOURCES);
      let lead = leadFor(keep[0].e);
      if (keep.length > 1) lead += ` Also see ${keep[1].e.title}.`;
      return { kind: "answer", lead, sources: keep.map((h) => source(h.e)) };
    }
    return { kind: "none", lead: "I could not find that in Guides yet. These are close.", sources: [], suggestions: suggestionsFor(found, index) };
  }

  const api = { mentorAnswer, THRESHOLD, tokens, stem };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.MinifolioMentor = api;
})(typeof window !== "undefined" ? window : globalThis);
