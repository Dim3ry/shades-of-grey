"""v76 tests for Minifolio (chunk 5.3: long names wrap, and a restore says when it lowered counts).

What changed:
 A very long recipe or paint name wraps in the recipe list, recipe view, paint list and paint detail instead of
 stretching the page sideways. Restore backup says how many unit counts it lowered to the 999 limit.

Checks:
1. A 320-character recipe name and a 300-character paint name: no sideways scroll at 390 px and 360 px, dark and light.
2. Restore backup with two counts over 999 says "2 counts lowered to 999"; one over says "1 count".
3. A backup with nothing over 999 says nothing about counts.
4. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

LONG_RECIPE = "R" * 320
LONG_PAINT = "P" * 300
PAINTS = [{"id": 1, "brand": "Citadel", "name": LONG_PAINT, "colour": "#0d407f", "status": "owned"}]
RECIPES = [t.rec(1, LONG_RECIPE, "Whole model", [1])]

def unit(i, count):
    return {"id": i, "name": f"Unit {i}", "hobby": "40K", "faction": "Orks", "stage": 1, "count": count}

def restore(page, models):
    backup = {"app": "Shades of Grey", "version": 6, "models": models}
    page.set_input_files("#restore-file", files=[{"name": "b.json", "mimeType": "application/json", "buffer": json.dumps(backup).encode()}])
    page.click("#dialog-yes")
    page.wait_for_function("() => document.getElementById('toast-text').textContent.includes('Backup restored')")
    return page.inner_text("#toast-text")

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        print("\n--- 1. Long names wrap ---")
        load(page, paints=PAINTS, recipes=RECIPES, units=[])
        for width, scheme in ((390, "dark"), (390, "light"), (360, "dark"), (360, "light")):
            page.set_viewport_size({"width": width, "height": 844})
            page.emulate_media(color_scheme=scheme)
            page.click('nav button[data-tab="recipes"]')
            page.click('[data-view="recipes"]')
            page.wait_for_timeout(150)
            listed = no_sideways(page)
            page.evaluate("openRecipe(1)")
            page.wait_for_timeout(150)
            viewed = no_sideways(page)
            page.click('nav button[data-tab="recipes"]')
            page.click('[data-view="palette"]')
            page.wait_for_timeout(150)
            paint_list = no_sideways(page)
            page.click(".paint-head >> nth=0")
            page.wait_for_timeout(150)
            check(f"{width} px {scheme}: recipe list, recipe view, paint list and paint detail do not scroll sideways",
                  listed and viewed and paint_list and no_sideways(page), (listed, viewed, paint_list))

        print("\n--- 2 and 3. Restore says when it lowered counts ---")
        page.set_viewport_size({"width": 390, "height": 844})
        load(page, units=[])
        text = restore(page, [unit(1, 5000), unit(2, 1200), unit(3, 10)])
        check("two counts over 999: the toast says 2 counts were lowered to 999", "2 counts lowered to 999" in text, text)
        check("and the counts are 999, 999, 10", page.evaluate("models.map(m => m.count)") == [999, 999, 10])
        page.reload(); page.wait_for_timeout(400)
        text = restore(page, [unit(1, 1000), unit(2, 10)])
        check("one count over 999: the toast says 1 count", "1 count lowered to 999" in text, text)
        page.reload(); page.wait_for_timeout(400)
        text = restore(page, [unit(1, 999), unit(2, 10)])
        check("nothing over 999: no mention of counts", "lowered" not in text, text)

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
