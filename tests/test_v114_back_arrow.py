"""Chunk B tests for Minifolio: the round back arrow beside the bottom bar. New behaviour only.

1. The arrow shows on the four sections (and on a page opened inside one), is 44 px, named "Back to menu", and has no words on screen.
2. It is hidden on the start circle, while the Mentor pop-up is open and while the segments travel; it is back when the travel ends.
3. Tapping it ends on the start circle by the same route as the Minifolio title (with the travel); the title still works; focus lands on the title button.
4. Reduced motion: tapping it goes back with no travel and no ripple; with motion on a ripple starts.
5. It stays clear of the Dashboard segment by 4 px or more at 320, 360 and 390 px (dark and light) and is still 44 px.
6. The last item on a page scrolls clear of the arrow.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import tap_tab, quiet, wait_settled, app_ready, wait_ring_done

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

SHOWN = """() => { const b = document.getElementById('back-menu'); const s = getComputedStyle(b); const r = b.getBoundingClientRect();
  return { visible: s.visibility !== 'hidden' && parseFloat(s.opacity) > 0.99 && s.display !== 'none', w: r.width, h: r.height,
           name: b.getAttribute('aria-label'), words: b.textContent.trim(), tag: b.tagName }; }"""

# the smallest gap, in px, between the arrow and the real (slanted) Dashboard segment, found by testing points on the screen
GAP = """() => { const a = document.getElementById('back-menu').getBoundingClientRect(); const w = document.querySelector('.tabs [data-tab=dashboard]');
  const d = w.getBoundingClientRect(); let min = 1e9;
  for (let x = d.left; x <= d.right; x += 0.5) for (let y = d.top; y <= d.bottom; y += 0.5) {
    const e = document.elementFromPoint(x, y);
    if (e === w || w.contains(e)) { const g = Math.hypot(Math.max(a.left - x, 0, x - a.right), Math.max(a.top - y, 0, y - a.bottom)); if (g < min) min = g; } }
  return { gap: min, w: a.width, h: a.height }; }"""

def unit(i):
    return {"id": i, "name": "Unit %d" % i, "count": 5, "stage": 1, "faction": "Orks", "hobby": "40K", "paints": [], "photos": []}

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. Shows on the four sections ---")
        t.load(page, units=[unit(i) for i in range(1, 4)])
        for tab in ("dashboard", "units", "recipes", "guides"):
            tap_tab(page, tab)
            wait_settled(page)
            s = page.evaluate(SHOWN)
            check("arrow shows on " + tab, s["visible"], s)
        check("it is a button, 44 px, named Back to menu, no words", s["tag"] == "BUTTON" and s["w"] == 44 and s["h"] == 44 and s["name"] == "Back to menu" and s["words"] == "", s)
        page.click('#more-seg button[data-page="help"]')
        wait_settled(page)
        check("still shows on a page inside Tools and Settings", page.evaluate(SHOWN)["visible"])

        print("\n--- 2. Hidden on the start circle and under Mentor ---")
        page.click("#home-button")
        wait_ring_done(page)
        check("hidden on the start circle", not page.evaluate(SHOWN)["visible"])
        tap_tab(page, "dashboard")
        wait_settled(page)
        page.click("#mentor-button")
        page.wait_for_selector(".mentor-window")
        page.wait_for_timeout(500)
        check("hidden while Mentor is open", not page.evaluate(SHOWN)["visible"])
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
        check("back after Mentor closes", page.evaluate(SHOWN)["visible"])

        print("\n--- 3. Back by the arrow (with the travel) and by the title ---")
        ctx2 = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="no-preference")
        pg = ctx2.new_page()
        pg.on("pageerror", lambda x: errors.append(str(x)))
        t.load(pg, units=[unit(1)])
        tap_tab(pg, "units")
        wait_settled(pg)
        pg.click("#back-menu")
        pg.wait_for_timeout(300)
        mid = pg.evaluate("() => ({ travelling: document.body.classList.contains('mo-travelling'), launching: document.body.classList.contains('launching') })")
        check("the travel plays after the arrow tap and the arrow is hidden meanwhile", mid["travelling"] and mid["launching"] and not pg.evaluate(SHOWN)["visible"], mid)
        pg.wait_for_function("() => !document.body.classList.contains('mo-travelling')", timeout=6000)
        wait_settled(pg)
        check("it ends on the start circle", pg.evaluate("() => document.body.classList.contains('launching')") and pg.locator('.tabs button[data-tab="units"]').is_visible())
        check("focus is on the title button", pg.evaluate("() => document.activeElement && document.activeElement.id") == "home-button")
        tap_tab(pg, "recipes")
        pg.wait_for_function("() => !document.body.classList.contains('mo-travelling')", timeout=6000)
        wait_settled(pg)
        pg.wait_for_timeout(300)   # the arrow fades in over 120 ms
        check("the arrow is back on the new section once the travel ends", pg.evaluate(SHOWN)["visible"])
        pg.click("#home-button")
        pg.wait_for_function("() => !document.body.classList.contains('mo-travelling') && document.body.classList.contains('launching')", timeout=6000)
        check("the title button still takes you to the start circle", pg.evaluate("() => document.body.classList.contains('launching')"))

        print("\n--- 4. Ripple and reduced motion ---")
        tap_tab(pg, "dashboard")
        pg.wait_for_function("() => !document.body.classList.contains('mo-travelling')", timeout=6000)
        wait_settled(pg)
        pg.dispatch_event("#back-menu", "pointerdown", {"clientX": 20, "clientY": 820, "bubbles": True})
        check("with motion on, a ripple starts", pg.locator("#back-menu .ripple").count() == 1)
        ctx2.close()
        page.click("#home-button")
        wait_ring_done(page)
        tap_tab(page, "units")
        wait_settled(page)
        page.dispatch_event("#back-menu", "pointerdown", {"clientX": 20, "clientY": 820, "bubbles": True})
        check("with reduced motion, no ripple", page.locator("#back-menu .ripple").count() == 0)
        page.click("#back-menu")
        page.wait_for_timeout(200)
        check("with reduced motion, it goes back at once with no travel",
              page.evaluate("() => document.body.classList.contains('launching') && !document.body.classList.contains('mo-travelling')"))

        print("\n--- 5. Clear of the Dashboard segment ---")
        for scheme in ("dark", "light"):
            for w, h in ((320, 568), (360, 640), (390, 844)):
                page.set_viewport_size({"width": w, "height": h})
                page.emulate_media(color_scheme=scheme)
                tap_tab(page, "units")
                wait_settled(page)
                g = page.evaluate(GAP)
                check("%s %d px: gap %.1f px (4 or more) and 44 px" % (scheme, w, g["gap"]), g["gap"] >= 4 and g["w"] == 44 and g["h"] == 44, g)
                page.click("#back-menu")
                page.wait_for_timeout(150)
                page.wait_for_function("() => document.body.classList.contains('launching')")

        print("\n--- 6. The last item scrolls clear of the arrow ---")
        for w, h in ((390, 844), (320, 568)):
            page.set_viewport_size({"width": w, "height": h})
            tap_tab(page, "dashboard")
            wait_settled(page)
            page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(150)
            r = page.evaluate("""() => { const kids = [...document.querySelectorAll('main > section:not(.hidden) > *')].filter(e => e.getBoundingClientRect().height > 0);
              const last = kids[kids.length - 1].getBoundingClientRect(); return { lastBottom: last.bottom, arrowTop: document.getElementById('back-menu').getBoundingClientRect().top }; }""")
            check("%d px: last item ends above the arrow" % w, r["lastBottom"] <= r["arrowTop"], r)
            page.click("#back-menu")
            page.wait_for_timeout(150)

        check("no page errors", not errors, errors)
        browser.close()
    print("\n%d/%d passed" % (sum(results), len(results)))
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
