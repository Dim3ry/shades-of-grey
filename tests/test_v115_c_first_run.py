"""Chunk C tests for Minifolio: first-run clarity. New behaviour only.

1. The start page has one line under the name (6 words or fewer) and no version number; the version is still in Updates.
2. The page has a description and share tags.
3. Help starts with the "5 things to know" card, with the five lines as written.
4. The Dashboard says what Done means, using the real stage name, and leaves the line out with no units.
5. With no units the graph card is left out, and with no paints the Palette tile is left out; both come back with data.
6. Game and Faction: a clear button (44 px, named), select-all on focus, and the clear button hides while the box is empty.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
import version_helpers as vh
from launch_helpers import tap_tab, wait_settled

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

FIVE = [
    "Add units in Models, then tap the arrows to move them through the stages.",
    "Painting holds recipes (one part of a model) and schemes (a whole army).",
    "Colour Lab suggests paints that go together. Add any to your shopping list.",
    "Mentor answers painting questions from built-in guides. It isn't AI and works offline.",
    "Everything stays on this phone. Save a backup in Settings.",
]

def unit(i):
    return {"id": i, "name": "Unit %d" % i, "count": 5, "stage": 1, "faction": "Orks", "hobby": "40K", "paints": [], "photos": []}

SHOWN = "(sel) => { const e = document.querySelector(sel); if (!e) return false; const r = e.getBoundingClientRect(); return getComputedStyle(e).display !== 'none' && r.width > 0 && r.height > 0; }"

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. Start page line and version ---")
        t.load(page, units=[unit(1)], launch=True)
        line = page.inner_text("#start-line").strip()
        check("the start page line is the agreed words", line == "Track your miniature painting", line)
        check("it is 6 words or fewer", len(line.split()) <= 6)
        check("the line shows on the start page", page.evaluate(SHOWN, "#start-line"))
        check("the version is not shown on the start page", not page.evaluate(SHOWN, "#version-tag"))
        tap_tab(page, "dashboard")
        wait_settled(page)
        check("the line is gone once you leave the start page", not page.evaluate(SHOWN, "#start-line"))
        check("the version still shows next to the title on a section", page.evaluate(SHOWN, "#version-tag"))
        page.click('nav button[data-tab="guides"]')
        wait_settled(page)
        page.click('#more-seg button[data-page="updates"]')
        wait_settled(page)
        check("Updates says which version you are on", "version" in page.inner_text("#version-note").lower() and vh.current() in page.inner_text("#version-note"))

        print("\n--- 2. Search and share tags ---")
        meta = page.evaluate("""() => { const g = (q) => { const e = document.querySelector(q); return e ? e.content : null; };
          return { desc: g('meta[name=description]'), ogt: g('meta[property="og:title"]'), ogd: g('meta[property="og:description"]'), type: g('meta[property="og:type"]'),
                   url: g('meta[property="og:url"]'), img: g('meta[property="og:image"]'), tw: g('meta[name="twitter:card"]') }; }""")
        check("description is there and under 160 characters", meta["desc"] and len(meta["desc"]) < 160, meta["desc"])
        check("description makes no free or paid claim", meta["desc"] and "free" not in meta["desc"].lower() and "paid" not in meta["desc"].lower())
        check("og:title, og:description, og:type, og:url", meta["ogt"] == "Minifolio" and meta["ogd"] and meta["type"] == "website" and meta["url"] == "https://minifolio.app/", meta)
        check("og:image is the app icon and twitter:card is summary", meta["img"] == "https://minifolio.app/icon-512.png" and meta["tw"] == "summary", meta)

        print("\n--- 3. Help: 5 things to know ---")
        page.click('#more-seg button[data-page="help"]')
        wait_settled(page)
        first = page.evaluate("() => document.querySelector('#view-help > :first-child').id")
        check("the card is the first thing in Help", first == "help-five", first)
        check("heading is 5 things to know", page.inner_text("#help-five h2").strip() == "5 things to know")
        items = page.eval_on_selector_all("#help-five ol > li", "els => els.map(e => e.textContent.trim())")
        check("the five lines are exactly as written", items == FIVE, items)
        check("nothing else is in the card", page.evaluate("() => [...document.querySelectorAll('#help-five > *')].map(e => e.tagName).join()") == "H2,OL")

        print("\n--- 4. What Done means ---")
        # (saved units with no saved settings get the old 5 stages, so the default 8 are seeded on purpose)
        t.load(page, units=[unit(1)], settings={"stages": ["Unassembled", "Part assembled", "Assembled", "Primed", "Part painted", "Battle ready", "Needs touch-ups", "Parade ready"], "doneFrom": 5})
        tap_tab(page, "dashboard")
        wait_settled(page)
        check("default stages: Done means Battle ready or later.", page.inner_text("#done-meaning").strip() == "Done means Battle ready or later.", page.inner_text("#done-meaning"))
        stages = ["Boxed", "Built", "Primed", "Finished"]
        t.load(page, units=[unit(1)], settings={"stages": stages, "doneFrom": 3})
        tap_tab(page, "dashboard")
        wait_settled(page)
        check("renamed stages: the line uses the real name, and no 'or later' on the last stage", page.inner_text("#done-meaning").strip() == "Done means Finished.", page.inner_text("#done-meaning"))
        t.load(page, units=[unit(1)], settings={"stages": stages, "doneFrom": 2})
        tap_tab(page, "dashboard")
        wait_settled(page)
        check("a middle stage reads 'Primed or later'", page.inner_text("#done-meaning").strip() == "Done means Primed or later.", page.inner_text("#done-meaning"))
        t.load(page, units=[])
        tap_tab(page, "dashboard")
        wait_settled(page)
        check("no units: the line is left out", not page.evaluate(SHOWN, "#done-meaning"))

        print("\n--- 5. Empty tiles ---")
        t.load(page, paints=[], units=[])
        tap_tab(page, "dashboard")
        wait_settled(page)
        check("no units: the graph card is left out", not page.evaluate(SHOWN, "#history-card"))
        check("no paints: the Palette tile is left out", not page.evaluate(SHOWN, "#palette-card"))
        check("the Achievements placeholder is untouched", page.evaluate(SHOWN, "#achievements-card") and "Coming soon" in page.inner_text("#achievements-card"))
        t.load(page, paints=None, units=[unit(1)])
        tap_tab(page, "dashboard")
        wait_settled(page)
        check("with a unit the graph card is back", page.evaluate(SHOWN, "#history-card"))
        check("with paints the Palette tile is back", page.evaluate(SHOWN, "#palette-card"))

        print("\n--- 6. Game and Faction ---")
        t.load(page, units=[unit(1)], settings={"lastGame": "Sci-fi", "lastFaction": "Orks"})
        tap_tab(page, "units")
        wait_settled(page)
        page.click("#toggle-add")
        check("the boxes are filled with the last values", page.input_value("#hobby-input") == "Sci-fi" and page.input_value("#faction-input") == "Orks")
        for box, clear, name in (("#hobby-input", "#clear-game", "Clear game"), ("#faction-input", "#clear-faction", "Clear faction")):
            r = page.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.width, r.height, document.querySelector(s).getAttribute('aria-label')]; }", clear)
            check(name + ": 44 px tap area and its name", r[0] >= 44 and r[1] >= 44 and r[2] == name, r)
            page.focus(box)
            page.wait_for_timeout(60)
            sel = page.evaluate("(s) => { const e = document.querySelector(s); return [e.selectionStart, e.selectionEnd, e.value.length]; }", box)
            check(name + ": focusing selects the whole value", sel[0] == 0 and sel[1] == sel[2] and sel[2] > 0, sel)
            page.click(clear)
            check(name + ": the x empties the box and keeps the cursor in it", page.input_value(box) == "" and page.evaluate("(s) => document.activeElement === document.querySelector(s)", box))
            check(name + ": the x hides while the box is empty", not page.evaluate(SHOWN, clear))
        check("maxlength is kept", page.get_attribute("#hobby-input", "maxlength") == "80" and page.get_attribute("#faction-input", "maxlength") == "80")
        for w in (360, 320):
            page.set_viewport_size({"width": w, "height": 640})
            page.fill("#hobby-input", "Sci-fi")
            check("%d px: no sideways scroll with the x showing" % w, page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth"))

        check("no page errors", not errors, errors)
        browser.close()
    print("\n%d/%d passed" % (sum(results), len(results)))
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
