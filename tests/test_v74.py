"""v74 tests for Minifolio (chunk 5.1: faster stage jump and one consistent arrow).

What changed:
 Each unit card has a stage button (the arrows icon) beside the big up arrow; picking a stage there moves the whole unit straight to
 it. The up arrow now does the same on every unit: it moves the whole unit up one stage (on a unit tracked model by model, every
 model moves up one). Both have an Undo.

Checks:
1. A one-model unit goes from the first stage to Parade ready in one pick; Undo puts it back, diary included.
2. The up arrow on a batch unit moves it up one stage.
3. The up arrow on a model-by-model unit moves every model up one (a model already at the top stays); Undo restores it exactly.
4. When every model is at the top stage the arrow is switched off.
5. Picking a stage on a model-by-model unit moves all its models.
6. 390 px and 360 px, dark and light: no sideways scroll, both buttons 44 px or more.
7. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

SOLO = {"id": 1, "name": "Solo hero", "hobby": "40K", "faction": "Orks", "stage": 0, "count": 1, "added": "2026-10-01", "log": [["2026-10-01", 0]]}
BATCH = {"id": 2, "name": "Batch squad", "hobby": "40K", "faction": "Orks", "stage": 2, "count": 5, "added": "2026-10-01", "log": [["2026-10-01", 2]]}
EACH = {"id": 3, "name": "Each squad", "hobby": "40K", "faction": "Orks", "stage": 1, "count": 3, "each": True, "stages": [1, 4, 7],
        "added": "2026-10-01", "log": [["2026-10-01", 1]]}

def unit(page, uid):
    return page.evaluate("(i) => { const m = models.find(x => x.id === i); return { stage: m.stage, stages: m.stages, log: m.log }; }", uid)

def card(page, uid):
    return page.locator(f"li.unit[data-id='{uid}']")

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
            load(page, units=units or [SOLO, BATCH, EACH], **kw)
            page.click('nav button[data-tab="units"]')
            page.wait_for_timeout(200)

        print("\n--- 1. Jump straight to a stage ---")
        start()
        last = page.evaluate("STAGES.length - 1")
        before = unit(page, 1)
        card(page, 1).locator(".stage-jump-menu").select_option(str(last))
        page.wait_for_timeout(250)
        check("one pick takes a one-model unit to the last stage", unit(page, 1)["stage"] == last, unit(page, 1))
        check("the line says where it went", "Parade ready" in page.evaluate("() => document.getElementById('toast-text').textContent"))
        undo(page)
        check("Undo puts stage and diary back exactly", unit(page, 1) == before, unit(page, 1))

        print("\n--- 2. The arrow on a batch unit ---")
        card(page, 2).locator(".up-button").click()
        page.wait_for_timeout(250)
        check("the batch unit moves up one stage", unit(page, 2)["stage"] == 3, unit(page, 2))

        print("\n--- 3. The arrow on a model-by-model unit ---")
        before = unit(page, 3)
        card(page, 3).locator(".up-button").click()
        page.wait_for_timeout(250)
        now = unit(page, 3)
        check("every model moves up one, the one at the top stays", now["stages"] == [2, 5, 7] and now["stage"] == 2, now)
        undo(page)
        check("Undo restores every model and the diary", unit(page, 3) == before, unit(page, 3))

        print("\n--- 4. Everything at the top ---")
        start(units=[{**EACH, "stages": [7, 7, 7], "stage": 7}])
        check("the arrow is switched off", card(page, 3).locator(".up-button").is_disabled())

        print("\n--- 5. Jump on a model-by-model unit ---")
        start()
        card(page, 3).locator(".stage-jump-menu").select_option("3")
        page.wait_for_timeout(250)
        check("all its models go to that stage", unit(page, 3)["stages"] == [3, 3, 3], unit(page, 3))

        print("\n--- 6. Phone sizes, dark and light ---")
        for scheme in ["dark", "light"]:
            for w in [390, 360]:
                page.set_viewport_size({"width": w, "height": 780})
                start(settings={"appearance": scheme})
                sizes = page.evaluate("""() => [...document.querySelectorAll('li.unit .stage-jump, li.unit .up-button')]
                    .map(e => { const r = e.getBoundingClientRect(); return [r.width, r.height]; })""")
                check(f"{w} px {scheme}: no sideways scroll, both buttons 44 px or more",
                      no_sideways(page) and sizes and all(a >= 44 and b >= 44 for a, b in sizes), sizes)

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
