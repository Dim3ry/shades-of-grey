"""TH3 tests for Minifolio (Parchment Codex restyle: red ink on parchment, with grain, ink stains and edge stains). New behaviour only:
1. The paper is drawn with CSS gradients and one small inline SVG noise tile (a data: picture), nothing loaded from another site,
   and the added texture stays under the size limit reported in the pull request.
2. A saved Parchment setting still loads the theme; the paper sits on one fixed layer behind the page, the header and the fade
   behind the bar show the same paper, and nothing on the page uses a fixed background (so scrolling does not repaint it).
3. Readability, measured on the drawn texture: every text colour reads at 4.5 to 1 against the darkest (light mode) or lightest
   (dark mode) point of the paper where text can sit (the page column, the inside of the cards and the header's small
   version number), and borders at 3 to 1.
4. The crimson accent leans blue-red and the "bad" red leans orange-red, so they are not mixed up.
5. The other themes do not get the paper layer.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import colorsys, io, os, re, sys
from playwright.sync_api import sync_playwright
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import quiet

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

SIZE_LIMIT = 8000   # bytes of texture tokens (both modes) plus the TH3 rules; about 6.3 KB at the time of writing
TEXT = ["--text", "--muted", "--accent", "--heading-colour", "--good", "--bad", "--warn", "--caution", "--wish", "--grey-status", "--note", "--danger"]
UNITS = [{"id": i, "name": f"Unit {i}", "hobby": "40K", "stage": i % 6, "count": 5, "added": "2026-10-01", "log": [["2026-10-01", 1]]} for i in range(1, 7)]

def lum(c):
    v = [x / 255 for x in c[:3]]
    v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]

def ratio(a, b):
    a, b = lum(a), lum(b)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)

def hue(c):
    return colorsys.rgb_to_hls(*[x / 255 for x in c[:3]])[0] * 360

def colours(page, names):
    return page.evaluate("""names => names.map(n => { const d = document.createElement('i'); d.style.color = getComputedStyle(document.documentElement).getPropertyValue(n);
        document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c.match(/[\\d.]+/g).slice(0, 3).map(Number); })""", names)

def extreme(img, box, darkest):
    px = list(img.crop(tuple(int(round(v)) for v in box)).convert("RGB").getdata())
    return (min if darkest else max)(px, key=lum)

def paper_extremes(page, darkest):
    """The worst point of the paper in the page column (between the header and the solid part of the fade behind the bar),
    and inside the content boxes of the cards and unit rows, with everything else hidden."""
    w, h = page.viewport_size["width"], page.viewport_size["height"]
    top = page.evaluate("Math.ceil(document.querySelector('.app-bar').getBoundingClientRect().bottom)")
    bottom = page.evaluate("Math.floor(innerHeight - parseFloat(getComputedStyle(document.querySelector('.tabs'), '::before').height) * 0.4)")
    vt = page.evaluate("(() => { const r = document.querySelector('h1 .version-tag').getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; })()")
    page.add_style_tag(content="body * { visibility: hidden !important; } :is(.card, li.unit) { visibility: visible !important; } :is(.card, li.unit) * { visibility: hidden !important; }")
    boxes = page.evaluate("""() => [...document.querySelectorAll('.card, li.unit')].filter(c => c.getClientRects().length).map(c => { const r = c.getBoundingClientRect(), s = getComputedStyle(c);
        const px = (p) => parseFloat(s['border' + p + 'Width']) + parseFloat(s['padding' + p]);
        return [r.left + px('Left'), Math.max(0, r.top + px('Top')), r.right - px('Right'), Math.min(innerHeight, r.bottom - px('Bottom'))]; }).filter(b => b[3] - b[1] > 4)""")
    cards = Image.open(io.BytesIO(page.screenshot()))
    page.add_style_tag(content=":is(.card, li.unit) { visibility: hidden !important; }")
    bare = Image.open(io.BytesIO(page.screenshot()))
    page.evaluate("() => document.querySelectorAll('style').forEach(s => { if (s.textContent.includes('visibility: hidden !important')) s.remove(); })")
    in_cards = [extreme(cards, b, darkest) for b in boxes]
    return extreme(bare, (16, top, w - 16, bottom), darkest), ((min if darkest else max)(in_cards, key=lum) if in_cards else None), len(boxes), extreme(bare, vt, darkest)

def main():
    errors, dialogs, outside = [], [], []
    html = t.read("index.html")
    style = html[html.index("<style>"):html.index("</style>")]

    print("\n--- 1. How the paper is drawn ---")
    blocks = {m: style[style.index(f'[data-t="parchment"][data-m="{m}"] {{'):] for m in ("light", "dark")}
    blocks = {m: b[:b.index("\n    }")] for m, b in blocks.items()}
    paper = {m: re.findall(r"--(?:texture|paper-grain|card-stain|card-stain-2|swatch-texture): ([^\n]*);", b) for m, b in blocks.items()}
    urls = [u for m in paper for v in paper[m] for u in re.findall(r"url\((?!%23)(.{0,40})", v)]
    check("both modes define the paper, the card stains and the grain", all(len(v) == 5 for v in paper.values()), {m: len(v) for m, v in paper.items()})
    check("the only picture in the paper is an inline SVG noise tile (no file, no other site)", urls and all(u.startswith('"data:image/svg+xml,') for u in urls), urls)
    rules = style[style.index("/* TH3:"):]
    rules = rules[:rules.index(".theme-swatch[data-t=\"parchment\"] {")]
    size = sum(len(v) for m in paper for v in paper[m]) + len(rules)
    check(f"the added texture stays under {SIZE_LIMIT} bytes", size < SIZE_LIMIT, size)
    check("no filter or blend mode in the TH3 rules", not re.search(r"(?<![-\w])filter:|mix-blend-mode|backdrop-filter", rules), rules[:200])

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        page.on("request", lambda r: outside.append(r.url) if r.resource_type in ("font", "image") and not r.url.startswith((t.BASE, "data:", "blob:")) and "goatcounter.com" not in r.url else None)

        print("\n--- 2. The theme loads from the saved setting, and the paper layer ---")
        t.load(page, units=UNITS, settings={"theme": "parchment", "appearance": "light", "examplesChecked": True})
        page.click('.tabs button[data-tab="units"]'); quiet(page)
        look = page.evaluate("""() => { const b = getComputedStyle(document.body), layer = getComputedStyle(document.body, '::before'),
            bar = getComputedStyle(document.querySelector('.app-bar')), fade = getComputedStyle(document.querySelector('.tabs'), '::before');
            return { t: document.documentElement.dataset.t, m: document.documentElement.dataset.m, body: b.backgroundImage, layer: layer.backgroundImage, pos: layer.position, z: layer.zIndex,
                     bar: bar.backgroundImage, fade: fade.backgroundImage, fixed: [document.body, ...document.querySelectorAll('body *')].filter(e => getComputedStyle(e).backgroundAttachment.includes('fixed')).length }; }""")
        check("a saved Parchment setting loads Parchment Codex light", look["t"] == "parchment" and look["m"] == "light", look)
        check("the paper is one fixed layer behind the page (the body itself has no picture)",
              look["body"] == "none" and look["pos"] == "fixed" and look["z"] == "-1" and look["layer"].count("gradient(") >= 8 and "data:image/svg+xml" in look["layer"], look)
        check("the header and the fade behind the bar show the same paper", look["bar"] == look["layer"] and look["fade"] == look["layer"])
        sizes = page.evaluate("""() => [getComputedStyle(document.body, '::before'), getComputedStyle(document.querySelector('.app-bar')), getComputedStyle(document.querySelector('.tabs'), '::before')]
            .map(s => { const z = s.backgroundSize.split(', '); return [s.backgroundImage.split('gradient(').length - 1, z.length - 1, z.filter(v => v === '180px 180px').length, z.pop()]; })""")
        check("each of the three sizes only the grain (the last layer) as a small tile", all(g == k and small == 1 and last == "180px 180px" for g, k, small, last in sizes), sizes)
        check("on a phone nothing uses a fixed background, so scrolling does not repaint the paper", look["fixed"] == 0, look["fixed"])
        some = page.evaluate("""() => [...document.querySelectorAll('li.unit')].map(li => getComputedStyle(li).backgroundImage)""")
        check("unit rows carry a corner stain, two kinds in turn", all("radial-gradient" in s for s in some) and len(set(some)) == 2, some[:3])

        print("\n--- 3. Readability on the drawn paper ---")
        for mode, w, h in (("light", 390, 844), ("dark", 360, 640)):
            page.set_viewport_size({"width": w, "height": h})
            if mode == "dark":
                t.load(page, units=UNITS, settings={"theme": "parchment", "appearance": "dark", "examplesChecked": True})
                page.click('.tabs button[data-tab="units"]'); quiet(page)
            page.wait_for_timeout(150)
            darkest = mode == "light"
            col, card, n, tag = paper_extremes(page, darkest)
            vals = dict(zip(TEXT + ["--border", "--accent", "--on-accent"], colours(page, TEXT + ["--border", "--accent", "--on-accent"])))
            low = [(k, round(ratio(vals[k], col), 2)) for k in TEXT if ratio(vals[k], col) < 4.5]
            check(f"{mode} {w}px: every text colour reads at 4.5:1 on the {'darkest' if darkest else 'lightest'} point of the page paper {col}", not low, low)
            low = [(k, round(ratio(vals[k], card), 2)) for k in TEXT if card and ratio(vals[k], card) < 4.5]
            check(f"{mode} {w}px: every text colour reads at 4.5:1 inside the cards, stains included ({n} cards)", n >= 3 and not low, (n, low))
            check(f"{mode} {w}px: the small version number in the header reads at 4.5:1 on the header paper", ratio(vals["--muted"], tag) >= 4.5, round(ratio(vals["--muted"], tag), 2))
            check(f"{mode} {w}px: borders reach 3:1 on the worst point of the paper", ratio(vals["--border"], col) >= 3, round(ratio(vals["--border"], col), 2))
            check(f"{mode} {w}px: button text reads at 4.5:1 on the crimson", ratio(vals["--on-accent"], vals["--accent"]) >= 4.5)
            acc, bad = hue(vals["--accent"]), hue(vals["--bad"])
            check(f"{mode}: the crimson leans blue-red and the bad red leans orange-red", 335 <= acc <= 358 and 5 <= bad <= 30 and (bad - acc) % 360 >= 15, (round(acc), round(bad)))
            for narrow in (320,):
                page.set_viewport_size({"width": narrow, "height": 640})
                check(f"{mode} {narrow}px: no sideways scroll", t.no_sideways(page))
            t.shot(page, f"v124_th3_{mode}.png")

        print("\n--- 4. The other themes ---")
        t.load(page, units=UNITS, settings={"theme": "forge", "appearance": "light", "examplesChecked": True})
        other = page.evaluate("() => ({ layer: getComputedStyle(document.body, '::before').content, bar: getComputedStyle(document.querySelector('.app-bar')).backgroundImage })")
        check("Grim Forge gets no paper layer and a plain header", other["layer"] == "none" and other["bar"] == "none", other)

        check("no font or picture loads from another site", not outside, outside)
        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()

    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
