"""AB9 tests for Minifolio (the examples, from the approved AI-tells items AT-09 and AT-27). New behaviour only:
1. The examples strip shows on Models and nowhere else: a thin strip (not a card, so no look frames it), "Sample bench.", the new hint behind
   More info, a plain Clear examples button (not red). Clearing says "Examples cleared." with Undo.
2. The new names: armies Ash wardens, Bog goblins and Gilded knights; paints named like pots, with no "Example" in front.
3. Old installs: units with the old army names are still recognised as examples, old "Example ..." paints stay made-up, and Restore does not
   add a second copy of an example scheme that is there under its old name. A paint of yours with a new pot name is not caught.
4. Anything you've changed stays: an example unit you moved on survives Clear (as yours); Undo brings back everything, marks too.
5. No empty brand slot on a recipe step or a palette row, no "from 0 brands", and a real pot with a brand never lands on a made-up paint.
Run with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fold_opener   # Your data (Restore example recipes) folds shut since v54
import test_v44 as e   # fresh, existing, main_tab, recipe_view, toast, restore_in_settings

results = []
NEW_PAINTS = ["Brick red", "Bone", "Swamp green", "Dull gold", "Brown wash"]   # the five names the approval gives

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def strips(page):
    """Every examples card or strip in the page, and where it is."""
    return page.evaluate("""() => [...document.querySelectorAll('[id^=examples-card]')].map(el => ({ id: el.id,
        view: (el.closest('section, [id^=view-]') || {}).id || '', card: el.classList.contains('card'),
        shown: !el.classList.contains('hidden') && el.getBoundingClientRect().height > 0 }))""")

def old_book():
    """A recipe book saved before AB9: an example recipe, its example scheme and two example paints, all with the old names."""
    step = lambda pid: {"technique": "Layer", "coats": 1, "paints": [{"paint": pid, "mix": None}], "ratio": "", "note": "", "optional": False}
    return {"parts": ["Whole model", "Armour"], "techniques": ["Layer"], "v15": True, "shorthand": {},
            "paints": [{"id": 1, "brand": "", "name": "Example deep blue", "colour": "#1f3f8f", "example": True},
                       {"id": 2, "brand": "", "name": "Example dark wash", "colour": "#2a2a2e", "example": True}],
            "recipes": [{"id": 1, "name": "Blue armour", "part": "Armour", "notes": "", "steps": [step(1), step(2)], "example": True}],
            "schemes": [{"id": 1, "name": "Blue army colours", "faction": "Blue army", "auto": False, "recipes": [1], "example": True}]}

OLD_UNITS = [{"id": 1, "name": "Captain", "hobby": "Sci-fi", "faction": "Blue army", "stage": 3, "count": 1},
             {"id": 2, "name": "Brutes", "hobby": "Sci-fi", "faction": "Green army", "stage": 0, "count": 10},
             {"id": 3, "name": "Guardians", "hobby": "Fantasy", "faction": "Gold army", "stage": 6, "count": 5}]

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block").new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        fold_opener.open_cards_on_load(page)   # Restore example recipes sits in a folded Settings card

        print("\n--- 1. The strip, on Models only ---")
        e.fresh(page, {"theme": "forge"})
        e.main_tab(page, "units")
        all_strips = strips(page)
        check("one examples strip in the whole app, on Models, and it shows", [(s["id"], s["view"], s["shown"]) for s in all_strips] == [("examples-card", "view-units", True)], all_strips)
        look = page.evaluate("""() => { const el = document.getElementById('examples-card'); const cs = getComputedStyle(el);
            return { card: el.classList.contains('card'), shadow: cs.boxShadow, left: cs.borderLeftWidth, image: cs.backgroundImage, h: el.getBoundingClientRect().height }; }""")
        check("a thin strip, not a framed card, even in Grim Forge (no shadow, side border or rivets)",
              not look["card"] and look["shadow"] == "none" and look["left"] == "0px" and look["image"] == "none" and look["h"] < 140, look)
        check("bold line 'Sample bench.'", page.inner_text("#examples-card strong") == "Sample bench.")
        hint = page.text_content("#examples-card .hint") or ""
        check("the hint behind More info", hint == "Made-up units and recipes, so the app isn't empty on day one. Clear them when you've got your own. Anything you've changed stays."
              and not page.locator("#examples-card .hint").is_visible(), hint)
        cls = page.get_attribute("#examples-card .clear-examples", "class")
        check("Clear examples is a plain button, not red", "plain-button" in cls and "danger-button" not in cls, cls)
        for where in ("dashboard", "recipes"):
            e.main_tab(page, where)
            check(f"no examples card on {where}", page.locator(f"#view-{where} [id^=examples-card]").count() == 0)

        print("\n--- 2. The new names ---")
        units = page.evaluate("() => models.map(m => m.faction)")
        check("the example armies are Ash wardens, Bog goblins and Gilded knights", units == ["Ash wardens", "Bog goblins", "Gilded knights"], units)
        names = page.evaluate("() => book.paints.map(p => p.name)")
        check("the paints are named like pots, without 'Example'", all(n in names for n in NEW_PAINTS) and not any(n.startswith("Example") for n in names), names)
        check("every one has no brand and the made-up mark", page.evaluate("() => book.paints.every(p => p.brand === '' && p.madeUp === true && isMadeUpPaint(p))"))
        check("the schemes follow the armies", page.evaluate("() => book.schemes.map(s => s.faction)") == ["Ash wardens", "Bog goblins"])

        print("\n--- 3. Brand slot and the palette header ---")
        e.main_tab(page, "recipes")
        page.evaluate("() => openRecipe(book.recipes[0].id)"); page.wait_for_timeout(300)
        check("a recipe step with a brandless paint has no empty brand slot",
              page.locator("#recipe-page .paint-line").count() > 0 and page.locator("#recipe-page .paint-line .brand").count() == 0)
        page.evaluate("history.back()"); page.wait_for_timeout(300)
        e.recipe_view(page, "palette")
        summary = page.text_content("#palette-summary") or ""
        meta = page.locator("#paint-list .details").first.text_content() or ""
        check("the header says '16 paints', not 'from 0 brands'", summary.startswith("16 paints") and "brand" not in summary, summary)
        check("a palette row says no 'No brand'", "No brand" not in meta and meta.startswith("in "), meta)
        found = page.evaluate("""() => paletteResultCard({ brand: 'The Army Painter', name: 'Brown Wash', colour: '#352a16' }).textContent""")
        check("a scanned real 'Brown Wash' pot is not taken for the made-up one", "Not in your palette yet" in found, found)

        print("\n--- 4. Anything you've changed stays ---")
        e.fresh(page)
        page.evaluate("() => { const m = models[0]; setStage(m, 4); m.notes = 'Mine now'; render(); }")
        e.main_tab(page, "units")
        page.click("#examples-card .clear-examples"); e.quiet(page)
        tt = e.toast(page)
        check("the message is 'Examples cleared.' with Undo", tt["text"] == "Examples cleared." and tt["undo"], tt)
        left = page.evaluate("() => models.map(m => [m.name, m.example === true, m.stage])")
        check("the Captain you moved on stays, as yours; the untouched examples go", left == [["Captain", False, 4]], left)
        check("the example recipes and paints go (the ones nothing of yours uses)", page.evaluate("() => book.recipes.length + book.paints.length") == 0)
        page.click("#toast-undo"); page.wait_for_timeout(300)
        back = page.evaluate("() => [models.map(m => [m.name, m.example === true]), book.recipes.length, book.schemes.length, book.paints.length]")
        check("Undo brings everything back, the Captain marked as an example again", back == [[["Captain", True], ["Brutes", True], ["Guardians", True]], 5, 2, 16], back)

        print("\n--- 5. An install made before AB9 ---")
        e.existing(page, OLD_UNITS, old_book(), {"recipeExamplesChecked": True})
        check("units with the old army names are recognised as examples",
              page.evaluate("() => models.every(m => m.example === true)"), page.evaluate("() => models"))
        e.main_tab(page, "units")
        check("the strip shows for them", page.locator("#examples-card").is_visible())
        page.click("#examples-card .keep-examples"); e.quiet(page)
        check("after Keep them, the old 'Example ...' paints are still made-up (no mark needed)",
              page.evaluate("() => book.paints.every(p => p.example !== true && isMadeUpPaint(p))"))
        e.restore_in_settings(page)
        schemes = page.evaluate("() => book.schemes.map(s => s.name)")
        check("Restore does not add the Ash wardens scheme beside its old name", "Blue army colours" in schemes and "Ash wardens colours" not in schemes, schemes)
        check("an own paint called 'Bone' with no mark is an ordinary paint",
              not page.evaluate("() => isMadeUpPaint({ id: 999, brand: '', name: 'Bone', colour: '#eeeecc' })"))
        e.existing(page, [dict(OLD_UNITS[0], stage=5, log=[["2026-11-01", 5]])], None, {"recipeExamplesChecked": True})
        check("an old example you had moved on is recognised by name, and Clear keeps it",
              page.evaluate("() => { clearExamples(); return models.map(m => [m.name, m.example === true]); }") == [["Captain", False]])

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
