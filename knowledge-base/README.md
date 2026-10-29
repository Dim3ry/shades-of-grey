# Minifolio knowledge base: brief for the builder

Minifolio is a hobby tracker for miniature painters. The knowledge base is the data behind two things:

- **Guides**: a section people can browse.
- **Mentor**: a pop-up helper that answers painting questions and links to the entries it used.

No AI model and no server run in the app. Mentor matches what a person types to the entries. So every entry has a fixed ID and a list of plain-word keywords.

You are writing data only. **Do not change any app code.** Nothing in this folder is loaded by the app. Claude Code wires your data in later.

## Hard rules (the checker enforces these)

1. **Own words**, from general painting and modelling knowledge. Never copy or closely paraphrase a creator, a book, a rulebook or a website. If an idea clearly comes from one creator, add a credit (name and link) and still write it fresh. If unsure, leave it out.
2. **No Games Workshop words** and no army, faction, character, unit, scheme or paint-range names. Describe the thing, not the product ("a dark red", not a paint name). No brand names or product names. The checker also rejects the words "shop", "buy" and "store", so write "keep paint in a cool place" and not "store paint".
3. **No em dashes, no emoji, no angle brackets** (the < and > signs).
4. **Plain short sentences.** No filler. Mature and practical.
5. **Colours** are a plain colour word plus a hex code ("a deep blue", #1f3a66). Never a paint name: the app finds the nearest real paint itself.
6. **Every ID** is unique, lower case, words joined by dashes, and never changes once released.

## The files

`SCHEMA.md` lists every field, allowed value and limit for each kind of entry. Read it first.

There are five kinds:

| Kind | What it is | Format |
|---|---|---|
| `guides` | Guide entries (new) | in SCHEMA.md |
| `starters` | Starter questions (new) | in SCHEMA.md |
| `mentor-tips` | Mentor tips by situation | same as the app's `mentor-tips.js` |
| `detail-recipes` | Detail recipes | same as the app's `detail-recipes.js` |
| `basing-tips` | Basing tips | same as the app's `basing-tips.js` |

Look at `samples/sample-entries.json` to see the shape. Every sample is marked SAMPLE. Do not copy sample wording into real entries.

Put your work in one JSON file per chunk, in a new folder `knowledge-base/data/`, for example `knowledge-base/data/k1-colour-basics.json`. A file is an object whose keys are kinds:

```json
{ "guides": [ { "key": "...", "...": "..." } ] }
```

To add to the 18 detail recipes or 12 basing tips that exist today, write only your new entries in your own file, using the same fields. Do not edit `detail-recipes.js` or `basing-tips.js`. (Their top comments are the format rules. SCHEMA.md repeats them.)

## The chunks

One branch and one pull request per chunk. K1 to K7 can run in parallel.

- **K1** colour basics: about 30 guide entries. Warm and cool, value, strength, harmonies, what goes with each common base colour.
- **K2** techniques: about 24 guide entries. Base coat, layering, glazing, wet blending, drybrushing, edge highlights, washes, stippling, feathering, light-source effects.
- **K3** detail recipes: add about 8 to the existing ones.
- **K4** basing: add about 8 to the existing ones.
- **K5** tools, prep and problems: about 25 guide entries. Brushes, thinning, palettes, priming, mould lines, streaky or chalky paint, pooling, rubbed-off paint, varnish.
- **K6** Mentor tips by situation: part (armour, eyes, weapon, base) by about 12 base colours, about 48 tips. They replace the three samples.
- **K7** Mentor matching data: keywords for every entry, 20 starter questions, and common beginner questions mapped to entries.
- **K8** review pass by someone fresh. Then the owner adds his own notes.

Start with ten entries and send them to the owner for a tone check before doing the rest.

## Running the checker

You need Python 3 and nothing else. From the repo folder:

```
python3 knowledge-base/check_knowledge.py knowledge-base/data/k1-colour-basics.json
```

It prints each problem in plain words and ends with CLEAN or NOT CLEAN. Exit code 0 means clean.

- `--partial`: use this while you work. A `related` or `targets` key that points at an entry in a chunk nobody has written yet is then only a note.
- `--final`: use this before you hand back. It also fails on any entry marked as a sample.
- Give it several files to check them together. Duplicate IDs and links are checked across all the files you give it.

To see what the app's own data looks like to the checker:

```
python3 knowledge-base/check_knowledge.py detail-recipes.js basing-tips.js mentor-tips.js
```

The checker also reads those three app files, so your new IDs can be checked against the existing ones.

## What to hand back

A pull request against the app repo per chunk with only that chunk's data file(s), the checker passing, and a short note of anything you are unsure about (a fact, a credit, a word that might be a brand). The owner reviews and merges. Claude Code wires the data into the app later. Do not change app code.

## How Mentor will use it

A person types something like "what colour for green armour eyes?" or taps a starter question. Mentor scores entries by keywords, title and summary, then shows the best two or three, with Sources links that open the exact entry or the colour wheel. So:

- Put the words a beginner would actually type in `keywords`. Include common wrong names ("thinners", "washing", "highlighting").
- Keep each summary to one clear line.
- Keep each entry about one thing.

## Suggested way to work

Claude Code, strongest model, high effort, one chunk per session.
