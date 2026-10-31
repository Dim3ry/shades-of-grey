# Knowledge base pack: technical brief for Claude

This brief is for the Claude that runs chunks X8, X8b and X8c in Minifolio. The chunk prompts themselves live in George's chunk-prompts.md, as usual. This file says what the pack contains, what has already been checked, and how the tools behave. Read it in full before giving an estimate.

The knowledge base deliberately carries no per-entry `credit` fields. It is general know-how distilled from about 1,700 videos and articles, then written fresh in plain words from points merged across many sources, and it was judged that no entry comes clearly from one creator. George has seen this explanation and decides on it. Do not add credits or audit the entries for them unless a chunk prompt asks.

## The pack

The zip mirrors the repo, so unpack it at the repo root. It only adds files under `knowledge-base/`.

```
knowledge-base/
  PACK.md                  this file
  data/                    the K-files, in the format README.md and SCHEMA.md describe
    k1-colour-basics.json         81 guides
    k2-techniques.json           316 guides
    k3-detail-recipes.json       119 detail recipes (new ones only)
    k4-basing-tips.json           48 basing tips (new ones only)
    k5-tools-prep-problems.json  205 guides
    k7-starters.json              20 starter questions
  extras/                  Mentor matching data (read only by build_mentor_data.py, never by the app)
    recipe-and-basing-keywords.json   keywords for recipes and basing tips (those kinds have no keywords field)
    beginner-synonyms.json            282 groups of words that mean the same thing, canonical first
    asked-as-phrases.json             10 ways people ask for each new entry
    quick-answers.json                for each entry, a quick answer for each of its phrases ("See: ..." means none)
  tools/
    kb_import.py           writes the K-files into guides-data.js, detail-recipes.js and basing-tips.js (X8)
    lint_recipes_tips.py   the v32/v33 wording rules, run over the data on its own (needs Node to read the paint list)
    build_mentor_data.py   builds mentor-data.js from extras/ (X8b); --no-quick leaves out quick answers
  eval/                    the 1,900-question test bench (Node; not part of the test run)
    eval_george.js, questions.tsv, topics.tsv, coverage.tsv, split.json, offtopic.txt
  upgrade/
    x8-test-changes.patch       tested edits to the older tests, the fixture and a new test, made against v103 (X8)
    mentor-engine.js            the upgraded engine, as a whole file (X8b)
    engine-upgrade.diff         the same change as a diff against v103 plus X8's data. Its index.html and sw.js parts don't apply after X8 (X8 changes the sw.js comment they need), so X8b applies only the engine part
    mentor-data.js              built output, for comparison (X8b rebuilds it)
    mentor_upgrade_check.js     Node checks of the new engine behaviour (X8b; moves to tests/)
    test_mentor_words.py        its runner plus two page checks (X8b; becomes tests/test_vNN_mentor_words.py)
  reference/               X8c only, for reading: README.md, search-engine/ (the reference engine), wordnet-map.json
```

- All Python is standard library only. The pack's tools run with `python3 -I` (`py -I` on Windows). George's README runs check_knowledge.py without `-I`, and either is fine.
- lint_recipes_tips.py and the Node scripts need Node 18 or later. Nothing in tools/, eval/ or upgrade/ needs npm.
- The reference/ scripts are for reading only. They need onnxruntime-node from npm and James's build files, so they won't run as they are.
- eval/questions.tsv quotes some real beginner questions that name paint brands. They are test data, never shown in the app.

## What has already been checked

Everything was checked on local copies of main, and nothing was pushed.

- **Checker:** `check_knowledge.py --final` reports CLEAN before the import (all six K-files with the app's original detail-recipes.js and basing-tips.js) and after it (k1, k2, k5 and k7 with the two imported .js files). Adding mentor-tips.js gives NOT CLEAN, but only because of its three `sample-*` entries. That's expected until K6.
- **Lint:** `lint_recipes_tips.py --source app` reports 0 violations over all 137 recipes and 60 tips after the import, and 0 over George's original 18 and 12 with `--source main`.
- **X8, full dry run on v101:** run from these instructions in a fresh clone.
  - The full run passed after the older tests were updated.
  - v32 and v33 took about 110 s each once their click-through loops were sampled.
  - test_v96 and test_v97 also needed updating.
- **X8 on v103:** upgrade/x8-test-changes.patch applies cleanly to v103 (`git apply --check`). With it:
  - every edited test passes on its own: v32 in 81 s, v33 in 86 s, v37 in 68 s, v96, v97 and v98 in seconds, and v100 47 of 47;
  - the new test_v104_knowledge_base.py passes 8 checks in 4 s;
  - George's v102 and v103 Mentor tests pass;
  - the quick run passes.
  On a busy 2-core machine, the full run's other failures were timing only. Each of those files passed when run alone (v87, v21_3, v18_paste, v55, v47). v35 and v37b went over their warning time only, so watch v35 on George's 4-core run.
- **X8b on v103 with X8's data:** `node tests/mentor_engine_check.js` passes 35 of 36 unedited. The only failure is the cold timing check "colour path with a 4000-paint catalogue under 60 ms", which George's engine also fails on the same busy 2-core machine. mentor_upgrade_check.js passes 32 of 32, and the runner (test_mentor_words.py) passes 34 of 34 with its page checks.
- **X8b, full dry run on v103 plus X8:** run from these instructions in a fresh clone.
  - mentor-data.js built identical to the pack's copy, and the engine part of the diff applied cleanly.
  - Before and after: 61% → 72.7% held-back top-3, with off-topic answers at 17 of 40 both times.
  - George's v102 (40/40) and v103 (20/20) Mentor tests pass with mentor-data.js on the page.
  - The new test took 26 s.
  - In the full run (30.5 min on 2 cores), every failure either also failed without X8b or passed alone:
    - the cold timing checks, including the new file's 600 ms first read under load;
    - test_v26, which fails on plain v103 on that machine too;
    - the X8 test files, because that run didn't have X8's test edits in.
  - The first answer on a 4x-slowed CPU took about 1 s.
- **The cold timing check** may pass on George's 4-core machine. If it fails there on main too, report it plainly. Don't loosen it.

## How kb_import.py behaves

`python3 -I knowledge-base/tools/kb_import.py . knowledge-base/data`

- **guides-data.js:** it rewrites only `GUIDE_ENTRIES` (602, under `// ---------- Category ----------` lines in Guides order) and `GUIDE_STARTERS` (20). It keeps the header comment (X8 step 4 updates it by hand) and puts one `// X8:` comment line above each list.
- **detail-recipes.js and basing-tips.js:** it appends each group's new entries at the end of that group's section, between `// X8 start: ...` and `// X8 end`, one step per line in the existing style. It never changes or reorders an existing entry: it reads the file back and stops if any old entry differs.
- **Re-running:** a second run replaces its own X8 blocks. On unchanged data it writes nothing.
- **It stops without writing** on any of these:
  - a key clash;
  - an unknown group or category;
  - an unknown or missing field;
  - a broken `related` or `targets` key;
  - a sample entry;
  - CRLF line endings, including in mentor-tips.js;
  - a read-back mismatch.
- **Keys** are unique across every kind, apart from the old `mud` pair. `knowledgeIndex()` answers `get(key)` with the first one loaded, in this order: guides, detail, basing, tips, starters.
- **Counts after the import:**
  - GUIDE_ENTRIES 602: colour basics 81, techniques 316, tools and prep 155, problems 50.
  - DETAIL_RECIPES 137: body 39, metal 30, material 44, light 24.
  - BASING_TIPS 60: ground 19, cold 10, plants 14, stone 17.
- **"muddy ground" fixture row:** with the new tips, George's check (which loads no data file) finds dry-mud-ground first. Both answers are right, so x8-test-changes.patch changes the row's expected key to dry-mud-ground and gives the reason as a fourth item on the row (the check reads only the first three).

## What X8b changes in mentor-engine.js

- **Unchanged:** the API, the return shape (`{ kind, lead, sources, picks?, suggestions? }`), THRESHOLD 8, COVER_BONUS 5, RELATIVE_KEEP 0.5 and the X6a SCORE numbers.
- **Where the data comes from:** `context.data`, or else the page's `MENTOR_DATA`.
- **What depends on the data file:** with no data file, (a), (b), (d) and (e) are off. The rare-word weights (c) and the unseen-word rule (f) come from the entries themselves, so they always apply, and George's check (which loads no data file) tests them.
- **Labels:** the new header comment labels the additions a to f, and each is tagged in place.

The additions:

- **(a) Extra keywords** for recipes and basing tips (fangs finds Teeth, magma finds Lava).
- **(b) Synonyms:** a whole-word swap to the canonical word, longest first, in both questions and entries. The colour reader sees the swapped words, so "green stuff", "white spirit" and "blue tack" no longer take the colour path.
- **(c) Rare-word weights:** `log(1+N/df)`, scaled so that a word in 8 entries counts 1, and clamped to 0.4 to 1.2.
- **(d) Phrase bank:** each entry's best IDF cosine against its asked-as phrases. Below 0.5 it adds nothing; from 0.5 to 1 it ramps from 0 to 10 points. Also new is `SCORE.keywordWord` (3), so one word of a keyword phrase earns its own credit.
- **(e) Quick lead:** when the top source's best phrase matches at 0.6 or more and has a quick answer, that answer is the lead. "Also see" is added only if the lead stays within two sentences and 260 characters. Starters use `MENTOR_DATA.starters`: 19 of the 20 have an answer (starter-painting-metal has none and uses George's lead). With `--no-quick` data, every lead follows George's own lead logic.
- **(f) Honest "none":**
  - Words found in no entry shrink every score. The strength is `UNSEEN_POWER` (3) × min(1, distinct words in the entries / `UNSEEN_VOCAB` 3000). With the app's ~4,000-word index that's the full 3, so "what time is it in tokyo" gets none. In George's small 216-entry check index (636 words) it's about 0.64, so everyday words such as "mean" and "use" don't sink fixture questions.
  - Chat words (hi, was, thanks, wondering...) join FILLER, so chatty questions aren't punished.

**Measured** on the 1,900-question bench (`eval/eval_george.js`), with the index built the app's way from v103 plus X8's data. Tuning used the repair set only (758 questions), with no more off-topic questions answered than George's engine (17 of 40). The held-back set is 1,137 questions.

| | repair top-3 | held-back top-3 | held-back top-1 | held-back answered but wrong |
|---|---|---|---|---|
| George's engine + X8 data | 76.6% | 61.0% | 42.5% | 33.6% |
| X8b + mentor-data.js | 88.7% | 72.7% | 55.1% | 21.8% |

The quick lead is used on about 45% of held-back answers. When it is used, the first source is right 75% of the time.

**With mentor-data.js on the page,** two rows of George's question table answer differently. mentor_upgrade_check.js names both:
- "muddy ground" finds mud, not dry-mud-ground. Both are right.
- "how tall is a tree" now finds the scenery guide trees-from-twigs instead of none. It's a near-miss answer to an off-topic question, of the kind counted above.

**Known limits:**
- **First question:** it takes about 460 ms here (260 ms before), and about 1 s with the CPU slowed 4x. George's X6b warm-up does this work 400 ms after Mentor opens, so most people won't notice. On a slow phone the window may pause briefly while it runs, so time it (X8b step 5).
- **Typo fixes:** with more words known, false fixes rise ("bread" is read as "bead").
- **Colour path:** "white armour" and "gold armour recipe" still take it, as George designed. That's about 1% of questions.
- **Off-topic questions:** 17 of 40 still get an answer, the same count as before. Many are near misses that share painting words ("how do I paint a car" finds the vehicles guide, "best way to paint a fence"). The list is in eval/offtopic.txt.
