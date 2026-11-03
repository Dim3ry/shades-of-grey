"""TH3 tests for Minifolio (Parchment Codex restyle: red ink on parchment, with grain, ink blots and edge stains). New behaviour only:
1. The paper is CSS gradients plus one small inline SVG grain tile, nothing loaded from another site, and it stays under the size limit.
2. A saved Parchment setting loads the theme. The page layer, the header and the fade behind the bar measure the paper from the top of
   the screen at the same height, so the stains line up (and on a phone do not jump when the browser bar slides away).
3. The start page: the fade's mask does not cut the top of the glow round the start circle.
4. Readability, measured on the drawn paper: every text colour at 4.5:1 against the darkest (light) or lightest (dark) point where text can
   sit (the page column, inside the cards, the header's version number), borders at 3:1, button text on the crimson fill at 4.5:1, and the
   crimson text on the highlighted Guides row (the accent wash) at 4.5:1.
5. The crimson, the "bad" red and the amber "caution" are told apart (CIEDE2000 distance), and the paper is not printed.
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

SIZE_LIMIT = 8000   # bytes: the paper tokens (shared and both modes) plus the TH3 rules
TEXT = ["--text", "--muted", "--accent", "--heading-colour", "--good", "--bad", "--warn", "--caution", "--wish", "--grey-status", "--note", "--danger"]
UNITS = [{"id": i, "name": f"Unit {i}", "hobby": "40K", "stage": i % 6, "count": 5, "added": "2026-10-01", "log": [["2026-10-01", 1]]} for i in range(1, 7)]

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

def extreme(img, box, darkest):
    px = list(img.crop(tuple(int(round(v)) for v in box)).convert("RGB").getdata())
    return (min if darkest else max)(px, key=lum)

HIDE = "body * { visibility: hidden !important; } :is(.card, li.unit) { visibility: visible !important; } :is(.card, li.unit) * { visibility: hidden !important; }"

def paper_extremes(page, darkest):
    """The worst point of the paper in the page column (between the header and the solid part of the fade behind the bar),
    inside the content boxes of the cards and unit rows, and behind the header's version number, with everything else hidden."""
    w = page.viewport_size["width"]
    top = page.evaluate("Math.ceil(document.querySelector('.app-bar').getBoundingClientRect().bottom)")
    bottom = page.evaluate("Math.floor(innerHeight - parseFloat(getComputedStyle(document.querySelector('.tabs'), '::before').height) * 0.4)")
    vt = page.evaluate("(() => { const r = document.querySelector('h1 .version-tag').getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; })()")
    tag = page.add_style_tag(content=HIDE)
    boxes = page.evaluate("""() => [...document.querySelectorAll('.card, li.unit')].filter(c => c.getClientRects().length).map(c => { const r = c.getBoundingClientRect(), s = getComputedStyle(c);
        const px = (p) => parseFloat(s['border' + p + 'Width']) + parseFloat(s['padding' + p]);
        return [r.left + px('Left'), Math.max(0, r.top + px('Top')), r.right - px('Right'), Math.min(innerHeight, r.bottom - px('Bottom'))]; }).filter(b => b[3] - b[1] > 4)""")
    cards = Image.open(io.BytesIO(page.screenshot()))
    tag2 = page.add_style_tag(content=":is(.card, li.unit) { visibility: hidden !important; }")
    bare = Image.open(io.BytesIO(page.screenshot()))
    page.evaluate("els => els.forEach(e => e.remove())", [tag, tag2])
    in_cards = [extreme(cards, b, darkest) for b in boxes]
    pick = min if darkest else max
    return extreme(bare, (16, top, w - 16, bottom), darkest), (pick(in_cards, key=lum) if in_cards else None), len(boxes), extreme(bare, vt, darkest)

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

    print("\n--- 1. How the paper is drawn ---")
    blocks = [style[style.index(sel):] for sel in ('[data-t="parchment"] {', '[data-t="parchment"][data-m="dark"] {', '[data-t="parchment"][data-m="light"] {')]
    blocks = [b[:b.index("\n    }")] for b in blocks]
    paper = [v for b in blocks for v in re.findall(r"--(?:texture|paper-grain|paper-shade|paper-size|card-stain|card-stain-2|ink-a|ink-b|soot-a|soot-b|tide): ([^\n]*);", b)]
    urls = [u for v in paper for u in re.findall(r"url\((?!%23)(.{0,40})", v)]
    check("the only picture in the paper is an inline SVG grain tile (no file, no other site)", urls and all(u.startswith('"data:image/svg+xml,') for u in urls), urls)
    rules = style[style.index("/* TH3: red ink"):]
    rules = rules[:rules.index("/* Grim Forge")]
    size = sum(len(v) for v in paper) + len(rules)
    print(f"     (paper tokens and rules: {size} bytes)")
    check(f"the added texture stays under {SIZE_LIMIT} bytes", size < SIZE_LIMIT, size)
    check("no filter or blend mode in the TH3 rules", not re.search(r"(?<![-\w])filter:|mix-blend-mode|backdrop-filter", rules), rules[:200])

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("request", lambda r: outside.append(r.url) if r.resource_type in ("font", "image") and not r.url.startswith((t.BASE, "data:", "blob:")) and "goatcounter.com" not in r.url else None)

        print("\n--- 2. The theme loads, and the paper lines up ---")
        t.load(page, units=UNITS, settings={"theme": "parchment", "appearance": "light", "examplesChecked": True}, launch=True)
        start = page.evaluate("""() => { const f = getComputedStyle(document.querySelector('.tabs'), '::before');
            return { t: document.documentElement.dataset.t, m: document.documentElement.dataset.m, launching: document.body.classList.contains('launching'),
                     mask: f.maskImage || f.webkitMaskImage, glow: f.backgroundImage }; }""")
        check("a saved Parchment setting loads Parchment Codex light", start["t"] == "parchment" and start["m"] == "light", start)
        check("start page: the fade is not masked, so the whole glow round the circle shows", start["launching"] and start["mask"] == "none" and "radial-gradient" in start["glow"], start)
        t.leave_launch(page)
        page.click('.tabs button[data-tab="units"]'); quiet(page)
        line = page.evaluate("""() => { const tabs = document.querySelector('.tabs'), bar = document.querySelector('.app-bar');
            const L = getComputedStyle(document.body, '::before'), B = getComputedStyle(bar), F = getComputedStyle(tabs, '::before');
            const h = s => parseFloat(s.backgroundSize.split(', ')[0].split(' ')[1]);
            const fadeTop = tabs.getBoundingClientRect().bottom - parseFloat(F.height);
            return { layer: [parseFloat(L.top), h(L), parseFloat(L.height)], bar: [bar.getBoundingClientRect().top + parseFloat(B.backgroundPositionY), h(B)],
                     fade: [fadeTop + parseFloat(F.backgroundPositionY), h(F)], same: L.backgroundImage === B.backgroundImage && B.backgroundImage === F.backgroundImage,
                     body: getComputedStyle(document.body).backgroundImage, card: getComputedStyle(document.querySelector('li.unit')).backgroundImage }; }""")
        tops = [line["layer"][0], line["bar"][0], line["fade"][0]]
        heights = [line["layer"][1], line["layer"][2], line["bar"][1], line["fade"][1]]
        check("the page layer, the header and the fade show the same paper, all measured from the top of the screen at the same height",
              line["same"] and line["body"] == "none" and all(abs(v) < 1 for v in tops) and max(heights) - min(heights) < 1, line)
        check("unit rows carry a corner stain", "radial-gradient" in line["card"], line["card"][:80])

        print("\n--- 3. Readability on the drawn paper, and the reds kept apart ---")
        names = TEXT + ["--border", "--on-accent", "--series-painted", "--accent-fill"]
        for mode, w, h in (("light", 390, 844), ("dark", 360, 640)):
            page.set_viewport_size({"width": w, "height": h})
            if mode == "dark":
                t.load(page, units=UNITS, settings={"theme": "parchment", "appearance": "dark", "examplesChecked": True})
                page.click('.tabs button[data-tab="units"]'); quiet(page)
            page.wait_for_timeout(150)
            darkest = mode == "light"
            col, card, n, tag = paper_extremes(page, darkest)
            v = dict(zip(names, colours(page, names)))
            fill = v["--accent-fill"]
            print(f"     ({mode}: worst page point {col}, worst card point {card}, header {tag})")
            low = [(k, round(ratio(v[k], col), 2)) for k in TEXT if ratio(v[k], col) < 4.5]
            check(f"{mode} {w}px: every text colour reads at 4.5:1 on the {'darkest' if darkest else 'lightest'} point of the page paper", not low, low)
            low = [(k, round(ratio(v[k], card), 2)) for k in TEXT if card and ratio(v[k], card) < 4.5]
            check(f"{mode} {w}px: every text colour reads at 4.5:1 inside the cards, stains included ({n} cards)", n >= 3 and not low, (n, low))
            check(f"{mode} {w}px: the small version number in the header reads at 4.5:1 on the header paper", ratio(v["--muted"], tag) >= 4.5, round(ratio(v["--muted"], tag), 2))
            check(f"{mode} {w}px: borders reach 3:1 on the worst point of the paper", ratio(v["--border"], col) >= 3, round(ratio(v["--border"], col), 2))
            check(f"{mode}: button text reads at 4.5:1 on the crimson fill", ratio(v["--on-accent"], fill) >= 4.5, round(ratio(v["--on-accent"], fill), 2))
            row = current_guides_row(page, darkest)
            check(f"{mode}: crimson text reads at 4.5:1 on the highlighted Guides row", ratio(v["--accent"], row) >= 4.5, (row, round(ratio(v["--accent"], row), 2)))
            bad = v["--bad"]
            gaps = {"bad/crimson": de2000(bad, v["--accent"]), "bad/crimson fill": de2000(bad, fill), "bad/caution": de2000(bad, v["--caution"])}
            need = {"bad/crimson": 15, "bad/crimson fill": 15, "bad/caution": 20 if mode == "dark" else 14}
            check(f"{mode}: bad is told apart from the crimson and from caution (CIEDE2000)", all(gaps[k] >= need[k] for k in gaps), {k: round(x, 1) for k, x in gaps.items()})
            check(f"{mode}: the Done line on the progress chart uses the good green", v["--series-painted"] == v["--good"], (v["--series-painted"], v["--good"]))
            t.shot(page, f"v124_th3_{mode}.png")

        print("\n--- 4. Print and the other themes ---")
        page.emulate_media(media="print")
        printed = page.evaluate("() => [getComputedStyle(document.body, '::before').content, getComputedStyle(document.querySelector('.app-bar')).backgroundImage]")
        check("the paper is not printed", printed == ["none", "none"], printed)
        page.emulate_media(media="screen")
        page.evaluate("() => { document.querySelector('.tabs button[data-tab=\"guides\"]').click(); document.querySelector('#more-seg button[data-page=\"settings\"]').click(); }")
        quiet(page)
        bars = page.evaluate("""() => [...document.querySelectorAll('.theme-swatch')].map(s => { const d = document.createElement('i'); d.style.color = getComputedStyle(s).getPropertyValue('--accent');
            s.append(d); const a = getComputedStyle(d).color; d.remove(); return [s.dataset.t, getComputedStyle(s.querySelector('.ts-bar')).backgroundColor, a]; })""")
        check("Parchment dark: the other themes' squares keep their own accent on their bar", len(bars) >= 4 and all(f == a for k, f, a in bars if k != "parchment"), bars)
        t.load(page, units=UNITS, settings={"theme": "forge", "appearance": "light", "examplesChecked": True})
        other = page.evaluate("() => ({ layer: getComputedStyle(document.body, '::before').content, bar: getComputedStyle(document.querySelector('.app-bar')).backgroundImage })")
        check("Grim Forge gets no paper layer and a plain header", other["layer"] == "none" and other["bar"] == "none", other)
        check("no font or picture loads from another site", not outside, outside)
        browser.close()

    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
