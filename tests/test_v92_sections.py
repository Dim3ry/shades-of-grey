"""v92 tests for Minifolio (chunk Mo3a: moving between screens).

New behaviour only:
1. Tapping a menu segment slides the sections: later in the bar slides left (new one comes in from the right), earlier slides right.
   While it moves the old section is a see-through layer that is hidden from screen readers and cannot be tapped; afterwards nothing is left.
2. Tapping the section you are in, the Settings cog and Help / Updates do not move. A jump chosen by code and leaving the start page fade only.
3. Scroll position, keyboard focus and the phone's Back button behave as before.
4. A recipe opening on a phone: the list steps back and the detail slides in; closing reverses it. At 1280 px: a fade only.
5. Reduced motion: nothing moves at all.
6. No sideways scroll while it moves (390 and 360 px). 500 units: the switch stays quick."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load = t.load
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

RECIPE = {"id": 1, "name": "Armour", "steps": [{"title": "Step", "paints": []}]}
UNITS = [{"id": 1, "name": "Squad", "hobby": "40K", "stage": 2, "count": 5, "added": "2026-10-01", "log": [["2026-10-01", 2]]}]
BIG = [{"id": i, "name": f"Unit {i}", "hobby": "40K", "stage": i % 6, "count": 3, "added": "2026-10-01", "log": [["2026-10-01", i % 6]]} for i in range(1, 501)]

def tap(page, tab):
    page.click(f'.tabs button[data-tab="{tab}"]')

def frames(page, sel):
    """The first keyframe of each animation running on the element: its transform and opacity."""
    return page.evaluate("""(sel) => document.querySelector(sel).getAnimations().map(a => {
        const k = a.effect.getKeyframes()[0]; return { transform: k.transform, opacity: k.opacity }; })""", sel)

def tidy(page):
    """Nothing left behind: no layers, no inert / aria-hidden, no animations, no resting transform on any section."""
    return page.evaluate("""() => {
        const secs = [...document.querySelectorAll('main > section'), ...document.querySelectorAll('#recipe-home, #recipe-page')];
        return document.querySelectorAll('.mo-out, .mo-box').length === 0
            && secs.every(s => !s.inert && !s.hasAttribute('aria-hidden') && getComputedStyle(s).transform === 'none'
                && s.getAnimations().length === 0 && !s.style.top && !s.style.width); }""")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 900}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. Sliding between sections ---")
        load(page, units=UNITS, recipes=[RECIPE])
        page.wait_for_timeout(400)
        tap(page, "recipes")   # Dashboard -> Painting: later, slides left
        mid = page.evaluate("""() => { const out = document.getElementById('view-dashboard'); return {
            hidden: out.classList.contains('hidden'), inert: out.inert, aria: out.getAttribute('aria-hidden'), layer: out.classList.contains('mo-out'),
            newHidden: document.getElementById('view-recipes').classList.contains('hidden') }; }""")
        check("old section keeps its hidden class and is a layer, inert and hidden from screen readers",
              mid["hidden"] and mid["layer"] and mid["inert"] and mid["aria"] == "true" and not mid["newHidden"], mid)
        f = frames(page, "#view-recipes")
        check("moving to a later section: the new one comes in from the right", f and f[0]["transform"] == "translateX(40%)", f)
        page.wait_for_timeout(450)
        check("all tidied away at the end", tidy(page))
        tap(page, "units")   # Painting -> Models: earlier, slides right
        f = frames(page, "#view-units")
        check("moving to an earlier section: the new one comes in from the left", f and f[0]["transform"] == "translateX(-40%)", f)
        page.wait_for_timeout(450)
        check("tidy again", tidy(page))

        print("\n--- 2. What does not slide ---")
        tap(page, "units")
        check("tapping the section you are in does not move", page.evaluate("() => document.getAnimations().length") == 0)
        page.click('.cog[data-tab="settings"]')
        check("the Settings cog does not move", page.evaluate("() => document.getAnimations().length") == 0)
        page.click('#more-seg button[data-page="help"]')
        check("Help does not move", page.evaluate("() => document.getAnimations().length") == 0)
        tap(page, "dashboard")
        page.wait_for_timeout(450)
        page.evaluate("() => goToUnits({})")
        f = frames(page, "#view-units")
        check("a jump chosen by code fades only", f and f[0]["opacity"] == "0" and not f[0]["transform"], f)
        page.wait_for_timeout(200)
        check("tidy after the fade", tidy(page))
        load(page, units=UNITS, recipes=[RECIPE], launch=True)
        tap(page, "units")
        f = frames(page, "#view-units")
        check("leaving the start page fades only, no slide", f and f[0]["opacity"] == "0" and not f[0]["transform"], f)

        print("\n--- 3. Scroll, focus and Back as before ---")
        load(page, units=BIG)
        page.wait_for_timeout(300)
        tap(page, "units")
        page.wait_for_timeout(450)
        page.evaluate("() => window.scrollTo(0, 800)")
        tap(page, "recipes")
        check("scroll goes to the top, as before", page.evaluate("() => window.scrollY") == 0)
        page.wait_for_timeout(450)
        check("the tapped segment keeps keyboard focus", page.evaluate("() => document.activeElement && document.activeElement.dataset.tab") == "recipes")
        page.go_back()
        page.wait_for_timeout(500)
        check("Back goes to the Dashboard as before", page.evaluate("() => settings.tab") == "dashboard"
              and page.evaluate("() => !document.getElementById('view-dashboard').classList.contains('hidden')"))
        check("tidy after Back", tidy(page))

        print("\n--- 4. A recipe opening ---")
        load(page, units=UNITS, recipes=[RECIPE])
        tap(page, "recipes")
        page.wait_for_timeout(450)
        page.click(".recipe-item")
        mid = page.evaluate("""() => { const l = document.getElementById('recipe-home'); return { layer: l.classList.contains('mo-out'), inert: l.inert,
            aria: l.getAttribute('aria-hidden') }; }""")
        check("phone: the list stays as an inert layer while the detail slides in", mid["layer"] and mid["inert"] and mid["aria"] == "true", mid)
        f = frames(page, "#recipe-page")
        check("the detail comes in from the right", f and f[0]["transform"] == "translateX(100%)", f)
        page.wait_for_timeout(450)
        check("tidy after opening", tidy(page))
        page.go_back()
        page.wait_for_timeout(100)
        f = frames(page, "#recipe-home")
        check("Back closes it, reversed: the list steps forward", f and "translateX(-20%)" == f[0]["transform"], f)
        page.wait_for_timeout(450)
        check("the list is showing and all tidy", page.evaluate("() => settings.tab") == "recipes" and tidy(page)
              and page.evaluate("() => !document.getElementById('recipe-home').classList.contains('hidden')"))
        page.set_viewport_size({"width": 1280, "height": 900})
        page.wait_for_timeout(200)
        page.click(".recipe-item")
        check("at 1280 px: a fade only, no layer", page.evaluate("() => document.querySelectorAll('.mo-out').length") == 0
              and all(not x["transform"] for x in frames(page, "#recipe-page")) and len(frames(page, "#recipe-page")) == 1)
        page.wait_for_timeout(300)

        print("\n--- 5. Reduced motion ---")
        page.emulate_media(reduced_motion="reduce")
        page.set_viewport_size({"width": 390, "height": 900})
        tap(page, "units")
        tap(page, "compendium")
        check("sections switch with no animation and no layer", page.evaluate("() => document.getAnimations().length") == 0
              and page.evaluate("() => document.querySelectorAll('.mo-out').length") == 0)
        load(page, units=UNITS, recipes=[RECIPE])
        tap(page, "recipes")
        page.click(".recipe-item")
        check("a recipe opens with no animation", page.evaluate("() => document.getAnimations().length") == 0
              and page.evaluate("() => !document.getElementById('recipe-page').classList.contains('hidden')"))
        page.emulate_media(reduced_motion="no-preference")

        print("\n--- 6. No sideways scroll, and speed ---")
        for w in (390, 360):
            page.set_viewport_size({"width": w, "height": 800})
            load(page, units=UNITS, recipes=[RECIPE])
            tap(page, "recipes")
            page.wait_for_timeout(60)
            wide = page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
            check(f"{w} px: no sideways scroll in the middle of a slide", not wide)
            page.wait_for_timeout(400)
        load(page, units=BIG)
        page.wait_for_timeout(300)
        tap(page, "units")
        page.wait_for_timeout(450)
        ms = page.evaluate("""() => { const t0 = performance.now(); document.querySelector('.tabs button[data-tab="recipes"]').click();
            const t1 = performance.now(); document.querySelector('.tabs button[data-tab="units"]').click(); return [t1 - t0, performance.now() - t1]; }""")
        print("500 units: tap to the Painting section %.1f ms, back to Models %.1f ms (script time)" % tuple(ms))
        check("500 units: each switch's script time stays under 250 ms", max(ms) < 250, ms)
        page.wait_for_timeout(450)
        check("tidy after quick double switch", tidy(page))
        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

main()
