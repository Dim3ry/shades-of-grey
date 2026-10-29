"""S1 tests for Minifolio (schemes are bundles of recipes: renames and explainer). Words only, no behaviour change.

New behaviour only:
1. Compendium: "Starter schemes" is "Colour plans" and "Your schemes" is "Colours you've used" (headings, search label, empty-state line);
   the element ids did not change.
2. Painting > Recipes and Painting > Schemes each start with a closed "Recipe or scheme? What's the difference" expander that opens to the
   three definitions, with a plain-colour example and no faction words.
3. Help has the same words.
4. Backup data is the same before and after opening the expander and the Compendium.
5. 390 and 360 px, dark and light: no sideways scroll, the expander is 44 px or more tall.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys, re
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways = t.load, t.no_sideways
results = []
TITLE = "Recipe or scheme? What's the difference"
FACTION_WORDS = re.compile(r"tyranid|space marine|ork|necron|eldar|ultramarine|warhammer|citadel|games workshop", re.I)

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def explainer(page, view):
    """The expander on one Painting sub-tab: its button text, whether it is open, and the panel text."""
    return page.evaluate("""(view) => {
        const host = document.getElementById(view === 'schemes' ? 'scheme-view' : 'recipe-home');
        const wrap = host.querySelector('.recipe-scheme-explainer');
        if (!wrap) return null;
        const b = wrap.querySelector('.more-info-button'), p = wrap.querySelector('.more-info-panel');
        return { first: host.firstElementChild === wrap, button: b.textContent.trim(), expanded: b.getAttribute('aria-expanded'),
                 hidden: p.hidden, text: p.textContent, tall: Math.round(b.getBoundingClientRect().height) };
    }""", view)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))

        print("\n--- 1. Compendium names ---")
        load(page, settings={"tab": "compendium", "examplesChecked": True})
        heads = page.evaluate("() => [...document.querySelectorAll('#compendium-body .compendium-folds > section.fold .fold-button')].map(b => b.firstElementChild.textContent)")
        check("the folds say Colours you've used and Colour plans", heads[2:4] == ["Colours you've used", "Colour plans"], heads)
        check("the ids are unchanged", page.locator("#cmp-fold-starter").count() == 1 and page.locator("#cmp-fold-history").count() == 1)
        page.evaluate("() => document.querySelector('#cmp-fold-starter').closest('section.fold').querySelector('.fold-button').click()")
        page.wait_for_selector("#cmp-starter-search")
        body = page.text_content("#compendium-body")
        check("the search box and the text say colour plans, not starter schemes", page.get_by_label("Search colour plans").count() >= 1
              and "Pick a group, then a colour plan" in body and "Starter scheme" not in body, body[:200])

        print("\n--- 2. The explainer on both sub-tabs ---")
        load(page, settings={"tab": "recipes", "examplesChecked": True})
        for view in ("recipes", "schemes"):
            page.evaluate("(v) => { settings.recipeView = v; renderRecipes(); }", view)
            ex = explainer(page, view)
            check(f"{view}: at the top, titled, closed", ex and ex["first"] and ex["button"] == TITLE and ex["expanded"] == "false" and ex["hidden"], ex)
        page.locator("#scheme-view .recipe-scheme-explainer .more-info-button").click()
        ex = explainer(page, "schemes")
        check("tapping it opens the three definitions", ex["expanded"] == "true" and not ex["hidden"]
              and "Recipe: how to paint one part" in ex["text"] and "Scheme: the look for a whole model, unit or army. It is a bundle of recipes." in ex["text"]
              and "Colour plan (Compendium): a quick idea of which colours go together. No steps." in ex["text"], ex["text"])
        check("the example uses plain colour words and no faction words", "dark green scheme" in ex["text"] and not FACTION_WORDS.search(ex["text"]), ex["text"])

        print("\n--- 3. Help ---")
        help_ = page.evaluate("() => document.getElementById('help-recipe-or-scheme').textContent")
        check("Help has the same words", TITLE in help_ and "It is a bundle of recipes" in help_ and "dark green scheme" in help_
              and "Save it into a recipe when you want steps" in help_ and not FACTION_WORDS.search(help_), help_)
        check("Help and the Compendium intro say colour plans", "colour plans with a similar colour" in page.evaluate("() => document.getElementById('help-ideas-for').textContent"))

        print("\n--- 4. Backup is unaffected ---")
        before = page.evaluate("() => JSON.stringify(backupData())")
        page.locator("#recipe-home .recipe-scheme-explainer .more-info-button, #scheme-view .recipe-scheme-explainer .more-info-button").first.click()
        page.evaluate("() => { settings.tab = 'compendium'; }")
        after = page.evaluate("() => JSON.stringify(backupData())")
        check("backup data is the same after opening the expander", before == after)
        check("backup fields still have the same names", sorted(page.evaluate("() => Object.keys(backupData())")) ==
              sorted(["app", "version", "dataVersion", "stages", "doneFrom", "models", "recipes", "factionColours", "palette", "appearance", "theme", "brandsOff", "useCustom", "customColours"]))

        print("\n--- 5. Phone sizes ---")
        for width in (390, 360):
            for scheme in ("dark", "light"):
                ctx2 = browser.new_context(viewport={"width": width, "height": 800}, color_scheme=scheme, service_workers="block")
                pg = ctx2.new_page()
                pg.on("pageerror", lambda x: errors.append(str(x)))
                load(pg, settings={"tab": "recipes", "recipeView": "schemes", "examplesChecked": True})
                pg.wait_for_selector("#scheme-view .recipe-scheme-explainer .more-info-button")
                pg.locator("#scheme-view .recipe-scheme-explainer .more-info-button").click()
                ex = explainer(pg, "schemes")
                check(f"{width} px {scheme}: expander open, 44 px or more tall, no sideways scroll", ex["tall"] >= 44 and no_sideways(pg), ex["tall"])
                ctx2.close()
        check("no page errors or pop-ups", not errors, errors)
        browser.close()

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)

if __name__ == "__main__":
    main()
