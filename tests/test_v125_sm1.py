"""SM1 tests for Minifolio (smoother start circle travel and Models taps). New behaviour only:
1. The travelling copies of the segments use the segments' own font (they were drawn in the browser's serif), in two themes.
2. During the travel the labels and icons only move and scale (transform): their font size, line height and weight are set
   at most once more (half way), not on every frame; colours are plain rgba(), not color-mix().
3. Opening or closing Details on a phone redraws only that card; every other card stays the same element.
4. content-visibility on the unit cards does not change the Models page height.
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
    const changes = { w: {}, c: {}, icon: {}, t: {}, other: {} }, colours = [];
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
        obs.disconnect(); done({ started, want, font, changes, colours: colours.slice(0, 400), wide }); };
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
    once = {k: {p: ch[k].get(p, 0) for p in sizes} for k in ("c", "icon", "t")}
    check(f"{theme}: label and icon sizes are set at most once more (half way), not every frame",
          all(n <= 4 for k in once.values() for n in k.values()), once)   # 4 copies, at most one switch each
    check(f"{theme}: the label only moves and scales (transform is the only thing that changes on it)",
          set(ch["t"]) <= {"transform"} and ch["t"].get("transform", 0) >= 8, ch["t"])
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

        print("\n--- 4. content-visibility keeps the Models page height ---")
        page.set_viewport_size({"width": 390, "height": 844})
        page.emulate_media(color_scheme="dark")
        t.load(page, units=units(120))
        page.evaluate("document.querySelector('.tabs button[data-tab=units]').click()")
        page.evaluate(_FINISH_BAR)
        wait_settled(page)
        r = page.evaluate("""() => { const cards = [...document.querySelectorAll('li.unit')];
            const cv = getComputedStyle(cards[0]).contentVisibility, h0 = document.documentElement.scrollHeight;
            const far = cards[cards.length - 1].getBoundingClientRect().height, near = cards[0].getBoundingClientRect().height;
            const s = document.createElement('style'); s.textContent = 'li.unit { content-visibility: visible !important; }'; document.head.append(s);
            const h1 = document.documentElement.scrollHeight, real = cards[cards.length - 1].getBoundingClientRect().height; s.remove();
            return { cv, h0, h1, far, near, real, n: cards.length }; }""")
        check("unit cards skip drawing while off screen (content-visibility: auto)", r["cv"] == "auto", r)
        check("an off-screen card takes the same height as a drawn one", abs(r["far"] - r["real"]) < 0.5 and abs(r["near"] - r["real"]) < 0.5, r)
        check("the page is exactly as tall as with every card drawn", abs(r["h0"] - r["h1"]) < 1 and r["n"] == 120, r)
        page.evaluate("window.scrollTo(0, 1e6)")
        page.wait_for_timeout(300)
        end = page.evaluate("[document.documentElement.scrollHeight, Math.round(scrollY + innerHeight)]")
        check("scrolled to the end, the page height has not moved", abs(end[0] - r["h0"]) < 1 and abs(end[1] - end[0]) <= 1, [end, r["h0"]])
        page.evaluate("window.scrollTo(0, 0)")
        wait_settled(page)

        print("\n--- 3. Details on a phone redraws one card ---")
        r = page.evaluate(TOGGLE, "3")
        check("opening Details: only that card is drawn again", r["fresh"] == ["3"] and r["total"] == 120, r)
        check("its Details panel is open", r["panel"], r)
        wait_settled(page)
        r = page.evaluate(TOGGLE, "3")
        check("closing Details: only that card is drawn again, panel shut", r["fresh"] == ["3"] and not r["panel"], r)
        svg = page.evaluate("""() => [1, 2, 120].map(id => document.querySelectorAll('li.unit[data-id="' + id + '"] svg').length)""")
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
