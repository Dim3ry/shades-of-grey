"""MC1 tests for Minifolio (compact model cards that open on a tap). New behaviour only:
1. Cards start closed: each shows the unit's name, game, army and stage in words (with a small strip), and is one button
   (aria-expanded false) read as "name, game, army, stage". No stepper, no Details button, no recipe buttons yet.
2. A tap anywhere on a closed card opens it (stepper, recipe buttons, Details); opening another closes the first, with its Details.
   A tap on the open card's header closes it.
3. The open card's stepper works in one tap, and a stage change draws only that card again; a redraw keeps the open card open
   and the closed ones closed (MS1's cardKey knows which is open).
4. goToUnit opens its card (and Details) and scrolls to it. Undo after deleting a unit from its open card brings it back open.
5. Keyboard: Enter opens, focus stays on the card, Tab reaches the buttons inside, Space closes.
6. Motion: the opened card unrolls (clip-path) and the cards below move (transform), nothing is left at rest; Reduce motion: no animation.
7. Wide screen (1280 px): a tap opens the unit in the side pane, as before, and the other list cards stay compact.
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

def units(n):
    out = []
    for i in range(1, n + 1):
        u = {"id": i, "name": f"Squad {i}", "hobby": "Skirmish", "stage": 2 + i % 3, "count": 3, "added": "2026-10-01", "log": [["2026-10-01", 2 + i % 3]]}
        if i % 2: u["faction"] = "Iron Wolves"
        if i == 1: u["recipes"] = [101]
        if i == 6: u.update(each=True, stages=[1, 3, 3])
        out.append(u)
    return out

SETTINGS = {"factionColours": {"Iron Wolves": "#3366aa"}, "tab": "units"}

def card(uid):
    return f'#unit-list > li.unit[data-id="{uid}"]'

def load(page, n=12):
    t.load(page, units=units(n), recipes=t.RECIPES, settings=SETTINGS)
    page.evaluate(_FINISH_BAR)
    wait_settled(page)

def is_open(page, uid):
    return page.evaluate("(s) => { const c = document.querySelector(s); return !!c && !c.classList.contains('compact') && !!c.querySelector('.stepper'); }", card(uid))

def open_ids(page):
    return page.evaluate("() => [...document.querySelectorAll('#unit-list > li.unit:not(.compact)')].map(li => +li.dataset.id)")

MARK = "() => { document.querySelectorAll('#unit-list > li.unit').forEach(li => li.__mc1 = true); }"
FRESH = "() => [...document.querySelectorAll('#unit-list > li.unit')].filter(li => !li.__mc1).map(li => +li.dataset.id)"

def settle(page):
    page.wait_for_function("() => ![...document.querySelectorAll('#unit-list > li.unit')].some(li => li.getAnimations().length)")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", color_scheme="dark", has_touch=True)
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        load(page)

        print("--- 1. Cards start closed ---")
        r = page.evaluate("""() => { const cards = [...document.querySelectorAll('#unit-list > li.unit')];
            const c = cards[0], info = c.querySelector('.info');
            return { n: cards.length, compact: cards.filter(li => li.classList.contains('compact')).length,
                     inner: cards.filter(li => li.querySelector('.stepper, .details-toggle, .recipe-links, .panel, button')).length,
                     name: c.querySelector('.name').textContent, details: c.querySelector('.details').textContent,
                     stage: c.querySelector('.unit-sum .stage').textContent, pips: c.querySelectorAll('.unit-sum .pip').length,
                     dot: !!c.querySelector('.faction-dot'), role: info.getAttribute('role'), tab: info.tabIndex,
                     expanded: info.getAttribute('aria-expanded'), label: info.getAttribute('aria-label'), stages: STAGES }; }""")
        st = r["stages"]
        check("every card starts closed", r["n"] == 12 and r["compact"] == 12, r)
        check("a closed card holds no stepper, Details, recipe buttons or any other button", r["inner"] == 0, r)
        check("it shows the name, game and army (with its colour dot)",
              r["name"] == "Squad 1" and "Skirmish" in r["details"] and "Iron Wolves" in r["details"] and r["dot"], r)
        check("…and the stage in words, with a strip of every stage", r["stage"] == st[3] and r["pips"] == len(st), r)
        check("the card is one button, closed, read as name, game, army, stage",
              r["role"] == "button" and r["tab"] == 0 and r["expanded"] == "false" and r["label"] == f"Squad 1, Skirmish, Iron Wolves, {st[3]}", r)
        mixed = page.evaluate("(s) => document.querySelector(s + ' .info').getAttribute('aria-label')", card(6))
        check("a unit tracked model by model shows its overall stage the same way",
              page.locator(card(6) + " .unit-sum .stage").inner_text().strip() == f"2 {st[3]} · 1 {st[1]}" and mixed.endswith(f"2 {st[3]}, 1 {st[1]}"), mixed)
        heights = page.evaluate("() => [...document.querySelectorAll('#unit-list > li.unit')].map(li => li.getBoundingClientRect().height)")

        print("\n--- 2. A tap opens one card and closes any other ---")
        page.locator(card(1) + " .details").click()
        settle(page)
        check("a tap on the card opens it: stepper, recipe button and Details", is_open(page, 1)
              and page.locator(card(1) + " .recipe-links button").count() == 1 and page.locator(card(1) + " .details-toggle").count() == 1)
        check("its header says it is open", page.get_attribute(card(1) + " .info", "aria-expanded") == "true")
        open_h = page.evaluate("(s) => document.querySelector(s).getBoundingClientRect().height", card(1))
        check("a closed card is well under half the open one's height", max(heights[1:5]) <= open_h / 2, (heights[:5], open_h))
        page.locator(card(1) + " .details-toggle").click()
        check("Details opens inside the open card as before", page.locator(card(1) + " > .panel").count() == 1)
        page.locator(card(3)).click(position={"x": 8, "y": 8})   # the card's corner, not its text
        settle(page)
        check("opening another card closes the first, with its Details", open_ids(page) == [3] and page.locator("#unit-list .panel").count() == 0, open_ids(page))
        page.locator(card(3) + " .name").click()
        settle(page)
        check("a tap on the open card's header closes it", open_ids(page) == [], open_ids(page))

        print("\n--- 3. The stepper in an open card, and redraws ---")
        page.locator(card(4)).click()
        settle(page)
        page.evaluate(MARK)
        page.locator(card(4) + " .up-button").click()
        check("one tap on Up moves the unit one stage", page.evaluate("models.find(m => m.id === 4).stage") == 4)
        check("…the card stays open and shows the new stage", is_open(page, 4) and page.locator(card(4) + " .stepper .stage").inner_text().strip() == st[4])
        check("…and only that card was drawn again", page.evaluate(FRESH) == [4], page.evaluate(FRESH))
        settle(page)
        page.evaluate(MARK)
        page.evaluate("render()")
        check("a full redraw keeps the open card open and the others closed, drawing none again",
              open_ids(page) == [4] and page.evaluate(FRESH) == [], (open_ids(page), page.evaluate(FRESH)))
        page.locator(card(4) + " .name").click()
        settle(page)
        page.evaluate("render()")
        check("…and a closed card stays closed after a redraw", open_ids(page) == [])

        print("\n--- 4. goToUnit ---")
        page.evaluate("window.scrollTo(0, 0)")
        page.evaluate("showTab('dashboard')")
        page.evaluate("goToUnit(11)")
        page.wait_for_timeout(600)
        settle(page)
        r = page.evaluate("""(s) => { const c = document.querySelector(s); const b = c.getBoundingClientRect();
            return { top: b.top, bottom: b.bottom, h: innerHeight, panel: !!c.querySelector(':scope > .panel') }; }""", card(11))
        check("goToUnit opens its card with its Details", open_ids(page) == [11] and r["panel"], (open_ids(page), r))
        check("…and scrolls it onto the screen", r["top"] < r["h"] and r["bottom"] > 0, r)
        page.locator(card(11) + " .name").click()
        settle(page)
        page.locator(card(8)).click()
        settle(page)
        page.locator(card(8) + " .details-toggle").click()
        page.locator(card(8) + " .panel button.danger-button", has_text="Delete").last.click()
        page.click("#dialog-yes")
        check("Delete from an open card takes it out", page.locator(card(8)).count() == 0 and open_ids(page) == [])
        page.click("#toast-undo")
        settle(page)
        check("…and Undo brings it back open, with its Details", open_ids(page) == [8] and page.locator(card(8) + " > .panel").count() == 1, open_ids(page))
        page.locator(card(8) + " .name").click()
        settle(page)

        print("\n--- 5. Keyboard ---")
        page.focus(card(2) + " .info")
        page.keyboard.press("Enter")
        settle(page)
        r = page.evaluate("(s) => ({ inCard: document.querySelector(s).contains(document.activeElement), expanded: document.activeElement.getAttribute('aria-expanded') })", card(2))
        check("Enter opens the card and focus stays on it", is_open(page, 2) and r["inCard"] and r["expanded"] == "true", r)
        page.keyboard.press("Tab")
        first = page.evaluate("() => document.activeElement.className")
        page.keyboard.press("Tab")
        second = page.evaluate("() => document.activeElement.className")
        check("Tab reaches the buttons inside: Details, then the stepper", "details-toggle" in first and second in ("step-back", "up-button"), (first, second))
        page.focus(card(2) + " .info")
        page.keyboard.press(" ")
        settle(page)
        check("Space on the header closes it again, focus still on the card",
              open_ids(page) == [] and page.evaluate("(s) => document.activeElement === document.querySelector(s + ' .info')", card(2)))

        print("\n--- 6. Motion ---")
        r = page.evaluate("""(s) => { document.querySelector(s).click();
            const out = {};
            for (const li of document.querySelectorAll('#unit-list > li.unit')) {
                const k = li.getAnimations().flatMap(a => a.effect.getKeyframes().flatMap(f => Object.keys(f)));
                if (k.length) out[li.dataset.id] = [...new Set(k)].filter(x => ['transform', 'clipPath', 'height', 'top', 'margin'].includes(x)); }
            return out; }""", card(5))
        check("the opened card unrolls with clip-path", "clipPath" in r.get("5", []), r)
        below = [k for k in r if int(k) > 5]
        check("the cards below move by transform only", below and all(r[k] == ["transform"] for k in below), r)
        settle(page)
        check("nothing is left moved at rest", page.evaluate("() => [...document.querySelectorAll('#unit-list > li.unit')].every(li => getComputedStyle(li).transform === 'none' && getComputedStyle(li).clipPath === 'none')"))
        rm = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        rp = rm.new_page()
        rp.on("pageerror", lambda x: errors.append(str(x)))
        load(rp)
        n = rp.evaluate("(s) => { document.querySelector(s).click(); return document.getAnimations().length; }", card(2))
        check("Reduce motion: the card opens at once, nothing animates", n == 0 and is_open(rp, 2), n)
        n = rp.evaluate("(s) => { document.querySelector(s + ' .name').click(); return document.getAnimations().length; }", card(2))
        check("…and closes at once", n == 0 and open_ids(rp) == [], n)
        rm.close()

        print("\n--- 7. Wide screen ---")
        page.set_viewport_size({"width": 1280, "height": 800})
        page.locator(card(5) + " .name").click()
        settle(page)
        page.locator(card(7)).click()
        settle(page)
        r = page.evaluate("""() => ({ side: [...document.querySelectorAll('#unit-side .unit-side-card')].map(c => +c.dataset.id),
            compact: document.querySelectorAll('#unit-list > li.unit.compact').length, n: document.querySelectorAll('#unit-list > li.unit').length,
            inline: document.querySelectorAll('#unit-list .panel').length })""")
        check("a tap opens the unit in the side pane, as before", 7 in r["side"] and r["inline"] == 0, r)
        check("…and the other list cards stay compact", open_ids(page) == [7] and r["compact"] == r["n"] - 1, (open_ids(page), r))
        page.locator(card(7) + " .up-button").click()
        check("the open card's stepper works there too", page.evaluate("models.find(m => m.id === 7).stage") == 4)

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
