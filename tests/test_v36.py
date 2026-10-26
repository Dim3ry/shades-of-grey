"""v36 tests for Minifolio (Compendium 2): a colour wheel at the top of the Compendium tab (Pro preview).

What changed: the Compendium now starts with a round SVG wheel. The outer ring has red, orange, yellow, green, blue and purple. The grey
circle in the middle has four slices: whites, greys, blacks, metallics. A hint line sits above it ("Tap a colour to see what's in it").
Tapping a slice opens the detail BELOW the wheel: a short description, then the paints in it (yours first and marked, then dark to light).
Browns sit under orange, bone under yellow, and metallics are split into gold, silver and bronze. It reuses the Compendium's shared
pieces (buildIdeaItem rows, buildShareRow, compendiumBaseChoices, the door). No new files, no libraries, works offline.

Checks:
1. Versions, the v36 Updates entry, wiring (still six script files, the same twelve offline files, data files and colour.js unchanged,
   security policy untouched), Help names the wheel, the new code has no network code, no storage, no innerHTML, no links.
2. Shape of the wheel: hint above it, six ring slices in order and four centre slices in order, the right angles, drawn as SVG paths.
3. Where paints land (the placing rules): reds, pinks, oranges, browns, yellows, bone, greens, teals, blues, purples, whites, greys,
   blacks, metallics (gold, silver, bronze) and the ones that must NOT land there (unknown colour, basing material, "Bronze Green").
4. Tapping: nothing open at the start, tap opens the detail below the wheel, tap again closes, another tap switches, keyboard works,
   the open slice is marked, the choice is kept while the app is open and not after a reload.
5. The lists: yours first and marked, then your wishlist and palette, then dark to light; browns under orange, bone under yellow,
   gold/silver/bronze under metallics; the other paints stay behind one button, with the right count; counts are honest.
6. Reuse, not copy: the rows are the shared rows, Copy as text is the shared share row, no second copy of the builders, the ids are unique.
7. Copy as text for the open part (the words, plain text only, no Save into a new recipe for a long list).
8. Text scan: nothing we wrote for the wheel names a Games Workshop game, faction, scheme, paint or product, or a brand or shop.
9. Hostile text (text-injection test): paint and brand names full of HTML never become markup in the wheel, the list or Copy as text.
10. Offline: no network requests, and it works with the network off.
11. Phone widths 360, 375, 390 and 400: the wheel fits, no sideways scroll, every slice can be tapped where you would tap it, and the
    centre slices are big enough (at least 44 px across), so the "four round buttons" fallback is not needed.
12. Dark and light at 390 and 360 px: contrast 4.5 or more on the text, 3 or more on the open slice's outline.
13. Nothing else changed: the rest of the Compendium, the other tabs, no pop-ups, no page errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, subprocess, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wheel_helpers as wh   # v43
from notice_watch import attach_notices
import test_v31 as t   # the helpers (loading the app, the palette, the colours) and the Games Workshop word lists
from combo_helpers import pick_combo   # v37 part 2: "Start from" is a search box now

SHOTS, ROOT = t.SHOTS, t.ROOT
read, load, blur, edit_recipe, open_panel = t.read, t.load, t.blur, t.edit_recipe, t.open_panel
shot, no_sideways, rgb, contrast = t.shot, t.no_sideways, t.rgb, t.contrast
rec, unit, HOSTILE, HOSTILE_BRAND = t.rec, t.unit, t.HOSTILE, t.HOSTILE_BRAND
GW_WORDS, GW_MORE = t.GW_WORDS, t.GW_MORE
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

BRAND_WORDS = re.compile(r"\b(citadel|vallejo|army painter|scale ?75|tamiya|games workshop|warhammer|amazon|ebay|etsy|shop|buy|store)\b", re.I)

def P(pid, name, colour, status="owned", brand="Test Paints", **extra):
    return dict({"id": pid, "brand": brand, "name": name, "colour": colour, "status": status}, **extra)

# A made-up palette that puts something in every part of the wheel (nothing here names a real paint).
WPAINTS = [
    P(1, "Deep Test Blue", "#0d2a5c"), P(2, "Mid Test Blue", "#3b6fb0"), P(3, "Pale Test Blue", "#a9c6ec"),
    P(4, "Wish Blue", "#1f4f9a", "wishlist"), P(5, "Empty Blue", "#2a5fa8", "empty"),
    P(6, "Test Orange", "#e8802a"), P(7, "Dark Brown Test", "#4a2d12"), P(8, "Light Brown Test", "#7b5230"), P(9, "Wish Orange", "#f09a3a", "wishlist"),
    P(10, "Test Yellow", "#e6c82e"), P(11, "Test Bone", "#d9cba4"),
    P(12, "Test Gold", "#c9a227"), P(13, "Test Silver", "#b8bec6"), P(14, "Test Copper", "#b4693a"),
    P(15, "Test Metallic", "#8d9299"), P(16, "Odd Shine", "#c8a06a", type="metallic"),
    P(17, "Test White", "#f4f6f8"), P(18, "Test Grey", "#8a9099"), P(19, "Test Black", "#0b0d10"),
    P(20, "Test Red", "#c1272d"), P(21, "Test Green", "#228b22"), P(22, "Test Purple", "#7b2d8b"),
    P(30, "Bronze Green", "#313a29"), P(31, "Unknown Colour", "#808080"), P(32, "Sand Material", "#c8b08a", type="material"),
]
COLOUR_OF = {p["name"]: p["colour"] for p in WPAINTS}

ROWS_JS = """(sel) => [...document.querySelectorAll(sel)].map(b => ({
    name: b.querySelector('.idea-name').childNodes[0].textContent, brand: (b.querySelector('.idea-name small') || {}).textContent || '',
    tag: b.querySelector('.idea-tag').textContent, why: b.querySelector('.idea-why').textContent,
    note: (b.querySelector('.idea-note') || {}).textContent || '', colour: b.querySelector('.swatch').style.getPropertyValue('--swatch') }))"""
# the detail as groups: [{ heading, rows: [...] }]
GROUPS_JS = """() => { const out = []; let cur = { heading: '', rows: [] }; out.push(cur);
    for (const el of document.querySelectorAll('#cmp-wheel-detail > h4.wheel-sub, #cmp-wheel-detail > ul.idea-list')) {
        if (el.tagName === 'H4') { cur = { heading: el.textContent, rows: [] }; out.push(cur); continue; }
        for (const b of el.querySelectorAll('.idea-static')) cur.rows.push({ name: b.querySelector('.idea-name').childNodes[0].textContent,
            tag: b.querySelector('.idea-tag').textContent, why: b.querySelector('.idea-why').textContent, note: (b.querySelector('.idea-note') || {}).textContent || '' }); }
    return out.filter(g => g.heading || g.rows.length); }"""
# everything WE wrote in the wheel part (paint names and brands are the user's or built-in names, so they are left out)
WHEEL_TEXT_JS = """() => { const c = document.getElementById('cmp-wheel-block').cloneNode(true);
    c.querySelectorAll('.idea-name').forEach(e => e.remove());
    return c.innerText + ' ' + [...c.querySelectorAll('[aria-label], title')].map(e => e.getAttribute('aria-label') || e.textContent).join(' '); }"""
KEYS = ["red", "orange", "yellow", "green", "blue", "purple", "white", "grey", "black", "metallic"]

def open_comp(page):
    blur(page)
    page.click('nav button[data-tab="compendium"]')
    page.wait_for_timeout(200)
    # v49: the page introduction sits behind a More info button; open it so the text can be read
    if page.get_attribute("#compendium-body > .more-info .more-info-button", "aria-expanded") == "false":
        page.click("#compendium-body > .more-info .more-info-button")
    # v37: the five parts under the wheel fold and start closed; open them so the rest of the Compendium can be checked as before
    for key in ["ideas", "history", "starter", "detail", "basing"]:
        if page.get_attribute(f"#cmp-fold-{key}-button", "aria-expanded") != "true":
            page.click(f"#cmp-fold-{key}-button")
    page.wait_for_timeout(100)

def tap(page, key):
    wh.tap(page, key)   # v43: a colour opens its groups first (see wheel_helpers.py); same meaning as before

def open_key(page):
    return page.evaluate("() => compendiumState.wheel")

def zoom_key(page):
    return page.evaluate("() => compendiumState.wheelZoom")

def part_groups(page, key):
    """The groups of a part as GROUPS_JS gives them. v43: the six colours open one group at a time, so for those each of the three groups is
    opened in turn and put together, which is the same list the whole colour used to show. The grey centre is read as it stands (tap it first)."""
    if key in wh.HUES:
        return [g for res in wh.open_each_group(page, key, lambda pg: pg.evaluate(GROUPS_JS)) for g in res]
    return page.evaluate(GROUPS_JS)

def copy_spy(page):
    page.evaluate("""() => { window.__copied = null;
        Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: (x) => { window.__copied = x; return Promise.resolve(); } } }); }""")

def copied(page):
    page.wait_for_timeout(200)
    return page.evaluate("() => window.__copied")

def place(page, colour, name="Plain", ptype=None):
    return page.evaluate("([c, n, ty]) => { const r = wheelPlace({ colour: c, name: n, type: ty || undefined }); return r ? r.seg + '/' + r.sub : null; }", [colour, name, ptype])

def tap_points(page):
    """Where a finger would land on each slice (the middle of the slice), in page pixels."""
    return page.evaluate("""() => { const r = document.getElementById('cmp-wheel').getBoundingClientRect(), k = r.width / 320, out = {};
        const at = (rad, deg) => [r.left + (160 + rad * Math.sin(deg * Math.PI / 180)) * k, r.top + (160 - rad * Math.cos(deg * Math.PI / 180)) * k];
        ['red', 'orange', 'yellow', 'green', 'blue', 'purple'].forEach((n, i) => out[n] = at(126, 60 * i));
        ['white', 'grey', 'black', 'metallic'].forEach((n, i) => out[n] = at(56, 90 * i + 45));
        return { points: out, scale: k, width: r.width, left: r.left, right: r.right }; }""")

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

        # ---------- 1. Versions and wiring ----------
        print("\n--- 1. Versions and wiring ---")
        load(page, paints=WPAINTS)
        html, app = read("index.html"), read("app.js")
        tags = re.findall(r'<script src="([^"]+)\?v=(\d+)"', html)
        check("the script files are the same six as before, in the same order",
              [n for n, _ in tags] == ["early.js", "colour.js", "schemes.js", "detail-recipes.js", "basing-tips.js", "app.js"], tags)
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v36')")
        joined = " ".join(entry["changes"]) if entry else ""
        if page.evaluate("['v36'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("the Updates entry says colour wheel, Compendium, Pro preview, You own this, Show other paints, gold, silver and bronze, offline and sends nothing anywhere",
                  all(w in joined for w in ["colour wheel", "Compendium", "Pro preview", "You own this", "Show other paints", "gold, silver and bronze", "offline", "sends nothing anywhere"]), joined[:300])
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'the Updates entry says colour wheel, Compendium, Pro preview, You own this, Show other pai')
        policy = re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]+)"', html)
        policy = policy.group(1) if policy else ""
        wheel_code = app[app.index("v36: THE COLOUR WHEEL"):app.index("function renderCompendium(")]
        check("the wheel code has no network code, no storage, no innerHTML, no links and no shop wording",
              not re.search(r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage|\beval\s*\(|new Function|insertAdjacentHTML|outerHTML|innerHTML|createElement\('a'\)|createElement\(\"a\"\)|href|affiliate|\bshop\b", wheel_code),
              [mm.group(0) for mm in re.finditer(r"(fetch|innerHTML|href|affiliate)[^\n]*", wheel_code)][:3])
        help_text = page.evaluate("() => document.getElementById('help-tabs').textContent")
        check("Help still names five tabs and now says the Compendium has a colour wheel", all(w in help_text for w in ["five tabs", "Compendium", "colour wheel", "without needing a recipe"]), help_text)
        check("the Pro preview label is still on the Compendium", page.locator("#view-compendium .pro-pill").inner_text() == "Pro preview")

        # ---------- 2. The shape of the wheel ----------
        print("\n--- 2. The shape of the wheel ---")
        open_comp(page)
        check("the hint line is exactly: Tap a colour to see what's in it", page.inner_text("#cmp-wheel-hint") == "Tap a colour to see what's in it", page.inner_text("#cmp-wheel-hint"))
        order = page.evaluate("() => [...document.querySelectorAll('#compendium-body > *')].flatMap(e => e.classList.contains('more-info') ? [...e.querySelectorAll('.more-info-panel > *')] : [e]).map(e => e.id)")
        check("the wheel comes first in the tab (after the intro line), before the colour chooser", order[0] == "cmp-intro" and order[1] == "cmp-wheel-block" and order.index("cmp-wheel-block") < len(order) - 1, order[:5])
        inside = page.evaluate("() => [...document.getElementById('cmp-wheel-block').children].map(e => e.id || e.tagName.toLowerCase())")
        check("inside the wheel part: the hint, the picture, then the small caption (v53: behind More info)", inside[:3] == ["cmp-wheel-hint", "cmp-wheel", "div"] and page.evaluate("() => !!document.querySelector('#cmp-wheel-block > .more-info .wheel-caption')"), inside)   # v53: the caption sits behind More info
        check("the hint sits above the picture", page.evaluate("() => document.getElementById('cmp-wheel-hint').getBoundingClientRect().bottom <= document.getElementById('cmp-wheel').getBoundingClientRect().top + 0.5"))
        shape = page.evaluate("""() => { const s = document.getElementById('cmp-wheel');
            return { tag: s.tagName.toLowerCase(), ns: s.namespaceURI, viewBox: s.getAttribute('viewBox'), slices: [...s.querySelectorAll('path.wheel-seg')].map(e => e.dataset.wheel),
                     imgs: document.querySelectorAll('#cmp-wheel-block img, #cmp-wheel-block canvas, #cmp-wheel-block foreignObject').length,
                     refs: [...s.querySelectorAll('[href], [src], image, use')].length }; }""")
        check("it is one round SVG picture made of ten slices (no image file, no canvas, no outside references)", shape["tag"] == "svg" and shape["ns"].endswith("/svg") and len(shape["slices"]) == 10 and shape["imgs"] == 0 and shape["refs"] == 0, shape)
        check("the slices are the six ring colours in order and then whites, greys, blacks, metallics", shape["slices"] == KEYS, shape["slices"])
        geo = page.evaluate("""() => { const out = {};
            for (const e of document.querySelectorAll('#cmp-wheel path.wheel-seg')) { const b = e.getBBox(); const cx = b.x + b.width / 2, cy = b.y + b.height / 2;
                out[e.dataset.wheel] = { cx: Math.round(cx), cy: Math.round(cy), w: Math.round(b.width), h: Math.round(b.height) }; }
            return out; }""")
        ring_ok = geo["red"]["cy"] < 60 and geo["yellow"]["cx"] > 200 and geo["yellow"]["cy"] > 160 and geo["green"]["cy"] > 260 and geo["blue"]["cx"] < 120 and geo["blue"]["cy"] > 160 and geo["purple"]["cx"] < 100 and geo["purple"]["cy"] < 160
        check("the ring runs clockwise from the top: red at the top, then orange, yellow, green at the bottom, blue and purple on the left", ring_ok, geo)
        centre_ok = geo["white"]["cx"] > 160 and geo["white"]["cy"] < 160 and geo["grey"]["cx"] > 160 and geo["grey"]["cy"] > 160 and geo["black"]["cx"] < 160 and geo["black"]["cy"] > 160 and geo["metallic"]["cx"] < 160 and geo["metallic"]["cy"] < 160
        check("the middle is split in four: whites top right, greys bottom right, blacks bottom left, metallics top left", centre_ok, geo)
        check("every slice can be reached with a keyboard and says what it is (name, how many paints, how many you own)",
              page.evaluate("() => [...document.querySelectorAll('#cmp-wheel path.wheel-seg')].every(e => e.getAttribute('role') === 'button' && e.tabIndex === 0 && /you own \\d+/.test(e.getAttribute('aria-label')) && e.hasAttribute('aria-pressed'))"))
        check("the caption under the picture says what the middle is", "whites, greys, blacks and metallics" in page.inner_text("#cmp-wheel-block .wheel-caption"))
        shot(page, "v36-wheel-closed-390.png")

        # ---------- 3. Where paints land ----------
        print("\n--- 3. Where paints land ---")
        table = [("#c1272d", "Test Red", None, "red/red"), ("#ff69b4", "Test Pink", None, "red/pink"), ("#ff6a00", "Bright Orange", None, "orange/orange"),
                 ("#4a2d12", "Dark Brown", None, "orange/brown"), ("#84443a", "Red Brown", None, "orange/brown"), ("#7a4a1f", "Gold Brown", None, "orange/brown"),
                 ("#e6c82e", "Sun", None, "yellow/yellow"), ("#d9cba4", "Pale Bone", None, "yellow/bone"),
                 ("#228b22", "Forest", None, "green/green"), ("#5a5a28", "Dark Olive", None, "green/olive"), ("#313a29", "Bronze Green", None, "green/green"),
                 ("#2fb5a8", "Teal", None, "blue/blue"), ("#3b6fb0", "Mid Blue", None, "blue/blue"), ("#7b2d8b", "Deep Purple", None, "purple/violet"),
                 ("#ffffff", "Pure White", None, "white/neutral"), ("#e8eef2", "Snow", None, "white/cool"),
                 ("#8a9099", "Mid Grey", None, "grey/cool"), ("#0b0d10", "Near Black", None, "black/neutral"), ("#0b1220", "Dark Navy", None, "black/cool"),
                 ("#c9a227", "Pale Gold", None, "metallic/gold"), ("#b8bec6", "Steel Wool", None, "metallic/silver"), ("#b4693a", "Copper Pot", None, "metallic/bronze"),
                 ("#8d9299", "Test Metallic", None, "metallic/silver"), ("#c8a06a", "Odd Shine", "metallic", "metallic/bronze"), ("#6a6d73", "Iron Grey", None, "metallic/silver"),
                 ("#c75b12", "Iron Orange", None, "orange/orange"),
                 ("#808080", "Default Grey", None, None), ("#888888", "Basing Sand", "material", None), ("nonsense", "No Colour", None, None)]
        wrong = [(c, n, got, want) for c, n, ty, want in table if (got := place(page, c, n, ty)) != want]
        check(f"all {len(table)} test paints land where they should (reds and pinks, orange, browns, yellow, bone, greens, teals, blues, purples, whites, greys, blacks, gold, silver, bronze) and unknown colours and basing materials land nowhere", not wrong, wrong)
        check("a paint is placed by its colour, not by its name: the same name gives a different place for a different colour",
              place(page, "#228b22", "Blue Thing") == "green/green" and place(page, "#3b6fb0", "Green Thing") == "blue/blue")
        check("lighter reads lighter: the tone words go Very dark, Dark, Mid, Light, Very light",
              page.evaluate("() => [5, 30, 50, 70, 90].map(wheelTone)") == ["Very dark", "Dark", "Mid", "Light", "Very light"])

        # ---------- 4. Tapping ----------
        print("\n--- 4. Tapping ---")
        load(page, paints=WPAINTS)
        open_comp(page)
        check("nothing is open at the start: no detail and every slice shows not pressed", page.locator("#cmp-wheel-detail").count() == 0 and open_key(page) == ""
              and page.evaluate("() => [...document.querySelectorAll('#cmp-wheel path')].every(e => e.getAttribute('aria-pressed') === 'false')"))
        tap(page, "white")   # v43: the six colours now drill into groups (see test_v43.py); the grey centre still opens its list straight away
        check("tapping a grey-centre slice opens its detail", page.locator("#cmp-wheel-detail").count() == 1 and page.inner_text("#cmp-wheel-detail h3") == "Whites")
        below = page.evaluate("() => { const a = document.getElementById('cmp-wheel').getBoundingClientRect(), b = document.getElementById('cmp-wheel-detail').getBoundingClientRect(); return [a.bottom, b.top]; }")
        check("the detail opens BELOW the wheel and the wheel stays visible", below[1] >= below[0] - 0.5 and page.is_visible("#cmp-wheel"), below)
        check("the open slice says so (pressed) and the others do not",
              page.evaluate("() => [...document.querySelectorAll('#cmp-wheel path')].map(e => e.dataset.wheel + ':' + e.getAttribute('aria-pressed')).filter(x => x.endsWith('true'))") == ["white:true"])
        check("the focus stays on the slice you tapped", page.evaluate("() => document.activeElement && document.activeElement.dataset && document.activeElement.dataset.wheel") == "white")
        tap(page, "white")
        check("tapping the same slice again closes the detail", page.locator("#cmp-wheel-detail").count() == 0 and open_key(page) == "")
        for key in KEYS:
            tap(page, key)
            h = page.inner_text("#cmp-wheel-detail h3")
            about = page.inner_text("#cmp-wheel-detail > .hint")
            want = {"white": "Whites", "grey": "Greys", "black": "Blacks", "metallic": "Metallics"}.get(key, key.capitalize())
            check(f"{key}: opens a part called {want} (for the six colours, a group of it: Colour: Group, v43) with a short description (one to three short sentences)", (h == want or h.startswith(want + ": ")) and 40 < len(about) < 260 and 1 <= len(re.findall(r"[.!?](?:\s|$)", about)) <= 3, (h, about))
        tap(page, "grey")
        tap(page, "black")
        check("tapping another slice switches to it (only one part is open)", open_key(page) == "black" and page.locator("#cmp-wheel-detail").count() == 1 and page.inner_text("#cmp-wheel-detail h3") == "Blacks")
        page.evaluate("() => { compendiumState.wheel = ''; renderCompendium(); }")
        page.focus('[data-wheel="white"]')
        page.keyboard.press("Enter")
        page.wait_for_timeout(120)
        check("the keyboard works: Enter opens the focused slice", open_key(page) == "white")
        page.keyboard.press(" ")
        page.wait_for_timeout(120)
        check("and Space closes it again", open_key(page) == "")
        tap(page, "metallic")
        blur(page)
        page.click('nav button[data-tab="dashboard"]')
        page.wait_for_timeout(100)
        open_comp(page)
        check("the open part is kept while the app is open (go to another tab and back)", open_key(page) == "metallic" and page.inner_text("#cmp-wheel-detail h3") == "Metallics")
        page.reload()
        page.wait_for_function("() => typeof APP_VERSION === 'string'")
        page.wait_for_timeout(300)
        check("after closing and opening the app the wheel starts closed again (like the other Compendium picks)", open_key(page) == "" and page.locator("#cmp-wheel-detail").count() == 0)

        # ---------- 5. The lists ----------
        print("\n--- 5. The lists ---")
        load(page, paints=WPAINTS)
        open_comp(page)
        # v43: the blues are opened one group at a time (Navy, Blues, Sky), and read together
        reads = wh.open_each_group(page, "blue", lambda pg: {"groups": pg.evaluate(GROUPS_JS), "count": pg.inner_text("#cmp-wheel-detail .idea-label"),
                                                           "btn": pg.inner_text("#cmp-wheel-others") if pg.locator("#cmp-wheel-others").count() else None})
        groups = [g for r in reads for g in r["groups"]]
        names = [r["name"] for g in groups for r in g["rows"]]
        tags = [r["tag"] for g in groups for r in g["rows"]]
        whys = [r["why"] for g in groups for r in g["rows"]]
        heads = [g["heading"] for g in groups if g["heading"]]
        check("Blue first shows only your own palette (the other paints are behind a button): 5 blue paints of yours, in three groups (v37 part 2, opened one at a time since v43)",
              len(names) == 5 and heads == ["Navy and deep blue (1)", "Blues (3)", "Sky and pale blue (1)"], (names, heads))
        by_group = {g["heading"]: [(r["name"], r["tag"]) for r in g["rows"]] for g in groups if g["heading"]}
        check("yours come first in each group, marked You own this, then the wishlist and the empty one",
              # v62 (chunk 2.2): only Wishlist paints are on the shopping list now, so the empty one no longer says On your shopping list.
              by_group["Blues (3)"] == [("Mid Test Blue", "You own this"), ("Wish Blue", "On your shopping list"), ("Empty Blue", "In your palette, not owned")]
              and by_group["Navy and deep blue (1)"] == [("Deep Test Blue", "You own this")] and by_group["Sky and pale blue (1)"] == [("Pale Test Blue", "You own this")], by_group)
        lab = lambda n: page.evaluate("(c) => MinifolioColour.hexToLab(c).L", COLOUR_OF[n])
        owned = [n for n, tg in zip(names, tags) if tg == "You own this"]
        owned_L = [lab(n) for n in owned]
        check("your own paints run dark to light across the groups: Deep, Mid, Pale", owned == ["Deep Test Blue", "Mid Test Blue", "Pale Test Blue"] and owned_L == sorted(owned_L), (owned, owned_L))
        check("the reason line gives the tone and the colour (for example Very dark blue.)", whys[0] == "Very dark blue." and whys[4] in ("Light blue.", "Very light blue."), whys)
        per_sub = page.evaluate("() => Object.fromEntries(['navy', 'blue', 'light'].map(k => [k, [wheelItems().filter(x => x.at.seg === 'blue' && x.at.sub === k && x.origin < 2).length, wheelItems().filter(x => x.at.seg === 'blue' && x.at.sub === k && x.origin === 2).length]]))")
        def cnt(k):
            n = per_sub[k][0] + per_sub[k][1]
            return f"You own 1 of {n} {'paint' if n == 1 else 'paints'} in this group."
        check("the count is honest in each group: You own 1 of (yours + the built-in ones in that group)", [r["count"] for r in reads] == [cnt("navy"), cnt("blue"), cnt("light")] and all(per_sub[k][0] for k in per_sub), ([r["count"] for r in reads], per_sub))
        check("each group's other paints are behind one button that says how many", [r["btn"] for r in reads] == [f"Show other paints ({per_sub[k][1]})" for k in ("navy", "blue", "light")], [r["btn"] for r in reads])
        built_in_blue = per_sub["blue"][1]
        wh.zoom_in(page, "blue")
        wh.open_group(page, "blue", "blue")
        check("the other-paints button starts shut (aria-expanded false)", page.get_attribute("#cmp-wheel-others", "aria-expanded") == "false")
        page.click("#cmp-wheel-others")
        page.wait_for_timeout(150)
        check("the button now says Hide and the built-in paints are in, but the group still stops after its first few (v37 part 2: Show all N)",
              page.inner_text("#cmp-wheel-others") == "Hide other paints" and page.get_attribute("#cmp-wheel-others", "aria-expanded") == "true"
              and len(page.evaluate(GROUPS_JS)) >= 1 and page.locator('#cmp-wheel-detail button[id^="cmp-wheel-more-"]').count() >= 1)
        for _ in range(6):   # open the group fully so the whole list can be checked
            more = page.locator('#cmp-wheel-detail button[id^="cmp-wheel-more-"][aria-expanded="false"]')
            if not more.count():
                break
            more.first.click()
            page.wait_for_timeout(80)
        groups = page.evaluate(GROUPS_JS)
        all_rows = [r for g in groups for r in g["rows"]]
        check("Show other paints adds the built-in blues after yours (all of them once the group is opened)", len(all_rows) == 3 + built_in_blue, (len(all_rows), built_in_blue))
        rest = [r for r in all_rows if r["tag"] == "Not in your palette"]
        check("every built-in paint is tagged Not in your palette", len(rest) == built_in_blue and all(r["tag"] != "Not in your palette" for r in all_rows if r not in rest))
        per_group_lights = page.evaluate("""() => { const out = []; let cur = null; for (const el of document.querySelectorAll('#cmp-wheel-detail > h4.wheel-sub, #cmp-wheel-detail > ul.idea-list')) {
            if (el.tagName === 'H4') { cur = []; out.push(cur); continue; }
            for (const b of el.querySelectorAll('.idea-static')) if (b.querySelector('.idea-tag').textContent === 'Not in your palette') cur.push(MinifolioColour.hexToLab(b.querySelector('.swatch').style.getPropertyValue('--swatch')).L); }
            return out; }""")
        # v63: the built-in paints now come in two runs, popular ranges first and then the other brands (chunk 3.3); each run is dark to light,
        # so the shown order is compared with that rule rather than with one dark-to-light run
        want_lights = page.evaluate("""() => wheelItems().filter(x => x.at.seg === 'blue' && x.at.sub === 'blue' && x.origin === 2)
            .sort((a, b) => wheelPopular(a) - wheelPopular(b) || a.at.L - b.at.L || String(a.paint.name).localeCompare(String(b.paint.name))).map(x => x.at.L)""")
        check("the built-in paints run popular ranges first, then the rest, each dark to light inside the group", [L for g in per_group_lights for L in g] == want_lights and sum(len(g) for g in per_group_lights) == built_in_blue, [g[:4] for g in per_group_lights])
        page.click("#cmp-wheel-others")
        page.wait_for_timeout(150)
        check("the focus stays on the button after it is pressed", page.evaluate("() => document.activeElement.id") == "cmp-wheel-others")
        check("Hide other paints puts them away again", sum(len(g["rows"]) for g in page.evaluate(GROUPS_JS)) == 3)
        wh.go_back(page)

        groups = part_groups(page, "orange")
        heads = [g["heading"] for g in groups]
        check("Orange shows two groups with these paints, Browns then Oranges (dark to light, v37 part 2), each with its count", heads == ["Browns (2)", "Oranges (2)"], heads)
        by = {g["heading"].split(" (")[0]: [r["name"] for r in g["rows"]] for g in groups}
        check("browns sit under orange (as their own group), dark to light; owned oranges first", by["Browns"] == ["Dark Brown Test", "Light Brown Test"] and by["Oranges"] == ["Test Orange", "Wish Orange"], by)
        red_names = [r["name"] for g in part_groups(page, "red") for r in g["rows"]]
        check("the browns are not in the red part", "Dark Brown Test" not in red_names and "Test Red" in red_names, red_names)
        groups = part_groups(page, "yellow")
        by = {g["heading"].split(" (")[0]: [r["name"] for r in g["rows"]] for g in groups}
        check("bone sits under yellow as its own group", [g["heading"] for g in groups] == ["Yellows (1)", "Bone (1)"] and by["Bone"] == ["Test Bone"] and by["Yellows"] == ["Test Yellow"], by)
        tap(page, "metallic")
        groups = page.evaluate(GROUPS_JS)
        by = {g["heading"].split(" (")[0]: [r["name"] for r in g["rows"]] for g in groups}
        check("metallics are split into Gold, Silver and Bronze in the list, in that order",
              [g["heading"].split(" (")[0] for g in groups] == ["Gold", "Silver", "Bronze"], [g["heading"] for g in groups])
        check("the right paints are in each: gold, silver (two) and bronze (copper and the metallic-typed one)",
              by["Gold"] == ["Test Gold"] and sorted(by["Silver"]) == ["Test Metallic", "Test Silver"] and sorted(by["Bronze"]) == ["Odd Shine", "Test Copper"], by)
        note = groups[0]["rows"][0]["note"]
        check("a metallic row says its colour is only a guide", note == "The colour shown is only a guide for this kind of paint.", note)
        green = [r["name"] for g in part_groups(page, "green") for r in g["rows"]]
        check("Bronze Green is a green (not a metallic), and the unknown-colour and basing-material paints are shown nowhere", "Bronze Green" in green and "Unknown Colour" not in green and "Sand Material" not in green, green)
        everywhere = []
        for key in KEYS:
            if key not in wh.HUES:
                tap(page, key)
            everywhere += [r["name"] for g in part_groups(page, key) for r in g["rows"]]
        check("across the whole wheel every paint of yours that has a colour appears exactly once, and the two without are missing",
              sorted(n for n in everywhere if n in COLOUR_OF) == sorted(n for n in COLOUR_OF if n not in ("Unknown Colour", "Sand Material")), sorted(everywhere)[:40])
        tap(page, "white")
        check("the whites part lists the white (and not the grey)", [r["name"] for g in page.evaluate(GROUPS_JS) for r in g["rows"]] == ["Test White"])
        tap(page, "black")
        check("the blacks part lists the black", [r["name"] for g in page.evaluate(GROUPS_JS) for r in g["rows"]] == ["Test Black"])
        load(page, paints=[])
        open_comp(page)
        tap(page, "blue")
        txt = page.inner_text("#cmp-wheel-detail")
        check("an empty palette says so plainly and still offers the built-in paints behind the button",
              "You own 0 of" in txt and "You have none of these in your palette yet" in txt and page.locator("#cmp-wheel-others").count() == 1 and page.locator("#cmp-wheel-detail .idea-static").count() == 0, txt[:300])
        page.click("#cmp-wheel-others")
        page.wait_for_timeout(150)
        wh.open_everything(page)   # v43: a group shows its first 8 and then "Show all N"; open that too
        check("and then shows them all as Not in your palette", page.locator("#cmp-wheel-detail .idea-static").count() > 20
              and page.evaluate("() => [...document.querySelectorAll('#cmp-wheel-detail .idea-tag')].every(e => e.textContent === 'Not in your palette')"))

        # ---------- 6. Reuse, not copy ----------
        print("\n--- 6. Reuse, not copy ---")
        check("the wheel uses the shared row, the shared share row, the shared tags, the shared paint list and the door (nothing copied)",
              all(w in wheel_code for w in ["buildIdeaItem(", "buildShareRow(", "colourIdeaTag(", "compendiumBaseChoices(", "ideaTextLine(", "door.id(", "door.state"]))
        check("each shared builder is still defined exactly once, and the wheel builds no rows or buttons of its own copy",
              all(app.count(f"function {n}(") == 1 for n in ["buildIdeaItem", "buildShareRow", "compendiumBaseChoices", "appendLibraryParts", "appendRolePicker", "buildIdeasList", "ideaTextLine"])
              and 'createElement("li")' not in wheel_code and "idea-static" not in wheel_code and "idea-tag" not in wheel_code)
        check("renderCompendium draws the wheel through the same door as the other parts", "appendColourWheel(body, door, redraw)" in app)
        load(page, paints=WPAINTS)
        open_comp(page)
        tap(page, "orange")
        page.click("#cmp-wheel-others")
        pick_combo(page, "#cmp-colour-ideas-base", index=1)
        dupes = page.evaluate("() => { const ids = [...document.querySelectorAll('[id]')].map(e => e.id); return ids.filter((x, i) => ids.indexOf(x) !== i); }")
        check("no page id appears twice with the wheel open next to the rest of the Compendium", not dupes, dupes[:5])
        check("every id the wheel adds starts with cmp- (so the recipe editor can never clash)",
              page.evaluate("() => [...document.querySelectorAll('#cmp-wheel-block [id], #cmp-wheel-block + * [id]')].filter(e => e.closest('#cmp-wheel-block')).every(e => e.id.startsWith('cmp-'))"))
        check("the rest of the Compendium still works with the wheel open (choose a colour, get 3 ideas, and the wheel stays open)",
              page.locator("#cmp-fold-ideas-panel > .idea-list .idea-static").count() == 3 and zoom_key(page) == "orange" and page.locator("#cmp-wheel-detail").count() == 1)
        page.click('#compendium-body [data-role="trim"]')
        page.wait_for_timeout(150)
        check("changing the role redraws the page and the wheel keeps its choice (and its other-paints switch)", zoom_key(page) == "orange" and page.get_attribute("#cmp-wheel-others", "aria-expanded") == "true")
        check("the wheel's choice is separate from the recipe card: the card's own state has no wheel", page.evaluate("() => !('wheel' in colourIdeasState)"))

        # ---------- 7. Copy as text ----------
        print("\n--- 7. Copy as text ---")
        load(page, paints=WPAINTS)
        open_comp(page)
        copy_spy(page)
        tap(page, "metallic")
        btns = page.evaluate("() => [...document.querySelectorAll('#cmp-wheel-detail .share-row button')].map(b => b.textContent)")
        check("the open part ends with Copy as text (and no Save into a new recipe, a long list is not a recipe)", btns == ["Copy as text"], btns)
        page.click("#cmp-wheel-detail .share-row button")
        text = copied(page)
        lines = text.splitlines()
        check("the copied text starts with the part's name and says how many you own", lines[0] == "Metallics" and any(re.fullmatch(r"You own 5 of \d+ paints in this colour\.", l) for l in lines), lines[:4])
        check("it lists the groups and the paints with their tags", "Gold (1)" in lines and "Silver (2)" in lines and "Bronze (2)" in lines
              and any(re.fullmatch(r"- Test Gold \(Test Paints\): You own this\. (Mid|Light|Very light) gold\. The colour shown is only a guide for this kind of paint\.", l) for l in lines), lines[:12])
        check("it ends with the same footnote as the rest of the Compendium", lines[-1] == "Colours on a screen are only a guide, so check them on your model.", lines[-1])
        check("it is plain text only (no tags, no web addresses)", not re.search(r"<[a-z/]|https?://", text))
        toast = page.evaluate("() => (document.getElementById('toast-text') || {}).textContent || ''")
        check("it tells you it was copied, in plain words (Metallics list copied. Paste it anywhere.)", toast == "Metallics list copied. Paste it anywhere.", toast)
        tap(page, "blue")
        shown_rows = page.locator("#cmp-wheel-detail .idea-static").count()
        page.click("#cmp-wheel-detail .share-row button")
        short = copied(page)
        check("with the other paints hidden only the paints shown are copied; showing them copies them too",
              short.count("\n- ") == shown_rows and (page.click("#cmp-wheel-others"), page.wait_for_timeout(150), page.click("#cmp-wheel-detail .share-row button"), copied(page).count("\n- ") > shown_rows + 5)[-1], (short.count("\n- "), shown_rows))

        # ---------- 8. Text scan ----------
        print("\n--- 8. Text scan: no Games Workshop names in any new text ---")
        load(page, paints=WPAINTS)
        open_comp(page)
        shown = [page.evaluate(WHEEL_TEXT_JS)]
        for key in KEYS:
            tap(page, key)
            shown.append(page.evaluate(WHEEL_TEXT_JS))
            if page.locator("#cmp-wheel-others").count():
                page.click("#cmp-wheel-others")
                page.wait_for_timeout(100)
                shown.append(page.evaluate(WHEEL_TEXT_JS))
                page.click("#cmp-wheel-others")
                page.wait_for_timeout(100)
        for key in wh.HUES:   # v43: every group of every colour, and the drilled-down picture's own words
            shown += wh.open_each_group(page, key, lambda pg: pg.evaluate(WHEEL_TEXT_JS))
        everything = "\n".join(shown)
        hits = GW_WORDS.findall(everything) + GW_MORE.findall(everything)
        check("everything we wrote for the wheel (hint, caption, ten descriptions, headings, counts, tones, tags, notes) names no Games Workshop game, faction, scheme, paint or product",
              not hits and len(shown) >= 15 and all(w.lower() in everything.lower() for w in ["Tap a colour to see what's in it", "Browns", "Bone", "Gold", "Show other paints"]), (hits[:10], len(shown)))
        brands = BRAND_WORDS.findall(everything)
        check("and none of it names a brand, a shop or a product", not brands, brands[:10])
        own = "\n".join([joined, help_text, wheel_code])
        own_hits = GW_WORDS.findall(own) + GW_MORE.findall(own)
        check("the new Updates entry, the Help line and the new code's words are clean too", not own_hits, own_hits[:10])
        check("the wheel has no links at all (no shop links, those come later)", page.locator("#cmp-wheel-block a, #cmp-wheel-block [href]").count() == 0)

        # ---------- 9. Hostile text ----------
        print("\n--- 9. Hostile text ---")
        evil = WPAINTS + [P(90, HOSTILE, "#2244aa", brand=HOSTILE_BRAND), P(91, HOSTILE + " Gold", "#c9a227", brand=HOSTILE_BRAND)]
        load(page, paints=evil)
        open_comp(page)
        copy_spy(page)
        tap(page, "blue")
        check("a hostile paint name and brand never become markup in the blue list and no script runs",
              page.locator("#view-compendium img, #view-compendium script, #view-compendium b, #view-compendium iframe").count() == 0 and page.evaluate("() => window.__pwned") is None)
        blue_rows = [r for g in part_groups(page, "blue") for r in g["rows"]]   # v37 part 2: the blues are in three groups (v43: opened one at a time)
        wh.zoom_in(page, "blue")
        wh.open_group(page, "blue", "blue")
        check("it shows as plain text instead", any("<img src=x" in r["name"] for r in blue_rows) and "<script>" in page.inner_text("#cmp-wheel-detail"), [r["name"] for r in blue_rows][:5])
        tap(page, "metallic")   # (goes back up from the blues first)
        check("the same in the metallics (a hostile name with a metal word in it)", page.locator("#view-compendium img, #view-compendium script, #view-compendium b").count() == 0
              and page.evaluate("() => window.__pwned") is None and "<img src=x" in page.inner_text("#cmp-wheel-detail"))
        page.click("#cmp-wheel-detail .share-row button")
        text = copied(page)
        check("Copy as text keeps it as plain text", "<img src=x" in text and page.evaluate("() => window.__pwned") is None)
        check("the swatch, tag and tooltip texts carry no markup either", page.locator("#cmp-wheel-block svg b, #cmp-wheel-block svg img").count() == 0)

        # ---------- 10. Offline ----------
        print("\n--- 10. Offline ---")
        load(page, paints=WPAINTS)
        mark = len(requests)
        open_comp(page)
        for key in KEYS:
            tap(page, key)
        tap(page, "blue")
        page.click("#cmp-wheel-others")
        copy_spy(page)
        page.click("#cmp-wheel-detail .share-row button")
        outside = [u for u in requests[mark:] if not u.startswith(t.BASE) and not u.startswith("data:") and not u.startswith("blob:")]
        check("using the wheel makes no request to any other address", not outside, outside[:5])
        ctx.set_offline(True)
        tap(page, "green")
        check("it works with the network off", zoom_key(page) == "green" and page.locator("#cmp-wheel-detail .idea-static").count() >= 1)
        ctx.set_offline(False)

        # ---------- 11. Phone widths ----------
        print("\n--- 11. Phone widths 360, 375, 390 and 400 ---")
        for width in (360, 375, 390, 400):
            page.set_viewport_size({"width": width, "height": 800})
            load(page, paints=WPAINTS)
            open_comp(page)
            page.evaluate("() => window.scrollTo(0, 0)")
            g = tap_points(page)
            fits = g["left"] >= 0 and g["right"] <= width + 0.5
            check(f"at {width} px the wheel is {round(g['width'])} px wide, inside the screen, and nothing scrolls sideways", fits and no_sideways(page), g["width"])
            inscribed = 2 * 0.4142 * 92 * g["scale"]
            check(f"at {width} px a finger has room in the middle: a circle {round(inscribed)} px across fits inside each centre slice (44 px or more), so the four-button fallback is not needed", inscribed >= 44, inscribed)
            ring_gap = 52 * g["scale"]
            check(f"at {width} px the ring is {round(ring_gap)} px thick (44 px or more)", ring_gap >= 44, ring_gap)
            wrong = []
            for key in KEYS:
                x, y = g["points"][key]
                hit = page.evaluate("([x, y]) => { const e = document.elementFromPoint(x, y); return e && e.dataset ? e.dataset.wheel : (e ? e.tagName : null); }", [x, y])
                page.mouse.click(x, y)
                page.wait_for_timeout(120)
                opened = (zoom_key(page) == key) if key in wh.HUES else (open_key(page) == key)   # v43: a colour drills in, a grey-centre slice opens its list
                if hit != key or not opened:
                    wrong.append((key, hit, open_key(page), zoom_key(page)))
                    page.evaluate("() => { compendiumState.wheel = ''; compendiumState.wheelZoom = ''; compendiumState.wheelGroup = ''; renderCompendium(); }")
                elif key in wh.HUES:
                    wh.go_back(page)   # back up, ready for the next
                    page.evaluate("() => window.scrollTo(0, 0)")   # the points were measured from the top of the page
                else:
                    page.mouse.click(x, y)   # tap again to close it, ready for the next
                    page.wait_for_timeout(100)
            check(f"at {width} px tapping the middle of each of the ten slices opens that slice", not wrong, wrong)
            longest = wh.open_each_group(page, "orange", wh.open_everything)   # v43: each of the three groups with every paint showing (the colour opens one group at a time)
            check(f"at {width} px nothing scrolls sideways with the longest lists open (every orange and brown, one group at a time)", all(ok for ok, _ in longest) and sum(n for _, n in longest) > 100, longest)
            tap(page, "orange")
            outside = page.evaluate("""() => { const c = document.querySelector('#view-compendium .card').getBoundingClientRect();
                return [...document.querySelectorAll('#cmp-wheel-block *')].filter(e => { const r = e.getBoundingClientRect();
                    return r.width > 0 && (r.right > c.right + 0.5 || r.left < c.left - 0.5); }).map(e => e.id || e.className.baseVal || e.className || e.tagName); }""")
            check(f"at {width} px everything in the wheel part is inside the Compendium card", not outside, outside[:5])
            if width in (360, 400):
                tap(page, "orange")
                tap(page, "blue")
                page.evaluate("() => window.scrollTo(0, 0)")
                shot(page, f"v36-wheel-open-{width}.png")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 12. Dark and light ----------
        print("\n--- 12. Dark and light, 390 and 360 px ---")
        for appearance in ("dark", "light"):
            for width in (390, 360):
                page.set_viewport_size({"width": width, "height": 844})
                load(page, paints=WPAINTS, settings={"appearance": appearance})
                open_comp(page)
                tap(page, "metallic")   # v43: a centre slice keeps the whole wheel on show, so the ring checks below still apply
                col = page.evaluate("""() => { const bg = (el) => { let e = el; while (e) { const v = getComputedStyle(e).backgroundColor;
                        const m = v.match(/rgba\\(.*,\\s*([\\d.]+)\\)/);
                        if (v && v !== 'transparent' && !(m && parseFloat(m[1]) < 0.9)) return v; e = e.parentElement; } return 'rgb(0,0,0)'; };
                    const out = {};
                    const pairs = [['hint', '#cmp-wheel-hint'], ['caption', '.wheel-caption'], ['title', '#cmp-wheel-detail h3'], ['about', '#cmp-wheel-detail > .hint'],
                                   ['count', '#cmp-wheel-detail .idea-label'], ['group', '.wheel-sub'], ['name', '#cmp-wheel-detail .idea-name'], ['why', '#cmp-wheel-detail .idea-why'],
                                   ['tag own', '#cmp-wheel-detail .idea-tag.own'], ['tag none', '#cmp-wheel-detail .idea-tag.none'], ['button', '#cmp-wheel-others'],
                                   ['copy', '#cmp-wheel-detail .share-row button'], ['intro', '#cmp-intro']];
                    for (const [k, s] of pairs) { const el = document.querySelector(s); if (el) out[k] = [getComputedStyle(el).color, bg(el)]; }
                    return out; }""")
                bad = {k: round(contrast(rgb(v[0]), rgb(v[1])), 2) for k, v in col.items() if contrast(rgb(v[0]), rgb(v[1])) < 4.5}
                tag = f"{appearance} {width}px"
                check(f"{tag}: the hint, caption, description, count, group names, rows, tags and buttons all have contrast of at least 4.5", not bad and len(col) >= 12, (bad, len(col)))
                ring = page.evaluate("""() => { const open = getComputedStyle(document.querySelector('#cmp-wheel path[aria-pressed="true"]')), shut = getComputedStyle(document.querySelector('#cmp-wheel path[aria-pressed="false"]'));
                    const card = getComputedStyle(document.querySelector('#view-compendium .card')).backgroundColor;
                    return { open: open.stroke, shut: shut.stroke, width: open.strokeWidth, card }; }""")
                check(f"{tag}: the open slice has an outline you can see (contrast 3 or more against the card) and the shut ones do not", contrast(rgb(ring["open"]), rgb(ring["card"])) >= 3 and ring["open"] != ring["shut"], ring)
                fills = page.evaluate("() => Object.fromEntries([...document.querySelectorAll('#cmp-wheel path.wheel-seg')].map(e => [e.dataset.wheel, getComputedStyle(e).fill]))")
                check(f"{tag}: the ring colours are all different from each other, and the metallic slice is a gradient", len({fills[k] for k in KEYS[:9]}) == 9 and fills["metallic"].startswith("url("), fills)
                check(f"{tag}: nothing scrolls sideways", no_sideways(page))
                shot(page, f"v36-compendium-{appearance}-{width}.png")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 13. Nothing else changed ----------
        print("\n--- 13. Nothing else changed ---")
        load(page, paints=WPAINTS)
        for tab, view in [("dashboard", "view-dashboard"), ("units", "view-units"), ("recipes", "view-recipes"), ("settings", "view-settings"), ("compendium", "view-compendium")]:
            blur(page)
            page.click(f'nav button[data-tab="{tab}"]')
            page.wait_for_timeout(120)
            check(f"the {tab} tab opens its own page and hides the others", page.is_visible(f"#{view}") and sum(page.is_visible(f"#{v}") for v in ["view-dashboard", "view-units", "view-recipes", "view-settings", "view-compendium"]) == 1)
        open_comp(page)
        # v37: the five parts now sit under folding headings (each opened by open_comp), so look inside them as well as at the top level
        ids = page.evaluate("() => [...document.querySelectorAll('#compendium-body > *, #compendium-body > .more-info .more-info-panel > *, #compendium-body .fold-panel > *')].map(e => e.id).filter(Boolean)")
        want = ["cmp-intro", "cmp-wheel-block", "cmp-colour-ideas-none", "cmp-faction-history", "cmp-starter-schemes", "cmp-detail-recipes", "cmp-basing-tips", "cmp-foot"]
        check("the rest of the Compendium is all still there, in the same order, after the wheel", [i for i in ids if i in want] == want, ids)
        check("the card in a recipe has no wheel and still starts closed", (lambda: (load(page, paints=WPAINTS, recipes=[rec(1, "R", "Armour", [1])]), t.open_editor(page), page.evaluate("() => [document.getElementById('colour-ideas').open, document.querySelectorAll('#view-recipes .wheel-svg').length]"))[-1])() == [False, 0])
        check("no real browser pop-ups appeared", not [d for d in dialogs if "Do you own" in d], dialogs[:3])
        check("no page errors", not errors, errors[:3])
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
