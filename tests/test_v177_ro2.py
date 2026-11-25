"""RO2 tests for Minifolio: a status menu on every real paint in an open recipe step. New behaviour only."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import leave_launch, quiet

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def step(paints, technique):
    return {"technique": technique, "coats": 1, "paints": [{"paint": p, "mix": None} for p in paints], "ratio": "", "note": "", "optional": False}

LONG = "Extremely Long Paint Name For Phone Width Testing Purposes Only"
PAINTS = [{"id": 1, "brand": "Citadel", "name": "Abaddon Black", "colour": "#231f20", "status": "owned"},
          {"id": 3, "brand": "Citadel", "name": "Nuln Oil", "colour": "#222222"},
          {"id": 4, "brand": "Citadel", "name": LONG, "colour": "#445566"},
          {"id": 5, "brand": "", "name": "Made Up Mauve", "colour": "#aa66aa", "madeUp": True}]
RECIPES = [{"id": 201, "name": "Test cloak", "part": "Armour", "notes": "", "steps": [step([1], "Base coat"), step([3], "Wash"), step([4], "Layer"), step([3], "Glaze")]},
           {"id": 202, "name": "Second", "part": "Armour", "notes": "", "steps": [step([3], "Layer")]}]

def go(page, width=390, height=844):
    page.set_viewport_size({"width": width, "height": height})
    page.evaluate("openRecipeId = 201; showTab('recipes'); renderRecipes()")
    page.wait_for_selector("#recipe-page .step-line")
    quiet(page)
    page.evaluate("document.querySelectorAll('#recipe-page .step-line').forEach(b => { if (b.getAttribute('aria-expanded') !== 'true') b.click(); })")

def st(page, pid):
    return page.evaluate(f"paintStatus(book.paints.find(p => p.id === {pid})) || ''")

def pick(page, pid, key):
    page.locator(f"#recipe-page .paint-status-select[data-paint-id='{pid}']").first.select_option(key)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.load(page, paints=PAINTS, recipes=RECIPES, settings={"tab": "recipes", "examplesChecked": True}); leave_launch(page)
        go(page)

        print("\n--- 1. The menu ---")
        ids = page.evaluate("[...document.querySelectorAll('#recipe-page .paint-status-select')].map(s => s.dataset.paintId)")
        check("one menu per real paint line (1, 3, 4, 3)", ids == ["1", "3", "4", "3"], ids)
        page.evaluate("book.paints.find(p => p.id === 5).name = Object.values(LEGACY_EXAMPLES.paints)[0]; book.recipes[0].steps[0].paints.push({paint: 5, mix: null}); renderRecipes()")
        check("none on made-up example paints", page.locator("#recipe-page .paint-status-select").count() == 4)
        page.evaluate("book.recipes[0].steps[0].paints.pop(); renderRecipes()")
        go(page)
        check("lists the five statuses in words", page.evaluate("[...document.querySelector('#recipe-page .paint-status-select').options].map(o => o.textContent)") == ["Owned", "Running low", "Empty", "Wishlist", "Not owned"])
        sel = page.evaluate("[...document.querySelectorAll('#recipe-page .paint-status-select')].map(s => s.options[s.selectedIndex].textContent)")
        check("shows the current status in words (Owned, Not owned for unset)", sel == ["Owned", "Not owned", "Not owned", "Not owned"], sel)
        check("the menu is 44 px tall or more", page.evaluate("Math.round(document.querySelector('#recipe-page .paint-status-select').getBoundingClientRect().height)") >= 44)
        check("the menu is labelled Status and points at its paint line", page.evaluate("(() => { const s = document.querySelectorAll('#recipe-page .paint-status-select')[1]; return s.getAttribute('aria-label') === 'Status' && document.getElementById(s.getAttribute('aria-describedby')).dataset.paintId === '3'; })()"))
        check("Mark owned stays only on paints you do not have", page.locator("#recipe-page .mark-owned").count() == 3)

        print("\n--- 2. Each status sticks ---")
        for key in ("wishlist", "low", "empty", "owned", "notowned"):
            pick(page, 3, key)
            check(f"{key} is set and shown", st(page, 3) == key and page.evaluate("document.querySelectorAll('#recipe-page .paint-status-select')[1].value") == key, st(page, 3))
        pick(page, 3, "wishlist")
        check("Wishlist lands on the shopping list", page.evaluate("shoppingList().some(p => p.id === 3)") if page.evaluate("typeof shoppingList") == "function" else page.evaluate("paintStatus(book.paints.find(p => p.id === 3))") == "wishlist")
        check("the second step with the same paint matches", page.evaluate("[...document.querySelectorAll('#recipe-page .paint-status-select[data-paint-id=\"3\"]')].every(s => s.value === 'wishlist')"))
        check("the other recipe shows it too", page.evaluate("() => { openRecipeId = 202; renderRecipes(); return true; }") and page.evaluate("document.querySelector('#recipe-page .paint-status-select') && document.querySelector('#recipe-page .paint-status-select').value") == "wishlist")
        page.evaluate("openRecipeId = 201; renderRecipes()")
        go(page)
        pick(page, 3, "owned")
        check("owned paint leaves the list and drops its Mark owned", page.locator("#recipe-page .mark-owned").count() == 1 and st(page, 3) == "owned")
        pick(page, 3, "low")
        check("running low keeps its tick (no Mark owned)", page.locator("#recipe-page .mark-owned").count() == 1)

        print("\n--- 3. Undo, focus, scroll ---")
        pick(page, 3, "empty")
        check("the open steps stay open", page.evaluate("[...document.querySelectorAll('#recipe-page .step-line')].every(b => b.getAttribute('aria-expanded') === 'true')"))
        toast = page.evaluate("document.querySelector('#toast, .toast') ? document.querySelector('#toast, .toast').textContent : ''")
        check("toast says the new status and offers Undo", "Nuln Oil is now empty" in toast and "Undo" in toast, toast)
        page.evaluate("[...document.querySelectorAll('#toast button, .toast button')].find(b => /undo/i.test(b.textContent)).click()")
        check("Undo restores Running low", st(page, 3) == "low", st(page, 3))
        go(page)
        page.evaluate("window.scrollTo(0, 60)")
        y0 = page.evaluate("window.scrollY")
        pick(page, 4, "wishlist")
        check("scroll did not jump", abs(page.evaluate("window.scrollY") - y0) < 2)
        check("focus is back on the same menu", page.evaluate("document.activeElement.classList.contains('paint-status-select') && document.activeElement.dataset.paintId") == "4")

        print("\n--- 4. Not owned on an unset paint ---")
        go(page)
        page.evaluate("document.querySelectorAll('#toast, .toast').forEach(e => e.remove())")
        page.evaluate("const q = book.paints.find(p => p.id === 3); delete q.status; q.owned = false; renderRecipes()")
        go(page)
        before = page.evaluate("JSON.stringify(book)")
        pick(page, 3, "notowned")
        after = page.evaluate("JSON.stringify(book)"); check("choosing Not owned again changes nothing", after == before, [before[:300], after[:300]])
        check("and shows no toast", page.evaluate("!document.querySelector('#toast.show, .toast.show')") )

        print("\n--- 5. Looks, sizes ---")
        for look in ("classic", "bench", "forge", "parchment"):
            for scheme in ("dark", "light"):
                page.emulate_media(color_scheme=scheme)
                for w, h in ((390, 844), (360, 640)):
                    page.evaluate(f"document.documentElement.dataset.t = '{look}'; document.documentElement.dataset.theme = '{scheme}'")
                    go(page, w, h)
                    ok = page.evaluate("""() => document.documentElement.scrollWidth <= document.documentElement.clientWidth
                        && [...document.querySelectorAll('.paint-status-select')].every(e => { const r = e.getBoundingClientRect(); return r.right <= innerWidth && r.left >= 0 && r.height >= 44; })""")
                    check(f"{look} {scheme} {w}: no sideways scroll, menu on screen", ok)
        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

main()
