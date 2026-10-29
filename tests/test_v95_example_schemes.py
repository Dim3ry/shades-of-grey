"""S2 tests for Minifolio (example schemes with their example recipes nested). New behaviour only:
1. Example cards say "Example scheme" / "Example recipe" in plain text above the name; a scheme of your own has no label.
2. A scheme card lists its recipes as nested rows (name, part and steps, colour dots). Tap a row to open the recipe.
3. More than 3 recipes: the first 3 and "Show all N" (then "Show fewer").
4. Every example recipe sits in at least one example scheme, and the new text has no faction words.
5. Clear examples takes schemes and recipes together; one Undo brings both back; Restore example recipes brings both back;
   an example you changed (so it is yours) is left alone; backup data is the same after Clear and Undo.
6. 390 and 360 px, dark and light: no sideways scroll, rows and Show all 44 px or more.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys, re
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v24 as t

results = []
FACTION_WORDS = re.compile(r"tyranid|space marine|ork|necron|eldar|ultramarine|warhammer|citadel|games workshop|chaos|imperial", re.I)

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def cards(page):
    """Each scheme card: label, name, row texts, the Show all button text."""
    return page.evaluate("""() => [...document.querySelectorAll('#scheme-list .scheme-item')].map(c => ({
        label: (c.querySelector('.example-label') || {}).textContent || '',
        first: c.firstElementChild.className,
        name: c.querySelector('.name').textContent,
        rows: [...c.querySelectorAll('.scheme-recipe-row')].map(r => ({ name: r.querySelector('.scheme-recipe-name').textContent,
            meta: r.querySelector('.scheme-recipe-meta').textContent, dots: r.querySelectorAll('.swatch').length })),
        toggle: (c.querySelector('.scheme-show-all') || {}).textContent || '' }))""")

def counts(page):
    return page.evaluate("() => [book.recipes.length, book.schemes.length, book.paints.length, book.recipes.filter(r => r.example).length, book.schemes.filter(s => s.example).length]")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))

        print("\n--- 1 to 3. Labels and nested rows ---")
        t.fresh(page)
        t.main_tab(page, "recipes")
        t.recipe_view(page, "schemes")
        cs = cards(page)
        check("two example schemes, each labelled Example scheme above its name",
              len(cs) == 2 and all(c["label"] == "Example scheme" and c["first"] == "example-label" for c in cs), cs)
        blue = next(c for c in cs if c["name"] == "Blue army colours")
        green = next(c for c in cs if c["name"] == "Green army colours")
        check("a scheme with 4 recipes shows 3 rows and Show all 4", len(blue["rows"]) == 3 and blue["toggle"] == "Show all 4", blue)
        check("a scheme with 3 recipes shows 3 rows and no Show all", len(green["rows"]) == 3 and green["toggle"] == "", green)
        row = green["rows"][0]
        check("a row has the recipe name, part and step count, and colour dots", row["name"] == "Green skin" and row["meta"] == "Skin · 4 steps" and row["dots"] >= 2, row)
        page.locator("#scheme-list .scheme-show-all").click()
        cs = cards(page)
        blue = next(c for c in cs if c["name"] == "Blue army colours")
        check("Show all opens the 4th row and the button says Show fewer", len(blue["rows"]) == 4 and blue["toggle"] == "Show fewer", blue)
        page.locator("#scheme-list .scheme-show-all").click()
        check("Show fewer goes back to 3", len(next(c for c in cards(page) if c["name"] == "Blue army colours")["rows"]) == 3)
        page.locator("#scheme-list .scheme-recipe-row", has_text="Green skin").click()
        page.wait_for_function("() => !document.getElementById('recipe-page').classList.contains('hidden')")
        check("tapping a row opens that recipe", "Green skin" in page.text_content("#recipe-page h2, #recipe-page"))
        page.evaluate("() => { openRecipeId = null; renderRecipes(); }")

        t.recipe_view(page, "recipes")
        labels = page.evaluate("() => [...document.querySelectorAll('#recipe-list .recipe-item')].map(b => (b.querySelector('.example-label') || {}).textContent)")
        check("all five example recipes say Example recipe", labels == ["Example recipe"] * 5, labels)

        print("\n--- 4. Every example recipe is inside an example scheme; wording ---")
        orphans = page.evaluate("() => book.recipes.filter(r => r.example && !book.schemes.some(s => s.example && s.recipes.includes(r.id))).map(r => r.name)")
        check("no example recipe is left on its own", orphans == [], orphans)
        text = page.evaluate("() => EXAMPLE_SCHEMES.map(s => s.name).concat(EXAMPLE_RECIPES.map(r => r.name + ' ' + r.part)).join(' ') + ' Example scheme Example recipe'")
        check("the example names and labels have no faction words", not FACTION_WORDS.search(text), text)

        print("\n--- 5. Clear, Undo, Restore, user data ---")
        t.recipe_view(page, "schemes")
        before_book = page.evaluate("() => JSON.stringify(backupData())")
        full = counts(page)
        page.click("#examples-card-recipes .clear-recipe-examples")
        page.wait_for_function("() => book.schemes.length === 0")
        check("Clear examples removes the example schemes and recipes together", counts(page)[:2] == [0, 0], counts(page))
        page.click("#toast-undo")
        page.wait_for_function("() => book.schemes.length === 2")
        check("one Undo brings both back, with the rows", counts(page) == full and len(cards(page)) == 2 and len(cards(page)[0]["rows"]) == 3, counts(page))
        check("backup data is the same after Clear and Undo", page.evaluate("() => JSON.stringify(backupData())") == before_book)
        # An edit makes an example yours (the app drops the mark, same as saving an edit): Clear leaves it alone.
        page.evaluate("() => { delete book.recipes.find(r => r.name === 'Green skin').example; delete book.schemes.find(s => s.name === 'Green army colours').example; renderRecipes(); }")
        page.click("#examples-card-recipes .clear-recipe-examples")
        page.wait_for_function("() => book.schemes.length === 1")
        left = page.evaluate("() => [book.schemes.map(s => s.name), book.recipes.map(r => r.name)]")
        check("an example you changed stays after Clear (the scheme and its recipe)", left[0] == ["Green army colours"] and "Green skin" in left[1], left)
        cs = cards(page)
        check("a scheme of your own looks the same but has no label", len(cs) == 1 and cs[0]["label"] == "" and len(cs[0]["rows"]) >= 1, cs)
        page.evaluate("() => addExamples()")
        c = counts(page)
        check("Restore brings the missing examples back and does not duplicate yours", c[1] == 2 and page.evaluate("() => book.schemes.filter(s => s.name === 'Green army colours').length") == 1, c)

        print("\n--- 6. Phone sizes ---")
        for width in (390, 360):
            for scheme in ("dark", "light"):
                ctx2 = browser.new_context(viewport={"width": width, "height": 800}, color_scheme=scheme, service_workers="block")
                pg = ctx2.new_page()
                pg.on("pageerror", lambda x: errors.append(str(x)))
                t.fresh(pg, settings={"tab": "recipes", "recipeView": "schemes"})
                pg.wait_for_selector("#scheme-list .scheme-recipe-row")
                sizes = pg.evaluate("""() => [...document.querySelectorAll('#scheme-list .scheme-recipe-row, #scheme-list .scheme-show-all')]
                    .map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; })""")
                inside = pg.evaluate("() => [...document.querySelectorAll('#scheme-list .scheme-recipe-row')].every(r => r.getBoundingClientRect().right <= innerWidth)")
                check(f"{width} px {scheme}: rows inside the screen, 44 px or more, no sideways scroll",
                      sizes and all(w >= 44 and h >= 44 for w, h in sizes) and inside and t.no_sideways(pg), sizes)
                ctx2.close()
        check("no page errors or pop-ups", not errors, errors)
        browser.close()

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)

if __name__ == "__main__":
    main()
