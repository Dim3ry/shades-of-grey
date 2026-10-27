"""v82 tests for Minifolio (chunk R3b-3: Your Palette, Shopping and Compendium at 1280 and 1920 px).

What changed (from 900 px only):
 The Compendium colour wheel stays in view (sticky) beside the long fold-outs.
 The Add to shopping list button in the Compendium is 44 px tall (it was 40).
Your Palette (list and swatches) and Shopping needed no change; they are only checked for sideways scroll and tap targets here.
Under 900 px nothing changes.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

BRANDS = ["Citadel", "Vallejo", "Army Painter", "Scale75", "AK", "Pro Acryl"]
PAINTS = [{"id": 100 + i, "brand": BRANDS[i % 6], "name": f"Test Paint {i}", "colour": "#%02x%02x%02x" % ((i * 37) % 256, (i * 91) % 256, (i * 53) % 256),
           "status": "wishlist" if i < 40 else "owned"} for i in range(50)]

def small_taps(page, scope):
    return page.evaluate("""(scope) => [...document.querySelectorAll(scope + ' button, ' + scope + ' summary')].filter(b => b.offsetParent)
        .map(b => b.getBoundingClientRect().height).filter(h => h < 43.5)""", scope)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 900}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        load(page, paints=PAINTS, recipes=[t.rec(1, "Blue", "Armour", [100, 101])], settings={"recipeView": "palette"})
        page.click('.tabs button[data-tab="recipes"]')

        print("\n--- 1. Palette (list, swatches) and Shopping, 40 wishlist paints: no sideways scroll, taps 44 px ---")
        for layout in ("list", "swatches"):
            page.click(f'#palette-layout [data-layout="{layout}"]')
            for scheme in ("dark", "light"):
                page.emulate_media(color_scheme=scheme)
                for width in (1280, 1920):
                    page.set_viewport_size({"width": width, "height": 900})
                    check(f"palette {layout} {scheme} {width}: no sideways scroll, buttons 44 px or taller",
                          no_sideways(page) and not small_taps(page, "#palette-view"), small_taps(page, "#palette-view"))
        page.evaluate("() => { settings.recipeView = 'shopping'; renderRecipes(); }")
        for scheme in ("dark", "light"):
            page.emulate_media(color_scheme=scheme)
            for width in (1280, 1920):
                page.set_viewport_size({"width": width, "height": 900})
                check(f"shopping {scheme} {width}: no sideways scroll, buttons 44 px or taller",
                      no_sideways(page) and not small_taps(page, "#shop-panel"), small_taps(page, "#shop-panel"))

        print("\n--- 2. Compendium ---")
        page.click('.tabs button[data-tab="compendium"]')
        page.wait_for_timeout(300)
        page.evaluate("() => document.querySelectorAll('#compendium-body .fold-button').forEach(b => b.click())")
        page.wait_for_timeout(300)
        pos = lambda: page.evaluate("() => getComputedStyle(document.querySelector('#compendium-body .compendium-split > .layout-main')).position")
        for scheme in ("dark", "light"):
            page.emulate_media(color_scheme=scheme)
            page.set_viewport_size({"width": 899, "height": 900})
            check(f"{scheme} 899: wheel not sticky (unchanged), no sideways scroll", pos() == "static" and no_sideways(page), pos())
            for width in (900, 1280, 1920):
                page.set_viewport_size({"width": width, "height": 900})
                page.evaluate("() => window.scrollTo(0, 0)")
                check(f"{scheme} {width}: wheel sticky, no sideways scroll", pos() == "sticky" and no_sideways(page), pos())
            check(f"{scheme} 1280: all fold-outs open, Add to shopping list 44 px or taller, section buttons 44 px or taller",
                  not small_taps(page, "#compendium-body"), small_taps(page, "#compendium-body"))
        page.set_viewport_size({"width": 1280, "height": 900})
        page.evaluate("() => window.scrollTo(0, 600)")
        page.wait_for_timeout(150)
        top = page.evaluate("() => document.querySelector('#compendium-body .wheel-block').getBoundingClientRect().top")
        check("scrolled down 600 px: the wheel is still on screen", 0 <= top < 200, top)
        page.click("#compendium-body .wheel-seg >> nth=0")
        page.wait_for_timeout(300)
        check("wheel detail open: no sideways scroll, buttons 44 px or taller, wheel block fits the screen",
              no_sideways(page) and not small_taps(page, "#compendium-body .wheel-block")
              and page.evaluate("() => document.querySelector('#compendium-body .wheel-block').getBoundingClientRect().height") <= 900,
              small_taps(page, "#compendium-body .wheel-block"))
        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
