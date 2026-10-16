// ===== colour.js: the colour maths for "colour coaching" (Coach 1, the engine) =====
// Nothing in here draws anything or talks to the internet. It is just sums.
// The app can call these helpers to answer questions like:
//   - "What are the opposite and neighbouring colours of this paint?"   -> harmonies()
//   - "Which paint in the catalogue is closest to this colour?"          -> nearestPaints()
//   - "Do the colours of this recipe hang together?"                     -> schemeCheck()
// The "Colour ideas" panel in the recipe editor uses all of these.
//
// How it is shared: the app loads this file as a plain script, which adds ONE name to the page,
// MinifolioColour. The test file loads the very same file in Node and checks the answers.
//
// Colours are always written "#rrggbb" (six hex digits), like the rest of the app.
(function (root) {
  "use strict";

  const DEFAULT_GREY = "#808080";   // the app's "colour not known yet" grey (DEFAULT_PAINT_COLOUR in app.js)

  // ---------- reading and writing colours ----------

  const isHex = (v) => typeof v === "string" && /^#[0-9a-f]{6}$/i.test(v);

  // "#1e3a8a" -> [30, 58, 138] (red, green, blue, each 0-255). Returns null for anything that isn't a colour.
  function hexToRgb(hex) {
    if (!isHex(hex)) return null;
    return [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
  }

  function rgbToHex(r, g, b) {
    const part = (n) => Math.max(0, Math.min(255, Math.round(n))).toString(16).padStart(2, "0");
    return "#" + part(r) + part(g) + part(b);
  }

  // Colour -> hue (0-360, round the colour wheel: 0 red, 120 green, 240 blue),
  // saturation (0 = grey, 1 = fully vivid) and lightness (0 = black, 1 = white).
  function hexToHsl(hex) {
    const rgb = hexToRgb(hex);
    if (!rgb) return null;
    const [r, g, b] = rgb.map((n) => n / 255);
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    const l = (max + min) / 2;
    if (max === min) return { h: 0, s: 0, l };
    const d = max - min;
    const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    let h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
    return { h: h * 60, s, l };
  }

  // The opposite of hexToHsl.
  function hslToHex(h, s, l) {
    h = ((h % 360) + 360) % 360;
    s = Math.max(0, Math.min(1, s));
    l = Math.max(0, Math.min(1, l));
    const c = (1 - Math.abs(2 * l - 1)) * s;
    const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
    const m = l - c / 2;
    const [r, g, b] = h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x]
      : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x];
    return rgbToHex((r + m) * 255, (g + m) * 255, (b + m) * 255);
  }

  // ---------- "how different do these two colours look?" ----------
  // Two colours with numbers that are close in red/green/blue can still look quite different to
  // an eye. So we convert to "Lab" (a scale built to match how people see) and measure there,
  // using the standard CIEDE2000 formula. A result of 0 means identical; about 1 is the smallest
  // difference you could notice; about 10 is clearly a different shade; 25+ is a different colour.

  function hexToLab(hex) {
    const rgb = hexToRgb(hex);
    if (!rgb) return null;
    const lin = rgb.map((n) => {
      const c = n / 255;
      return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    });
    const [r, g, b] = lin;
    // sRGB -> XYZ (D65 white), then scaled by the white point
    const x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047;
    const y = (0.2126729 * r + 0.7151522 * g + 0.0721750 * b) / 1.0;
    const z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883;
    const f = (t) => (t > 216 / 24389 ? Math.cbrt(t) : (24389 / 27 * t + 16) / 116);
    const fx = f(x), fy = f(y), fz = f(z);
    return { L: 116 * fy - 16, a: 500 * (fx - fy), b: 200 * (fy - fz) };
  }

  const rad = (deg) => (deg * Math.PI) / 180;
  const deg = (r) => (r * 180) / Math.PI;

  // CIEDE2000, written out as published (Sharma, Wu and Dalal, 2005).
  function labDistance(p, q) {
    const avgL = (p.L + q.L) / 2;
    const c1 = Math.hypot(p.a, p.b), c2 = Math.hypot(q.a, q.b);
    const avgC = (c1 + c2) / 2;
    const g = 0.5 * (1 - Math.sqrt(Math.pow(avgC, 7) / (Math.pow(avgC, 7) + Math.pow(25, 7))));
    const a1 = (1 + g) * p.a, a2 = (1 + g) * q.a;
    const C1 = Math.hypot(a1, p.b), C2 = Math.hypot(a2, q.b);
    const hue = (b, a) => {
      if (b === 0 && a === 0) return 0;
      const h = deg(Math.atan2(b, a));
      return h < 0 ? h + 360 : h;
    };
    const h1 = hue(p.b, a1), h2 = hue(q.b, a2);
    const dL = q.L - p.L, dC = C2 - C1;
    let dh = 0;
    if (C1 * C2 !== 0) {
      dh = h2 - h1;
      if (dh > 180) dh -= 360; else if (dh < -180) dh += 360;
    }
    const dH = 2 * Math.sqrt(C1 * C2) * Math.sin(rad(dh / 2));
    const avgCp = (C1 + C2) / 2;
    let avgH;
    if (C1 * C2 === 0) avgH = h1 + h2;
    else if (Math.abs(h1 - h2) <= 180) avgH = (h1 + h2) / 2;
    else avgH = h1 + h2 < 360 ? (h1 + h2 + 360) / 2 : (h1 + h2 - 360) / 2;
    const T = 1 - 0.17 * Math.cos(rad(avgH - 30)) + 0.24 * Math.cos(rad(2 * avgH))
      + 0.32 * Math.cos(rad(3 * avgH + 6)) - 0.20 * Math.cos(rad(4 * avgH - 63));
    const dTheta = 30 * Math.exp(-Math.pow((avgH - 275) / 25, 2));
    const Rc = 2 * Math.sqrt(Math.pow(avgCp, 7) / (Math.pow(avgCp, 7) + Math.pow(25, 7)));
    const Sl = 1 + (0.015 * Math.pow(avgL - 50, 2)) / Math.sqrt(20 + Math.pow(avgL - 50, 2));
    const Sc = 1 + 0.045 * avgCp;
    const Sh = 1 + 0.015 * avgCp * T;
    const Rt = -Math.sin(rad(2 * dTheta)) * Rc;
    return Math.sqrt(Math.pow(dL / Sl, 2) + Math.pow(dC / Sc, 2) + Math.pow(dH / Sh, 2)
      + Rt * (dC / Sc) * (dH / Sh));
  }

  // Difference between two "#rrggbb" colours. Returns null if either isn't a colour.
  function colourDistance(hexA, hexB) {
    const p = hexToLab(hexA), q = hexToLab(hexB);
    return p && q ? labDistance(p, q) : null;
  }

  // ---------- harmonies: colours that go well with a base colour ----------
  // These come from rotating round the colour wheel (the "hue" number above):
  //   opposite (complementary): straight across the wheel, 180 degrees. Blue <-> orange.
  //   neighbours (analogous):   30 degrees either side. Calm, blends in.
  //   split-opposite:           150 and 210 degrees. Contrast, but gentler than the straight opposite.
  //   triad:                    120 and 240 degrees. Three evenly spaced, lively.
  // The new colours keep the base colour's saturation and lightness, so they feel like the same family.
  // (This is the computer's colour wheel, not the painter's red-yellow-blue one. They agree on the
  // main pairs people know: blue/orange, red/green, yellow/purple.)
  //
  // Neutrals are the "safe" choices: a near-black, a mid grey and an off-white, each tinted ever so
  // slightly towards the base colour so they sit comfortably beside it rather than looking dead.
  //
  // If the base is almost grey (or almost black or white) its hue means very little, so
  // hueMeaningful is false. The panel can then say "this colour is neutral, so anything goes".

  const GREY_BELOW = 0.12;    // saturation under this: the hue is too faint to trust
  const EDGE_BELOW = 0.06;    // lightness under this (near black) or over 1 minus this (near white): same

  function harmonies(hex) {
    const base = hexToHsl(hex);
    if (!base) return null;
    const { h, s, l } = base;
    const turn = (d) => hslToHex(h + d, s, l);
    const tint = Math.min(s, 0.15);   // a hint of the base hue, never a strong colour
    return {
      base: hex.toLowerCase(),
      hueMeaningful: s >= GREY_BELOW && l >= EDGE_BELOW && l <= 1 - EDGE_BELOW,
      hue: h,
      complementary: turn(180),
      analogous: [turn(-30), turn(30)],
      split: [turn(150), turn(210)],
      triad: [turn(120), turn(240)],
      neutrals: [hslToHex(h, tint, 0.10), hslToHex(h, tint, 0.50), hslToHex(h, tint, 0.92)],
    };
  }

  // A plain-English name for where a colour sits. Handy for the "why" sentences in Coach 2.
  // Returns things like "blue", "dark red", "pale yellow", "grey", "near-black", "near-white".
  function colourFamily(hex) {
    const c = hexToHsl(hex);
    if (!c) return null;
    if (c.l < EDGE_BELOW) return "near-black";
    if (c.l > 1 - EDGE_BELOW) return "near-white";
    if (c.s < GREY_BELOW) return c.l < 0.3 ? "dark grey" : c.l > 0.7 ? "light grey" : "grey";
    const h = c.h;
    const name = h < 15 || h >= 345 ? "red" : h < 45 ? "orange" : h < 65 ? "yellow" : h < 95 ? "lime"
      : h < 165 ? "green" : h < 195 ? "teal" : h < 255 ? "blue" : h < 290 ? "purple"
      : h < 345 ? "pink" : "red";
    // brown is dark/muted orange or yellow; it's worth its own word for painters
    if ((name === "orange" || name === "yellow") && c.l < 0.4) return "brown";
    if (c.l < 0.32) return "dark " + name;
    if (c.l > 0.75) return "pale " + name;
    return name;
  }

  // ---------- nearest paint ----------
  // Paints in the app look like { brand, name, colour: "#rrggbb", type?, status?, owned? }.
  // "Have it" matches the app: status Owned or Running low, or the older owned: true.
  function haveIt(paint) {
    if (!paint) return false;
    if (paint.status === "owned" || paint.status === "low") return true;
    const known = ["owned", "low", "empty", "wishlist", "notowned"];
    return !known.includes(paint.status) && paint.owned === true;
  }

  // Some paints have colours that are only a rough guide: metallics shine, Contrast and Speedpaint
  // paints go on translucent, washes and inks stain. The colour in the list is what they look like
  // in the pot, which is not what you see on the model. So their matches are "close enough" only.
  const ROUGH_TYPES = /^(contrast|speedpaint|metallic|wash|shade|ink|glaze|technical)$/i;
  const ROUGH_NAMES = /\b(metallic|metal|contrast|speedpaint|xpress|express|wash|shade|ink|glaze|gold|silver|bronze|copper|brass|steel|iron|chrome|medium)\b/i;
  function isRoughColour(paint) {
    if (!paint) return false;
    if (typeof paint.type === "string" && ROUGH_TYPES.test(paint.type)) return true;
    return typeof paint.name === "string" && ROUGH_NAMES.test(paint.name);
  }

  // Basing materials, and paints still on the untouched grey (colour unknown), can't be matched.
  function canMatch(paint) {
    return !!paint && isHex(paint.colour) && paint.colour.toLowerCase() !== DEFAULT_GREY
      && paint.type !== "material";
  }

  // How good is a match? From the CIEDE2000 distance (see above):
  //   "good"  - hard to tell apart (up to 6)
  //   "close" - same colour family, slightly different shade (up to 15)
  //   "poor"  - a different colour; show it with a warning, or say there is nothing close
  // For rough paints (see above) each step is looser by a third, and the match is flagged
  // "approximate" so the screen can say "close enough" rather than "exact".
  // confidence is a number from 0 (hopeless) to 1 (identical) the screen can turn into words.
  const GOOD_UNDER = 6, CLOSE_UNDER = 15, FAR_AT = 40;
  function judgeMatch(distance, rough) {
    const stretch = rough ? 4 / 3 : 1;
    const quality = distance <= GOOD_UNDER * stretch ? "good" : distance <= CLOSE_UNDER * stretch ? "close" : "poor";
    const confidence = Math.max(0, 1 - distance / (FAR_AT * stretch));
    return { quality, approximate: !!rough, confidence: Math.round(confidence * 100) / 100 };
  }

  // Finds the paints closest to a wanted colour.
  //   wanted: "#rrggbb"
  //   paints: a list of paints (the catalogue, or the catalogue plus the user's own)
  //   options.limit:      how many to return (default 3)
  //   options.ownedFirst: true (default) puts paints the user has ahead of ones they'd have to buy,
  //                       each group in order of closeness. false mixes them, purely by closeness.
  //   options.exclude:    a list of "#rrggbb" colours to skip (paints already used in the recipe)
  // Each result: { paint, distance, owned, quality, approximate, confidence }
  // Never throws; a bad colour or list gives an empty list.
  function nearestPaints(wanted, paints, options) {
    const opts = options || {};
    const limit = Number.isInteger(opts.limit) && opts.limit > 0 ? opts.limit : 3;
    const ownedFirst = opts.ownedFirst !== false;
    const skip = new Set((Array.isArray(opts.exclude) ? opts.exclude : []).filter(isHex).map((c) => c.toLowerCase()));
    const target = hexToLab(wanted);
    if (!target || !Array.isArray(paints)) return [];
    const seen = new Set();
    const scored = [];
    for (const paint of paints) {
      if (!canMatch(paint)) continue;
      const colour = paint.colour.toLowerCase();
      if (skip.has(colour)) continue;
      // The same paint can appear twice (built-in list plus the user's copy). Keep one, preferring the owned copy.
      const key = (paint.brand || "") + "|" + (paint.name || "").toLowerCase();
      const distance = labDistance(target, hexToLab(colour));
      const entry = Object.assign({ paint, distance, owned: haveIt(paint) },
        judgeMatch(distance, isRoughColour(paint)));
      if (seen.has(key)) {
        const at = scored.findIndex((e) => (e.paint.brand || "") + "|" + (e.paint.name || "").toLowerCase() === key);
        if (at >= 0 && entry.owned && !scored[at].owned) scored[at] = entry;
        continue;
      }
      seen.add(key);
      scored.push(entry);
    }
    scored.sort((x, y) => {
      if (ownedFirst && x.owned !== y.owned) return x.owned ? -1 : 1;
      return x.distance - y.distance || String(x.paint.name).localeCompare(String(y.paint.name));
    });
    return scored.slice(0, limit);
  }

  // Convenience: the single closest paint the user owns (or null), and the closest of all.
  function closestOwned(wanted, paints) {
    return nearestPaints(wanted, (paints || []).filter(haveIt), { limit: 1 })[0] || null;
  }
  function closestAny(wanted, paints) {
    return nearestPaints(wanted, paints, { limit: 1, ownedFirst: false })[0] || null;
  }

  // ---------- does a scheme hang together? (Coach 3) ----------
  // Looks at the colours of one recipe and answers three plain questions. It hands back numbers and
  // colours only; the screen chooses the words. It is a rule of thumb, not a verdict.
  //   1. How many STRONG colours are there? Strong means clearly coloured (not grey, not brown), and not
  //      so dark or so pale that it fades into the background. Colours whose hues are within 20 degrees
  //      of each other on the colour wheel count as ONE, so a base, shade and highlight of the same red is one red.
  //      Painters' guides say one or two colours should lead and the rest support. Past 3 strong
  //      colours they start to fight each other.
  //   2. Is there light and dark? Compare the lightest and darkest colour (the Lab "L" number, 0 black
  //      to 100 white). Less than 30 apart and the model can look flat.
  //   3. Which strong colour should be the focus? The one that stands out most against the main colour
  //      (the strong colour used in the most steps, or the one listed first on a tie): the furthest
  //      round the colour wheel from it.
  //      If there is only one strong colour it is the focus already.
  const STRONG_SATURATION = 0.45;         // colourful enough (0 grey to 1 pure colour)
  const STRONG_LIGHTNESS = [0.15, 0.8];   // not almost black, not almost white
  const SAME_COLOUR_WITHIN = 20;          // hues this close (degrees) count as the same colour
  const MAX_STRONG = 3;                   // more than this many strong colours is too many
  const FLAT_UNDER = 30;                  // lightest and darkest less than this far apart is "flat"

  function isStrongColour(hex) {
    const c = hexToHsl(hex);
    if (!c || colourFamily(hex) === "brown") return false;
    return c.s >= STRONG_SATURATION && c.s >= GREY_BELOW && c.l >= STRONG_LIGHTNESS[0] && c.l <= STRONG_LIGHTNESS[1];
  }

  const hueGap = (a, b) => { const d = Math.abs(a - b) % 360; return Math.min(d, 360 - d); };

  // entries: [{ colour: "#rrggbb", uses: how many steps use it }]. Anything that isn't a colour, and the
  // untouched grey, is ignored. Never throws.
  function schemeCheck(entries) {
    const byHex = new Map();
    for (const e of Array.isArray(entries) ? entries : []) {
      if (!e || !isHex(e.colour) || e.colour.toLowerCase() === DEFAULT_GREY) continue;
      const hex = e.colour.toLowerCase();
      const uses = Number.isFinite(e.uses) && e.uses > 0 ? e.uses : 1;
      byHex.set(hex, (byHex.get(hex) || 0) + uses);
    }
    const colours = [...byHex].map(([hex, uses]) => ({ hex, uses, L: hexToLab(hex).L }));

    // 1. strong colours, merged when their hues are close
    // Most-used first. On a tie the colour listed first wins (a recipe usually starts with its main colour).
    const strong = colours.filter((c) => isStrongColour(c.hex)).map((c) => Object.assign({ hsl: hexToHsl(c.hex) }, c))
      .sort((a, b) => b.uses - a.uses);
    const groups = [];
    for (const c of strong) {
      const group = groups.find((g) => hueGap(g.hsl.h, c.hsl.h) <= SAME_COLOUR_WITHIN);
      if (group) group.uses += c.uses; else groups.push({ hex: c.hex, hsl: c.hsl, uses: c.uses });
    }
    groups.sort((a, b) => b.uses - a.uses);   // a stable sort: ties keep the order the colours were listed in
    const shape = (g) => ({ hex: g.hex, family: colourFamily(g.hex), uses: g.uses });

    // 3. the focus colour
    let focus = null, focusKind = "none";
    if (groups.length === 1) { focus = groups[0]; focusKind = "only"; }
    else if (groups.length > 1) {
      focus = groups.slice(1).sort((a, b) => hueGap(b.hsl.h, groups[0].hsl.h) - hueGap(a.hsl.h, groups[0].hsl.h) || b.hsl.s - a.hsl.s)[0];
      focusKind = "accent";
    }

    // 2. light and dark
    const enough = colours.length >= 2;
    const byLight = colours.slice().sort((a, b) => a.L - b.L);
    const darkest = byLight[0] || null, lightest = byLight[byLight.length - 1] || null;
    const lightRange = enough ? lightest.L - darkest.L : 0;
    const tooManyStrong = groups.length > MAX_STRONG;
    const flat = enough && lightRange < FLAT_UNDER;
    return {
      enough,
      colourCount: colours.length,
      strong: groups.map(shape),
      tooManyStrong,
      dominant: groups[0] ? shape(groups[0]) : null,
      focus: focus ? shape(focus) : null,
      focusKind,
      darkest: darkest && { hex: darkest.hex, L: Math.round(darkest.L * 10) / 10 },
      lightest: lightest && { hex: lightest.hex, L: Math.round(lightest.L * 10) / 10 },
      lightRange: Math.round(lightRange * 10) / 10,
      flat,
      hangsTogether: enough && !tooManyStrong && !flat,
    };
  }

  const api = {
    isHex, hexToRgb, rgbToHex, hexToHsl, hslToHex, hexToLab,
    labDistance, colourDistance, harmonies, colourFamily,
    haveIt, isRoughColour, canMatch, judgeMatch,
    nearestPaints, closestOwned, closestAny,
    isStrongColour, schemeCheck,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.MinifolioColour = api;
})(typeof window !== "undefined" ? window : globalThis);
