"""TH6 tests for Minifolio (more personality for the looks, and a distinct set of fonts for each). New behaviour only:
1. Fonts: no two looks share a title, body or number face; every font file is our own woff2, small, and its family has a licence
   (SIL OFL or Apache) in fonts/LICENSES.md; every look's font stack has a fallback sized to match it; Parchment Codex uses lining,
   tabular figures and never fakes bold or italic; Paint Bench writes its stencilled name in sentence case.
2. A look downloads only its own fonts (counted from the requests after choosing it), and Settings adds only the tiny name-only files
   for the Theme squares. The fallbacks keep the title and a unit row the same height when the real fonts arrive.
3. The new marks (Parchment Codex ink, Grim Forge bolts, cogs and rust, Paint Bench brush strokes, smudges and stickers) are CSS and
   inline SVG only, under 15 KB per look, with no filter or blend mode; the page-layer and header marks stay in the 16 px margins, out of
   the column where text sits; every text colour reads at 4.5:1 on the worst point of the page column and inside the cards, marks
   included, in light and dark; the start-page ink spray in Parchment Codex never sits under text.
4. Grim Forge: hex bolts on the header's rule and the cards' top corners, cogs on the header and the page, and the rust colour told apart
   from the forge orange, the brass and the bad red (CIEDE2000 12 or more). Paint Bench: three stickers and three brush strokes, none
   of which can be tapped.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import io, json, math, os, re, sys
from playwright.sync_api import sync_playwright
from PIL import Image, ImageChops

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import quiet, leave_launch, open_settings, app_ready

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

LOOKS = ["classic", "forge", "parchment", "bench"]
LIMIT = 15000   # bytes of new decoration per look (the brief: under about 15 KB)
TEXT = ["--text", "--muted", "--accent", "--heading-colour", "--good", "--bad", "--warn", "--caution", "--wish", "--grey-status", "--note", "--danger"]
UNITS = [{"id": i, "name": f"Unit {i}", "hobby": "Test game", "stage": i % 6, "count": 5, "added": "2026-10-01", "log": [["2026-10-01", 1]]} for i in range(1, 7)]
OWN = {   # the font files each look may download on its own screens
    "classic": {"oxanium-latin-600-normal", "chakra-petch-latin-400-normal", "chakra-petch-latin-600-normal", "azeret-mono-latin-500-normal"},
    "forge": {"anton-latin-400-normal", "barlow-latin-400-normal", "barlow-latin-500-normal", "barlow-latin-600-normal"},
    "parchment": {"grenze-gotisch-latin-500-normal", "eb-garamond-lnum-latin-400-normal", "eb-garamond-lnum-latin-500-normal", "eb-garamond-lnum-latin-400-italic"},
    "bench": {"atkinson-hyperlegible-latin-400-normal", "atkinson-hyperlegible-latin-700-normal", "big-shoulders-stencil-latin-700-normal",
              "dm-mono-latin-400-normal", "dm-mono-latin-500-normal", "permanent-marker-latin-400-normal"},
}
NAMES = {"theme-name-classic", "theme-name-parchment", "theme-name-forge", "theme-name-bench"}

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

def shot(page):
    return Image.open(io.BytesIO(page.screenshot())).convert("RGB")

def extreme(img, box, darkest):
    crop = img.crop(tuple(int(round(v)) for v in box))
    px = list(crop.get_flattened_data() if hasattr(crop, "get_flattened_data") else crop.getdata())
    return (min if darkest else max)(px, key=lum)

def first(family):
    return family.split(",")[0].strip().strip('"\'')

def set_look(page, th, m):
    page.evaluate("([th, m]) => { Object.assign(settings, { theme: th, appearance: m }); applyPalette(settings.palette); }", [th, m])
    quiet(page)

def new_page(browser, th, m="dark", w=390, h=844, block_fonts=False):
    ctx = browser.new_context(viewport={"width": w, "height": h}, service_workers="block", reduced_motion="reduce")
    ctx.add_init_script(f"""try {{ localStorage.setItem('shades-of-grey-settings', JSON.stringify({json.dumps({"theme": th, "appearance": m, "examplesChecked": True})}));
        localStorage.setItem('mini-tracker-models', {json.dumps(json.dumps(UNITS))}); }} catch (e) {{}}""")
    if block_fonts:
        ctx.route("**/*.woff2", lambda r: r.abort())
    page = ctx.new_page()
    fonts = []
    page.on("request", lambda r: fonts.append(r.url) if r.url.endswith(".woff2") else None)
    page.goto(t.URL)
    app_ready(page)
    return ctx, page, fonts

# The name and the first unit row measured with the real fonts, then with each element's first font dropped, so the next one (its sized local
# fallback) draws it; the fallbacks are fonts on the phone, so nothing has to download. Also returns whether those fallback faces loaded.
MEASURE_FALLBACK = """async () => { const els = [document.querySelector('h1 .home'), ...document.querySelectorAll('li.unit, li.unit *')];
    const size = () => { const a = document.querySelector('h1 .home').getBoundingClientRect(); return [a.width, a.height, document.querySelector('li.unit').getBoundingClientRect().height]; };
    const real = size(), names = new Set();
    for (const e of els) { const f = getComputedStyle(e).fontFamily; const rest = f.split(',').slice(1).join(','); names.add(rest.split(',')[0].trim()); e.style.fontFamily = rest; }
    await document.fonts.ready; const fb = size();
    for (const e of els) e.style.fontFamily = '';
    const loaded = [...names].filter(n => / Fallback/.test(n)).every(n => document.fonts.check('16px ' + n));
    return [real, fb, loaded]; }"""

HIDE_CONTENT = "main, .tabs, .back-menu, .mentor-orb, h1, .app-actions { visibility: hidden !important; }"
NO_MARKS = "body::after, .app-bar::before, .app-bar::after { content: none !important; }"
CARDS_BARE = "body * { visibility: hidden !important; } :is(.card, li.unit) { visibility: visible !important; } :is(.card, li.unit) * { visibility: hidden !important; }"

def main():
    html = t.read("index.html")
    style = html[html.index("<style>"):html.index("</style>")]
    licences = t.read("fonts/LICENSES.md")
    block = style[style.index("    /* TH6: "):style.index("/* TH6 end */")]

    print("\n--- 1. Fonts: files, licences, fallbacks ---")
    faces = re.findall(r"@font-face \{[^}]*\}", style)
    files = [(re.search(r"font-family: '([^']+)'", f).group(1), re.search(r"url\(fonts/([\w-]+\.woff2)\)", f).group(1)) for f in faces if "url(fonts/" in f]
    bad = [n for _, n in files if not os.path.exists(os.path.join(t.ROOT, "fonts", n)) or open(os.path.join(t.ROOT, "fonts", n), "rb").read(4) != b"wOF2"
           or os.path.getsize(os.path.join(t.ROOT, "fonts", n)) > 40_000]
    check("every font the page names is our own woff2 file in fonts/, under 40 KB", files and not bad, bad)
    sections = {s.split("\n", 1)[0].strip(): s for s in re.split(r"(?m)^## ", licences)[1:]}
    unlicensed = []
    for fam, _ in files:
        base = fam.replace(" Theme Name", "")
        if fam not in sections or base not in sections or not re.search(r"SIL Open Font License|Apache License", sections[base]):
            unlicensed.append(fam)
    check("every font family has its licence (SIL OFL or Apache) in fonts/LICENSES.md, the name-only files under their source font", not unlicensed, unlicensed)
    fallbacks = {re.search(r"font-family: '([^']+) Fallback'", f).group(1) for f in faces if "Fallback'" in f and "local(" in f and "size-adjust" in f and "ascent-override" in f}
    stacks = re.findall(r"--font-(?:heading|body|num): ([^;]+);", style)
    unfit = [s for s in stacks if first(s) not in ("system-ui", "inherit") and (first(s) not in fallbacks or f"'{first(s)} Fallback'" not in s)]
    check("every look's font stack names a local fallback sized to match its first font", stacks and not unfit, unfit)
    check("no font, stylesheet or picture comes from another site", not re.search(r"url\((?!fonts/|\"data:|var)", block) and "@import" not in style)

    print("\n--- 2. The new marks: how they are drawn and how big ---")
    # each look's marks are one section of the TH6 block (from its comment to the next look's), plus the shared layer rule and the print rule
    marks = block[block.index("/* The extra marks"):]
    starts = {th: marks.index(head) for th, head in (("parchment", "/* Parchment Codex: more ink"), ("forge", "/* Grim Forge: hex bolts"), ("bench", "/* Paint Bench: faint"))}
    shared = len(marks[:starts["parchment"]]) + len(marks[marks.index("@media print"):])
    for th, nxt in (("parchment", "forge"), ("forge", "bench"), ("bench", None)):
        section = marks[starts[th]:starts[nxt] if nxt else marks.index("@media print")]
        size = len(section) + shared
        print(f"     ({th}: {size} bytes)")
        check(f"{th}: the new marks are under {LIMIT // 1000} KB", 0 < size < LIMIT, size)
    check("the marks are CSS and inline SVG only, with no filter or blend mode and no px font size",
          not re.search(r"(?<![-\w])filter:|mix-blend-mode|backdrop-filter|font-size:\s*[\d.]+px", block)
          and all(u.startswith('"data:image/svg+xml,') for u in re.findall(r"url\(([^)]{0,30})", block) if not u.startswith("fonts/")), "")

    with sync_playwright() as p:
        browser = p.chromium.launch()

        print("\n--- 3. Each look's own fonts, and only those ---")
        faces_seen, jumps = {}, {}
        for th in LOOKS:
            ctx, page, fonts = new_page(browser, th)
            leave_launch(page)
            for tab in ("units", "dashboard"):
                page.evaluate(f"() => document.querySelector('.tabs button[data-tab=\"{tab}\"]').click()"); quiet(page)
            page.evaluate("document.fonts.ready"); page.wait_for_timeout(250)
            own = {u.split("/")[-1][:-6] for u in fonts}
            page.evaluate("() => document.querySelector('.tabs button[data-tab=\"units\"]').click()"); quiet(page)
            page.evaluate("document.fonts.ready"); page.wait_for_timeout(150)
            jumps[th] = page.evaluate(MEASURE_FALLBACK)
            faces_seen[th] = page.evaluate("""() => { const f = s => { const e = document.querySelector(s); return e ? getComputedStyle(e).fontFamily : ''; };
                return { title: f('h1'), card: f('.card h2'), body: f('body'), num: f('.group-button strong'), h1t: getComputedStyle(document.querySelector('h1')).textTransform,
                         nums: getComputedStyle(document.querySelector('.group-button strong')).fontVariantNumeric, bodynums: getComputedStyle(document.body).fontVariantNumeric,
                         synth: getComputedStyle(document.body).fontSynthesis }; }""")
            check(f"{th}: its screens download only its own fonts, its title font among them",
                  own and own <= OWN[th] and (OWN[th] & own) and all(u.startswith(t.BASE) for u in fonts), sorted(own))
            before = len(fonts)
            open_settings(page); page.evaluate("document.querySelector('#theme-card').scrollIntoView()")
            page.evaluate("document.fonts.ready"); page.wait_for_timeout(300)
            extra = {u.split("/")[-1][:-6] for u in fonts[before:]}
            check(f"{th}: Settings adds only the name-only files for the Theme squares (under 12 KB together)",
                  extra <= NAMES and sum(os.path.getsize(os.path.join(t.ROOT, "fonts", n + ".woff2")) for n in NAMES) < 12_000, sorted(extra))
            ctx.close()
        roles = {r: {th: first(faces_seen[th][k]) for th in LOOKS} for r, k in (("title", "title"), ("card title", "card"), ("body", "body"), ("number", "num"))}
        print("     " + json.dumps(roles))
        for role, by in roles.items():
            check(f"no two looks share a {role} face", len(set(by.values())) == 4, by)
        pa, be = faces_seen["parchment"], faces_seen["bench"]
        check("Parchment Codex: lining figures everywhere, tabular in counts, no faked bold or italic",
              "lining-nums" in pa["bodynums"] and "lining-nums" in pa["nums"] and "tabular-nums" in pa["nums"] and pa["synth"] == "none", pa)
        check("Paint Bench: the stencilled name in sentence case, the tape in marker", be["h1t"] == "none" and first(be["title"]) == "Big Shoulders Stencil"
              and first(be["card"]) == "Permanent Marker", be)

        print("\n--- 4. No jump when the fonts arrive ---")
        for th in LOOKS:
            (w1, h1, u1), (w0, h0, u0), fb = jumps[th]
            if not fb:
                # T6: the fallback faces use fonts a machine has to have installed (Arial or Helvetica or Roboto, Times New Roman or Times or
                # Noto Serif, Courier New or Courier). A bare Linux container has none, so there is nothing to compare: say so out loud and leave
                # this one check out, instead of failing on a machine that cannot run it. Every machine with those fonts still runs it.
                print(f"SKIP {th}: no fallback font is installed on this machine, so the no-jump check cannot run here")
                continue
            check(f"{th}: with the fallbacks the name and a unit row take the same room as with the real fonts",
                  fb and abs(h0 - h1) <= 2 and abs(u0 - u1) <= 4 and abs(w0 - w1) <= 0.2 * w1, jumps[th])

        print("\n--- 5. Where the marks sit, and text over them ---")
        ctx, page, _ = new_page(browser, "parchment", "light")
        leave_launch(page)
        page.evaluate("() => document.querySelector('.tabs button[data-tab=\"dashboard\"]').click()"); quiet(page)
        for th in ("parchment", "forge", "bench"):
            for m, (w, h) in (("light", (390, 844)), ("dark", (360, 640))):
                page.set_viewport_size({"width": w, "height": h})
                set_look(page, th, m); page.evaluate("window.scrollTo(0, 0)"); page.wait_for_timeout(150)
                darkest = m == "light"
                tag = page.add_style_tag(content=HIDE_CONTENT)
                with_marks = shot(page)
                tag2 = page.add_style_tag(content=NO_MARKS)
                without = shot(page)
                page.evaluate("els => els.forEach(e => e.remove())", [tag, tag2])
                diff = ImageChops.difference(with_marks, without).convert("L").point(lambda v: 255 if v > 3 else 0)
                inside = diff.crop((16, 0, w - 16, h)).getbbox()
                outside = diff.getbbox()
                top = page.evaluate("Math.ceil(document.querySelector('.app-bar').getBoundingClientRect().bottom)")
                bottom = page.evaluate("Math.floor(innerHeight - parseFloat(getComputedStyle(document.querySelector('.tabs'), '::before').height) * 0.4)")
                col = extreme(with_marks, (16, top, w - 16, bottom), darkest)
                tag = page.add_style_tag(content=CARDS_BARE)
                boxes = page.evaluate("""() => [...document.querySelectorAll('.card, li.unit')].filter(c => c.getClientRects().length).map(c => { const r = c.getBoundingClientRect(), s = getComputedStyle(c);
                    const px = (p) => parseFloat(s['border' + p + 'Width']) + parseFloat(s['padding' + p]);
                    return [r.left + px('Left'), Math.max(0, r.top + px('Top')), r.right - px('Right'), Math.min(innerHeight, r.bottom - px('Bottom'))]; }).filter(b => b[3] - b[1] > 4)""")
                cards = shot(page)
                tag.evaluate("e => e.remove()")
                pts = [extreme(cards, b, darkest) for b in boxes]
                card = (min if darkest else max)(pts, key=lum) if pts else None
                v = dict(zip(TEXT, colours(page, TEXT)))
                worst = min((min(ratio(v[k], col), ratio(v[k], card) if card else 99), k) for k in TEXT)
                print(f"     ({th} {m}: lowest text contrast {worst[0]:.2f}:1 ({worst[1]}), worst page point {col}, worst card point {card})")
                low = [(k, round(min(ratio(v[k], col), ratio(v[k], card) if card else 99), 2)) for k in TEXT if min(ratio(v[k], col), ratio(v[k], card) if card else 99) < 4.5]
                check(f"{th} {m} {w}px: the new marks are drawn ({outside}) and stay out of the text column; every text colour reads at 4.5:1 on the page column and in {len(boxes)} cards",
                      outside and inside is None and len(boxes) >= 3 and not low, (inside, low))
                if th == "forge":
                    rust, acc, brass, bad_ = colours(page, ["--rust", "--accent", "--brass", "--bad"])
                    gaps = {"orange": de2000(rust, acc), "brass": de2000(rust, brass), "bad": de2000(rust, bad_)}
                    check(f"forge {m}: the rust is told apart from the forge orange, the brass and the bad red (CIEDE2000 12 or more)",
                          all(g >= 12 for g in gaps.values()), {k: round(g, 1) for k, g in gaps.items()})
        set_look(page, "forge", "dark")
        page.evaluate("() => document.querySelector('.tabs button[data-tab=\"units\"]').click()"); quiet(page)
        fx = page.evaluate("""() => { const bg = (e, p) => getComputedStyle(e, p).backgroundImage, svg = s => (s.match(/data:image\\/svg/g) || []).length;
            const card = [...document.querySelectorAll('.card')].find(c => c.getClientRects().length), unit = document.querySelector('li.unit');
            return { bar: svg(bg(document.querySelector('.app-bar'), '::before')), cog: svg(bg(document.querySelector('.app-bar'), '::after')), layer: svg(bg(document.body, '::after')),
                     unit: [svg(bg(unit)), bg(unit).split('closest-side at 42% 40%').length - 1], card: card ? [svg(bg(card)), bg(card).split('closest-side at 42% 40%').length - 1] : null }; }""")
        check("Grim Forge: two hex bolts on the header's rule, a cog behind its corner and one on the page; unit rows keep four rivets",
              fx["bar"] == 2 and fx["cog"] == 1 and fx["layer"] == 1 and fx["unit"][1] == 4, fx)
        set_look(page, "bench", "light")
        bn = page.evaluate("""() => { const s = getComputedStyle(document.body, '::after'); return [(s.backgroundImage.match(/data:image\\/svg/g) || []).length, s.pointerEvents, s.position]; }""")
        check("Paint Bench: three stickers and three brush strokes on a fixed layer that cannot be tapped", bn == [6, "none", "fixed"], bn)
        ctx.close()

        print("\n--- 6. The start page spray (Parchment Codex) ---")
        ctx, page, _ = new_page(browser, "parchment", "light")
        for w, h in ((320, 568),):   # the smallest phone, where the circle comes closest to the header
            page.set_viewport_size({"width": w, "height": h})
            page.evaluate("document.fonts.ready"); page.wait_for_timeout(400)
            tag = page.add_style_tag(content=".tabs, h1, .app-actions { visibility: hidden !important; }")
            a = shot(page)
            tag2 = page.add_style_tag(content=NO_MARKS)
            b = shot(page)
            page.evaluate("els => els.forEach(e => e.remove())", [tag, tag2])
            box = ImageChops.difference(a, b).convert("L").point(lambda v: 255 if v > 3 else 0).crop((16, 0, w - 16, h)).getbbox()
            texts = page.evaluate("""() => { const out = []; const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                while (walk.nextNode()) { const n = walk.currentNode; if (!n.textContent.trim()) continue; const r = document.createRange(); r.selectNodeContents(n);
                  for (const q of r.getClientRects()) if (q.width && q.bottom > 0 && q.top < innerHeight) out.push([q.left, q.top, q.right, q.bottom]); } return out; }""")
            hit = [r for r in texts if box and r[0] < box[2] + 16 and r[2] > box[0] + 16 and r[1] < box[3] and r[3] > box[1]]
            check(f"start page {w}px: the ink spray is drawn in the empty paper and under no text", box and page.evaluate("document.body.classList.contains('launching')") and not hit, (box, hit))
        ctx.close()
        browser.close()

    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
