---
name: lean-tests
description: Use whenever you write, change, delete or run Minifolio tests (tests/), or a chunk adds behaviour that needs a test. Keeps the suite small and fast: update old tests instead of copying them, sample instead of looping, never re-check version plumbing.
---

# Lean tests for Minifolio

The aim is a suite that stays short and quick as the app grows. CLAUDE.md has the hard rules; this is the working method.

## Before writing a test: three questions
1. **What is new?** List the behaviours this chunk adds or changes, in one line each. Only those get checks.
2. **Is it already covered?** Search `tests/` for the screen, button or function name (`grep -l "Add all steps" tests/*.py`). If an older test covers it:
   - behaviour changed: edit that older test in this chunk, and say so in the pull request;
   - behaviour unchanged: write nothing. Do not copy a "still works" check forward.
3. **Does it need a browser?** Reading `app.js`, `index.html` or a data file for a fact (a word is gone, a rule is in the code) is a file check: no page, near-instant. Use the browser only for behaviour a person would see or tap.

## Never put these in a chunk's test
Version, `sw.js` VERSION, script tags, the Updates entry, `DATA_VERSION`, file lists, storage names, the security policy, "content files unchanged", "no CSP errors". `tests/test_version_plumbing.py` and the runner do these once. If you need to know the version, import `tests/version_helpers.py` (`current()`, `at_least("vN")`, `newer_than("vN")`, `has_entry(page, "vN")`, `data_version()`). A new test file that mentions `APP_VERSION`, `sw.js`, `?v=`, `CHANGELOG`, `DATA_VERSION` or `git diff` fails the runner's lint.

Keep `no page errors` and `no browser pop-ups` in each new test; those are cheap and catch real breakage.

## Keeping a test cheap
- Target: under 30 s and 40 checks. Hard limits: 45 s and 60 checks.
- Loops over every paint, recipe or tip: sample three (shortest, longest, one unusual). Loop over all only when the point is the whole list (for example "every recipe's rows match the user's paints"), and then run the loop inside one `page.evaluate`, not one click per item.
- Check widths 390 and 360, dark and light, once each. Do not repeat every check at every size; repeat only the layout checks (no sideways scroll, tap targets 44 px or more).
- One page load per section, not per check. Prefer `page.wait_for_function` over fixed `wait_for_timeout` pauses.
- Share setup: reuse `load`, `book` and other helpers from the helper-library tests instead of pasting them. Helper-library files (v27, v31, v35, v37b, v38, v39, v41, v42, v44, v51, v52, v53, v54) are imported by other tests: never delete them.

## While building
1. Run only your test: serve the repo (`python3 -m http.server 8801`) and `SOG_PORT=8801 python3 tests/test_vNN.py tests/screenshots`.
2. Then `python3 tests/run_all.py --quick` for the newest versions and the plumbing test.
3. Before the pull request: the full `python3 tests/run_all.py` in the background. Known failures that also happen on main: `test_colour_engine`, `test_v21_7`.

## Removing tests (only when George has approved the list)
- Say what goes and why in the pull request, one line each.
- Check imports first: `grep -n "import test_vNN\|from test_vNN" tests/*.py`.
- Remove duplicates by keeping the oldest copy. Never weaken a check that stays.
- Prove it: checks before and after, run time before and after, and that every kept check still passes (compare the PASS lines of a before and an after run).

## Triage helper
`python3 tests/run_all.py --rerun-failed` reruns each failed file alone and says "failed in the run, passed alone", "time only" or "still failing". The `test-runner` agent (`.claude/agents/test-runner.md`) runs the full suite this way and gives one plain paragraph; use it before a merge by saying "use the test-runner agent".

## Budget
`tests/time_budget.json` records each file's time. A warning is a prompt to sample or cut, not to raise the number. Run `python3 tests/run_all.py --update-budget` only after a clean full run and only on purpose, and say so in the pull request.

## Smell list (ask before adding)
- Does the check restate the label or the code (`"button exists"` right before `"button works"`)?
- Would it still pass if the feature were broken? If so it proves nothing.
- Is it in an older test already? Delete the new one.
- Is it a count of how many items exist (`== 24 schemes`)? Prefer a check on the rule, not the number, unless the number is the feature.
