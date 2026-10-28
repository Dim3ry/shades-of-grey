"""v80 tests for Minifolio (chunk R2c: Your Palette shows open paint details in a side pane on wide screens).

What changed:
 From 900 px the paint list is on the left and the details of every open paint are stacked as cards in a pane on the right,
 each with a Close button. Under 900 px the details still open inside the paint's own row. Units use the same pane helper
 (fillSidePane), so one Units check here proves the shared helper still works for them.

Checks:
1. 899 px (and 390 / 360): details inside the row, no pane, no sideways scroll. Dark and light.
2. 900 px and 1280 px: list left, pane right, same top, open row marked. Dark and light, no sideways scroll.
3. Several paints open, close one, close all. Tap targets 44 px or more.
4. Swatches view: the picked tile opens in the pane from 900 px and inside the grid below it.
5. Crossing 900 px with details open.
6. Units still use the shared pane.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways, rec, unit = t.load, t.no_sideways, t.rec, t.unit
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

PAINTS = t.PAINTS[:3]
A, B, C = (p["name"] for p in PAINTS)
RECIPES = [rec(1, "Blue armour", "Armour", [1, 2])]

def state(page):
    return page.evaluate("""() => { const r = s => document.querySelector(s).getBoundingClientRect();
        const shown = s => { const e = document.querySelector(s); return !!e && getComputedStyle(e).display !== 'none'; };
        return { side: shown('#palette-side'), cards: document.querySelectorAll('#palette-side .unit-side-card').length,
                 inline: document.querySelectorAll('#paint-list .panel').length,
                 list: r('#paint-list'), pane: r('#palette-side') }; }""")

def tap(page, name):
    page.click(f'#paint-list .paint-head:has-text("{name}")')

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        load(page, paints=PAINTS, recipes=RECIPES, units=[unit(1, "Troop A", "Gloom Legion")], settings={"recipeView": "palette"})
        page.click('nav button[data-tab="recipes"], nav button[data-tab="recipes"]')

        print("\n--- 1. Under 900 px: unchanged ---")
        for scheme in ("dark", "light"):
            page.emulate_media(color_scheme=scheme)
            for width in (360, 390, 899):
                page.set_viewport_size({"width": width, "height": 900})
                tap(page, A)
                s = state(page)
                check(f"{scheme} {width}: details inside the row, no pane", s["inline"] == 1 and not s["side"] and s["cards"] == 0, s)
                check(f"{scheme} {width}: no sideways scroll", no_sideways(page))
                tap(page, A)
                check(f"{scheme} {width}: tapping again closes it", state(page)["inline"] == 0)

        print("\n--- 2. 900 px and wider: side by side ---")
        for scheme in ("dark", "light"):
            page.emulate_media(color_scheme=scheme)
            for width in (900, 1280):
                page.set_viewport_size({"width": width, "height": 900})
                tap(page, A)
                s = state(page)
                check(f"{scheme} {width}: list left, pane right, same top, no inline panel",
                      s["side"] and s["cards"] == 1 and s["inline"] == 0 and s["list"]["left"] < s["pane"]["left"]
                      and abs(s["list"]["top"] - s["pane"]["top"]) < 2, s)
                check(f"{scheme} {width}: the open row is marked in the list",
                      page.evaluate("(n) => document.querySelector('#paint-list li.paint-item[aria-current=true]').textContent.includes(n)", A))
                check(f"{scheme} {width}: no sideways scroll", no_sideways(page))
                page.click("#palette-side .unit-side-card >> text=Close")
                check(f"{scheme} {width}: closing hides the pane", not state(page)["side"])

        print("\n--- 3. Several open, close one, close all ---")
        page.set_viewport_size({"width": 1280, "height": 900})
        tap(page, A); tap(page, B); tap(page, C)
        check("three paints open as three stacked cards", state(page)["cards"] == 3, state(page))
        page.click(f'#palette-side .unit-side-card:has-text("{B}") >> text=Close')
        side = page.inner_text("#palette-side")
        check("closing one leaves the other two", state(page)["cards"] == 2 and B not in side, side)
        small = page.evaluate("""() => [...document.querySelectorAll('#palette-side button, #paint-list .paint-head')]
            .filter(b => b.offsetParent && b.tagName === 'BUTTON').map(b => b.getBoundingClientRect().height).filter(h => h < 43.5)""")
        check("buttons in the pane and the list are 44 px or taller", not small, small)
        page.click(f'#palette-side .unit-side-card:has-text("{A}") >> text=Close')
        page.click(f'#palette-side .unit-side-card:has-text("{C}") >> text=Close')
        s = state(page)
        check("closing all gives the list the full width back", not s["side"] and s["list"]["width"] > 1000, s)
        tap(page, A)
        page.locator("#palette-side .linked-list button").first.click()
        page.wait_for_timeout(300)
        check("the recipe opens full screen from the pane", page.evaluate("() => openRecipeId") == 1)
        page.evaluate("() => { openRecipeId = null; settings.recipeView = 'palette'; renderRecipes(); }")

        print("\n--- 4. Swatches ---")
        page.click("#palette-layout button >> text=Swatches")
        page.click(".swatch-tile >> nth=0")
        s = state(page)
        check("1280: picked tile opens in the pane, not in the grid", s["cards"] == 1 and page.locator("#paint-list .swatch-detail").count() == 0, s)
        page.click("#palette-side .unit-side-card >> text=Close")
        check("closing the pane card unpicks the tile", not state(page)["side"] and page.locator(".swatch-tile[aria-expanded=true]").count() == 0)
        page.set_viewport_size({"width": 899, "height": 900})
        page.click(".swatch-tile >> nth=0")
        check("899: picked tile opens under its row", page.locator("#paint-list .swatch-detail").count() == 1 and not state(page)["side"])
        page.click(".swatch-tile >> nth=0")
        page.click("#palette-layout button >> text=List")

        print("\n--- 5. Crossing 900 px ---")
        page.set_viewport_size({"width": 1280, "height": 900})
        page.evaluate("() => { openPaintIds.clear(); renderPalette(); }")   # the recipe check above left one open
        tap(page, A)
        page.set_viewport_size({"width": 700, "height": 900})
        page.wait_for_timeout(300)
        s = state(page)
        check("narrowing puts the details inside the row", s["inline"] == 1 and not s["side"], s)
        page.set_viewport_size({"width": 1280, "height": 900})
        page.wait_for_timeout(300)
        s = state(page)
        check("widening puts them in the pane again", s["inline"] == 0 and s["cards"] == 1, s)

        print("\n--- 6. Units use the shared pane ---")
        page.click('nav button[data-tab="units"], nav button[data-tab="units"]')
        page.click('#unit-list li.unit:has-text("Troop A") .info')
        check("a unit opens in its pane", page.locator("#unit-side .unit-side-card").count() == 1)
        page.click("#unit-side .unit-side-card >> text=Close")
        check("and closes", page.locator("#unit-side .unit-side-card").count() == 0)

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
