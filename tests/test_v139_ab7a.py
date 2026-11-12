"""AB7a tests for Minifolio (the four segment icons are hand-drawn hobby icons, AT-18).

New behaviour only:
1. Each segment has its own new icon (Dashboard a shelf, Models a figure on a base, Painting a brush, Tools clippers) and keeps its label.
   The old drawings (four-square grid, shield, drop, circled question mark) are gone. Each is an inline 24 px svg, hidden from screen readers,
   drawn in strokes only, and the button's own label is its accessible name.
2. In the start circle and in the bar the icons are shown whole inside their segment, at 390x844 and 360x640, dark and light.
3. The travelling copies carry the same four drawings."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled, _FINISH_BAR

load = t.load
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

UNITS = [{"id": 1, "name": "Squad", "hobby": "40K", "stage": 2, "count": 5, "added": "2026-10-01", "log": [["2026-10-01", 2]]}]
NAMES = {"dashboard": "Nexus", "units": "Models", "recipes": "Painting", "guides": "Tools"}
OLD = ["M12 3l8 3v6c0 4.5", "M12 3c3.5 4.2", "M9.6 9.5a2.5 2.5", 'width="7" height="9"', "M3 9h18", "M9.2 3.8Q8.4", "M20 4l-8 8"]  # MI1: the AB7a drawings are gone too

INFO = """() => Object.fromEntries([...document.querySelectorAll('.arc > [data-tab]')].map(b => {
    const s = b.querySelector('.icon svg'), r = s.getBoundingClientRect(), br = b.getBoundingClientRect(), cs = getComputedStyle(s);
    const clip = b.getBoundingClientRect();
    return [b.dataset.tab, { label: b.textContent.trim(), name: b.getAttribute('aria-label') || b.textContent.trim(), icon: s.dataset.icon, html: s.innerHTML,
        vb: s.getAttribute('viewBox'), hidden: s.getAttribute('aria-hidden'), fill: cs.fill, stroke: cs.stroke, w: r.width, h: r.height,
        inside: r.left >= br.left - 0.5 && r.right <= br.right + 0.5 && r.top >= br.top - 0.5 && r.bottom <= br.bottom + 0.5, shown: r.width > 8 && cs.visibility !== 'hidden' }];
  }))"""

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. The four icons ---")
        load(page, units=UNITS, launch=True)
        info = page.evaluate(INFO)
        check("each segment has its new icon and its label",
              all(info[s]["icon"] == s and info[s]["label"] == NAMES[s] and info[s]["name"] == NAMES[s] for s in NAMES), info)
        check("the old drawings are gone", not any(o in info[s]["html"] for s in NAMES for o in OLD), [info[s]["html"] for s in NAMES])
        check("the four drawings are different from each other", len({info[s]["html"] for s in NAMES}) == 4)
        check("each is a 24 px box drawing, hidden from screen readers, strokes only",
              all(info[s]["vb"] == "0 0 24 24" and info[s]["hidden"] == "true" and info[s]["fill"] == "none" and info[s]["stroke"] != "none" for s in NAMES), info)
        # MI1 (v156): the four drawings changed again (bars, hex base, palette, book). The AB7a shape checks that named the shelf, figure,
        # brush and clippers are replaced by the MI1 test (tests/test_v156_mi1.py); the checks above (own icon, label, 24 px, strokes only) still hold.

        print("\n--- 2. Shown whole in the circle and the bar ---")
        check("start circle: every icon is shown inside its segment", all(info[s]["shown"] and info[s]["inside"] for s in NAMES), info)
        for w, h in ((390, 844), (360, 640)):
            for mode in ("dark", "light"):
                page.set_viewport_size({"width": w, "height": h})
                load(page, units=UNITS, settings={"appearance": mode}, launch=True)
                a = page.evaluate(INFO)
                page.evaluate("() => document.querySelector('.tabs button[data-tab=units]').click()")
                page.evaluate(_FINISH_BAR)
                b = page.evaluate(INFO)
                ok = all(x[s]["shown"] and x[s]["inside"] and x[s]["icon"] == s for x in (a, b) for s in NAMES)
                check(f"{w}x{h} {mode}: icons whole in the circle and in the bar", ok, (a, b))

        print("\n--- 3. The travelling copies ---")
        page.set_viewport_size({"width": 390, "height": 844})
        load(page, units=UNITS, launch=True)
        page.evaluate("() => document.querySelector('.tabs button[data-tab=recipes]').click()")
        copies = page.evaluate("""() => { const l = document.querySelector('.mo-tr'); return l ? [...l.querySelectorAll('svg')].map(s => s.innerHTML) : null; }""")
        real = page.evaluate("() => [...document.querySelectorAll('.arc > [data-tab] .icon svg')].map(s => s.innerHTML)")
        check("the copies that travel into the bar draw the same four icons",
              copies is not None and all(r in copies for r in real), (copies, real))
        page.evaluate(_FINISH_BAR)
        wait_settled(page)

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

main()
