# Minifolio: instructions for Claude

Mobile-first miniature-painting tracker. Plain JavaScript web app, no accounts, data stays on the user's device, works offline. Owner: George. He is not a professional developer: explain things in plain language and assume no prior knowledge.

## Working rules
- Branch every chunk from main. Open a pull request. Never merge, push to main or deploy unless George says yes.
- One chunk per session. If the work is clearly bigger than the prompt, stop and say so before building.
- Before building, give a cost estimate as a % of a session and warn George if it is over 10%. Chunks have run at about double their estimate.
- Never invent a chunk. The only source of next steps is chunk-prompts.md in George's private repo Dim3ry/minifolio-plans. Read it with add_repo (read access is enough). Do not copy anything from that repo into this public one.
- Never change recipe, scheme or paint content files (schemes.js, detail-recipes.js, basing-tips.js and the paint catalogue) unless the prompt says to.
- On Windows, Python is py.

## Running chunks in parallel
Use it when a chunk splits cleanly by page (for example "check every page at 1280 px and 1920 px"). Do not use it for work that changes shared code in one place, or when one part needs another's result.
- George says yes to the split first. The parent session (the one he is talking to) splits the work, launches one code session per group of pages, and does the merging and the single version bump. Sonnet is the default model for page checks.
- Each child session: branches from main, makes no version bump (no APP_VERSION, sw.js, ?v= or CHANGELOG change), puts its CSS next to its own pages under one comment line starting with its chunk label (such as "R3b-1:"), puts its tests in a new file named for its group (tests/test_vNN_<group>.py), runs only its own tests and the quick run, opens a pull request and does not merge. If nothing needs fixing it opens no pull request and says so.
- Child sessions are told that George has approved the parallel run, so they give a one-line cost estimate and carry on. They do not paste a next-chunk prompt.
- The parent merges the pull requests one at a time, fixes any clash, then does one version bump, one full test run and one pull request for the bump. It reports to George in plain language what each session found, fixed and left alone.
- Measure a tap target by its real tap area. A button with an enlarged ::after hit area (the basket in the tab bar) counts at the size of that area.

## Versions
One version bump per chunk that changes the app. A bump means:
- the ?v= number on all six script tags in index.html, and the comments that name it
- VERSION in sw.js
- APP_VERSION in app.js
- one new entry at the top of CHANGELOG in app.js, in plain words
- update Help when behaviour or names change
- add tests/test_vNN.py for the new behaviour only (see Tests below)
- if you add a script file, index.html and sw.js change and the shared test follows them; no test file is edited
A bump does not touch old tests. tests/test_version_plumbing.py checks the version, sw.js, script tags and Updates entry once, for every version.
Docs-only changes need no bump.

## Tests
- Windows: PYTHONIOENCODING=utf-8 py tests/run_all.py. Elsewhere: python3 tests/run_all.py. It runs cores + 2 test files at a time (at most 8; 6 on a 4-core machine) and takes about 12 minutes on a 4-core machine (longer on a slow one), so run it in the background.
- Quick mode: python3 tests/run_all.py --quick runs only the newest three versions, the version plumbing test and the HTML safety scan. Use it while building. Never merge on a quick run: do the full run first.
- Growth guard (full runs): tests/time_budget.json holds each file's recorded time. A file over its recorded time plus 25% or over 120 s, a new file over 30 s or 60 checks, or a whole run over 13 minutes prints a TIME WARNINGS block and still passes. A file over 180 s, a new file over 45 s or a whole run over 18 minutes fails. These numbers are for the machine the budget was recorded on (4 cores): every full run first times a small fixed CPU job and scales the per-file and whole-run limits by how much slower (or, down to 0.8, faster) this machine is, and the whole-run limits also by the number of cores (shown on the first line of the output; tests/test_budget_scaling.py checks this). The three files named under fail_overrides in the budget file keep a longer allowance because the app itself is slow to redraw there. Rewrite the budget only on purpose, after a clean full run: python3 tests/run_all.py --update-budget. A new test file that mentions APP_VERSION, sw.js, ?v=, CHANGELOG, DATA_VERSION or git diff also fails (source lint).
- Changing recipe, scheme or tip content on purpose (the prompt says to): run with CONTENT_CHANGE_OK=1. Changing the security policy on purpose: update tests/csp_baseline.txt in the same chunk.
- Known failures that also happen on main: test_colour_engine (needs Node.js) and test_v21_7 (select_option timeout). Report any other failure plainly. Never skip or weaken a test to get green.
- When a test checked old wording, update it and say why in the test.
- A chunk's new test covers only its new behaviour. It never checks the app version, sw.js VERSION, script tags, the Updates entry, DATA_VERSION, file lists, storage names, the security policy or "content files unchanged". tests/test_version_plumbing.py does that once, using tests/version_helpers.py (current(), at_least("vN"), newer_than("vN"), changelog_versions(page), has_entry(page, "vN"), data_version()).
- Do not copy a "still works" check from an older test. If older behaviour changes, update the older test in the same chunk and say so.
- Keep a new test file under 45 s and 60 checks. The runner warns above 30 s and fails above 45 s. A loop over every paint, recipe or tip needs a reason; sample 3 unless the point is the whole list.
- Some test files are imported by other tests as helper libraries (v27, v31, v35, v37b, v38, v39, v41, v42, v44, v51, v52, v53, v54). Never delete them; if their checks go, keep the helper functions or move them to tests/common.py first.
- The Cloudflare "Workers Builds" check fails on every pull request. Ignore it. Check main's build after each merge.
- Check on a 390 px and a 360 px wide phone screen, dark and light. No sideways scroll. Tap targets 44 px or more.

## UI text rule (applies to every change)
- No descriptive subtitle under a heading, tab title or card title unless the screen would be confusing without it.
- Empty states get one short line at most.
- Prefer clear labels, icons and tooltips over sentences. No helper text that restates the label.
- No em dashes in UI copy. No emoji unless already in use. No badges, pills or decorative callouts by default.
- Status is never shown by colour alone.
- If unsure whether text is needed, leave it out and say so in the summary.

## Legal and content
- No Games Workshop names, artwork or logos beyond the existing trademark notice. Colours are shown as approximate.
- Mentor and tips content comes from George's own notes. Credit or link any creator it draws on. Never copy creators' content.

## Finishing a chunk
1. Give a summary in plain language: what changed, what was tested, anything left over, anything you chose to leave out. Put the full description in the pull request.
2. Then attach Dim3ry/minifolio-plans with add_repo (read access), read chunk-prompts.md, and paste the next chunk's prompt in full in a code block, word for word. The next chunk is the one named by the "Next chunk:" line at the end of the prompt you just did. Also say which model and effort level suit it, as given in that file.
3. Never compose a prompt yourself. If the repo or the file cannot be reached, or you cannot tell which chunk is next, say so and stop.
4. Leave any placeholder in the pasted prompt (such as the one in chunk 2.2) as it is. George fills those in.
