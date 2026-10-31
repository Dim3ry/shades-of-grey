"""v109 tests for Minifolio (chunk Mo4b: the start circle's segments travel into the menu bar).

New behaviour only:
1. Tapping a segment on the start circle draws four copies of the segments (a .tabs.mo-tr layer, inert, hidden from screen readers) that travel
   on one 1.5 s clock with a small overshoot; the real segments wait see-through; the Mentor button glides on the same clock.
2. Mid-travel the copies are real polygons (not the circle's or the bar's shape), spread outward, and the page opens at about 70%.
3. Taps on the bar and the title button are ignored while it travels.
4. At the end nothing is left over and the bar is exactly the one a page opened straight onto that section draws; each of the four segments works.
5. Reduced motion: no travel. Phone sizes, dark and light, and a wide screen."""
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
BAR = """() => { const r = e => { const b = e.getBoundingClientRect(); return [b.left, b.top, b.width, b.height].map(v => Math.round(v * 100) / 100); };
    return { orb: r(document.getElementById('mentor-button')),
             segs: [...document.querySelectorAll('.arc [data-tab]')].map(b => { const c = getComputedStyle(b); return [r(b), c.clipPath, c.backgroundColor, c.color, c.opacity, c.fontWeight, b.getAttribute('aria-current')]; }) }; }"""
TIDY = """() => document.querySelectorAll('.mo-tr, .mo-ring, .mo-ghost').length === 0 && !document.body.classList.contains('mo-travelling')
    && !document.body.classList.contains('launching') && document.querySelector('.tabs').getAnimations({ subtree: true }).length === 0"""
# tap and look in the same call, so a slow machine cannot finish the travel first
TAP = """(tab) => { document.querySelector('.tabs button[data-tab=' + tab + ']').click();
    const layer = document.querySelector('.mo-tr');
    const view = document.querySelector('main > :not(.hidden):not(.app-bar)');
    const fade = view && view.getAnimations().find(a => a.effect.getTiming().fill === 'backwards');
    return { layer: !!layer, inert: layer && layer.inert, aria: layer && layer.getAttribute('aria-hidden'), copies: document.querySelectorAll('.mo-tr .w').length,
             realHidden: [...document.querySelectorAll('.arc > [data-tab]')].every(b => getComputedStyle(b).opacity === '0' && getComputedStyle(b).pointerEvents === 'none'),
             orbMoves: document.getElementById('mentor-button').getAnimations().length === 1,
             clock: layer ? layer.getAnimations()[0].effect.getTiming() : null,
             fade: fade ? { delay: fade.effect.getTiming().delay } : null,
             scrollW: document.documentElement.scrollWidth > document.documentElement.clientWidth }; }"""
# freeze the travel at a given moment and read what is drawn
AT = """(ms) => new Promise(res => { const l = document.querySelector('.mo-tr'); l.getAnimations().forEach(a => { a.pause(); if (a.effect.getTiming().delay === 0) a.currentTime = ms; });
    requestAnimationFrame(() => requestAnimationFrame(() => res({
        progress: l.getAnimations()[0].effect.getComputedTiming().progress,
        clips: [...l.querySelectorAll('.w')].map(w => w.style.clipPath), bgs: [...l.querySelectorAll('.w')].map(w => w.style.backgroundColor),
        boxes: [...l.querySelectorAll('.w')].map(w => { const c = w.querySelector('.c').getBoundingClientRect(); return [c.left + c.width / 2, c.top + c.height / 2]; }) }))); })"""

def settle(page):
    page.evaluate(_FINISH_BAR)
    wait_settled(page)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 900}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. The travel starts ---")
        load(page, units=UNITS, launch=True)
        tok = page.evaluate("() => [getComputedStyle(document.documentElement).getPropertyValue('--motion-travel').trim(), getComputedStyle(document.documentElement).getPropertyValue('--motion-travel-ease').trim()]")
        check("tokens: --motion-travel is 1500ms and --motion-travel-ease is a cubic-bezier with y above 1", tok[0] == "1500ms" and tok[1].startswith("cubic-bezier(") and float(tok[1][:-1].split(",")[3]) > 1, tok)
        r = page.evaluate(TAP, "recipes")
        check("four copies on top, inert and hidden from screen readers", r["layer"] and r["inert"] and r["aria"] == "true" and r["copies"] == 4, r)
        check("the real segments wait: see-through and not tappable", r["realHidden"], r)
        check("the Mentor button glides on the same clock", r["orbMoves"], r)
        check("the clock is 1500 ms and the section's page waits for 70% of it (1050 ms)", r["clock"]["duration"] == 1500 and r["fade"] and abs(r["fade"]["delay"] - 1050) < 1, r)
        check("the section is already the current one", page.evaluate("() => settings.tab") == "recipes")

        print("\n--- 2. Mid-travel ---")
        start = page.evaluate(AT, 0)
        mid = page.evaluate(AT, 750)
        check("half way the copies are neither the circle's nor the bar's shape (24-point polygons)",
              all(c.startswith("polygon(") for c in mid["clips"]) and all(a != b for a, b in zip(start["clips"], mid["clips"])), mid["clips"][0][:60])
        check("the fill colours are blending (they changed from the start)", start["bgs"] != mid["bgs"])
        check("the icons and labels moved with their segments", all(abs(a[0] - b[0]) + abs(a[1] - b[1]) > 5 for a, b in zip(start["boxes"], mid["boxes"])))
        over = page.evaluate(AT, 1350)
        check("the soft bounce: the eased progress goes above 1 near the end, then settles", over["progress"] > 1.0, over["progress"])
        end = page.evaluate(AT, 1499)
        check("just before the end the progress is within 0.01 of 1", abs(end["progress"] - 1) < 0.01, end["progress"])

        print("\n--- 3. Taps are ignored while it travels ---")
        page.evaluate("() => { document.querySelector('.arc [data-tab=\"units\"]').click(); document.getElementById('home-button').click(); }")
        check("a tap on another segment and on the title do nothing", page.evaluate("() => settings.tab") == "recipes" and page.evaluate("() => !!document.querySelector('.mo-tr')"))
        settle(page)

        print("\n--- 4. The end is the bar exactly ---")
        check("nothing left over", page.evaluate(TIDY))
        load(page, units=UNITS)
        page.evaluate("() => showTab('recipes')")   # the straight-to-section reference
        ref = page.evaluate(BAR)
        load(page, units=UNITS, launch=True)
        page.evaluate(TAP, "recipes")
        settle(page)
        check("after the travel, every segment and the Mentor button match a page opened straight onto Painting", page.evaluate(BAR) == ref, (page.evaluate(BAR), ref))
        for tab in ("dashboard", "units", "guides"):
            load(page, units=UNITS, launch=True)
            page.evaluate(TAP, tab)
            settle(page)
            check(f"tapping {tab}: it opens, it is the lit one, tidy", page.evaluate("(tab) => settings.tab === tab && document.querySelector('.arc [aria-current=page]').dataset.tab === tab", tab) and page.evaluate(TIDY))
        check("the title button works again once it is over", page.evaluate("() => { document.getElementById('home-button').click(); return document.body.classList.contains('launching'); }"))
        settle(page)

        print("\n--- 5. Reduced motion ---")
        page.emulate_media(reduced_motion="reduce")
        load(page, units=UNITS, launch=True)
        r = page.evaluate(TAP, "units")
        check("no copies, no clock, no movement", not r["layer"] and r["copies"] == 0 and not r["orbMoves"] and not r["realHidden"], r)
        check("the bar is in place at once and tidy", page.evaluate(TIDY) and page.evaluate("() => settings.tab") == "units")
        page.emulate_media(reduced_motion="no-preference")

        print("\n--- 6. Phone sizes, wide screen, dark and light ---")
        for w, h, scheme in ((360, 740, "dark"), (400, 800, "light"), (320, 568, "light"), (1280, 800, "dark")):
            page.set_viewport_size({"width": w, "height": h})
            page.emulate_media(color_scheme=scheme)
            load(page, units=UNITS)
            page.evaluate("() => showTab('guides')")
            ref = page.evaluate(BAR)
            load(page, units=UNITS, launch=True)
            r = page.evaluate(TAP, "guides")
            m = page.evaluate(AT, 700) if r["layer"] else None
            settle(page)
            check(f"{w}x{h} {scheme}: travels, no sideways scroll, ends exactly on the bar",
                  (r["layer"] and r["copies"] == 4 and not r["scrollW"] and m and all(c.startswith("polygon(") for c in m["clips"])) and page.evaluate(BAR) == ref and page.evaluate(TIDY), (r, page.evaluate(BAR)["orb"], ref["orb"]))
        page.emulate_media(color_scheme="dark")
        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

main()
