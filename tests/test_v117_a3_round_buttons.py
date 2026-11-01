"""Chunk A3 tests for Minifolio: no square highlight on the round buttons. New behaviour only.

1. The Ask Mentor button (start page and bottom bar), the back arrow, the basket and the Mentor window's back and close buttons have
   no phone tap flash and no long-press text selection.
2. The Ask Mentor button, pressed, has a round shape and no square background, outline or hard-edged shadow.
3. Keyboard focus still shows a ring that follows the circle, with 3:1 contrast against the page colour it sits on, in all six themes, dark and light.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import quiet

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

STYLE = """(sel) => { const e = document.querySelector(sel); if (!e) return null; const s = getComputedStyle(e);
  return { tap: s.webkitTapHighlightColor, sel: s.userSelect || s.webkitUserSelect, callout: s.webkitTouchCallout,
           radius: s.borderTopLeftRadius, w: e.getBoundingClientRect().width, h: e.getBoundingClientRect().height,
           bg: s.backgroundColor, outline: s.outlineStyle + ' ' + s.outlineWidth, shadow: s.boxShadow }; }"""

# the focus ring colour against the button's own fill, as a contrast ratio (colours turned into plain rgb by a canvas)
RING = """() => { const e = document.getElementById('mentor-button'); const s = getComputedStyle(e);
  const c = document.createElement('canvas').getContext('2d', { willReadFrequently: true });
  const rgb = v => { c.clearRect(0, 0, 1, 1); c.fillStyle = '#000'; c.fillStyle = v; c.fillRect(0, 0, 1, 1); return [...c.getImageData(0, 0, 1, 1).data].slice(0, 3); };
  const lum = a => { const [r, g, b] = a.map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const a = lum(rgb(s.outlineColor)), b = lum(rgb(getComputedStyle(document.body).backgroundColor));
  return { style: s.outlineStyle, width: parseFloat(s.outlineWidth), offset: s.outlineOffset, radius: s.borderTopLeftRadius,
           ratio: (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05), focused: document.activeElement === e && e.matches(':focus-visible') }; }"""

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", has_touch=True)
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. No tap flash or text selection (start page) ---")
        t.load(page, launch=True)
        quiet(page)
        for name, sel in (("Ask Mentor", "#mentor-button"), ("basket", ".app-actions .basket"), ("title button", ".app-bar h1 .home")):
            s = page.evaluate(STYLE, sel)
            check(name + ": tap flash is clear", s and s["tap"] in ("rgba(0, 0, 0, 0)", "transparent"), s)
        check("Ask Mentor: no long-press text selection", page.evaluate(STYLE, "#mentor-button")["sel"] == "none")
        s = page.evaluate(STYLE, "#mentor-button")
        check("start page: Ask Mentor is round and 124 px", s["radius"] in ("50%", "62px") and round(s["w"]) == 124 and round(s["h"]) == 124, s)

        print("\n--- 2. Pressed Ask Mentor stays round (start page, then bottom bar) ---")
        for where in ("start page", "bottom bar"):
            if where == "bottom bar":
                page.click('.tabs button[data-tab="dashboard"]')
                page.wait_for_function("() => !document.body.classList.contains('launching')")
                page.evaluate("() => document.getAnimations().forEach(a => a.finish())")
                page.wait_for_timeout(200)
            box = page.locator("#mentor-button").bounding_box()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.down()
            s = page.evaluate(STYLE, "#mentor-button")
            page.mouse.move(2, 2)       # slide off before letting go, so the tap does not open Mentor
            page.mouse.up()
            check(where + ": pressed radius is round", s["radius"] in ("50%",) or float(s["radius"].replace("px", "")) >= s["w"] / 2 - 0.5, s)
            check(where + ": pressed has no outline", s["outline"].startswith("none") or s["outline"].split()[-1] == "0px", s)
            check(where + ": pressed fill is the accent, not a square panel", s["bg"] not in ("rgba(0, 0, 0, 0)", "transparent"), s)
            check(where + ": shadow has no hard square edge (no spread)", " 0px 0px 28px 0px" in s["shadow"] or " 0px 0px 56px 0px" in s["shadow"] or s["shadow"] == "none", s)
            check(where + ": still 44 px or more", s["w"] >= 44 and s["h"] >= 44, s)

        print("\n--- 3. Other round buttons ---")
        for name, sel in (("back arrow", "#back-menu"),):
            s = page.evaluate(STYLE, sel)
            check(name + ": tap flash clear, no selection", s and s["tap"] in ("rgba(0, 0, 0, 0)", "transparent") and s["sel"] == "none", s)
        page.evaluate("() => document.getElementById('mentor-button').click()")
        page.wait_for_selector(".mentor-close", state="visible")
        for name, sel in (("Mentor close", ".mentor-close"), ("Mentor back", ".mentor-back")):
            s = page.evaluate(STYLE, sel)
            check(name + ": tap flash clear, no selection", s and s["tap"] in ("rgba(0, 0, 0, 0)", "transparent") and s["sel"] == "none", s)
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)

        print("\n--- 4. Keyboard ring follows the circle, 3:1, six themes x dark and light ---")
        bad = []
        for theme in ("classic", "blueprint", "parchment", "forge", "bench", "rulebook"):
            for mode in ("dark", "light"):
                page.evaluate("([th, m]) => { document.documentElement.dataset.t = th; document.documentElement.dataset.m = m; }", [theme, mode])
                page.evaluate("() => document.activeElement && document.activeElement.blur()")
                page.keyboard.press("Tab")
                page.evaluate("() => document.getElementById('mentor-button').focus()")
                r = page.evaluate(RING)
                ok = r["focused"] and r["style"] == "solid" and r["width"] >= 2 and r["ratio"] >= 3 and r["radius"] in ("50%",)
                if not ok:
                    bad.append((theme, mode, r))
        check("ring is a visible solid 2 px+ line, round, 3:1 in all 12 combinations", not bad, bad)

        check("no page errors", not errors, errors)
        browser.close()
    print("\n%d/%d passed" % (sum(results), len(results)))
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
