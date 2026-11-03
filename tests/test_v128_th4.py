"""TH4 tests for Minifolio (Paint Bench as the plain hobby desk: lighter, warmer desk colours, a quieter cutting-mat grid, a cork tint at the
page edges, paler masking tape with a little crepe texture, a less saturated yellow accent, and no tilted main button). New behaviour only:
1. The desk is drawn with CSS gradients only (no picture, nothing from another site), small, with no filter or blend mode.
2. A saved Paint Bench setting loads the theme, and the page and the phone's top bar take the new desk colour before app.js runs.
3. No resting transform on the main button or on any button, link or field (or anything holding one), in light and dark.
   A tape heading that holds a button (the folding Settings cards) is straight; on a sharp screen the fine grid lines are a hairline.
4. Readability, measured on the drawn desk: every text colour at 4.5:1 against the darkest (light) or lightest (dark) point where text can
   sit (the page column, inside the cards, the header's version number), borders at 3:1, button text on the accent at 4.5:1, the toast's Undo
   at 4.5:1, and the marker writing on the tape at 4.5:1 against the tape's darkest point.
5. Good, bad, warning, caution and the yellow accent are told apart (CIEDE2000), and the light start circle stands off the page.
6. The TH4 touches stay in Paint Bench: Classic and Parchment Codex get no tape and no grid.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import io, os, re, sys
from playwright.sync_api import sync_playwright
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import quiet
from test_v124_th3 import ratio, de2000, colours, extreme, paper_extremes

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

SIZE_LIMIT = 3000   # bytes: the Paint Bench texture, tape and grid tokens plus the TH4 rules
TEXT = ["--text", "--muted", "--accent", "--heading-colour", "--wordmark-colour", "--good", "--bad", "--warn", "--caution", "--wish", "--grey-status", "--note", "--danger"]
UNITS = [{"id": i, "name": f"Unit {i}", "hobby": "40K", "stage": i % 6, "count": 5, "added": "2026-10-01", "log": [["2026-10-01", 1]]} for i in range(1, 7)]
NEW_PAGE = {"dark": (0x20, 0x25, 0x1f), "light": (0xe0, 0xe4, 0xd8)}

def rgb(text):
    return tuple(int(float(v)) for v in re.findall(r"[\d.]+", text)[:3])

def go(page, tab, sub=None):
    page.evaluate("(tab) => document.querySelector(`.tabs button[data-tab=\"${tab}\"]`).click()", tab); quiet(page)
    if sub:
        page.evaluate("(p) => document.querySelector(`#more-seg button[data-page=\"${p}\"]`).click()", sub); quiet(page)

TRANSFORMED = """() => [...document.querySelectorAll('main :is(button, a[href], input, select, textarea, summary, [role=button])')].filter(e => e.getClientRects().length)
    .filter(e => { for (let x = e; x && x !== document.body; x = x.parentElement) { const s = getComputedStyle(x); if (s.transform !== 'none' || s.rotate !== 'none') return true; } return false; })
    .map(e => (e.id || e.className || e.tagName).toString().slice(0, 40))"""

def main():
    outside = []
    html = t.read("index.html")
    style = html[html.index("<style>"):html.index("</style>")]

    print("\n--- 1. How the desk is drawn ---")
    blocks = [style[style.index(sel):] for sel in ('[data-t="bench"] {', '[data-t="bench"][data-m="dark"] {', '[data-t="bench"][data-m="light"] {')]
    blocks = [b[:b.index("\n    }")] for b in blocks]
    desk = [v for b in blocks for v in re.findall(r"--(?:texture|texture-size|grid-line): ([^\n]*);", b)]
    rules = [ln for ln in style.splitlines() if "TH4" in ln or ('[data-t="bench"]' in ln and any(k in ln for k in ("--tape", ".card h2", "--grid-line", ".arc [data-tab]")))]
    size = sum(len(v) for v in desk) + sum(len(r) for r in rules)
    print(f"     (desk tokens and TH4 rules: {size} bytes)")
    check(f"the desk is gradients only (no picture, no other site) and stays under {SIZE_LIMIT} bytes",
          desk and "url(" not in "".join(desk + rules) and "gradient" in "".join(desk) and size < SIZE_LIMIT, (size, [d[:60] for d in desk]))
    check("no filter or blend mode in the Paint Bench rules", not re.search(r"(?<![-\w])filter:|mix-blend-mode|backdrop-filter", "".join(blocks + rules)))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("request", lambda r: outside.append(r.url) if r.resource_type in ("font", "image") and not r.url.startswith((t.BASE, "data:", "blob:")) and "goatcounter.com" not in r.url else None)

        print("\n--- 2. The theme loads from the saved setting (early.js alone, on a sharp screen) ---")
        # app.js is not loaded here: early.js marks the page from the saved setting, so the styles alone can be checked quickly.
        ctx2 = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, service_workers="block")
        p2 = ctx2.new_page()
        p2.route("**/app.js*", lambda r: r.fulfill(status=200, content_type="text/javascript", body="window.__noApp = true;"))
        p2.goto(t.BASE + "manifest.json")
        def early_page(theme):
            p2.evaluate("(th) => localStorage.setItem('shades-of-grey-settings', JSON.stringify({ theme: th, appearance: 'light' }))", theme)
            p2.goto(t.URL)
            return p2.evaluate("""() => { const r = getComputedStyle(document.documentElement); return { t: document.documentElement.dataset.t, m: document.documentElement.dataset.m,
                bar: document.querySelector('meta[name=theme-color]').content, bg: getComputedStyle(document.body).backgroundColor, grid: r.getPropertyValue('--grid-line').trim(),
                first: getComputedStyle(document.body).backgroundImage.split('),')[0], tape: r.getPropertyValue('--tape').trim(), h2: getComputedStyle(document.querySelector('.card h2')).transform }; }""")
        early = early_page("bench")
        check("before app.js runs, a saved Paint Bench light marks the page, and the top bar and page take the new light desk colour",
              early["t"] == "bench" and early["m"] == "light" and early["bar"] == "#e0e4d8" and rgb(early["bg"]) == NEW_PAGE["light"], early)
        check("on a sharp screen the fine grid lines are half a pixel", early["grid"] == ".5px" and "0.5px" in early["first"], early)
        print("\n--- 6. Only Paint Bench ---")
        for th in ("classic", "parchment"):
            other = early_page(th)
            check(f"{th}: no tape, no grid and no tilted heading", other["t"] == th and (other["tape"], other["grid"], other["h2"]) == ("", "", "none"), other)
        ctx2.close()

        for mode, w, h in (("light", 390, 844), ("dark", 360, 640)):
            page.set_viewport_size({"width": w, "height": h})
            t.load(page, units=UNITS, settings={"theme": "bench", "appearance": mode, "examplesChecked": True}, launch=True)
            page.wait_for_timeout(150)
            got = page.evaluate("() => ({ t: document.documentElement.dataset.t, m: document.documentElement.dataset.m, bar: document.querySelector('meta[name=theme-color]').content, bg: getComputedStyle(document.body).backgroundColor, tex: getComputedStyle(document.body).backgroundImage })")
            check(f"{mode}: a saved Paint Bench setting loads it with the new desk colour, the grid and the cork edge",
                  got["t"] == "bench" and got["m"] == mode and rgb(got["bg"]) == NEW_PAGE[mode] and got["tex"].count("linear-gradient") == 5, got)

            if mode == "light":
                print("\n--- 5a. The start circle on the pale desk ---")
                seg = page.evaluate("() => getComputedStyle(document.querySelector('.arc [data-tab]')).backgroundColor")
                v = page.evaluate("(c) => { const d = document.createElement('i'); d.style.color = c; document.body.append(d); const r = getComputedStyle(d).color; d.remove(); return r; }", seg)
                seg_rgb = [round(float(x) * (255 if "srgb" in v else 1)) for x in re.findall(r"[\d.]+", v.split("srgb")[-1])[:3]]
                gap = de2000(seg_rgb, NEW_PAGE["light"])
                check("light: the start circle's segments stand off the page more clearly than before (CIEDE2000 6 or more; 5.4 before)", gap >= 6, (seg, round(gap, 1)))
            t.leave_launch(page)

            print(f"\n--- 3. No tilted tap targets ({mode}) ---")
            btn = page.evaluate("() => { const b = [...document.querySelectorAll('.primary-button')].find(e => e.getClientRects().length); return b && [getComputedStyle(b).transform, getComputedStyle(b).rotate]; }")
            check(f"{mode}: the main button has no resting transform", btn == ["none", "none"], btn)
            bad = page.evaluate(TRANSFORMED)
            go(page, "guides", "settings")
            bad += page.evaluate(TRANSFORMED)
            check(f"{mode}: no button, link or field on the Dashboard or in Settings (the page, not the round menu) is tilted, or sits in anything tilted", not bad, bad[:5])
            tape = page.evaluate("""() => { const hs = [...document.querySelectorAll('.card h2')].filter(h => h.getClientRects().length);
                const plain = hs.find(h => !h.querySelector('button')), fold = hs.find(h => h.querySelector('button'));
                return { plain: plain && getComputedStyle(plain).transform, fold: fold && getComputedStyle(fold).transform, bg: plain && getComputedStyle(plain).backgroundImage }; }""")
            check(f"{mode}: a tape heading holding a button is straight; plain tape keeps a slight tilt and its crepe texture",
                  tape["fold"] == "none" and tape["plain"] not in (None, "none") and "repeating-linear-gradient" in (tape["bg"] or ""), tape)

            print(f"\n--- 4. Readability on the drawn desk ({mode}) ---")
            go(page, "units")
            page.wait_for_timeout(150)
            darkest = mode == "light"
            col, card, n, tag = paper_extremes(page, darkest)
            names = TEXT + ["--border", "--on-accent", "--accent-fill", "--toast-action"]
            v = dict(zip(names, colours(page, names)))
            print(f"     ({mode}: worst page point {col}, worst card point {card}, header {tag})")
            low = [(k, round(ratio(v[k], col), 2)) for k in TEXT if ratio(v[k], col) < 4.5]
            check(f"{mode} {w}px: every text colour reads at 4.5:1 on the {'darkest' if darkest else 'lightest'} point of the desk", not low, low)
            low = [(k, round(ratio(v[k], card), 2)) for k in TEXT if card and ratio(v[k], card) < 4.5]
            check(f"{mode} {w}px: every text colour reads at 4.5:1 inside the cards ({n} cards)", n >= 3 and not low, (n, low))
            check(f"{mode} {w}px: the small version number in the header reads at 4.5:1", ratio(v["--muted"], tag) >= 4.5, round(ratio(v["--muted"], tag), 2))
            check(f"{mode} {w}px: borders reach 3:1 on the worst point of the desk and inside the cards",
                  min(ratio(v["--border"], col), ratio(v["--border"], card)) >= 3, (round(ratio(v["--border"], col), 2), round(ratio(v["--border"], card), 2)))
            check(f"{mode}: button text reads at 4.5:1 on the accent", ratio(v["--on-accent"], v["--accent-fill"]) >= 4.5, round(ratio(v["--on-accent"], v["--accent-fill"]), 2))
            check(f"{mode}: the toast's Undo reads at 4.5:1 on the toast", ratio(v["--toast-action"], v["--text"]) >= 4.5, round(ratio(v["--toast-action"], v["--text"]), 2))
            go(page, "guides", "settings")
            box = page.evaluate("() => { const h = [...document.querySelectorAll('.card h2')].find(h => h.getClientRects().length && !h.querySelector('button')); h.scrollIntoView({ block: 'center' }); const r = h.getBoundingClientRect(); return [r.left + 6, r.top + 3, r.right - 6, r.bottom - 3]; }")
            hide = page.add_style_tag(content=".card h2 * { visibility: hidden !important; } .card h2 { color: transparent !important; }")
            img = Image.open(io.BytesIO(page.screenshot()))
            hide.evaluate("e => e.remove()")
            worst_tape = extreme(img, box, True)
            check(f"{mode}: the marker writing reads at 4.5:1 on the darkest point of the tape", ratio((0x2b, 0x26, 0x16), worst_tape) >= 4.5, (worst_tape, round(ratio((0x2b, 0x26, 0x16), worst_tape), 2)))

            print(f"\n--- 5. Status colours and the accent told apart ({mode}) ---")
            s = dict(zip(["accent", "good", "bad", "warn", "caution"], colours(page, ["--accent", "--good", "--bad", "--warn", "--caution"])))
            pairs = {f"{a}/{b}": de2000(s[a], s[b]) for i, a in enumerate(s) for b in list(s)[i + 1:]}
            close = {k: round(x, 1) for k, x in pairs.items() if x < 9}
            check(f"{mode}: good, bad, warning, caution and the accent are all 9 or more apart (CIEDE2000; the accent and warning were 5 apart before)", not close, close)

        check("no font or picture loads from another site", not outside, outside)
        browser.close()

    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
