"""FB1 tests for Minifolio (the version number is back at the top of every screen and opens Updates). New behaviour only:
the version text is on all four main screens, one tap opens Tools then Updates, Back returns to the screen the person was on,
the tap area is 44 px or more, nothing overlaps or scrolls sideways at 390, 360 and 320 px in dark and light, and it is hidden on the start page."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
import version_helpers as vh

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

TABS = ["dashboard", "units", "recipes", "guides"]
SETTLE = """async () => {
  const b = document.getElementById('basket-button'), key = () => ['#version-tag', '#home-button', '.app-bar'].map(q => { const x = document.querySelector(q).getBoundingClientRect(); return [x.left, x.right, x.top, x.bottom].join(); }).join('|');
  await document.fonts.ready;
  let last = '', same = 0;
  for (let i = 0; i < 120 && same < 4; i++) {   // settled = the header rects are equal for 4 frames in a row
    b.classList.remove('hidden'); b.textContent = '88';   // the app may redraw the basket (hidden when empty), so it is put back each frame
    await new Promise(r => requestAnimationFrame(r));
    const k = key(); same = k === last ? same + 1 : 0; last = k;
  }
}"""
GEOM = """() => { const r = s => document.querySelector(s).getBoundingClientRect();
  const v = r('#version-tag'), h = r('#home-button'), b = r('#basket-button'), bar = r('.app-bar');
  const a = getComputedStyle(document.getElementById('version-tag'), '::after');
  const basketShown = !document.getElementById('basket-button').classList.contains('hidden');
  return { text: document.getElementById('version-tag').textContent,
    vLeft: v.left, vRight: v.right, vTop: v.top, vBottom: v.bottom, hRight: h.right, hBottom: h.bottom, bLeft: b.left, basketShown,
    barTop: bar.top, barBottom: bar.bottom, afterW: parseFloat(a.width), afterH: parseFloat(a.height),
    sideways: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    focusOutline: (document.getElementById('version-tag').focus(), getComputedStyle(document.getElementById('version-tag')).outlineStyle) }; }"""

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        print("\n--- 1. The number on every main screen, at three phone sizes, dark and light ---")
        for (w, h) in [(390, 844), (360, 640), (320, 568)]:
            for scheme in ["dark", "light"]:
                ctx = browser.new_context(viewport={"width": w, "height": h}, service_workers="block", color_scheme=scheme)
                page = ctx.new_page()
                page.on("pageerror", lambda x: errors.append(str(x)))
                t.load(page, units=[])
                tag = f"{w}x{h} {scheme}"
                for tab in TABS:
                    page.evaluate("(x) => showTab(x)", tab)
                    page.evaluate(SETTLE)   # the basket is empty (hidden) on a fresh page; SETTLE shows it with a wide count (worst case) and waits for fonts and a steady header
                    g = page.evaluate(GEOM)
                    if tab == "dashboard":
                        check(f"{tag}: the text is the app's version", g["text"] == vh.current() and g["text"].startswith("v"), g)
                        check(f"{tag}: tap area is 44 px or more", g["afterW"] >= 44 and g["afterH"] >= 44, g)
                        check(f"{tag}: it has a visible keyboard focus", g["focusOutline"] != "none", g)
                    check(f"{tag} {tab}: shown, beside the title, clear of the basket, inside the header, no sideways scroll",
                          g["basketShown"] and g["text"] == vh.current() and g["vLeft"] >= g["hRight"] and g["vRight"] <= g["bLeft"] - 4 and g["vTop"] >= g["barTop"] and g["vBottom"] <= g["barBottom"] and not g["sideways"], g)
                ctx.close()

        print("\n--- 2. One tap opens Tools, then Updates; Back returns ---")
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.load(page, units=[])
        for tab in ["units", "recipes"]:
            page.evaluate("(x) => showTab(x)", tab)
            page.wait_for_timeout(450)
            page.click("#version-tag")
            page.wait_for_timeout(450)
            on = page.evaluate("() => ({ tab: settings.tab, updates: !document.getElementById('view-updates').classList.contains('hidden'), seg: document.querySelector('#more-seg [aria-selected=true]').dataset.page, bar: document.querySelector('nav button[aria-current=page]').dataset.tab })")
            check(f"from {tab}: one tap lands on Updates inside Tools", on["tab"] == "updates" and on["updates"] and on["seg"] == "updates" and on["bar"] == "guides", on)
            page.evaluate("() => history.back()")
            page.wait_for_timeout(600)
            back = page.evaluate("() => settings.tab")
            check(f"from {tab}: the phone's Back returns to {tab}", back == tab, back)
        page.evaluate("() => showTab('dashboard')")
        page.wait_for_timeout(400)
        page.keyboard.press("Tab")
        page.evaluate("() => document.getElementById('version-tag').focus()")
        page.keyboard.press("Enter")
        page.wait_for_timeout(450)
        check("the keyboard (Enter) opens Updates too", page.evaluate("() => settings.tab") == "updates")
        page.click('nav button[data-tab="units"]')
        page.wait_for_timeout(450)
        page.evaluate("() => history.back()")
        page.wait_for_timeout(600)
        check("after moving on by the menu, Back is as before (to the Dashboard)", page.evaluate("() => settings.tab") == "dashboard")
        ctx.close()

        print("\n--- 3. Shown on the start page (FB5) ---")
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        t.load(page, units=[], launch=True)
        # FB5 (v152): George wanted the number on the start circle too, so this old check (hidden there) is reversed; test_v152_fb5 covers the details.
        check("the start page shows it (FB5)", page.evaluate("() => getComputedStyle(document.getElementById('version-tag')).display") != "none")
        ctx.close()
        browser.close()
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)} / {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
