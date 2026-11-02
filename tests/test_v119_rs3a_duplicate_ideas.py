"""Chunk RS3a tests for Minifolio: Duplicate title, Colour ideas keep their choices, no line pointing at nothing. New behaviour only.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
import lab_helpers as labh
from launch_helpers import quiet

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

R1 = {"id": 101, "name": "Cold armour", "part": "Armour", "notes": "keep dry", "steps": [
    {"technique": "Base coat", "coats": 2, "paints": [{"paint": 1, "mix": None}], "ratio": "", "note": "thin", "optional": False},
    {"technique": "Layer", "coats": 1, "paints": [{"paint": 4, "mix": 60}, {"paint": 6, "mix": 40}], "ratio": "3:2", "note": "", "optional": False}]}

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block").new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. Duplicate ---")
        t.load(page, recipes=[R1], settings={"tab": "recipes", "recipeView": "recipes", "examplesChecked": True})
        page.evaluate("() => openRecipe(101)")
        quiet(page)
        page.click(".recipe-menu-button")
        page.click("text=Duplicate")
        check("the screen is titled Duplicate recipe", page.inner_text("#recipe-page h2") == "Duplicate recipe", page.inner_text("#recipe-page h2"))
        d = page.evaluate("() => ({ n: recipeDraft.name, p: recipeDraft.part, o: recipeDraft.notes, s: recipeDraft.steps.map(s => [s.technique, s.coats, s.ratio, s.note, s.paints.map(x => [x.name, x.mix])]) })")
        check("name ends ' copy' and the rest carries over", d["n"] == "Cold armour copy" and d["p"] == "Armour" and d["o"] == "keep dry"
              and d["s"][0] == ["Base coat", 2, "", "thin", [["Macragge Blue", None]]] and d["s"][1][2] == "3:2" and d["s"][1][4] == [["Eshin Grey", 60], ["Rakarth Flesh", 40]], d)
        page.click("text=Save recipe")
        quiet(page)
        names = page.evaluate("() => book.recipes.map(r => r.name)")
        check("saving makes a new recipe and keeps the original", names == ["Cold armour", "Cold armour copy"], names)
        page.evaluate("() => { recipeDraft = null; startRecipeDraft({ id: null, name: '', part: '', notes: '', linkUnit: null, steps: [blankStep()] }); }")
        check("a plain new recipe is still New recipe", page.inner_text("#recipe-page h2") == "New recipe")

        print("\n--- 2. Colour ideas keep their choices ---")
        t.load(page, settings={"tab": "recipes", "examplesChecked": True})
        labh.go_compendium(page)
        page.click("#cmp-fold-ideas-button")
        quiet(page)
        page.click("#cmp-colour-ideas-base")
        page.fill("#cmp-colour-ideas-base", "Macragge")
        page.wait_for_timeout(150)
        page.keyboard.press("ArrowDown"); page.keyboard.press("Enter")
        page.wait_for_timeout(250)
        for key, part, glow in (("glow", "Eyes", True), ("trim", "Trim", False), ("cloth", "Cloth", False)):
            page.click(f'[data-role="{key}"]')
            page.wait_for_timeout(200)
            n_ideas = page.locator("#cmp-fold-ideas-panel .idea-list > li").count()
            page.click("#cmp-fold-ideas-panel .share-row button:has-text(\"Save into\")")
            page.wait_for_timeout(300)
            d = page.evaluate("() => ({ n: recipeDraft.name, p: recipeDraft.part, s: recipeDraft.steps.map(s => s.paints[0].name) })")
            check(f"{part}: the part is set and the name starts with it", d["p"] == part and d["n"].startswith(part + " "), d)
            check(f"{part}: step 1 is the start paint, the ideas follow", d["s"][0] == "Macragge Blue" and len(d["s"]) == n_ideas + 1 and "Macragge Blue" not in d["s"][1:], (d, n_ideas))
            if glow:
                check("Eyes or glow name reads like 'Eyes yellow glow'", d["n"].endswith(" glow") and d["n"].count(" ") == 2, d["n"])
            page.evaluate("() => { recipeDraft = null; }")
            labh.go_compendium(page)
            if page.get_attribute("#cmp-fold-ideas-button", "aria-expanded") != "true":
                page.click("#cmp-fold-ideas-button")
            quiet(page)

        print("\n--- 3. The 'Choose a colour above' line ---")
        t.load(page, settings={"tab": "recipes", "examplesChecked": True})
        labh.go_compendium(page)
        page.click("#cmp-fold-mentor-button")
        quiet(page)
        check("with paints to choose from, the Mentor line shows", page.locator("#cmp-mentor-none").count() == 1)
        check("a draft recipe's own page is unaffected (no errors)", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
