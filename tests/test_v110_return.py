"""v110 tests for Minifolio (chunk Mo4c: the way back to the start circle is the Mo4b travel run backwards).

New behaviour only:
1. The title button from each section: four copies of the bar's segments (a .tabs.mo-tr layer, inert, hidden from screen readers) travel back
   into the circle on the same 1.5 s clock and easing, starting 350 ms later; no loading ring; the old Mo3b picture (.mo-ghost) is gone.
2. While it waits and travels the copies are real polygons; taps on the title and the real circle segments are ignored.
3. At the end nothing is left over and the circle is exactly the one a fresh load draws.
4. Reduced motion: no travel, a short fade (--motion-fast) on the bar. Phone sizes, wide screen, dark and light."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled, wait_ring_done, _FINISH_BAR

load = t.load
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

UNITS = [{"id": 1, "name": "Squad", "hobby": "40K", "stage": 2, "count": 5, "added": "2026-10-01", "log": [["2026-10-01", 2]]}]
CIRCLE = """() => { const r = e => { const b = e.getBoundingClientRect(); return [b.left, b.top, b.width, b.height].map(v => Math.round(v * 100) / 100); };
    return { orb: r(document.getElementById('mentor-button')),
             segs: [...document.querySelectorAll('.arc [data-tab]')].map(b => { const c = getComputedStyle(b); return [r(b), c.clipPath, c.backgroundColor, c.opacity, b.getAttribute('aria-current')]; }) }; }"""
TIDY = """() => document.querySelectorAll('.mo-tr, .mo-ring, .mo-ghost').length === 0 && !document.body.classList.contains('mo-travelling')
    && document.body.classList.contains('launching') && document.querySelector('.tabs').getAnimations({ subtree: true }).length === 0"""
# tap the title and look in the same call, so a slow machine cannot finish first
TAP = """() => { document.getElementById('home-button').click();
    const layer = document.querySelector('.mo-tr');
    const anims = layer ? layer.getAnimations() : [];
    return { layer: !!layer, inert: layer && layer.inert, aria: layer && layer.getAttribute('aria-hidden'), copies: document.querySelectorAll('.mo-tr .w').length,
             ring: !!document.querySelector('.mo-load, .mo-ring, .mo-ghost'),
             realHidden: [...document.querySelectorAll('.arc > [data-tab]')].every(b => getComputedStyle(b).opacity === '0' && getComputedStyle(b).pointerEvents === 'none'),
             orb: document.getElementById('mentor-button').getAnimations().map(a => a.effect.getTiming().delay),
             clock: anims.length ? anims[0].effect.getTiming() : null,
             fade: document.querySelector('.tabs').getAnimations().filter(a => !a.effect.pseudoElement).map(a => a.effect.getTiming().duration),
             scrollW: document.documentElement.scrollWidth > document.documentElement.clientWidth }; }"""
AT = """(ms) => new Promise(res => { const l = document.querySelector('.mo-tr'); l.getAnimations().forEach(a => { a.pause(); a.currentTime = ms; });
    requestAnimationFrame(() => requestAnimationFrame(() => res({
        progress: l.getAnimations()[0].effect.getComputedTiming().progress,
        clips: [...l.querySelectorAll('.w')].map(w => w.style.clipPath) }))); })"""

def settle(page):
    page.evaluate(_FINISH_BAR)
    wait_settled(page)

def fresh_circle(page):
    load(page, units=UNITS, launch=True)
    wait_ring_done(page)
    return page.evaluate(CIRCLE)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 900}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. The travel back starts ---")
        ref = fresh_circle(page)
        load(page, units=UNITS)
        for tab in ("dashboard", "units", "recipes", "guides"):
            page.evaluate("(tab) => showTab(tab)", tab)
            settle(page)
            r = page.evaluate(TAP)
            check(f"{tab}: four copies on top, inert and hidden from screen readers, the real segments wait",
                  r["layer"] and r["inert"] and r["aria"] == "true" and r["copies"] == 4 and r["realHidden"], r)
            check(f"{tab}: no loading ring and no old picture of the bar", not r["ring"], r)
            if tab == "dashboard":
                check("the clock is 1500 ms with the 350 ms wait; the Mentor button waits and glides on the same clock",
                      r["clock"]["duration"] == 1500 and r["clock"]["delay"] == 350 and r["orb"] == [350], r)
                check("same easing as the way out", r["clock"]["easing"].startswith("cubic-bezier(") and "1.25" in r["clock"]["easing"], r["clock"]["easing"])
                check("the app is already on the start page", page.evaluate("() => document.body.classList.contains('launching')"))
            settle(page)
            check(f"{tab}: ends tidy on the start page, exactly the circle a fresh load draws", page.evaluate(TIDY) and page.evaluate(CIRCLE) == ref, (page.evaluate(CIRCLE)["orb"], ref["orb"]))
            page.evaluate("(tab) => { document.querySelector('.tabs button[data-tab=' + tab + ']').click(); }", tab)
            settle(page)

        print("\n--- 2. Waiting, mid-travel and taps ---")
        page.evaluate("() => showTab('recipes')")
        settle(page)
        page.evaluate(TAP)
        wait = page.evaluate(AT, 100)
        check("while it waits the progress is 0 (the copies hold the bar's shape)", wait["progress"] == 0, wait["progress"])
        mid = page.evaluate(AT, 350 + 750)
        check("half way the copies are 24-point polygons that have changed from the start",
              all(c.startswith("polygon(") for c in mid["clips"]) and all(a != b for a, b in zip(wait["clips"], mid["clips"])), mid["clips"][0][:60])
        over = page.evaluate(AT, 350 + 1350)
        check("the soft bounce: the eased progress goes above 1 near the end", over["progress"] > 1.0, over["progress"])
        page.evaluate("() => { document.querySelector('.arc [data-tab=\"units\"]').click(); document.getElementById('home-button').click(); }")
        check("a tap on a segment and on the title do nothing while it travels", page.evaluate("() => settings.tab") == "recipes" and page.evaluate("() => !!document.querySelector('.mo-tr') && document.body.classList.contains('launching')"))
        settle(page)

        print("\n--- 3. Back to a section afterwards ---")
        page.evaluate("() => document.querySelector('.tabs button[data-tab=\"units\"]').click()")
        settle(page)
        check("a segment works again once it is over", page.evaluate("() => settings.tab === 'units' && !document.body.classList.contains('launching')"))

        print("\n--- 4. Reduced motion ---")
        page.emulate_media(reduced_motion="reduce")
        load(page, units=UNITS, launch=True)
        wait_ring_done(page)
        page.evaluate("() => document.querySelector('.tabs button[data-tab=\"units\"]').click()")
        settle(page)
        r = page.evaluate(TAP)
        check("no travel: no copies, nothing waiting, the circle is there at once", not r["layer"] and r["copies"] == 0 and not r["realHidden"] and r["orb"] == [], r)
        check("a short fade of 120 ms (--motion-fast) on the bar instead", r["fade"] == [120], r["fade"])
        settle(page)
        check("tidy, and the circle is the fresh one", page.evaluate(TIDY) and page.evaluate(CIRCLE) == ref)
        page.emulate_media(reduced_motion="no-preference")

        print("\n--- 5. Phone sizes, wide screen, dark and light ---")
        for w, h, scheme in ((360, 740, "dark"), (400, 800, "light"), (1280, 800, "dark")):
            page.set_viewport_size({"width": w, "height": h})
            page.emulate_media(color_scheme=scheme)
            ref = fresh_circle(page)
            load(page, units=UNITS)
            page.evaluate("() => showTab('guides')")
            settle(page)
            r = page.evaluate(TAP)
            settle(page)
            check(f"{w}x{h} {scheme}: travels, no sideways scroll, ends exactly on the fresh circle, tidy",
                  r["layer"] and not r["scrollW"] and page.evaluate(TIDY) and page.evaluate(CIRCLE) == ref, (r, page.evaluate(CIRCLE)["orb"], ref["orb"]))
        page.emulate_media(color_scheme="dark")

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
