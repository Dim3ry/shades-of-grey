"""SM1 tests for Minifolio (smoother start circle travel and Models taps). New behaviour only:
1. The travelling copies of the segments use the segments' own font (they were drawn in the browser's serif), in two themes.
2. During the travel the labels and icons only move and scale (transform): their font size, line height and weight are set
   at most once more (half way), not on every frame; colours are plain rgba(), not color-mix().
3. Opening or closing Details on a phone redraws only that card; every other card stays the same element.
4. With 150 cards of mixed shapes, the Models page height stays the same while you scroll, a stage tap keeps the tapped card where it was,
   and goToUnit puts the card fully on screen (Smooth2, content-visibility on unit cards, was dropped because it broke these).
Reduced motion and taps during the travel are checked in test_v109_travel. Nothing here depends on the machine's speed.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_v31 as t
from launch_helpers import wait_settled, _FINISH_BAR

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def mixed_units(n):
    # long names, nicknames, factions, repaint, linked recipes and per-model stages: cards of many heights
    out = []
    for i in range(1, n + 1):
        u = {"id": i, "name": (f"A very long unit name that wraps onto a second line {i}" if i % 5 == 0 else f"Squad {i}"),
             "hobby": "40K", "stage": i % 6, "count": 3, "added": "2026-10-01", "log": [["2026-10-01", i % 6]]}
        if i % 7 == 0: u["nickname"] = f"The nickname of unit {i}"
        if i % 3 == 0: u["faction"] = "Iron Wolves"
        if i % 11 == 0: u["repaint"] = True
        if i % 4 == 0: u["recipes"] = [101]
        if i % 6 == 0: u.update(each=True, stages=[1, 3, 5])
        out.append(u)
    return out

def units(n):
    # all cards the same shape, so every card is the same height
    return [{"id": i, "name": f"Squad {i}", "hobby": "40K", "stage": i % 8, "count": 5, "added": "2026-10-01",
             "log": [["2026-10-01", i % 8]]} for i in range(1, n + 1)]

# Tap a segment, watch every style write on the copies until the travel ends, and report which properties changed how often.
TRAVEL = """(tab) => new Promise(done => {
    const seg = document.querySelector('.tabs .arc > [data-tab=' + tab + ']');
    const real = getComputedStyle(seg);
    const want = [real.fontFamily, real.fontStyle, real.letterSpacing, real.textTransform];
    const parse = (s) => { const m = {}; (s || '').split(';').forEach(d => { const i = d.indexOf(':'); if (i > 0) m[d.slice(0, i).trim()] = d.slice(i + 1).trim(); }); return m; };
    const kind = (el) => el.matches('.w') ? 'w' : el.matches('.c') ? 'c' : el.matches('.icon') ? 'icon' : el.matches('.t') ? 't' : 'other';
    const changes = { w: {}, c: {}, icon: {}, t: {}, other: {} }, colours = [], seen = new Map(), values = { c: {}, icon: {}, t: {} };
    let font = null, wide = false;
    const obs = new MutationObserver(list => {
        // records come in a batch: each one's new value is the next record's old value for the same element (or the style now)
        const recs = list.filter(m => m.target.closest && m.target.closest('.mo-tr'));
        recs.forEach((m, i) => {
            const next = recs.slice(i + 1).find(n => n.target === m.target);
            const a = parse(m.oldValue), b = parse(next ? next.oldValue : m.target.getAttribute('style')), k = kind(m.target);
            for (const p of new Set([...Object.keys(a), ...Object.keys(b)])) {
                if (a[p] === b[p]) continue;
                if (p in a) changes[k][p] = (changes[k][p] || 0) + 1;   // a value set for the first time is not a change
                if (/color/.test(p) && b[p]) colours.push(b[p]);
                if (k in values && b[p]) { if (!seen.has(m.target)) seen.set(m.target, {}); const v = seen.get(m.target); (v[p] = v[p] || new Set()).add(b[p]);
                    values[k][p] = Math.max(values[k][p] || 0, v[p].size); }
            }
        });
        const c = document.querySelector('.mo-tr .w .c');
        if (c && !font) { const cs = getComputedStyle(c.querySelector('.t') || c); font = [cs.fontFamily, cs.fontStyle, cs.letterSpacing, cs.textTransform]; }
        if (document.documentElement.scrollWidth > document.documentElement.clientWidth) wide = true;
    });
    obs.observe(document.documentElement, { subtree: true, attributes: true, attributeFilter: ['style'], attributeOldValue: true });
    seg.click();
    const started = !!document.querySelector('.mo-tr');
    const end = () => { if (document.querySelector('.mo-tr')) return requestAnimationFrame(end);
        obs.disconnect(); done({ started, want, font, changes, values, colours: colours.slice(0, 400), wide }); };
    requestAnimationFrame(end);
})"""

# mark every card, tap one card's Details, and say which cards are new elements
TOGGLE = """(id) => { const list = document.getElementById('unit-list');
    [...list.children].forEach(li => li.__sm1 = true);
    document.querySelector('li.unit[data-id="' + id + '"] .details-toggle').click();
    const cards = [...list.children].filter(li => li.matches('li.unit'));
    return { fresh: cards.filter(li => !li.__sm1).map(li => li.dataset.id), total: cards.length,
             panel: !!document.querySelector('li.unit[data-id="' + id + '"] > .panel') }; }"""

def travel_checks(page, theme):
    r = page.evaluate(TRAVEL, "units")
    ch = r["changes"]
    check(f"{theme}: the travel ran", r["started"], r)
    check(f"{theme}: the travelling labels use the segments' font, style, letter spacing and case", r["font"] == r["want"], [r["font"], r["want"]])
    sizes = ("font-size", "line-height", "font-weight", "gap")
    # each copy is drawn at two sizes only: the start's, then (from half way) the end's; before SM1 they took a new size every frame
    two = {k: {p: r["values"][k].get(p, 0) for p in sizes} for k in ("c", "icon", "t")}
    check(f"{theme}: label and icon are laid out at two sizes only (start, then end from half way), not a new one every frame",
          all(n <= 2 for k in two.values() for n in k.values()), two)
    # v129 (MO6): the lit piece's label switched from plain to bold in one frame half way; it now crossfades from its start look to its end look,
    # so the labels may also change opacity (still never a size, so no new layout)
    check(f"{theme}: the label only moves and scales (transform is the only thing that changes on it, plus MO6's crossfade opacity)",
          set(ch["t"]) <= {"transform", "opacity"} and ch["t"].get("transform", 0) >= 8, ch["t"])
    check(f"{theme}: the icon changes only its transform and colour (plus one size switch)",
          set(ch["icon"]) <= {"transform", "color", "font-size"} and ch["icon"].get("transform", 0) >= 8, ch["icon"])
    check(f"{theme}: colours are plain rgba(), never color-mix()", r["colours"] and not any("color-mix" in c for c in r["colours"]), r["colours"][:3])
    check(f"{theme}: no sideways scroll during the travel", not r["wide"])

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", color_scheme="dark")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        print("--- 1 and 2. The travel: the real font, transform only ---")
        t.load(page, units=units(3), launch=True)
        travel_checks(page, "classic, 390 dark")
        page.set_viewport_size({"width": 360, "height": 740})
        page.emulate_media(color_scheme="light")
        t.load(page, units=units(3), settings={"theme": "parchment"}, launch=True)
        check("parchment theme is on", page.evaluate("document.documentElement.dataset.t") == "parchment",
              page.evaluate("document.documentElement.dataset.t"))
        travel_checks(page, "parchment, 360 light")

        print("\n--- 4. Mixed cards: steady page height, stage taps and goToUnit ---")
        page.set_viewport_size({"width": 390, "height": 844})
        page.emulate_media(color_scheme="dark")
        t.load(page, units=mixed_units(150), recipes=t.RECIPES)
        page.evaluate("document.querySelector('.tabs button[data-tab=units]').click()")
        page.evaluate(_FINISH_BAR)
        wait_settled(page)
        r = page.evaluate("""async () => { const hs = [], heights = new Set();
            document.querySelectorAll('li.unit').forEach(li => heights.add(Math.round(li.getBoundingClientRect().height)));
            for (let y = 0; y <= document.documentElement.scrollHeight; y += 700) {
                window.scrollTo(0, y); await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
                hs.push(document.documentElement.scrollHeight); }
            return { hs: [...new Set(hs)], kinds: heights.size, n: document.querySelectorAll('li.unit').length }; }""")
        check("the cards really are of mixed heights", r["kinds"] >= 3 and r["n"] == 150, r)
        check("the page height stays the same while scrolling to the end", len(r["hs"]) == 1, r["hs"])
        before = page.evaluate("""() => { const li = document.querySelector('li.unit[data-id="122"]');
            window.scrollTo(0, 0); window.scrollTo(0, li.getBoundingClientRect().top + scrollY - 200);
            return li.getBoundingClientRect().top; }""")
        wait_settled(page)
        page.locator('li.unit[data-id="122"] .up-button').click()
        wait_settled(page)
        after = page.evaluate("""() => document.querySelector('li.unit[data-id="122"]').getBoundingClientRect().top""")
        check("a stage tap keeps the tapped card where it was", abs(after - before) <= 2, [before, after])
        page.evaluate("goToUnit(140)")
        wait_settled(page)
        box = page.evaluate("""() => { const r = document.querySelector('li.unit[data-id="140"]').getBoundingClientRect(); return [r.top, r.bottom, innerHeight]; }""")
        # it opens the card's Details, so a tall card is centred (scrollIntoView, block centre) and a short one is fully on screen
        fits = box[1] - box[0] <= box[2]
        check("goToUnit shows the card: centred, and fully on screen when it fits",
              abs((box[0] + box[1]) / 2 - box[2] / 2) <= 2 and (not fits or (box[0] >= 0 and box[1] <= box[2])), box)
        page.evaluate("openIds.clear(); renderUnits(); window.scrollTo(0, 0)")
        wait_settled(page)

        print("\n--- 3. Details on a phone redraws one card ---")
        r = page.evaluate(TOGGLE, "3")
        check("opening Details: only that card is drawn again", r["fresh"] == ["3"] and r["total"] == 150, r)
        check("its Details panel is open", r["panel"], r)
        wait_settled(page)
        r = page.evaluate(TOGGLE, "3")
        check("closing Details: only that card is drawn again, panel shut", r["fresh"] == ["3"] and not r["panel"], r)
        svg = page.evaluate("""() => [1, 2, 149].map(id => document.querySelectorAll('li.unit[data-id="' + id + '"] svg').length)""")
        check("every card still has its own chevrons (drawn once, then copied)", svg[0] > 0 and len(set(svg)) == 1, svg)
        check("no sideways scroll on Models", page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"))

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()

    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
