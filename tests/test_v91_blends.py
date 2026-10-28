"""Mix 2 tests for Minifolio (paint blend suggestions in the Similar paints pop-up, "Your closest").

New behaviour only:
1. The mixing model (colour.js mixColours): blue + yellow gives a green, black + white is darker than a screen average, two darks stay dark.
2. blendSuggestions: only a blend at least 5 points closer than the best single paint and an Okay fit or better; at most 2; larger share first.
3. Which paints may be mixed: shades, Contrast, Technical, metallics, mediums, odd finishes, default-grey customs and unowned paints are never
   used; pure white and black are; the same colour counts once.
4. The pop-up: Try mixing only when your closest paint is a Poor fit; the label, the one note line, no fit words, swatches; nothing otherwise.
5. Add to recipe step: two paints and the ratio land in a new step (and in an existing one), the step editor can read the ratio, Undo.
6. Phones (390 and 360 px, dark and light): no sideways scroll, tap targets 44 px or more. Speed with 500 paints."""
import os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

no_sideways = t.no_sideways

def load(page, **kw):
    """t.load, tried once more if the browser drops the page load (net::ERR_ABORTED, seen now and then on a busy machine)."""
    try:
        t.load(page, **kw)
    except Exception as err:
        if "ERR_ABORTED" not in str(err):
            raise
        page.wait_for_timeout(300)
        t.load(page, **kw)
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def P(id, brand, name, colour, **more):
    return dict({"id": id, "brand": brand, "name": name, "colour": colour}, **more)

TARGET = P(1, "Test", "Target Green", "#4a8a4a", status="notowned")
BLUE = P(2, "Citadel", "Macragge Blue", "#0d407f", status="owned")
YELLOW = P(3, "Citadel", "Averland Sunset", "#fbb81c", status="owned")
BROWN = P(4, "Citadel", "Scrag Brown", "#5a3a22", status="owned")
WHITE = P(5, "Citadel", "Corax White", "#f2f2f2", status="owned")
RECIPE = {"id": 1, "name": "Test recipe", "part": "Armour", "notes": "",
          "steps": [{"technique": "Base", "coats": 1, "paints": [{"paint": 4, "mix": None}], "ratio": "", "note": "", "optional": False}]}
SET = [TARGET, BLUE, YELLOW, BROWN, WHITE]

def lab_L(page, hexes):
    return page.evaluate("(h) => h.map(x => MinifolioColour.hexToLab(x).L)", hexes)

def open_yours(page):
    page.evaluate("() => openSimilarPaints(book.paints[0], null)")
    page.wait_for_timeout(120)
    if page.locator("#similar-tab-yours").is_visible():
        page.click("#similar-tab-yours")
    page.wait_for_timeout(80)

def blend_boxes(page):
    return page.evaluate("""() => [...document.querySelectorAll('.mix-blend')].map(b => ({
        title: b.querySelector('.mix-title').textContent, note: b.querySelector('.similar-note').textContent,
        button: b.querySelector('.mix-add').textContent, text: b.textContent,
        swatches: [...b.querySelectorAll('.mix-swatch')].map(s => s.style.getPropertyValue('--swatch')) }))""")

def main():
    errors, dialogs = [], []
    app = t.read("app.js")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        # ---------- 1. The mixing model ----------
        print("\n--- 1. The mixing model ---")
        load(page, paints=SET, recipes=[RECIPE])
        green = page.evaluate("() => MinifolioColour.mixColours(['#0d407f', '#fbb81c'], [1, 1])")
        hue = page.evaluate("(h) => MinifolioColour.hexToHsl(h).h", green)
        check("blue plus yellow gives a green", 80 <= hue <= 160, [green, hue])
        mixed, screen = lab_L(page, [page.evaluate("() => MinifolioColour.mixColours(['#171314', '#f2f2f2'], [1, 1])"), "#808080"])
        check("black plus white is darker than a screen average", mixed < screen - 10, [mixed, screen])
        dark = page.evaluate("() => MinifolioColour.mixColours(['#5a3a22', '#284631'], [1, 1])")
        check("two darks stay dark", lab_L(page, [dark])[0] < 30, dark)
        check("more of one paint pulls the mix towards it",
              page.evaluate("() => MinifolioColour.colourDistance(MinifolioColour.mixColours(['#0d407f', '#f2f2f2'], [3, 1]), '#0d407f') < MinifolioColour.colourDistance(MinifolioColour.mixColours(['#0d407f', '#f2f2f2'], [1, 3]), '#0d407f')"))
        check("a bad input gives nothing, not an error",
              page.evaluate("() => MinifolioColour.mixColours(['nope'], [1]) === null && MinifolioColour.mixColours(['#ffffff', '#000000'], [1]) === null"))

        # ---------- 2. Which blends are offered ----------
        print("\n--- 2. Which blends are offered ---")
        got = page.evaluate("""() => { const pool = book.paints.slice(1);
            const w = MinifolioColour.blendSuggestions('#4a8a4a', pool, { single: 38 });
            const none = MinifolioColour.blendSuggestions('#4a8a4a', pool, { single: 12 });
            return { n: w.length, first: w[0] && [w[0].a.paint.name, w[0].b.paint.name, w[0].ratio, w[0].distance], none: none.length,
                     bigger: w.every(x => x.a.parts >= x.b.parts), ratios: w.every(x => ['1:1', '2:1', '3:1', '4:1'].includes(x.ratio)) }; }""")
        check("a clearly better blend is found: blue and yellow", got["n"] >= 1 and set(got["first"][:2]) == {"Macragge Blue", "Averland Sunset"}, got)
        check("at most two, larger share first, painter-friendly ratios", got["n"] <= 2 and got["bigger"] and got["ratios"], got)
        check("it is an Okay fit or better (15 or less)", got["first"][3] <= 15, got)
        check("a blend that is not at least 5 points closer than the single paint is not offered", got["none"] == 0, got)

        # ---------- 3. Which paints may be mixed ----------
        print("\n--- 3. Paints that are never mixed ---")
        skipped = [("Citadel", "Agrax Earthshade"), ("Citadel", "Baal Red"), ("Citadel", "Agrellan Earth"), ("Citadel", "Leadbelcher"),
                   ("Citadel", "Balthasar Gold"), ("Citadel", "Contrast Medium"), ("Vallejo", "Fluorescent Orange"), ("Vallejo", "Clear Base"),
                   ("Test", "Nuln Oil Gloss")]
        kept = [("Citadel", "Corax White"), ("Citadel", "Corvus Black")]
        owned = [P(10 + i, b, n, "#" + "%02x" % (40 + i * 7) + "3a22", status="owned") for i, (b, n) in enumerate(skipped + kept)]
        owned.append(P(40, "Mine", "Never Coloured", "#808080", status="owned"))            # a custom paint still on the default grey
        owned.append(P(41, "Citadel", "Unowned Red", "#aa2222", status="notowned"))         # not yours
        owned.append(P(42, "Alpha", "Twin One", "#336699", status="owned"))
        owned.append(P(43, "Beta", "Twin Two", "#336699", status="owned"))                  # the same colour in another brand
        load(page, paints=[TARGET] + owned)
        names = page.evaluate("() => blendPool(book.paints[0]).map(p => p.name)")
        check("shades, Contrast, Technical, metallics, mediums, odd finishes, a default-grey custom and unowned paints are never used",
              not any(n for n in names if n in [n for _, n in skipped] + ["Never Coloured", "Unowned Red"]), names)
        check("pure white and pure black paints are kept", "Corax White" in names and "Corvus Black" in names, names)
        check("the same colour in two brands counts once", sum(n.startswith("Twin") for n in names) == 1, names)
        check("the Citadel position list and the name rule are in the code, not in the paint data",
              "BLEND_SKIP_CITADEL" in app and "KNOWN_PAINT_TABLE.Citadel.slice(" in app)

        # ---------- 4. The pop-up ----------
        print("\n--- 4. Try mixing in Your closest ---")
        load(page, paints=SET, recipes=[RECIPE])
        open_yours(page)
        boxes = blend_boxes(page)
        check("one blend row with the label and the parts",
              len(boxes) == 1 and boxes[0]["title"] == "Try mixing 1 part Macragge Blue, 1 part Averland Sunset", boxes)
        b = boxes[0] if boxes else {"note": "", "text": "", "swatches": [], "button": ""}
        check("the one note line and the button", b["note"] == "Approximate. Test on a palette first." and b["button"] == "Add to recipe step", b)
        check("never a fit word on a blend, and no em dash", not re.search(r"Good|Okay|Poor|fit|—", b["text"]), b["text"])
        check("four swatches: the two paints, the mix and the wanted colour", len(b["swatches"]) == 4 and b["swatches"][3] == "#4a8a4a", b)
        check("the predicted colour is the model's own",
              page.evaluate("(c) => c === MinifolioColour.mixColours(['#0d407f', '#fbb81c'], [1, 1])", b["swatches"][2] if b["swatches"] else ""), b)
        page.keyboard.press("Escape")

        load(page, paints=SET + [P(6, "Citadel", "Close Green", "#4c8c4a", status="owned")], recipes=[RECIPE])
        open_yours(page)
        check("nothing when your closest paint is already a fit", not blend_boxes(page))
        page.keyboard.press("Escape")
        load(page, paints=[TARGET, BLUE, P(7, "Citadel", "Navy Two", "#10447f", status="owned")], recipes=[RECIPE])
        open_yours(page)
        check("nothing when no blend is clearly better", not blend_boxes(page))
        page.keyboard.press("Escape")
        load(page, paints=[TARGET, BLUE], recipes=[RECIPE])
        open_yours(page)
        check("nothing when you own fewer than two mixable paints", not blend_boxes(page))
        page.keyboard.press("Escape")

        # ---------- 5. Add to recipe step ----------
        print("\n--- 5. Add to recipe step ---")
        load(page, paints=SET, recipes=[RECIPE])
        open_yours(page)
        page.click(".mix-add")
        picker = page.locator(".mix-blend .paint-recipe-picker")
        check("the same recipe and step picker opens", picker.count() == 1 and page.locator(".mix-add").get_attribute("aria-expanded") == "true")
        page.select_option(".mix-blend select[aria-label=Recipe]", "1")
        page.select_option(".mix-blend select[aria-label=Step]", "-1")
        page.click(".mix-blend .primary-button")
        page.wait_for_timeout(150)
        step = page.evaluate("() => recipeById(1).steps[1]")
        check("a new step holds the two paints and the ratio",
              step and [x["paint"] for x in step["paints"]] == [2, 3] and step["ratio"] == "1:1" and [x["mix"] for x in step["paints"]] == [50, 50], step)
        check("the step editor reads that ratio as a fit for two paints", page.evaluate("() => ratioPercents('1:1', 2)") == [50, 50])
        check("the picker closes and focus returns to Add to recipe step",
              page.locator(".mix-blend .paint-recipe-picker").count() == 0 and page.evaluate("() => document.activeElement.classList.contains('mix-add')"))
        page.click(".toast button")
        page.wait_for_timeout(150)
        check("Undo puts the recipe back", page.evaluate("() => recipeById(1).steps.length") == 1)
        page.click(".mix-add")
        page.select_option(".mix-blend select[aria-label=Recipe]", "1")
        page.select_option(".mix-blend select[aria-label=Step]", "0")
        page.click(".mix-blend .primary-button")
        page.wait_for_timeout(150)
        step = page.evaluate("() => recipeById(1).steps[0]")
        check("an existing step is filled with the two paints and the ratio",
              [x["paint"] for x in step["paints"]] == [2, 3] and step["ratio"] == "1:1", step)
        page.click(".mix-add")
        reach = []
        for _ in range(8):
            reach.append(page.evaluate("() => document.activeElement.tagName"))
            page.keyboard.press("Tab")
        check("Tab reaches the dropdowns inside the pop-up", "SELECT" in reach, reach)
        page.keyboard.press("Escape")

        # ---------- 6. Phones ----------
        print("\n--- 6. Phones, dark and light ---")
        for width, scheme in ((390, "dark"), (360, "light")):
            page.set_viewport_size({"width": width, "height": 844})
            load(page, paints=SET, recipes=[RECIPE], settings={"appearance": scheme})
            open_yours(page)
            page.click(".mix-add")
            small = page.evaluate("""() => [...document.querySelectorAll('.mix-blend button, .mix-blend select')].filter(e => e.offsetParent)
                .map(e => { const r = e.getBoundingClientRect(); return [e.className || e.tagName, Math.round(r.width), Math.round(r.height)]; })
                .filter(x => x[1] < 44 || x[2] < 44)""")
            check(f"{width} px {scheme}: no sideways scroll, tap targets 44 px or more", no_sideways(page) and not small, small)
            c = page.evaluate("() => [getComputedStyle(document.querySelector('.mix-title')).color, getComputedStyle(document.querySelector('.mix-blend')).backgroundColor]")
            lc, bc = t.luminance(t.rgb(c[0])), t.luminance(t.rgb(c[1]))
            check(f"{width} px {scheme}: the label is readable (contrast 4.5 or more)", (max(lc, bc) + 0.05) / (min(lc, bc) + 0.05) >= 4.5, c)
            if os.path.isdir(t.SHOTS):
                page.screenshot(path=os.path.join(t.SHOTS, f"v91-blend-{width}-{scheme}.png"))
            page.keyboard.press("Escape")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 7. Speed with a big collection ----------
        print("\n--- 7. Speed, 500 owned paints ---")
        big = [TARGET] + [P(100 + i, f"Brand{i % 9}", f"Paint {i}", "#%02x%02x%02x" % (150 + (i * 53) % 100, (i * 97) % 90, (i * 29) % 90), status="owned")   # all reds: no single fit for a green
                          for i in range(500)]
        load(page, paints=big)
        timing = page.evaluate("""() => { const t0 = performance.now(); openSimilarPaints(book.paints[0], null); const open = performance.now() - t0;
            const c = similarCards(book.paints[0], 0); const t1 = performance.now();
            const b = c.yours && typeof c.yours.single === 'number' ? similarBlends(book.paints[0], 0.0001, c.yours.single) : null;
            const first = performance.now() - t1; const t2 = performance.now();
            if (c.yours && typeof c.yours.single === 'number') similarBlends(book.paints[0], 0.0001, c.yours.single);
            return { open, first, again: performance.now() - t2, single: c.yours ? c.yours.single : null, owned: book.paints.length - 1 }; }""")
        check("the search really ran (your closest was a Poor fit)", timing["single"] is not None, timing)
        print("  500 paints: pop-up opens in %.0f ms, first blend search %.0f ms, the same search again %.1f ms" % (timing["open"], timing["first"], timing["again"]))
        check("the pop-up opens quickly (under 300 ms) and the blend search is not run on the way in", timing["open"] < 300, timing)
        check("the blend search is cheap (under 1.5 s) and remembered (the repeat is instant)", timing["first"] < 1500 and timing["again"] < 20, timing)
        page.keyboard.press("Escape")

        # ---------- 8. Errors ----------
        print("\n--- 8. Errors ---")
        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
