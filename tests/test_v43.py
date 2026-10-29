"""v43 tests for Minifolio (W1): the colour wheel drills down (Pro preview).

What changed:
 - In the Compendium, tapping red, orange, yellow, green, blue or purple redraws the wheel picture as that colour's THREE groups (the existing
   groups and names), each a big labelled segment, with the names outside the ring. A round Back button sits in the middle, and there is a
   "Back to all colours" button under the picture. Escape also goes back.
 - Tapping a group shows that group's paints below the picture (the same detail list as before: yours first, dark to light, Show all N,
   Copy as text); tapping it again closes it.
 - The grey centre (whites, greys, blacks, metallics) works exactly as before.
 - Focusable segments with names, level changes spoken through a polite live region, open state kept while the app is open.

Checks:
1. Versions, the v43 Updates entry, Help and the Compendium intro line, wiring (six script files, the same twelve offline files, no new
   network code, no storage, no innerHTML, no links, no Games Workshop words), reuse of WHEEL / wheelPlace / wheelSub / buildWheelDetail.
2. The top of the wheel: no drilling at the start, hint line unchanged, hue colours say they open their groups, the grey centre does not.
3. EVERY one of the 18 groups by tap: the right three names, a segment that says colour, group, paint count and what you own, tapping opens
   that group's paints (and only that group's), tapping again closes it.
4. EVERY one of the 18 groups by keyboard (Enter and Space): focus order, open, close, back, focus returns to the colour.
5. The detail list: only that group, yours first, dark to light, Show other paints, Show all N / Show fewer, Copy as text.
6. The way back up: the middle button, the Back button, Escape, the keyboard; each says "Back to all colours." and returns focus.
7. The open state survives leaving the tab and coming back (and is not kept after a reload, like the other Compendium state).
8. The grey centre is unchanged.
9. Shopping list: the paint panel inside a group list, "On your shopping list" markers, and the shopping-list source
   ("Compendium: Colour wheel, <colour>") are as before.
10. Screen reader: live announcements for every level change; aria labels.
11. Phones 360, 375, 390 and 400 px, dark and light, all six colours: labels outside the ring, readable size, no overlap, big tap targets,
    contrast, no sideways scroll.
12. Hostile text (text-injection test): HTML in paint and brand names stays plain text everywhere in the drilled-down wheel.
13. Nothing else changed: other tabs, no pop-ups, no page errors, offline.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, subprocess, sys
from playwright.sync_api import sync_playwright
from launch_helpers import leave_launch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
import test_v31 as t
import test_v39 as h   # wheel helpers (P, open_tab, open_row, open_fold, prows, stored_paints ...)

SHOTS, ROOT = t.SHOTS, t.ROOT
read, load, blur = t.read, t.load, t.blur
shot, no_sideways, rgb, contrast = t.shot, t.no_sideways, t.rgb, t.contrast
HOSTILE, HOSTILE_BRAND, GW_WORDS = t.HOSTILE, t.HOSTILE_BRAND, t.GW_WORDS
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

P = h.P
HUES = ["red", "orange", "yellow", "green", "blue", "purple"]
CENTRE = ["white", "grey", "black", "metallic"]
LABEL = {"red": "Red", "orange": "Orange", "yellow": "Yellow", "green": "Green", "blue": "Blue", "purple": "Purple"}
# the 18 groups, in the order they sit in the picture (first at the top, second lower right, third lower left)
GROUPS = {
    "red": [("deep", "Deep reds"), ("red", "Reds"), ("pink", "Pinks")],
    "orange": [("brown", "Browns"), ("orange", "Oranges"), ("peach", "Peach and apricot")],
    "yellow": [("mustard", "Mustard and ochre"), ("yellow", "Yellows"), ("bone", "Bone")],
    "green": [("olive", "Olive and moss"), ("green", "Greens"), ("sea", "Sea green and mint")],
    "blue": [("navy", "Navy and deep blue"), ("blue", "Blues"), ("light", "Sky and pale blue")],
    "purple": [("deep", "Deep purple"), ("violet", "Violet"), ("lavender", "Lavender and lilac")],
}
ALL18 = [(hue, sk, label) for hue in HUES for sk, label in GROUPS[hue]]

# A made-up palette (nothing here names a real paint) with something in several groups; one wishlist blue.
PAINTS = [
    P(1, "Deep Test Blue", "#0d2a5c"), P(2, "Mid Test Blue", "#3b6fb0"), P(3, "Pale Test Blue", "#a9c6ec"),
    P(4, "Wish Blue", "#1f4f9a", "wishlist"), P(5, "Empty Blue", "#2a5fa8", "empty"),
    P(6, "Test Red", "#c1272d"), P(7, "Test Green", "#228b22"), P(8, "Test Purple", "#7b2d8b"),
    P(9, "Test Orange", "#e8802a"), P(10, "Dark Brown Test", "#4a2d12"), P(11, "Test Yellow", "#e6c82e"),
    P(12, "Test Gold", "#c9a227"), P(13, "Test White", "#f4f6f8"), P(14, "Test Grey", "#8a9099"), P(15, "Test Black", "#0b0d10"),
]

STATE_JS = "() => ({ zoom: compendiumState.wheelZoom, group: compendiumState.wheelGroup, wheel: compendiumState.wheel, paint: compendiumState.paintOpen })"
SEGS_JS = """() => [...document.querySelectorAll('#cmp-wheel .wheel-sub-seg')].map(g => ({ key: g.dataset.wheelSub, aria: g.getAttribute('aria-label'),
    role: g.getAttribute('role'), tab: g.getAttribute('tabindex'), pressed: g.getAttribute('aria-pressed'),
    text: [...g.querySelectorAll('.wheel-label')].map(e => e.textContent).join(' '), lines: g.querySelectorAll('.wheel-label').length,
    fill: g.querySelector('path').getAttribute('fill'), chip: g.querySelector('.wheel-chip').getAttribute('fill') }))"""
DETAIL_JS = """() => { const d = document.getElementById('cmp-wheel-detail'); if (!d) return null;
    return { title: d.querySelector('h3').textContent, headings: [...d.querySelectorAll('h4.wheel-sub')].map(e => e.textContent),
             split: !!d.querySelector('#cmp-wheel-groups'), count: d.querySelector('.idea-label').textContent,
             rows: [...d.querySelectorAll('ul.idea-list > li')].map(li => ({ name: li.querySelector('.idea-name').childNodes[0].textContent,
                 tag: li.querySelector('.idea-tag').textContent, why: li.querySelector('.idea-why').textContent })) }; }"""

def wait(page, ms=150):
    page.wait_for_timeout(ms)

def open_comp(page):
    h.open_tab(page)

def live(page, ms=120):
    wait(page, ms)
    return page.evaluate("() => document.getElementById('wheel-live').textContent")

def state(page):
    return page.evaluate(STATE_JS)

def into_view(page):
    page.evaluate("() => document.getElementById('cmp-wheel').scrollIntoView({ block: 'center' })")
    wait(page, 60)

def zoom(page, hue):
    into_view(page)
    page.click(f'[data-wheel="{hue}"]')
    wait(page)

def ring_point(page, index):
    """Where a finger lands on group `index` (0 top, 1 lower right, 2 lower left): the middle of its ring slice, in page pixels."""
    return page.evaluate("""(i) => { const r = document.getElementById('cmp-wheel').getBoundingClientRect(), k = r.width / 320, a = [0, 120, 240][i] * Math.PI / 180;
        return [r.left + (160 + 73 * Math.sin(a)) * k, r.top + (150 - 73 * Math.cos(a)) * k]; }""", index)

def tap_group(page, hue, sk, how="ring"):
    index = [k for k, _ in GROUPS[hue]].index(sk)
    into_view(page)
    if how == "label":
        page.click(f'[data-wheel-sub="{hue}/{sk}"] .wheel-hit')
    else:
        x, y = ring_point(page, index)
        page.mouse.click(x, y)
    wait(page)

def back_button(page):
    into_view(page)
    page.click("#cmp-wheel-back")
    wait(page)

def expected_group(page, hue, sk):
    return page.evaluate("([s, k]) => wheelItems().filter(x => x.at.seg === s && x.at.sub === k).map(x => ({ name: x.paint.name, origin: x.origin, L: x.at.L }))", [hue, sk])

def active(page):
    return page.evaluate("() => { const a = document.activeElement; return a ? { ws: a.dataset.wheelSub || null, w: a.dataset.wheel || null, back: a.dataset.wheelBack || null, id: a.id, tag: a.tagName } : null; }")

def copy_spy(page):
    page.evaluate("""() => { window.__copied = null;
        Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: (x) => { window.__copied = x; return Promise.resolve(); } } }); }""")

GEOMETRY_JS = """() => { const svg = document.getElementById('cmp-wheel'); const r = svg.getBoundingClientRect(); const k = r.width / 320;
    const cx = r.left + 160 * k, cy = r.top + 150 * k, R = 96 * k;
    const labels = [...svg.querySelectorAll('.wheel-sub-seg')].map(g => {
        const t = [...g.querySelectorAll('.wheel-label')].map(e => e.getBoundingClientRect());
        const l = Math.min(...t.map(x => x.left)), rr = Math.max(...t.map(x => x.right)), tp = Math.min(...t.map(x => x.top)), b = Math.max(...t.map(x => x.bottom));
        const nx = Math.max(l, Math.min(cx, rr)), ny = Math.max(tp, Math.min(cy, b));
        const hit = g.querySelector('.wheel-hit').getBoundingClientRect(), path = g.querySelector('path').getBoundingClientRect();
        return { l, r: rr, t: tp, b, dist: Math.hypot(nx - cx, ny - cy), font: parseFloat(getComputedStyle(g.querySelector('.wheel-label')).fontSize) * k,
                 hitW: hit.width, hitH: hit.height, pathW: path.width, pathH: path.height, lines: t.length }; });
    const disc = svg.querySelector('.wheel-back-disc').getBoundingClientRect();
    return { k, R, svg: { l: r.left, r: r.right, t: r.top, b: r.bottom, w: r.width }, vw: window.innerWidth, labels, disc: { w: disc.width, h: disc.height } }; }"""

def overlap(a, b):
    return not (a["r"] <= b["l"] or b["r"] <= a["l"] or a["b"] <= b["t"] or b["b"] <= a["t"])

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        errors, dialogs, requests = [], [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        attach_notices(page, dialogs.append)
        page.on("request", lambda r: requests.append(r.url))

        # ---------- 1. Versions, wiring and reuse ----------
        print("\n--- 1. Versions, wiring and reuse ---")
        load(page, paints=PAINTS)
        html, app = read("index.html"), read("app.js")
        tags = re.findall(r'<script src="([^"]+)\?v=(\d+)"', html)
        help_text = page.evaluate("() => document.getElementById('help-tabs').textContent")
        # v75: removed check "Help says the wheel opens into groups": Help's tab line is now one short sentence (v75, HELP-3), so it no longer describes the Compendium
        open_comp(page)
        intro = page.inner_text("#cmp-intro")
        check("the Compendium intro line says a colour opens its groups", "tap a colour to open its groups" in intro, intro)
        diff = subprocess.run(["git", "diff", "main", "--", "app.js"], cwd=ROOT, capture_output=True, text=True).stdout
        added = [l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
        removed = [l[1:] for l in diff.splitlines() if l.startswith("-") and not l.startswith("---")]
        code_added = [re.sub(r"\s//\s.*$", "", l) for l in added if not l.strip().startswith("//")]
        check("no new web address, network call or storage in the code added", not any(re.search(r"https?:|fetch\(|XMLHttpRequest|localStorage|sessionStorage|indexedDB|WebSocket|sendBeacon", l) for l in code_added if "w3.org/2000/svg" not in l),
              [l for l in code_added if "http" in l][:2])
        check("nothing was added that writes page text from variables (no innerHTML, insertAdjacentHTML, outerHTML, eval)",
              not any(re.search(r"innerHTML|insertAdjacentHTML|outerHTML|document\.write|eval\(|new Function", l) for l in [l for l in code_added if re.sub(r"(['\"]).*?\1", "", l).strip() not in {re.sub(r"(['\"]).*?\1", "", r).strip() for r in removed}]))   # v59: a line that only had its words changed is not new code
        # It checks the lines this version added (a diff against main), so it only means something while this is the newest
        # version (as George did for v45's Settings check). Later changes may need the brand name Citadel in their code.
        if page.evaluate("APP_VERSION") in ('v43',):
            check("no Games Workshop word in anything added", not [l for l in added if GW_WORDS.search(l)], [l for l in added if GW_WORDS.search(l)][:2])
        else:
            print("SKIP (a later version is newest): no Games Workshop word in anything added")
        drill_code = app[app.index("function appendWheelDrill("):app.index("function appendColourWheel(")]
        check("the drill-down code reuses WHEEL, wheelSlicePath and buildWheelDetail (no second copy of the groups or of the paint lists)",
              all(w in drill_code for w in ("WHEEL_ZOOM_FILL[seg.key]", "wheelSlicePath(", "buildWheelDetail(door, seg")) and "wheelSub(" not in drill_code and "wheelPlace(" not in drill_code and "buildIdeaItem(" not in drill_code,
              [w for w in ("wheelSlicePath(", "buildWheelDetail(door, seg") if w not in drill_code])
        check("the groups come from the same placing rules (wheelPlace/wheelSub are unchanged; no copy of them)", app.count("function wheelSub(") == 1 and app.count("function wheelPlace(") == 1 and app.count("const WHEEL = [") == 1)
        check("the drill-down code has no network code, no storage, no innerHTML and no links",
              not re.search(r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|localStorage|sessionStorage|innerHTML|insertAdjacentHTML|outerHTML|href|createElement\(.a.\)", re.sub(r"(?m)\s//.*$", "", drill_code)))

        # ---------- 2. The top of the wheel ----------
        print("\n--- 2. The top of the wheel ---")
        open_comp(page)
        check("at the start nothing is drilled into: ten slices, no group segments, no detail, no Back button",
              page.locator("#cmp-wheel path.wheel-seg").count() == 10 and page.locator(".wheel-sub-seg").count() == 0 and page.locator("#cmp-wheel-detail").count() == 0 and page.locator("#cmp-wheel-back").count() == 0 and state(page)["zoom"] == "")
        check("the hint line is unchanged: Tap a colour to see what's in it", page.inner_text("#cmp-wheel-hint") == "Tap a colour to see what's in it", page.inner_text("#cmp-wheel-hint"))
        labels = page.evaluate("() => Object.fromEntries([...document.querySelectorAll('#cmp-wheel path.wheel-seg')].map(e => [e.dataset.wheel, e.getAttribute('aria-label')]))")
        check("each of the six colours says it opens its groups; the four grey-centre slices do not",
              all(labels[k].endswith(", opens its groups") and re.match(rf"{LABEL[k]}, \d+ paints?, you own \d+, opens its groups$", labels[k]) for k in HUES) and all("opens" not in labels[k] for k in CENTRE), labels)

        # ---------- 3. All 18 groups, by tap ----------
        print("\n--- 3. All 18 groups, by tap ---")
        names_ok, seg_ok, open_ok, only_ok, close_ok = [], [], [], [], []
        for hue in HUES:
            load(page, paints=PAINTS)
            open_comp(page)
            zoom(page, hue)
            segs = page.evaluate(SEGS_JS)
            st = state(page)
            check(f"{hue}: tapping the colour redraws the picture as its three groups, with the three names from the lists, in order",
                  st["zoom"] == hue and [s["text"] for s in segs] == [lab for _, lab in GROUPS[hue]] and [s["key"] for s in segs] == [f"{hue}/{k}" for k, _ in GROUPS[hue]], (st, segs))
            check(f"{hue}: the ring of six and the grey centre are gone from the picture, and the hint names the colour",
                  page.locator("#cmp-wheel path.wheel-seg").count() == 0 and page.inner_text("#cmp-wheel-hint") == f"{LABEL[hue]}: tap a group to see its paints")
            check(f"{hue}: nothing opens under the picture until a group is tapped", page.locator("#cmp-wheel-detail").count() == 0 and st["group"] == "" and st["wheel"] == "")
            check(f"{hue}: the three segments are different colours, and each name has a chip of its segment's colour", len({s["fill"] for s in segs}) == 3 and all(s["fill"] == s["chip"] for s in segs), segs)
            for sk, label in GROUPS[hue]:
                tag = f"{hue}/{label}"
                seg = next(s for s in page.evaluate(SEGS_JS) if s["key"] == f"{hue}/{sk}")
                expected = expected_group(page, hue, sk)
                owned = sum(1 for e in expected if e["origin"] == 0)
                n = len(expected)
                aria_ok = seg["aria"] == f"{LABEL[hue]}, {label}, {n} paint{'' if n == 1 else 's'}, you own {owned}" and seg["role"] == "button" and seg["tab"] == "0" and seg["pressed"] == "false"
                seg_ok.append((tag, aria_ok, seg["aria"]))
                tap_group(page, hue, sk)
                det = page.evaluate(DETAIL_JS)
                st = state(page)
                shown_names = {e["name"] for e in expected if e["origin"] < 2}
                rows = [r["name"] for r in det["rows"]] if det else []
                open_ok.append((tag, bool(det) and det["title"] == f"{LABEL[hue]}: {label}" and st["group"] == sk and st["zoom"] == hue and page.get_attribute(f'[data-wheel-sub="{hue}/{sk}"]', "aria-pressed") == "true", det and det["title"]))
                # one heading when the group has paints of yours to show; none (and a plain line pointing at the other paints button) when it has only built-in ones
                heads_ok = bool(det) and not det["split"] and set(rows) <= {e["name"] for e in expected} and (
                    (len(det["headings"]) == 1 and det["headings"][0].startswith(label + " (") and shown_names <= set(rows)) if shown_names
                    else (det["headings"] == [] and rows == [] and "none of these in your palette" in page.inner_text("#cmp-wheel-detail")))
                only_ok.append((tag, heads_ok, (det and det["headings"], rows[:4])))
                tap_group(page, hue, sk)
                close_ok.append((tag, page.locator("#cmp-wheel-detail").count() == 0 and state(page)["group"] == "" and state(page)["zoom"] == hue
                                 and page.get_attribute(f'[data-wheel-sub="{hue}/{sk}"]', "aria-pressed") == "false", state(page)))
            back_button(page)
        bad = lambda xs: [x for x in xs if not x[1]]
        check("all 18 segments say colour, group, how many paints and how many you own, and are buttons you can focus (tabindex 0)", len(seg_ok) == 18 and not bad(seg_ok), bad(seg_ok)[:2])
        check("tapping each of the 18 groups opens it under the picture, titled Colour: Group, marked pressed", len(open_ok) == 18 and not bad(open_ok), bad(open_ok)[:2])
        check("each open group shows only its own paints under one heading (not the other two groups, no 'Split into' line)", len(only_ok) == 18 and not bad(only_ok), bad(only_ok)[:2])
        check("tapping each of the 18 groups again closes it (still drilled into its colour)", len(close_ok) == 18 and not bad(close_ok), bad(close_ok)[:2])
        # the same by tapping the NAME instead of the ring (the name is part of the button)
        load(page, paints=PAINTS)
        open_comp(page)
        zoom(page, "green")
        tap_group(page, "green", "sea", how="label")
        check("tapping the group's NAME (outside the ring) works like tapping its segment", state(page)["group"] == "sea" and page.locator("#cmp-wheel-detail").count() == 1, state(page))
        tap_group(page, "green", "green")
        check("tapping another group switches to it (one open at a time)", state(page)["group"] == "green" and page.evaluate(DETAIL_JS)["title"] == "Green: Greens")

        # ---------- 4. All 18 groups, by keyboard ----------
        print("\n--- 4. All 18 groups, by keyboard ---")
        kb_open, kb_close, kb_order, kb_back = [], [], [], []
        for hue in HUES:
            load(page, paints=PAINTS)
            open_comp(page)
            into_view(page)
            page.focus(f'[data-wheel="{hue}"]')
            page.keyboard.press("Enter")
            wait(page)
            kb_order.append((hue, "first", active(page)["ws"] == f"{hue}/{GROUPS[hue][0][0]}", active(page)))
            for i, (sk, label) in enumerate(GROUPS[hue]):
                if i:
                    page.keyboard.press("Tab")
                    wait(page, 40)
                kb_order.append((hue, sk, active(page)["ws"] == f"{hue}/{sk}", active(page)))
                key = "Enter" if i % 2 == 0 else " "
                page.keyboard.press(key)
                wait(page)
                det = page.evaluate(DETAIL_JS)
                kb_open.append((f"{hue}/{label} ({'Enter' if key == 'Enter' else 'Space'})", bool(det) and det["title"] == f"{LABEL[hue]}: {label}" and state(page)["group"] == sk and active(page)["ws"] == f"{hue}/{sk}", det and det["title"]))
                page.keyboard.press(key)
                wait(page)
                kb_close.append((f"{hue}/{label}", page.locator("#cmp-wheel-detail").count() == 0 and state(page)["group"] == "" and active(page)["ws"] == f"{hue}/{sk}", state(page)))
            page.keyboard.press("Tab")
            wait(page, 40)
            kb_order.append((hue, "back disc", active(page)["back"] == "1", active(page)))
            page.keyboard.press("Tab")
            wait(page, 40)
            kb_order.append((hue, "back button", active(page)["id"] == "cmp-wheel-back", active(page)))
            page.keyboard.press("Shift+Tab")
            page.keyboard.press("Enter")
            wait(page)
            kb_back.append((hue, state(page)["zoom"] == "" and active(page)["w"] == hue and page.locator(".wheel-sub-seg").count() == 0 and page.locator("#cmp-wheel path.wheel-seg").count() == 10, (state(page), active(page))))
        check("Enter on each of the six colours drills in and puts the focus on its first group", all(x[2] for x in kb_order if x[1] == "first"), [x for x in kb_order if x[1] == "first" and not x[2]][:2])
        check("Tab goes through the three groups in order, then the round Back button, then the Back button, for every colour", all(x[2] for x in kb_order), [x for x in kb_order if not x[2]][:2])
        check("every one of the 18 groups opens from the keyboard (Enter for the first and third, Space for the second)", len(kb_open) == 18 and not bad(kb_open), bad(kb_open)[:2])
        check("every one of the 18 groups closes from the keyboard and the focus stays on it", len(kb_close) == 18 and not bad(kb_close), bad(kb_close)[:2])
        check("Enter on the round Back button goes back to the whole wheel and the focus returns to the colour you drilled into", len(kb_back) == 6 and not bad(kb_back), bad(kb_back)[:2])

        # ---------- 5. The detail list ----------
        print("\n--- 5. The detail list for a group ---")
        load(page, paints=PAINTS)
        open_comp(page)
        copy_spy(page)
        zoom(page, "blue")
        tap_group(page, "blue", "navy")
        det = page.evaluate(DETAIL_JS)
        navy = expected_group(page, "blue", "navy")
        check("Navy and deep blue: your own paints are listed first and say You own this, dark to light",
              det["rows"][0]["name"] == "Deep Test Blue" and det["rows"][0]["tag"] == "You own this" and det["headings"] == [f"Navy and deep blue ({sum(1 for e in navy if e['origin'] < 2)})"], (det["rows"][:2], det["headings"]))
        tap_group(page, "blue", "blue")
        det = page.evaluate(DETAIL_JS)
        mine = [r for r in det["rows"]]
        check("Blues: yours first, then your wishlist paint (marked On your shopping list; v62: the empty one no longer is), never the built-in ones until asked",
              [r["name"] for r in mine][:1] == ["Mid Test Blue"] and {r["name"]: r["tag"] for r in mine}.get("Wish Blue") == "On your shopping list" and {r["name"]: r["tag"] for r in mine}.get("Empty Blue") == "In your palette, not owned",   # v62: only Wishlist is on the list now
              {r["name"]: r["tag"] for r in mine})
        others = page.locator("#cmp-wheel-others")
        check("a Show other paints button counts only this group's built-in paints", others.count() == 1 and re.match(r"Show other paints \(\d+\)$", others.inner_text()) is not None
              and int(re.search(r"\((\d+)\)", others.inner_text()).group(1)) == sum(1 for e in expected_group(page, "blue", "blue") if e["origin"] == 2), others.inner_text())
        others.click()
        wait(page)
        # v63: within the built-in paints, popular ranges come before other brands (chunk 3.3), so the sort key has that step too
        order = page.evaluate("() => wheelItems().filter(x => x.at.seg === 'blue' && x.at.sub === 'blue').map(x => [x.origin, wheelPopular(x), x.at.L, x.paint.name])")
        want = [n for _, _, _, n in sorted(order, key=lambda x: (x[0], x[1], x[2], x[3].lower()))]
        shown8 = [r["name"] for r in page.evaluate(DETAIL_JS)["rows"]]
        check("with the others shown, the first paints run owned first, then dark to light", shown8 == want[:len(shown8)] and len(shown8) >= 8, (shown8[:5], want[:5]))
        more = page.locator("#cmp-wheel-more-blue")
        total = len(order)
        check("a long group shows 'Show all N' for exactly this group's N paints, and aria-expanded is false", more.count() == 1 and more.inner_text() == f"Show all {total}" and more.get_attribute("aria-expanded") == "false", more.inner_text() if more.count() else None)
        more.click()
        wait(page)
        check("Show all N lists all N, and the button turns into Show fewer", len(page.evaluate(DETAIL_JS)["rows"]) == total and page.inner_text("#cmp-wheel-more-blue") == "Show fewer", page.evaluate(DETAIL_JS)["headings"])
        page.click("#cmp-wheel-more-blue")
        wait(page)
        check("Show fewer puts them away again", len(page.evaluate(DETAIL_JS)["rows"]) < total)
        into_view(page)
        page.locator("#cmp-wheel-detail .share-row button").first.scroll_into_view_if_needed()
        page.locator("#cmp-wheel-detail .share-row button").first.click()
        wait(page, 250)
        copied = page.evaluate("() => window.__copied")
        check("Copy as text copies this group's list: its title, the colour's description and the paints, as plain text", bool(copied) and copied.startswith("Blue: Blues") and "Mid Test Blue" in copied and "<" not in copied.replace("Save into", ""), (copied or "")[:120])
        ids = page.evaluate("() => { const all = [...document.querySelectorAll('[id]')].map(e => e.id); return all.filter((x, i) => all.indexOf(x) !== i); }")
        check("no id appears twice on the page with a group open", not ids, ids)

        # ---------- 6. The way back up ----------
        print("\n--- 6. The way back up ---")
        def whole_again(hue):
            s = state(page)
            return s["zoom"] == "" and s["group"] == "" and s["paint"] == "" and page.locator(".wheel-sub-seg").count() == 0 and page.locator("#cmp-wheel-detail").count() == 0 and page.locator("#cmp-wheel path.wheel-seg").count() == 10 and active(page)["w"] == hue
        ways = []
        for way in ("the round Back button (tap)", "the Back to all colours button", "Escape", "Escape from a group's paints open"):
            load(page, paints=PAINTS)
            open_comp(page)
            zoom(page, "purple")
            if way.endswith("open"):
                tap_group(page, "purple", "violet")
            if way.startswith("the round"):
                page.click("#cmp-wheel .wheel-back-disc")
            elif way.startswith("the Back to"):
                page.click("#cmp-wheel-back")
            else:
                page.focus('[data-wheel-sub="purple/violet"]')
                page.keyboard.press("Escape")
            wait(page)
            ways.append((way, whole_again("purple") and live(page) == "Back to all colours.", (state(page), live(page), active(page))))
        check("all four ways back (the round button, the Back button, Escape, Escape with a group open) return to the whole wheel, clear everything and put the focus on the colour",
              not bad(ways), bad(ways)[:2])
        load(page, paints=PAINTS)
        open_comp(page)
        zoom(page, "red")
        tap_group(page, "red", "red")
        page.click("#cmp-wheel-back")
        wait(page)
        zoom(page, "red")
        check("going back and drilling in again starts with no group open", state(page)["group"] == "" and page.locator("#cmp-wheel-detail").count() == 0)
        check("the round Back button is big enough to tap (at least 44 px) and says Back to all colours", page.evaluate(GEOMETRY_JS)["disc"]["w"] >= 44 and page.get_attribute("#cmp-wheel [data-wheel-back]", "aria-label") == "Back to all colours")

        # ---------- 7. Kept while the app is open ----------
        print("\n--- 7. The open state survives leaving the tab ---")
        load(page, paints=PAINTS)
        open_comp(page)
        zoom(page, "green")
        tap_group(page, "green", "sea")
        for tab in ("dashboard", "units", "recipes", "settings"):
            blur(page)
            page.click(f'nav button[data-tab="{tab}"]')
            wait(page, 120)
            open_comp(page)
            st = state(page)
            det = page.evaluate(DETAIL_JS)
            check(f"after visiting {tab} and coming back: still drilled into green with Sea green and mint open, picture and paints as they were",
                  st["zoom"] == "green" and st["group"] == "sea" and det and det["title"] == "Green: Sea green and mint" and page.get_attribute('[data-wheel-sub="green/sea"]', "aria-pressed") == "true" and page.locator(".wheel-sub-seg").count() == 3, (st, det and det["title"]))
        check("leaving only the picture drilled in (no group open) is kept too", (lambda: (tap_group(page, "green", "sea"), blur(page), page.click('nav button[data-tab="dashboard"]'), wait(page, 100), open_comp(page), state(page)["zoom"] == "green" and state(page)["group"] == "" and page.locator(".wheel-sub-seg").count() == 3)[-1])())
        page.reload()
        page.wait_for_function("() => typeof APP_VERSION === 'string'")
        leave_launch(page)   # U4b: tap through the start page
        wait(page, 300)
        open_comp(page)
        check("after the app is closed and opened again it starts at the whole wheel (like the other Compendium picks)", state(page)["zoom"] == "" and page.locator(".wheel-sub-seg").count() == 0 and page.locator("#cmp-wheel path.wheel-seg").count() == 10)

        # ---------- 8. The grey centre ----------
        print("\n--- 8. The grey centre is unchanged ---")
        load(page, paints=PAINTS)
        open_comp(page)
        centre_ok = []
        for key in CENTRE:
            into_view(page)
            page.click(f'[data-wheel="{key}"]')
            wait(page)
            det = page.evaluate(DETAIL_JS)
            centre_ok.append((key, bool(det) and det["title"] in ("Whites", "Greys", "Blacks", "Metallics") and len(det["headings"]) >= 1 and page.locator(".wheel-sub-seg").count() == 0 and page.locator("#cmp-wheel path.wheel-seg").count() == 10 and state(page)["wheel"] == key and state(page)["zoom"] == "", det and det["title"]))
            page.click(f'[data-wheel="{key}"]')
            wait(page)
            centre_ok.append((key + " closes", page.locator("#cmp-wheel-detail").count() == 0 and state(page)["wheel"] == "", state(page)))
        check("each of whites, greys, blacks and metallics still opens all its groups under the unchanged picture, and a second tap closes it", not bad(centre_ok), bad(centre_ok)[:2])
        page.focus('[data-wheel="white"]')
        page.keyboard.press("Enter")
        wait(page)
        check("the grey centre still works from the keyboard", state(page)["wheel"] == "white")

        # ---------- 9. Shopping list ----------
        print("\n--- 9. The shopping list inside the new group lists ---")
        load(page, paints=h.JUST_BLUE)
        open_comp(page)
        zoom(page, "blue")
        tap_group(page, "blue", "blue")
        check("a paint row in a group list is a button; tapping it opens the matching-colours panel under it (as before)", page.locator("#cmp-wheel-detail button.idea-link").count() >= 1, page.locator("#cmp-wheel-detail button.idea-link").count())
        h.open_row(page, "Probe Blue")
        check("the panel opens inside the group list and the paint is remembered as the open one", page.locator("#cmp-paint-panel").count() == 1 and state(page)["paint"] != "")
        rows0 = h.prows(page)
        first = next(r["name"] for r in rows0 if r["hasFold"])
        h.open_fold(page, 0)
        page.click("#cmp-paint-panel .shop-more .shop-add button")
        wait(page, 250)
        src = next((p.get("shopFrom") for p in h.stored_paints(page) if p["name"] == first), "missing")
        check("Add in that panel records Compendium: Colour wheel, Blue on the one paint (the part the colour wheel is in, as before)", src == ["Compendium: Colour wheel, Blue"], src)
        check("the paint's row in the panel now says On your shopping list straight away and the basket count follows",
              next(r["tag"] for r in h.prows(page) if r["name"] == first) == "On your shopping list" and page.evaluate("() => { const b = document.getElementById('basket-button'); return !b.classList.contains('hidden') && b.textContent.trim(); }") not in ("", False))
        page.click("#toast-undo") if page.locator("#toast-undo:not(.hidden)").count() else None
        wait(page, 250)
        check("Undo takes it off the list again, and the tag goes back", next(r["tag"] for r in h.prows(page) if r["name"] == first) != "On your shopping list")
        tap_group(page, "blue", "blue")
        check("closing the group closes its paint panel too (nothing stale is kept)", page.locator("#cmp-paint-panel").count() == 0 and state(page)["paint"] == "")
        # wishlist / empty paints in other groups carry the marker, owned ones never
        load(page, paints=PAINTS)
        open_comp(page)
        zoom(page, "blue")
        tap_group(page, "blue", "blue")
        tags = {r["name"]: r["tag"] for r in page.evaluate(DETAIL_JS)["rows"]}
        check("inside a group list: wishlist paints say On your shopping list (v62: empty ones no longer do), owned paints still say You own this",
              tags.get("Wish Blue") == "On your shopping list" and tags.get("Empty Blue") == "In your palette, not owned" and   # v62: only Wishlist is on the list now
               tags.get("Mid Test Blue") == "You own this", tags)
        page.click("#cmp-wheel-back")
        wait(page)
        h.tap(page, "orange")
        # v73 (chunk 4.3): buildShopFoldout is left out of this list, because it gained one option (the Mentor rows have their own Add button).
        check("the shopping-list code was not touched (addToShoppingList, noteShopSource, shopListTag, watchShopTag and the shop table are not in the diff)",
              not any(re.search(r"function (addToShoppingList|noteShopSource|shopListTag|watchShopTag|onShoppingList|updateShopFoldouts)|const SHOPS", l) for l in added))

        # ---------- 10. Screen reader ----------
        print("\n--- 10. Screen reader ---")
        load(page, paints=PAINTS)
        open_comp(page)
        region = page.evaluate("() => { const e = document.getElementById('wheel-live'); return { role: e.getAttribute('role'), live: e.getAttribute('aria-live'), outside: !document.getElementById('compendium-body').contains(e), text: e.textContent }; }")
        check("a polite live region sits outside the Compendium's body (so redrawing does not remove it) and starts empty", region == {"role": "status", "live": "polite", "outside": True, "text": ""}, region)
        zoom(page, "red")
        check("drilling in is announced: the colour, its three groups and how to go back", live(page) == "Red. 3 groups: deep reds, reds and pinks. Tap a group to see its paints, or Back to return to all colours.", live(page))
        tap_group(page, "red", "pink")
        check("opening a group is announced with its colour and name", live(page) == "Red, Pinks. Its paints are listed below the picture.", live(page))
        tap_group(page, "red", "pink")
        check("closing a group is announced", live(page) == "Pinks closed.", live(page))
        page.click("#cmp-wheel-back")
        check("going back is announced", live(page) == "Back to all colours.", live(page))
        zoom(page, "orange")
        check("the drilled-down picture is a group with a name that says which colour and how many groups, and the paint rows beneath keep their own buttons",
              page.get_attribute("#cmp-wheel", "aria-label") == "Orange colour wheel, 3 groups" and page.get_attribute("#cmp-wheel", "role") == "group")
        check("the three group segments and the Back button are the only tab stops in the picture",
              page.evaluate("() => [...document.querySelectorAll('#cmp-wheel [tabindex]')].map(e => e.dataset.wheelSub || (e.dataset.wheelBack ? 'back' : '?'))") == ["orange/brown", "orange/orange", "orange/peach", "back"])

        # ---------- 11. Phones and looks ----------
        print("\n--- 11. Phones: 360, 375, 390 and 400 px, dark and light ---")
        for appearance in ("dark", "light"):
            for width in (360, 375, 390, 400):
                page.set_viewport_size({"width": width, "height": 844})
                load(page, paints=PAINTS, settings={"appearance": appearance})
                open_comp(page)
                bad_geo, fonts, hits = [], [], []
                for hue in HUES:
                    zoom(page, hue)
                    tap_group(page, hue, GROUPS[hue][0][0])
                    g = page.evaluate(GEOMETRY_JS)
                    boxes = g["labels"]
                    inside = all(b["l"] >= g["svg"]["l"] - 0.5 and b["r"] <= g["svg"]["r"] + 0.5 and b["t"] >= g["svg"]["t"] - 0.5 and b["b"] <= g["svg"]["b"] + 0.5 for b in boxes)
                    apart = not any(overlap(boxes[i], boxes[j]) for i in range(3) for j in range(i + 1, 3))
                    outside = all(b["dist"] >= g["R"] - 0.5 for b in boxes)
                    fine = g["svg"]["l"] >= 0 and g["svg"]["r"] <= g["vw"] and no_sideways(page)
                    if not (inside and apart and outside and fine):
                        bad_geo.append((hue, inside, apart, outside, fine))
                    fonts.append(min(b["font"] for b in boxes))
                    hits.append(min(min(b["hitW"], b["hitH"]) for b in boxes))
                    hits.append(min(min(b["pathW"], b["pathH"]) for b in boxes))
                    hits.append(g["disc"]["w"])
                    page.click("#cmp-wheel-back")
                    wait(page, 80)
                tag = f"{appearance} {width}px"
                check(f"{tag}: for all six colours the names sit outside the ring, inside the picture, none touch each other or the ring, and nothing slides sideways", not bad_geo, bad_geo[:2])
                check(f"{tag}: the names are at least 12.5 px on screen (smallest {round(min(fonts), 1)})", min(fonts) >= 12.5, fonts)
                check(f"{tag}: every group's tap area (its name and its segment) and the Back button are at least 44 px across (smallest {round(min(hits), 1)})", min(hits) >= 44, hits)
                zoom(page, "blue")
                tap_group(page, "blue", "navy")
                col = page.evaluate("""() => { const bg = getComputedStyle(document.querySelector('#view-compendium .card')).backgroundColor, out = {};
                    const pairs = [['hint', '#cmp-wheel-hint'], ['label', '#cmp-wheel .wheel-sub-seg[aria-pressed="false"] .wheel-label'], ['back disc', '#cmp-wheel .wheel-back-text'],
                                   ['title', '#cmp-wheel-detail h3'], ['about', '#cmp-wheel-detail > .hint'], ['count', '#cmp-wheel-detail .idea-label'], ['group', '.wheel-sub'], ['name', '#cmp-wheel-detail .idea-name'],
                                   ['copy', '#cmp-wheel-detail .share-row button'], ['back button', '#cmp-wheel-back']];
                    for (const [k, s] of pairs) { const el = document.querySelector(s); if (el) out[k] = [getComputedStyle(el).fill !== 'none' && el.namespaceURI.endsWith('svg') ? getComputedStyle(el).fill : getComputedStyle(el).color, k === 'back disc' ? getComputedStyle(document.querySelector('#cmp-wheel .wheel-back-disc')).fill : bg]; }
                    const open = document.querySelector('#cmp-wheel .wheel-sub-seg[aria-pressed="true"] path'), shut = document.querySelector('#cmp-wheel .wheel-sub-seg[aria-pressed="false"] path');
                    out.__ring = [getComputedStyle(open).stroke, bg, getComputedStyle(shut).stroke, getComputedStyle(open).strokeWidth];
                    out.__openLabel = [getComputedStyle(document.querySelector('#cmp-wheel .wheel-sub-seg[aria-pressed="true"] .wheel-label')).fill, bg];
                    return out; }""")
                low = {k: round(contrast(rgb(v[0]), rgb(v[1])), 2) for k, v in col.items() if not k.startswith("__") and contrast(rgb(v[0]), rgb(v[1])) < 4.5}
                check(f"{tag}: the hint, group names, Back, title, description, count, rows and buttons all have contrast of at least 4.5 (checked {len([k for k in col if not k.startswith('__')])})", not low and len(col) >= 10, (low, len(col)))
                check(f"{tag}: the open group's outline can be seen (contrast 3 or more against the card), differs from the shut ones, and its name turns accent-coloured with contrast 4.5 or more",
                      contrast(rgb(col["__ring"][0]), rgb(col["__ring"][1])) >= 3 and col["__ring"][0] != col["__ring"][2] and contrast(rgb(col["__openLabel"][0]), rgb(col["__openLabel"][1])) >= 4.5, col["__ring"])
                if width in (360, 400):
                    shot(page, f"v43-wheel-open-{appearance}-{width}.png")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 12. Hostile text ----------
        print("\n--- 12. Hostile text ---")
        evil = PAINTS + [P(90, HOSTILE, "#2244aa", brand=HOSTILE_BRAND), P(91, HOSTILE + " Pink", "#f0a0c0", brand=HOSTILE_BRAND)]
        load(page, paints=evil)
        open_comp(page)
        copy_spy(page)
        zoom(page, "blue")
        tap_group(page, "blue", "blue")
        check("a hostile paint name and brand never become markup in the drilled-down wheel and its list, and no script runs",
              page.locator("#view-compendium img, #view-compendium script, #view-compendium b, #view-compendium iframe").count() == 0 and page.evaluate("() => window.__pwned") is None)
        rows = [r["name"] for r in page.evaluate(DETAIL_JS)["rows"]]
        check("the hostile name is shown as plain text, tags and all, inside the group list", HOSTILE in rows, rows)
        h.open_row(page, HOSTILE)
        check("opening its matching-colours panel shows the name as text too", page.locator("#cmp-paint-panel img, #cmp-paint-panel script, #cmp-paint-panel b").count() == 0 and HOSTILE in page.inner_text("#cmp-paint-panel-title"))
        page.locator("#cmp-wheel-detail > .share-row button").first.click() if page.locator("#cmp-wheel-detail > .share-row button").count() else None
        wait(page, 250)
        copied = page.evaluate("() => window.__copied")
        check("Copy as text keeps the hostile name as literal text", bool(copied) and HOSTILE in copied, (copied or "")[:100])
        live_text = page.evaluate("() => document.getElementById('wheel-live').textContent")
        check("the spoken announcements never contain a paint name (only colour and group names, which we wrote)", "<" not in live_text and HOSTILE not in live_text)
        words = page.evaluate("""() => { const c = document.getElementById('cmp-wheel-block').cloneNode(true); c.querySelectorAll('.idea-name').forEach(e => e.remove());
            return c.innerText + ' ' + [...c.querySelectorAll('[aria-label], title')].map(e => e.getAttribute('aria-label') || e.textContent).join(' '); }""")
        check("nothing we wrote in the drilled-down wheel names a Games Workshop game, faction, scheme, paint or product", not GW_WORDS.search(words), GW_WORDS.search(words) and GW_WORDS.search(words).group(0))

        # ---------- 13. Nothing else changed ----------
        print("\n--- 13. Nothing else changed ---")
        load(page, paints=PAINTS)
        for tab, view in [("dashboard", "view-dashboard"), ("units", "view-units"), ("recipes", "view-recipes"), ("settings", "view-settings"), ("compendium", "view-compendium")]:
            blur(page)
            page.click(f'nav button[data-tab="{tab}"]')
            wait(page, 150)
            check(f"the {tab} tab still opens", page.locator(f"#{view}").is_visible())
        open_comp(page)
        parts = page.evaluate("() => [...document.querySelectorAll('#compendium-body .compendium-folds > .fold > h3 button span:first-child')].map(e => e.textContent)")
        check("the six folding parts under the wheel are all still there (v71: Ask the Mentor first)", parts == ["Ask the Mentor", "Colour ideas", "Colours you've used", "Colour plans", "Detail recipes", "Basing tips"], parts)
        zoom(page, "red")
        check("the six folding parts still work while the wheel is drilled into a colour",
              page.evaluate("() => [...document.querySelectorAll('#compendium-body .compendium-folds > .fold')].length") == 6 and page.locator("#cmp-fold-starter-button").count() == 1)
        page.click("#cmp-wheel-back")
        wait(page)
        check("no network requests were made (offline app)", not [u for u in requests if not u.startswith(("http://127.0.0.1", "http://localhost", "data:", "blob:"))], [u for u in requests if not u.startswith(("http://127.0.0.1", "http://localhost"))][:3])
        offline = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", offline=False)
        page2 = offline.new_page()
        load(page2, paints=PAINTS)
        offline.set_offline(True)
        page2.click('nav button[data-tab="compendium"]')
        wait(page2, 200)
        page2.click('[data-wheel="green"]')
        wait(page2)
        page2.mouse.click(*ring_point(page2, 1))
        wait(page2)
        check("with the network switched off, drilling in and opening a group still works", state(page2)["zoom"] == "green" and state(page2)["group"] == "green" and page2.locator("#cmp-wheel-detail").count() == 1, state(page2))
        offline.close()
        check("no page errors and no pop-up boxes", not errors and not [d for d in dialogs if d.strip()], (errors[:2], dialogs[:2]))
        browser.close()

if __name__ == "__main__":
    main()
    passed = sum(results)
    print(f"\n{passed}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)
