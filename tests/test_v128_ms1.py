"""MS1 tests for Minifolio (Models opens without the first-frame stall). New behaviour only, and nothing here depends on the machine's speed:
1. A redraw on Models builds again only the cards that changed: a stage tap, a rename or Undo rebuilds that one card and every other card
   stays the same element; a filter shows the right cards and keeps the ones it showed before; a faction colour or a recipe's new name
   still reaches the cards that show it.
2. Arriving on Models with motion (the start circle's travel, the slide from the Dashboard) puts only the first screen of cards (and a
   margin) in the page in the tap's frame. The rest arrive over the next frames, in order and below the ones already there, and all
   of them are in by the time the travel (or slide) ends; nothing on screen moves meanwhile, the first card can take keyboard focus at once, and a
   wheel turn puts the rest in at once. Reduced motion draws the whole list at once (and has no travel).
3. With 300 cards of mixed shapes: the page height is steady while scrolling, a stage tap keeps the tapped card in place, and goToUnit
   finds and centres a card that was not drawn yet.
4. On a wide screen (1280 px) the side pane still shows an open unit, and a stage tap there changes the card and the pane.
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
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

def mixed_units(n):
    # long names, nicknames, two factions, repaint, linked recipes and per-model stages: cards of many heights
    out = []
    for i in range(1, n + 1):
        u = {"id": i, "name": (f"A very long unit name that wraps onto a second line {i}" if i % 5 == 0 else f"Squad {i}"),
             "hobby": "40K", "stage": i % 6, "count": 3, "added": "2026-10-01", "log": [["2026-10-01", i % 6]]}
        if i % 7 == 0: u["nickname"] = f"The nickname of unit {i}"
        if i % 3 == 0: u["faction"] = "Iron Wolves"
        if i % 8 == 1: u["faction"] = "Ash Riders"
        if i % 11 == 0: u["repaint"] = True
        if i % 4 == 0: u["recipes"] = [101]
        if i % 6 == 0: u.update(each=True, stages=[1, 3, 5])
        out.append(u)
    return out

COLOURS = {"factionColours": {"Iron Wolves": "#3366aa", "Ash Riders": "#aa5522"}}

def load(page, n, tab, launch):
    t.load(page, units=mixed_units(n), recipes=t.RECIPES, settings=dict(COLOURS, tab=tab), launch=launch)

def settle(page):
    page.evaluate(_FINISH_BAR)
    wait_settled(page)

# Tap something that brings Models in, then watch every frame until the travel (or slide) and the list's arrival are over.
ARRIVE = """(sel) => new Promise(done => {
    const list = document.getElementById('unit-list');
    const cards = () => list.querySelectorAll(':scope > li.unit');
    document.querySelector(sel).click();
    const first = cards().length, max = typeof firstScreenCards === 'function' ? firstScreenCards() : 0;
    const toggle = list.querySelector('li.unit .details-toggle');
    if (toggle) toggle.focus();
    const focused = !!toggle && document.activeElement === toggle;
    const frames = [];
    const step = () => {
        const all = cards(), last = all[all.length - 1];
        frames.push({ n: all.length, travel: !!document.querySelector('.mo-tr'), arriving: views.units.getAnimations().length > 0,
                      y: scrollY, top: Math.round(all[0].getBoundingClientRect().top), bottom: last.getBoundingClientRect().bottom });
        if (frames.length < 3 || frames[frames.length - 1].travel || frames[frames.length - 1].arriving) requestAnimationFrame(step);
        else done({ first, max, focused, frames, ids: [...cards()].map(li => +li.dataset.id),
                    want: models.filter(isVisible).map(m => m.id), height: innerHeight });
    };
    queueMicrotask(() => requestAnimationFrame(step));   // after the app has asked for its own frames, as anything waiting for the travel does
})"""

def arrival_checks(page, label, sel, total, travel):
    r = page.evaluate(ARRIVE, sel)
    f = r["frames"]
    check(f"{label}: the tap's frame holds only the first screen and a margin ({r['first']} of {total} cards, at most {r['max']})",
          0 < r["first"] <= r["max"] < total, [r["first"], r["max"]])
    check(f"{label}: those cards fill the first screen", f[0]["bottom"] >= r["height"], [f[0]["bottom"], r["height"]])
    full = next((i for i, x in enumerate(f) if x["n"] == total), None)
    check(f"{label}: the rest arrive over later frames", full is not None and full >= 1 and len({x["n"] for x in f}) >= 3, [x["n"] for x in f][:30])
    if travel:
        ended = next((i for i, x in enumerate(f) if i > 0 and not x["travel"]), None)
        check(f"{label}: every card is in by the time the travel ends", ended is not None and f[ended]["n"] == total, [(x["n"], x["travel"]) for x in f][-12:])
    else:
        ended = next((i for i, x in enumerate(f) if i > 0 and not x["arriving"]), None)
        check(f"{label}: every card is in by the end of the slide", ended is not None and f[ended]["n"] == total, [(x["n"], x["arriving"]) for x in f][-12:])
    check(f"{label}: cards only ever arrive (the count never drops)", all(b["n"] >= a["n"] for a, b in zip(f, f[1:])), [x["n"] for x in f])
    check(f"{label}: nothing on screen moves (scroll and first card stay put)", len({(x["y"], x["top"]) for x in f}) == 1, sorted({(x["y"], x["top"]) for x in f}))
    check(f"{label}: the list ends in the right order, for a screen reader too", r["ids"] == r["want"], (r["ids"][:5], r["want"][:5]))
    check(f"{label}: the first card takes keyboard focus straight away", r["focused"])

MARK = """() => { document.querySelectorAll('#unit-list > li').forEach(li => li.__ms1 = true); }"""
FRESH = """() => { const cards = [...document.querySelectorAll('#unit-list > li.unit')];
    return { fresh: cards.filter(li => !li.__ms1).map(li => +li.dataset.id), total: cards.length }; }"""

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", color_scheme="dark", has_touch=True)
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        print("--- 2. Start circle to Models, 300 mixed cards (Models not drawn yet) ---")
        load(page, 300, "dashboard", True)
        arrival_checks(page, "circle, Models new", '.tabs .arc > [data-tab="units"]', 300, True)
        settle(page)

        print("\n--- 3. 300 mixed cards: height, a stage tap, Undo, goToUnit ---")
        r = page.evaluate("""async () => { const hs = [], heights = new Set();
            document.querySelectorAll('li.unit').forEach(li => heights.add(Math.round(li.getBoundingClientRect().height)));
            for (let y = 0; y <= document.documentElement.scrollHeight; y += 900) {
                window.scrollTo(0, y); await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
                hs.push(document.documentElement.scrollHeight); }
            return { hs: [...new Set(hs)], kinds: heights.size, n: document.querySelectorAll('li.unit').length }; }""")
        check("300 cards of mixed heights are all there", r["kinds"] >= 3 and r["n"] == 300, r)
        check("the page height stays the same while scrolling to the end", len(r["hs"]) == 1, r["hs"])

        print("\n--- 1. A redraw builds again only what changed ---")
        before = page.evaluate("""() => { const li = document.querySelector('li.unit[data-id="152"]');
            window.scrollTo(0, 0); window.scrollTo(0, li.getBoundingClientRect().top + scrollY - 250);
            return li.getBoundingClientRect().top; }""")
        wait_settled(page)
        page.evaluate(MARK)
        page.locator('li.unit[data-id="152"] .up-button').click()
        r = page.evaluate(FRESH)
        check("a stage tap rebuilds that one card, not the list", r == {"fresh": [152], "total": 300}, r)
        wait_settled(page)
        after = page.evaluate("""() => document.querySelector('li.unit[data-id="152"]').getBoundingClientRect().top""")
        check("a stage tap keeps the tapped card where it was", abs(after - before) <= 2, [before, after])
        stage = lambda: page.evaluate("""() => document.querySelector('li.unit[data-id="152"] .stage').textContent""")
        moved = stage()
        page.evaluate(MARK)
        page.locator("#toast button").click()
        r = page.evaluate(FRESH)
        check("Undo puts the card back (that card only is rebuilt)", r["fresh"] == [152] and stage() != moved and
              page.evaluate("models.find(m => m.id === 152).stage") == 152 % 6, [r, moved, stage()])
        page.evaluate(MARK)
        page.evaluate("() => { const m = models.find(x => x.id === 3); m.name = 'Renamed squad'; render(); }")
        r = page.evaluate(FRESH)
        check("a rename rebuilds that card only, with the new name", r["fresh"] == [3] and
              page.evaluate("""() => document.querySelector('li.unit[data-id="3"] .name').textContent""") == "Renamed squad", r)
        page.evaluate(MARK)
        page.evaluate("() => { filters.faction = 'Iron Wolves'; render(); }")
        r = page.evaluate("""() => ({ ids: [...document.querySelectorAll('#unit-list > li.unit')].map(li => +li.dataset.id),
            want: models.filter(isVisible).map(m => m.id), kept: [...document.querySelectorAll('#unit-list > li.unit')].every(li => li.__ms1) })""")
        check("a filter shows exactly its cards, in order, and keeps the cards it showed", r["ids"] == r["want"] and len(r["ids"]) == 87 and r["kept"], r["ids"][:5])
        page.evaluate("() => { clearFilters(); render(); }")
        r = page.evaluate(FRESH)
        check("clearing the filter brings back the same cards (none rebuilt)", r == {"fresh": [], "total": 300}, r)
        page.evaluate(MARK)
        page.evaluate("setFactionColour('Ash Riders', '#22aa66')")
        r = page.evaluate("""() => { const ids = [...document.querySelectorAll('#unit-list > li.unit')].filter(li => !li.__ms1).map(li => +li.dataset.id);
            const want = models.filter(m => m.faction === 'Ash Riders').map(m => m.id);
            return { same: JSON.stringify(ids) === JSON.stringify(want), n: ids.length,
                     colour: document.querySelector('li.unit[data-id="9"]').style.getPropertyValue('--faction-colour') }; }""")
        check("a new faction colour rebuilds exactly the cards of that faction, in its colour", r["same"] and r["n"] == 38 and r["colour"] == "#22aa66", r)
        page.evaluate("() => { recipeById(101).name = 'Armour blue renamed'; render(); }")
        chip = page.evaluate("""() => document.querySelector('li.unit[data-id="4"] .recipe-chip').textContent""")
        check("a recipe's new name reaches the cards that link it", "Armour blue renamed" in chip, chip)
        page.evaluate(MARK)
        page.evaluate("() => { const i = models.findIndex(m => m.id === 10); models.splice(i, 1); render(); }")
        r = page.evaluate(FRESH)
        check("deleting a unit takes its card out and rebuilds none", r == {"fresh": [], "total": 299} and
              not page.evaluate("""() => !!document.querySelector('li.unit[data-id="10"]')"""), r)

        print("\n--- 3. goToUnit finds a card that is not drawn yet ---")
        page.evaluate("() => { window.scrollTo(0, 0); document.querySelector('.tabs button[data-tab=\"dashboard\"]').click(); }")
        settle(page)
        page.evaluate("() => { const m = models.find(x => x.id === 20); m.stage = (m.stage + 1) % 6; render(); }")   # a change made elsewhere
        r = page.evaluate("""() => { goToUnit(260); const li = document.querySelector('li.unit[data-id="260"]');
            return { found: !!li, n: document.querySelectorAll('#unit-list > li.unit').length }; }""")
        check("goToUnit from the Dashboard finds card 260 while the list is still arriving", r["found"] and r["n"] < 299, r)
        settle(page)
        box = page.evaluate("""() => { const r = document.querySelector('li.unit[data-id="260"]').getBoundingClientRect(); return [r.top, r.bottom, innerHeight,
            document.querySelectorAll('#unit-list > li.unit').length]; }""")
        fits = box[1] - box[0] <= box[2]
        check("goToUnit centres the card (fully on screen when it fits), and the rest of the list has arrived",
              abs((box[0] + box[1]) / 2 - box[2] / 2) <= 2 and (not fits or (box[0] >= 0 and box[1] <= box[2])) and box[3] == 299, box)

        print("\n--- 2. The slide from the Dashboard, a wheel turn, and the circle with Models already drawn ---")
        page.evaluate("() => { openIds.clear(); document.querySelector('.tabs button[data-tab=\"dashboard\"]').click(); }")
        settle(page)
        page.evaluate("() => { const m = models.find(x => x.id === 40); m.stage = (m.stage + 1) % 6; render(); }")   # a change made elsewhere
        arrival_checks(page, "slide from the Dashboard", '.tabs button[data-tab="units"]', 299, False)
        settle(page)
        page.evaluate("() => { document.querySelector('.tabs button[data-tab=\"dashboard\"]').click(); }")
        settle(page)
        n, r = page.evaluate("""() => { document.querySelector('.tabs button[data-tab="units"]').click();
            const n = document.querySelectorAll('#unit-list > li.unit').length;
            document.dispatchEvent(new WheelEvent('wheel', { bubbles: true, deltaY: 120 }));
            return [n, document.querySelectorAll('#unit-list > li.unit').length]; }""")
        check("turning the wheel while the list arrives puts the rest in at once", n < 299 and r == 299, [n, r])
        settle(page)
        page.evaluate("goToStartPage()")   # back to the circle: Models stays drawn underneath
        settle(page)
        arrival_checks(page, "circle, Models already drawn", '.tabs .arc > [data-tab="units"]', 299, True)

        print("\n--- 2. Reduced motion: all at once, no travel ---")
        page.emulate_media(reduced_motion="reduce")
        load(page, 40, "dashboard", True)
        r = page.evaluate("""() => { document.querySelector('.tabs .arc > [data-tab="units"]').click();
            return { n: document.querySelectorAll('#unit-list > li.unit').length, travel: !!document.querySelector('.mo-tr') }; }""")
        check("reduced motion: the whole list is drawn at once, with no travel", r == {"n": 40, "travel": False}, r)
        page.emulate_media(reduced_motion="no-preference")

        print("\n--- 4. Wide screen: the side pane ---")
        page.set_viewport_size({"width": 1280, "height": 800})
        load(page, 60, "units", False)
        page.locator('li.unit[data-id="5"] .details-toggle').click()
        wait_settled(page)
        r = page.evaluate("""() => ({ side: [...document.querySelectorAll('#unit-side .unit-side-card')].map(c => c.dataset.id),
            current: document.querySelector('li.unit[data-id="5"]').getAttribute('aria-current') })""")
        check("wide: an open unit shows in the side pane and its card is marked", r == {"side": ["5"], "current": "true"}, r)
        page.evaluate(MARK)
        page.locator('li.unit[data-id="5"] .up-button').click()
        r = page.evaluate("""() => ({ fresh: [...document.querySelectorAll('#unit-list > li.unit')].filter(li => !li.__ms1).map(li => +li.dataset.id),
            stage: models.find(m => m.id === 5).stage, card: document.querySelector('li.unit[data-id="5"] .stage').textContent,
            side: document.querySelector('#unit-side .unit-side-card[data-id="5"]') !== null })""")
        check("wide: a stage tap rebuilds that card only and the side pane stays", r["fresh"] == [5] and r["stage"] == 6 and r["side"], r)
        check("no sideways scroll", page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"))

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()

    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
