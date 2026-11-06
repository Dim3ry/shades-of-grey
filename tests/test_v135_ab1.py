"""AB1 tests for Minifolio (wording sweep from the approved AI-tells list). New behaviour only:
1. Each new line is shown where it lives: Dashboard empty line, Mentor box placeholder, Saved toast, empty Models / Recipes / Your Palette.
2. The delete question reads "Delete your only unit?" with 1 unit and "Delete all 3 units?" with several; No is the filled button.
3. Colour match words are Close / Near / Not close and "Yours, not close".
4. The Dashboard headings and chart legend, the Updates heading.
5. The Palette tile: "No paints marked Owned yet." with no Owned paints (strip hidden); a gap line "No orange or yellow yet" otherwise; no "Gap" words.
6. A kept draft card reads "Your pasted recipe notes are still here."
Run with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def unit(i):
    return {"id": i, "name": f"Squad {i}", "hobby": "40K", "stage": 2, "count": 5, "added": "2026-10-01", "log": [["2026-10-01", 2]]}

def text(page, sel):
    return page.evaluate("(s) => (document.querySelector(s) || {}).textContent || ''", sel).strip()

def paints(status):
    mk = lambda i, n, c: {"id": i, "name": n, "colour": c, "status": status, "brand": "", "type": ""}
    return [mk(901, "Zed red", "#c0282c"), mk(902, "Ash red", "#d03030"), mk(904, "Sky blue", "#3a7bd5"), mk(905, "Leaf green", "#3f9a52"), mk(906, "Pine", "#2f8f4a")]

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width, height in [(390, 844), (360, 640)]:
            ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
            page = ctx.new_page()
            page.on("pageerror", lambda x: errors.append(str(x)))

            print(f"\n--- 1. Empty collection, {width} px ---")
            t.load(page, paints=[], units=[])
            page.evaluate("() => document.querySelector('.tabs button[data-tab=dashboard]').click()"); t.quiet(page)
            check("Dashboard headline with no units is just 'No units yet.'", text(page, "#done-summary") == "No units yet.", text(page, "#done-summary"))
            check("Dashboard headings are Added and painted / Where everything is / Armies",
                  [text(page, s) for s in ("#history-card h2", "#stage-card h2", "#faction-card h2")] == ["Added and painted", "Where everything is", "Armies"])
            check("the chart legend reads Added and Painted", [x.strip() for x in page.evaluate("() => [...document.querySelectorAll('#history-legend .legend-key')].map(k => k.textContent)")] == ["Added", "Painted"])
            page.evaluate("() => document.querySelector('nav button[data-tab=units]').click()"); t.quiet(page)
            check("empty Models says 'Nothing on the bench yet.'", text(page, "#units-empty").startswith("Nothing on the bench yet."), text(page, "#units-empty"))
            align = page.evaluate("() => [getComputedStyle(document.getElementById('units-empty')).textAlign, getComputedStyle(document.querySelector('#units-empty .button-grid')).textAlign, document.querySelector('#units-empty .button-grid').getBoundingClientRect().left - document.getElementById('units-empty').getBoundingClientRect().left]")
            check("the empty block and its buttons are left-aligned", align[0] in ("left", "start") and align[1] in ("left", "start") and align[2] < 4, align)
            check("no sideways scroll", page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth"))
            page.evaluate("() => document.querySelector('nav button[data-tab=recipes]').click()"); t.quiet(page)
            check("empty Recipes says 'Nothing written down yet.'", "Nothing written down yet." in text(page, "#recipe-list .empty"), text(page, "#recipe-list .empty"))
            page.evaluate("() => { settings.recipeView = 'palette'; renderRecipes(); }"); t.quiet(page)
            check("empty Your Palette says 'Nothing in the paint rack yet.'", text(page, "#paint-list .empty") == "Nothing in the paint rack yet.", text(page, "#paint-list .empty"))
            page.evaluate("() => document.getElementById('mentor-button').click()"); t.quiet(page)
            check("the Mentor box placeholder is 'Ask away'", page.evaluate("() => { const i = document.querySelector('.mentor-input'); return !!i && i.placeholder === 'Ask away'; }"))
            ctx.close()

        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 2. The delete question ---")
        def ask(units):
            t.load(page, units=units)
            page.evaluate("() => { document.getElementById('delete-all').click(); }"); t.quiet(page)
            return text(page, "#dialog-message"), page.evaluate("() => [document.getElementById('dialog-no').className, document.getElementById('dialog-yes').className]")
        msg, cls = ask([unit(1)])
        check("with 1 unit: 'Delete your only unit?'", msg.startswith("Delete your only unit?"), msg)
        check("Yes and No stay; No is the filled button", "primary-button" in cls[0] and "danger-button" in cls[1], cls)
        msg, _ = ask([unit(1), unit(2), unit(3)])
        check("with 3 units: 'Delete all 3 units?'", msg.startswith("Delete all 3 units?"), msg)

        print("\n--- 3. Match words ---")
        words = page.evaluate("() => MinifolioColour.FIT_WORDS")
        check("fit words are Close, Near, Not close, Yours, not close", [words[k] for k in ("good", "close", "poor", "ownedPoor")] == ["Close", "Near", "Not close", "Yours, not close"], words)

        print("\n--- 4. Updates heading ---")
        page.evaluate("() => showTab('updates')"); t.quiet(page)
        check("the Updates feedback card heading is 'Bugs and ideas'", page.evaluate("() => [...document.querySelectorAll('#view-updates h2')].some(h => h.textContent.trim() === 'Bugs and ideas')"))

        print("\n--- 5. Palette tile ---")
        t.load(page, paints=paints("wishlist"), units=[unit(1)])
        page.evaluate("() => document.querySelector('.tabs button[data-tab=dashboard]').click()"); t.quiet(page)
        lines = page.evaluate("() => [...document.querySelectorAll('#palette-lines span')].map(s => s.textContent)")
        check("no Owned paints: the strip is hidden and the tile says so", page.evaluate("() => document.getElementById('palette-strip').hidden") and "No paints marked Owned yet." in lines, lines)
        t.load(page, paints=paints("owned"), units=[unit(1)])
        page.evaluate("() => document.querySelector('.tabs button[data-tab=dashboard]').click()"); t.quiet(page)
        lines = page.evaluate("() => [...document.querySelectorAll('#palette-lines span')].map(s => s.textContent)")
        check("with Owned paints: 'No orange or yellow yet'", "No orange or yellow yet" in lines, lines)
        check("empty blocks carry no word", page.evaluate("() => document.querySelectorAll('#palette-strip .palette-gap').length === 0 && !document.getElementById('palette-strip').hidden"))

        print("\n--- 6. A kept draft ---")
        t.load(page, paints=[], units=[])
        page.evaluate("() => { draftOffers.paste = { text: 'a pasted recipe' }; fillDraftCard('paste', true); }")
        check("a kept paste draft reads 'Your pasted recipe notes are still here.'", text(page, "#draft-card-paste strong") == "Your pasted recipe notes are still here.", text(page, "#draft-card-paste"))
        ctx.close()
        browser.close()
    check("no page errors", not [e for e in errors if "woff2" not in e], errors)
    bad = results.count(False)
    print(f"\n{len(results) - bad} passed, {bad} failed")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
