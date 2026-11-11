// ===== where-to-buy.js: what to buy for some Guides entries (plain data) =====
// This file is only data. It draws nothing, talks to nothing and stores nothing. app.js reads it when it shows a Guides entry,
// a Basing tip or a Mentor answer.
//
// How it is shared: it is loaded as a plain script just before app.js, so WHERE_TO_BUY is there when app.js starts.
//
// L1: WHERE_TO_BUY = { Guides entry key: { kind, types: [up to 3 product types] } }.
//   kind:  "guide" for an entry in guides-data.js, "basing" for a tip in basing-tips.js. One key can be used in two files, so the
//          kind makes sure the products only ever show on the entry they were chosen for.
//   types: generic product types, the words a shop's own search box is given. Product types only: no brand names, no model
//          names, nothing taken from a creator. George approved each one (L1 the first 5, L2 the other 20).
// An entry here shows a closed "Where to buy" fold-out: each type with plain search links (the shops in SHOPS that sell every
// brand) and an Add to shopping list button that puts the type on the shopping list as a Gear item. A key with no Guides entry
// is ignored by the app (and a test fails on it).
const WHERE_TO_BUY = {
  // L1: the first 5
  "wet-palette": { kind: "guide", types: ["wet palette", "wet palette paper"] },
  "mould-line-removal": { kind: "guide", types: ["mould line remover", "sanding sticks", "needle files"] },
  "clippers-and-clipping": { kind: "guide", types: ["sprue cutters", "hobby knife"] },
  "varnishing": { kind: "guide", types: ["matt varnish", "gloss varnish", "satin varnish"] },
  "static-grass": { kind: "basing", types: ["static grass", "static grass applicator"] },

  // L2 group 1: Tools and prep
  "airbrush-setup": { kind: "guide", types: ["airbrush", "airbrush compressor", "moisture trap"] },
  "airbrush-cleaning": { kind: "guide", types: ["airbrush cleaner", "airbrush cleaning pot", "airbrush cleaning kit"] },
  "spray-booth": { kind: "guide", types: ["spray booth", "spray booth filter"] },
  "hobby-safety": { kind: "guide", types: ["respirator mask", "nitrile gloves"] },
  "brush-care": { kind: "guide", types: ["brush soap", "brush restorer"] },
  "choosing-glue": { kind: "guide", types: ["plastic glue", "super glue", "PVA glue"] },
  "pinning-parts": { kind: "guide", types: ["pin vice", "drill bits", "brass rod"] },
  "two-part-putty": { kind: "guide", types: ["epoxy putty", "sculpting tools"] },
  "light-and-magnification": { kind: "guide", types: ["LED lamp", "magnifying glasses"] },
  "painting-handles": { kind: "guide", types: ["painting handle"] },

  // L2 group 2: Techniques and Basing
  "applying-transfers": { kind: "guide", types: ["decal softener", "gloss varnish"] },
  "weathering-pigments": { kind: "guide", types: ["weathering pigments", "pigment fixer"] },
  "hairspray-chipping": { kind: "guide", types: ["chipping medium", "satin varnish"] },
  "oil-washes": { kind: "guide", types: ["oil paint", "odourless thinner"] },
  "airbrush-masking": { kind: "guide", types: ["masking tape", "masking putty", "liquid mask"] },
  "snow-bases": { kind: "basing", types: ["snow texture", "snow powder"] },
  "puddles-and-water": { kind: "basing", types: ["water effects", "gloss varnish"] },
  "natural-tufts": { kind: "basing", types: ["grass tufts", "flower tufts"] },
  "texture-paint-bases": { kind: "basing", types: ["texture paint", "texture paste"] },
  "foam-bushes-and-shrubs": { kind: "basing", types: ["clump foliage", "scatter foliage"] },
};

// ===== HS2: the short safety line (plain data) =====
// Entries that touch sprays, solvents, glue, resin, heat or dust show one quiet line under their text (Guides only, never under a
// Mentor answer). HOBBY_SAFETY_KEYS = { entry key: kind }, kind "guide" (guides-data.js) or "basing" (basing-tips.js), the same idea as
// WHERE_TO_BUY above. A key not listed here shows no line. The words are fixed: do not reword them here.
const HOBBY_SAFETY_LINE = "Hobby tip, not safety advice. Follow the maker's instructions and ventilate well.";
const HOBBY_SAFETY_KEYS = {
  "acrylic-enamel-and-oil-paints": "guide", "airbrush-basics": "guide", "airbrush-paint-thinning": "guide",
  "airbrush-priming": "guide", "airbrush-safety": "guide", "airbrushing-one-coat-paints": "guide",
  "basing-glue-and-tools": "guide", "choosing-glue": "guide", "cutting-and-sealing-foam": "guide",
  "disposing-of-paint-water": "guide", "dust-weathering": "guide", "enamel-washes": "guide",
  "filament-3d-prints": "guide", "fix-basing-problems": "guide", "fix-glue-marks-and-fingerprints": "guide",
  "fix-priming-problems": "guide", "fixing-building-mistakes": "guide", "gap-filling": "guide",
  "gluing-strong-joints": "guide", "hobby-kit-pets-and-kids": "guide", "hobby-safety": "guide",
  "keeping-solvents-safe": "guide", "model-materials-compared": "guide", "oil-blending": "guide",
  "oil-washes": "guide", "painting-tank-tracks": "guide", "panel-lining": "guide", "pinning-parts": "guide",
  "polymer-clay-sculpting": "guide", "preparing-3d-prints": "guide", "preparing-metal-models": "guide",
  "resin-or-filament-printing": "guide", "resin-print-problems": "guide", "resin-printer-care": "guide",
  "resin-printing-setup": "guide", "resin-water-effects": "guide", "spray-booth": "guide",
  "spray-can-faults": "guide", "stripping-paint": "guide", "superglue-problems": "guide",
  "taking-apart-old-models": "guide", "two-part-putty": "guide", "ultrasonic-cleaner": "guide",
  "using-filters": "guide", "weathering-pigments": "guide",
  "resin-ice": "basing", "cave-floor": "basing",
};
