"""AB11 tests for Minifolio (first stage name for new installs, AT-37). New behaviour only:
1. A brand-new install starts with "On sprue" as the first stage, and the stage legend shows it.
2. Existing installs keep "Unassembled": a saved v132 to v137 default list, an older default list (renamed by TD1a's
   path, now to the "Unassembled" list), saved units with no stage list, and damaged settings. Units keep their stage number.
   A backup or safety copy with an old default list is renamed to the "Unassembled" list too.
3. A custom list is left alone.
4. CSV import: "On sprue", "Unassembled" and the everyday words land on stage one, on both a fresh and an existing list.
   (The army-list paste import does not read stage words, so it has nothing to check here.)
Run with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

REST = ["Part assembled", "Assembled", "Primed", "Part painted", "Tabletop ready", "Needs touch-ups", "Display ready"]
FRESH = ["On sprue"] + REST
EXISTING = ["Unassembled"] + REST
V131 = ["Unassembled", "Part assembled", "Assembled", "Primed", "Part painted", "Battle ready", "Needs touch-ups", "Parade ready"]
CUSTOM = ["Grey", "Unassembled", "Primed", "Done"]
UNITS = [{"id": i, "name": f"Unit {i}", "hobby": "40K", "faction": "Orks", "stage": s, "count": 1,
          "added": "2026-10-01", "log": [["2026-10-01", s]]} for i, s in [(1, 0), (2, 5), (3, 7)]]
SETTINGS = {"tab": "units", "examplesChecked": True}

def stored(page, key):
    return json.loads(page.evaluate(f"localStorage.getItem('{key}') || 'null'"))

def stage_of(page, text):
    return page.evaluate("(w) => { const r = csvToUnits([['name','status'],['X', w]]); return r.units ? r.units[0].stage : r }", text)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. A brand-new install ---")
        t.load(page, settings=SETTINGS)
        check("the first stage is On sprue, the rest unchanged", page.evaluate("STAGES") == FRESH, page.evaluate("STAGES"))
        s = stored(page, "shades-of-grey-settings")
        check("...saved, with Done from Tabletop ready", s["stages"] == FRESH and s["doneFrom"] == 5, s)
        legend = page.evaluate("document.getElementById('stage-legend').textContent")
        check("...and the stage legend shows On sprue", "On sprue" in legend and "Unassembled" not in legend, legend[:120])

        print("\n--- 2. Existing installs keep Unassembled ---")
        t.load(page, units=UNITS, settings={**SETTINGS, "stages": EXISTING, "doneFrom": 5, "dataVersion": 2})
        check("a saved v132 to v137 default list is kept as it is", page.evaluate("STAGES") == EXISTING, page.evaluate("STAGES"))
        check("...units keep their stage numbers", [u["stage"] for u in stored(page, "mini-tracker-models")] == [0, 5, 7])
        t.load(page, units=UNITS, settings={**SETTINGS, "stages": V131, "doneFrom": 5, "dataVersion": 2})
        check("an older default list is renamed to the Unassembled list, not to On sprue", page.evaluate("STAGES") == EXISTING, page.evaluate("STAGES"))
        check("...saved, and units keep their stage numbers", stored(page, "shades-of-grey-settings")["stages"] == EXISTING
              and [u["stage"] for u in stored(page, "mini-tracker-models")] == [0, 5, 7])
        check("a backup or safety copy with an old default list gets the Unassembled list",
              page.evaluate("(l) => renamedStageList(l)", V131) == EXISTING)
        t.load(page, units=UNITS, settings=SETTINGS)
        check("saved units with no stage list get the Unassembled list", page.evaluate("STAGES") == EXISTING, page.evaluate("STAGES"))
        page.evaluate("() => { localStorage.setItem('shades-of-grey-settings', '{not json'); }")
        page.reload()
        t.app_ready(page)
        check("damaged settings get the Unassembled list", page.evaluate("STAGES") == EXISTING, page.evaluate("STAGES"))

        print("\n--- 3. A custom list ---")
        t.load(page, units=UNITS[:1], settings={**SETTINGS, "stages": CUSTOM, "doneFrom": 3})
        check("a custom list is left alone", page.evaluate("STAGES") == CUSTOM and stored(page, "shades-of-grey-settings")["stages"] == CUSTOM,
              page.evaluate("STAGES"))
        got = {w: stage_of(page, w) for w in ["On sprue", "Unassembled", "on the sprue"]}
        check("...its Unassembled stage still reads both names", got == {"On sprue": 1, "Unassembled": 1, "on the sprue": 1}, got)

        print("\n--- 4. CSV import ---")
        words = ["On sprue", "on-sprue", "Unassembled", "unassembled", "on the sprue", "unbuilt"]
        t.load(page, settings=SETTINGS)
        got = {w: stage_of(page, w) for w in words}
        check("fresh list: both names and the everyday words land on stage one", all(v == 0 for v in got.values()), got)
        t.load(page, units=UNITS[:1], settings={**SETTINGS, "stages": EXISTING, "doneFrom": 5})
        got = {w: stage_of(page, w) for w in words}
        check("existing list: both names and the everyday words land on stage one", all(v == 0 for v in got.values()), got)

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

main()
