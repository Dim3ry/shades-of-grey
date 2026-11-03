"""TH5 tests for Minifolio (the four looks reviewed together: Classic, Grim Forge, Parchment Codex and Paint Bench, light and dark).
New behaviour only, for the three fixes TH5 made:
1. The hint inside an empty text box (its placeholder) uses the look's own muted colour and reads at 4.5:1 on its box, in all eight
   look and mode pairs (the browser's own grey was under 4.5:1 in every one of them).
2. A pressed chip fills with the same colour as the buttons (--accent-fill). In Parchment Codex dark that is the deep red ink, with cream
   text at 4.5:1 or more (it was the lighter text crimson, 2.8:1). There the fill also reaches 3:1 against the cards and the page.
3. The round Mentor button's shine stops above its label, so "Ask Mentor" reads at 4.5:1 at the lightest point behind it, in the bar
   and on the start circle, in all eight pairs.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import io, os, sys
from playwright.sync_api import sync_playwright
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import quiet

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

LOOKS = [(th, m) for th in ("classic", "forge", "parchment", "bench") for m in ("dark", "light")]
UNITS = [{"id": 1, "name": "Squad", "hobby": "Test game", "stage": 2, "count": 5, "added": "2026-10-01", "log": [["2026-10-01", 2]]}]

def lum(c):
    v = [x / 255 for x in c[:3]]
    v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]

def ratio(a, b):
    x, y = lum(a), lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)

# Any CSS colour (rgb, color(srgb ...), color-mix results) to [r, g, b, a] through a 1x1 canvas, and a box's background with
# the see-through layers above the page laid over each other.
HELPERS = """window.__th5 = (() => {
    const cx = Object.assign(document.createElement('canvas'), { width: 1, height: 1 }).getContext('2d', { willReadFrequently: true });
    const rgba = (c) => { cx.clearRect(0, 0, 1, 1); cx.fillStyle = '#000'; cx.fillStyle = c; cx.fillRect(0, 0, 1, 1); const d = cx.getImageData(0, 0, 1, 1).data; return [d[0], d[1], d[2], d[3] / 255]; };
    const over = (a, b) => [0, 1, 2].map(i => a[i] * a[3] + b[i] * (1 - a[3])).concat([1]);
    const bg = (el) => { const layers = []; for (let e = el; e; e = e.parentElement) { const c = rgba(getComputedStyle(e).backgroundColor); if (c[3] > 0) layers.push(c); if (c[3] >= 0.999) break; }
        let out = rgba(getComputedStyle(document.documentElement).backgroundColor); if (out[3] < 1) out = [255, 255, 255, 1];
        for (let i = layers.length - 1; i >= 0; i--) out = over(layers[i], out); return out; };
    const tok = (n) => rgba(getComputedStyle(document.documentElement).getPropertyValue(n).trim());
    return { rgba, bg, tok };
})()"""

def set_look(page, th, m):
    # the same page, switched as Settings switches it
    page.evaluate("([th, m]) => { Object.assign(settings, { theme: th, appearance: m }); applyPalette(settings.palette); }", [th, m])
    quiet(page)

HIDE = """*, *::before, *::after { color: transparent !important; -webkit-text-fill-color: transparent !important; text-shadow: none !important; transition: none !important; }
    svg { visibility: hidden !important; }"""

def label_worst(page):
    """The lowest contrast between the Mentor button's label colour and any pixel of the button behind the label (label and drawing hidden)."""
    lab = page.evaluate("""() => { const b = document.getElementById('mentor-button'); const n = [...b.childNodes, ...[...b.children].flatMap(e => [...e.childNodes])].find(x => x.nodeType === 3 && x.textContent.trim());
        const r = document.createRange(); r.selectNodeContents(n); const q = r.getBoundingClientRect();
        return { box: [q.left + 1, q.top + 1, q.right - 1, Math.min(q.bottom - 1, innerHeight)], fg: getComputedStyle(n.parentElement).color.match(/[\\d.]+/g).slice(0, 3).map(Number) }; }""")
    tag = page.add_style_tag(content=HIDE)
    page.wait_for_timeout(50)
    img = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
    tag.evaluate("e => e.remove()")
    cols = img.crop(tuple(int(round(v)) for v in lab["box"])).getcolors(1 << 20)
    return min(ratio(lab["fg"], c[1]) for c in cols)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. The hint in an empty text box ---")
        t.load(page, units=UNITS, settings={"tab": "recipes", "recipeView": "palette", "examplesChecked": True, "recipeExamplesChecked": True})
        page.evaluate(HELPERS)
        low, wrong = [], []
        for th, m in LOOKS:
            set_look(page, th, m)
            got = page.evaluate("""() => { const el = document.getElementById('palette-search'); el.value = '';
                return { ph: __th5.rgba(getComputedStyle(el, '::placeholder').color), muted: __th5.tok('--muted'), bg: __th5.bg(el) }; }""")
            if got["ph"][:3] != got["muted"][:3]:
                wrong.append((th, m, got["ph"], got["muted"]))
            r = ratio(got["ph"], got["bg"])
            if r < 4.5:
                low.append((th, m, round(r, 2)))
        check("all eight look and mode pairs: the hint in Your Palette's search box is the look's muted colour", not wrong, wrong)
        check("all eight: that hint reads at 4.5:1 or more on its box", not low, low)
        page.click('.tabs button[data-tab="dashboard"]'); quiet(page)
        page.click("#mentor-button"); page.wait_for_timeout(600)
        low = []
        for th, m in LOOKS:
            set_look(page, th, m)
            got = page.evaluate("() => { const el = document.querySelector('.mentor-input'); return { ph: __th5.rgba(getComputedStyle(el, '::placeholder').color), bg: __th5.bg(el) }; }")
            r = ratio(got["ph"], got["bg"])
            if r < 4.5:
                low.append((th, m, round(r, 2)))
        check("all eight: the Ask Mentor box's hint reads at 4.5:1 or more", not low, low)
        page.keyboard.press("Escape"); page.wait_for_timeout(400)

        print("\n--- 2. Pressed chips use the fill colour ---")
        page.click('.tabs button[data-tab="dashboard"]'); quiet(page)
        page.evaluate("() => document.querySelector('.range-chips .chip[aria-pressed=\"true\"]').scrollIntoView({ block: 'center' })"); quiet(page)
        bad_fill, bad_text = [], []
        for th, m in LOOKS:
            set_look(page, th, m)
            got = page.evaluate("""() => { const c = document.querySelector('.range-chips .chip[aria-pressed="true"]'), s = getComputedStyle(c);
                const layer = s.backgroundImage.match(/rgba?\\([^)]*\\)/); return { layer: layer ? __th5.rgba(layer[0]) : null, size: s.backgroundSize,
                fill: __th5.tok('--accent-fill'), text: __th5.rgba(s.color) }; }""")
            if not got["layer"] or got["layer"][:3] != got["fill"][:3] or got["size"] != "100% 100%":
                bad_fill.append((th, m, got))
            elif ratio(got["text"], got["layer"]) < 4.5:
                bad_text.append((th, m, round(ratio(got["text"], got["layer"]), 2)))
        check("all eight: a pressed chip is filled with the buttons' fill colour", not bad_fill, bad_fill)
        check("all eight: the text on a pressed chip reads at 4.5:1 or more", not bad_text, bad_text)
        set_look(page, "parchment", "dark")
        pd = page.evaluate("() => ({ fill: __th5.tok('--accent-fill'), accent: __th5.tok('--accent'), card: __th5.tok('--card'), page: __th5.tok('--background'), cream: __th5.tok('--on-accent') })")
        check("Parchment Codex dark: the chip is the deep red ink, not the lighter crimson used for text", pd["fill"][:3] != pd["accent"][:3], pd)
        check("Parchment Codex dark: the fill reaches 3:1 against the cards and the page, and cream text on it 4.5:1",
              ratio(pd["fill"], pd["card"]) >= 3 and ratio(pd["fill"], pd["page"]) >= 3 and ratio(pd["cream"], pd["fill"]) >= 4.5,
              [round(ratio(pd["fill"], pd["card"]), 2), round(ratio(pd["fill"], pd["page"]), 2), round(ratio(pd["cream"], pd["fill"]), 2)])

        print("\n--- 3. The Mentor button's label ---")
        page.evaluate("() => window.scrollTo(0, 0)"); quiet(page)
        low = []
        for th, m in LOOKS:
            set_look(page, th, m)
            r = label_worst(page)
            if r < 4.5:
                low.append((th, m, round(r, 2)))
        check("in the bar, all eight: \"Ask Mentor\" reads at 4.5:1 at the lightest (or darkest) point of the button behind it", not low, low)
        t.load(page, units=UNITS, settings={"examplesChecked": True, "recipeExamplesChecked": True}, launch=True)
        low = []
        for th, m in LOOKS:
            set_look(page, th, m)
            r = label_worst(page)
            if r < 4.5:
                low.append((th, m, round(r, 2)))
        check("on the start circle, all eight: \"Ask Mentor\" reads at 4.5:1 at the worst point behind it", not low, low)
        shine = page.evaluate("getComputedStyle(document.getElementById('mentor-button')).backgroundImage")
        check("the button keeps its shine (a soft white spot at the top left)", "radial-gradient" in shine and "35% 30%" in shine, shine)
        check("no errors on the page", not errors, errors)
        browser.close()

    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
