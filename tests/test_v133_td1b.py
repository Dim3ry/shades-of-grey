"""TD1b tests for Minifolio. New behaviour only:
1. Default appearance: a fresh install follows the phone (Match my phone), light or dark; a saved Dark, Light or Match my phone is kept.
2. Fonts: every font file in fonts/ is used by the page's @font-face rules (or is a theme-name file), the nine unused ones are gone,
   the service worker lists nothing that is missing, and Credits lists every family that is loaded and no deleted one.
3. Colour Lab scroll: on a narrow screen the next set of colours scrolls into view when it is below the screen; not when it is already
   in view, never on a wide screen; a jump (not smooth) with reduced motion; focus stays on the tapped colour.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
import test_v127_f2 as f2   # its paints, recipe and units, to give Colour Lab some own colours

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

DELETED = ["barlow-semi-condensed-latin-400-normal", "barlow-semi-condensed-latin-500-normal", "eb-garamond-latin-400-italic",
           "eb-garamond-latin-400-normal", "eb-garamond-latin-500-normal", "im-fell-english-latin-400-italic",
           "im-fell-english-latin-400-normal", "teko-latin-500-normal", "teko-latin-600-normal"]

def look(page):
    return page.evaluate("() => [document.documentElement.dataset.m, document.querySelector('[data-appearance-choice][aria-pressed=true]').dataset.appearanceChoice]")

def fresh(browser, scheme, saved=None):
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", color_scheme=scheme)
    page = ctx.new_page()
    t.load(page, settings=({"examplesChecked": True, **saved} if saved is not None else None), launch=True)
    if saved is None:
        page.evaluate("() => localStorage.clear()")
        page.reload(); t.app_ready(page)
    return ctx, page

def main():
    errors = []
    html = t.read("index.html")
    worker = t.read([f for f in os.listdir(t.ROOT) if f.startswith("sw.")][0])   # the service worker file
    with sync_playwright() as p:
        browser = p.chromium.launch()

        print("\n--- 1. Default appearance ---")
        for scheme in ("dark", "light"):
            ctx, page = fresh(browser, scheme)
            check(f"fresh install, phone set to {scheme}: Match my phone is chosen and the app is {scheme}", look(page) == [scheme, "auto"], look(page))
            ctx.close()
        for saved, scheme, want in (("dark", "light", ["dark", "dark"]), ("light", "dark", ["light", "light"]), ("auto", "light", ["light", "auto"]),
                                    ("sepia", "light", ["light", "auto"])):
            ctx, page = fresh(browser, scheme, {"appearance": saved})
            check(f"saved {saved!r}, phone {scheme}: shows {want}", look(page) == want, look(page))
            ctx.close()

        print("\n--- 2. Fonts ---")
        used = set(re.findall(r"url\(fonts/([\w-]+)\.woff2\)", html))
        on_disk = {f[:-6] for f in os.listdir(os.path.join(t.ROOT, "fonts")) if f.endswith(".woff2")}
        check("every font file in fonts/ is used by a @font-face rule, and every rule's file exists", used == on_disk, (sorted(used ^ on_disk)))
        check("the nine unused files are gone", not (set(DELETED) & on_disk))
        sw_files = re.findall(r"\"\./([^\"]+\.(?:woff2|md))\"", worker)
        check("the service worker's list names no missing font file", all(os.path.exists(os.path.join(t.ROOT, f)) for f in sw_files), sw_files)
        lic = t.read("fonts/LICENSES.md")
        check("fonts/LICENSES.md no longer mentions the deleted families", not re.search(r"Barlow Semi|IM Fell|Teko|eb-garamond-latin-", lic))
        ctx, page = fresh(browser, "dark", {})
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("requestfailed", lambda r: errors.append("failed " + r.url))
        for th in ("classic", "parchment", "forge", "bench"):
            page.evaluate("(th) => { settings.theme = th; saveSettings(); applyPalette(settings.palette); render(); }", th)
            page.evaluate("() => document.fonts.ready")
            page.wait_for_timeout(150)
        check("no font file fails to load in any look", not [e for e in errors if "woff2" in e or "failed" in e], errors)
        ctx.close()

        print("\n--- 3. Colour Lab scroll ---")
        def lab(w, h, reduced, throttle=1):
            ctx = browser.new_context(viewport={"width": w, "height": h}, service_workers="block", reduced_motion=reduced)
            page = ctx.new_page()
            page.on("pageerror", lambda x: errors.append(str(x)))
            t.load(page, paints=f2.OWN, recipes=f2.RECIPES, units=f2.UNITS, settings=f2.LAB)
            if throttle > 1:
                page.context.new_cdp_session(page).send("Emulation.setCPUThrottlingRate", {"rate": throttle})
            f2.open_lab(page, "ideas")
            page.wait_for_timeout(300)
            return ctx, page
        def tap(page, wait=1500):
            page.click("#cmp-start-swatches .start-swatch")
            page.wait_for_timeout(wait)
        ctx, page = lab(360, 640, "no-preference")
        tap(page, 100)
        mid = page.evaluate("scrollY")
        page.wait_for_timeout(1400)
        end = page.evaluate("scrollY")
        first = page.evaluate("() => document.querySelector('.idea-list > li').getBoundingClientRect().top")
        check("narrow screen, set below the screen: the page scrolls (smoothly, so not all at once) to show its start", end > 300 and mid < end and 0 <= first < 640, (mid, end, first))
        check("focus stays on the tapped colour", page.evaluate("() => document.activeElement.classList.contains('start-swatch')"))
        ctx.close()
        ctx, page = lab(360, 640, "reduce")
        tap(page, 200)
        check("reduced motion: it jumps at once", page.evaluate("scrollY") > 300, page.evaluate("scrollY"))
        ctx.close()
        ctx, page = lab(360, 640, "no-preference", throttle=4)
        tap(page, 3000)
        check("slowed phone (4 times slower CPU): it still ends with the set's start in view", page.evaluate("scrollY") > 300)
        ctx.close()
        ctx, page = lab(1280, 800, "no-preference")
        tap(page)
        check("wide screen: no scroll", page.evaluate("scrollY") == 0, page.evaluate("scrollY"))
        ctx.close()
        ctx, page = lab(390, 2400, "no-preference")
        tap(page)
        check("set already in view: no scroll", page.evaluate("scrollY") == 0, page.evaluate("scrollY"))
        ctx.close()
        browser.close()
    check("no page errors", not [e for e in errors if not e.startswith("failed") and "woff2" not in e], errors)
    bad = results.count(False)
    print(f"\n{len(results) - bad} passed, {bad} failed")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
