"""v90 tests for Minifolio (chunk U5: the Mentor orb in the round button).

New behaviour only:
1. The round Ask Mentor button holds one inline orb graphic (hidden from screen readers, four arcs, a lens), the same button in the bar
   and on the start page, with no image file and no new network request.
2. Size: 50 px in the bar, 64 px on the start page; the button keeps its size, its name and its tap area.
3. Colours: every theme, dark and light, paints the arcs and the lens from the theme's own colours (no arc invisible, lens and core differ).
4. The button still opens Ask the Mentor."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

THEMES = ["classic", "blueprint", "parchment", "forge", "bench", "rulebook"]

def start(page, w=390, h=844, launch=True):
    page.set_viewport_size({"width": w, "height": h})
    load(page, paints=[], settings={"examplesChecked": True}, launch=launch)

def size(page, sel):
    return page.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; }", sel)

PAINT_OF = """() => {
    const c = k => getComputedStyle(document.querySelector('#mentor-button .' + k));
    return { a: c('orb-a').stroke, b: c('orb-b').stroke, c: c('orb-c').stroke, dim: c('orb-dim').stroke,
             bg: c('orb-bg').fill, lens: c('orb-lens').fill, core: c('orb-core').fill };
}"""

def main():
    errors, requests = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("request", lambda r: requests.append(r.url))

        print("\n--- 1. The orb is in the button ---")
        start(page)
        orb = page.locator("#mentor-button svg")
        check("one inline graphic in the button, hidden from screen readers", orb.count() == 1 and orb.get_attribute("aria-hidden") == "true")
        check("four arcs and a lens", page.locator("#mentor-button svg .orb-a, #mentor-button svg .orb-b, #mentor-button svg .orb-c, #mentor-button svg .orb-dim").count() == 4
              and page.locator("#mentor-button svg .orb-lens").count() == 1)
        check("no image, no link to a file inside it", page.locator("#mentor-button img, #mentor-button image, #mentor-button use").count() == 0)
        check("the button keeps its name and is still the one component in the bar",
              page.get_attribute("#mentor-button", "aria-label") == "Ask Mentor" and page.locator(".tabs .arc #mentor-button").count() == 1)
        check("no picture or graphic file was fetched", not [u for u in requests if u.split("?")[0].endswith((".svg", ".png", ".jpg", ".webp"))
              and "icon" not in u and "manifest" not in u], requests)
        check("nothing was fetched from another site for it", all(u.startswith(t.BASE) or u.startswith("data:") or u.startswith("blob:") for u in requests if "goatcounter" not in u), requests)

        print("\n--- 2. Size ---")
        check("start page: button 124 px, orb 64 px", size(page, "#mentor-button") == [124, 124] and size(page, "#mentor-button svg") == [64, 64],
              (size(page, "#mentor-button"), size(page, "#mentor-button svg")))
        check("the orb has no resting scale on it", page.evaluate("() => getComputedStyle(document.querySelector('#mentor-button svg')).transform") == "none"
              and page.evaluate("() => getComputedStyle(document.querySelector('#mentor-button')).transform") == "none")
        start(page, launch=False)
        check("in the bar: button 100 px (a tap area over 44 px), orb 50 px", size(page, "#mentor-button") == [100, 100] and size(page, "#mentor-button svg") == [50, 50],
              (size(page, "#mentor-button"), size(page, "#mentor-button svg")))
        label = page.evaluate("() => { const b = document.querySelector('#mentor-button').getBoundingClientRect(), s = document.querySelector('#mentor-button svg').getBoundingClientRect();"
                              " return [s.top >= b.top, s.bottom <= b.bottom - 14]; }")
        check("the orb and the label fit inside the round button", label == [True, True], label)
        for w in (390, 360):
            start(page, w, 780, launch=False)
            check(f"{w} px wide: no sideways scroll, button still 44 px or more", no_sideways(page) and min(size(page, "#mentor-button")) >= 44)

        print("\n--- 3. Colours in every theme ---")
        start(page, launch=False)
        for theme in THEMES:
            for mode in ("dark", "light"):
                page.evaluate("([t, m]) => { const r = document.documentElement; r.dataset.t = t; r.dataset.m = m;"
                              " if (m === 'light') r.dataset.appearance = 'light'; else delete r.dataset.appearance; }", [theme, mode])
                c = page.evaluate(PAINT_OF)
                bar = page.evaluate("() => getComputedStyle(document.querySelector('#mentor-button')).backgroundColor")
                arcs = {c["a"], c["b"], c["c"], c["dim"]}
                ok = (len(arcs) == 4 and all(v not in ("none", "") for v in arcs) and c["lens"] != c["core"] and c["bg"] != bar and c["lens"] != "rgba(0, 0, 0, 0)")
                check(f"{theme} {mode}: four different arcs, lens differs from its core, disc differs from the button", ok, (c, bar))

        print("\n--- 4. It still opens Ask the Mentor ---")
        start(page)
        page.click("#mentor-button")
        page.wait_for_timeout(200)
        check("tapping the orb opens Ask the Mentor in the Compendium", page.get_attribute("#cmp-fold-mentor-button", "aria-expanded") == "true")

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
