"""v78 tests for Minifolio (chunk R2a: the Recipes tab beside its open recipe on wide screens).

What changed:
 From 900 px an open recipe (or one being written) shows to the right of the recipe list. Under 900 px the recipe still
 fills the screen exactly as before. Recipes opened from Your Palette or Schemes still fill the screen.

Checks:
1. 899 px (and 390 / 360): an open recipe replaces the list, as before. No sideways scroll. Dark and light.
2. 900 px and 1280 px: list on the left, recipe on the right, the open recipe is marked in the list. Dark and light.
3. Opening another recipe from the list works, Back closes the recipe and the list fills the width again.
4. Tap targets 44 px or more; writing a recipe sits beside the list; picking another recipe while writing asks first.
5. Delete and Undo still work from the open recipe.
6. Crossing 900 px with a recipe open moves it between full screen and beside the list.
7. A recipe opened from Your Palette stays full screen on a wide screen.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from launch_helpers import wait_settled
import test_v31 as t

load, no_sideways, rec = t.load, t.no_sideways, t.rec
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

RECIPES = [rec(1, "Blue armour", "Armour", [1]), rec(2, "Orange trim", "Trim", [2]), rec(3, "Teal eyes", "Eyes", [3])]

def state(page):
    return page.evaluate("""() => { const r = s => document.querySelector(s).getBoundingClientRect();
        const vis = s => { const e = document.querySelector(s); return !!e && getComputedStyle(e).display !== 'none'; };
        return { homeShown: vis('#recipe-home'), pageShown: vis('#recipe-page'), home: r('#recipe-home'), page: r('#recipe-page') }; }""")

def open_recipe(page, name):
    page.click(f'#recipe-list .recipe-item:has-text("{name}")')

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        load(page, recipes=RECIPES, units=[])
        page.click('nav button[data-tab="recipes"], nav button[data-tab="recipes"]')

        print("\n--- 1. Under 900 px: unchanged ---")
        for scheme in ("dark", "light"):
            page.emulate_media(color_scheme=scheme)
            for width in (360, 390, 899):
                page.set_viewport_size({"width": width, "height": 900})
                open_recipe(page, "Blue armour")
                wait_settled(page)   # v92 (Mo3a): below 900 px the list steps back over 240 ms; once done only the detail is showing
                s = state(page)
                check(f"{scheme} {width}: recipe fills the screen, list hidden", s["pageShown"] and not s["homeShown"], s)
                check(f"{scheme} {width}: no sideways scroll", no_sideways(page))
                page.click("#recipe-page >> text=All recipes")
                wait_settled(page)   # v92 (Mo3a): the detail slides away over 240 ms
                check(f"{scheme} {width}: Back shows the list again", state(page)["homeShown"] and not state(page)["pageShown"])

        print("\n--- 2. 900 px and wider: side by side ---")
        for scheme in ("dark", "light"):
            page.emulate_media(color_scheme=scheme)
            for width in (900, 1280):
                page.set_viewport_size({"width": width, "height": 900})
                open_recipe(page, "Blue armour")
                s = state(page)
                check(f"{scheme} {width}: list left, recipe right, same top", s["homeShown"] and s["pageShown"] and s["home"]["left"] < s["page"]["left"]
                      and abs(s["home"]["top"] - s["page"]["top"]) < 2 and s["page"]["width"] > s["home"]["width"], s)
                check(f"{scheme} {width}: open recipe is marked in the list",
                      page.evaluate("() => document.querySelector('#recipe-list .recipe-item[aria-current=true]').textContent.includes('Blue armour')"))
                check(f"{scheme} {width}: no sideways scroll", no_sideways(page))
                page.click("#recipe-page >> text=All recipes")
                s = state(page)
                check(f"{scheme} {width}: closing gives the list the full width", s["homeShown"] and not s["pageShown"] and s["home"]["width"] > width * 0.8, s)

        print("\n--- 3. Switching recipes, tap targets ---")
        page.set_viewport_size({"width": 1280, "height": 900})
        open_recipe(page, "Blue armour")
        open_recipe(page, "Orange trim")
        check("opening another recipe shows it on the right", "Orange trim" in page.inner_text("#recipe-page h2"), page.inner_text("#recipe-page"))
        small = page.evaluate("""() => [...document.querySelectorAll('#recipe-page button, #recipe-home .recipe-item, #new-recipe')]
            .filter(b => b.offsetParent).map(b => b.getBoundingClientRect().height).filter(h => h < 43.5)""")
        check("buttons in both columns are 44 px or taller", not small, small)

        print("\n--- 4. Writing a recipe beside the list ---")
        page.click("#new-recipe")
        s = state(page)
        check("a new recipe opens on the right with the list kept", s["homeShown"] and s["pageShown"] and s["home"]["left"] < s["page"]["left"], s)
        page.fill("#recipe-page input >> nth=0", "Half written")
        open_recipe(page, "Teal eyes")
        check("picking another recipe while writing asks first", page.is_visible("#dialog-yes"))
        page.click("#dialog-no") if page.is_visible("#dialog-no") else None
        check("saying no keeps what was typed", page.input_value("#recipe-page input >> nth=0") == "Half written")
        open_recipe(page, "Teal eyes")
        page.click("#dialog-yes")
        check("saying yes opens the other recipe", "Teal eyes" in page.inner_text("#recipe-page h2"))

        print("\n--- 5. Delete and Undo ---")
        page.click("#recipe-page >> text=Delete")
        page.click("#dialog-yes")
        check("deleted: gone from the list, list full width", page.locator('#recipe-list .recipe-item:has-text("Teal eyes")').count() == 0 and not state(page)["pageShown"])
        page.click("#toast-undo")
        check("Undo brings the recipe back", page.locator('#recipe-list .recipe-item:has-text("Teal eyes")').count() == 1)

        print("\n--- 6. Crossing 900 px ---")
        open_recipe(page, "Blue armour")
        page.set_viewport_size({"width": 700, "height": 900})
        page.wait_for_timeout(300)
        s = state(page)
        check("narrowing under 900 px puts the recipe full screen", s["pageShown"] and not s["homeShown"], s)
        page.set_viewport_size({"width": 1280, "height": 900})
        page.wait_for_timeout(300)
        s = state(page)
        check("widening puts it beside the list again", s["pageShown"] and s["homeShown"], s)

        print("\n--- 7. From Your Palette: still full screen ---")
        page.click("#recipe-page >> text=All recipes")
        page.click('#recipe-seg [data-view="palette"]')
        page.click("#paint-list .paint-head:has-text('Macragge Blue')")
        # v80: from 900 px an open paint's details (with its recipe links) are in the Palette side pane, not under the paint in the list.
        page.locator("#palette-side").get_by_text("Blue armour").first.click()
        s = state(page)
        check("recipe opened from Your Palette fills the screen", s["pageShown"] and not s["homeShown"] and "Your Palette" in page.inner_text("#recipe-page"), s)
        check("no sideways scroll there", no_sideways(page))

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
