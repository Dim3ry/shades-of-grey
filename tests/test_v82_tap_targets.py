"""v82 test for Minifolio (R3b follow-up: Show as a table is a 44 px tap target on phones too).

Checks: the Show as a table line on the Dashboard is 44 px or taller at 360, 390 and 899 px and at 1280 px, dark and light, with no sideways scroll.
The tab bar basket is measured by its tap area (its ::after), which was already 44 px tall."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import quiet, wait_settled

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

NO_SIDEWAYS = "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
WIDEST = """() => { const w = window.innerWidth; const wide = [...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > w + 1)
    .slice(0, 3).map(e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + '.' + String(e.className).slice(0, 30));
    return { scrollWidth: document.documentElement.scrollWidth, innerWidth: w, wide }; }"""

def no_sideways_settled(page):
    """T4: the same measure as before, but when the machine is starved the page can still be settling (a slide or fade longer than quiet() waits
    for), so it is given up to 5 s to stop overflowing. A page that really overflows still fails, and the message says what stuck out."""
    try:
        page.wait_for_function(NO_SIDEWAYS, timeout=5000)
        return True
    except Exception:
        return page.evaluate(WIDEST)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 390, "height": 900}, service_workers="block").new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        units = [{"id": i, "name": f"Unit {i}", "faction": "Gloom Legion", "stage": i % 4, "count": 5, "added": "2026-05-10", "log": []} for i in range(1, 6)]
        t.load(page, units=units)
        page.click('nav button[data-tab="dashboard"]')
        wait_settled(page)   # T4: a starved machine measured the page while the section was still sliding in
        for scheme in ("dark", "light"):
            page.emulate_media(color_scheme=scheme)
            for width in (360, 390, 899, 1280):
                page.set_viewport_size({"width": width, "height": 900})
                quiet(page)   # T4: let the resize and any colour change finish before measuring (they were measured mid-change when the machine was starved)
                h = page.evaluate("() => { const e = document.querySelector('#history-table-box > summary'); return e && e.offsetParent ? e.getBoundingClientRect().height : null; }")
                check(f"{scheme} {width}: Show as a table is 44 px or taller", h is not None and h >= 43.5, h)
                res = no_sideways_settled(page)
                check(f"{scheme} {width}: no sideways scroll", res is True, res)
        page.set_viewport_size({"width": 390, "height": 900})
        check("the basket tap area is 44 px or taller (it is hidden with an empty list, so read the style)",
              page.evaluate("() => { const b = document.getElementById('basket-button'); b.classList.remove('hidden');"
                            " const a = getComputedStyle(b, '::after'); return b.getBoundingClientRect().height + Math.abs(parseFloat(a.top)) * 2 >= 44; }"))
        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
