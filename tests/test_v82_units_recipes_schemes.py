"""R3b-2 tests for Minifolio (Units, Recipes and Schemes pages at wide sizes).

What changed (from 900 px):
 A recipe opened on its own (from Schemes) fills the content width instead of a 780 px strip; the recipe and scheme
 editors keep the narrow form width. Unit names inside a recipe chip are 12 px (were 10.8 px).
Checks: 899 px unchanged (recipe page still 780 max), 900 / 1280 / 1920 as designed, real dark and light (the
 'appearance' setting, not just the browser hint), no sideways scroll, tap targets 44 px or more.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright
from launch_helpers import leave_launch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways, rec, unit = t.load, t.no_sideways, t.rec, t.unit
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

RECIPES = [rec(1, "Blue armour", "Armour", [1]), rec(2, "Orange trim", "Trim", [2])]
UNITS = [unit(1, "Troop A", "Gloom Legion", [1, 2]), unit(2, "Troop B", "Gloom Legion", [1])]
SCHEMES = [{"id": 1, "name": "Gloom scheme", "faction": "Gloom Legion", "auto": False, "recipes": [1, 2]}]

def set_up(page, appearance):
    page.evaluate("""([s, a]) => { const b = JSON.parse(localStorage.getItem('shades-of-grey-recipes')); b.schemes = s;
        localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b));
        const st = JSON.parse(localStorage.getItem('shades-of-grey-settings') || '{}'); st.appearance = a;
        localStorage.setItem('shades-of-grey-settings', JSON.stringify(st)); }""", [SCHEMES, appearance])
    page.reload()
    page.wait_for_timeout(400)
    leave_launch(page)   # U4b: tap through the start page

def widths(page):
    return page.evaluate("""() => { const w = s => document.querySelector(s).getBoundingClientRect().width;
        return { page: w('#recipe-page'), main: w('main') }; }""")

def small_taps(page):
    return page.evaluate("""() => [...document.querySelectorAll('main button, main select')].filter(e => {
        const r = e.getBoundingClientRect(); return r.width > 0 && !e.closest('.hidden, .app-bar') && r.height < 43.5; })   /* U4a: the header's basket (inside main now) counts at its enlarged tap area, 44 px, checked in test_v88_menu */.map(e => e.textContent.trim().slice(0, 20))""")

def open_scheme_recipe(page):
    page.click('nav button[data-tab="recipes"]')
    page.click('#recipe-seg [data-view="schemes"]')
    page.click('#scheme-list .scheme-recipe-row:has-text("Orange trim")')   # S2 (v95): the scheme card lists its recipes as rows now, not chips
    page.wait_for_timeout(150)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: d.dismiss())
        load(page, recipes=RECIPES, units=UNITS)

        for appearance in ("dark", "light"):
            set_up(page, appearance)
            check(f"{appearance}: the page really is {appearance}",
                  page.evaluate("() => document.documentElement.dataset.appearance === 'light'") == (appearance == "light"))

            print(f"\n--- {appearance}: 899 px, nothing changes ---")
            page.set_viewport_size({"width": 899, "height": 900})
            open_scheme_recipe(page)
            w = widths(page)
            check(f"{appearance} 899: recipe page not widened by the new rule", w["page"] <= 899, w)
            check(f"{appearance} 899: no sideways scroll", no_sideways(page))
            check(f"{appearance} 899: unit chips keep the old small text size",
                  page.evaluate("() => parseFloat(getComputedStyle(document.querySelector('#recipe-page .recipe-chip small')).fontSize)") < 11.5)

            print(f"\n--- {appearance}: 900, 1280 and 1920 ---")
            for width in (900, 1280, 1920):
                page.set_viewport_size({"width": width, "height": 900})
                w = widths(page)
                check(f"{appearance} {width}: recipe from Schemes fills the content width (no 780 strip)",
                      w["page"] > 800 and abs(w["page"] - w["main"]) < 2, w)
                check(f"{appearance} {width}: not wider than --content-max",
                      page.evaluate("() => document.querySelector('#recipe-page').getBoundingClientRect().width <= parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--content-max'))"))
                check(f"{appearance} {width}: no sideways scroll", no_sideways(page))
                check(f"{appearance} {width}: unit names in the chip are 12 px",
                      page.evaluate("() => getComputedStyle(document.querySelector('#recipe-page .recipe-chip small')).fontSize") == "12px")
                check(f"{appearance} {width}: tap targets 44 px or more", not small_taps(page), small_taps(page))

            page.set_viewport_size({"width": 1280, "height": 900})
            print(f"\n--- {appearance}: editors keep the form width ---")
            page.evaluate("() => { document.querySelector('#recipe-page .recipe-menu-button').click(); document.querySelector('#recipe-page .recipe-menu-list button').click(); }")   # RS1: Edit is a menu now
            page.wait_for_timeout(200)
            w = widths(page)
            check(f"{appearance} 1280: recipe editor stays at 780 or less", w["page"] <= 781, w)
            check(f"{appearance} 1280: recipe editor, no sideways scroll", no_sideways(page))
            page.click("#recipe-page >> text=Cancel")
            page.wait_for_timeout(150)
            w = widths(page)
            check(f"{appearance} 1280: back from the editor, the recipe fills the width again", w["page"] > 1000, w)

            print(f"\n--- {appearance}: list pages and the unit pane ---")
            page.reload(); page.wait_for_timeout(400); leave_launch(page)   # U4b: tap through the start page
            page.click('nav button[data-tab="recipes"]')
            page.click('#recipe-seg [data-view="schemes"]')
            for width in (1280, 1920):
                page.set_viewport_size({"width": width, "height": 900})
                check(f"{appearance} {width}: scheme list, no sideways scroll, taps 44 px or more", no_sideways(page) and not small_taps(page), small_taps(page))
            page.click('nav button[data-tab="units"]')
            page.click('#unit-list li.unit:has-text("Troop A") .info')
            page.wait_for_timeout(150)
            for width in (1280, 1920):
                page.set_viewport_size({"width": width, "height": 900})
                check(f"{appearance} {width}: units with the side pane open, no sideways scroll, taps 44 px or more", no_sideways(page) and not small_taps(page), small_taps(page))

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
