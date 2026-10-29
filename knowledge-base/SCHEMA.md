# Knowledge base schema

The exact fields, allowed values and limits. `check_knowledge.py` enforces everything here. A field not listed is not allowed. A limit written "3 to 8" includes both ends. Lengths count characters.

## IDs (the `key` field)

- Lower case letters and digits, words joined by single dashes: `warm-and-cool`, `thin-your-paint`.
- 2 to 50 characters.
- **Unique across all kinds.** A guide and a starter question cannot share an ID. (One old pair already shares `mud`: a detail recipe and a basing tip. That pair is the only exception. Do not add more.)
- Never changed once released. Other entries, starter questions and saved links point at it. To retire an entry, tell the owner. Do not rename it.
- Make them describe the content. Do not number them.

## File shape

A JSON file. The top-level keys are kinds, each holding a list. A file can hold one kind or several.

```json
{ "guides": [ ... ], "starters": [ ... ] }
```

The three older kinds are also read from the app's own `.js` files.

Any entry may carry `"sample": true`. Only the samples in `samples/` do. `--final` rejects it.

All text fields: no em dashes, no emoji, no angle brackets, and none of the banned words (see below).

## guides (new)

| Field | Type | Rule |
|---|---|---|
| `key` | text | ID rules above |
| `category` | text | one of `colour-basics`, `techniques`, `tools-prep`, `problems` |
| `title` | text | 3 to 60 characters. Says what the entry is about. |
| `summary` | text | 20 to 140 characters. One sentence. |
| `body` | list of text | 3 to 8 short paragraphs or steps. Each 20 to 400 characters. |
| `related` | list of keys | 0 to 4. Each must be a real entry key. Not itself. No repeats. |
| `keywords` | list of text | 6 to 12. Lower case, 2 to 40 characters each, no repeats. Plain words or phrases a beginner would type, including common wrong names. |
| `credit` | object, optional | `{ "name": "...", "url": "https://..." }`. Both required if present. |

## starters (new): starter questions

| Field | Type | Rule |
|---|---|---|
| `key` | text | ID rules above |
| `text` | text | 8 to 90 characters. The question as a person would ask it. |
| `targets` | list of keys | 1 to 6. Each must be a real entry key (a guide, or any other kind). No repeats. |

About 20 starter questions in total.

## mentor-tips (existing format, unchanged)

| Field | Type | Rule |
|---|---|---|
| `key` | text | ID rules above |
| `part` | text | one of `armour`, `eyes`, `weapon`, `base` |
| `colour` | text | 3 to 40 characters. A plain colour word or two. |
| `technique` | text | 3 to 40 characters. Free text. Usual words: Base coat, Layer, Shade, Wash, Glaze, Drybrush, Edge highlight, Blend. |
| `advice` | text | 20 to 400 characters. Plain sentences. |
| `colours` | list | 1 to 4 items, each exactly `{ "look": "a deep blue", "hex": "#1f3a66" }`. `look` up to 30 characters. `hex` is `#` plus 6 lower case digits. |
| `credit` | object, optional | as for guides |

## detail-recipes (existing format, unchanged)

| Field | Rule |
|---|---|
| `key` | ID rules above |
| `group` | `body`, `metal`, `material` or `light` |
| `name` | 3 to 40 characters. Letters, spaces, apostrophes and dashes only. The technique or the thing being painted. |
| `summary` | 10 to 100 characters. One short line. |
| `steps` | 3 to 4 steps |

Each step has exactly: `technique`, `coats`, `mix`, `look`, `hex`, `note`.

- `technique`: one of Prime, Base coat, Contrast, Layer, Wash, Shade, Glaze, Dry brush, Edge highlight, Wet blend, Stipple, Sponge, Airbrush, Technical, Texture, Varnish. (The older recipes only use Base coat, Layer, Wash, Shade, Glaze, Dry brush, Edge highlight, Stipple and Sponge.)
- `coats`: a whole number from 1 to 3.
- `mix`: a whole number from 1 to 100. 100 is straight from the pot. A Wash, Shade or Glaze must be under 100. Every other technique must be 100.
- `look`: a plain colour word or two, up to 30 characters.
- `hex`: the target colour, `#` plus 6 lower case digits. Each step in a recipe has its own colour.
- `note`: one sentence, up to 100 characters.

## basing-tips (existing format, unchanged)

| Field | Rule |
|---|---|
| `key` | ID rules above |
| `group` | `ground`, `cold`, `plants` or `stone` |
| `name` | as for detail recipes |
| `summary` | 10 to 100 characters. One short line. |
| `materials` | 3 to 6 plain things, each up to 70 characters, no full stop at the end. No brand or product names. |
| `howto` | 3 to 5 steps. One sentence each, up to 120 characters, ending in a full stop. |
| `paintSteps` | 0 to 5 steps in the same shape as a recipe step. May be an empty list. |

## Banned words

The checker uses the same word lists as the app's own tests:

- `GW_WORDS` and `GW_MORE`: Games Workshop names, army and faction names, characters, units, schemes and paint ranges. From `tests/test_v31.py`.
- `BRAND_WORDS`: brand, product and shop words, including "shop", "buy" and "store". From `tests/test_v35.py`.

It also looks for a few plain words that are real words and also faction words (for example "chaos", "imperial", "legion", "crusade"). Find another way to say it.

## Colours

A colour is always a plain colour word and a hex: `"look": "a deep blue", "hex": "#1f3a66"`. Never a paint name.
