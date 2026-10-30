"""X1 tests for Minifolio (Painting > Colour Lab). New behaviour only:
1. Painting's sub-tabs: Recipes, Schemes, Colour Lab, Your Palette, Shopping. Colour Lab's own row: Wheel, Colour ideas, Colour plans,
   Colours you've used, Picker; one open at a time, Wheel first.
2. Each Colour Lab section shows its own content; the Compendium keeps only Detail recipes and Basing tips.
3. The round Ask Mentor button opens Colour Lab > Picker. Ideas for this opens Colour Lab and Back returns.
4. Shopping sources: new ones say "Colour Lab: ..."; an old stored "Compendium: ..." is shown as "Colour Lab: ..." and the stored text stays.
5. Old saved state: a saved tab "compendium", a saved Colour Lab view, an unknown sub-tab; a backup from before this change.
6. No new network use; no faction words in the new text.
7. 390 and 360 px, dark and light: no sideways scroll, 44 px taps.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys, re, json
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v24 as t

results = []
FACTION_WORDS = re.compile(r"tyranid|space marine|ork|necron|eldar|ultramarine|warhammer|citadel|games workshop|chaos|imperial", re.I)
OLD_SOURCE = "Compendium: Colour ideas"

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def labels(page, sel):
    return page.evaluate("(s) => [...document.querySelectorAll(s)].map(b => b.textContent.trim())", sel)

def lab_open(page, key):
    page.click(f'#lab-seg [data-lab="{key}"]')
    page.wait_for_selector(f"#cmp-lab-{key}")

def book_with_old_source():
    return {"parts": ["Whole model"], "techniques": ["Layer"], "schemes": [], "shorthand": {}, "v15": True, "recipes": [],
            "paints": [{"id": 1, "name": "Mid Blue", "brand": "Test", "colour": "#3355aa", "status": "wishlist", "shopFrom": [OLD_SOURCE]}]}

def main():
    errors = []
    requests = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))
        page.on("request", lambda r: requests.append(r.url) if not r.url.startswith(("http://localhost", "http://127.0.0.1", "data:", "blob:")) else None)

        print("\n--- 1. Sub-tabs ---")
        t.fresh(page)
        t.main_tab(page, "recipes")
        check("Painting sub-tabs in order", labels(page, "#recipe-seg button") == ["Recipes", "Schemes", "Colour Lab", "Your Palette", "Shopping"], labels(page, "#recipe-seg button"))
        t.recipe_view(page, "colourlab")
        check("Colour Lab sections in order", labels(page, "#lab-seg button") == ["Wheel", "Colour ideas", "Colour plans", "Colours you've used", "Picker"], labels(page, "#lab-seg button"))
        check("Wheel is open first, the only one selected", page.evaluate("() => [...document.querySelectorAll('#lab-seg button')].map(b => b.getAttribute('aria-selected')).join()") == "true,false,false,false,false"
              and page.locator("#cmp-wheel").count() == 1)

        print("\n--- 2. Each section ---")
        marks = {"wheel": "#cmp-wheel", "ideas": "#cmp-colour-ideas-base", "plans": "#cmp-starter-schemes", "history": "#cmp-faction-history", "picker": "#cmp-mentor-base"}
        for key, mark in marks.items():
            lab_open(page, key)
            only = page.evaluate("(k) => document.querySelectorAll('#colourlab-body .lab-section').length === 1 && !!document.getElementById('cmp-lab-' + k)", key)
            check(f"{key}: its own content shows and no other section", page.locator(mark).count() == 1 and only)
        page.locator("#cmp-mentor-base").fill("Mid")
        check("Picker keeps its Part chips (Armour first)", page.locator("[data-mentor-part]").first.get_attribute("data-mentor-part") == "armour")
        page.evaluate("() => document.activeElement.blur()")   # the tab bar hides while a text box has the focus
        t.main_tab(page, "compendium")
        check("Compendium keeps only Detail recipes and Basing tips", labels(page, "#compendium-body .fold-button") == ["Detail recipes", "Basing tips"]
              and page.locator("#cmp-wheel, #cmp-fold-mentor, #cmp-fold-ideas").count() == 0, labels(page, "#compendium-body .fold-button"))
        check("Pro preview shows on the Compendium and on Colour Lab", "Pro preview" in page.inner_text("#view-guides")
              and page.evaluate("() => !!document.querySelector('#colourlab-view .pro-pill')"))

        print("\n--- 3. Links ---")
        t.main_tab(page, "dashboard")
        page.click("#mentor-button")
        page.wait_for_selector("#cmp-lab-picker")
        check("Ask Mentor button opens Painting > Colour Lab > Picker", page.evaluate("() => [settings.tab, settings.recipeView, compendiumState.lab].join()") == "recipes,colourlab,picker")
        seed = {"parts": ["Whole model"], "techniques": ["Layer"], "schemes": [], "shorthand": {}, "v15": True, "recipes": [],
                "paints": [{"id": 1, "name": "Mid Blue", "brand": "Test", "colour": "#3355aa", "status": "owned"}]}
        t.existing(page, [], seed, {"tab": "recipes", "recipeView": "palette"})
        page.wait_for_selector("#paint-list .paint-item")
        page.evaluate("() => document.querySelector('#paint-list .paint-head').click()")
        page.wait_for_selector("[data-ideas-for]")
        page.evaluate("() => document.querySelector('[data-ideas-for]').click()")
        page.wait_for_selector("#cmp-focus-back")
        check("Ideas for this opens Colour Lab with the paint's ideas", page.evaluate("() => settings.recipeView") == "colourlab" and page.locator("#cmp-focus-panel").count() == 1)
        page.click("#cmp-focus-back")
        page.wait_for_selector("[data-ideas-for]")
        check("Back goes to Your Palette with the paint still open", page.evaluate("() => settings.recipeView") == "palette" and page.locator("[data-ideas-for]").count() == 1)

        print("\n--- 4. Shopping sources ---")
        t.existing(page, [], book_with_old_source(), {"tab": "recipes", "recipeView": "shopping"})
        page.wait_for_selector(".shop-from")
        shown = page.inner_text("#shop-panel")
        stored = page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-recipes')).paints[0].shopFrom")
        check("old source shows as Colour Lab: ... and never as Compendium", "Colour Lab: Colour ideas" in shown and "Compendium" not in shown, shown)
        check("the stored text is not rewritten", stored == [OLD_SOURCE], stored)
        page.evaluate("() => { const p = book.paints[0]; noteShopSource(p, 'Colour Lab: Picker'); }")
        t.recipe_view(page, "recipes"); t.recipe_view(page, "shopping")
        check("old and new sources show side by side, each once", page.inner_text("#shop-panel").count("Colour Lab: Colour ideas") == 1 and "Colour Lab: Picker" in page.inner_text("#shop-panel"))
        # the Picker's Add to shopping list writes the new text
        t.existing(page, [], seed, {"tab": "recipes", "recipeView": "colourlab"})
        page.evaluate("() => { const c = compendiumBaseChoices(); compendiumState.mentorBase = c.key(book.paints[0]); compendiumState.lab = 'picker'; renderColourLab(); }")
        add = page.locator("#cmp-lab-picker button", has_text="Add to shopping list").first
        add.wait_for()
        add.click()
        got = page.evaluate("() => book.paints.flatMap(p => p.shopFrom || [])")
        check("a new source from the Picker is saved as Colour Lab: Picker", "Colour Lab: Picker" in got and not any(g.startswith("Compendium") for g in got), got)

        print("\n--- 5. Old saved state ---")
        t.existing(page, [], None, {"tab": "compendium"})
        page.wait_for_selector("#cmp-fold-detail")
        check("a saved Compendium tab opens cleanly", page.evaluate("() => settings.tab") == "guides")   # X2: the Compendium tab is gone; a saved "compendium" opens Guides
        t.existing(page, [], None, {"tab": "recipes", "recipeView": "colourlab"})
        page.wait_for_selector("#cmp-lab-wheel")
        check("a saved Colour Lab view opens on Wheel after a reload", page.evaluate("() => settings.recipeView") == "colourlab")
        t.existing(page, [], None, {"tab": "recipes", "recipeView": "no-such-view"})
        page.wait_for_selector("#recipe-list, #recipe-home")
        check("an unknown Painting sub-tab falls back to Recipes", page.evaluate("() => document.getElementById('recipe-seg').querySelector('[aria-selected=true]').dataset.view") == "recipes")
        t.existing(page, [], None, {"tab": "recipes", "recipeView": "palette"})
        backup = {"app": "Shades of Grey", "version": 6, "models": [], "recipes": book_with_old_source()}
        page.set_input_files("#restore-file", files=[{"name": "old.json", "mimeType": "application/json", "buffer": json.dumps(backup).encode()}])
        page.click("#dialog-yes")   # the app asks before replacing recipes
        page.wait_for_function("() => book.paints.some(p => p.name === 'Mid Blue')")
        check("a backup from before this change restores with its source text unchanged",
              page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-recipes')).paints.find(p => p.name === 'Mid Blue').shopFrom") == [OLD_SOURCE])

        print("\n--- 6. Network and words ---")
        check("no outside network use", not requests, requests)
        new_text = " ".join(labels(page, "#recipe-seg button") + labels(page, "#lab-seg button") + [page.inner_text("#help-ideas-for"), page.inner_text("#help-ask-mentor")])
        check("no faction words in the new text", not FACTION_WORDS.search(new_text), FACTION_WORDS.findall(new_text))
        check("no page errors or pop-ups", not errors, errors)
        ctx.close()

        print("\n--- 7. Phone sizes ---")
        for width in (390, 360):
            for scheme in ("dark", "light"):
                ctx2 = browser.new_context(viewport={"width": width, "height": 800}, color_scheme=scheme, service_workers="block")
                pg = ctx2.new_page()
                pg.on("pageerror", lambda x: errors.append(str(x)))
                t.fresh(pg, settings={"tab": "recipes", "recipeView": "colourlab"})
                pg.wait_for_selector("#cmp-lab-wheel")
                sizes = pg.evaluate("""() => [...document.querySelectorAll('#recipe-seg button, #lab-seg button')].map(b => { const r = b.getBoundingClientRect();
                    return [Math.round(r.width), Math.round(r.height), r.right <= innerWidth]; })""")
                check(f"{width} px {scheme}: both rows 44 px or more, inside the screen, no sideways scroll",
                      len(sizes) == 10 and all(w >= 44 and h >= 44 and ok for w, h, ok in sizes) and t.no_sideways(pg), sizes)
                for key in ("picker", "history"):
                    lab_open(pg, key)
                check(f"{width} px {scheme}: Picker and Colours you've used leave no sideways scroll", t.no_sideways(pg))
                ctx2.close()
        check("no page errors on phone sizes", not errors, errors)
        browser.close()

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)

if __name__ == "__main__":
    main()
