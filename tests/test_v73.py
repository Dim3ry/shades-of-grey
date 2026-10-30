"""v73 tests for Minifolio (chunk 4.3: next steps from each Mentor pick).

What changed:
 Each paint pick in Ask the Mentor gets Add to shopping list in plain view (outside the closed Shop links fold-out), next to the
 Use in a recipe, Add to a recipe and Similar paints buttons it already shared with Colour ideas. The shopping list remembers
 "Compendium: Ask the Mentor". The button is not hidden by Settings -> Shop links, and is not offered for a paint you own or a
 made-up example paint. Every action says what it did and has an Undo.

Checks:
1. A pick you do not own shows Add to shopping list without opening anything; the fold-out has the shop links but no second button.
2. Tap it: the line says what was added, the row says it is on the list, the list remembers the Mentor; Undo puts it all back.
3. Settings -> Shop links off: the fold-out is gone, the button stays.
4. A pick you own has no Add to shopping list. A made-up example paint is not offered it.
5. Use in a recipe and Add to a recipe work from a Mentor pick, with an Undo.
6. 390 px and 360 px, dark and light: no sideways scroll, the new button is 44 px or more.
7. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lab_helpers as labh   # X1: the old all-in-one Compendium page (see lab_helpers.py)
import test_v31 as t
import test_v71 as m

load, no_sideways = t.load, t.no_sideways
open_mentor, pick = m.open_mentor, m.pick
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

ROWS = "#cmp-fold-mentor-panel .idea-list > li"
RECIPES = [{"id": 1, "name": "Blue armour", "part": "Armour", "notes": "", "linkUnit": None,
            "steps": [{"technique": "Base coat", "coats": 1, "paints": [{"paint": 1, "mix": 100}], "ratio": "", "note": "", "optional": False}]}]

def toast(page):
    return page.evaluate("() => document.getElementById('toast-text').textContent")

def undo(page):
    page.click("#toast-undo")
    page.wait_for_timeout(250)

def listed(page):
    return page.evaluate("() => book.paints.filter(p => p.status === 'wishlist').map(p => ({ name: p.name, from: p.shopFrom || [] }))")

def not_owned_row(page):
    """The first Mentor row whose paint you do not own (it has the new button)."""
    for i in range(page.locator(ROWS).count()):
        row = page.locator(ROWS).nth(i)
        if row.locator(".shop-add-row button").count():
            return row
    return None

def name_of(row):
    return row.locator(".idea-name").first.evaluate("e => e.childNodes[0].textContent")

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        print("\n--- 1. Add to shopping list in plain view ---")
        load(page, paints=[], recipes=RECIPES)
        open_mentor(page)
        pick(page, "base", "Macragge")
        row = not_owned_row(page)
        check("a pick you do not own has Add to shopping list", row is not None)
        name = name_of(row)
        btn = row.locator(".shop-add-row button")
        check("it is visible without opening Shop links", btn.is_visible() and btn.inner_text() == "Add to shopping list")
        check("it is not inside the closed fold-out", page.evaluate("(r) => !r.closest('details')", btn.element_handle()))
        foldout = row.locator("details.shop-more")
        check("the fold-out still has shop links and no second Add button", foldout.locator("a").count() >= 1 and foldout.locator("button").count() == 0)
        check("the row keeps Use in a recipe, Add to a recipe and Similar paints",
              row.locator(".paint-recipe-buttons button").all_inner_texts() == ["Use in a recipe", "Add to a recipe", "Similar paints"])

        print("\n--- 2. Add and Undo ---")
        btn.click()
        page.wait_for_timeout(300)
        check("the line says what was added", f"Added {name} to your shopping list" in toast(page), toast(page))
        # X1/X5: the source now says "Colour Lab: Paint Picker" (renamed in X5; was "Compendium: Ask the Mentor")
        check("the paint is on the list and the list remembers the Mentor", [x for x in listed(page) if x["name"] == name and "Colour Lab: Paint Picker" in x["from"]], listed(page))
        row = page.locator(ROWS).filter(has=page.locator(".idea-name", has_text=name)).first
        check("the same row now says On your shopping list, and its button is gone",
              "On your shopping list" in row.locator(".shop-add-row").inner_text() and row.locator(".shop-add-row button").count() == 0, row.locator(".shop-add-row").inner_text())
        undo(page)
        check("Undo takes it off the list and the button comes back", not listed(page) and page.locator(f"{ROWS} .shop-add-row button").count() >= 1)

        print("\n--- 3. Shop links switched off ---")
        load(page, paints=[], settings={"hideShopLinks": True})
        open_mentor(page)
        pick(page, "base", "Macragge")
        check("no Shop links fold-out on the picks", page.locator(f"{ROWS} details.shop-more").count() == 0)
        check("Add to shopping list is still there", page.locator(f"{ROWS} .shop-add-row button").count() >= 1)

        print("\n--- 4. Owned and made-up paints ---")
        load(page)   # the usual palette: Macragge Blue and others are owned
        open_mentor(page)
        pick(page, "base", "Macragge")
        owned = [page.locator(ROWS).nth(i) for i in range(page.locator(ROWS).count()) if "You own this" in page.locator(ROWS).nth(i).inner_text()]
        check("there is a pick you own, and it has no Add to shopping list", owned and all(r.locator(".shop-add-row").count() == 0 for r in owned))
        made_up = page.evaluate("() => { const n = EXAMPLE_RECIPES[0].steps[0].paints[0][1]; return [realPaintForShop({ brand: '', name: n }), realPaintForShop({ brand: 'Vallejo', name: 'Ink Sky' }), realPaintForShop({ brand: 'Citadel', name: 'Not In My Palette' })]; }")
        check("a made-up example paint is not offered it, a real unowned paint is", made_up == [False, False, True], made_up)

        print("\n--- 5. Recipe actions from a pick ---")
        load(page, paints=[], recipes=RECIPES)
        open_mentor(page)
        pick(page, "base", "Macragge")
        row = not_owned_row(page)
        name = name_of(row)
        row.locator("button", has_text="Use in a recipe").click()
        page.wait_for_timeout(300)
        check("Use in a recipe starts a recipe with the paint in step 1", page.evaluate("() => recipeDraft && recipeDraft.steps[0].paints.map(p => p.name)") == [name])
        check("the line says so and has an Undo", f"Started a new recipe with {name}" in toast(page) and page.is_visible("#toast-undo"), toast(page))
        undo(page)
        check("Undo closes it again", page.evaluate("() => recipeDraft") is None)
        labh.go_compendium(page)
        open_mentor(page)
        row = not_owned_row(page)
        row.locator("button", has_text="Add to a recipe").click()
        row.locator(".paint-recipe-picker select").first.select_option("1")
        row.locator(".paint-recipe-picker .primary-button").click()
        page.wait_for_timeout(300)
        check("Add to a recipe adds a new step and says so", "Blue armour" in toast(page) and page.evaluate("() => recipeById(1).steps.length") == 2, toast(page))
        undo(page)
        check("Undo puts the recipe back", page.evaluate("() => recipeById(1).steps.length") == 1)

        print("\n--- 6. Phone sizes ---")
        for w in (390, 360):
            for scheme in ("dark", "light"):
                page.set_viewport_size({"width": w, "height": 844})
                page.emulate_media(color_scheme=scheme)
                load(page, paints=[])
                open_mentor(page)
                pick(page, "base", "Macragge")
                page.wait_for_timeout(200)
                tall = page.evaluate("() => [...document.querySelectorAll('#cmp-fold-mentor-panel .shop-add-row button')].every(b => b.getBoundingClientRect().height >= 44)")
                check(f"{w} px {scheme}: no sideways scroll, Add to shopping list is 44 px or more", no_sideways(page) and tall)

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
