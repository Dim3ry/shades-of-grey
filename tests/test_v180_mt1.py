"""MT1 tests for Minifolio: three Models tab changes (new behaviour only).

1. Search models: a box at the top of the Filters sheet; matches name and nickname, any part, any case; updates as you type and keeps focus;
   works with the other filters, counts in the Filters number, shows in the summary line, and Clear all empties it.
2. Game headings fold: an arrow and a 44 px tap target; remembered on this device; a search or filter shows matches in a folded game without
   changing the remembered fold; Select all shown skips a folded game; jumps open the game first; no arrows when not grouped by game.
3. Unit card: no Recipes section until Details is open; inside Details the order is stage, photos, recipes, notes, edit, delete;
   Back from Open in Painting reopens Details and Recipes at the same scroll place.
4. Looks: phone and wide, dark and light, no sideways scroll.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from common import open_unit_card

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

PAINTS = [{"id": 1, "brand": "Citadel", "name": "Kantor Blue", "colour": "#1b3f94"}]
R1 = {"id": 1, "name": "Deep blue armour", "steps": [{"title": "Base", "technique": "Base", "coats": 2, "paints": [{"paint": 1, "mix": 100}]}]}

def unit(i, name, game, faction="Ultramarines", **extra):
    u = {"id": i, "name": name, "hobby": game, "faction": faction, "stage": 1, "count": 1, "added": "2026-10-01", "log": [["2026-10-01", 1]]}
    u.update(extra)
    return u

UNITS = [unit(1, "Intercessors", "40K", recipes=[1], nickname="Gold Squad"), unit(2, "Hellblasters", "40K"),
         unit(3, "Captain", "Horus Heresy", "Sons of Horus"), unit(4, "Legionaries", "Horus Heresy", "Sons of Horus", nickname="Old Guard"),
         unit(5, "Dreadnought", "40K", "Space Wolves", stage=5, log=[["2026-10-01", 5]])]
PAD = [unit(20 + i, f"Pad {i}", "40K") for i in range(10)]

def start(page, units=UNITS, settings=None):
    load(page, units=units, paints=PAINTS, recipes=[R1], settings=settings)
    page.click('nav button[data-tab="units"]')
    page.wait_for_timeout(250)

def shown_names(page):
    return page.evaluate("[...document.querySelectorAll('#unit-list > li.unit .name')].map(e => e.textContent)")

def open_filters(page):
    page.click("#toggle-filters")
    page.wait_for_selector("#fs-search-input")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("--- 1. Search models ---")
        start(page)
        open_filters(page)
        check("the box is the first thing in the sheet and is labelled Search models",
              page.evaluate("document.querySelector('#filters-sheet .fs-body').firstElementChild.querySelector('label').textContent") == "Search models")
        page.focus("#fs-search-input")
        page.keyboard.type("ELL")
        page.wait_for_timeout(200)
        check("part of a word, any case, updates as you type", shown_names(page) == ["Hellblasters"], shown_names(page))
        check("the box keeps focus while the list changes", page.evaluate("document.activeElement.id") == "fs-search-input")
        page.keyboard.press("Control+A")
        page.keyboard.type("gold")
        page.wait_for_timeout(200)
        check("a nickname matches too", len(shown_names(page)) == 1 and "Gold Squad" in shown_names(page)[0], shown_names(page))
        check("it counts as one filter and shows in the summary line",
              "Filters (1)" in page.inner_text("#toggle-filters") and "gold" in page.inner_text("#filter-note").lower(), page.inner_text("#filter-note"))
        page.click("#fs-chips-game .chip >> text=Horus Heresy")
        page.wait_for_timeout(200)
        check("with another filter both must match", shown_names(page) == [] and "Filters (2)" in page.inner_text("#toggle-filters"), shown_names(page))
        page.click("#fs-clear")
        page.wait_for_timeout(200)
        check("Clear all empties the box and shows everything again",
              page.input_value("#fs-search-input") == "" and len(shown_names(page)) == 5 and page.inner_text("#toggle-filters").strip() == "Filters")
        page.fill("#fs-search-input", "   ")
        page.wait_for_timeout(150)
        check("only spaces search nothing", len(shown_names(page)) == 5 and page.inner_text("#toggle-filters").strip() == "Filters")
        page.click(".fs-close")

        print("--- 2. Folding game headings ---")
        start(page)
        heads = page.locator("#unit-list .game-fold")
        check("each game heading has an arrow button, all open", heads.count() == 2 and heads.nth(0).get_attribute("aria-expanded") == "true")
        h = heads.nth(0).bounding_box()
        check("the heading is 44 px tall or more", h["height"] >= 44, h)
        heads.nth(0).click()
        page.wait_for_timeout(250)
        check("tapping folds that game only", len(shown_names(page)) == 2 and heads.nth(0).get_attribute("aria-expanded") == "false", shown_names(page))
        check("the fold is remembered in settings", page.evaluate("settings.foldedGames") == ["40K"])
        page.reload()
        page.wait_for_timeout(800)
        page.click('nav button[data-tab="units"]')
        page.wait_for_timeout(300)
        check("and survives a reload", len(shown_names(page)) == 2, shown_names(page))
        open_filters(page)
        page.fill("#fs-search-input", "dread")
        page.wait_for_timeout(200)
        check("a search shows its match in a folded game", shown_names(page) == ["Dreadnought"], shown_names(page))
        check("while searching there is no arrow and the fold is unchanged",
              page.locator("#unit-list .game-fold").count() == 0 and page.evaluate("settings.foldedGames") == ["40K"])
        page.click("#fs-clear")
        page.click(".fs-close")
        page.wait_for_timeout(200)
        check("clearing the search folds the game away again", len(shown_names(page)) == 2, shown_names(page))
        page.evaluate("selectMode = true; render()")
        page.wait_for_timeout(200)
        page.evaluate("selectAllShown()")
        page.wait_for_timeout(200)
        check("Select all shown skips the folded game", page.evaluate("[...ticked].sort()") == [3, 4], page.evaluate("[...ticked]"))
        page.evaluate("selectMode = false; render()")
        page.wait_for_timeout(200)
        page.evaluate("goToUnit(2)")
        page.wait_for_timeout(500)
        check("jumping to a unit opens its game first", page.locator("li.unit[data-id='2']").count() == 1 and page.evaluate("settings.foldedGames") == [])
        page.evaluate("saveUnitSort('az')")
        page.wait_for_timeout(250)
        check("sorted another way (not by game) there are no arrows and everything shows",
              page.locator("#unit-list .game-fold").count() == 0 and len(shown_names(page)) == 5)

        print("--- 3. The unit card ---")
        start(page)
        card = page.locator("li.unit[data-id='1']")
        open_unit_card(page, "li.unit[data-id='1']")
        check("an open card with Details shut has no Recipes section", card.locator(".recipes-head, .unit-recipes").count() == 0)
        card.locator(".details-toggle").click()
        page.wait_for_timeout(300)
        order = page.evaluate("""() => [...document.querySelector("li.unit[data-id='1'] .panel").children].map(e =>
            e.classList.contains('jump-stage') || e.querySelector('.jump-stage') ? 'stage' : e.classList.contains('gallery') ? 'photos' :
            e.classList.contains('unit-recipes') ? 'recipes' : e.querySelector('textarea') ? 'notes' : e.classList.contains('edit-details') ? 'edit' :
            e.classList.contains('panel-buttons') ? 'delete' : '?')""")
        check("inside Details: stage, photos, recipes, notes, edit, delete", order == ["stage", "photos", "recipes", "notes", "edit", "delete"], order)
        card.locator(".recipes-head").click()
        page.wait_for_timeout(250)
        card.locator(".recipe-row").nth(0).click()
        page.wait_for_timeout(250)
        page.evaluate("() => { const r = document.querySelector(\"li.unit[data-id='1'] .recipe-open\").getBoundingClientRect(); window.scrollTo(0, window.scrollY + r.top - 200); }")
        page.wait_for_timeout(200)
        y = page.evaluate("window.scrollY")
        card.locator(".recipe-open").click()
        page.wait_for_timeout(500)
        page.locator("#recipe-page .link-button").first.click()
        page.wait_for_timeout(600)
        back_y = page.evaluate("window.scrollY")
        check("Back reopens Details and Recipes", card.locator(".panel").is_visible() and card.locator(".recipe-unroll").is_visible())
        check("at the same scroll place", abs(back_y - y) <= 2, (y, back_y))

        print("--- 4. Looks and sizes ---")
        for scheme in ("dark", "light"):
            for w, hh in ((390, 844), (360, 640)):
                page.set_viewport_size({"width": w, "height": hh})
                start(page, UNITS + PAD, settings={"appearance": scheme})
                page.locator("#unit-list .game-fold").nth(0).click()
                page.wait_for_timeout(200)
                fold = page.locator("#unit-list .game-fold").nth(0).bounding_box()
                open_filters(page)
                box = page.locator("#fs-search-input").bounding_box()
                check(f"{scheme} {w} px: folded heading and search box are 44 px or more and nothing scrolls sideways",
                      fold["height"] >= 43.9 and box["height"] >= 43.9 and no_sideways(page), (fold, box))
                page.click(".fs-close")
        page.set_viewport_size({"width": 1280, "height": 900})
        start(page, UNITS)
        page.locator("#unit-list .game-fold").nth(0).click()
        page.wait_for_timeout(200)
        open_filters(page)
        page.fill("#fs-search-input", "cap")
        page.wait_for_timeout(200)
        check("1280 px: search and fold work and nothing scrolls sideways", shown_names(page) == ["Captain"] and no_sideways(page), shown_names(page))
        page.click(".fs-close")
        page.set_viewport_size({"width": 390, "height": 844})

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
