// ===== schemes.js: the starter colour schemes for Colour ideas (Pro preview) =====
// This file is only data. It draws nothing, talks to nothing and stores nothing. app.js reads it when you open the
// "Starter schemes" part of the Colour ideas card in a recipe.
//
// How it is shared: it is loaded as a plain script just before app.js, so the two names below
// (STARTER_MOODS and STARTER_SCHEMES) are there when app.js starts.
//
// Rules for anything written here (a test checks the text):
//  - Hand-written and generic, in our own words from general painting knowledge. Names describe the colours, nothing else.
//  - No Games Workshop names, faction names, scheme names, artwork or logos, and nothing that points at a real army.
//  - Each scheme has: key (a short unique id), mood (one of the keys below), name (colours only), summary (one short line),
//    reason (one or two short sentences) and exactly four colours. A colour has a part (what it is for), look (a plain
//    colour word or two, written to follow "Trim: ") and hex (the colour we look for in your paints and the built-in list).
//  - Shown as plain text only (app.js uses textContent), but keep it free of angle brackets anyway.

// The four mood groups. The chips above the scheme chips use these, in this order.
const STARTER_MOODS = [
  { key: "cold", name: "Cold" },
  { key: "warm", name: "Warm" },
  { key: "dark", name: "Dark" },
  { key: "bright", name: "Bright" },
];

const STARTER_SCHEMES = [
  // ---------- Cold ----------
  { key: "blue-gold", mood: "cold", name: "Cold blue and gold", summary: "Cold blue armour, gold trim, red eyes",
    reason: "Blue and gold is a classic pair. One small bright red spot makes the eyes the first thing people see.",
    colours: [ { part: "Armour", look: "a deep blue", hex: "#1f4287" }, { part: "Armour highlight", look: "a lighter blue", hex: "#6d93d6" },
               { part: "Trim", look: "gold", hex: "#c8a02a" }, { part: "Eyes", look: "a bright red", hex: "#d62b2b" } ] },
  { key: "grey-cyan", mood: "cold", name: "Pale grey and cyan", summary: "Pale grey armour, dark blue trim, cyan glow",
    reason: "A light armour makes dark trim easy to read. Cyan glow stands out on cool colours.",
    colours: [ { part: "Armour", look: "a pale grey", hex: "#b9bdc4" }, { part: "Trim", look: "a dark blue", hex: "#22365c" },
               { part: "Cloth", look: "a mid grey", hex: "#6b7078" }, { part: "Glow", look: "a bright cyan", hex: "#3ed3e6" } ] },
  { key: "teal-silver", mood: "cold", name: "Teal and silver", summary: "Teal armour, silver metal, pale ice blue glow",
    reason: "Teal and silver are both cool, so the model feels calm and clean. A pale blue glow stays in the same family without fighting it.",
    colours: [ { part: "Armour", look: "a deep teal", hex: "#1d6f73" }, { part: "Armour highlight", look: "a lighter teal", hex: "#5fb0ad" },
               { part: "Metal", look: "silver", hex: "#b7bcc2" }, { part: "Glow", look: "a pale ice blue", hex: "#aee6f2" } ] },
  { key: "steel-ice", mood: "cold", name: "Steel blue and ice white", summary: "Steel blue armour, ice white trim, small orange accent",
    reason: "Soft blue-greys and a near-white edge look crisp and cold. Orange sits opposite blue, so a tiny dab of it pops.",
    colours: [ { part: "Armour", look: "a steel blue", hex: "#4a6b8a" }, { part: "Armour highlight", look: "a pale blue-grey", hex: "#9db4c9" },
               { part: "Trim", look: "an icy off-white", hex: "#e9eef2" }, { part: "Accent", look: "a warm orange", hex: "#e0801f" } ] },
  { key: "violet-slate", mood: "cold", name: "Cool violet and slate", summary: "Cool violet armour, slate cloth, pale green glow",
    reason: "Violet and slate grey feel quiet and a little strange. A pale green glow is a long way round the colour wheel, so it stands out.",
    colours: [ { part: "Armour", look: "a deep violet", hex: "#3f2f6b" }, { part: "Armour highlight", look: "a lighter violet", hex: "#7a68b5" },
               { part: "Cloth", look: "a slate grey", hex: "#4b5260" }, { part: "Glow", look: "a pale green", hex: "#9be3a8" } ] },
  { key: "navy-yellow", mood: "cold", name: "Navy and pale yellow", summary: "Navy armour, pale yellow trim, cool grey cloth",
    reason: "Yellow and blue sit opposite each other, so pale yellow trim jumps out against dark navy. The cool grey cloth keeps things quiet.",
    colours: [ { part: "Armour", look: "a navy blue", hex: "#17254d" }, { part: "Armour highlight", look: "a brighter blue", hex: "#3d5ba0" },
               { part: "Trim", look: "a pale yellow", hex: "#efe08a" }, { part: "Cloth", look: "a cool grey", hex: "#7c828c" } ] },

  // ---------- Warm ----------
  { key: "sand-teal", mood: "warm", name: "Sand and teal", summary: "Sandy armour, brown cloth, teal gems",
    reason: "Earth tones are calm and sit well together. Teal is the opposite of warm brown, so small gems in it stand out.",
    colours: [ { part: "Armour", look: "a sandy tan", hex: "#c4aa78" }, { part: "Cloth", look: "a brown", hex: "#5c4330" },
               { part: "Gems", look: "a teal", hex: "#1f9e9a" }, { part: "Base", look: "a dark earth brown", hex: "#3a2f26" } ] },
  { key: "red-grey", mood: "warm", name: "Deep red and dark grey", summary: "Deep red armour, dark grey cloth, pale gold trim",
    reason: "Dark red and dark grey feel serious and tidy. Pale gold gives clean, bright edges.",
    colours: [ { part: "Armour", look: "a deep red", hex: "#8c1d22" }, { part: "Armour highlight", look: "a brighter red", hex: "#c2383a" },
               { part: "Cloth", look: "a dark grey", hex: "#3b3d44" }, { part: "Trim", look: "a pale gold", hex: "#d8bc62" } ] },
  { key: "orange-brown", mood: "warm", name: "Burnt orange and brown", summary: "Burnt orange armour, dark brown cloth, cream trim",
    reason: "Orange and brown are close neighbours, so they blend into a warm, rich look. Cream trim keeps the edges clear.",
    colours: [ { part: "Armour", look: "a burnt orange", hex: "#b8541a" }, { part: "Armour highlight", look: "a lighter orange", hex: "#e08a3c" },
               { part: "Cloth", look: "a dark brown", hex: "#4a3222" }, { part: "Trim", look: "a cream", hex: "#e8dcc0" } ] },
  { key: "mustard-charcoal", mood: "warm", name: "Mustard and charcoal", summary: "Mustard armour, charcoal cloth, deep red spot",
    reason: "Mustard yellow is warm but not loud, and charcoal grey makes it look richer. One deep red spot adds a focus point.",
    colours: [ { part: "Armour", look: "a mustard yellow", hex: "#c99a1c" }, { part: "Armour highlight", look: "a pale yellow", hex: "#e8cf6a" },
               { part: "Cloth", look: "a charcoal grey", hex: "#2e2f33" }, { part: "Bright spot", look: "a deep red", hex: "#a82424" } ] },
  { key: "terracotta-cream", mood: "warm", name: "Terracotta and cream", summary: "Terracotta armour, cream trim, muted blue gems",
    reason: "Clay red and cream feel soft and sun-baked. A muted blue is the opposite colour, so small gems read clearly without shouting.",
    colours: [ { part: "Armour", look: "a clay red", hex: "#b5623f" }, { part: "Armour highlight", look: "a lighter clay", hex: "#d68f6a" },
               { part: "Trim", look: "a cream", hex: "#eadfc5" }, { part: "Gems", look: "a muted blue", hex: "#3c6a99" } ] },
  { key: "olive-amber", mood: "warm", name: "Olive and amber", summary: "Olive armour, amber trim, brown cloth",
    reason: "Olive green leans warm, so it sits happily with amber and brown. It is a calm, earthy set that is easy to paint.",
    colours: [ { part: "Armour", look: "an olive green", hex: "#6b6a2f" }, { part: "Armour highlight", look: "a lighter olive", hex: "#9a9a4d" },
               { part: "Trim", look: "an amber", hex: "#d9951f" }, { part: "Cloth", look: "a brown", hex: "#4a3a28" } ] },

  // ---------- Dark ----------
  { key: "green-bone", mood: "dark", name: "Dark green and bone", summary: "Dark green armour, bone trim, orange glow",
    reason: "Dark green is calm and pale bone lifts the edges. Orange glows against green because it sits on the other side of the colour wheel.",
    colours: [ { part: "Armour", look: "a dark green", hex: "#2e5d3b" }, { part: "Armour highlight", look: "a lighter green", hex: "#5f9a62" },
               { part: "Trim", look: "a pale bone colour", hex: "#d9cfb0" }, { part: "Glow", look: "a bright orange", hex: "#ee7d1b" } ] },
  { key: "dark-bright", mood: "dark", name: "Dark with one bright colour", summary: "Near-black armour, pale trim, one bright purple",
    reason: "Strong light and dark makes the shapes easy to read. One bright colour keeps the eye in one place.",
    colours: [ { part: "Armour", look: "a near-black", hex: "#1d1e23" }, { part: "Cloth", look: "a mid grey", hex: "#5a5c63" },
               { part: "Trim", look: "an off-white", hex: "#e6e3da" }, { part: "Bright spot", look: "a bright purple", hex: "#8a3fd1" } ] },
  { key: "black-red", mood: "dark", name: "Black and deep red", summary: "Near-black armour, deep red trim, hot orange glow",
    reason: "Black with a little red looks sharp and serious. A hot orange glow reads as light because it is much brighter than everything around it.",
    colours: [ { part: "Armour", look: "a near-black", hex: "#17181c" }, { part: "Armour highlight", look: "a dark grey", hex: "#3f4148" },
               { part: "Trim", look: "a deep red", hex: "#8f1f25" }, { part: "Glow", look: "a hot orange", hex: "#f0541f" } ] },
  { key: "charcoal-gold", mood: "dark", name: "Charcoal and old gold", summary: "Charcoal armour, old gold trim, dark brown cloth",
    reason: "Dull, aged gold looks grand against dark grey without being flashy. Dark brown cloth ties the two together.",
    colours: [ { part: "Armour", look: "a charcoal grey", hex: "#2d2f35" }, { part: "Armour highlight", look: "a mid grey", hex: "#62656d" },
               { part: "Trim", look: "an old gold", hex: "#a9862f" }, { part: "Cloth", look: "a dark brown", hex: "#3a2b22" } ] },
  { key: "midnight-sea", mood: "dark", name: "Midnight blue and sea green", summary: "Midnight blue armour, sea green trim, mint glow",
    reason: "A very dark blue with a cool green edge feels deep, like night water. A pale mint glow is easy to see against it.",
    colours: [ { part: "Armour", look: "a midnight blue", hex: "#11193a" }, { part: "Armour highlight", look: "a brighter blue", hex: "#2c3f7a" },
               { part: "Trim", look: "a sea green", hex: "#2f8f7d" }, { part: "Glow", look: "a pale mint", hex: "#a7f0d2" } ] },
  { key: "plum-lime", mood: "dark", name: "Dark plum and lime", summary: "Dark plum armour, grey-bone cloth, lime glow",
    reason: "Plum is dark but still has colour in it. Lime is far from purple on the colour wheel, so a small lime glow stands out strongly.",
    colours: [ { part: "Armour", look: "a dark plum", hex: "#3a1f3f" }, { part: "Armour highlight", look: "a lighter plum", hex: "#6a3f73" },
               { part: "Cloth", look: "a grey-bone colour", hex: "#a8a393" }, { part: "Glow", look: "a bright lime green", hex: "#b6e03a" } ] },

  // ---------- Bright ----------
  { key: "red-white", mood: "bright", name: "Bright red and white", summary: "Bright red armour, white trim, dark grey cloth",
    reason: "Red and white is bold and easy to read from across a table. Dark grey cloth gives your eye somewhere to rest.",
    colours: [ { part: "Armour", look: "a bright red", hex: "#c8262b" }, { part: "Armour highlight", look: "an orange-red", hex: "#e8553a" },
               { part: "Trim", look: "a white", hex: "#f1efe9" }, { part: "Cloth", look: "a dark grey", hex: "#3a3c42" } ] },
  { key: "yellow-black", mood: "bright", name: "Yellow and near-black", summary: "Yellow armour, near-black cloth, mid grey metal",
    reason: "Yellow against black is about the strongest light and dark pair there is. Mid grey metal keeps it from feeling flat.",
    colours: [ { part: "Armour", look: "a strong yellow", hex: "#e8c21a" }, { part: "Armour highlight", look: "a pale yellow", hex: "#f4de6f" },
               { part: "Cloth", look: "a near-black", hex: "#1f2024" }, { part: "Metal", look: "a mid grey", hex: "#7a7d84" } ] },
  { key: "orange-blue", mood: "bright", name: "Orange and mid blue", summary: "Orange armour, mid blue trim, dark blue cloth",
    reason: "Orange and blue are opposites, so each makes the other look brighter. Dark blue cloth stops it from getting too busy.",
    colours: [ { part: "Armour", look: "a bright orange", hex: "#ea7a1c" }, { part: "Armour highlight", look: "a light orange", hex: "#f5a64d" },
               { part: "Trim", look: "a mid blue", hex: "#2f5fa8" }, { part: "Cloth", look: "a dark blue", hex: "#1c2c52" } ] },
  { key: "lime-purple", mood: "bright", name: "Lime green and purple", summary: "Lime green armour, purple cloth, hot pink eyes",
    reason: "Green and purple are far apart on the colour wheel, so this is a loud, playful pair. Keep the pink to the eyes only so it stays under control.",
    colours: [ { part: "Armour", look: "a lime green", hex: "#7cc42a" }, { part: "Armour highlight", look: "a lighter lime", hex: "#a8dd5a" },
               { part: "Cloth", look: "a purple", hex: "#5b2f8f" }, { part: "Eyes", look: "a hot pink", hex: "#e83e8c" } ] },
  { key: "turquoise-coral", mood: "bright", name: "Turquoise and coral", summary: "Turquoise armour, coral trim, cream cloth",
    reason: "Turquoise and coral are opposites and feel fresh and sunny together. Cream cloth softens the contrast.",
    colours: [ { part: "Armour", look: "a bright turquoise", hex: "#19b5b0" }, { part: "Armour highlight", look: "a light turquoise", hex: "#6fdcd6" },
               { part: "Trim", look: "a coral", hex: "#f26b5b" }, { part: "Cloth", look: "a pale cream", hex: "#f0e6d0" } ] },
  { key: "white-sky", mood: "bright", name: "White and sky blue", summary: "White armour, sky blue trim, yellow accent",
    reason: "A white or off-white armour is light and clean, and sky blue adds colour without weight. A small yellow accent gives one warm spot.",
    colours: [ { part: "Armour", look: "an off-white", hex: "#eceae4" }, { part: "Armour shade", look: "a light grey", hex: "#b8b9bd" },
               { part: "Trim", look: "a sky blue", hex: "#4fa3e0" }, { part: "Accent", look: "a bright yellow", hex: "#f0c419" } ] },
];
