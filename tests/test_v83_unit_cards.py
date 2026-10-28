"""v83 tests for Minifolio (chunk M1: unit card with a stage stepper).

New behaviour only:
1. The card header shows the name, "N models" and a Details button; under it a stepper has a back button, the stage with one bar per stage, and an up button.
2. Up and Back move the unit one stage, say where to ("Up to ...", "Back to ..."), and have Undo. Back is off at the first stage, up at the last.
3. A unit tracked model by model: Back moves every model back one, with Undo.
4. The old stage button (arrows icon) and the "Back a stage" button at the bottom of the details are gone.
5. Details opens and says Hide; it holds Jump to stage first, then a Paints row (6 swatches at most, "Paints · N") that opens the full grid,
   and the per-model rows still work inside it. A unit with no paints has no Paints row.
6. 900, 1280 and 1920 px: Details opens the side pane with the same contents.
7. 390 and 360 px, dark and light: no sideways scroll, tap targets 44 px or more.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

PAINTS = [{"id": i, "brand": "Citadel", "name": f"Paint {i}", "colour": "#%02x%02x%02x" % (25 * i, 90, 220 - 20 * i)} for i in range(1, 9)]
RECIPE = {"id": 1, "name": "Ork green", "steps": [{"title": "Step", "paints": [{"paint": i, "mix": 100}]} for i in range(1, 9)]}
BATCH = {"id": 1, "name": "Batch squad", "hobby": "40K", "faction": "Orks", "stage": 2, "count": 5, "recipes": [1], "added": "2026-10-01", "log": [["2026-10-01", 2]]}
FIRST = {"id": 2, "name": "First stage", "hobby": "40K", "stage": 0, "count": 1, "added": "2026-10-01", "log": [["2026-10-01", 0]]}
LAST = {"id": 3, "name": "Last stage", "hobby": "40K", "stage": 7, "count": 1, "added": "2026-10-01", "log": [["2026-10-01", 7]]}
EACH = {"id": 4, "name": "Each squad", "hobby": "40K", "stage": 1, "count": 3, "each": True, "stages": [1, 4, 7], "added": "2026-10-01", "log": [["2026-10-01", 1]]}
UNITS = [BATCH, FIRST, LAST, EACH]

def card(page, uid):
    return page.locator(f"li.unit[data-id='{uid}']")

def saved(page, uid):
    return page.evaluate("(i) => { const m = models.find(x => x.id === i); return { stage: m.stage, stages: m.stages, log: m.log }; }", uid)

def undo(page):
    page.click("#toast-undo")
    page.wait_for_timeout(250)

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        def start(units=None, **kw):
            load(page, units=units or UNITS, paints=PAINTS, recipes=[RECIPE], **kw)
            page.click('nav button[data-tab="units"]')
            page.wait_for_timeout(250)

        print("\n--- 1. The card ---")
        start()
        STAGES = page.evaluate("STAGES")
        c = card(page, 1)
        check("header shows the name, the model count and a Details button",
              "Batch squad" in c.inner_text() and "5 models" in c.inner_text() and c.locator(".details-toggle").inner_text().strip() == "Details")
        check("the stepper has a back button, the stage name and one bar per stage, and an up button",
              c.locator(".stepper .step-back").count() == 1 and c.locator(".stepper .up-button").count() == 1
              and c.locator(".stepper .stage").inner_text().strip() == STAGES[2] and c.locator(".stepper .pip").count() == len(STAGES))
        check("the buttons say where they go",
              c.locator(".step-back").get_attribute("aria-label") == f"Back to {STAGES[1]}" and c.locator(".up-button").get_attribute("aria-label") == f"Up to {STAGES[3]}")
        check("the old stage button and the old Back a stage button are gone",
              page.locator(".stage-jump").count() == 0 and "⇅" not in page.inner_text("#view-units") and page.locator("button:has-text('Back a stage')").count() == 0)

        print("\n--- 2. Up and Back ---")
        before = saved(page, 1)
        c.locator(".up-button").click()
        page.wait_for_timeout(250)
        check("up moves the unit up one stage", saved(page, 1)["stage"] == 3, saved(page, 1))
        undo(page)
        check("Undo puts stage and diary back", saved(page, 1) == before, saved(page, 1))
        c.locator(".step-back").click()
        page.wait_for_timeout(250)
        check("back moves the unit down one stage", saved(page, 1)["stage"] == 1, saved(page, 1))
        undo(page)
        check("Undo puts it back again", saved(page, 1) == before, saved(page, 1))
        check("back is off at the first stage", card(page, 2).locator(".step-back").is_disabled() and not card(page, 2).locator(".up-button").is_disabled())
        check("up is off at the last stage", card(page, 3).locator(".up-button").is_disabled() and not card(page, 3).locator(".step-back").is_disabled())

        print("\n--- 3. Tracked model by model ---")
        before = saved(page, 4)
        card(page, 4).locator(".step-back").click()
        page.wait_for_timeout(250)
        check("back moves every model down one, the one at the start stays", saved(page, 4)["stages"] == [0, 3, 6], saved(page, 4))
        undo(page)
        check("Undo restores every model and the diary", saved(page, 4) == before, saved(page, 4))

        print("\n--- 4. Details ---")
        c = card(page, 1)
        c.locator(".details-toggle").click()
        page.wait_for_timeout(250)
        check("Details turns into Hide and the panel opens",
              c.locator(".details-toggle").inner_text().strip() == "Hide" and c.locator(".panel").count() == 1)
        order = page.evaluate("""() => [...document.querySelectorAll('li.unit[data-id="1"] .panel > *')].map(e =>
            e.querySelector && e.querySelector('select.jump-stage') ? 'jump' : e.classList.contains('unit-paints') ? 'paints' : e.classList.contains('edit-details') ? 'edit' : '')
            .filter(Boolean)""")
        check("Jump to stage comes first, then Paints, then Edit details", order == ["jump", "paints", "edit"], order)
        check("the stage menu is labelled Jump to stage", "Jump to stage" in c.locator(".panel > label").first.inner_text())
        row = c.locator(".paints-row")
        check("the Paints row shows 6 swatches at most and the count", row.inner_text().strip() == "Paints · 8" and row.locator(".swatch").count() == 6, row.inner_text())
        check("the full grid is closed to start with", c.locator(".paints-grid").count() == 0 and row.get_attribute("aria-expanded") == "false")
        row.click()
        page.wait_for_timeout(250)
        check("tapping the row opens the full grid of every paint", card(page, 1).locator(".paints-grid .swatch").count() == 8)
        card(page, 1).locator(".details-toggle").click()
        page.wait_for_timeout(250)
        check("Hide shuts the panel", card(page, 1).locator(".panel").count() == 0)

        card(page, 2).locator(".details-toggle").click()
        page.wait_for_timeout(250)
        check("a unit with no paints has no Paints row", card(page, 2).locator(".panel").count() == 1 and card(page, 2).locator(".paints-row").count() == 0)

        card(page, 4).locator(".details-toggle").click()
        page.wait_for_timeout(250)
        card(page, 4).locator(".each-list .each-up").first.click()
        page.wait_for_timeout(250)
        check("the per-model rows still work inside Details", saved(page, 4)["stages"][0] == 2, saved(page, 4))

        print("\n--- 5. Wide screens: the side pane ---")
        for width in (900, 1280, 1920):
            page.set_viewport_size({"width": width, "height": 900})
            start()
            card(page, 1).locator(".details-toggle").click()
            page.wait_for_timeout(300)
            side = page.locator("#unit-side")
            check(f"{width} px: Details opens the side pane with Jump to stage and Paints",
                  side.is_visible() and side.locator("select.jump-stage").count() == 1 and "Paints · 8" in side.inner_text(), side.inner_text()[:80])
            check(f"{width} px: the card keeps its stepper and no sideways scroll",
                  card(page, 1).locator(".stepper").is_visible() and no_sideways(page))

        print("\n--- 6. Phones, dark and light ---")
        for scheme in ("dark", "light"):
            for width in (390, 360):
                page.set_viewport_size({"width": width, "height": 800})
                start(settings={"appearance": scheme})
                card(page, 1).locator(".details-toggle").click()
                page.wait_for_timeout(250)
                card(page, 1).locator(".paints-row").click()
                page.wait_for_timeout(250)
                sizes = page.evaluate("""() => [...document.querySelectorAll('li.unit .step-back, li.unit .up-button, li.unit .details-toggle, li.unit .paints-row')]
                    .map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; })""")
                check(f"{width} px {scheme}: no sideways scroll, back, up, Details and Paints are 44 px or more",
                      no_sideways(page) and len(sizes) >= 12 and all(a >= 44 and b >= 44 for a, b in sizes), sizes)

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
