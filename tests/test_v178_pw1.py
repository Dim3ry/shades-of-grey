"""v178 tests (chunk PW1): Your Palette opens as Swatches, and the Status buttons never split a word.
Run with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

PAINTS = t.PAINTS[:3]

def open_palette(page):
    page.click('nav button[data-tab="recipes"]')

def words_whole(page):
    # For each Status button: the label must be one line per word, so no line holds part of a word.
    return page.evaluate("""() => [...document.querySelectorAll('.status-chip')].map(b => {
        const r = b.getBoundingClientRect(); const cs = getComputedStyle(b);
        const range = document.createRange(); range.selectNodeContents(b);
        const rects = [...range.getClientRects()].filter(x => x.width > 0);
        const lines = new Set(rects.map(x => Math.round(x.top))).size;
        const words = b.textContent.trim().split(/\\s+/).length;
        return { text: b.textContent.trim(), h: r.height, w: r.width, lines, words, over: b.scrollWidth > b.clientWidth + 1, ws: cs.whiteSpace };
    })""")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        load(page, paints=PAINTS, settings={"recipeView": "palette"})
        open_palette(page)

        print("\n--- 1. Swatches first ---")
        check("a fresh open shows the swatch tiles", page.locator(".swatch-tile").count() == 3)
        check("Swatches is the pressed switch", page.locator('#palette-layout [data-layout="swatches"]').get_attribute("aria-pressed") == "true")
        page.click('#palette-layout [data-layout="list"]')
        check("List is one tap away", page.locator(".swatch-tile").count() == 0 and page.locator("#paint-list .paint-head").count() == 3)
        page.click('nav button[data-tab="shopping"]') if page.locator('nav button[data-tab="shopping"]').count() else None
        open_palette(page)
        check("leaving and returning keeps List while the app is open", page.locator(".swatch-tile").count() == 0)
        page.click('#palette-layout [data-layout="swatches"]')
        check("and back to Swatches", page.locator(".swatch-tile").count() == 3)
        page.reload()
        open_palette(page)
        check("a fresh app open shows Swatches again", page.locator(".swatch-tile").count() == 3)

        print("\n--- 2. Empty palette ---")
        load(page, paints=[], settings={"recipeView": "palette"})
        open_palette(page)
        check("an empty palette shows no tiles and no error", page.locator(".swatch-tile").count() == 0 and not errors, errors)

        print("\n--- 3. Status buttons keep every word whole ---")
        load(page, paints=PAINTS, settings={"recipeView": "palette"})
        open_palette(page)
        for look in ("classic", "forge"):
            for scheme in ("dark", "light"):
                page.emulate_media(color_scheme=scheme)
                page.evaluate("(l) => { document.documentElement.dataset.t = l; }", look)
                for width in (320, 360, 390, 450):
                    page.set_viewport_size({"width": width, "height": 800})
                    if page.locator(".swatch-detail .status-chip").count() == 0:
                        page.locator(".swatch-tile").first.click()
                    info = words_whole(page)
                    name = f"{look} {scheme} {width}"
                    good = (len(info) == 5 and all(i["lines"] <= i["words"] and not i["over"] and i["h"] >= 43.5 for i in info) and no_sideways(page))
                    check(f"{name}: five buttons, no word split, 44 px tall, no sideways scroll", good, info)
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator(".swatch-detail .status-chip").first.click()
        pressed = page.evaluate("() => [...document.querySelectorAll('.status-chip')].filter(b => b.getAttribute('aria-pressed') === 'true').length")
        check("tapping a status still sets it", pressed >= 1 or page.locator(".swatch-tile .status-marker").count() >= 1, pressed)
        check("no page errors", not errors, errors)
        browser.close()
    passed = sum(results)
    print(f"\n{passed} of {len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)

if __name__ == "__main__":
    main()
