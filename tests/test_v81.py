"""v81 tests for Minifolio (chunk R3a: wide layouts for Shopping and the Compendium).

What changed:
 From 900 px the Shopping list card has the brand lists on the left and the shop links and Copy as text in a column on the right.
 From 900 px the Compendium has the colour wheel on the left and the fold-outs on the right, and no longer stops at 780 px wide.
 Under 900 px both are exactly as before (one column, same order).

Checks:
1. 899 / 390 / 360 px: Shopping stacked in its old order, Compendium wheel above the sections, no sideways scroll. Dark and light.
2. 900 / 1280 / 1920 px, dark and light: Shopping lists left, buy bar and Copy right (Copy under the buy bar). No sideways scroll,
   tap targets 44 px or more, card no wider than the content width.
3. 900 / 1280 / 1920 px, dark and light: Compendium wheel left, sections right, same top. A section still opens.
4. Shop links turned off: Copy as text still sits on the right. An empty list stays a plain card.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lab_helpers as labh   # X1: the old all-in-one Compendium page (see lab_helpers.py)
import test_v31 as t

load, no_sideways, rec = t.load, t.no_sideways, t.rec
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

PAINTS = [dict(p, status="wishlist") for p in t.PAINTS[:6]]
RECIPES = [rec(1, "Blue armour", "Armour", [1, 2])]
CONTENT_MAX = 1280   # --content-max

def shop_boxes(page):
    return page.evaluate("""() => { const r = s => { const e = document.querySelector(s); return e ? e.getBoundingClientRect().toJSON() : null; };
        return { card: r('#shop-panel .card'), lists: r('#shop-panel .shop-lists'), buy: r('#shop-panel .shop-side-buy'),
                 copy: r('#shop-panel .shop-side-copy'), head: r('#shop-panel .shop-head') }; }""")

def comp_boxes(page):
    return page.evaluate("""() => { const r = s => { const e = document.querySelector(s); return e ? e.getBoundingClientRect().toJSON() : null; };
        return { card: r('.compendium-card'), wheel: r('#compendium-body .wheel-block'), folds: r('#compendium-body .compendium-folds'),
                 firstFold: r('#compendium-body .fold') }; }""")

def small_taps(page, scope):
    return page.evaluate("""(scope) => [...document.querySelectorAll(scope + ' button')].filter(b => b.offsetParent)
        .map(b => b.getBoundingClientRect().height).filter(h => h < 43.5)""", scope)

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 900}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        load(page, paints=PAINTS, recipes=RECIPES, settings={"recipeView": "shopping"})
        page.click('nav button[data-tab="recipes"]')

        print("\n--- 1. Shopping under 900 px: one column in the old order ---")
        for scheme in ("dark", "light"):
            page.emulate_media(color_scheme=scheme)
            for width in (360, 390, 899):
                page.set_viewport_size({"width": width, "height": 900})
                b = shop_boxes(page)
                check(f"{scheme} {width}: buy bar, then lists, then Copy, all one column",
                      b["head"]["bottom"] <= b["buy"]["top"] + 1 and b["buy"]["bottom"] <= b["lists"]["top"] + 1
                      and b["lists"]["bottom"] <= b["copy"]["top"] + 1 and abs(b["lists"]["left"] - b["buy"]["left"]) < 30, b)
                check(f"{scheme} {width}: no sideways scroll", no_sideways(page))

        print("\n--- 2. Shopping from 900 px: lists left, buy bar and Copy right ---")
        for scheme in ("dark", "light"):
            page.emulate_media(color_scheme=scheme)
            for width in (900, 1280, 1920):
                page.set_viewport_size({"width": width, "height": 900})
                b = shop_boxes(page)
                check(f"{scheme} {width}: lists left, buy bar right, Copy under the buy bar",
                      b["lists"]["right"] <= b["buy"]["left"] + 1 and abs(b["buy"]["left"] - b["copy"]["left"]) < 2
                      and b["buy"]["bottom"] <= b["copy"]["top"] + 1 and b["copy"]["top"] < b["lists"]["bottom"] + 40, b)
                check(f"{scheme} {width}: card no wider than the content width, no sideways scroll",
                      b["card"]["width"] <= CONTENT_MAX + 1 and no_sideways(page), b["card"])
                check(f"{scheme} {width}: buttons 44 px or taller", not small_taps(page, "#shop-panel"), small_taps(page, "#shop-panel"))

        print("\n--- 3. Compendium ---")
        labh.go_compendium(page)
        page.wait_for_timeout(300)
        for scheme in ("dark", "light"):
            page.emulate_media(color_scheme=scheme)
            for width in (360, 899):
                page.set_viewport_size({"width": width, "height": 900})
                b = comp_boxes(page)
                check(f"{scheme} {width}: wheel above the sections, no sideways scroll",
                      b["wheel"]["bottom"] <= b["firstFold"]["top"] + 1 and no_sideways(page), b)
            for width in (900, 1280, 1920):
                page.set_viewport_size({"width": width, "height": 900})
                b = comp_boxes(page)
                check(f"{scheme} {width}: wheel left, sections right, same top",
                      b["wheel"]["right"] <= b["folds"]["left"] + 1 and abs(b["wheel"]["top"] - b["folds"]["top"]) < 2, b)
                check(f"{scheme} {width}: card fills the content width (not 780), no sideways scroll",
                      b["card"]["width"] > min(width - 40, CONTENT_MAX) - 40 and b["card"]["width"] <= CONTENT_MAX + 1 and no_sideways(page), b["card"])
                check(f"{scheme} {width}: section buttons 44 px or taller", not small_taps(page, "#compendium-body .fold-head"),
                      small_taps(page, "#compendium-body .fold-head"))
        page.set_viewport_size({"width": 1280, "height": 900})
        page.click("#compendium-body .fold-button >> nth=0")
        check("a section still opens in the right column", page.locator("#compendium-body .compendium-folds .fold-panel:not([hidden])").count() == 1)
        page.click("#compendium-body .wheel-seg >> nth=0")
        check("tapping the wheel keeps the section open", page.locator("#compendium-body .compendium-folds .fold-panel:not([hidden])").count() == 1)

        print("\n--- 4. Edge cases ---")
        page.click('nav button[data-tab="recipes"]')
        page.evaluate("() => { settings.hideShopLinks = true; renderRecipes(); }")
        b = shop_boxes(page)
        check("shop links off: Copy as text still on the right, lists on the left",
              b["buy"] is None and b["copy"] and b["lists"]["right"] <= b["copy"]["left"] + 1, b)
        page.evaluate("() => { book.paints.forEach(p => p.status = 'owned'); renderRecipes(); }")
        check("nothing to buy: a plain card with no split", page.locator("#shop-panel .card.layout-split").count() == 0)

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
