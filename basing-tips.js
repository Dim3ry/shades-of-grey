// ===== basing-tips.js: the generic basing how-tos for Colour ideas (Pro preview) =====
// This file is only data. It draws nothing, talks to nothing and stores nothing. app.js reads it when you open the
// "Basing tips" part of the Colour ideas card in a recipe.
//
// How it is shared: it is loaded as a plain script just before app.js (after detail-recipes.js), so the two names below
// (BASING_GROUPS and BASING_TIPS) are there when app.js starts.
//
// Rules for anything written here (a test checks the text):
//  - Hand-written and generic, in our own words from general modelling knowledge. Names describe the kind of ground or
//    surface, nothing else.
//  - No Games Workshop names, faction names, scheme names, artwork or logos, and nothing that points at a real army.
//  - No brand names and no product names anywhere. Materials are plain things (fine sand, white glue, an old brush).
//  - Each tip has: key (a short unique id), group (one of the keys below), name (the ground or surface only), summary (one
//    short line), materials (3 to 6 plain things), howto (3 to 5 short steps, one sentence each) and paintSteps (0 to 5
//    optional paint steps).
//  - Materials and how-to steps are only ever SHOWN. They are never added to a recipe.
//  - A paint step names a TARGET COLOUR (a plain colour word and a hex), never a paint. app.js finds the nearest paint in
//    your palette (yours first) and then in the built-in list. Each paint step has: technique (one of the app's usual
//    technique names), coats (a whole number), mix (the share of paint in the step, 100 = straight from the pot, lower =
//    thinned), look (a plain colour word or two), hex (the target colour) and note (one short sentence).
//  - Shown as plain text only (app.js uses textContent), but keep it free of angle brackets anyway.

// The groups. The chips above the tip chips use these, in this order.
const BASING_GROUPS = [
  { key: "ground", name: "Dry ground" },
  { key: "cold", name: "Wet and cold" },
  { key: "plants", name: "Plants" },
  { key: "stone", name: "Stone and fire" },
];

const BASING_TIPS = [
  // ---------- Dry ground ----------
  { key: "sand", group: "ground", name: "Sand", summary: "Dry, pale ground with soft drifts",
    materials: ["Fine sand, washed and dried", "White glue that dries clear", "A little water", "An old brush you do not mind ruining", "A small sieve or tea strainer"],
    howto: [
      "Paint a thin layer of white glue on the base, one small area at a time.",
      "Sprinkle sand over the glue, then tip the base over a tray to shake off the extra.",
      "Press it down gently with a finger or the flat of the brush.",
      "Let it dry fully, then dribble thinned glue over it to lock the sand in place.",
    ],
    paintSteps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a mid sandy brown", hex: "#9c8760", note: "Cover every grain and get paint into the gaps." },
      { technique: "Wash", coats: 1, mix: 30, look: "a warm brown", hex: "#5e4a30", note: "Thin it and let it settle between the grains." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a light sand", hex: "#cdbd94", note: "Wipe most of the paint off the brush first." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a pale cream", hex: "#e6dcc0", note: "Very light touches on the high spots only." },
    ] },
  { key: "gravel", group: "ground", name: "Gravel", summary: "Small loose stones on packed ground",
    materials: ["Fine gravel or crushed stone, washed and dried", "Fine sand", "White glue that dries clear", "An old brush", "Tweezers"],
    howto: [
      "Spread glue over the base and sprinkle fine sand on it for the packed ground.",
      "Let it dry, then dab glue onto a few patches.",
      "Drop small stones onto the patches with tweezers, leaving gaps between them.",
      "Let it dry fully and shake off anything loose before painting.",
    ],
    paintSteps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a dark grey-brown", hex: "#5a5248", note: "Paint the stones and the ground between them in one go." },
      { technique: "Wash", coats: 1, mix: 30, look: "a dark brown", hex: "#3a2e24", note: "Thin it so it runs into the gaps between the stones." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a light grey-brown", hex: "#9a9082", note: "Wipe most of the paint off the brush first." },
      { technique: "Edge highlight", coats: 1, mix: 100, look: "a pale warm grey", hex: "#c9c0b0", note: "Pick out the tops of the biggest stones only." },
    ] },
  { key: "cracked", group: "ground", name: "Cracked earth", summary: "Dry ground split into flat plates",
    materials: ["Air-drying modelling clay, or a thick paste filler", "A blunt tool such as a cocktail stick", "Water", "An old brush"],
    howto: [
      "Press a thin layer of clay onto the base and smooth it with a damp finger.",
      "Cut thin, wandering cracks into it with the tool while it is soft, and do not make them all the same width.",
      "Press the tool in deeper where two cracks meet.",
      "Let it dry fully, for a day or more, before painting.",
    ],
    paintSteps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a dull orange-brown", hex: "#8b6a4a", note: "Get paint right down into the cracks." },
      { technique: "Wash", coats: 1, mix: 30, look: "a dark brown", hex: "#3f2f22", note: "Let it pool in the cracks so they look deep." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a pale dusty tan", hex: "#bda884", note: "Brush across the plates and keep the cracks dark." },
      { technique: "Edge highlight", coats: 1, mix: 100, look: "a light cream", hex: "#dccfae", note: "Only the edges of the plates." },
    ] },
  { key: "ash", group: "ground", name: "Ash and soot", summary: "Burnt grey ground with a layer of pale dust",
    materials: ["Fine sand", "White glue that dries clear", "Soft grey chalk, scraped into powder", "A soft old brush"],
    howto: [
      "Glue fine sand over the base with white glue and let it dry.",
      "Paint it using the paint steps below.",
      "Scrape a little soft grey chalk into powder, and do not breathe in the dust.",
      "Brush the powder over the dry paint with a soft brush, with more in the hollows.",
    ],
    paintSteps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a near-black grey", hex: "#2a2a2c", note: "Aim for an even, flat dark coat." },
      { technique: "Wash", coats: 1, mix: 30, look: "a thin brown-black", hex: "#3a2f2a", note: "Use it around any patches that should look burnt." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a dark grey", hex: "#55555a", note: "Wipe most of the paint off the brush first." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a light grey", hex: "#9a9a9c", note: "Keep it light, as if the ash is lying on top." },
    ] },

  // ---------- Wet and cold ----------
  { key: "mud", group: "cold", name: "Mud", summary: "Thick, wet mud with a shiny top",
    materials: ["Fine sand", "White glue that dries clear", "Dark brown paint", "Clear gloss varnish", "A cocktail stick", "An old brush"],
    howto: [
      "Mix fine sand into white glue until it makes a thick paste.",
      "Stir in a few drops of dark brown paint so the mix dries dark.",
      "Spread it onto the base with the cocktail stick, leaving ridges and dips.",
      "Press a boot print or a wheel line into it while it is wet, if you like.",
      "Let it dry fully, then brush gloss varnish into the wet-looking dips only.",
    ],
    paintSteps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a dark brown", hex: "#3b2b1e", note: "Cover the whole patch, including the dips." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a mid brown", hex: "#6b5239", note: "Catch the ridges and leave the dips dark." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a light dusty brown", hex: "#9a825f", note: "Keep it on the highest ridges." },
      { technique: "Glaze", coats: 1, mix: 25, look: "a very dark brown", hex: "#2a1d14", note: "Brush it into the dips, then add gloss varnish on top for a wet look." },
    ] },
  { key: "snow", group: "cold", name: "Snow", summary: "Soft, fresh snow with cool blue shadows",
    materials: ["White glue that dries clear", "Baking soda", "Water", "An old brush"],
    howto: [
      "Mix white glue and baking soda into a thick paste, adding the powder a little at a time.",
      "Dab the paste onto the base with an old brush, making soft, uneven drifts.",
      "Sprinkle a little extra baking soda on top for a powdery look.",
      "Let it dry fully before painting, since the paste shrinks as it dries.",
    ],
    paintSteps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a pale cool grey", hex: "#cfd6dd", note: "Thin coats work better than one thick coat." },
      { technique: "Wash", coats: 1, mix: 30, look: "a pale blue", hex: "#7d97b8", note: "Run it into the low spots and under any overhangs." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a near-white", hex: "#f3f6f8", note: "Very light touches on the tops of the drifts." },
      { technique: "Stipple", coats: 1, mix: 100, look: "a bright white", hex: "#ffffff", note: "Dot it on the very highest points for sparkle." },
    ] },
  { key: "ice", group: "cold", name: "Ice", summary: "Clear, cold ice with pale edges",
    materials: ["Thin clear plastic from packaging", "Scissors", "Clear glue that dries glossy", "White glue that dries clear", "A cocktail stick"],
    howto: [
      "Cut small shards from thin clear plastic with scissors, taking care with the sharp edges.",
      "Glue them in clusters pointing up and out, in different sizes.",
      "Brush clear glue over the base around them for a flat, wet-looking sheet of ice.",
      "Let it dry fully, and the glue will go clear.",
    ],
    paintSteps: [
      { technique: "Glaze", coats: 1, mix: 25, look: "a deep blue", hex: "#2f5f8f", note: "A little at the base of each shard, where the ice is thickest." },
      { technique: "Glaze", coats: 1, mix: 25, look: "a pale blue", hex: "#8fb4d6", note: "Brush it up the shard and fade it out, and never cover the whole piece." },
      { technique: "Edge highlight", coats: 1, mix: 100, look: "a bright white", hex: "#f5f9fc", note: "Thin lines on the sharp edges." },
    ] },

  // ---------- Plants ----------
  { key: "grass", group: "plants", name: "Grass", summary: "Short green grass with dry tips",
    materials: ["Grass fibres, sold for model landscapes", "White glue that dries clear", "Fine sand", "An old brush", "A small sieve"],
    howto: [
      "Glue and sand the base first, then paint it with the paint steps below.",
      "Brush thin white glue over the areas where grass should grow.",
      "Sprinkle grass fibres thickly over the glue through the sieve.",
      "Press them down lightly, then tip off the extra and let it dry.",
      "Brush it gently once dry so the fibres stand up.",
    ],
    paintSteps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a dark olive green", hex: "#3d4a26", note: "Paint the ground before the fibres go on so no bare patches show." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a mid green", hex: "#6a8040", note: "Use it on painted ground or on fibres that came out too dark." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a light yellow-green", hex: "#a3b565", note: "Light touches on the tips." },
      { technique: "Stipple", coats: 1, mix: 100, look: "a dry straw yellow", hex: "#c8b676", note: "Dab on a few dry tips for variety." },
    ] },
  { key: "moss", group: "plants", name: "Moss", summary: "Damp, soft moss on stone and earth",
    materials: ["A dry sponge", "White glue that dries clear", "Tweezers", "An old brush"],
    howto: [
      "Tear a dry sponge into tiny uneven clumps, with no straight edges.",
      "Dab a small spot of white glue where the moss should grow.",
      "Press a clump on with tweezers, and group them in damp corners and cracks.",
      "Let the glue dry fully, then paint the clumps.",
    ],
    paintSteps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a dark green", hex: "#2b3a22", note: "Dab it into the holes of the sponge." },
      { technique: "Wash", coats: 1, mix: 30, look: "a deep green", hex: "#1f3320", note: "Dab it into the shadowed gaps between clumps." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a mid green", hex: "#52703a", note: "Brush across the tops of the clumps." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a bright yellow-green", hex: "#8fb04e", note: "Only on the highest points." },
    ] },

  // ---------- Stone and fire ----------
  { key: "rock", group: "stone", name: "Rock", summary: "Rough grey rock with sharp, lit edges",
    materials: ["Cork bark or a rough piece of cork", "White glue that dries clear", "Fine sand", "An old brush", "Tweezers"],
    howto: [
      "Break the cork into rough chunks with your hands, so each has flat and angled faces.",
      "Glue the chunks to the base in layers, with the bigger pieces at the back.",
      "Fill the gaps with a mix of glue and fine sand.",
      "Let it dry fully before painting.",
    ],
    paintSteps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a dark grey", hex: "#4a4a4e", note: "Cover every face and get into the cracks." },
      { technique: "Wash", coats: 1, mix: 30, look: "a dark blue-grey", hex: "#2f3340", note: "Let it run into every crack." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a mid grey", hex: "#85858a", note: "Wipe most of the paint off the brush first." },
      { technique: "Edge highlight", coats: 1, mix: 100, look: "a pale grey", hex: "#c4c4c4", note: "Only the edges that face upwards." },
    ] },
  { key: "rubble", group: "stone", name: "Rubble", summary: "Broken stones and dusty bits of old wall",
    materials: ["Small broken stones or crumbled cork", "Fine sand", "White glue that dries clear", "Tweezers", "Thin card, torn into splinters"],
    howto: [
      "Glue fine sand over the base and let it dry.",
      "Glue bigger stones on in piles, tipped at different angles.",
      "Add smaller bits on top and around them, with some sand on the slopes of each pile.",
      "Lay one or two card splinters across a pile as broken beams.",
      "Let it dry fully before painting.",
    ],
    paintSteps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a dark warm grey", hex: "#54504b", note: "Paint the stones and the sand in one go." },
      { technique: "Wash", coats: 1, mix: 30, look: "a dark brown", hex: "#35291f", note: "Thin it so it settles between the stones." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a light stone grey", hex: "#a29d94", note: "Wipe most of the paint off the brush first." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a pale dusty grey", hex: "#cdc7bb", note: "Keep it on the sharp top edges, like dust." },
    ] },
  { key: "lava", group: "stone", name: "Lava", summary: "Dark crust with a hot orange glow in the cracks",
    materials: ["Air-drying modelling clay, or white glue mixed with fine sand", "A blunt tool such as a cocktail stick", "An old brush", "A fine brush"],
    howto: [
      "Build the crust from a thick, uneven layer of clay, or glue and sand.",
      "Press wide, wandering cracks into it with the tool, and keep the cracks joined up.",
      "Add a few thick bumps of cooled crust between the cracks.",
      "Let it dry fully before painting.",
    ],
    paintSteps: [
      { technique: "Base coat", coats: 2, mix: 100, look: "a near-black brown", hex: "#1d1715", note: "Cover the crust and the cracks." },
      { technique: "Layer", coats: 1, mix: 100, look: "a deep red", hex: "#8f1f12", note: "Paint into the cracks only, with a fine brush." },
      { technique: "Layer", coats: 1, mix: 100, look: "a bright orange", hex: "#e8661b", note: "Narrower, down the middle of each crack." },
      { technique: "Edge highlight", coats: 1, mix: 100, look: "a bright yellow", hex: "#ffd04a", note: "A thin line or dots at the hottest points." },
      { technique: "Dry brush", coats: 1, mix: 100, look: "a dark grey", hex: "#4a4442", note: "Lightly over the crust to show its texture." },
    ] },
];
