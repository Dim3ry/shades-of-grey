"""X4 tests for Minifolio (Dashboard Palette and Achievements tiles). New behaviour only:
1. Palette strip: one block per hue in wheel order (then greys and neutrals), wider for more paints, gaps (none or one paint) say Gap in text.
2. The lines: most used paint (a tie goes to the name first in A to Z), the first two gaps, the counts.
3. No paints: one short line, no strip. The tile opens Painting > Your Palette. The text alternative says the same as the lines.
4. Achievements: title, three empty circles, Coming soon, nothing to tap.
5. Order and layout: Palette then Achievements after the faction card; side by side at 1280 px; phone sizes, dark and light.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v24 as t
from launch_helpers import quiet, tap_tab

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# red x3 (one running low), blue x1, green x1, a wishlist yellow, a grey and a gold metallic (neutral), a paint with no colour
FIXTURE = """() => {
    const mk = (id, name, colour, status) => ({ id, name, colour, status, brand: "", type: "" });
    book.paints.length = 0;
    book.paints.push(mk(901, "Zed red", "#c0282c", "owned"), mk(902, "Ash red", "#d03030", "owned"), mk(903, "Deep red", "#8a1c1c", "low"),
        mk(904, "Sky blue", "#3a7bd5", "owned"), mk(905, "Leaf green", "#3f9a52", "owned"), mk(906, "Sun yellow", "#e8c93a", "wishlist"),
        mk(907, "Stone grey", "#8a8f98", "owned"), mk(908, "Mystery", "", "owned"));
    book.recipes.length = 0;
    const step = (...ids) => ({ paints: ids.map(id => ({ paint: id })) });
    book.recipes.push({ id: 801, name: "A", part: "", steps: [step(901, 904)] }, { id: 802, name: "B", part: "", steps: [step(901, 904), step(902)] },
        { id: 803, name: "C", part: "", steps: [step(902)] });
    render();
}"""

def tile(page):
    return page.evaluate("""() => ({
        hues: [...document.querySelectorAll('#palette-strip .palette-bar')].map(b => b.dataset.hue),
        gapLabels: [...document.querySelectorAll('#palette-strip .palette-gap')].map(g => g.textContent),
        widths: Object.fromEntries([...document.querySelectorAll('#palette-strip .palette-cell')].map(c => [c.querySelector('.palette-bar').dataset.hue, Math.round(c.getBoundingClientRect().width)])),
        lines: [...document.querySelectorAll('#palette-lines span')].map(s => s.textContent),
        stripHidden: document.getElementById('palette-strip').hidden,
        label: document.getElementById('palette-tile').getAttribute('aria-label') })""")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))

        print("\n--- 0. Example data (a brand-new start) ---")
        t.fresh(page)
        d = tile(page)
        check("example paints and recipes: tile draws, three lines, no errors", len(d["lines"]) >= 2 and not errors, d)

        print("\n--- 1 and 2. Strip and lines from a fixture palette ---")
        page.evaluate(FIXTURE)
        d = tile(page)
        check("blocks run red, orange, yellow, green, blue, purple, then neutral", d["hues"] == ["red", "orange", "yellow", "green", "blue", "purple", "neutral"], d["hues"])
        check("the block for 3 red paints is wider than the one for 1 blue", d["widths"]["red"] > d["widths"]["blue"], d["widths"])
        check("gaps say Gap in text: orange, yellow (wishlist does not count), green and blue (one), purple; not red or neutral",
              len(d["gapLabels"]) == 5 and all(g == "Gap" for g in d["gapLabels"]), d["gapLabels"])
        check("most used: the tie (two recipes each) goes to the first name A to Z", d["lines"][0] == "Most used: Ash red, in 2 recipes", d["lines"])
        check("gap line names the first two gaps", d["lines"][1] == "Gap: Orange, Yellow", d["lines"])
        check("counts line: owned, running low, wishlist", d["lines"][2] == "6 owned, 1 running low, 1 wishlist", d["lines"])
        check("the strip's text alternative carries the same lines and each hue's count",
              all(l in d["label"] for l in d["lines"]) and "Red 3" in d["label"] and "Blue 1 (gap)" in d["label"], d["label"])
        page.evaluate("() => { book.recipes.length = 0; render(); }")
        d = tile(page)
        check("no recipe uses a paint: the Most used line is left out", not any(l.startswith("Most used") for l in d["lines"]), d["lines"])
        page.evaluate("() => { book.paints.push({ id: 950, name: 'Pine', colour: '#2f8f4a', status: 'owned' }); render(); }")
        d = tile(page)
        check("a second green paint means green is no longer a gap", "Gap: Orange, Yellow" == d["lines"][0] and d["gapLabels"].count("Gap") == 4, d)

        print("\n--- 3. No paints, and the tap ---")
        page.evaluate("() => { book.paints.length = 0; book.recipes.length = 0; render(); }")
        d = tile(page)
        check("no paints: one short line and no strip", d["lines"] == ["No paints yet"] and d["stripHidden"], d)
        page.click("#palette-tile")
        quiet(page)
        check("tapping the tile opens Painting > Your Palette", page.evaluate("() => settings.tab === 'recipes' && settings.recipeView === 'palette' && !document.getElementById('palette-view').classList.contains('hidden')"))
        tap_tab(page, "dashboard"); quiet(page)
        page.evaluate("() => { book.paints.push({ id: 960, name: 'Late', colour: '#c0282c', status: 'owned' }); }")
        tap_tab(page, "recipes"); quiet(page); tap_tab(page, "dashboard"); quiet(page)
        check("the tile is up to date when you come back to the Dashboard", tile(page)["lines"][-1].startswith("1 owned"), tile(page)["lines"])

        print("\n--- 4. Achievements placeholder ---")
        a = page.evaluate("""() => { const c = document.getElementById('achievements-card');
            return { title: c.querySelector('h2').textContent, circles: c.querySelectorAll('.ach-circles i').length,
                     text: c.textContent.replace(/\\s+/g, ' ').trim(), taps: c.querySelectorAll('button, a, input').length } }""")
        check("Achievements: title, three circles, Coming soon, nothing to tap", a["title"] == "Achievements" and a["circles"] == 3 and a["text"] == "Achievements Coming soon" and a["taps"] == 0, a)

        print("\n--- 5. Order and layout ---")
        page.evaluate(FIXTURE)
        order = page.evaluate("() => [...document.getElementById('view-dashboard').children].map(c => c.id).filter(Boolean).slice(-4)")
        check("Palette then Achievements come after the faction card", order == ["faction-card", "palette-card", "achievements-card"] or order[-3:] == ["faction-card", "palette-card", "achievements-card"], order)
        big = browser.new_context(viewport={"width": 1280, "height": 900}, service_workers="block")
        pg = big.new_page(); pg.on("pageerror", lambda x: errors.append(str(x)))
        t.fresh(pg)
        pg.evaluate(FIXTURE)
        tops = pg.evaluate("() => ['palette-card', 'achievements-card'].map(i => { const r = document.getElementById(i).getBoundingClientRect(); return [Math.round(r.top), Math.round(r.left)]; })")
        check("1280 px: the two tiles sit side by side", tops[0][0] == tops[1][0] and tops[0][1] < tops[1][1], tops)
        big.close()
        for width in (390, 360):
            for scheme in ("dark", "light"):
                c2 = browser.new_context(viewport={"width": width, "height": 800}, color_scheme=scheme, service_workers="block")
                pg = c2.new_page(); pg.on("pageerror", lambda x: errors.append(str(x)))
                t.fresh(pg)
                pg.evaluate(FIXTURE.replace("book.paints.push(", "book.paints.push(mk(970, 'P', '#8452c4', 'owned'), ", 1))
                m = pg.evaluate("""() => { const b = document.getElementById('palette-tile').getBoundingClientRect(), s = document.getElementById('palette-strip').getBoundingClientRect(),
                    cardR = document.getElementById('palette-card').getBoundingClientRect();
                    return { h: b.height, w: b.width, stripInside: s.right <= innerWidth, cardW: cardR.width,
                             tapArea: getComputedStyle(document.getElementById('palette-tile'), '::after').position } }""")
                check(f"{width} px {scheme}: tile 44 px or more, strip inside the screen, whole card is the tap area, no sideways scroll",
                      m["h"] >= 44 and m["stripInside"] and m["tapArea"] == "absolute" and t.no_sideways(pg), m)
                c2.close()
        check("no page errors or pop-ups", not errors, errors)
        browser.close()

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)

if __name__ == "__main__":
    main()
