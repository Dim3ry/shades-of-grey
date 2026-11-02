"""Chunk RS2 tests for Minifolio: Recipe preferences in Settings. New behaviour only.
1. The Parts and Techniques chips are gone from the recipes page; a "Recipe preferences" link opens Settings at the section.
2. Removing an entry asks first (says how many recipes use it); Cancel keeps it; Remove takes it out and shows Undo, which puts it back.
3. A recipe keeps a removed part and technique, opened and saved; the part filter drops the removed part.
4. A new part or technique used by a saved recipe adds itself to the lists.
5. Taps and sideways scroll at 390, 360 and 320 px wide, dark and light.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import quiet

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block").new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        t.load(page, settings={"tab": "recipes", "recipeView": "recipes", "examplesChecked": True}, recipes=t.RECIPES)
        page.evaluate("() => { book.parts = DEFAULT_PARTS.slice(); book.techniques = DEFAULT_TECHNIQUES.slice(); render(); }")

        # 1. Moved out of the recipes page.
        check("recipes page has no Parts or Techniques chips", page.locator("#recipe-home #part-chips, #recipe-home #technique-chips").count() == 0)
        link = page.locator("#recipe-prefs-link")
        check("Recipe preferences link is on the recipes page, 44 px tall", link.count() == 1 and link.bounding_box()["height"] >= 43.5, link.bounding_box())
        link.click(); quiet(page)
        check("the link opens Settings with the section open", page.evaluate("settings.tab") == "settings" and page.locator("#card-fold-recipe-prefs-panel").is_visible())
        n_parts = page.evaluate("book.parts.length")
        check("every part is listed, each with a remove button", page.locator("#part-chips .chip").count() == n_parts and n_parts > 3)
        check("every technique is listed", page.locator("#technique-chips .chip").count() == page.evaluate("book.techniques.length"))

        # 2. Removing asks first, then Undo.
        used = page.evaluate("book.recipes.filter(r => r.part === 'Armour').length")
        page.locator('#part-chips [aria-label="Remove Armour"]').click(); quiet(page)
        text = page.evaluate("document.getElementById('dialog-message').textContent")
        check("the question names the part and how many recipes use it", "Armour" in text and f"{used} recipes use it" in text, text)
        page.click("#dialog-no"); quiet(page)
        check("Cancel keeps it", "Armour" in page.evaluate("book.parts"))
        page.locator('#part-chips [aria-label="Remove Armour"]').click(); quiet(page)
        page.click("#dialog-yes"); quiet(page)
        check("Remove takes it out of the list", "Armour" not in page.evaluate("book.parts"))
        check("an Undo toast shows", page.locator("#toast-undo").is_visible())
        page.click("#toast-undo"); quiet(page)
        check("Undo puts it back in the same place", page.evaluate("book.parts.indexOf('Armour')") == page.evaluate("DEFAULT_PARTS.indexOf('Armour')"))
        page.locator('#technique-chips [aria-label="Remove Glaze"]').click(); quiet(page)
        check("a technique no recipe uses says so", "No recipes use it" in page.evaluate("document.getElementById('dialog-message').textContent"))
        page.click("#dialog-no"); quiet(page)

        # 3. A recipe keeps a removed value.
        page.locator('#part-chips [aria-label="Remove Armour"]').click(); quiet(page); page.click("#dialog-yes"); quiet(page)
        page.locator('#technique-chips [aria-label="Remove Base coat"]').click(); quiet(page); page.click("#dialog-yes"); quiet(page)
        rec = page.evaluate("book.recipes.find(r => r.part === 'Armour' && r.steps.some(s => s.technique === 'Base coat') ).id")
        before = page.evaluate("(id) => JSON.stringify(recipeById(id).steps.map(s => s.technique))", rec)
        page.evaluate("(id) => { showTab('recipes'); openRecipe(id); }", rec)
        quiet(page)
        check("the recipe still shows its removed part", "Armour" in page.locator("#recipe-page").inner_text())
        opts = page.evaluate("(id) => { const r = recipeById(id); const s = pickOrAdd('parts','part', r.part, 'x', () => {}); return [...s.options].map(o => o.value); }", rec)
        check("the editor menu still offers the recipe's own removed part, once", opts.count("Armour") == 1, opts)
        page.evaluate("(id) => startRecipeDraft(draftFrom(recipeById(id)))", rec)
        quiet(page)
        page.evaluate("saveRecipeDraft()"); quiet(page)
        check("saving keeps the removed part and technique", page.evaluate("(id) => recipeById(id).part", rec) == "Armour"
              and before == page.evaluate("(id) => JSON.stringify(recipeById(id).steps.map(s => s.technique))", rec))
        check("saving does not put the removed entries back in the lists", "Armour" not in page.evaluate("book.parts") and "Base coat" not in page.evaluate("book.techniques"))
        page.evaluate("settings.recipeView = 'recipes'; openRecipeId = null; renderRecipes()")
        filt = page.evaluate("[...document.getElementById('part-filter').options].map(o => o.value)")
        check("the part filter no longer offers the removed part", "Armour" not in filt and "Eyes" in filt, filt)
        check("its recipes still show under All", page.locator("#recipe-list .recipe-item").count() == len(t.RECIPES))

        # 4. New entries add themselves.
        page.evaluate("""() => { const r = book.recipes[0]; startRecipeDraft({ id: null, name: 'Gem test', part: 'Gems', notes: '', linkUnit: null,
            steps: [{ technique: 'Drybrush glow', coats: '1', paints: [{ brand: '', name: 'Test Red', colour: '#aa0000', mix: null }], ratio: '', note: '', optional: false }] }); }""")
        page.evaluate("saveRecipeDraft()"); quiet(page)
        check("a new part from a saved recipe joins the list", "Gems" in page.evaluate("book.parts"))
        check("a new technique from a saved recipe joins the list", "Drybrush glow" in page.evaluate("book.techniques"), page.evaluate("book.techniques"))

        # 5. Phone sizes, dark and light.
        for mode in ("dark", "light"):
            t.load(page, settings={"tab": "settings", "appearance": mode, "examplesChecked": True}, recipes=t.RECIPES)
            for width, height in ((390, 844), (360, 640), (320, 640)):
                page.set_viewport_size({"width": width, "height": height})
                page.evaluate("openCardFold('recipe-prefs')"); quiet(page)
                small = page.evaluate("[...document.querySelectorAll('#recipe-prefs-card .chip')].filter(c => c.getBoundingClientRect().height < 43.5).length")
                check(f"{mode} {width}px: remove buttons are 44 px tall", small == 0, small)
                check(f"{mode} {width}px: no sideways scroll", page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"))
        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
