"""v93 tests for Minifolio (chunk Mo3b: the start circle turns into the menu bar and back).

New behaviour only:
1. Tapping a segment on the start circle: the real Mentor button glides to the bar, the segments rise, a picture of the circle (inert, hidden
   from screen readers) shrinks and fades, and the chosen segment's fill changes. At the end nothing is left over and the bar and button are
   exactly where a page opened straight onto a section draws them.
2. The title button runs the same move backwards.
3. No movement on first load, with reduced motion (both ways), or when the bar is not drawn (keyboard open).
4. Interrupted moves tidy up; scroll and focus as before; short phones, 360 px, dark and light."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled

load = t.load
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

UNITS = [{"id": 1, "name": "Squad", "hobby": "40K", "stage": 2, "count": 5, "added": "2026-10-01", "log": [["2026-10-01", 2]]}]

GEOM = """() => { const r = e => { const b = e.getBoundingClientRect(); return [b.left, b.top, b.width, b.height].map(v => Math.round(v * 100) / 100); };
    return { orb: r(document.getElementById('mentor-button')), segs: [...document.querySelectorAll('.arc [data-tab]')].map(r) }; }"""
TIDY = """() => document.querySelectorAll('.mo-ring, .mo-ghost').length === 0
    && [...document.querySelectorAll('.tabs, .arc, .arc > button')].every(e => getComputedStyle(e).transform === (e.classList.contains('arc') ? getComputedStyle(e).transform : 'none') && !e.inert)
    && document.querySelector('.tabs').getAnimations({ subtree: true }).length === 0"""
# the first keyframe of everything moving on the bar, read in the same call as the tap so a slow machine cannot finish first
TAP = """(sel) => { document.querySelector(sel).click();
    const orb = document.getElementById('mentor-button');
    const ghost = document.querySelector('.mo-ring, .mo-ghost');
    return { orb: orb.getAnimations().map(a => a.effect.getKeyframes()[0].transform),
             ghost: ghost ? { cls: ghost.className, inert: ghost.inert, aria: ghost.getAttribute('aria-hidden'), anims: ghost.getAnimations({ subtree: true }).length } : null,
             segs: [...document.querySelectorAll('.tabs:not(.mo-ghost) .arc > [data-tab]')].filter(b => b.getAnimations().length).length,
             fills: [...document.querySelectorAll('.arc [aria-current=page]')].map(b => b.getAnimations().some(a => 'backgroundColor' in a.effect.getKeyframes()[0])),
             scrollW: document.documentElement.scrollWidth > document.documentElement.clientWidth }; }"""

def settle(page):
    wait_settled(page)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 900}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 0. The finished bar, as drawn when the app opens straight onto a section ---")
        load(page, units=UNITS)
        bar_ref = page.evaluate(GEOM)
        load(page, units=UNITS, launch=True)

        print("\n--- 1. First load: nothing moves ---")
        check("start page on first load: no animation anywhere and no picture of a circle",
              page.evaluate("() => document.getAnimations().filter(a => a.effect.target && a.effect.target.closest('.tabs, .mo-ring, .mo-ghost')).length") == 0
              and page.evaluate("() => document.querySelectorAll('.mo-ring, .mo-ghost').length") == 0)
        ring_orb = page.evaluate(GEOM)["orb"]
        check("the Mentor button is 124 px across (times the circle's scale) on the circle",
              abs(ring_orb[2] - 124 * page.evaluate("() => parseFloat(document.documentElement.style.getPropertyValue('--ring-scale'))")) < 0.05, ring_orb)

        print("\n--- 2. Circle to bar ---")
        r = page.evaluate(TAP, '.tabs button[data-tab="recipes"]')
        check("the real Mentor button moves (from its circle place to none)", len(r["orb"]) == 1 and r["orb"][0].startswith("translate("), r["orb"])
        g = r["ghost"]
        check("a picture of the circle is on top, inert and hidden from screen readers, and it is animating",
              g and "mo-ring" in g["cls"] and g["inert"] and g["aria"] == "true" and g["anims"] >= 1, g)
        check("the segments rise (all four move) and the chosen one changes fill", r["segs"] == 4 and r["fills"] == [True], r)
        check("the chosen section shows already (state is new at once)", page.evaluate("() => settings.tab === 'recipes' && !document.body.classList.contains('launching')"))
        settle(page)
        check("end: nothing left, no resting transform", page.evaluate(TIDY))
        end = page.evaluate(GEOM)
        check("end: the Mentor button and the four segments are exactly where the straight-to-section page draws them",
              end["orb"] == bar_ref["orb"] and end["segs"] == bar_ref["segs"], (end["orb"], bar_ref["orb"]))
        check("end: the chosen segment is lit with a real background colour, different from the others",
              page.evaluate("""() => { const b = document.querySelector('.arc [aria-current=page]');
                  return b.dataset.tab === 'recipes' && getComputedStyle(b).backgroundColor !== getComputedStyle(document.querySelector('.arc [data-tab=units]')).backgroundColor; }"""))

        print("\n--- 3. Bar to circle (title button) ---")
        r = page.evaluate(TAP, "#home-button")
        check("the Mentor button glides back and a picture of the bar is on top (inert)",
              r["orb"] and r["orb"][0].startswith("translate(") and r["ghost"] and "mo-ghost" in r["ghost"]["cls"] and r["ghost"]["inert"] and r["ghost"]["aria"] == "true", r)
        check("the circle's segments grow in", r["segs"] == 4, r)
        settle(page)
        end = page.evaluate(GEOM)
        check("end: the start page is showing, nothing left, the button is 124 px again at its circle place",
              page.evaluate("() => document.body.classList.contains('launching')") and page.evaluate(TIDY) and end["orb"] == ring_orb, (end["orb"], ring_orb))

        print("\n--- 4. Other ways out, and interruptions ---")
        r = page.evaluate(TAP, "#mentor-button")
        check("tapping the Mentor button on the circle also moves", r["orb"] and r["ghost"] and "mo-ring" in r["ghost"]["cls"], r)
        settle(page)
        check("... and lands in the Compendium, tidy", page.evaluate("() => settings.tab") == "compendium" and page.evaluate(TIDY))
        page.evaluate("() => { document.getElementById('home-button').click(); document.querySelector('.tabs button[data-tab=\"units\"]').click(); }")
        settle(page)
        check("title then a segment straight away: one clean end state, no extra picture",
              page.evaluate("() => settings.tab") == "units" and page.evaluate(TIDY) and page.evaluate(GEOM)["orb"] == bar_ref["orb"])
        page.evaluate("() => { document.getElementById('home-button').click(); }")
        page.evaluate("() => { window.scrollTo(0, 0); document.querySelector('.cog[data-tab=\"settings\"]').click(); }")
        settle(page)
        check("the Settings cog from the circle: lands in Settings, tidy", page.evaluate("() => settings.tab") == "settings" and page.evaluate(TIDY))

        print("\n--- 5. Keyboard open: nothing to move ---")
        load(page, units=UNITS, launch=True)
        page.evaluate("() => document.body.classList.add('typing')")
        r = page.evaluate(TAP, '.tabs button[data-tab="units"]')
        check("bar hidden while typing: no move and no picture left behind", not r["orb"] and not r["ghost"], r)
        page.evaluate("() => document.body.classList.remove('typing')")
        check("tidy afterwards", page.evaluate(TIDY))

        print("\n--- 6. Reduced motion ---")
        page.emulate_media(reduced_motion="reduce")
        load(page, units=UNITS, launch=True)
        r = page.evaluate(TAP, '.tabs button[data-tab="units"]')
        check("reduced motion, circle to bar: no animation, no picture", not r["orb"] and not r["ghost"] and r["segs"] == 0, r)
        check("... and the bar is in its place at once", page.evaluate(GEOM)["orb"] == bar_ref["orb"])
        r = page.evaluate(TAP, "#home-button")
        check("reduced motion, bar to circle: no animation, no picture", not r["orb"] and not r["ghost"] and r["segs"] == 0, r)
        check("... and the circle is in place at once", page.evaluate(GEOM)["orb"] == ring_orb)
        page.emulate_media(reduced_motion="no-preference")

        print("\n--- 7. Phone sizes, dark and light ---")
        for w, h, scheme in ((360, 740, "dark"), (390, 420, "light"), (320, 568, "dark")):
            page.set_viewport_size({"width": w, "height": h})
            page.emulate_media(color_scheme=scheme)
            load(page, units=UNITS)
            ref = page.evaluate(GEOM)
            load(page, units=UNITS, launch=True)
            r = page.evaluate(TAP, '.tabs button[data-tab="dashboard"]')
            ok_mid = r["orb"] and r["ghost"] and not r["scrollW"]
            settle(page)
            check(f"{w}x{h} {scheme}: circle to bar moves, no sideways scroll, ends exactly on the bar", ok_mid and page.evaluate(GEOM) == ref and page.evaluate(TIDY), (r, page.evaluate(GEOM)["orb"], ref["orb"]))
            r = page.evaluate(TAP, "#home-button")
            settle(page)
            check(f"{w}x{h} {scheme}: bar to circle ends tidy on the start page", r["ghost"] and not r["scrollW"] and page.evaluate("() => document.body.classList.contains('launching')") and page.evaluate(TIDY))
            o = page.evaluate(GEOM)["orb"]
            check(f"{w}x{h}: the Mentor button is round and inside the screen", abs(o[2] - o[3]) < 0.01 and o[1] >= 0 and o[1] + o[3] <= h + 0.5, o)
        page.emulate_media(color_scheme="dark")

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

main()
