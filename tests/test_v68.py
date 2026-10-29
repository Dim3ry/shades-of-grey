"""v68 tests for Minifolio (chunk 2.3: the "Painted with issues" stage).

What changed:
 AI testers found "Painted with issues" confusing: it sits between Battle ready and Parade ready, the ▲
 from Battle ready moves a unit into it, it counts as Done, and nothing explained it. George chose to
 rename it to "Needs touch-ups". Units save a stage NUMBER, so renaming the name in the saved stage list
 moves nobody. Anyone still on exactly the v3 to v61 default list gets the new name, on the device, from
 a backup and from a safety copy. Custom stage lists are left alone. DATA_VERSION went up to 2 (George's
 choice), so an older copy of the app left open stops saving instead of writing the old name back.

Checks:
1. Versions, the v68 Updates entry, DATA_VERSION is 2.
2. A new device gets "Needs touch-ups" as the 7th stage.
3. A device on the v61 default list: the name changes and is saved; units, models, diary and
   Done starts at are exactly as they were; the saved data version is 2.
4. A custom stage list that still says "Painted with issues" keeps it.
5. The pre-v3 default list still upgrades, and ends with the new name.
6. Restoring a v61 backup (data version 1) renames the stage; a custom backup keeps its names.
7. Restoring a safety copy with the v61 list renames it too.
8. ▲ on a Battle ready unit moves it to Needs touch-ups, which counts as Done.
9. Help explains the stage and names the old name; no em dashes.
10. 390 px and 360 px, dark and light: no sideways scroll.
11. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright
from launch_helpers import app_ready
from launch_helpers import leave_launch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
import test_v44 as e   # main_tab, sub_tab

URL, read = t.URL, t.read
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

OLD = ["Unassembled", "Part assembled", "Assembled", "Primed", "Part painted",
       "Battle ready", "Painted with issues", "Parade ready"]
NEW = OLD[:6] + ["Needs touch-ups", "Parade ready"]
PRE_V3 = ["Unassembled", "Part assembled", "Assembled", "Primed", "Part painted",
          "Painted with issues", "Battle ready"]
CUSTOM = ["Grey", "Primed", "Battle ready", "Painted with issues", "Parade ready"]

UNITS = [
    {"id": 1, "name": "Boyz", "hobby": "40K", "faction": "Orks", "stage": 6, "count": 1,
     "added": "2026-10-01", "log": [["2026-10-01", 5], ["2026-10-05", 6]],
     "photos": [{"id": "p1", "stage": 6, "date": "2026-10-05"}]},
    {"id": 2, "name": "Gretchin", "hobby": "40K", "faction": "Orks", "stage": 5, "count": 3, "each": True,
     "stages": [5, 6, 7], "added": "2026-10-01", "log": [["2026-10-01", 5], ["2026-10-06", 6, 1], ["2026-10-07", 7, 2]]},
    {"id": 3, "name": "Warboss", "hobby": "40K", "faction": "Orks", "stage": 5, "count": 1,
     "added": "2026-10-01", "log": [["2026-10-01", 5]]},
]
SETTINGS = {"tab": "units", "examplesChecked": True, "stages": OLD, "doneFrom": 5, "dataVersion": 1}

def stored(page, key):
    return json.loads(page.evaluate(f"localStorage.getItem('{key}') || 'null'"))

def restore(page, backup):
    page.set_input_files("#restore-file", files=[{"name": "b.json", "mimeType": "application/json",
                                                   "buffer": json.dumps(backup).encode()}])
    page.wait_for_selector("#dialog-yes", state="visible", timeout=5000)
    page.click("#dialog-yes")
    page.wait_for_timeout(600)

def main():
    errors, dialogs = [], []
    html = read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        # ---------- 1. Versions ----------
        print("\n--- 1. Versions and the Updates entry ---")
        t.load(page, units=UNITS, settings=SETTINGS)
        entry = page.evaluate("CHANGELOG.find(c => c.version === 'v68')")
        words = " ".join(entry["changes"]) if entry else ""
        check("the entry names the old and the new name", "Painted with issues" in words and "Needs touch-ups" in words, entry)

        # ---------- 3. The v61 default list on this device ----------
        print("\n--- 3. A device on the v61 default stages ---")
        check("the stages now say Needs touch-ups", page.evaluate("STAGES") == NEW, page.evaluate("STAGES"))
        s = stored(page, "shades-of-grey-settings")
        check("…and that is saved", s["stages"] == NEW, s["stages"])
        check("…Done starts at is unchanged (Battle ready)", s["doneFrom"] == 5, s["doneFrom"])
        check("…the saved data version is 2", s.get("dataVersion") == 2, s.get("dataVersion"))
        # The app's usual tidy-up on load (repaint: false added, photo records with no picture dropped) is not
        # part of this change, so the check looks at what the rename could touch: stages and the diary.
        keep = lambda units: [(u["id"], u["stage"], u.get("stages"), u["log"]) for u in units]
        check("every unit, model and diary entry is exactly as it was", keep(stored(page, "mini-tracker-models")) == keep(UNITS), stored(page, "mini-tracker-models"))
        card = page.inner_text('#view-units li.unit[data-id="1"]')
        check("the unit's card shows Needs touch-ups", "Needs touch-ups" in card and "Painted with issues" not in card, card)

        # ---------- 8. The ▲ from Battle ready ----------
        print("\n--- 8. ▲ from Battle ready ---")
        up = page.locator('#view-units li.unit[data-id="3"] .up-button')
        check("▲ on a Battle ready unit names Needs touch-ups", "Needs touch-ups" in (up.get_attribute("aria-label") or ""), up.get_attribute("aria-label"))
        up.click()
        page.wait_for_timeout(300)
        u = next(x for x in stored(page, "mini-tracker-models") if x["id"] == 3)
        check("…and moves it there, which counts as Done", u["stage"] == 6 and page.evaluate("isDone(6)"), u)

        # ---------- 2. A new device ----------
        print("\n--- 2. A new device ---")
        t.load(page, settings={"tab": "units", "examplesChecked": True})
        check("a new device gets Needs touch-ups as the 7th stage", page.evaluate("STAGES") == NEW, page.evaluate("STAGES"))

        # ---------- 4. A custom list ----------
        print("\n--- 4. A custom stage list ---")
        t.load(page, units=[dict(UNITS[0], stage=3, log=[["2026-10-01", 3]], photos=[])],
               settings=dict(SETTINGS, stages=CUSTOM, doneFrom=2))
        check("a custom list that says Painted with issues keeps it", page.evaluate("STAGES") == CUSTOM, page.evaluate("STAGES"))
        check("…saved as it was", stored(page, "shades-of-grey-settings")["stages"] == CUSTOM)
        extra = OLD + ["Based"]
        t.load(page, settings=dict(SETTINGS, stages=extra))
        check("the default list with an added stage is left alone too", page.evaluate("STAGES") == extra, page.evaluate("STAGES"))

        # ---------- 5. The pre-v3 list ----------
        print("\n--- 5. The pre-v3 default list ---")
        t.load(page, units=[dict(UNITS[2], stage=5, log=[["2026-10-01", 5]])],
               settings={"tab": "units", "examplesChecked": True, "stages": PRE_V3, "doneFrom": 5})
        check("the pre-v3 list upgrades to the new default list", page.evaluate("STAGES") == NEW, page.evaluate("STAGES"))
        u = stored(page, "mini-tracker-models")[0]
        check("…its Painted with issues unit lands on Needs touch-ups", u["stage"] == 6, u)

        # ---------- 6. Backups ----------
        print("\n--- 6. Restoring a backup ---")
        t.load(page, settings={"tab": "units", "examplesChecked": True})
        e.main_tab(page, "settings")
        backup = {"app": "Minifolio", "version": 6, "dataVersion": 1, "stages": OLD, "doneFrom": 5,
                  "models": UNITS, "recipes": {"recipes": []}}
        restore(page, backup)
        s = stored(page, "shades-of-grey-settings")
        check("a v61 backup (data version 1) is restored", len(stored(page, "mini-tracker-models")) == 3, stored(page, "mini-tracker-models"))
        check("…with Needs touch-ups in place of Painted with issues", s["stages"] == NEW and page.evaluate("STAGES") == NEW, s["stages"])
        check("…its units keep their stages", [x["stage"] for x in stored(page, "mini-tracker-models")] == [6, 5, 5])
        restore(page, dict(backup, stages=CUSTOM, doneFrom=2, models=[dict(UNITS[2], stage=3, log=[["2026-10-01", 3]])]))
        check("a backup with custom stages keeps its names", stored(page, "shades-of-grey-settings")["stages"] == CUSTOM,
              stored(page, "shades-of-grey-settings")["stages"])

        # ---------- 7. Safety copies ----------
        print("\n--- 7. Recovering a safety copy ---")
        t.load(page, settings={"tab": "units", "examplesChecked": True})
        page.evaluate("""([s, m]) => localStorage.setItem('mini-tracker-models-before-restore',
            JSON.stringify({ date: '2026-10-20', stages: s, doneFrom: 5, models: m }))""", [OLD, UNITS])
        page.reload()
        app_ready(page)
        leave_launch(page)   # U4b: tap through the start page
        page.evaluate("() => recoverSafetyCopy('-before-restore')")
        page.wait_for_selector("#dialog-yes", state="visible", timeout=5000)
        page.click("#dialog-yes")
        page.wait_for_timeout(500)
        check("a safety copy with the v61 list comes back with Needs touch-ups", stored(page, "shades-of-grey-settings")["stages"] == NEW,
              stored(page, "shades-of-grey-settings")["stages"])
        check("…and its units keep their stages", [x["stage"] for x in stored(page, "mini-tracker-models")] == [6, 5, 5])

        # ---------- 9. Help ----------
        print("\n--- 9. Help ---")
        e.main_tab(page, "settings")
        e.sub_tab(page, "help")
        page.click("summary:has-text('Stages and')")
        page.wait_for_timeout(150)
        # A3: the unit card's ▲ became a right arrow, so Help says "right arrow".
        topic = page.text_content("#help-touch-ups") or ""
        check("Help explains Needs touch-ups, where it sits and its old name",
              all(w in topic for w in ["Needs touch-ups", "Battle ready", "Parade ready", "right arrow", "Painted with issues"]), topic)
        check("Help's Done line names the new stage", '"Needs touch-ups"' in html and '"Battle ready", "Painted with issues" and' not in html)

        # ---------- 10. Phones, dark and light ----------
        for appearance in ["dark", "light"]:
            for width in [390, 360]:
                tag = f"{appearance} {width}px"
                print(f"\n--- 10. {tag} ---")
                page.set_viewport_size({"width": width, "height": 780})
                t.load(page, units=UNITS, settings=dict(SETTINGS, appearance=appearance))
                page.click('#view-units li.unit[data-id="1"] .info')
                page.wait_for_timeout(250)
                check(f"{tag}: no sideways scroll", not page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth"))

        # ---------- 11. Safety ----------
        print("\n--- 11. Safety ---")
        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
