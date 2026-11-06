"""TD1a tests for Minifolio (wording changes). New behaviour only:
1. Fresh start: the stages are Tabletop ready and Display ready (Done means Tabletop ready or later).
2. A saved v68 to v131 default list (old names) and a v61 default list are renamed; units keep their stage number.
   A custom list that uses the old names is left alone.
3. CSV import: the new names, the old names and the everyday words all land on the right stage (fresh list and custom old list).
4. The Help sub-tab is called How it works, and its internal page still opens with the link text.
5. The feedback card line is the new text.
6. The Credits link in How it works > About opens the Credits sub-tab.
Item 4 of the chunk (army import default) was not changed: no list names a game today and the default was already 40K.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

BASE = ["Unassembled", "Part assembled", "Assembled", "Primed", "Part painted"]
NEW = BASE + ["Tabletop ready", "Needs touch-ups", "Display ready"]
V132_PREV = BASE + ["Battle ready", "Needs touch-ups", "Parade ready"]
V61 = BASE + ["Battle ready", "Painted with issues", "Parade ready"]
CUSTOM = ["Grey", "Primed", "Battle ready", "Parade ready"]
UNITS = [{"id": i, "name": f"Unit {i}", "hobby": "40K", "faction": "Orks", "stage": s, "count": 1,
          "added": "2026-10-01", "log": [["2026-10-01", s]]} for i, s in [(1, 5), (2, 6), (3, 7)]]

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

        print("\n--- 1. Fresh start ---")
        t.load(page, settings={"tab": "units", "examplesChecked": True})
        # AB11 (v138): a fresh start's first stage is now "On sprue"; the rest of the list is TD1a's.
        check("fresh stages use the new names", page.evaluate("STAGES") == ["On sprue"] + NEW[1:], page.evaluate("STAGES"))
        check("the old names are gone from the stage list", "Battle ready" not in page.evaluate("STAGES") and "Parade ready" not in page.evaluate("STAGES"))

        print("\n--- 2. Saved stage lists ---")
        for label, old, done in (("the v68 to v131 default", V132_PREV, 5), ("the v61 default", V61, 5)):
            t.load(page, units=UNITS, settings={"tab": "units", "examplesChecked": True, "stages": old, "doneFrom": done, "dataVersion": 2})
            check(f"{label} list is renamed", page.evaluate("STAGES") == NEW, page.evaluate("STAGES"))
            s = stored(page, "shades-of-grey-settings")
            check("...saved, with Done starting where it did", s["stages"] == NEW and s["doneFrom"] == 5, s)
            check("...every unit keeps its stage number", [u["stage"] for u in stored(page, "mini-tracker-models")] == [5, 6, 7], stored(page, "mini-tracker-models"))
        t.load(page, units=UNITS[:1], settings={"tab": "units", "examplesChecked": True, "stages": CUSTOM, "doneFrom": 2})
        check("a custom list with the old names is left alone", page.evaluate("STAGES") == CUSTOM, page.evaluate("STAGES"))
        check("...and still saved as it was", stored(page, "shades-of-grey-settings")["stages"] == CUSTOM)
        check("an old default list with an extra stage is left alone",
              (t.load(page, settings={"tab": "units", "examplesChecked": True, "stages": V132_PREV + ["Based"]}) or True) and page.evaluate("STAGES") == V132_PREV + ["Based"], page.evaluate("STAGES"))

        print("\n--- 3. CSV stage words ---")
        t.load(page, settings={"tab": "units", "examplesChecked": True})
        got = {w: stage_of(page, w) for w in ["Tabletop ready", "Battle ready", "battle-ready", "Display ready", "Parade ready", "parade", "tabletop", "Needs touch-ups"]}
        check("new and old names for the 6th stage land on it", got["Tabletop ready"] == 5 and got["Battle ready"] == 5 and got["battle-ready"] == 5 and got["tabletop"] == 5, got)
        check("new and old names for the last stage land on it", got["Display ready"] == 7 and got["Parade ready"] == 7 and got["parade"] == 7, got)
        check("the middle stage is unchanged", got["Needs touch-ups"] == 6, got)
        t.load(page, settings={"tab": "units", "examplesChecked": True, "stages": CUSTOM, "doneFrom": 2})
        got = {w: stage_of(page, w) for w in ["Battle ready", "tabletop", "Parade ready", "display"]}
        check("a custom list with the old names still reads the everyday words", got == {"Battle ready": 2, "tabletop": 2, "Parade ready": 3, "display": 3}, got)

        print("\n--- 4. How it works ---")
        t.load(page, settings={"examplesChecked": True}, launch=True)
        page.click('.tabs button[data-tab="guides"]')
        wait_settled(page)
        labels = page.evaluate("() => [...document.querySelectorAll('#more-seg button')].map(b => b.textContent.trim())")
        check("the sub-tab is called How it works", "How it works" in labels and "Help" not in labels, labels)
        page.click('#more-seg button[data-page="help"]')
        wait_settled(page)
        check("it opens the same page", page.is_visible("#view-help") and page.is_visible("#help-five"))
        check("the page text no longer calls it Help", "<strong>Help</strong>" not in t.read("index.html"))

        print("\n--- 6. Credits link in How it works > About ---")
        page.evaluate("document.getElementById('about').open = true")
        link = page.locator("#help-credits-link")
        check("one Credits link in the About fold-out", link.count() == 1 and link.inner_text().strip() == "Credits")
        check("it is at least 44 px tall", link.bounding_box()["height"] >= 43.5, link.bounding_box())
        link.click()
        wait_settled(page)
        check("it opens the Credits sub-tab", page.is_visible("#view-credits") and not page.is_visible("#view-help"))

        print("\n--- 5. Feedback card ---")
        t.load(page, settings={"examplesChecked": True}, launch=True)
        page.evaluate("() => { window.feedbackCardWanted = () => true; renderFeedbackCard(); }")
        text = page.evaluate("document.getElementById('feedback-card').innerText")
        check("the card line is the new text", "Anything missing or broken?" in text and "Enjoying" not in text, text)
        check("same buttons", "Give feedback" in text and "Not now" in text, text)

        for w, h in ((390, 844), (360, 640), (320, 568)):
            page.set_viewport_size({"width": w, "height": h})
            t.load(page, settings={"examplesChecked": True}, launch=True)
            page.click('.tabs button[data-tab="guides"]')
            wait_settled(page)
            wide = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
            check(f"{w} px: the switch with the longer label does not scroll sideways", not wide)

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

main()
