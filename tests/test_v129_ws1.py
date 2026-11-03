"""v129 tests for Minifolio (chunk WS1: wide-screen start circle and bottom bar, the same shapes placed and sized better). New behaviour only.

On wide screens (900 px and over):
1. The start circle on a cold start shows only the circle: the Dashboard no longer shows through behind it (its wide grid rule beat
   the start page's "hide every section"), with motion on and with reduced motion, light and dark.
2. At 1280 and 1920 px, scrolled to the bottom, the bar and the Mentor button cover no content row: the last card ends 24 px or more
   above the bar's top, as on a phone.
3. An open unit's side pane, and an open paint's in Your Palette, scrolled to its own end while the page is not at its bottom:
   its last button ends above the bar and nothing drawn in it is under the bar or the Mentor button.
4. The round back arrow sits beside the bar, 12 px from the Dashboard segment's box as on a 390 px phone, clear of the segment's real
   shape, 44 px; at 899 px it is still in the phone's place. Tap targets 44 px or more, no sideways scroll.
5. Reduced motion still turns the travel off on a wide screen.
6. Phones: 390x844 and 360x640 measure exactly as before (the numbers were measured on v127, before WS1)."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled, quiet, app_ready, _FINISH_BAR
from test_v114_back_arrow import GAP   # the smallest gap between the arrow and the Dashboard segment's real (slanted) shape

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def step(tech, *ids):
    return {"technique": tech, "coats": 1, "paints": [{"paint": p, "mix": None if len(ids) == 1 else 50} for p in ids], "ratio": "", "note": "", "optional": False}

PAINTS = t.PAINTS + [{"id": 100 + i, "brand": ["Vallejo", "Citadel"][i % 2], "name": "Extra paint %d" % i,
                      "colour": "#%02x%02x%02x" % ((i * 37) % 256, (i * 91) % 256, (i * 53) % 256), "status": "owned"} for i in range(40)]
RECIPES = [{"id": 200 + i, "name": "Recipe %d" % i, "part": "Armour", "notes": "", "steps": [step("Base coat", 1), step("Layer", 4, 6), step("Layer", 100 + i)]} for i in range(20)]
UNITS = [{"id": i, "name": "Troop unit %d" % i, "hobby": "Test game", "faction": "Faction %d" % (i % 5), "stage": i % 5, "count": 5,
          "added": "2026-10-01", "log": [["2026-10-01", i % 5]]} for i in range(1, 31)]

# the phone numbers measured on v127 before WS1: body padding at the bottom, then [left, top, width, height] of each part
PHONE = {
    (390, 844): {"pad": "196px", "back": [8, 794, 44, 44], "orb": [145, 754, 100, 100], "dashboard": [64, 707, 89, 89],
                 "units": [109, 672, 85, 85], "recipes": [196, 672, 85, 85], "guides": [237, 707, 89, 89]},
    (360, 640): {"pad": "182.756px", "back": [8, 590, 44, 44], "orb": [133.85, 556.93, 92.3, 92.3], "dashboard": [59.09, 513.55, 82.15, 82.15],
                 "units": [100.62, 481.24, 78.46, 78.45], "recipes": [180.92, 481.24, 78.46, 78.45], "guides": [218.77, 513.55, 82.15, 82.15]},
}
PROBE = """() => { const R = e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height].map(v => Math.round(v * 100) / 100); };
  const out = { pad: getComputedStyle(document.body).paddingBottom, back: R(document.getElementById('back-menu')), orb: R(document.getElementById('mentor-button')) };
  document.querySelectorAll('.tabs .arc > [data-tab]').forEach(b => out[b.dataset.tab] = R(b)); return out; }"""

# what shows on the start page besides the circle: any section of main that is drawn
SECTIONS_SHOWN = """() => [...document.querySelectorAll('main > :not(.app-bar)')].filter(e => getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().height > 0).map(e => e.id || e.className)"""

# the part of an element that is drawn: its box cut by every scrolling or clipping box around it, or null when it is not drawn at all
# (inside a closed fold, hidden, or scrolled out of its pane)
VIS = """const vis = e => { if (!e.checkVisibility({ visibilityProperty: true })) return null; let r = e.getBoundingClientRect();
    let a = { l: r.left, t: Math.max(r.top, 0), r: r.right, b: Math.min(r.bottom, innerHeight) };
    for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) { const s = getComputedStyle(p);
      if (s.overflowY !== 'visible' || s.overflowX !== 'visible') { const q = p.getBoundingClientRect(); a = { l: Math.max(a.l, q.left), t: Math.max(a.t, q.top), r: Math.min(a.r, q.right), b: Math.min(a.b, q.bottom) }; } }
    return a.r - a.l > 1 && a.b - a.t > 1 ? a : null; };"""

# the drawn content rows, cards and controls that lie under the bar or the Mentor button (by the real shapes: elementFromPoint on a grid
# over the bar's box), the lowest drawn row or card, and the bar's top
COVERED = """(root) => { """ + VIS + """ const scope = document.querySelector(root || 'main');
  const bar = [...document.querySelectorAll('.tabs .arc > [data-tab], #mentor-button')].map(b => b.getBoundingClientRect());
  const bx = { l: Math.min(...bar.map(r => r.left)), t: Math.min(...bar.map(r => r.top)), r: Math.max(...bar.map(r => r.right)), b: Math.max(...bar.map(r => r.bottom)) };
  const rows = [...scope.querySelectorAll('li, .card, button, select, input, textarea')].map(e => [e, vis(e)]).filter(x => x[1]);
  const under = [];
  for (const [e, a] of rows) { let found = false;
    for (let x = Math.max(a.l, bx.l) + 2; x < Math.min(a.r, bx.r) - 1 && !found; x += 5) for (let y = Math.max(a.t, bx.t) + 2; y < Math.min(a.b, bx.b) - 1 && !found; y += 5) {
      const h = document.elementFromPoint(x, y); if (h && h.closest('.tabs .arc > [data-tab], #mentor-button')) found = true; }
    if (found) under.push((e.tagName + ' ' + (e.textContent || e.placeholder || '').trim()).slice(0, 40)); }
  const lowest = Math.max(...rows.filter(x => x[0].matches('li, .card')).map(x => x[1].b));
  return { under, barTop: bx.t, lowest, scrollX: document.documentElement.scrollWidth > document.documentElement.clientWidth }; }"""

# a side pane scrolled to its own end: its last drawn control, and whether that control is on top and above the bar
PANE_END = """(sel) => { """ + VIS + """ const pane = document.querySelector(sel); pane.scrollTop = pane.scrollHeight;
  return new Promise(res => requestAnimationFrame(() => requestAnimationFrame(() => {
    const pr = pane.getBoundingClientRect();
    const drawn = [...pane.querySelectorAll('button, select, input, textarea')].filter(e => vis(e));
    const last = drawn[drawn.length - 1], lr = last.getBoundingClientRect();
    const barTop = Math.min(...[...document.querySelectorAll('.tabs .arc > [data-tab], #mentor-button')].map(b => b.getBoundingClientRect().top));
    const hit = document.elementFromPoint(lr.left + lr.width / 2, lr.top + lr.height / 2);
    res({ last: last.textContent.trim().slice(0, 20), lastBottom: lr.bottom, barTop, paneBottom: pr.bottom, sticky: pr.top < 100,
          paneScrolls: pane.scrollHeight > pane.clientHeight, lastIsOnTop: !!hit && last.contains(hit) }); }))); }"""

ARROW = """() => { const a = document.getElementById('back-menu').getBoundingClientRect(), d = document.querySelector('.tabs .arc [data-tab=dashboard]').getBoundingClientRect(),
    arc = document.querySelector('.tabs .arc').getBoundingClientRect(); return { left: a.left, boxGap: d.left - a.right, inFromArc: a.left - arc.left, bottom: innerHeight - a.bottom }; }"""

def wide_checks(page, w):
    print(f"\n--- 2. {w} px: the bar and the Mentor button cover no content row ---")
    for name, prep in (("Dashboard", "() => showTab('dashboard')"), ("Models", "() => { openIds.clear(); showTab('units'); render(); }"),
                       ("Painting with a recipe open", "() => { settings.recipeView = 'recipes'; openRecipe(203); }")):
        page.evaluate(prep)
        quiet(page)
        page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
        quiet(page)
        c = page.evaluate(COVERED, None)
        check(f"{w} {name}, scrolled to the bottom: nothing under the bar, the last card ends 24 px or more above it, no sideways scroll",
              not c["under"] and c["barTop"] - c["lowest"] >= 23.5 and not c["scrollX"], c)

    print(f"\n--- 3. {w} px: side panes scroll clear of the bar ---")
    page.evaluate("() => { openRecipeId = null; openIds.clear(); [3, 7, 12].forEach(i => openIds.add(i)); showTab('units'); render(); }")
    quiet(page)
    page.evaluate("() => window.scrollTo(0, 400)")
    quiet(page)
    r = page.evaluate(PANE_END, "#unit-split.layout-split > .layout-side")
    check(f"{w} Models, three units open, the page part way down: the pane is held in view and scrolls on its own", r["sticky"] and r["paneScrolls"], r)
    check(f"{w} ... at the pane's end its last button ({r['last']}) is drawn on top and ends 20 px or more above the bar",
          r["lastIsOnTop"] and r["barTop"] - r["lastBottom"] >= 20, r)
    c = page.evaluate(COVERED, "#unit-split > .layout-side")
    check(f"{w} ... nothing drawn in the pane is under the bar or the Mentor button", not c["under"], c["under"])
    page.evaluate("() => { settings.recipeView = 'palette'; showTab('recipes'); renderRecipes(); }")
    quiet(page)
    if not page.locator("#palette-split > .layout-side .unit-side-card").count():
        page.evaluate("() => [...document.querySelectorAll('#palette-view .paint-item')].slice(0, 3).forEach(i => (i.querySelector('button, [role=button]') || i).click())")
        quiet(page)
    page.evaluate("() => window.scrollTo(0, 1500)")
    quiet(page)
    r = page.evaluate(PANE_END, "#palette-split.layout-split > .layout-side")
    check(f"{w} Your Palette, three paints open: at the pane's end its last button ({r['last']}) is on top and ends 20 px or more above the bar",
          r["sticky"] and r["paneScrolls"] and r["lastIsOnTop"] and r["barTop"] - r["lastBottom"] >= 20, r)

    print(f"\n--- 4. {w} px: the back arrow beside the bar, tap targets ---")
    page.evaluate("() => { settings.recipeView = 'recipes'; window.scrollTo(0, 0); showTab('dashboard'); }")
    quiet(page)
    a = page.evaluate(ARROW)
    check(f"{w}: the arrow sits 8 px in from the bar's left edge, 12 px from the Dashboard segment's box (as on a 390 px phone), 6 px from the bottom",
          abs(a["inFromArc"] - 8) < 0.6 and abs(a["boxGap"] - 12) < 0.6 and abs(a["bottom"] - 6) < 0.6, a)
    g = page.evaluate(GAP)
    check(f"{w}: it stays clear of the segment's real shape (4 px or more) and is 44 px", g["gap"] >= 4 and g["w"] == 44 and g["h"] == 44, g)
    sizes = page.evaluate("""() => [...document.querySelectorAll('.tabs .arc > [data-tab], #mentor-button, #back-menu')].map(b => { const r = b.getBoundingClientRect(); return Math.min(r.width, r.height); })""")
    check(f"{w}: every bar part and the arrow is 44 px or more", min(sizes) >= 44, sizes)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # one page with motion on, light: the cold start and the checks at 1280, then the same page at 1920
        ctx = browser.new_context(viewport={"width": 1280, "height": 800}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        print("\n--- 1. 1280 px, light: the start circle on a cold start ---")
        t.load(page, paints=PAINTS, recipes=RECIPES, units=UNITS, settings={"appearance": "light", "examplesChecked": True, "tab": "dashboard"}, launch=True)
        check("1280: only the circle shows on the start page (the Dashboard is not drawn behind it)",
              page.evaluate("() => document.body.classList.contains('launching')") and page.evaluate(SECTIONS_SHOWN) == [], page.evaluate(SECTIONS_SHOWN))
        hit = page.evaluate("""() => { const o = document.getElementById('mentor-button').getBoundingClientRect();
            return [...document.querySelectorAll('.arc > [data-tab]')].map(b => { const r = b.getBoundingClientRect(); const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
              const e = document.elementFromPoint(cx + (cx - o.left - o.width / 2) * 0.2, cy + (cy - o.top - o.height / 2) * 0.2); return e && e.closest('button') ? e.closest('button').dataset.tab : ''; }); }""")
        check("1280: a tap on each segment's place lands on that segment", hit == ["dashboard", "units", "recipes", "guides"], hit)
        page.evaluate("() => document.querySelector('.tabs button[data-tab=dashboard]').click()")
        page.evaluate(_FINISH_BAR)
        wait_settled(page)
        check("1280: leaving the circle still opens the Dashboard in its wide grid", page.evaluate("() => !document.body.classList.contains('launching') && settings.tab === 'dashboard'")
              and page.evaluate("() => getComputedStyle(document.getElementById('view-dashboard')).display") == "grid")
        wide_checks(page, 1280)
        page.set_viewport_size({"width": 1920, "height": 1080})
        quiet(page)
        wide_checks(page, 1920)
        page.click("#back-menu")
        page.evaluate(_FINISH_BAR)
        wait_settled(page)
        check("1920: the arrow still takes you back to the circle, with nothing drawn behind it",
              page.evaluate("() => document.body.classList.contains('launching')") and page.evaluate(SECTIONS_SHOWN) == [], page.evaluate(SECTIONS_SHOWN))
        ctx.close()

        # one page with reduced motion, dark: the phones, the 900 px edge, then a wide screen
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        print("\n--- 6. Phones unchanged ---")
        t.load(page, units=UNITS[:8], settings={"tab": "dashboard", "appearance": "dark"})
        page.evaluate("() => { showTab('units'); openIds.add(2); render(); }")
        quiet(page)
        for (w, h) in ((390, 844), (360, 640)):
            page.set_viewport_size({"width": w, "height": h})
            quiet(page)
            got, exp = page.evaluate(PROBE), PHONE[(w, h)]
            far = max(abs(a - b) for k in exp if k != "pad" for a, b in zip(got[k], exp[k]))
            check(f"{w}x{h}: the bar, the Mentor button, the back arrow and the page's bottom room measure exactly as before",
                  got["pad"] == exp["pad"] and far < 0.05, (got, exp))

        print("\n--- 4b. 899 px is still a phone; 900 px is wide ---")
        page.set_viewport_size({"width": 899, "height": 800})
        quiet(page)
        check("899 px: the arrow is in the phone's place (8 px from the left edge)", page.evaluate(ARROW)["left"] == 8, page.evaluate(ARROW))
        page.set_viewport_size({"width": 900, "height": 800})
        quiet(page)
        a = page.evaluate(ARROW)
        check("900 px: it moves beside the bar", abs(a["boxGap"] - 12) < 0.6, a)

        print("\n--- 5. Reduced motion on a wide screen (1280 px, dark) ---")
        page.set_viewport_size({"width": 1280, "height": 800})
        page.evaluate("() => { showTab('dashboard'); saveSettings(); }")
        page.reload()   # a cold start on the Dashboard
        app_ready(page)
        check("reduced motion: only the circle on the start page", page.evaluate("() => document.body.classList.contains('launching')") and page.evaluate(SECTIONS_SHOWN) == [],
              page.evaluate(SECTIONS_SHOWN))
        page.evaluate("() => document.querySelector('.tabs button[data-tab=units]').click()")
        check("reduced motion: leaving the circle has no travel", page.evaluate("() => !document.querySelector('.mo-tr') && settings.tab === 'units' && !document.body.classList.contains('launching')"))
        page.click("#back-menu")
        check("reduced motion: the arrow goes back at once with no travel, nothing drawn behind the circle",
              page.evaluate("() => !document.querySelector('.mo-tr') && document.body.classList.contains('launching')") and page.evaluate(SECTIONS_SHOWN) == [])
        ctx.close()

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

main()
