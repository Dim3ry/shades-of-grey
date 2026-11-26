"""UC1 tests for Minifolio: the Recipes section on an open unit card (new behaviour only).

1. An open card has "Recipes · N" right under the stepper, closed to start with; the old recipe chips, Paints row and Paint recipes list are gone.
2. Open: one row per recipe (name, paint dots, arrow). A tap unrolls its steps (technique, paint, mix, coats, ratio, note, optional); one at a time.
3. Open in Painting goes to the recipe; Back returns to the same unit, still open, at the same scroll place.
4. + Add recipe links a recipe (and offers schemes and a new recipe); Edit shows unlink buttons and turns into Done.
5. No recipes: "Recipes · 0" and + Add recipe only.
6. Phone and wide layouts, the four looks, light and dark: no sideways scroll, tap targets 44 px or more.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from common import open_unit_card

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

PAINTS = [{"id": i, "brand": "Citadel", "name": n, "colour": c} for i, (n, c) in enumerate(
    [("Kantor Blue", "#1b3f94"), ("Macragge Blue", "#0d407f"), ("Fenrisian Grey", "#6d94b3"), ("Nuln Oil", "#14100e")], start=1)]
R1 = {"id": 1, "name": "Deep blue armour", "steps": [
    {"title": "Base", "technique": "Base", "coats": 2, "note": "Thin it a little", "paints": [{"paint": 1, "mix": 100}]},
    {"title": "Mix", "technique": "Glaze", "coats": 1, "ratio": "2:1", "optional": True, "paints": [{"paint": 2, "mix": 67}, {"paint": 4, "mix": 33}]}]}
R2 = {"id": 2, "name": "Cold edges", "steps": [{"title": "Edge", "technique": "Edge", "coats": 1, "paints": [{"paint": 3, "mix": 100}]}]}
R3 = {"id": 3, "name": "Dark wash", "steps": [{"title": "Wash", "technique": "Wash", "coats": 1, "paints": [{"paint": 4, "mix": 100}]}]}
SCHEME = {"id": 1, "name": "Cold look", "faction": "", "recipes": [3]}
SQUAD = {"id": 1, "name": "Blue squad", "hobby": "40K", "stage": 2, "count": 5, "recipes": [1, 2], "added": "2026-10-01", "log": [["2026-10-01", 2]]}
BARE = {"id": 2, "name": "Bare unit", "hobby": "40K", "stage": 0, "count": 1, "added": "2026-10-01", "log": [["2026-10-01", 0]]}
FILLER = [{"id": 10 + i, "name": f"Filler {i}", "hobby": "40K", "stage": 1, "count": 1, "added": "2026-10-01", "log": [["2026-10-01", 1]]} for i in range(12)]
CARD = "li.unit[data-id='1']"

def start(page, units, settings=None, recipes=None, schemes=None):
    load(page, units=units, paints=PAINTS, recipes=recipes or [R1, R2, R3], settings=settings)
    if schemes:
        page.evaluate("(s) => { book.schemes = s; save(); render(); }", schemes)
    page.click('nav button[data-tab="units"]')
    page.wait_for_timeout(250)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        card = lambda uid=1: page.locator(f"li.unit[data-id='{uid}']")

        print("--- 1. The section, closed ---")
        start(page, [SQUAD, BARE] + FILLER, schemes=[SCHEME])
        open_unit_card(page, CARD)
        head = card().locator(".recipes-head")
        check("Recipes · 2 sits right under the stepper, with Details still shut",
              head.inner_text().strip() == "Recipes · 2" and card().locator(".panel").count() == 0
              and page.evaluate("(s) => document.querySelector(s + ' .stepper').nextElementSibling.classList.contains('unit-recipes')", CARD))
        check("it is closed to start with", head.get_attribute("aria-expanded") == "false" and card().locator(".recipe-row").count() == 0)
        check("no recipe chips on the card", card().locator(".recipe-links, .recipe-chip").count() == 0)
        card().locator(".details-toggle").click()
        page.wait_for_timeout(250)
        check("Details no longer holds the Paints row or the Paint recipes list",
              card().locator(".paints-row, .unit-paints, .linked-list").count() == 0 and "Paint recipes" not in card().locator(".panel").inner_text()
              and card().locator(".panel select.jump-stage").count() == 1)
        card().locator(".details-toggle").click()
        page.wait_for_timeout(250)

        print("--- 2. Rows and steps ---")
        head.click()
        page.wait_for_timeout(250)
        rows = card().locator(".recipe-row")
        check("two rows, with names and paint dots", rows.count() == 2 and "Deep blue armour" in rows.nth(0).inner_text()
              and rows.nth(0).locator(".swatch").count() == 3 and rows.nth(0).get_attribute("aria-expanded") == "false")
        rows.nth(0).click()
        page.wait_for_timeout(250)
        text = card().locator(".recipe-unroll").inner_text()
        check("the steps unroll in place in order, with technique, paint, coats, note", card().locator(".unroll-steps > li").count() == 2
              and text.index("1. Base") < text.index("2. Glaze") and "Kantor Blue" in text and "2 coats" in text and "Thin it a little" in text, text)
        check("a mix shows its paints, percentages, ratio and Optional", "Macragge Blue" in text and "67%" in text and "mix 2:1" in text and "optional" in text, text)
        card().locator(".recipe-row").nth(1).click()
        page.wait_for_timeout(250)
        check("only one recipe is open at a time", card().locator(".recipe-unroll").count() == 1 and "Fenrisian Grey" in card().locator(".recipe-unroll").inner_text())
        card().locator(".recipe-row").nth(1).click()
        page.wait_for_timeout(250)
        check("tapping it again rolls it up", card().locator(".recipe-unroll").count() == 0)

        print("--- 3. Open in Painting and back ---")
        card().locator(".recipe-row").nth(0).click()
        page.wait_for_timeout(250)
        page.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); window.scrollTo(0, window.scrollY + r.top - 20); }", CARD)
        page.wait_for_timeout(200)
        y = page.evaluate("window.scrollY")
        card().locator(".recipe-open").click()
        page.wait_for_timeout(500)
        check("it opens that recipe on the Painting tab", page.evaluate("settings.tab") == "recipes" and page.evaluate("openRecipeId") == 1
              and "Deep blue armour" in page.inner_text("#recipe-page"))
        check("the back link names the unit", "Blue squad" in page.locator("#recipe-page .link-button").first.inner_text())
        page.locator("#recipe-page .link-button").first.click()
        page.wait_for_timeout(600)
        back_y = page.evaluate("window.scrollY")
        check("Back returns to Models, the same unit open, its recipe still unrolled",
              page.evaluate("settings.tab") == "units" and card().locator(".recipe-unroll").is_visible() and card().locator(":scope .stepper").is_visible())
        check("at the same scroll place", abs(back_y - y) <= 2 and y > 50, (y, back_y))
        card().locator(".recipe-open").click()
        page.wait_for_timeout(500)
        page.go_back()
        page.wait_for_timeout(600)
        check("the phone's Back button does the same", page.evaluate("settings.tab") == "units" and card().locator(".recipe-unroll").is_visible())

        print("--- 4. Add, Edit and unlink ---")
        add = card().locator("select.recipes-add")
        opts = add.evaluate("e => [...e.options].map(o => o.textContent)")
        check("+ Add recipe lists the recipe not linked yet, the scheme and a new recipe",
              opts[0] == "+ Add recipe" and "Dark wash" in opts and "Apply scheme: Cold look" in opts and opts[-1] == "New recipe for this unit", opts)
        add.select_option(label="Dark wash")
        page.wait_for_timeout(300)
        check("choosing one links it", card().locator(".recipes-head").inner_text().strip() == "Recipes · 3" and card().locator(".recipe-row").count() == 3)
        check("there are no unlink buttons until Edit", card().locator(".recipe-unlink").count() == 0)
        card().locator(".recipes-edit").click()
        page.wait_for_timeout(250)
        check("Edit shows an unlink button on each row and says Done", card().locator(".recipe-unlink").count() == 3
              and card().locator(".recipes-edit").inner_text().strip() == "Done")
        card().locator(".recipe-unlink").nth(2).click()
        page.wait_for_timeout(300)
        check("unlinking drops it", card().locator(".recipes-head").inner_text().strip() == "Recipes · 2"
              and page.evaluate("models[0].recipes") == [1, 2])
        card().locator(".recipes-edit").click()
        page.wait_for_timeout(250)
        check("Done hides the unlink buttons", card().locator(".recipe-unlink").count() == 0)

        print("--- 5. No recipes ---")
        open_unit_card(page, "li.unit[data-id='2']")
        bare = card(2)
        check("Recipes · 0 with + Add recipe and no Edit", bare.locator(".recipes-head").inner_text().strip() == "Recipes · 0")
        bare.locator(".recipes-head").click()
        page.wait_for_timeout(250)
        check("only + Add recipe inside", bare.locator("select.recipes-add").count() == 1 and bare.locator(".recipes-edit, .recipe-row").count() == 0)

        print("--- 6. Looks and sizes ---")
        for theme in ("classic", "parchment", "forge", "bench"):
            for scheme in ("dark", "light"):
                start(page, [SQUAD], settings={"appearance": scheme, "theme": theme})
                open_unit_card(page, CARD)
                card().locator(".recipes-head").click()
                page.wait_for_timeout(200)
                card().locator(".recipe-row").nth(0).click()
                page.wait_for_timeout(200)
                card().locator(".recipes-edit").click()
                page.wait_for_timeout(200)
                for w, h in ((390, 844), (360, 640)):
                    page.set_viewport_size({"width": w, "height": h})
                    page.wait_for_timeout(150)
                    sizes = page.evaluate("""(s) => [...document.querySelectorAll(s + ' .recipes-head, ' + s + ' .recipe-row, ' + s + ' .recipe-unlink, ' + s + ' .recipe-open, ' + s + ' .recipes-add, ' + s + ' .recipes-edit')]
                        .map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; })""", CARD)
                    check(f"{theme} {scheme} {w} px: no sideways scroll, every Recipes control 44 px or more",
                          no_sideways(page) and len(sizes) >= 6 and all(a >= 44 and b >= 44 for a, b in sizes), sizes)
                page.set_viewport_size({"width": 390, "height": 844})
        for width in (900, 1280, 1920):
            page.set_viewport_size({"width": width, "height": 900})
            start(page, [SQUAD])
            open_unit_card(page, CARD)
            page.wait_for_timeout(250)
            card().locator(".recipes-head").click()
            page.wait_for_timeout(250)
            check(f"{width} px: the Recipes section is on the card and nothing scrolls sideways",
                  card().locator(".recipe-row").count() == 2 and no_sideways(page))

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
