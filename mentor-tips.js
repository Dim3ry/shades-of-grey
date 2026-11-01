// ===== mentor-tips.js: the Mentor tips library (plain data) =====
// This file is only data. It draws nothing, talks to nothing and stores nothing. app.js reads it through mentorTipsFor().
//
// How it is shared: it is loaded as a plain script just before app.js (after basing-tips.js), so the names below
// (MENTOR_PARTS, MENTOR_TECHNIQUES and MENTOR_TIPS) are there when app.js starts.
//
// Where tips come from: George's own notes, nothing else. Do not invent tips. The list below is empty until George's notes arrive.
//
// Rules for anything written here (a test checks the text):
//  - Our own words. A tip that draws on a creator carries a credit (name and link); never copy a creator's wording.
//  - No Games Workshop names, faction names, scheme names, artwork or logos, and no em dashes.
//  - Each tip has: key (a short unique id), part (one of MENTOR_PARTS), colour (a plain colour word or two), technique (free
//    text; MENTOR_TECHNIQUES is the short list of usual ones), advice (the tip itself, plain sentences), colours (suggested
//    colours: each a plain look and a hex, never a paint name) and credit (optional: { name, url }, or left out).
//  - A sample tip also has sample: true. Real tips leave it out.
//  - Shown as plain text only (app.js uses textContent), but keep it free of angle brackets anyway.

// The parts of a model a tip can be about. The keys are the only values allowed in a tip's part.
const MENTOR_PARTS = [
  { key: "armour", name: "Armour" },
  { key: "eyes", name: "Eyes" },
  { key: "weapon", name: "Weapon" },
  { key: "base", name: "Base" },
];

// The usual technique words. A tip's technique is free text, this is only the short list to reach for first.
const MENTOR_TECHNIQUES = ["Base coat", "Layer", "Shade", "Wash", "Glaze", "Drybrush", "Edge highlight", "Blend"];

const MENTOR_TIPS = [
];
