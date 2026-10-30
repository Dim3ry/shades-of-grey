// ===== guides-data.js: the Guides library's new kinds of entry (plain data) =====
// This file is only data. It draws nothing, talks to nothing and stores nothing. app.js reads it through knowledgeIndex().
//
// How it is shared: it is loaded as a plain script just before app.js (after mentor-tips.js), so the names below
// (GUIDE_ENTRIES and GUIDE_STARTERS) are there when app.js starts.
//
// Where the entries come from: the knowledge base written from knowledge-base/SCHEMA.md and merged by a later chunk (X8). Both lists are
// empty until then. Do not invent entries here.
//
// The shape of an entry is in knowledge-base/SCHEMA.md:
//  - GUIDE_ENTRIES: { key, category (colour-basics, techniques, tools-prep or problems), title, summary, body (list of text), related (list of keys),
//    keywords (list of text), credit (optional: { name, url }) }
//  - GUIDE_STARTERS: { key, text (the question), targets (list of keys) }
//  Shown as plain text only (app.js uses textContent), but keep it free of angle brackets anyway.

const GUIDE_ENTRIES = [];

const GUIDE_STARTERS = [];
