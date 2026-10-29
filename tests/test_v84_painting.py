"""B1 tests for Minifolio (chunk U3: the "Recipes" group is now "Painting").

New behaviour only:
1. The tab bar says Painting; the sub-tabs still say Recipes, Schemes, Your Palette, Shopping.
2. The empty Recipes and Schemes lists keep one short line; recipe and scheme are explained behind More info.
3. Help names the Painting tab and says what a recipe and a scheme are.
4. The toast after Restore example recipes says "the Painting tab".
5. 390 and 360 px, dark and light: no sideways scroll, the Painting tab is at least 44 px.
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

def tab_text(page):
    return page.evaluate("""() => [...document.querySelector('nav.tabs button[data-tab=recipes]').childNodes]
        .filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim()""")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. The tab and its sub-tabs ---")
        load(page, settings={"tab": "recipes", "examplesChecked": True})
        check("the tab bar says Painting", tab_text(page) == "Painting", tab_text(page))
        subs = page.evaluate("() => [...document.querySelectorAll('#recipe-seg button')].map(b => b.textContent.trim())")
        check("the sub-tabs keep their names", subs == ["Recipes", "Schemes", "Your Palette", "Shopping"], subs)

        print("\n--- 2. Empty states ---")
        empty = page.locator("#recipe-list li.empty")
        check("no recipes: one short line, recipe explained behind More info",
              empty.count() == 1 and "No recipes yet." in empty.inner_text()
              and "your own step-by-step for a model" not in empty.inner_text()
              and "your own step-by-step for a model" in page.text_content("#recipe-list li.empty"), empty.all_inner_texts())
        page.evaluate("() => { settings.recipeView = 'schemes'; renderRecipes(); }")
        page.wait_for_timeout(200)
        # S1: George changed the meaning of a scheme (a bundle of recipes), so the old U3 wording is gone
        check("no schemes: the explanation says a scheme is a bundle of recipes",
              "It is a bundle of recipes" in page.text_content("#scheme-list li.empty"))

        print("\n--- 3. Help ---")
        help_ = page.evaluate("() => document.getElementById('view-help').textContent")
        check("Help lists the Painting tab", "Dashboard" in help_ and "Painting" in page.text_content("#help-tabs")
              and "Recipes" not in page.text_content("#help-tabs"), page.text_content("#help-tabs"))
        check("Help says what a recipe and a scheme are",
              "your own step-by-step for a model" in help_ and "the look for a whole model, unit or army" in help_)   # S1: new wording
        check("Help no longer calls the group the Recipes tab", "Recipes tab" not in help_, help_.count("Recipes tab"))

        print("\n--- 4. Restore example recipes ---")
        load(page, settings={"examplesChecked": True})
        page.evaluate("() => { document.getElementById('restore-examples').click(); }")
        page.wait_for_timeout(300)
        check("the message says the Painting tab", "on the Painting tab." in page.inner_text("#toast"), page.inner_text("#toast"))

        print("\n--- 5. Phone sizes ---")
        for width in (390, 360):
            for scheme in ("dark", "light"):
                ctx2 = browser.new_context(viewport={"width": width, "height": 800}, color_scheme=scheme, service_workers="block")
                pg = ctx2.new_page()
                pg.on("pageerror", lambda x: errors.append(str(x)))
                load(pg, settings={"tab": "recipes", "examplesChecked": True})
                size = pg.evaluate("""() => { const r = document.querySelector('nav.tabs button[data-tab=recipes]').getBoundingClientRect();
                    return [Math.round(r.width), Math.round(r.height)]; }""")
                check(f"{width} px {scheme}: Painting tab 44 px or more and no sideways scroll",
                      size[0] >= 44 and size[1] >= 44 and no_sideways(pg), size)
                ctx2.close()
        check("no page errors", not errors, errors)
        browser.close()

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)

if __name__ == "__main__":
    main()
