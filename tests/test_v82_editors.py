"""v82 editors tests for Minifolio (chunk R3b-5: recipe editor, scheme editor and Paste recipes on wide screens).

What changed:
 Paste recipes is held to 780 px wide from 900 px (its text box and step rows were 1200 px or more). The scheme editor
 shows its two cards side by side from 900 px. The recipe editor beside the list already looked right and is untouched.
Checks: 899 px unchanged (stacked, full width), 900 / 1280 / 1920 as designed, dark and light, no sideways scroll,
 tap targets 44 px or more. Serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []
def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

RECIPES = [t.rec(1, "Blue armour", "Armour", [1, 3]), t.rec(2, "Orange trim", "Trim", [2]), t.rec(3, "Teal eyes", "Eyes", [3])]
NOTES = "Armour:\nMacragge Blue, Turquoise\n\nEyes:\nEshin Grey, Ink Sky"
SMALL = """(sel) => [...document.querySelectorAll(sel + ' button, ' + sel + ' select, ' + sel + ' textarea, ' + sel + ' input:not([type=checkbox])')]
    .filter(e => e.getBoundingClientRect().width && e.getBoundingClientRect().height < 43.5).map(e => e.textContent.trim().slice(0, 15))"""
RECT = "(sel) => { const r = document.querySelector(sel).getBoundingClientRect(); return {x: r.x, w: r.width, y: r.y, h: r.height}; }"

def to_paste(page, review):
    t.blur(page)
    page.click('nav button[data-tab="recipes"]')
    page.click("#paste-recipes:visible, #paste-recipes-schemes:visible")
    page.wait_for_timeout(250)
    if review:
        page.fill("#import-text", NOTES)
        page.click("text=Read notes")
        page.wait_for_timeout(400)

def to_scheme(page):
    t.blur(page)
    page.click('nav button[data-tab="recipes"]')
    page.click('[data-view="schemes"]')
    page.click("#new-scheme")
    page.wait_for_timeout(250)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for scheme in ("dark", "light"):
            ctx = browser.new_context(viewport={"width": 899, "height": 900}, service_workers="block", color_scheme=scheme)
            page = ctx.new_page()
            page.on("pageerror", lambda x: errors.append(str(x)))
            t.load(page, recipes=RECIPES, units=[])
            for width in (899, 900, 1280, 1920):
                page.set_viewport_size({"width": width, "height": 900})
                wide = width >= 900
                to_paste(page, True)
                box = page.evaluate(RECT, "#import-text")
                content = page.evaluate("() => document.querySelector('main').getBoundingClientRect().width")
                if wide:
                    check(f"{scheme} {width}: Paste recipes box is at most 780 px", box["w"] <= 780.5, box)
                else:
                    check(f"{scheme} {width}: Paste recipes box fills the page", box["w"] >= content - 60, (box, content))
                check(f"{scheme} {width}: Paste recipes no sideways scroll", t.no_sideways(page))
                check(f"{scheme} {width}: Paste recipes tap targets 44 px", not page.evaluate(SMALL, "#import-page"), page.evaluate(SMALL, "#import-page"))
                page.evaluate("() => closeImport(false)")
                to_scheme(page)
                a = page.evaluate(RECT, "#scheme-page > .card:nth-of-type(1)")
                b = page.evaluate(RECT, "#scheme-page > .card:nth-of-type(2)")
                side = abs(a["y"] - b["y"]) < 4 and b["x"] > a["x"] + a["w"] - 1
                check(f"{scheme} {width}: scheme cards {'side by side' if wide else 'stacked'}", side == wide, (a, b))
                check(f"{scheme} {width}: scheme editor no sideways scroll", t.no_sideways(page))
                check(f"{scheme} {width}: scheme editor tap targets 44 px", not page.evaluate(SMALL, "#scheme-page"), page.evaluate(SMALL, "#scheme-page"))
                page.evaluate("() => closeScheme(false)")
            ctx.close()
        # The recipe editor beside the list was checked and left alone: still inside the pane, no sideways scroll.
        ctx = browser.new_context(viewport={"width": 1920, "height": 900}, service_workers="block")
        page = ctx.new_page()
        t.load(page, recipes=RECIPES, units=[])
        t.open_editor(page)
        pane = page.evaluate(RECT, "#recipe-page")
        check("1920: recipe editor sits right of the list, inside the content width", pane["x"] > 600 and pane["x"] + pane["w"] <= 1600, pane)
        check("1920: recipe editor no sideways scroll", t.no_sideways(page))
        ctx.close()
        browser.close()
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

main()
