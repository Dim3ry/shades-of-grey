"""Chunk RS1 tests for Minifolio: the recipe page. New behaviour only.

1. Edit button by the title rolls out Edit steps and paints, Duplicate, Copy as text, Delete recipe; closes on Edit, outside tap, Escape;
   the old row of four buttons at the bottom is gone; Delete recipe still asks first.
2. Each step row names the paint and the technique ("1. Macragge Blue, Base coat").
3. Used on is folded with the count in the heading, and shows nothing when the recipe is used on nothing.
4. Add to scheme sits on the shopping list row, same height, and shows none / the scheme name / "In 2 schemes".
5. The picker: ticks only apply on Done, 44 px ticks, search only over 6 schemes, toasts (10 s, above the bottom menu), units untouched.
6. New scheme opens the scheme form with the recipe ticked.
7. 390, 360 and 320 px, dark and light: no sideways scroll, tap targets 44 px or more.
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

def step(technique, *paint_ids):
    return {"technique": technique, "coats": 1, "paints": [{"paint": pid, "mix": None if len(paint_ids) == 1 else 50} for pid in paint_ids],
            "ratio": "", "note": "", "optional": False}

R1 = {"id": 101, "name": "Cold armour", "part": "Armour", "notes": "", "steps": [step("Base coat", 1), step("Layer", 4, 6), step("Glaze", 30)]}
R2 = {"id": 102, "name": "Lonely recipe", "part": "Armour", "notes": "", "steps": [step("Layer", 3)]}
UNITS = [{"id": i, "name": "Troop %d" % i, "hobby": "Test game", "faction": "Gloom Legion", "stage": 2, "count": 5,
          **({"recipes": [101]} if i <= 10 else {})} for i in range(1, 12)]

def schemes(n, with_recipe=()):
    return [{"id": i, "name": "Scheme %d" % i, "faction": "Gloom Legion", "auto": False,
             "recipes": [101] if i in with_recipe else [102]} for i in range(1, n + 1)]

def start(page, n_schemes, with_recipe=(), recipe_id=101, units=UNITS):
    t.load(page, paints=t.PAINTS + [{"id": 30, "brand": "Vallejo", "name": "Plain Grey", "colour": "#888888"}], recipes=[R1, R2], units=units, settings={"tab": "recipes", "recipeView": "recipes", "examplesChecked": True})
    page.evaluate("(s) => { book.schemes = s; render(); }", schemes(n_schemes, with_recipe))
    page.evaluate("(id) => openRecipe(id)", recipe_id)
    quiet(page)

def toast(page):
    page.wait_for_timeout(450)   # the message slides in; measure it once it has settled
    return page.evaluate("""() => { const e = document.getElementById('toast');
        return { shown: !e.classList.contains('hidden'), text: document.getElementById('toast-text').textContent,
                 life: e.style.getPropertyValue('--toast-life'), undo: !document.getElementById('toast-undo').classList.contains('hidden'),
                 bottom: e.getBoundingClientRect().bottom, tabs: Math.min(...[...document.querySelectorAll('.tabs button')].map(b => b.getBoundingClientRect().top)) }; }""")

def clear_toast(page):
    page.evaluate("() => document.getElementById('toast').classList.add('hidden')")

def open_picker(page):
    page.click(".recipe-scheme-add")
    page.wait_for_timeout(200)

def scheme_ids(page):
    return page.evaluate("() => book.schemes.filter(s => s.recipes.includes(101)).map(s => s.id)")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. Edit menu ---")
        start(page, 3, with_recipe=(1,))
        check("one small Edit button sits in the title card", page.locator("#recipe-page .recipe-title-row .recipe-menu-button").count() == 1)
        check("no row of four buttons at the bottom", page.locator("#recipe-page .panel-buttons").count() == 0
              and not page.locator("#recipe-page >> text=/^Delete$/").count())
        check("menu starts closed", page.locator(".recipe-menu-list").is_hidden())
        page.click(".recipe-menu-button")
        words = page.evaluate("() => [...document.querySelectorAll('.recipe-menu-list button')].map(b => b.textContent)")
        check("menu lists the four actions", words == ["Edit steps and paints", "Duplicate", "Copy as text", "Delete recipe"], words)
        check("each menu entry is 44 px or more", page.evaluate("() => [...document.querySelectorAll('.recipe-menu-list button, .recipe-menu-button')].every(b => b.getBoundingClientRect().height >= 43.5)"))
        page.click(".recipe-menu-button")
        check("Edit again closes it", page.locator(".recipe-menu-list").is_hidden())
        page.click(".recipe-menu-button")
        page.mouse.click(5, 400)
        check("tapping outside closes it", page.locator(".recipe-menu-list").is_hidden())
        page.click(".recipe-menu-button")
        page.keyboard.press("Escape")
        check("Escape closes it", page.locator(".recipe-menu-list").is_hidden())
        page.click(".recipe-menu-button")
        page.click("text=Delete recipe")
        check("Delete recipe still asks first", page.locator("#dialog-backdrop:not(.hidden)").count() == 1 and "Delete the recipe" in page.inner_text("#dialog-message"))
        page.click("#dialog-no")
        check("answering No keeps the recipe", page.evaluate("() => !!recipeById(101)"))
        page.click(".recipe-menu-button")
        page.click("text=Delete recipe")
        page.click("#dialog-yes")
        tt = toast(page)
        check("deleting still offers Undo", tt["shown"] and tt["undo"] and "Deleted" in tt["text"], tt)
        page.click("#toast-undo")
        check("Undo brings it back", page.evaluate("() => !!recipeById(101)"))
        page.evaluate("(id) => openRecipe(id)", 101)
        quiet(page)
        page.click(".recipe-menu-button")
        page.click("text=Duplicate")
        check("Duplicate opens a copy in the editor", "(copy)" in page.evaluate("() => recipeDraft && recipeDraft.name"))
        page.evaluate("() => { recipeDraft = null; renderRecipes(); }")
        page.evaluate("(id) => openRecipe(id)", 101)
        quiet(page)
        page.click(".recipe-menu-button")
        page.click("text=Edit steps and paints")
        check("Edit steps and paints opens the editor", page.evaluate("() => !!recipeDraft && recipeDraft.id === 101"))

        print("\n--- 2. Steps name the paint ---")
        start(page, 3)
        rows = page.evaluate("() => [...document.querySelectorAll('.step-line')].map(b => ({ t: b.querySelector('.step-line-text').textContent, sw: b.querySelectorAll('.swatch').length }))")
        check("step 1 reads paint name then technique", rows[0]["t"] == "1. Macragge Blue, Base coat", rows)
        check("a mixed step names both paints", rows[1]["t"] == "2. Eshin Grey + Rakarth Flesh, Layer", rows)
        check("each row keeps its colour swatches", rows[0]["sw"] == 1 and rows[1]["sw"] == 2, rows)

        print("\n--- 3. Used on ---")
        head = page.inner_text("#recipe-page .card-fold-button")
        check("Used on is folded with the count", head.strip() == "Used on 10 units", head)
        check("list hidden by default", page.locator("#used-on-list").is_hidden())
        page.click("#recipe-page .card-fold-button")
        check("tap opens the full list", page.locator("#used-on-list").is_visible() and page.locator("#used-on-list .recipe-chip").count() == 10)
        page.click("#recipe-page .card-fold-button")
        check("tap again folds it", page.locator("#used-on-list").is_hidden())
        page.evaluate("(id) => openRecipe(id)", 102)
        quiet(page)
        check("a recipe used on nothing shows no Used on", "Used on" not in page.inner_text("#recipe-page"))
        check("the Add to a unit menu is still there", page.locator('#recipe-page select[aria-label="Link this recipe to a unit"]').count() == 1)

        print("\n--- 4. Add to scheme button ---")
        start(page, 3)
        check("no scheme: Add to scheme", page.inner_text(".recipe-scheme-add") == "Add to scheme")
        a = page.evaluate("""() => { const s = document.querySelector('.recipe-scheme-add').getBoundingClientRect(), b = document.querySelector('.recipe-bottom-row button:not(.recipe-scheme-add)').getBoundingClientRect();
            return { sameRow: Math.abs(s.top - b.top) < 3, h: s.height, bh: b.height, w: s.width, bw: b.width }; }""")
        check("same row, same height as the shopping list button", a["sameRow"] and abs(a["h"] - a["bh"]) < 1 and a["h"] >= 43.5, a)
        start(page, 3, with_recipe=(2,))
        check("one scheme: its name", page.inner_text(".recipe-scheme-add") == "Scheme 2")
        start(page, 3, with_recipe=(1, 3))
        check("two schemes: a count", page.inner_text(".recipe-scheme-add") == "In 2 schemes")

        print("\n--- 5. The picker ---")
        start(page, 3, with_recipe=(1, 3))
        open_picker(page)
        check("picker lists every scheme", page.locator(".scheme-picker-row").count() == 3)
        check("already-in schemes start ticked", page.evaluate("() => [...document.querySelectorAll('.scheme-picker-row .pick-tick')].map(b => b.getAttribute('aria-checked'))") == ["true", "false", "true"])
        check("ticks are 44 px or more", page.evaluate("() => [...document.querySelectorAll('.scheme-picker-row .pick-tick')].every(b => { const r = b.getBoundingClientRect(); return r.width >= 43.5 && r.height >= 43.5; })"))
        check("no search with 3 schemes", page.locator(".scheme-picker-search").count() == 0)
        check("New scheme and Done are at the bottom", page.evaluate("() => [...document.querySelectorAll('#dialog-buttons button:not(.hidden)')].map(b => b.textContent)") == ["New scheme", "Done"])
        page.click(".scheme-picker-row:nth-child(2) .pick-tick")
        check("ticking changes nothing until Done", scheme_ids(page) == [1, 3])
        page.click("#dialog-yes")
        tt = toast(page)
        check("Done adds it and says how many", scheme_ids(page) == [1, 2, 3] and tt["text"] == "Added to 1 scheme", (scheme_ids(page), tt))
        check("toast: shared 10 s length, above the bottom menu, no Undo", tt["life"] == "10s" and tt["bottom"] <= tt["tabs"] + 1 and not tt["undo"], tt)
        check("the button now counts the schemes", page.inner_text(".recipe-scheme-add") == "In 3 schemes")
        check("units were not touched", page.evaluate("() => models.filter(m => (m.recipes || []).includes(101)).length") == 10)
        clear_toast(page)
        open_picker(page)
        page.click("#dialog-yes")
        check("nothing changed: no toast", not toast(page)["shown"])
        open_picker(page)
        page.click(".scheme-picker-row:nth-child(1) .pick-tick")
        page.click("#dialog-yes")
        check("unticking says Schemes updated", scheme_ids(page) == [2, 3] and toast(page)["text"] == "Schemes updated", toast(page))
        clear_toast(page)
        open_picker(page)
        page.click(".scheme-picker-row:nth-child(1) .pick-tick")
        page.mouse.click(5, 5)
        tt = toast(page)
        check("outside tap throws the ticks away and says so", scheme_ids(page) == [2, 3] and tt["text"] == "Closed without changes" and tt["life"] == "10s", (scheme_ids(page), tt))
        open_picker(page)
        page.keyboard.press("Escape")
        check("Escape does the same", toast(page)["text"] == "Closed without changes" and page.locator("#dialog-backdrop.hidden").count() == 1)
        start(page, 8)
        open_picker(page)
        check("search shows with 8 schemes", page.locator(".scheme-picker-search").count() == 1)
        page.fill(".scheme-picker-search", "scheme 7")
        check("search narrows the list", page.locator(".scheme-picker-row:visible").count() == 1)
        page.fill(".scheme-picker-search", "")
        page.click(".scheme-picker-row:nth-child(1) .pick-tick")
        page.click(".scheme-picker-row:nth-child(2) .pick-tick")
        page.click("#dialog-yes")
        check("two added: Added to 2 schemes", toast(page)["text"] == "Added to 2 schemes", toast(page))

        print("\n--- 6. New scheme ---")
        start(page, 3)
        open_picker(page)
        page.click("#dialog-extra")
        quiet(page)
        check("the scheme form opens with this recipe in it", page.evaluate("() => !!schemeDraft && schemeDraft.id === null && schemeDraft.recipes.join() === '101'"))
        page.click("#scheme-page .link-button")
        check("closing it straight away does not ask to discard", page.locator("#dialog-backdrop.hidden").count() == 1 and page.evaluate("() => !schemeDraft"))

        print("\n--- 7. Fit at three widths, dark and light ---")
        for width, height in ((390, 844), (360, 640), (320, 640)):
            for mode in ("dark", "light"):
                page.set_viewport_size({"width": width, "height": height})
                start(page, 8, with_recipe=(1,))
                page.emulate_media(color_scheme=mode)
                label = f"{width}px {mode}: "
                small = page.evaluate("""() => [...document.querySelectorAll('#recipe-page button, #recipe-page select')].filter(b => b.offsetParent && !b.closest('.step-body'))
                    .filter(b => b.getBoundingClientRect().height < 43.5).map(b => b.textContent.trim().slice(0, 20))""")
                check(label + "no sideways scroll, taps are 44 px or more", t.no_sideways(page) and not small, small)
                open_picker(page)
                fit = page.evaluate("""() => { const d = document.getElementById('dialog').getBoundingClientRect();
                    const y = document.getElementById('dialog-yes').getBoundingClientRect();
                    return { inside: d.left >= 0 && d.right <= innerWidth && d.top >= 0 && d.bottom <= innerHeight, doneInside: y.bottom <= innerHeight && y.height >= 43.5,
                             side: document.documentElement.scrollWidth <= innerWidth + 1 }; }""")
                check(label + "picker fits and Done is reachable", fit["inside"] and fit["doneInside"] and fit["side"], fit)
                page.keyboard.press("Escape")
        page.screenshot(path=os.path.join(t.SHOTS, "rs1_recipe_page.png"))

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
