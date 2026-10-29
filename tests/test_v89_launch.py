"""v89 tests for Minifolio (chunk U4b: the launch page, a circular menu).

New behaviour only:
1. A fresh load shows the launch page: four quarter segments (Dashboard, Models, Painting, Compendium) around the round Ask Mentor
   button, no section open, nothing lit, no sentences. The header keeps the title (a button), the basket and the cog.
2. The circle: centred under the header, 124 px Mentor button, 340 px across at 390 px, each segment is its own tap area, a tap in a gap hits nothing.
3. A segment opens its section lit; Ask Mentor opens Ask the Mentor; the title goes back to the launch page, and the section you were in is untouched.
4. Switching away and back (visibilitychange, blur, focus) never changes the screen, typed text or scroll position; only a reload shows the circle.
5. A link that names a section (#units) opens it. Back on the launch page has nothing to close.
6. 390, 360 and 320 px, dark and light, and short screens: the circle fits, no sideways scroll, tap areas 44 px or more, no motion."""
import os, sys
from playwright.sync_api import sync_playwright
from launch_helpers import wait_settled

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

PAINT = {"id": 1, "brand": "Citadel", "name": "Macragge Blue", "colour": "#1f3f9a", "status": "wishlist", "shopFrom": ["Recipe: Blue"]}
UNIT = {"id": 1, "name": "Squad", "hobby": "40K", "stage": 1, "count": 5, "added": "2026-10-01", "log": [["2026-10-01", 1]]}
SEGMENTS = ["dashboard", "units", "recipes", "compendium"]
NAMES = {"dashboard": "Dashboard", "units": "Models", "recipes": "Painting", "compendium": "Compendium"}

def seg(tab):
    return f'.tabs button[data-tab="{tab}"]'

def box(page, sel):
    return page.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }", sel)

def hit(page, x, y):
    return page.evaluate("([x, y]) => { const e = document.elementFromPoint(x, y); const b = e && e.closest('button'); return b ? (b.dataset.tab || b.id || '') : ''; }", [x, y])

def launching(page):
    return page.evaluate("() => document.body.classList.contains('launching')")

def shown_sections(page):
    return page.evaluate("() => [...document.querySelectorAll('main > section')].filter(s => s.offsetParent !== null).map(s => s.id)")

def start(page, w=390, h=844, settings=None, units=True):
    page.set_viewport_size({"width": w, "height": h})
    load(page, paints=[PAINT], units=[UNIT] if units else None, settings=dict({"examplesChecked": True}, **(settings or {})), launch=True)

def circle(page):
    """The circle's centre and size as drawn: the Mentor button's centre, and the four segments' boxes."""
    o = box(page, "#mentor-button")
    return o[0] + o[2] / 2, o[1] + o[3] / 2, o

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        print("\n--- 1. The launch page ---")
        start(page, settings={"tab": "recipes"})
        check("a fresh load shows the launch page, even when Painting was the last section", launching(page) and shown_sections(page) == [], shown_sections(page))
        names = [page.get_attribute(seg(s), "aria-label") or page.inner_text(seg(s)).strip() for s in SEGMENTS]
        check("four segments, in order, each a real button with its name", names == [NAMES[s] for s in SEGMENTS], names)
        check("nothing is lit (no aria-current anywhere)", page.locator("[aria-current]").count() == 0)
        words = [w.strip() for w in page.inner_text(".tabs").split("\n") if w.strip()]
        check("no sentences: only the four names and Ask Mentor", sorted(words) == sorted(list(NAMES.values()) + ["Ask Mentor"]), words)
        check("header: the title is a real button with an aria-label, next to the basket and the cog",
              page.locator("button#home-button[aria-label]").count() == 1 and page.is_visible("#basket-button") and page.is_visible('.cog[data-tab="settings"]'))
        check("the round Mentor button is the same one component as in the bar", page.locator("#mentor-button").count() == 1 and page.locator(".tabs .arc #mentor-button").count() == 1)

        print("\n--- 2. The circle ---")
        cx, cy, o = circle(page)
        head = page.evaluate("() => document.querySelector('.app-bar').getBoundingClientRect().bottom")
        check("the Mentor button is 124 px across", abs(o[2] - 124) < 1 and abs(o[3] - 124) < 1, o)
        check("centred across the screen and in the space under the header (about 450 px down at 844 px tall)",
              abs(cx - 195) < 1 and abs(cy - (head + (844 - head) / 2)) < 2 and 440 <= cy <= 460, (cx, cy, head))
        r = lambda d: d  # readability
        check("the ring is 340 px across: a tap 165 px out hits a segment, 175 px out hits nothing",
              hit(page, cx - 118, cy - 118) == "dashboard" and hit(page, cx - 128, cy - 128) == "" and hit(page, cx + 118, cy + 118) == "compendium")
        check("a tap on the round button (56 px from its centre) hits Ask Mentor, not a segment", hit(page, cx - 40, cy - 40) == "mentor-button")
        check("segments sit top left, top right, bottom left, bottom right",
              hit(page, cx - 90, cy - 90) == "dashboard" and hit(page, cx + 90, cy - 90) == "units" and hit(page, cx - 90, cy + 90) == "recipes" and hit(page, cx + 90, cy + 90) == "compendium")
        check("a tap in the gap on the vertical or the horizontal axis hits nothing",
              hit(page, cx, cy - 120) == "" and hit(page, cx - 120, cy) == "" and hit(page, cx + 120, cy) == "" and hit(page, cx, cy + 120) == "")
        check("the glow behind the circle uses a theme colour (a gradient on the layer behind it)",
              "radial-gradient" in page.evaluate("() => getComputedStyle(document.querySelector('.tabs'), '::before').backgroundImage"))
        before = [box(page, seg(s)) for s in SEGMENTS]
        page.wait_for_timeout(300)
        check("nothing moves on first load (no motion)", before == [box(page, seg(s)) for s in SEGMENTS]
              and page.evaluate("() => [...document.querySelectorAll('.tabs button')].every(b => parseFloat(getComputedStyle(b).transitionDuration) === 0 && getComputedStyle(b).animationName === 'none')"))

        print("\n--- 3. Going in and coming back ---")
        for s in SEGMENTS:
            start(page)
            cx, cy, _ = circle(page)
            dx, dy = {"dashboard": (-90, -90), "units": (90, -90), "recipes": (-90, 90), "compendium": (90, 90)}[s]
            page.mouse.click(cx + dx, cy + dy)
            page.wait_for_timeout(150)
            ok = (not launching(page) and shown_sections(page) == [f"view-{s}"]
                  and page.get_attribute(seg(s), "aria-current") == "page" and page.locator(".tabs [aria-current]").count() == 1)
            check(f"tapping {NAMES[s]} opens it, lit, and the circle is gone", ok, (launching(page), shown_sections(page)))
            if s == "units":
                bg = lambda sel: page.evaluate("(s) => getComputedStyle(document.querySelector(s)).backgroundColor", sel)
                check("the lit segment keeps a real background-colour, different from the others", bg(seg("units")) != "rgba(0, 0, 0, 0)" and bg(seg("units")) != bg(seg("recipes")))
        start(page)
        page.click("#mentor-button")
        page.wait_for_timeout(200)
        # X1: Ask Mentor opens Painting > Colour Lab > Picker
        check("Ask Mentor opens Colour Lab with the Picker open", not launching(page) and shown_sections(page) == ["view-recipes"]
              and page.get_attribute('#lab-seg [data-lab="picker"]', "aria-selected") == "true")
        page.click(seg("units"))
        page.wait_for_timeout(150)
        page.click("#toggle-add")
        page.fill("#name-input", "Half typed unit")
        page.click("#home-button")
        page.wait_for_timeout(200)
        check("the title goes back to the launch page: circle shown, no section, nothing lit", launching(page) and shown_sections(page) == [] and page.locator(".tabs [aria-current]").count() == 0)
        check("Back has nothing to close on the launch page (no spare history step is left)", page.evaluate("() => history.state === null"))
        page.click(seg("units"))
        page.wait_for_timeout(150)
        check("coming back in, the typed text is still there", page.input_value("#name-input") == "Half typed unit")

        print("\n--- 4. Switching away and back never resets ---")
        page.click(seg("dashboard"))
        page.click("button.cog")
        page.wait_for_timeout(150)
        page.evaluate("() => window.scrollTo(0, 400)")
        page.click(seg("units"))
        page.fill("#name-input", "Still here")
        page.evaluate("() => window.scrollTo(0, 120)")
        y0 = page.evaluate("() => window.scrollY")
        for fire in ["() => { Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true }); document.dispatchEvent(new Event('visibilitychange')); }",
                     "() => window.dispatchEvent(new Event('blur'))", "() => window.dispatchEvent(new Event('pagehide'))",
                     "() => { Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true }); document.dispatchEvent(new Event('visibilitychange')); }",
                     "() => window.dispatchEvent(new Event('focus'))", "() => window.dispatchEvent(new Event('pageshow'))"]:
            page.evaluate(fire)
        page.wait_for_timeout(1200)
        check("after hidden / blur / pagehide and back: still on Models, no circle", not launching(page) and shown_sections(page) == ["view-units"])
        check("...with the typed text and the scroll position as they were", page.input_value("#name-input") == "Still here" and abs(page.evaluate("() => window.scrollY") - y0) < 2,
              (page.evaluate("() => window.scrollY"), y0))
        page.reload()
        page.wait_for_function("() => typeof settings === 'object'")
        page.wait_for_timeout(300)
        check("a real reload shows the circle again", launching(page) and shown_sections(page) == [])

        print("\n--- 5. A link that names a section ---")
        page.goto("about:blank")
        page.goto(t.URL + "#units")
        page.wait_for_function("() => typeof settings === 'object'")
        page.wait_for_timeout(300)
        check("#units opens Models straight away", not launching(page) and shown_sections(page) == ["view-units"])
        page.goto("about:blank")
        page.goto(t.URL + "#toString")
        page.wait_for_function("() => typeof settings === 'object'")
        page.wait_for_timeout(300)
        check("a hash that names nothing known shows the launch page", launching(page))

        print("\n--- 6. Sizes, light and dark ---")
        for w, h in [(390, 844), (360, 740), (320, 568)]:
            for mode in ["dark", "light"]:
                start(page, w, h, settings={"appearance": mode})
                cx, cy, o = circle(page)
                scale = o[2] / 124
                head = page.evaluate("() => document.querySelector('.app-bar').getBoundingClientRect().bottom")
                thick = min(box(page, seg(s))[2] for s in SEGMENTS) / 167.1 * 90   # the ring is 90 px thick (drawn), times the scale
                inside = cy - 170 * scale >= head - 0.5 and cy + 170 * scale <= h and cx - 170 * scale >= -0.5 and cx + 170 * scale <= w + 0.5
                ok = no_sideways(page) and inside and thick >= 44 and o[2] >= 44 and box(page, "#home-button")[3] >= 44 and box(page, ".cog")[3] >= 44
                check(f"{w} px {mode}: circle fits under the header, no sideways scroll, ring {thick:.0f} px thick, Mentor {o[2]:.0f} px, title and cog 44 px+",
                      ok, (inside, thick, o, no_sideways(page)))
        for w, h in [(640, 360), (390, 420)]:
            start(page, w, h)
            cx, cy, o = circle(page)
            scale = o[2] / 124
            head = page.evaluate("() => document.querySelector('.app-bar').getBoundingClientRect().bottom")
            thick = min(box(page, seg(s))[2] for s in SEGMENTS) / 167.1 * 90
            check(f"short screen {w} x {h}: the circle shrinks to fit the height, ring {thick:.0f} px thick",
                  cy - 170 * scale >= head - 0.5 and cy + 170 * scale <= h and thick >= 44 and no_sideways(page), (cy, scale, head, thick))
        start(page, 1280, 800)
        cx, cy, o = circle(page)
        check("1280 px wide: full size and centred", abs(o[2] - 124) < 1 and abs(cx - 640) < 1)
        start(page)
        page.click(seg("dashboard"))
        wait_settled(page)   # v93 (Mo3b): the circle now takes half a second to turn into the bar; measure once it has settled
        check("after going in, the bar is back to the curved band along the bottom (Mentor button 100 px, near the bottom)",
              abs(box(page, "#mentor-button")[2] - 100) < 1 and box(page, "#mentor-button")[1] > 844 - 200)
        check("help says how the start page works", "start page" in page.evaluate("() => document.getElementById('help-tabs').textContent"))

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
