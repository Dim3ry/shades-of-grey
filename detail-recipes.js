// ===== detail-recipes.js: the generic detail recipes for Colour ideas (Pro preview) =====
// This file is only data. It draws nothing, talks to nothing and stores nothing. app.js reads it when you open the
// "Detail recipes" part of the Colour ideas card in a recipe.
//
// How it is shared: it is loaded as a plain script just before app.js (after schemes.js), so the two names below
// (DETAIL_GROUPS and DETAIL_RECIPES) are there when app.js starts.
//
// Rules for anything written here (a test checks the text):
//  - Hand-written and generic, in our own words from general painting knowledge. Names describe the technique or the
//    thing being painted, nothing else.
//  - No Games Workshop names, faction names, scheme names, artwork or logos, and nothing that points at a real army.
//  - A step names a TARGET COLOUR (a plain colour word and a hex), never a paint. app.js finds the nearest paint in
//    your palette (yours first) and then in the built-in list.
//  - Each recipe has: key (a short unique id), group (one of the keys below), name (technique or subject only),
//    summary (one short line) and 3 or 4 steps.
//  - Each step has: technique (one of the app's usual technique names), coats (a whole number), mix (the share of paint in
//    the step, 100 = straight from the pot, lower = thinned), look (a plain colour word or two), hex (the target colour)
//    and note (one short sentence).
//  - Shown as plain text only (app.js uses textContent), but keep it free of angle brackets anyway.

// The groups. The chips above the recipe chips use these, in this order.
const DETAIL_GROUPS = [
  { key: "body", name: "Body" },
  { key: "metal", name: "Metal" },
  { key: "material", name: "Materials" },
  { key: "light", name: "Light" },
];

const DETAIL_RECIPES = [
  // ---------- Body ----------
  { key: "teeth", group: "body", name: "Teeth", summary: "Aged ivory teeth with a dark gum line",
    steps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a warm grey-brown", hex: "#8a7b66", note: "Paint from the root towards the tip." },
      { technique: "Wash", coats: 1, mix: 30, look: "a warm brown", hex: "#6b4f33", note: "Thin it with water or medium and touch it into the gum line." },
      { technique: "Layer", coats: 1, mix: 100, look: "a pale ivory", hex: "#d8cdb0", note: "Leave a little of the base showing at the root." },
      { technique: "Edge highlight", coats: 1, mix: 100, look: "a near-white cream", hex: "#f0e8d2", note: "Tips only, with a fine brush." },
    ] },
  { key: "bone", group: "body", name: "Bone", summary: "Weathered bone, warm and slightly yellow",
    steps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a dull tan", hex: "#a89a7c", note: "Thin, even coats look better than one thick coat." },
      { technique: "Wash", coats: 1, mix: 30, look: "a warm brown", hex: "#5a4630", note: "Thin it and let it pool in the cracks." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a light bone", hex: "#d8cfb4", note: "Wipe most of the paint off the brush first." },
      { technique: "Edge highlight", coats: 1, mix: 100, look: "a pale cream", hex: "#efe7d0", note: "Only on the sharpest edges." },
    ] },
  { key: "chitin", group: "body", name: "Chitin", summary: "Dark, glossy insect-like shell with a cool sheen",
    steps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a near-black purple", hex: "#2b2530", note: "Aim for a smooth, even coat." },
      { technique: "Layer", coats: 1, mix: 100, look: "a muted purple", hex: "#50426e", note: "Paint the raised, curved areas and leave the dark in the gaps." },
      { technique: "Edge highlight", coats: 1, mix: 100, look: "a pale violet", hex: "#9a8bc0", note: "A thin line on the top of each curve." },
      { technique: "Glaze", coats: 1, mix: 25, look: "a teal tint", hex: "#3a8f8a", note: "One small patch on each plate gives a shiny, oily sheen." },
    ] },
  { key: "skin", group: "body", name: "Skin", summary: "Natural skin with a shade, two lights and a touch of warmth",
    steps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a mid skin tone", hex: "#b98a6a", note: "Pick the colour closest to your model's skin and keep the steps." },
      { technique: "Shade", coats: 1, mix: 30, look: "a warm brown", hex: "#6e4330", note: "Thin it and put it in the creases only." },
      { technique: "Layer", coats: 1, mix: 100, look: "a lighter skin tone", hex: "#d1a688", note: "Leave the creases dark." },
      { technique: "Edge highlight", coats: 1, mix: 100, look: "a pale skin tone", hex: "#ecc9ac", note: "Nose, brow, cheekbones and knuckles." },
    ] },
  { key: "blood", group: "body", name: "Blood", summary: "Fresh, wet-looking blood with darker older edges",
    steps: [
      { technique: "Base coat", coats: 1, mix: 100, look: "a deep red", hex: "#6e0f12", note: "Dab it on in small drips and splashes, not a flat coat." },
      { technique: "Glaze", coats: 1, mix: 30, look: "a very dark red-brown", hex: "#3a0a0c", note: "Thin it and add it to the edges so they look older." },
      { technique: "Layer", coats: 1, mix: 100, look: "a bright red", hex: "#c0281f", note: "Leave the middle of the freshest drops brighter." },
      { technique: "Edge highlight", coats: 1, mix: 100, look: "a light orange-red", hex: "#e8553e", note: "A tiny dot on top of a drop looks like a wet shine." },
    ] },

  // ---------- Metal ----------
  { key: "rust", group: "metal", name: "Rusty metal", summary: "Dark metal with orange rust patches and worn edges",
    steps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a dark brown-grey", hex: "#4a3a30", note: "This is the old metal under the rust." },
      { technique: "Sponge", coats: 1, mix: 100, look: "a rusty brown", hex: "#8a4a24", note: "Dab most of the paint off the sponge first, then tap on patches." },
      { technique: "Stipple", coats: 1, mix: 100, look: "a bright orange", hex: "#c0702a", note: "Small dots in the middle of the patches only." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a light metal grey", hex: "#9a948c", note: "A light touch on the edges, where metal would be rubbed clean." },
    ] },
  { key: "oiled-metal", group: "metal", name: "Oiled metal", summary: "Dark gunmetal that looks greasy and well used",
    steps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a dark gunmetal", hex: "#2a2d33", note: "Smooth and even." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a mid steel grey", hex: "#6a7078", note: "Light touch on the edges and raised parts." },
      { technique: "Wash", coats: 1, mix: 30, look: "an oily black-brown", hex: "#1a1612", note: "Let it pool in the low spots and recesses." },
      { technique: "Glaze", coats: 1, mix: 20, look: "a warm oily brown", hex: "#3d3226", note: "Streak it downwards from joins and bolts." },
    ] },
  { key: "verdigris", group: "metal", name: "Verdigris", summary: "Old copper turning blue-green",
    steps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a copper brown", hex: "#8a5a2e", note: "This is the bare metal under the green." },
      { technique: "Glaze", coats: 1, mix: 30, look: "a blue-green", hex: "#2f8f7f", note: "Thin it and let it collect in the recesses." },
      { technique: "Layer", coats: 1, mix: 100, look: "a light turquoise", hex: "#6fc2b0", note: "Dab it onto the edges of the green patches." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a pale mint", hex: "#cfe8dd", note: "The barest touch on the highest points." },
    ] },
  { key: "weathering", group: "metal", name: "Paint chips and weathering", summary: "Chips, scratches and dust on painted armour or machines",
    steps: [
      { technique: "Sponge", coats: 1, mix: 100, look: "a dark brown", hex: "#3b2d25", note: "Dab small chips along edges and corners, where things get knocked." },
      { technique: "Edge highlight", coats: 1, mix: 100, look: "a light steel grey", hex: "#9a9aa0", note: "A thin scratch line along one side of each chip." },
      { technique: "Wash", coats: 1, mix: 25, look: "a dusty brown", hex: "#5a4a3a", note: "Thin it and run it down from rivets and joins for dirt streaks." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a pale dust", hex: "#b8a78a", note: "Add dust to the lower parts only." },
    ] },
  { key: "gold", group: "metal", name: "Gold metal", summary: "Rich gold with a warm shade and a pale edge",
    steps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a dark gold-brown", hex: "#7a5a1f", note: "Smooth and even." },
      { technique: "Wash", coats: 1, mix: 30, look: "a warm brown", hex: "#5a3a16", note: "Thin it and keep it in the recesses." },
      { technique: "Layer", coats: 1, mix: 100, look: "a rich gold", hex: "#c19a2e", note: "Cover the raised areas and leave the shade in the gaps." },
      { technique: "Edge highlight", coats: 1, mix: 100, look: "a pale gold", hex: "#f0d77a", note: "Thin lines on the sharpest edges." },
    ] },
  { key: "steel", group: "metal", name: "Bright steel", summary: "Clean, shiny steel with a cool shade",
    steps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a dark steel", hex: "#3a3d44", note: "Smooth and even." },
      { technique: "Wash", coats: 1, mix: 30, look: "a cool dark grey-blue", hex: "#2a2e36", note: "Thin it and push it into the recesses." },
      { technique: "Layer", coats: 1, mix: 100, look: "a mid steel", hex: "#8d939b", note: "Raised areas only." },
      { technique: "Edge highlight", coats: 1, mix: 100, look: "a bright silver", hex: "#d6dae0", note: "A thin line on the edges and one small dot on each corner." },
    ] },

  // ---------- Materials ----------
  { key: "leather", group: "material", name: "Leather", summary: "Soft brown leather with darker creases and pale stitching edges",
    steps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a mid brown", hex: "#5a3a24", note: "Thin, smooth coats work best." },
      { technique: "Wash", coats: 1, mix: 30, look: "a dark brown", hex: "#2b1a10", note: "Thin it and keep it in the creases and under straps." },
      { technique: "Layer", coats: 1, mix: 100, look: "a warm tan-brown", hex: "#7d5233", note: "Raised, curved parts only." },
      { technique: "Edge highlight", coats: 1, mix: 100, look: "a light tan", hex: "#a9794d", note: "Edges and stitches only." },
    ] },
  { key: "cloth", group: "material", name: "Cloth", summary: "Fabric with deep folds and light ridges",
    steps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a drab khaki", hex: "#8a7f6a", note: "Swap in your own cloth colour and keep the same steps." },
      { technique: "Shade", coats: 1, mix: 30, look: "a dark brown", hex: "#3f382b", note: "Thin it and run it into the folds." },
      { technique: "Layer", coats: 1, mix: 100, look: "a light khaki", hex: "#aaa086", note: "Paint the ridges of the folds and leave the dark in the gaps." },
      { technique: "Edge highlight", coats: 1, mix: 100, look: "a pale sand", hex: "#cfc7ac", note: "Only the sharpest folds and hems." },
    ] },
  { key: "wood", group: "material", name: "Wood", summary: "Wood with visible grain",
    steps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a mid brown", hex: "#6b4a2e", note: "Smooth and even." },
      { technique: "Wash", coats: 1, mix: 30, look: "a dark brown", hex: "#3a2616", note: "Thin it and let it run along the direction of the grain." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a light tan", hex: "#a8845c", note: "Brush along the grain, not across it." },
      { technique: "Layer", coats: 1, mix: 100, look: "a pale tan", hex: "#c9a679", note: "A few thin lines for grain, and a pale edge on corners." },
    ] },
  { key: "mud", group: "material", name: "Mud and dust", summary: "Dried dirt on the legs and edges, with a few wet patches",
    steps: [
      { technique: "Base coat", coats: 1, mix: 100, look: "a dark earth brown", hex: "#4f3b2a", note: "Thin patches, heavier near the bottom." },
      { technique: "Stipple", coats: 1, mix: 100, look: "a mid earth brown", hex: "#7a5c3e", note: "Dab it with an old brush for a rough surface." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a dusty sand", hex: "#b09a76", note: "Lower legs and edges only." },
      { technique: "Glaze", coats: 1, mix: 25, look: "a wet dark brown", hex: "#3b2a1c", note: "Small glossy patches look like fresh mud." },
    ] },
  { key: "scorch", group: "material", name: "Scorch marks", summary: "Burnt, blackened patches that fade out softly",
    steps: [
      { technique: "Stipple", coats: 1, mix: 100, look: "a near-black", hex: "#1f1c1b", note: "Small dots, clustered tightly at the centre of the burn." },
      { technique: "Glaze", coats: 2, mix: 25, look: "a soft charcoal grey", hex: "#3d3a3a", note: "Fade it outwards in thin layers." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a faint brown", hex: "#6b5a4a", note: "A very light touch around the edge of the burn." },
      { technique: "Glaze", coats: 1, mix: 20, look: "a warm orange-brown", hex: "#9a5a24", note: "Just a faint tint at the outer edge, like heat staining." },
    ] },

  // ---------- Light ----------
  { key: "glow", group: "light", name: "Eyes and glow", summary: "A small glowing eye or light, dark to bright",
    steps: [
      { technique: "Base coat", coats: 1, mix: 100, look: "a deep red", hex: "#8a1c14", note: "For another glow colour, keep the order of dark, bright, then brightest." },
      { technique: "Layer", coats: 1, mix: 100, look: "a hot orange", hex: "#ee5a1c", note: "Leave a thin dark rim round the edge." },
      { technique: "Edge highlight", coats: 1, mix: 100, look: "a bright yellow", hex: "#ffd45a", note: "One tiny dot near the centre." },
      { technique: "Glaze", coats: 1, mix: 20, look: "a faint orange", hex: "#ff7a3c", note: "A very thin haze on the surface next to the eye, as if it lights it up." },
    ] },
  { key: "gems", group: "light", name: "Gems and lenses", summary: "A shiny gem or glass lens with a bright reflection",
    steps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a deep blue", hex: "#1d3f8a", note: "Any colour works, so pick a deep version of yours and keep the steps." },
      { technique: "Layer", coats: 1, mix: 100, look: "a bright blue", hex: "#3c78d6", note: "Paint the lower half only." },
      { technique: "Layer", coats: 1, mix: 100, look: "a pale blue", hex: "#8fc4f2", note: "A thin curve along the bottom edge, as light passing through." },
      { technique: "Edge highlight", coats: 1, mix: 100, look: "a near-white", hex: "#f4faff", note: "One tiny dot and a short line in the top corner for the reflection." },
    ] },
];
