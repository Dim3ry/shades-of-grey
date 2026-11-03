"""v127 tests for Minifolio (chunk MN1: the start circle's segment order matches the bar's, James 3 Nov).

New behaviour only:
1. The four segments sit Models top left, Painting top right, Dashboard bottom left, Tools bottom right (by their boxes on screen, not by
   markup order), at 390x844, 360x640, 320x568 and 1280x800, light and dark, Classic and two other themes. No sideways scroll, tap areas 44 px or more.
2. A tap on each segment's place opens its section. The keyboard (Tab) order stays the menu's own order, the same as the bar's.
3. The travel into the bar (Mo4b) and back (Mo4c): each copy ends on its own piece, the horizontal order of the copies never changes
   (Dashboard, Models, Painting, Tools from left to right) and no copy overlaps another. Reduced motion still has no travel.
4. The loading ring brings the segments in clockwise from the top left: Models, Painting, Tools, Dashboard."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled, _FINISH_BAR

load = t.load
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

UNITS = [{"id": 1, "name": "Squad", "hobby": "40K", "stage": 2, "count": 5, "added": "2026-10-01", "log": [["2026-10-01", 2]]}]
BAR_ORDER = ["dashboard", "units", "recipes", "guides"]   # the bar, left to right
NAMES = {"dashboard": "Dashboard", "units": "Models", "recipes": "Painting", "guides": "Tools"}
PLACE = {"units": (-1, -1), "recipes": (1, -1), "dashboard": (-1, 1), "guides": (1, 1)}   # MN1: x and y sign from the Mentor button's centre

# each segment's box centre relative to the Mentor button's centre, its smallest side, and the page's sideways scroll
BOXES = """() => { const o = document.getElementById('mentor-button').getBoundingClientRect(), ox = o.left + o.width / 2, oy = o.top + o.height / 2;
    const segs = Object.fromEntries([...document.querySelectorAll('.arc > [data-tab]')].map(b => { const r = b.getBoundingClientRect();
        return [b.dataset.tab, [r.left + r.width / 2 - ox, r.top + r.height / 2 - oy, Math.min(r.width, r.height)]]; }));
    return { segs, ox, oy, scale: o.width / 124, scrollX: document.documentElement.scrollWidth > document.documentElement.clientWidth }; }"""
HIT = """([x, y]) => { const e = document.elementFromPoint(x, y); const b = e && e.closest('button'); return b ? (b.dataset.tab || b.id || '') : ''; }"""
# the label's centre in each real segment (the text node), and in each travel copy
REAL_LABELS = """() => Object.fromEntries([...document.querySelectorAll('.arc > [data-tab]')].map(b => { const n = [...b.childNodes].find(c => c.nodeType === 3 && c.textContent.trim());
    const g = document.createRange(); g.selectNodeContents(n); const r = g.getBoundingClientRect(); return [b.dataset.tab, [r.left + r.width / 2, r.top + r.height / 2]]; }))"""
# freeze the travel at a moment (the layer's own clock; the copies are in the bar's order) and read each copy's label centre and polygon in page pixels
AT = """(ms) => new Promise(res => { const l = document.querySelector('.mo-tr'); if (!l) return res(null);
    if (l.mn1 === undefined) l.mn1 = l.getAnimations();   // kept: a paused clock seeked to its end drops out of getAnimations()
    l.mn1.forEach(a => { a.pause(); a.currentTime = ms; });
    requestAnimationFrame(() => requestAnimationFrame(() => res([...l.querySelectorAll('.w')].map(w => {
        const wr = w.getBoundingClientRect(), c = w.querySelector('.c .t').getBoundingClientRect();
        const poly = w.style.clipPath.replace(/^polygon\\(|\\)$/g, '').split(',').map(s => s.trim().split(/\\s+/).map(v => parseFloat(v)))
            .map(p => [p[0] + wr.left, p[1] + wr.top]);
        return { label: [c.left + c.width / 2, c.top + c.height / 2], poly }; })))); })"""

def inside(pt, poly):
    """Is the point well inside the polygon (ray casting)?"""
    x, y, n, ok = pt[0], pt[1], len(poly), False
    j = n - 1
    for i in range(n):
        xi, yi, xj, yj = poly[i][0], poly[i][1], poly[j][0], poly[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            ok = not ok
        j = i
    return ok

def shrink(poly, k=0.97):
    """The polygon pulled 3% toward its own middle, so pieces that only touch at an edge do not count as overlapping."""
    mx, my = sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)
    return [[mx + (p[0] - mx) * k, my + (p[1] - my) * k] for p in poly]

def travel_frames(page, times):
    out = [page.evaluate(AT, ms) for ms in times]
    # rewound and running again, so finishing it (_FINISH_BAR) ends the travel the usual way
    page.evaluate("() => { const l = document.querySelector('.mo-tr'); if (l && l.mn1) l.mn1.forEach(a => { a.currentTime = 0; a.play(); }); }")
    return out

def order_ok(frames, tol=4):
    """The copies' labels and pieces stay in the bar's order from left to right in every frame. In the circle Models sits straight above
    Dashboard (and Painting above Tools), so their x is equal there and the soft bounce at the end may sway them a few px either way (tol)."""
    bad = []
    for n, f in enumerate(frames):
        lx = [c["label"][0] for c in f]
        px = [sum(p[0] for p in c["poly"]) / len(c["poly"]) for c in f]
        if any(lx[i] > lx[i + 1] + tol or px[i] > px[i + 1] + tol for i in range(3)):
            bad.append((n, [round(v) for v in lx], [round(v) for v in px]))
    return bad

def overlaps(frames):
    bad = []
    for n, f in enumerate(frames):
        for i in range(4):
            for j in range(4):
                if i != j and any(inside(p, f[j]["poly"]) for p in shrink(f[i]["poly"])):
                    bad.append((n, BAR_ORDER[i], BAR_ORDER[j]))
    return bad

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. Where the segments sit ---")
        load(page, units=UNITS, launch=True)
        r = page.evaluate(BOXES)
        check("390x844: Models top left, Painting top right, Dashboard bottom left, Tools bottom right (by their boxes)",
              all((r["segs"][s][0] > 0) == (PLACE[s][0] > 0) and (r["segs"][s][1] > 0) == (PLACE[s][1] > 0) and min(abs(r["segs"][s][0]), abs(r["segs"][s][1])) > 40 for s in PLACE), r["segs"])
        check("the rows line up: Models and Painting share a top, Dashboard and Tools share a bottom; left and right columns match",
              abs(r["segs"]["units"][1] - r["segs"]["recipes"][1]) < 1 and abs(r["segs"]["dashboard"][1] - r["segs"]["guides"][1]) < 1
              and abs(r["segs"]["units"][0] - r["segs"]["dashboard"][0]) < 1 and abs(r["segs"]["recipes"][0] - r["segs"]["guides"][0]) < 1, r["segs"])
        hits = {s: page.evaluate(HIT, [r["ox"] + PLACE[s][0] * 90, r["oy"] + PLACE[s][1] * 90]) for s in PLACE}
        check("a tap in each quarter hits that segment (the tap area is the segment itself)", all(hits[s] == s for s in PLACE), hits)
        labels = {s: page.evaluate("(s) => document.querySelector('.arc [data-tab=' + s + ']').textContent.trim()", s) for s in PLACE}
        check("each segment keeps its own label and icon", all(labels[s] == NAMES[s] for s in PLACE)
              and page.evaluate("() => [...document.querySelectorAll('.arc > [data-tab]')].every(b => b.querySelector('.icon svg'))"), labels)
        page.evaluate("() => document.getElementById('home-button').focus()")
        tab_order = []
        for _ in range(30):
            page.keyboard.press("Tab")
            s = page.evaluate("() => document.activeElement.dataset.tab || ''")
            if s and s not in tab_order:
                tab_order.append(s)
            if len(tab_order) == 4:
                break
        check("keyboard order stays the menu's own order, the same as the bar (Dashboard, Models, Painting, Tools)", tab_order == BAR_ORDER, tab_order)

        for (w, h, mode, theme) in ((360, 640, "light", "classic"), (320, 568, "dark", "parchment"), (1280, 800, "light", "forge"), (900, 700, "dark", "bench")):
            page.set_viewport_size({"width": w, "height": h})
            load(page, units=UNITS, settings={"theme": theme, "appearance": mode}, launch=True)
            r = page.evaluate(BOXES)
            ok = all((r["segs"][s][0] > 0) == (PLACE[s][0] > 0) and (r["segs"][s][1] > 0) == (PLACE[s][1] > 0) for s in PLACE)
            check(f"{w}x{h} {mode} {theme}: the same four places, tap areas 44 px or more, no sideways scroll",
                  ok and all(v[2] >= 44 for v in r["segs"].values()) and not r["scrollX"], r)
        page.set_viewport_size({"width": 390, "height": 844})

        print("\n--- 2. Each segment opens its section ---")
        # one page, reduced motion (no travel to wait for; the travel is section 3), back to the circle by the title button each time
        page.emulate_media(reduced_motion="reduce")
        load(page, units=UNITS, launch=True)
        for s in BAR_ORDER:
            r = page.evaluate(BOXES)
            page.mouse.click(r["ox"] + PLACE[s][0] * 90 * r["scale"], r["oy"] + PLACE[s][1] * 90 * r["scale"])
            wait_settled(page)
            check(f"a tap on {NAMES[s]}'s place opens {NAMES[s]}, lit",
                  page.evaluate("(s) => settings.tab === s && !document.body.classList.contains('launching') && document.querySelector('.arc [aria-current=page]').dataset.tab === s", s))
            page.click("#home-button")
            wait_settled(page)
        page.emulate_media(reduced_motion="no-preference")

        print("\n--- 3. The travel: symmetrical, no crossing ---")
        times = list(range(0, 1501, 75))
        load(page, units=UNITS, launch=True)
        circle = page.evaluate(REAL_LABELS)
        for s in ("recipes",):   # Painting: the piece that used to cross over (the travel's shape is the same whichever segment is tapped)
            page.evaluate("(s) => document.querySelector('.tabs button[data-tab=' + s + ']').click()", s)
            frames = travel_frames(page, times)
            page.evaluate(_FINISH_BAR)
            wait_settled(page)
            real = page.evaluate(REAL_LABELS)
            check(f"to the bar ({NAMES[s]}): four copies in every frame", all(f and len(f) == 4 for f in frames))
            first = frames[0]
            check(f"to the bar ({NAMES[s]}): the copies start on the circle, the top two (Models, Painting) above the bottom two",
                  first[1]["label"][1] < first[0]["label"][1] - 40 and first[2]["label"][1] < first[3]["label"][1] - 40, [c["label"] for c in first])
            end = frames[-1]
            far = max(abs(end[i]["label"][0] - real[t][0]) + abs(end[i]["label"][1] - real[t][1]) for i, t in enumerate(BAR_ORDER))
            check(f"to the bar ({NAMES[s]}): each copy ends on its own bar piece (Models and Painting on the raised middle two)", far < 3,
                  ([c["label"] for c in end], real))
            check(f"to the bar ({NAMES[s]}): the horizontal order never changes", not order_ok(frames), order_ok(frames)[:3])
            check(f"to the bar ({NAMES[s]}): no copy ever overlaps another", not overlaps(frames), overlaps(frames)[:3])

        # the way back (Mo4c): from Painting to the circle, by the round back arrow
        page.evaluate("() => document.getElementById('back-menu').click()")
        frames = travel_frames(page, [0] + list(range(350, 1851, 75)))
        page.evaluate(_FINISH_BAR)
        wait_settled(page)
        check("the way back: four copies in every frame", all(f and len(f) == 4 for f in frames))
        end = frames[-1]
        far = max(abs(end[i]["label"][0] - circle[t][0]) + abs(end[i]["label"][1] - circle[t][1]) for i, t in enumerate(BAR_ORDER))
        check("the way back: each copy lands on its own circle segment", far < 3, ([c["label"] for c in end], circle))
        check("the way back: the horizontal order never changes", not order_ok(frames), order_ok(frames)[:3])
        check("the way back: no copy ever overlaps another", not overlaps(frames), overlaps(frames)[:3])
        r = page.evaluate(BOXES)
        check("back on the circle: the segments are in their new places",
              page.evaluate("() => document.body.classList.contains('launching')") and all((r["segs"][s][0] > 0) == (PLACE[s][0] > 0) and (r["segs"][s][1] > 0) == (PLACE[s][1] > 0) for s in PLACE), r["segs"])

        print("\n--- 4. Reduced motion ---")
        page.emulate_media(reduced_motion="reduce")   # the same page, on the circle again
        page.evaluate("() => document.querySelector('.tabs button[data-tab=recipes]').click()")
        check("reduced motion, to the bar: no travel copies", page.evaluate("() => !document.querySelector('.mo-tr') && settings.tab === 'recipes'"))
        page.evaluate("() => document.getElementById('back-menu').click()")
        check("reduced motion, the way back: no travel copies, the circle at once",
              page.evaluate("() => !document.querySelector('.mo-tr') && document.body.classList.contains('launching')"))
        page.emulate_media(reduced_motion="no-preference")

        print("\n--- 5. The loading ring brings them in clockwise from the top left ---")
        page.reload()   # a fresh load of the same seeded page (the last load above), so the ring plays
        order =page.evaluate("""() => new Promise(done => { const seen = [], t0 = performance.now();
            const f = () => { for (const b of document.querySelectorAll('.arc [data-tab]'))
                if (!b.classList.contains('ring-hold') && !seen.includes(b.dataset.tab) && document.querySelector('.mo-load')) seen.push(b.dataset.tab);
              if (!document.querySelector('.mo-load') && performance.now() - t0 > 300 || performance.now() - t0 > 5000) done(seen); else requestAnimationFrame(f); }; f(); })""")
        check("they arrive Models, Painting, Tools, Dashboard", order == ["units", "recipes", "guides", "dashboard"], order)
        wait_settled(page)

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

main()
