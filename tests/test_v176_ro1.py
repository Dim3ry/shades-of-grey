"""RO1 tests for Minifolio: clearer optional recipe steps and Mark owned. New behaviour only.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import leave_launch, quiet

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def step(paints, technique, optional=False):
    return {"technique": technique, "coats": 1, "paints": [{"paint": p, "mix": None} for p in paints], "ratio": "", "note": "", "optional": optional}

LONG = "Extremely Long Paint Name For Phone Width Testing Purposes Only"
PAINTS = [{"id": 1, "brand": "Citadel", "name": "Abaddon Black", "colour": "#231f20", "status": "owned"},
          {"id": 2, "brand": "Citadel", "name": "Mephiston Red", "colour": "#9a1115", "status": "low"},
          {"id": 3, "brand": "Citadel", "name": "Nuln Oil", "colour": "#222222"},
          {"id": 4, "brand": "Citadel", "name": LONG, "colour": "#445566"},
          {"id": 5, "brand": "", "name": "Made Up Mauve", "colour": "#aa66aa", "madeUp": True}]
RECIPES = [{"id": 201, "name": "Test cloak", "part": "Armour", "notes": "", "steps": [
              step([1], "Base coat"), step([3], "Wash", True), step([4], "Layer", True), step([2], "Edge"), step([3], "Glaze")]},
           {"id": 202, "name": "Second", "part": "Armour", "notes": "", "steps": [step([3], "Layer")]}]

def go(page, width=390, height=844):
    page.set_viewport_size({"width": width, "height": height})
    page.evaluate("openRecipeId = 201; showTab('recipes'); renderRecipes()")
    page.wait_for_selector("#recipe-page .step-line")
    quiet(page)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.load(page, paints=PAINTS, recipes=RECIPES, settings={"tab": "recipes", "examplesChecked": True}); leave_launch(page)
        go(page)

        print("\n--- 1. Optional steps ---")
        lines = page.locator("#recipe-page .step-line")
        check("only the two optional steps say Optional on their line", [lines.nth(i).locator(".step-optional").count() for i in range(5)] == [0, 1, 1, 0, 0])
        check("the word is plain text, not a pill", page.evaluate("""() => { const s = getComputedStyle(document.querySelector('.step-optional'));
            return s.backgroundColor === 'rgba(0, 0, 0, 0)' && s.borderTopWidth === '0px'; }"""))
        check("the whole step has a dashed border on all four sides", page.evaluate("""() => { const s = getComputedStyle(document.querySelector('li.optional-step'));
            return ['Top','Right','Bottom','Left'].every(d => s['border'+d+'Style'] === 'dashed' && parseFloat(s['border'+d+'Width']) >= 1); }"""))
        lines.nth(1).click()
        facts = page.locator("#rstep-1 .step-facts").inner_text().lower()
        check("the open step's facts line does not repeat optional", "optional" not in facts, facts)
        check("a long step name wraps and the word Optional stays whole inside the line", page.evaluate("""() => {
            const b = document.querySelectorAll('#recipe-page .step-line')[2], w = b.querySelector('.step-optional'), tx = b.querySelector('.step-line-text');
            const r = w.getBoundingClientRect(), br = b.getBoundingClientRect();
            return tx.getBoundingClientRect().height > 30 && r.right <= br.right && r.height < 24 && r.width >= w.scrollWidth - 1; }"""))
        check("the word has full text contrast (no opacity)", page.evaluate("getComputedStyle(document.querySelector('.step-optional')).opacity") == "1")

        print("\n--- 2. Mark owned ---")
        lines.nth(1).click()   # fold again
        page.evaluate("document.querySelectorAll('#recipe-page .step-line').forEach(b => { if (b.getAttribute('aria-expanded') !== 'true') b.click(); })")
        names = page.evaluate("[...document.querySelectorAll('#recipe-page .mark-owned')].map(b => document.getElementById(b.getAttribute('aria-describedby')).dataset.paintId)")
        check("Mark owned shows for paints you don't have, once per paint line", names.count("3") == 2 and "4" in names and len(names) == 3, names)
        check("owned and running low paints keep just the tick", "1" not in names and "2" not in names)
        page.evaluate("book.paints.find(p => p.id === 5).name = Object.values(LEGACY_EXAMPLES.paints)[0]; book.recipes[0].steps[0].paints.push({paint: 5, mix: null}); renderRecipes()")
        check("never for made-up example paints", page.locator("#recipe-page .mark-owned").count() == 3)
        page.evaluate("book.recipes[0].steps[0].paints.pop(); renderRecipes()")
        page.evaluate("document.querySelectorAll('#recipe-page .step-line').forEach(b => { if (b.getAttribute('aria-expanded') !== 'true') b.click(); })")
        h = page.evaluate("Math.round(document.querySelector('#recipe-page .mark-owned').getBoundingClientRect().height)")
        check("Mark owned is 44 px tall or more", h >= 44, h)

        btn = page.locator("#rstep-1 .mark-owned")
        page.evaluate("window.scrollTo(0, 60)")
        y0 = page.evaluate("window.scrollY")
        btn.click()
        check("Nuln Oil is now Owned", page.evaluate("paintStatus(book.paints.find(p => p.id === 3))") == "owned")
        check("every step using it lost its button", page.evaluate("[...document.querySelectorAll('#recipe-page .mark-owned')].map(b => document.getElementById(b.getAttribute('aria-describedby')).dataset.paintId)").count("3") == 0)
        check("steps stay open", page.evaluate("[...document.querySelectorAll('#recipe-page .step-line')].every(b => b.getAttribute('aria-expanded') === 'true')"))
        check("the scroll position did not jump", abs(page.evaluate("window.scrollY") - y0) < 2, (y0, page.evaluate("window.scrollY")))
        check("focus lands on the paint's line", page.evaluate("document.activeElement.classList.contains('paint-line')"))
        check("the shopping list button counts one paint fewer", page.evaluate("document.querySelector('.recipe-shop-add') ? document.querySelector('.recipe-shop-add').textContent : ''") == "Add to shopping list (1)")
        check("a second recipe using the paint shows it as owned too", page.evaluate("""() => { openRecipeId = 202; renderRecipes();
            const r = document.querySelectorAll('#recipe-page .mark-owned').length; openRecipeId = 201; renderRecipes(); return r === 0; }"""))
        toast = page.evaluate("document.querySelector('#toast, .toast') ? document.querySelector('#toast, .toast').textContent : ''")
        check("a toast offers Undo", "Undo" in toast, toast)
        page.evaluate("[...document.querySelectorAll('#toast button, .toast button')].find(b => /undo/i.test(b.textContent)).click()")
        check("Undo puts the paint back to no status", page.evaluate("paintStatus(book.paints.find(p => p.id === 3))") in ("", None, "notowned"))

        print("\n--- 3. No status set yet ---")
        t.load(page, paints=[dict((k, v) for k, v in q.items() if k != "status") for q in PAINTS], recipes=RECIPES, settings={"tab": "recipes", "examplesChecked": True}); leave_launch(page)
        go(page)
        page.evaluate("document.querySelectorAll('#recipe-page .step-line').forEach(b => b.click())")
        check("it shows even when no paint has a status", page.locator("#recipe-page .mark-owned").count() >= 3)

        print("\n--- 4. Looks, sizes ---")
        for look in ("classic", "bench", "forge", "parchment"):
            for scheme in ("dark", "light"):
                page.emulate_media(color_scheme=scheme)
                for w, h in ((390, 844), (360, 640)):
                    page.evaluate(f"document.documentElement.dataset.t = '{look}'; document.documentElement.dataset.theme = '{scheme}'")
                    go(page, w, h)
                    page.evaluate("document.querySelectorAll('#recipe-page .step-line').forEach(b => { if (b.getAttribute('aria-expanded') !== 'true') b.click(); })")
                    ok = page.evaluate("""() => document.documentElement.scrollWidth <= document.documentElement.clientWidth
                        && [...document.querySelectorAll('.step-optional')].every(e => { const r = e.getBoundingClientRect(); return r.right <= innerWidth && e.scrollWidth <= Math.ceil(r.width); })""")
                    check(f"{look} {scheme} {w}: no sideways scroll and Optional whole", ok)
        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

main()
