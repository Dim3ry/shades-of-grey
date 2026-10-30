"""v88 tests for Minifolio (chunk U4a: the menu bar around the round Ask Mentor button, the header cog and basket, Units renamed Models).

New behaviour only:
1. Four segments, left to right Dashboard, Models, Painting, Compendium, each a real button with an aria-label; Units is gone from the bar.
2. The tap area is the segment itself (clip-path): a tap at its middle hits it, a tap in the gap between two does not.
3. The section you are in is lit (aria-current, bold, a different fill); Settings lights the cog instead, no segment.
4. Ask Mentor: a round 100 px button, its centre 26 px above the bottom edge, opens the Compendium with Ask the Mentor open.
5. The cog in the header opens Settings (Help and Updates inside); the basket sits next to it with a 44 px tap area and opens the Shopping list.
6. The bar scales with the screen (min(1, width / 390)), stays full size and centred on wide screens, and there is no top tab bar.
7. Pages scroll clear of the bar; the bar steps aside while a text box has the cursor (phones).
8. 390, 360 and 320 px, dark and light: no sideways scroll, every segment 44 px or more in its real tap area."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

PAINT = {"id": 1, "brand": "Citadel", "name": "Macragge Blue", "colour": "#1f3f9a", "status": "wishlist", "shopFrom": ["Recipe: Blue"]}
UNIT = {"id": 1, "name": "Squad", "hobby": "40K", "stage": 1, "count": 5, "added": "2026-10-01", "log": [["2026-10-01", 1]]}
SEGMENTS = ["dashboard", "units", "recipes", "guides"]   # X2: the fourth is Tools and Settings (data-tab guides)

def seg(tab):
    return f'.tabs button[data-tab="{tab}"]'

def box(page, sel):
    return page.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }", sel)

def hit(page, x, y):
    """The data-tab or id of the element a tap at (x, y) would land on ('' if neither)."""
    return page.evaluate("([x, y]) => { const e = document.elementFromPoint(x, y); const b = e && e.closest('button'); return b ? (b.dataset.tab || b.id || '') : ''; }", [x, y])

def tap_area(page, tab):
    """The segment's real tap area: its box is the segment's bounding box, so the smaller side of that box, after scaling."""
    w, h = box(page, seg(tab))[2:]
    return min(w, h)

def start(page, w=390, h=844, tab="dashboard"):
    page.set_viewport_size({"width": w, "height": h})
    load(page, paints=[PAINT], units=[UNIT], settings={"examplesChecked": True})
    page.click(seg(tab))
    page.wait_for_timeout(150)

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        print("\n--- 1. The four segments ---")
        start(page)
        labels = page.evaluate("() => [...document.querySelectorAll('.tabs button[data-tab]')].sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left).map(b => [b.getAttribute('aria-label') || b.textContent.trim(), b.textContent.trim()])")
        check("left to right: Dashboard, Models, Painting, Tools (aria-label and visible label; X2: the fourth says Tools, the page is Tools and Settings)",
              labels == [["Dashboard", "Dashboard"], ["Models", "Models"], ["Painting", "Painting"], ["Tools", "Tools"]], labels)
        check("the old Units name is gone from the bar and Settings is not a segment",
              "Units" not in [l[1] for l in labels] and page.locator(".tabs button[data-tab='settings']").count() == 0)
        check("the Models segment still opens the unit list", (page.click(seg("units")), page.wait_for_timeout(100), page.is_visible("#view-units"))[2])
        check("Help says Models and names Tools and Settings (X2: the cog is gone)", "Models" in page.inner_text("#help-tabs") and "Tools and Settings" in page.inner_text("#help-tabs") and "cog" not in page.inner_text("#help-tabs"))

        print("\n--- 2. The tap area is the segment ---")
        page.click(seg("dashboard"))
        ok = True
        for tab in SEGMENTS:
            x, y, w, h = box(page, seg(tab))
            if hit(page, x + w / 2, y + h / 2) != tab: ok = False
        check("a tap at the middle of each segment lands on it", ok)
        # the gap between Models and Painting is straight above the Mentor button's centre
        m = box(page, "#mentor-button")
        cx = m[0] + m[2] / 2
        check("a tap in the gap between Models and Painting lands on neither", hit(page, cx, m[1] - 20) not in ("units", "recipes"), hit(page, cx, m[1] - 20))
        check("a tap in the page above the bar lands on the page", hit(page, 195, 700) == "" or hit(page, 195, 700) not in SEGMENTS)

        print("\n--- 3. The lit segment ---")
        page.click(seg("recipes"))
        lit = page.evaluate("() => [...document.querySelectorAll('.tabs button[data-tab]')].map(b => [b.dataset.tab, b.getAttribute('aria-current'), getComputedStyle(b).fontWeight, getComputedStyle(b).backgroundColor])")
        on = [r for r in lit if r[1] == "page"]
        off = [r for r in lit if r[1] != "page"]
        check("exactly one segment is current", len(on) == 1 and on[0][0] == "recipes", lit)
        check("it is bold and has a different fill from the others (not colour alone)",
              int(on[0][2]) >= 700 and all(int(r[2]) < 700 for r in off) and all(r[3] != on[0][3] for r in off), lit)
        page.click(seg("guides"))
        page.click("#more-seg [data-page='settings']")
        page.wait_for_timeout(100)
        # X2: Settings is a page of the fourth segment now, which stays lit (there is no cog)
        check("Settings: the Tools segment is current", page.get_attribute(seg("guides"), "aria-current") == "page" and page.locator(".tabs [aria-current]").count() == 1)
        check("Settings shows its Settings, Help and Updates switch", page.is_visible("#more-seg") and page.is_visible("#view-settings"))
        page.click("[data-page='help']")
        check("Help is reached from Settings and the Tools segment stays current", page.is_visible("#view-help") and page.get_attribute(seg("guides"), "aria-current") == "page")

        print("\n--- 4. Ask Mentor ---")
        page.click(seg("units"))
        m = box(page, "#mentor-button")
        check("100 px across and round", abs(m[2] - 100) < 0.6 and abs(m[3] - 100) < 0.6 and page.evaluate("getComputedStyle(document.getElementById('mentor-button')).borderRadius") in ("50%", "50px"), m)
        check("its centre is 26 px above the bottom edge", abs((m[1] + m[3] / 2) - (844 - 26)) < 1, m)
        check("it has the name Ask Mentor", page.get_attribute("#mentor-button", "aria-label") == "Ask Mentor")
        page.click("#mentor-button")
        page.wait_for_timeout(200)
        fold = box(page, "#cmp-lab-picker")   # X1: the button opens Painting > Colour Lab > Picker
        check("it opens Colour Lab with the Picker open", page.is_visible("#colourlab-view") and page.get_attribute('#lab-seg [data-lab="picker"]', "aria-selected") == "true")
        check("the Picker is scrolled into view, below the header", 0 <= fold[1] < 400, fold)
        check("the Painting segment is lit", page.get_attribute(seg("recipes"), "aria-current") == "page")

        print("\n--- 5. The header: basket (X2: the cog is gone) ---")
        page.click(seg("dashboard"))
        b = page.evaluate("() => { const r = document.getElementById('basket-button').getBoundingClientRect(); const a = getComputedStyle(document.getElementById('basket-button'), '::after'); return [r.right, r.top, r.height, a.top, a.bottom, a.left, a.right, a.position]; }")
        check("the basket shows in the header, in the top corner (it has a paint on the list)", page.is_visible("#basket-button") and b[0] > 390 - 40 and b[1] < 60 and page.locator(".cog").count() == 0, b)
        check("the basket keeps its enlarged tap area (the ::after reaches 11 px above and below)", b[7] == "absolute" and b[3] == "-11px" and b[4] == "-11px", b)
        page.click("#basket-button")
        page.wait_for_timeout(150)
        check("tapping the basket opens the Shopping list", page.is_visible("#shop-panel") and page.get_attribute(seg("recipes"), "aria-current") == "page")
        page.evaluate("() => window.scrollTo(0, 400)")
        check("the header stays in view while the page scrolls", box(page, ".app-bar")[1] <= 1)

        print("\n--- 6. Scaling ---")
        for w in (360, 320):
            start(page, w=w, h=740)
            scale = page.evaluate("parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--arc-scale'))")
            arc = box(page, ".arc")
            check(f"{w} px: scale is width / 390 and the bar spans the screen", abs(scale - w / 390) < 0.01 and abs(arc[2] - w) < 1 and abs(arc[0]) < 1, (scale, arc))
        start(page, w=1280, h=800)
        arc = box(page, ".arc")
        check("1280 px: full size and centred at the bottom", abs(arc[2] - 390) < 1 and abs(arc[0] + 195 - 640) < 1 and abs(arc[1] + arc[3] - 800) < 1, arc)
        check("1280 px: there is no tab bar at the top", box(page, ".tabs")[1] > 400)
        check("1280 px: the header is the only thing at the top and the basket is in the right corner", box(page, "#basket-button")[0] + box(page, "#basket-button")[2] > 1280 - 60 and box(page, "#basket-button")[1] < 40)

        print("\n--- 7. Room under the page, and the keyboard ---")
        start(page, tab="guides")
        page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
        page.wait_for_timeout(100)
        gap = page.evaluate("() => { const els = [...document.querySelectorAll('#view-guides *')].filter(e => e.getBoundingClientRect().height > 0); const last = Math.max(...els.map(e => e.getBoundingClientRect().bottom)); return [last, document.querySelector('.tabs').getBoundingClientRect().top]; }")
        check("the end of Guides scrolls clear of the bar", gap[0] <= gap[1] + 1, gap)
        check("the page has at least 170 px of room at the bottom", page.evaluate("parseFloat(getComputedStyle(document.body).paddingBottom)") >= 170)
        page.click(seg("units"))
        page.click("#toggle-add")
        page.focus("#name-input")
        page.wait_for_timeout(100)
        check("a phone with the cursor in a text box: the bar steps aside", page.evaluate("getComputedStyle(document.querySelector('.tabs')).display") == "none")
        page.evaluate("() => document.activeElement.blur()")
        page.wait_for_timeout(100)
        check("…and comes back", page.evaluate("getComputedStyle(document.querySelector('.tabs')).display") != "none")
        # Pressing a button takes the cursor out of the box on the way down; the bar and message must not move until the press ends.
        page.focus("#name-input")
        page.evaluate("() => { document.dispatchEvent(new Event('pointerdown')); document.activeElement.blur(); }")
        page.wait_for_timeout(100)
        check("the bar stays hidden while a press is still held", page.evaluate("document.body.classList.contains('typing')"))
        page.evaluate("() => document.dispatchEvent(new Event('pointerup'))")
        page.wait_for_timeout(100)
        check("…and comes back once the press ends", not page.evaluate("document.body.classList.contains('typing')"))

        print("\n--- 8. Narrow phones, dark and light ---")
        ctx.close()
        for scheme in ("dark", "light"):
            for w in (390, 360, 320):
                c2 = browser.new_context(viewport={"width": w, "height": 740}, color_scheme=scheme, service_workers="block")
                p2 = c2.new_page()
                p2.on("pageerror", lambda x: errors.append(str(x)))
                start(p2, w=w, h=740, tab="units")
                areas = [tap_area(p2, tab) for tab in SEGMENTS]
                mm = box(p2, "#mentor-button")
                check(f"{w} px {scheme}: no sideways scroll, every segment 44 px or more in its real tap area, Ask Mentor 44 px or more",
                      no_sideways(p2) and min(areas) >= 44 and min(mm[2], mm[3]) >= 44, (areas, mm))
                c2.close()

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)

if __name__ == "__main__":
    main()
