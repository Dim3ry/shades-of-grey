"""v77 tests for Minifolio (chunk R1: the wide-screen layout foundation).

What changed:
 One shared 900 px breakpoint (written down in index.html and as WIDE_MIN_PX in app.js), a reusable two-column class
 (layout-split with layout-main and layout-side), a widest-content value, and a developer page (both-views.html) that
 shows the app at phone and desktop width. The Updates page is the pilot for the new class.

Checks:
1. The breakpoint is written the same everywhere it appears.
2. Updates at 899 px and 390 px / 360 px: stacked, feedback first, no sideways scroll. At 900 px and wider: side by
   side, What's new on the left and wider, feedback on the right. Dark and light.
3. Content never gets wider than 1280 px on a very wide screen. A hidden layout-split page stays hidden.
4. both-views.html: frames the app twice (390 px and 1280 px), the page selector opens the chosen page in both, both show
   the same saved data, and nothing in the app links to it.
5. No page errors, no browser pop-ups, no blocked-by-policy messages.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright
from launch_helpers import open_settings, wait_settled

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways, read, BASE = t.load, t.no_sideways, t.read, t.BASE
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

UNIT = {"id": 1, "name": "Frame probe squad", "hobby": "40K", "faction": "Orks", "stage": 2, "count": 5,
        "added": "2026-10-01", "log": [["2026-10-01", 2]]}

def boxes(page):
    return page.evaluate("""() => { const r = s => document.querySelector(s).getBoundingClientRect();
        const side = r('#view-updates > .layout-side'), main = r('#view-updates > .layout-main');
        return { sideX: side.left, sideW: side.width, sideTop: side.top, mainX: main.left, mainW: main.width, mainTop: main.top,
                 firstIsSide: document.querySelector('#view-updates').firstElementChild.classList.contains('layout-side'),
                 mainEl: r('main').width }; }""")

def main():
    errors, dialogs, console = [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        page.on("console", lambda m: console.append(m.text) if m.type == "error" else None)

        print("\n--- 1. One breakpoint ---")
        html, js = read("index.html"), read("app.js")
        nums = set(re.findall(r"\((?:min-width: 900px|max-width: 899\.98px)\)", html))
        wrong = re.findall(r"\(min-width: (?!900px|700px|640px)\d+px\)", html)
        check("index.html writes the wide breakpoint only as 900 px / 899.98 px", nums == {"(min-width: 900px)", "(max-width: 899.98px)"} and not wrong, (nums, wrong))
        check("app.js has WIDE_MIN_PX = 900 and uses it", "const WIDE_MIN_PX = 900;" in js and "WIDE_MIN_PX + \"px)\"" in js)
        check("index.html documents it once, with layout-split", html.count("THE WIDE-SCREEN BREAKPOINT") == 1 and ".layout-split" in html)

        print("\n--- 2. Updates pilot: below and above 900 px ---")
        load(page, units=[])
        for scheme in ("dark", "light"):
            page.emulate_media(color_scheme=scheme)
            for width in (360, 390, 899):
                page.set_viewport_size({"width": width, "height": 900})
                open_settings(page); page.click("[data-page='updates']")
                b = boxes(page)
                check(f"{scheme} {width}: stacked, feedback first, same left edge", b["firstIsSide"] and b["sideTop"] < b["mainTop"] and abs(b["sideX"] - b["mainX"]) < 1, b)
                check(f"{scheme} {width}: no sideways scroll", no_sideways(page))
            for width in (900, 1280):
                page.set_viewport_size({"width": width, "height": 900})
                b = boxes(page)
                check(f"{scheme} {width}: side by side, main left and wider", b["mainX"] < b["sideX"] and b["mainW"] > b["sideW"] * 1.5 and abs(b["mainTop"] - b["sideTop"]) < 2, b)
                check(f"{scheme} {width}: no sideways scroll", no_sideways(page))

        print("\n--- 3. Widest content, hidden page ---")
        page.set_viewport_size({"width": 1920, "height": 900})
        check("content is at most 1280 px wide on a 1920 px screen", boxes(page)["mainEl"] <= 1280.5, boxes(page)["mainEl"])
        page.click("[data-tab='dashboard']")
        wait_settled(page)   # X2: Updates is in the fourth section now, so leaving it slides and the old page is a layer until the move ends
        check("Updates stays hidden when another page is open", page.evaluate("() => getComputedStyle(document.getElementById('view-updates')).display") == "none")

        print("\n--- 4. both-views.html ---")
        check("nothing in the app links to both-views", not any("both-views" in read(f) for f in ("index.html", "app.js", "early.js")))
        load(page, units=[UNIT])
        page.set_viewport_size({"width": 1500, "height": 900})
        page.goto(BASE + "both-views.html")
        page.wait_for_function("() => [...document.querySelectorAll('iframe')].every(f => f.contentDocument && f.contentDocument.getElementById('version-tag') && f.contentDocument.getElementById('version-tag').textContent)")
        w = page.evaluate("() => [...document.querySelectorAll('iframe')].map(f => f.contentWindow.innerWidth)")
        check("frames are 390 px and 1280 px wide", w == [390, 1280], w)
        box = page.evaluate("() => { const r = document.getElementById('desktop-box').getBoundingClientRect(); return [r.right, r.width]; }")
        check("desktop frame is scaled to fit the window", box[0] <= 1500 and box[1] < 1280, box)
        page.select_option("#page", "updates")
        page.wait_for_timeout(300)
        shown = page.evaluate("() => [...document.querySelectorAll('iframe')].map(f => !f.contentDocument.getElementById('view-updates').classList.contains('hidden'))")
        check("the selector opens Updates in both frames", shown == [True, True], shown)
        sides = page.evaluate("() => [...document.querySelectorAll('iframe')].map(f => { const d = f.contentDocument; return d.querySelector('#view-updates > .layout-main').getBoundingClientRect().left < d.querySelector('#view-updates > .layout-side').getBoundingClientRect().left; })")
        check("the narrow frame is stacked and the wide frame is side by side", sides == [False, True], sides)
        page.select_option("#page", "units")
        page.wait_for_timeout(300)
        names = page.evaluate("() => [...document.querySelectorAll('iframe')].map(f => f.contentDocument.getElementById('view-units').innerText.includes('Frame probe squad'))")
        check("both frames show the same saved data", names == [True, True], names)
        check("the selector opens Units in both frames", page.evaluate("() => [...document.querySelectorAll('iframe')].every(f => !f.contentDocument.getElementById('view-units').classList.contains('hidden'))"))

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        check("no policy-blocked messages", not [c for c in console if "Content Security Policy" in c or "frame" in c.lower()], console)
        browser.close()
    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
