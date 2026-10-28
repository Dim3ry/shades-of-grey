"""v87 tests for Minifolio (chunk Mo2: unit card motion).

New behaviour only:
1. Stage change on the card: the old name slides out and the new one slides in; the stripe, the Up button and the bar segments
   fade from the old colour, the segments one after another; moving up pulses a ring once, back has none; all of it is put away after.
2. A model row moves on its own: its name slides, no ring, no other row and not the card.
3. Details: the panel grows and shrinks, the swatches pop in one by one and the whole thing ends under 300 ms even with 30 paints.
4. Nothing moves for Undo, a bulk move, a page load or a stage move you did not tap on that unit.
5. With reduced motion on: no animation of any kind, and no spacer left after closing.
6. A unit of 100 models: the stage change and Details stay quick.
7. 390 and 360 px, dark and light: no sideways scroll, tap targets 44 px or more once the motion has ended."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

PAINTS = [{"id": i, "brand": "Citadel", "name": f"Paint {i}", "colour": "#%02x%02x%02x" % (7 * i % 256, 90, 220 - 5 * i)} for i in range(1, 31)]
RECIPE = {"id": 1, "name": "Many paints", "steps": [{"title": "Step", "paints": [{"paint": i, "mix": 100}]} for i in range(1, 31)]}
BATCH = {"id": 1, "name": "Batch squad", "hobby": "40K", "stage": 2, "count": 5, "recipes": [1], "added": "2026-10-01", "log": [["2026-10-01", 2]]}
OTHER = {"id": 2, "name": "Other squad", "hobby": "40K", "stage": 3, "count": 5, "added": "2026-10-01", "log": [["2026-10-01", 3]]}
EACH = {"id": 4, "name": "Each squad", "hobby": "40K", "stage": 1, "count": 3, "each": True, "stages": [1, 4, 4], "added": "2026-10-01", "log": [["2026-10-01", 1]]}
HUGE = {"id": 5, "name": "Huge unit", "hobby": "40K", "stage": 0, "count": 100, "each": True, "stages": [i % 6 for i in range(100)], "added": "2026-10-01", "log": [["2026-10-01", 0]]}
UNITS = [BATCH, OTHER, EACH]

def card(page, uid):
    return page.locator(f"li.unit[data-id='{uid}']")

def start(page, units=None):
    load(page, units=units or UNITS, paints=PAINTS, recipes=[RECIPE])
    page.click('nav button[data-tab="units"]')
    page.wait_for_timeout(250)

def running(page):
    """Animations running inside the unit list (the Undo message has its own, longer line)."""
    return page.evaluate("() => document.querySelector('ul.units').getAnimations({ subtree: true }).length")

def moving(page):
    """Everything the app has marked as moving, anywhere on the page."""
    return page.evaluate("() => document.querySelectorAll('.mo-stage, .mo-row, .mo-slide, .mo-pip').length")

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 900}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        print("\n--- 1. Stage change on the card ---")
        start(page)
        STAGES = page.evaluate("STAGES")
        check("nothing moves on a first load", moving(page) == 0 and page.evaluate("() => document.getAnimations().length") == 0)
        old_colour = page.evaluate("() => getComputedStyle(document.querySelector('li.unit[data-id=\"1\"]')).borderLeftColor")
        card(page, 1).locator(".up-button").click()
        info = page.evaluate("""() => { const li = document.querySelector('li.unit[data-id="1"]'); const st = li.querySelector('.stage');
            return { cls: li.className, text: st.textContent, from: st.dataset.from, before: getComputedStyle(st, '::before').content,
                     ring: getComputedStyle(li, '::after').animationName, stripe: getComputedStyle(li).borderLeftColor,
                     delays: [...li.querySelectorAll('.pip')].map(p => getComputedStyle(p).animationDelay), pips: li.querySelectorAll('.mo-pip').length }; }""")
        check("the new name is the text; the old one is only a pseudo-element, not page text",
              info["text"] == STAGES[3] and info["from"] == STAGES[2] and STAGES[2] in info["before"], info)
        check("up pulses a ring once", "mo-up" in info["cls"] and info["ring"] == "mo-ring", info)
        check("the stripe starts in the old stage colour", info["stripe"] == old_colour, (info["stripe"], old_colour))
        check("the bar segments follow one another", info["pips"] == len(STAGES) and len(set(info["delays"])) == len(STAGES), info["delays"])
        page.wait_for_timeout(1100)
        check("everything is put away afterwards", moving(page) == 0 and running(page) == 0)
        card(page, 1).locator(".step-back").click()
        during = page.evaluate("""() => ({ other: document.querySelector('li.unit[data-id="2"]').className, mine: document.querySelector('li.unit[data-id="1"]').className,
            ring: getComputedStyle(document.querySelector('li.unit[data-id="1"]'), '::after').animationName,
            out: getComputedStyle(document.querySelector('li.unit[data-id="1"] .stage'), '::before').animationName })""")
        check("back slides the names the other way, has no ring, and only that unit moves",
              "mo-back" in during["mine"] and "mo-up" not in during["mine"] and during["ring"] == "none"
              and during["out"] == "mo-name-out-down" and "mo-" not in during["other"], during)
        page.wait_for_timeout(1000)

        print("\n--- 2. A model row ---")
        open_btn = card(page, 4).locator(".details-toggle")
        open_btn.click()
        page.wait_for_timeout(500)
        card(page, 4).locator(".each-up").first.click()
        row = page.evaluate("""() => { const li = document.querySelector('li.unit[data-id="4"]'); const rows = [...li.querySelectorAll('.each-row')];
            return { moved: rows.map(r => r.classList.contains('mo-row')), card: li.className, ring: getComputedStyle(rows[0], '::after').animationName,
                     name: rows[0].querySelector('.each-stage-name').textContent, was: rows[0].querySelector('.each-stage-name').dataset.from }; }""")
        check("only the tapped row moves: its name slides, the card does not pulse",
              row["moved"] == [True, False, False] and "mo-stage" not in row["card"] and row["name"] == STAGES[2] and row["was"] == STAGES[1], row)
        page.wait_for_timeout(1000)
        check("…and it is put away afterwards", moving(page) == 0)

        print("\n--- 3. Details opens and closes ---")
        start(page, units=[BATCH, OTHER])
        card(page, 1).locator(".details-toggle").click()
        a = page.evaluate("""() => { const pn = document.querySelector('li.unit[data-id="1"] > .panel');
            const sw = pn.querySelectorAll('.paints-preview .swatch'); const as = pn.getAnimations();
            return { panel: as.length, overflow: pn.style.overflow, swatches: sw.length, popping: [...sw].filter(s => s.getAnimations().length).length }; }""")
        check("the panel grows (clipped while it does) and the swatches pop in", a["panel"] >= 1 and a["overflow"] == "hidden" and a["swatches"] == 6 and a["popping"] == 6, a)
        page.wait_for_timeout(400)
        card(page, 1).locator(".details-toggle").click()
        page.wait_for_timeout(300)
        card(page, 1).locator(".details-toggle").click()
        total = page.evaluate("""() => { const sw = document.querySelectorAll('li.unit[data-id="1"] .paints-preview .swatch, li.unit[data-id="1"] .paints-grid .swatch');
            return { n: sw.length, ends: [...sw].map(s => s.getAnimations().map(a => { const t = a.effect.getComputedTiming(); return t.delay + t.duration; })).flat() }; }""")
        check("30 paints in the unit's recipe: the six shown pop one after another, all over in under 300 ms",
              total["n"] == 6 and total["ends"] and max(total["ends"]) < 300 and len(set(total["ends"])) == 6, total)
        page.wait_for_timeout(400)
        at_rest = page.evaluate("() => document.querySelector('li.unit[data-id=\"1\"] > .panel').style.overflow") + "|" + str(running(page))
        check("at rest the panel is not clipped and nothing is running", at_rest == "|0", at_rest)
        card(page, 1).locator(".details-toggle").click()
        closing = page.evaluate("""() => ({ panels: document.querySelectorAll('li.unit[data-id="1"] > .panel').length, ghost: document.querySelectorAll('li.unit[data-id="1"] > .panel-ghost').length,
            hidden: document.querySelector('.panel-ghost')?.getAttribute('aria-hidden') })""")
        check("closing: the panel is gone at once; a hidden spacer shrinks away", closing == {"panels": 0, "ghost": 1, "hidden": "true"}, closing)
        page.wait_for_timeout(500)
        check("…and the spacer removes itself", page.locator(".panel-ghost").count() == 0)

        print("\n--- 4. Only a tapped change moves ---")
        card(page, 1).locator(".up-button").click()
        page.wait_for_timeout(1100)
        page.click("#toast-undo")
        page.wait_for_timeout(100)
        check("Undo moves nothing", moving(page) == 0 and page.evaluate("() => document.querySelectorAll('li.unit').length") == 2)
        page.click("#toggle-select")
        page.wait_for_timeout(200)
        page.evaluate("() => document.querySelectorAll('.unit-tick input').forEach(i => i.click())")
        page.wait_for_timeout(100)
        page.evaluate("""() => { const s = document.querySelector('#select-bar select'); if (s) { s.value = '5'; s.dispatchEvent(new Event('change', { bubbles: true })); } }""")
        page.wait_for_timeout(100)
        check("moving several at once moves nothing", moving(page) == 0)

        print("\n--- 5. Reduced motion ---")
        rctx = browser.new_context(viewport={"width": 390, "height": 900}, service_workers="block", reduced_motion="reduce")
        rp = rctx.new_page()
        start(rp, units=[BATCH, OTHER])
        card(rp, 1).locator(".up-button").click()
        r1 = rp.evaluate("() => ({ marked: document.querySelectorAll('.mo-stage, .mo-slide, .mo-pip').length, running: document.getAnimations().length })")
        check("a stage change has no movement and no animation at all", r1 == {"marked": 0, "running": 0}, r1)
        card(rp, 1).locator(".details-toggle").click()
        r2 = rp.evaluate("() => ({ running: document.getAnimations().length, clipped: document.querySelector('li.unit[data-id=\"1\"] > .panel').style.overflow })")
        check("Details opens at once, unclipped", r2 == {"running": 0, "clipped": ""}, r2)
        card(rp, 1).locator(".details-toggle").click()
        check("…and closes at once, no spacer", rp.locator(".panel-ghost").count() == 0 and rp.evaluate("() => document.getAnimations().length") == 0)
        rctx.close()

        print("\n--- 6. A unit with 100 models ---")
        start(page, units=[HUGE])
        card(page, 5).locator(".details-toggle").click()
        page.wait_for_timeout(500)
        cost = page.evaluate("""() => { const t0 = performance.now(); changeStage(5, 1); const t1 = performance.now();
            const b = document.querySelector('li.unit[data-id="5"] .details-toggle'); const t2 = performance.now(); b.click(); const t3 = performance.now();
            return { stage: Math.round(t1 - t0), toggle: Math.round(t3 - t2) }; }""")
        print("   measured:", cost)
        check("100 models: the stage change and closing Details each take well under half a second", cost["stage"] < 500 and cost["toggle"] < 500, cost)

        print("\n--- 7. Layout ---")
        for width in (390, 360):
            for scheme in ("dark", "light"):
                c2 = browser.new_context(viewport={"width": width, "height": 900}, service_workers="block", color_scheme=scheme)
                p2 = c2.new_page()
                start(p2)
                card(p2, 1).locator(".up-button").click()
                card(p2, 4).locator(".details-toggle").click()
                p2.wait_for_timeout(1200)
                small = p2.evaluate("""() => [...document.querySelectorAll('li.unit .step-back, li.unit .up-button, li.unit .details-toggle, li.unit .each-back, li.unit .each-up')]
                    .filter(b => !b.disabled && b.offsetParent && (b.getBoundingClientRect().height < 43.9 || b.getBoundingClientRect().width < 43.9)).length""")
                check(f"{width} px {scheme}: no sideways scroll, step buttons 44 px or more at rest", no_sideways(p2) and small == 0, small)
                c2.close()

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
