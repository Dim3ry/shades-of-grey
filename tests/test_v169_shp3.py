"""SHP3 tests for Minifolio: add to the shopping list from more places, and the three Add buttons inside Shopping.

New behaviour only:
1. The add button under the Shopping tabs changes its words with the tab (+ Add paint, + Add gear, + Add model).
2. + Add paint: search, Add puts the paint on the list once, a second tap cannot duplicate, Undo, an owned paint says so.
3. + Add gear: product types grouped by guide, Add once, Undo.
4. + Add model: the Models add form opens in Shopping and saves to the Wishlist.
5. Suggested also offers Running low paints, added only when tapped, then Undo puts it back.
6. The colour wheel panel's paint rows have Add to shopping list in plain view, also with Show shop links off.
7. The example paint line, and the empty states.
8. 390, 360 and 320 px, dark and light: no sideways scroll, tap targets 44 px or more.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def P(i, name, **more):
    return dict({"id": i, "brand": "Citadel", "name": name, "colour": "#3366aa"}, **more)

PAINTS = [P(1, "Alpha Blue", status="wishlist"), P(2, "Delta Owned", status="owned"), P(3, "Low Green", colour="#33aa55", status="low")]
SETTINGS = {"tab": "dashboard", "examplesChecked": True}

def tabs(page):
    return [b.inner_text().strip() for b in page.locator("#shop-seg > button").all()]

def open_shop(page, tab=None):
    page.click("#basket-button")
    page.wait_for_function("() => settings.tab === 'shopping'")
    if tab:
        page.click(f'#shop-seg [data-stab="{tab}"]')
    page.wait_for_timeout(150)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))

        print("\n--- 1. The add button follows the tab ---")
        load(page, paints=PAINTS, settings=SETTINGS)
        open_shop(page, "paints")
        words = []
        for tab in ("paints", "gear", "wishlist"):
            page.click(f'#shop-seg [data-stab="{tab}"]')
            words.append(page.inner_text("#shop-add-btn").strip())
        check("+ Add paint, + Add gear, + Add model", words == ["+ Add paint", "+ Add gear", "+ Add model"], words)

        print("\n--- 2. + Add paint ---")
        page.click('#shop-seg [data-stab="paints"]')
        page.click("#shop-add-btn")
        page.fill(".shop-add-search", "ivory")
        page.wait_for_selector("#shop-add-slot .shop-add-item")
        first = page.locator("#shop-add-slot .shop-add-item").first
        pick_name = first.inner_text().split("\n")[0].split(" · ")[0].strip()
        count_before = page.evaluate("() => shoppingItems().length")
        first.get_by_role("button", name="Add to shopping list").click()
        page.wait_for_timeout(200)
        check("the paint is on the list as Wishlist, once",
              page.evaluate("(n) => shoppingItems().filter(i => i.paint.name === n).length", pick_name) == 1
              and page.evaluate("() => shoppingItems().length") == count_before + 1, pick_name)
        check("the row now says it is on the list, and there is no second Add",
              "On your shopping list" in page.inner_text("#shop-add-slot .shop-add-item") and
              page.locator("#shop-add-slot .shop-add-item").first.get_by_role("button").count() == 0)
        check("the box stays open after an Add", page.locator("#shop-add-slot .shop-add-box").count() == 1)
        page.click("#toast-undo")
        page.wait_for_timeout(200)
        check("Undo takes it off again", page.evaluate("() => shoppingItems().length") == count_before
              and "On your shopping list" not in page.inner_text("#shop-add-slot .shop-add-item"))
        page.fill(".shop-add-search", "Delta Owned")
        page.wait_for_selector("#shop-add-slot .shop-add-item")
        check("a paint you own says so and has no Add", "You own this" in page.inner_text("#shop-add-slot") and
              page.locator("#shop-add-slot .shop-add-item button").count() == 0)
        page.fill(".shop-add-search", "zzzqq")
        check("no match gives one short line", page.inner_text("#shop-add-slot .shop-add-none") == "No paints found.")
        page.keyboard.press("Escape")
        check("Escape closes the box", page.locator("#shop-add-slot .shop-add-box").count() == 0)

        print("\n--- 3. + Add gear ---")
        page.click('#shop-seg [data-stab="gear"]')
        page.click("#shop-add-btn")
        check("types are grouped under a guide title", page.locator("#shop-add-slot .shop-add-group").count() >= 3)
        page.fill(".shop-add-search", "wet palette")
        row = page.locator("#shop-add-slot .shop-add-item", has_text="Wet palette").first
        row.get_by_role("button", name="Add to shopping list").click()
        page.wait_for_timeout(200)
        check("Gear is added once and the tab count follows",
              page.evaluate("() => gearItems().filter(g => g.id === 'wet palette').length") == 1 and tabs(page)[1] == "Gear (1)", tabs(page))
        check("its row says it is on the list", "On your shopping list" in row.inner_text())
        page.click("#toast-undo")
        page.wait_for_timeout(200)
        check("Undo removes it and the Add comes back", page.evaluate("() => gearItems().length") == 0
              and row.get_by_role("button", name="Add to shopping list").count() == 1)
        page.click('#shop-seg [data-stab="wishlist"]')
        check("changing tab closes the box", page.locator("#shop-add-slot .shop-add-box").count() == 0)

        print("\n--- 4. + Add model ---")
        page.click("#shop-add-btn")
        check("the Models add form opens here", page.locator("#shop-add-slot form.wish-form").count() == 1)
        page.fill("#shop-add-slot .w-name", "Test Squad")
        page.fill("#shop-add-slot .w-count", "5")
        page.click("#shop-add-slot button[type=submit]")
        page.wait_for_timeout(250)
        check("Save puts it on the Wishlist tab and closes the form", page.locator("#shop-wish-panel .wish-row", has_text="Test Squad").count() == 1
              and page.locator("#shop-add-slot form").count() == 0 and tabs(page)[2] == "Wishlist (1)", tabs(page))
        check("it is the same Wishlist Models shows", page.evaluate("() => wishes().some(w => w.name === 'Test Squad')"))

        print("\n--- 5. Running low in Suggested ---")
        page.click('#shop-seg [data-stab="paints"]')
        page.wait_for_timeout(150)
        check("Suggested lists the Running low paint, and the list does not hold it yet",
              page.evaluate("() => suggestedItems().some(x => x.paint.name === 'Low Green' && x.word === 'Running low')")
              and not page.evaluate("() => shoppingItems().some(i => i.paint.name === 'Low Green')"))
        page.click(".shop-suggest-head")
        page.locator(".shop-suggest-item", has_text="Low Green").get_by_role("button", name="Add").click()
        page.wait_for_timeout(200)
        check("tapping Add puts it on the list as Wishlist", page.evaluate("() => shoppingItems().some(i => i.paint.name === 'Low Green')"))
        page.click("#toast-undo")
        page.wait_for_timeout(200)
        check("Undo makes it Running low again", page.evaluate("() => paintStatus(book.paints.find(p => p.name === 'Low Green'))") == "low")

        print("\n--- 6. Colour wheel panel ---")
        page.evaluate("() => { settings.hideShopLinks = true; }")
        info = page.evaluate("""() => {
            const door = compendiumDoor();
            const paint = book.paints.find(p => p.name === 'Delta Owned');
            const box = buildPaintPanel(door, { paint, at: wheelPlace(paint), origin: 0, key: 'k' });
            document.body.appendChild(box);
            const adds = [...box.querySelectorAll('.shop-add-row button')].map(b => b.textContent);
            const rows = box.querySelectorAll('.idea-pick').length;
            const own = box.querySelectorAll('.idea-pick .idea-tag');
            box.remove();
            return { adds, rows };
        }""")
        check("with Show shop links off, a paint you do not own still has Add to shopping list in plain view",
              info["adds"] and all(a == "Add to shopping list" for a in info["adds"]), info)

        print("\n--- 7. The example paint line ---")
        page.evaluate("() => { settings.hideShopLinks = false; }")
        ex = [P(7, "Made Up Red", brand="", example=True)]
        rec = [{"id": 1, "name": "Ex", "example": True, "part": "Whole model", "steps": [{"technique": "Layer", "coats": 1, "paints": [{"paint": 7, "mix": 100}]}]}]
        load(page, paints=ex, recipes=rec, settings=SETTINGS)
        page.evaluate("() => { settings.tab = 'recipes'; render(); openRecipe(1); }")
        page.wait_for_selector(".recipe-shop-idle-wrap", state="attached")
        line = page.evaluate("() => document.querySelector('.recipe-shop-idle-wrap').textContent")
        check("an example recipe's disabled Add says why in one plain line", "Example paint. Add your own paint first." in line, line)
        load(page, paints=[], settings=SETTINGS)
        open_shop(page, "paints")
        check("empty Paints tab says what fills it", page.inner_text("#shop-panel .shop-empty") == "Paints you add or mark Wishlist appear here.")
        page.click('#shop-seg [data-stab="gear"]')
        check("empty Gear tab says what fills it", page.inner_text("#shop-gear-panel .shop-empty") == "Gear you add here or from Guides appears here.")
        page.click('#shop-seg [data-stab="wishlist"]')
        check("empty Wishlist tab says what fills it", page.inner_text("#shop-wish-panel .shop-empty") == "Models you add here or in Models appear here.")

        check("no page errors or pop-ups", not errors, errors)
        ctx.close()

        print("\n--- 8. Sizes and looks ---")
        for width, height in ((390, 844), (360, 640), (320, 640)):
            for scheme in ("dark", "light"):
                c = browser.new_context(viewport={"width": width, "height": height}, service_workers="block", reduced_motion="reduce", color_scheme=scheme)
                pg = c.new_page()
                pg.on("pageerror", lambda x: errors.append(str(x)))
                load(pg, paints=PAINTS, settings=SETTINGS)
                small = []
                for tab in ("paints", "gear"):
                    open_shop(pg, tab)
                    pg.click("#shop-add-btn")
                    pg.fill(".shop-add-search", "blue" if tab == "paints" else "palette")
                    pg.wait_for_timeout(150)
                    small += pg.evaluate("""() => [...document.querySelectorAll('#view-shopping button, #view-shopping input:not([type=checkbox])')]
                        .filter(e => e.offsetParent && e.getBoundingClientRect().height < 43.5).map(e => e.tagName + '.' + e.className)""")
                check(f"{width} px {scheme}: no sideways scroll, no control under 44 px", no_sideways(pg) and not small, (no_sideways(pg), small))
                c.close()
        browser.close()

    check("no page errors in the size runs", not errors, errors)
    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)

if __name__ == "__main__":
    main()
