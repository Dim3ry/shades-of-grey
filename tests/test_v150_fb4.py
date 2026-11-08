"""FB4 tests for Minifolio (paint brands as tiles). New behaviour only:
1. Every brand is a tile in a wrapping grid: no sliding row, no inner scroll, no sideways scroll at 390, 360 and 320 px.
2. A tile is 44 px or more each way, shows "on" with a tick as well as colour, and a long name wraps inside it.
3. Tapping switches the brand exactly as the old strip did (same saved value, same paints searched); a saved choice shows after a reload.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import open_settings, wait_settled

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def open_brands(page, settings=None, w=390, h=844, theme=None):
    page.set_viewport_size({"width": w, "height": h})
    s = {"examplesChecked": True}
    s.update(settings or {})
    t.load(page, settings=s)
    open_settings(page)
    b = page.locator("#card-fold-paint-brands-button")
    if b.get_attribute("aria-expanded") != "true":
        b.click()
    page.wait_for_selector("#brand-toggles .chip")
    wait_settled(page)

GEOM = """() => { const box = document.getElementById('brand-toggles'); const tiles = [...box.querySelectorAll('.chip')];
    const r = tiles.map(c => c.getBoundingClientRect()); const cs = getComputedStyle(box);
    return { n: tiles.length, brands: PAINT_BRANDS.length, rows: new Set(r.map(x => Math.round(x.top))).size,
             minH: Math.min(...r.map(x => x.height)), minW: Math.min(...r.map(x => x.width)),
             scrolls: box.scrollWidth > box.clientWidth + 1, overflowX: cs.overflowX, wrap: cs.flexWrap,
             sideways: document.documentElement.scrollWidth > innerWidth,
             outside: r.filter(x => x.right > innerWidth + 0.5 || x.left < -0.5).length,
             sameFamily: box.classList.contains('chips-wrap') && document.getElementById('part-chips').classList.contains('chips-wrap'),
             cut: tiles.filter(c => c.scrollWidth > c.clientWidth + 1).length }; }"""

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. A wrapping grid at three widths ---")
        for w, h in ((390, 844), (360, 640), (320, 568)):
            open_brands(page, w=w, h=h)
            g = page.evaluate(GEOM)
            check(f"{w}px: one tile per brand, wrapped over several rows", g["n"] == g["brands"] and g["rows"] > 1, g)
            check(f"{w}px: no sliding row, no inner scroll, no sideways scroll", g["wrap"] == "wrap" and g["overflowX"] == "visible"
                  and not g["scrolls"] and not g["sideways"] and g["outside"] == 0, g)
            check(f"{w}px: tiles are 44 px or more and nothing is cut off", g["minH"] >= 44 and g["minW"] >= 44 and g["cut"] == 0, g)
        check("the tiles share Recipe preferences' wrapping style", g["sameFamily"], g)

        print("\n--- 2. State and long names ---")
        open_brands(page, settings={"brandsOff": ["Vallejo"]})
        st = page.evaluate("""() => { const on = document.querySelector('[data-brand-choice="Tamiya"]'), off = document.querySelector('[data-brand-choice="Vallejo"]');
            const tick = (e) => getComputedStyle(e, '::before').opacity + '|' + getComputedStyle(e, '::before').content;
            return { on: on.getAttribute('aria-pressed'), off: off.getAttribute('aria-pressed'), tOn: tick(on), tOff: tick(off) }; }""")
        check("an on tile has a tick and an off tile has none, besides the colour", st["on"] == "true" and st["off"] == "false"
              and st["tOn"].startswith("1|") and st["tOff"].startswith("0|"), st)
        page.evaluate("""() => { const c = document.querySelector('[data-brand-choice="Tamiya"]');
            c.textContent = 'A very long paint brand name that goes on and on <b>not html</b>'; }""")
        lg = page.evaluate("""() => { const c = document.querySelector('[data-brand-choice="Tamiya"]'); const r = c.getBoundingClientRect();
            return { lines: Math.round(r.height / 20), cut: c.scrollWidth > c.clientWidth + 1, inside: r.right <= innerWidth, bold: !!c.querySelector('b'), sideways: document.documentElement.scrollWidth > innerWidth }; }""")
        check("a long name wraps inside its tile with nothing cut off, and tags stay plain text", lg["lines"] >= 2 and not lg["cut"] and lg["inside"]
              and not lg["bold"] and not lg["sideways"], lg)

        print("\n--- 3. Tapping and keeping the choice ---")
        open_brands(page)
        page.click('[data-brand-choice="Formula P3"]')
        s1 = page.evaluate("""() => ({ pressed: document.querySelector('[data-brand-choice="Formula P3"]').getAttribute('aria-pressed'),
            saved: JSON.parse(localStorage.getItem('shades-of-grey-settings')).brandsOff, p3: searchedPaints.some(k => k.brand === 'Formula P3') })""")
        check("tapping a tile switches it off: same saved value as before, its paints no longer searched",
              s1["pressed"] == "false" and s1["saved"] == ["Formula P3"] and not s1["p3"], s1)
        page.keyboard.press("Tab")
        page.reload(); page.wait_for_function("() => typeof settings === 'object'")
        open_settings(page)
        page.locator("#card-fold-paint-brands-button").click()
        page.wait_for_selector("#brand-toggles .chip")
        check("the choice shows on its tile after a reload", page.get_attribute('[data-brand-choice="Formula P3"]', "aria-pressed") == "false"
              and page.get_attribute('[data-brand-choice="Tamiya"]', "aria-pressed") == "true")
        page.click('[data-brand-choice="Formula P3"]')
        check("tapping again switches it back on and clears the saved choice", page.evaluate("JSON.parse(localStorage.getItem('shades-of-grey-settings')).brandsOff") == [])

        print("\n--- 4. Looks, light and dark ---")
        for look, mode in (("classic", "dark"), ("classic", "light"), ("forge", "dark"), ("bench", "light")):
            open_brands(page, settings={"theme": look, "appearance": mode, "brandsOff": ["Vallejo", "Tamiya"]}, w=360, h=640)
            g = page.evaluate(GEOM)
            check(f"{look} {mode}: tiles wrap, no sideways scroll, 44 px or more", g["rows"] > 1 and not g["sideways"] and not g["scrolls"] and g["minH"] >= 44, g)

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
