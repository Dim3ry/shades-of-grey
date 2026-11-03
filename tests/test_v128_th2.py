"""TH2 tests for Minifolio (Grim Forge restyle: worn, scratched steel with brass rivets, forge orange as the accent). New behaviour only:
1. The steel is CSS gradients plus two small inline SVG tiles (scratches, brushed grain), nothing loaded from another site, under the size
   limit, with no filter or blend mode in the TH2 rules.
2. A saved Grim Forge setting loads the theme. The steel is drawn on a fixed layer behind the page; the header and the fade behind the bar
   show the same steel measured from the top of the screen. Cards and unit rows carry four brass rivets inside their padding.
3. Readability, measured on the drawn steel: every text colour at 4.5:1 against the lightest (dark) or darkest (light) point where text can
   sit (the page column, inside the cards, the header's version number), borders and the brass rule at 3:1, button text on the forge orange
   at 4.5:1, and the orange on the highlighted Guides row at 4.5:1.
4. The forge orange, the brass, the "bad" red, the amber "caution", the yellow "warn" and the green "good" are told apart (CIEDE2000).
5. The start circle, the basket, the Undo message and the Mentor window stay readable; the steel is not printed; no other theme gets rivets.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import io, math, os, re, sys
from playwright.sync_api import sync_playwright
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import quiet

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

SIZE_LIMIT = 9000   # bytes: Grim Forge's texture and rivet tokens (shared and both modes) plus the TH2 rules
TEXT = ["--text", "--muted", "--accent", "--heading-colour", "--good", "--bad", "--warn", "--caution", "--wish", "--grey-status", "--note", "--danger"]
UNITS = [{"id": i, "name": f"Unit {i}", "hobby": "40K", "stage": i % 6, "count": 5, "added": "2026-10-01", "log": [["2026-10-01", 1]]} for i in range(1, 7)]
RIVET = "closest-side at 42% 40%"

def lum(c):
    v = [x / 255 for x in c[:3]]
    v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]

def ratio(a, b):
    a, b = lum(a), lum(b)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)

def lab(c):
    r, g, b = [(x / 255) / 12.92 if x / 255 <= 0.04045 else ((x / 255 + 0.055) / 1.055) ** 2.4 for x in c[:3]]
    xyz = ((r * .4124 + g * .3576 + b * .1805) / .95047, r * .2126 + g * .7152 + b * .0722, (r * .0193 + g * .1192 + b * .9505) / 1.08883)
    f = [v ** (1 / 3) if v > 216 / 24389 else (24389 / 27 * v + 16) / 116 for v in xyz]
    return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])

def de2000(c1, c2):
    (L1, a1, b1), (L2, a2, b2) = lab(c1), lab(c2)
    cb = (math.hypot(a1, b1) + math.hypot(a2, b2)) / 2
    g = .5 * (1 - math.sqrt(cb ** 7 / (cb ** 7 + 25 ** 7)))
    a1, a2 = a1 * (1 + g), a2 * (1 + g)
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    h1, h2 = math.degrees(math.atan2(b1, a1)) % 360, math.degrees(math.atan2(b2, a2)) % 360
    dh = 0 if C1 * C2 == 0 else (h2 - h1 if abs(h2 - h1) <= 180 else h2 - h1 - 360 if h2 > h1 else h2 - h1 + 360)
    dH = 2 * math.sqrt(C1 * C2) * math.sin(math.radians(dh / 2))
    Lb, Cb = (L1 + L2) / 2, (C1 + C2) / 2
    hb = h1 + h2 if C1 * C2 == 0 else (h1 + h2) / 2 if abs(h1 - h2) <= 180 else (h1 + h2 + 360) / 2 if h1 + h2 < 360 else (h1 + h2 - 360) / 2
    T = 1 - .17 * math.cos(math.radians(hb - 30)) + .24 * math.cos(math.radians(2 * hb)) + .32 * math.cos(math.radians(3 * hb + 6)) - .2 * math.cos(math.radians(4 * hb - 63))
    rt = -math.sin(math.radians(60 * math.exp(-((hb - 275) / 25) ** 2))) * 2 * math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7))
    sl, sc, sh = 1 + .015 * (Lb - 50) ** 2 / math.sqrt(20 + (Lb - 50) ** 2), 1 + .045 * Cb, 1 + .015 * Cb * T
    dl, dc, dhh = (L2 - L1) / sl, (C2 - C1) / sc, dH / sh
    return math.sqrt(dl * dl + dc * dc + dhh * dhh + rt * dc * dhh)

def colours(page, names):
    return page.evaluate("""names => names.map(n => { const d = document.createElement('i'); d.style.color = getComputedStyle(document.documentElement).getPropertyValue(n);
        document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c.match(/[\\d.]+/g).slice(0, 3).map(Number); })""", names)

def css_rgb(text):
    return [float(x) for x in re.findall(r"[\d.]+", text)[:3]]

def extreme(img, box, darkest):
    crop = img.crop(tuple(int(round(v)) for v in box)).convert("RGB")
    px = list(crop.get_flattened_data() if hasattr(crop, "get_flattened_data") else crop.getdata())
    return (min if darkest else max)(px, key=lum)

HIDE = "body * { visibility: hidden !important; } :is(.card, li.unit) { visibility: visible !important; } :is(.card, li.unit) * { visibility: hidden !important; }"

def steel_extremes(page, darkest):
    """The worst point of the steel in the page column (between the header and the solid part of the fade behind the bar), inside the content
    boxes of the cards and unit rows (the rivets sit in the padding), behind the header's version number, and in the header next to the brass rule."""
    w = page.viewport_size["width"]
    top = page.evaluate("Math.ceil(document.querySelector('.app-bar').getBoundingClientRect().bottom)")
    bottom = page.evaluate("Math.floor(innerHeight - parseFloat(getComputedStyle(document.querySelector('.tabs'), '::before').height) * 0.4)")
    vt = page.evaluate("(() => { const r = document.querySelector('h1 .version-tag').getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; })()")
    tag = page.add_style_tag(content=HIDE)
    boxes = page.evaluate("""() => [...document.querySelectorAll('.card, li.unit')].filter(c => c.getClientRects().length).map(c => { const r = c.getBoundingClientRect(), s = getComputedStyle(c);
        const px = (p) => parseFloat(s['border' + p + 'Width']) + parseFloat(s['padding' + p]);
        return [r.left + px('Left'), Math.max(0, r.top + px('Top')), r.right - px('Right'), Math.min(innerHeight, r.bottom - px('Bottom'))]; }).filter(b => b[3] - b[1] > 4)""")
    cards = Image.open(io.BytesIO(page.screenshot()))
    tag2 = page.add_style_tag(content=":is(.card, li.unit) { visibility: hidden !important; } .app-bar { border-bottom-color: transparent !important; }")
    bare = Image.open(io.BytesIO(page.screenshot()))
    page.evaluate("els => els.forEach(e => e.remove())", [tag, tag2])
    in_cards = [extreme(cards, b, darkest) for b in boxes]
    pick = min if darkest else max
    # TH6 (v129): hex bolts now hold the brass rule at both ends, in the 16 px page margins, so the steel beside the rule is measured between them
    rule = page.evaluate("(() => { const r = document.querySelector('.app-bar').getBoundingClientRect(); return [16, r.bottom - 12, innerWidth - 16, r.bottom + 6]; })()")
    return (extreme(bare, (16, top, w - 16, bottom), darkest), (pick(in_cards, key=lum) if in_cards else None), len(boxes),
            extreme(bare, vt, darkest), extreme(bare, rule, darkest))

def current_guides_row(page, darkest):
    """The worst point of the highlighted Guides row's own background (inside its border and the 4 px bar), with its text hidden."""
    page.evaluate("() => { document.querySelector('.tabs button[data-tab=\"guides\"]').click(); document.querySelector('#more-seg button[data-page=\"guides\"]').click(); }")
    quiet(page)
    box = page.evaluate("""() => { const r = document.querySelector('.guides-row'); r.setAttribute('aria-current', 'true'); r.scrollIntoView({ block: 'center' });
        const b = r.getBoundingClientRect(), s = getComputedStyle(r), bw = parseFloat(s.borderTopWidth);
        return [b.left + bw + 4, b.top + bw, b.right - bw, b.bottom - bw]; }""")
    tag = page.add_style_tag(content=".guides-row[aria-current] * { visibility: hidden !important; }")
    img = Image.open(io.BytesIO(page.screenshot()))
    tag.evaluate("e => e.remove()")
    return extreme(img, box, darkest)

def main():
    outside = []
    html = t.read("index.html")
    style = html[html.index("<style>"):html.index("</style>")]

    print("\n--- 1. How the steel is drawn ---")
    blocks = [style[style.index(sel):] for sel in ('[data-t="forge"] {', '[data-t="forge"][data-m="dark"] {', '[data-t="forge"][data-m="light"] {')]
    blocks = [b[:b.index("\n    }")] for b in blocks]
    steel = [v for b in blocks for v in re.findall(r"--(?:texture|texture-size|forge-shade|forge-scratch|forge-brush|rivet|plate|rivet-hi|rivet-a|rivet-b|rivet-edge|plate-hi|plate-lo): ([^\n]*);", b)]
    urls = [u for v in steel for u in re.findall(r"url\((?!%23)(.{0,40})", v)]
    check("the only pictures in the steel are inline SVG tiles (no file, no other site)", len(urls) == 4 and all(u.startswith('"data:image/svg+xml,') for u in urls), urls)
    rules = style[style.index("/* TH2: worn steel"):]
    rules = rules[:rules.index("\n\n")]   # the TH2 rules are one block that ends at the next blank line
    size = sum(len(v) for v in steel) + len(rules)
    print(f"     (steel and rivet tokens and TH2 rules: {size} bytes)")
    check(f"the added texture stays under {SIZE_LIMIT} bytes", size < SIZE_LIMIT, size)
    check("no filter or blend mode in the TH2 rules", not re.search(r"(?<![-\w])filter:|mix-blend-mode|backdrop-filter", rules), rules[:200])

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("request", lambda r: outside.append(r.url) if r.resource_type in ("font", "image") and not r.url.startswith((t.BASE, "data:", "blob:")) and "goatcounter.com" not in r.url else None)

        print("\n--- 2. The theme loads; the steel, the header, the fade and the rivets ---")
        t.load(page, units=UNITS, settings={"theme": "forge", "appearance": "dark", "examplesChecked": True}, launch=True)
        start = page.evaluate("""() => { const f = getComputedStyle(document.querySelector('.tabs'), '::before'), seg = document.querySelector('.arc [data-tab="units"]'), s = getComputedStyle(seg);
            return { t: document.documentElement.dataset.t, m: document.documentElement.dataset.m, launching: document.body.classList.contains('launching'),
                     mask: f.maskImage || f.webkitMaskImage, glow: f.backgroundImage, segBg: s.backgroundColor, segText: s.color }; }""")
        check("a saved Grim Forge setting loads Grim Forge dark", start["t"] == "forge" and start["m"] == "dark", start)
        check("start page: the fade is not masked, so the whole glow round the circle shows", start["launching"] and start["mask"] == "none" and "radial-gradient" in start["glow"], start)
        check("start page: the circle's labels read at 4.5:1 on their segments", ratio(css_rgb(start["segText"]), css_rgb(start["segBg"])) >= 4.5, start)
        t.leave_launch(page)
        page.click('.tabs button[data-tab="units"]'); quiet(page)
        line = page.evaluate("""() => { const tabs = document.querySelector('.tabs'), bar = document.querySelector('.app-bar');
            const L = getComputedStyle(document.body, '::before'), B = getComputedStyle(bar), F = getComputedStyle(tabs, '::before');
            const h = s => parseFloat(s.backgroundSize.split(', ')[0].split(' ')[1]);
            const fadeTop = tabs.getBoundingClientRect().bottom - parseFloat(F.height);
            return { layer: [parseFloat(L.top), h(L), parseFloat(L.height)], fixed: L.position, bar: [bar.getBoundingClientRect().top + parseFloat(B.backgroundPositionY), h(B)],
                     fade: [fadeTop + parseFloat(F.backgroundPositionY), h(F)], same: L.backgroundImage === B.backgroundImage && B.backgroundImage === F.backgroundImage,
                     svg: (L.backgroundImage.match(/data:image\\/svg/g) || []).length, body: getComputedStyle(document.body).backgroundImage }; }""")
        tops = [line["layer"][0], line["bar"][0], line["fade"][0]]
        heights = [line["layer"][1], line["layer"][2], line["bar"][1], line["fade"][1]]
        check("the steel is on a fixed layer behind the page (scratches and brushed grain), not on the scrolling page",
              line["fixed"] == "fixed" and line["svg"] == 2 and line["body"] == "none", line)
        check("the layer, the header and the fade show the same steel, measured from the top of the screen at the same height",
              line["same"] and all(abs(v) < 1 for v in tops) and max(heights) - min(heights) < 1, line)
        rv = page.evaluate(f"""() => [...document.querySelectorAll('li.unit, .card')].filter(c => c.getClientRects().length).slice(0, 4).map(c => {{
            const s = getComputedStyle(c); return {{ n: s.backgroundImage.split('{RIVET}').length - 1, size: s.backgroundSize.split(', ')[0],
            pos: s.backgroundPosition.split(', ').slice(0, 4), pad: Math.min(parseFloat(s.paddingTop), parseFloat(s.paddingRight)) }}; }})""")
        check("cards and unit rows each carry four brass rivets, one in each corner, inside their padding",
              rv and all(r["n"] == 4 and r["size"] == "9px 9px" and 3 + 9 <= r["pad"] for r in rv)
              and rv[0]["pos"] == ["3px 3px", "calc(100% - 3px) 3px", "3px calc(100% - 3px)", "calc(100% - 3px) calc(100% - 3px)"], rv)
        btn = page.evaluate("getComputedStyle(document.querySelector('.primary-button')).transform")
        check("the main button has no resting transform", btn == "none", btn)

        print("\n--- 3. Readability on the drawn steel, and the colours kept apart ---")
        names = TEXT + ["--border", "--on-accent", "--accent-fill", "--toast-action", "--brass", "--card"]
        for mode, w, h in (("dark", 390, 844), ("light", 360, 640)):
            page.set_viewport_size({"width": w, "height": h})
            if mode == "light":
                t.load(page, units=UNITS, settings={"theme": "forge", "appearance": "light", "examplesChecked": True})
                page.click('.tabs button[data-tab="units"]'); quiet(page)
            page.wait_for_timeout(150)
            darkest = mode == "light"
            col, card, n, tag, rule_bg = steel_extremes(page, darkest)
            v = dict(zip(names, colours(page, names)))
            print(f"     ({mode}: worst page point {col}, worst card point {card}, header {tag}, by the rule {rule_bg})")
            low = [(k, round(ratio(v[k], col), 2)) for k in TEXT if ratio(v[k], col) < 4.5]
            check(f"{mode} {w}px: every text colour reads at 4.5:1 on the {'darkest' if darkest else 'lightest'} point of the steel", not low, low)
            low = [(k, round(ratio(v[k], card), 2)) for k in TEXT if card and ratio(v[k], card) < 4.5]
            check(f"{mode} {w}px: every text colour reads at 4.5:1 inside the cards, plate sheen included ({n} cards)", n >= 3 and not low, (n, low))
            check(f"{mode} {w}px: the small version number in the header reads at 4.5:1 on the header's steel", ratio(v["--muted"], tag) >= 4.5, round(ratio(v["--muted"], tag), 2))
            check(f"{mode} {w}px: borders reach 3:1 on the worst point of the steel and on the cards",
                  min(ratio(v["--border"], col), ratio(v["--border"], v["--card"])) >= 3, (round(ratio(v["--border"], col), 2), round(ratio(v["--border"], v["--card"]), 2)))
            rule = page.evaluate("getComputedStyle(document.querySelector('.app-bar')).borderBottomColor")
            check(f"{mode} {w}px: the brass rule under the header reaches 3:1 on the steel beside it", ratio(css_rgb(rule), rule_bg) >= 3, (rule, round(ratio(css_rgb(rule), rule_bg), 2)))
            check(f"{mode}: button text reads at 4.5:1 on the forge orange", ratio(v["--on-accent"], v["--accent-fill"]) >= 4.5, round(ratio(v["--on-accent"], v["--accent-fill"]), 2))
            check(f"{mode}: the Undo on the toast reads at 4.5:1", ratio(v["--toast-action"], v["--text"]) >= 4.5, round(ratio(v["--toast-action"], v["--text"]), 2))
            basket = page.evaluate("(() => { const s = getComputedStyle(document.querySelector('.app-actions .basket')); return [s.color, s.backgroundImage]; })()")
            check(f"{mode}: the basket's count reads at 4.5:1 on its orange", ratio(css_rgb(basket[0]), v["--accent-fill"]) >= 4.5 and "gradient" in basket[1], basket)
            row = current_guides_row(page, darkest)
            check(f"{mode}: the orange reads at 4.5:1 on the highlighted Guides row", ratio(v["--accent"], row) >= 4.5, (row, round(ratio(v["--accent"], row), 2)))
            acc, bad, cau, warn, good, brass = v["--accent"], v["--bad"], v["--caution"], v["--warn"], v["--good"], v["--brass"]
            gaps = {"bad/orange": de2000(bad, acc), "bad/caution": de2000(bad, cau), "orange/caution": de2000(acc, cau), "brass/caution": de2000(brass, cau),
                    "brass/warn": de2000(brass, warn), "brass/orange": de2000(brass, acc), "warn/caution": de2000(warn, cau), "warn/good": de2000(warn, good)}
            check(f"{mode}: forge orange, brass, bad, caution, warn and good are told apart (CIEDE2000 12 or more, bad from the orange 15 or more)",
                  all(x >= 12 for x in gaps.values()) and gaps["bad/orange"] >= 15, {k: round(x, 1) for k, x in gaps.items()})
            t.shot(page, f"v128_th2_{mode}.png")

        print("\n--- 4. The Mentor window, print and the other themes ---")
        page.evaluate("() => { document.querySelector('.tabs button[data-tab=\"dashboard\"]').click(); }"); quiet(page)
        page.click(".mentor-orb"); page.wait_for_timeout(500)
        mw = page.evaluate("""() => { const w = document.querySelector('.mentor-window'), g = w && w.querySelector('.mentor-greeting');
            return w && g ? [getComputedStyle(w).backgroundColor, getComputedStyle(g).color, w.getBoundingClientRect().width] : null; }""")
        check("light: the Mentor window's greeting reads at 4.5:1 on the window", mw and mw[2] > 0 and ratio(css_rgb(mw[1]), css_rgb(mw[0])) >= 4.5, mw)
        page.keyboard.press("Escape"); page.wait_for_timeout(200)
        page.emulate_media(media="print")
        printed = page.evaluate("() => [getComputedStyle(document.body, '::before').content, getComputedStyle(document.querySelector('.app-bar')).backgroundImage]")
        check("the steel is not printed", printed == ["none", "none"], printed)
        page.emulate_media(media="screen")
        page.evaluate("() => { document.querySelector('.tabs button[data-tab=\"guides\"]').click(); document.querySelector('#more-seg button[data-page=\"settings\"]').click(); }")
        quiet(page)
        sq = page.evaluate(f"""() => {{ const s = document.querySelector('.theme-swatch[data-t="forge"]'), c = s.querySelector('.ts-card');
            return [getComputedStyle(s).backgroundImage.includes('data:image/svg'), getComputedStyle(c).backgroundImage.split('{RIVET}').length - 1]; }}""")
        check("the Grim Forge square in Settings shows the steel and four small rivets", sq == [True, 4], sq)
        page.evaluate("() => { document.querySelector('.tabs button[data-tab=\"units\"]').click(); }"); quiet(page)
        for theme in ("classic", "parchment", "bench"):
            # the theme's own selectors follow the page's data-t at once, so the same page is reused (the Theme buttons do the same plus saving)
            got = page.evaluate(f"""(th) => {{ document.documentElement.dataset.t = th; const cards = [...document.querySelectorAll('li.unit, .card')].filter(c => c.getClientRects().length);
                return [cards.length, cards.some(c => getComputedStyle(c).backgroundImage.includes('{RIVET}'))]; }}""", theme)
            check(f"{theme}: no rivets on its cards", got[0] >= 3 and not got[1], got)
        check("no font or picture loads from another site", not outside, outside)
        browser.close()

    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
