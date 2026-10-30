"""A1 tests for Minifolio (chunks U1 and U1b: basket and filter fixes, then the Bought tick on the shopping list).

New behaviour only:
1. Remove: a paint added from the Compendium, from a recipe and by hand can each be taken off the list, with Undo for that paint alone.
2. Every recipe has an Add to shopping list button: counted when paints can be added, greyed with one line (and no adding) on an example recipe.
3. Toggling a brand keeps the place: the brand rows in Settings and Your Palette stay slid where they were, and the page does not jump.
4. Bought: tick greys the row, then it moves to a closed "Bought · n" section; the paint is Owned everywhere; Undo and Add back restore the
   status it had; Clear bought asks first; the history is in backups and an old backup without it still loads; the shop bar and
   the recipe button ignore ticked paints.
5. 390 and 360 px, dark and light: no sideways scroll, tap targets 44 px or more.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys, json
from playwright.sync_api import sync_playwright
from launch_helpers import leave_launch, open_settings

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def P(i, name, **more):
    return dict({"id": i, "brand": "Citadel", "name": name, "colour": "#3366aa"}, **more)

WISH = {"status": "wishlist", "shopFrom": ["Recipe: Blue"]}
PAINTS = [P(1, "Alpha Blue", **WISH), P(2, "Beta Red", **WISH), P(3, "Gamma Green", **WISH), P(4, "Delta Owned", status="owned"),
          P(5, "Epsilon Plain")]
SETTINGS = {"tab": "recipes", "recipeView": "shopping", "examplesChecked": True}
PAUSE = 1100   # the grey pause (700 ms) plus a margin

def open_shop(page):
    page.evaluate("() => { settings.recipeView = 'shopping'; renderRecipes(); }")
    page.click('nav button[data-tab="recipes"]')
    page.wait_for_timeout(250)

def names(page):
    return sorted(page.evaluate("shoppingItems().map(i => i.paint.name)"))

def status(page, pid):
    return page.evaluate("(id) => paintStatus(book.paints.find(p => p.id === id))", pid)

def tick(page, name):
    page.locator("#shop-panel .shop-item", has_text=name).locator(".shop-tick").click()
    page.wait_for_timeout(PAUSE)

def small_taps(page):
    return page.evaluate("""() => [...document.querySelectorAll('#shop-panel button')].filter(b => b.offsetParent)
        .map(b => Math.round(b.getBoundingClientRect().height)).filter(h => h < 44)""")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. Remove an item ---")
        rec = t.rec(1, "Blue", "Armour", [1, 2])
        load(page, paints=PAINTS, recipes=[rec], settings=SETTINGS)
        open_shop(page)
        check("each row has a tick box and a Remove button", page.locator("#shop-panel .shop-item").count() == 3
              and page.locator("#shop-panel .shop-remove").count() == 3)
        # three ways onto the list: by hand (Wishlist status, Alpha above), from a recipe, from the Compendium (a built-in paint)
        page.evaluate("() => addSchemePaintsToShoppingList([palettePaintFor({ name: 'Epsilon Plain', brand: 'Citadel' })], 'Recipe: Blue')")
        page.evaluate("() => addToShoppingList({ brand: 'Citadel', name: 'Macragge Blue', colour: '#0d407f' }, 'Compendium: Colour wheel')")
        open_shop(page)
        before = names(page)
        check("three kinds of item are on the list", len(before) == 5 and "Macragge Blue" in before and "Epsilon Plain" in before, before)
        for name in ("Alpha Blue", "Epsilon Plain", "Macragge Blue"):
            page.locator("#shop-panel .shop-item", has_text=name).locator(".shop-remove").click()
            page.wait_for_timeout(150)
            check(f"Remove takes {name} off the list and says so", name not in names(page) and "Removed" in page.inner_text("#toast"))
        check("a removed paint is Not owned, and the basket count follows", status(page, 1) == "notowned"
              and page.inner_text("#basket-button").strip() == "2", page.inner_text("#basket-button"))
        page.click("#toast-undo")
        page.wait_for_timeout(150)
        check("Undo puts back only that paint, with where it came from",
              # X1: a stored "Compendium: ..." source is shown as "Colour Lab: ..." (display only)
              "Macragge Blue" in names(page) and "Alpha Blue" not in names(page) and page.evaluate("shoppingItems().find(i => i.paint.name === 'Macragge Blue').from[0]") == "Colour Lab: Colour wheel")

        print("\n--- 2. Add to shopping list on every recipe ---")
        load(page, paints=PAINTS, recipes=[t.rec(1, "Blue", "Armour", [1, 5])], settings=dict(SETTINGS, recipeView="recipes"))
        page.evaluate("() => openRecipe(1)")
        page.wait_for_timeout(250)
        btn = page.locator("#recipe-page button.recipe-shop-add")
        check("a recipe with paints to add shows Add to shopping list (1)", btn.count() == 1 and btn.inner_text() == "Add to shopping list (1)", btn.all_inner_texts())
        page.goto(t.URL)   # a brand-new start has the example recipes
        page.evaluate("() => { localStorage.clear(); }")
        page.reload()
        page.wait_for_function("() => typeof renderShopPanel === 'function'")
        page.wait_for_timeout(400)
        leave_launch(page)   # U4b: tap through the start page
        page.evaluate("() => openRecipe(book.recipes.find(r => r.example === true).id)")
        page.wait_for_timeout(300)
        idle = page.locator("#recipe-page .shop-idle-button")
        check("an example recipe has the same button, greyed out", idle.count() == 1 and idle.inner_text() == "Add to shopping list"
              and idle.get_attribute("aria-disabled") == "true")
        check("with one short line saying why", "made up" in page.inner_text("#recipe-page .shop-idle .hint"), page.inner_text("#recipe-page .shop-idle .hint"))
        idle.dispatch_event("click")
        page.wait_for_timeout(150)
        check("tapping it adds nothing", page.evaluate("shoppingItems().length") == 0)

        print("\n--- 3. A brand filter keeps the place ---")
        brands = ["Citadel", "Vallejo", "Army Painter", "Scale75", "AK", "Pro Acryl", "Tamiya", "Green Stuff World", "Mig", "Kimera", "Reaper"]
        many = [P(100 + i, f"Test Paint {i}", brand=brands[i % 11]) for i in range(150)]
        load(page, paints=many, recipes=[t.rec(1, "Blue", "Armour", [100])], settings=dict(SETTINGS, recipeView="palette"))
        page.click('nav button[data-tab="recipes"]')
        page.wait_for_timeout(250)
        row = "#brand-chips"
        page.evaluate("(r) => { document.querySelector(r).scrollLeft = 9999; }", row)
        before = page.evaluate("(r) => document.querySelector(r).scrollLeft", row)
        page.locator(f"{row} .chip").nth(9).click()
        page.wait_for_timeout(300)
        after = page.evaluate("(r) => document.querySelector(r).scrollLeft", row)
        check("Your Palette brand row stays slid to the end when a brand is tapped", before > 300 and abs(after - before) < 60, (before, after))
        page.evaluate("() => window.scrollTo(0, 250)")
        top = page.evaluate("(r) => document.querySelector(r).getBoundingClientRect().top", row)
        page.locator(f"{row} .chip").nth(10).click()
        page.wait_for_timeout(300)
        check("and the page stays where it was", abs(page.evaluate("(r) => document.querySelector(r).getBoundingClientRect().top", row) - top) < 3)
        open_settings(page)
        page.wait_for_timeout(250)
        page.evaluate("() => document.querySelector('#brands-card button').click()")
        page.wait_for_timeout(250)
        page.evaluate("() => { document.querySelector('#brand-toggles').scrollLeft = 9999; }")
        for index in (-1, -2):   # turning brands off one after another: it must not go back to the start between taps
            page.locator("#brand-toggles .chip").nth(index).click()
            page.wait_for_timeout(250)
        after = page.evaluate("(() => { const r = document.querySelector('#brand-toggles'); return [r.scrollLeft, r.scrollWidth - r.clientWidth]; })()")
        check("Settings Paint brands stays slid to the end while brands are turned off (it did go back to the start)",
              after[1] > 300 and after[0] > after[1] - 80, after)

        print("\n--- 4. Bought ---")
        load(page, paints=PAINTS, recipes=[t.rec(1, "Blue", "Armour", [1, 2]), t.rec(2, "Red", "Armour", [1, 3])], settings=SETTINGS)
        open_shop(page)
        check("there is no Bought section before anything is ticked", page.locator(".shop-bought").count() == 0)
        page.locator("#shop-panel .shop-item", has_text="Alpha Blue").locator(".shop-tick").click()
        page.wait_for_timeout(200)
        ticking = page.locator("#shop-panel .shop-item.shop-ticking")
        check("ticking greys the row first (and the tick box says it is ticked)", ticking.count() == 1
              and ticking.locator(".shop-tick").get_attribute("aria-checked") == "true")
        page.wait_for_timeout(PAUSE)
        check("then the paint moves to Bought, which is closed and shows its count", "Alpha Blue" not in names(page)
              and page.locator(".shop-bought-head").inner_text() == "Bought · 1" and page.locator(".shop-bought-body").is_hidden())
        check("the paint is Owned in Your Palette, so both recipes that use it have it", status(page, 1) == "owned"
              and page.evaluate("[1, 2].map(id => recipeMissing(recipeById(id)).missing)") == [1, 1])
        check("a message with Undo", "Bought Alpha Blue" in page.inner_text("#toast") and page.locator("#toast-undo").is_visible())
        page.click("#toast-undo")
        page.wait_for_timeout(150)
        check("Undo puts it straight back on the list as it was", "Alpha Blue" in names(page) and status(page, 1) == "wishlist"
              and page.locator(".shop-bought").count() == 0)
        tick(page, "Alpha Blue")
        tick(page, "Beta Red")
        page.click(".shop-bought-head")
        page.wait_for_timeout(100)
        check("opening Bought lists the paints, each with Add back, and a Clear bought button", page.locator(".shop-addback").count() == 2
              and page.locator(".shop-bought-clear").is_visible() and page.locator(".shop-bought-head").inner_text() == "Bought · 2")
        check("the shop bar and Copy as text only have what is still to buy",
              "Alpha Blue" not in page.evaluate("shoppingText(shoppingItems())") and page.evaluate("shopsFor(shoppingItems())[0].paints.length") == 1)
        check("the recipe button does not offer a paint you ticked", page.evaluate("schemePaintsToAdd(recipeShopPaints(recipeById(1))).length") == 0)
        page.locator(".shop-bought-body .shop-item", has_text="Alpha Blue").locator(".shop-addback").click()
        page.wait_for_timeout(150)
        check("Add back returns it to the list with its status and source", "Alpha Blue" in names(page) and status(page, 1) == "wishlist"
              and page.evaluate("shoppingItems().find(i => i.paint.name === 'Alpha Blue').from[0]") == "Recipe: Blue")
        check("the Bought section stays open and now counts 1", page.locator(".shop-bought-head").inner_text() == "Bought · 1"
              and page.locator(".shop-bought-body").is_visible())
        page.click(".shop-bought-clear")
        page.wait_for_timeout(150)
        check("Clear bought asks first", page.locator("#dialog-yes").is_visible() and page.locator(".shop-bought").count() == 1)
        page.click("#dialog-no")
        page.wait_for_timeout(150)
        check("saying no keeps the history", page.locator(".shop-addback").count() == 1)
        page.click(".shop-bought-clear")
        page.click("#dialog-yes")
        page.wait_for_timeout(200)
        check("saying yes clears it for good, and the paint stays Owned", page.locator(".shop-bought").count() == 0 and status(page, 2) == "owned")

        print("\n--- 5. Backup and restore ---")
        tick(page, "Gamma Green")
        saved = page.evaluate("JSON.parse(JSON.stringify(backupData()))")
        check("the bought history is in the backup", saved["recipes"].get("bought") == [{"id": 3, "prev": "wishlist", "from": ["Recipe: Blue"]}], saved["recipes"].get("bought"))
        again = page.evaluate("(b) => cleanRecipeBook(b)", saved["recipes"])
        check("it survives a restore", again.get("bought", [{}])[0].get("id") == 3)
        old = dict(saved["recipes"])
        old.pop("bought")
        check("an old backup without it loads, with no history", "bought" not in page.evaluate("(b) => cleanRecipeBook(b)", old))
        junk = dict(saved["recipes"], bought=[{"id": 999}, {"id": 3, "prev": "nonsense", "from": [5]}, "x", None, {"id": 3}])
        cleaned = page.evaluate("(b) => cleanRecipeBook(b).bought", junk)
        check("damaged entries are dropped, one entry per paint", cleaned == [{"id": 3, "prev": "wishlist", "from": ["5"]}], cleaned)
        page.reload()
        page.wait_for_function("() => typeof renderShopPanel === 'function'")
        page.wait_for_timeout(300)
        leave_launch(page)   # U4b: tap through the start page
        check("the history is still there after reopening the app", page.evaluate("boughtItems().length") == 1)

        print("\n--- 6. Phone sizes, dark and light ---")
        for width in (390, 360):
            for scheme in ("dark", "light"):
                page.close()
                ctx2 = browser.new_context(viewport={"width": width, "height": 800}, service_workers="block", color_scheme=scheme)
                page = ctx2.new_page()
                page.on("pageerror", lambda x: errors.append(str(x)))
                load(page, paints=PAINTS + [P(6, "Zeta Wishlist With A Rather Long Paint Name Indeed", **WISH)],
                     recipes=[t.rec(1, "Blue", "Armour", [1, 2])], settings=SETTINGS)
                open_shop(page)
                tick(page, "Beta Red")
                page.click(".shop-bought-head")
                page.wait_for_timeout(100)
                check(f"{width} px {scheme}: no sideways scroll, every shopping button 44 px or taller",
                      no_sideways(page) and not small_taps(page), small_taps(page))
        check("no page errors", not errors, errors)
        browser.close()

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)

if __name__ == "__main__":
    main()
