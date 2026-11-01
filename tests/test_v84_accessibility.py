"""v84 tests for Minifolio (wave B polish: accessible names and "1 model").

New behaviour only:
1. "1 model" (not "1 models") in the Units summary line, the filtered line, the Dashboard line and the Settings summary.
2. A unit tracked model by model with mixed stages is announced with the mix in select mode, not just the furthest-behind stage.
3. "Edit details" is exposed as a button that says whether it is open.
4. The unit card has names on everything: the checkboxes in Edit details, the Delete button says which unit, buttons and menus all have a name.
5. 390 and 360 px, dark and light: no sideways scroll, the buttons just touched are 44 px or more.
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

SOLO = {"id": 1, "name": "Solo hero", "hobby": "40K", "faction": "Orks", "stage": 2, "count": 1, "added": "2026-10-01", "log": [["2026-10-01", 2]]}
MIXED = {"id": 2, "name": "Mixed squad", "hobby": "40K", "faction": "Orks", "stage": 0, "count": 10, "each": True,
         "stages": [4] * 4 + [0] * 6, "added": "2026-10-01", "log": [["2026-10-01", 0]]}
BATCH = {"id": 3, "name": "Batch squad", "hobby": "40K", "stage": 1, "count": 3, "added": "2026-10-01", "log": [["2026-10-01", 1]]}

def card(page, uid):
    return page.locator(f"li.unit[data-id='{uid}']")

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        def start(units, **kw):
            load(page, units=units, **kw)
            page.click('nav button[data-tab="units"]')
            page.wait_for_timeout(250)

        print("\n--- 1. 1 model ---")
        start([SOLO])
        check("the Units line says 1 model", "1 unit, 1 model" in page.inner_text("#view-units") and "1 models" not in page.inner_text("#view-units"),   # A2: one unit now reads "1 unit" (the plural helper), it was "1 units"
              page.inner_text("#view-units")[:200])
        page.evaluate("() => { filters.hobby = '40K'; render(); }")
        check("the filtered line says 1 model", "(1 model)" in page.inner_text("#view-units"), page.inner_text("#view-units")[:200])
        page.evaluate("() => { filters.hobby = ''; render(); }")
        page.click('nav button[data-tab="dashboard"]')
        page.wait_for_timeout(250)
        dash = page.inner_text("#view-dashboard")
        check("the Dashboard line says 0 of 1 model done", "of 1 model done" in dash and "1 models" not in dash, dash[:300])
        page.click("#settings-button") if page.locator("#settings-button").count() else page.evaluate("() => showTab('settings')")
        page.wait_for_timeout(250)
        check("Settings does not say 1 models", "1 models" not in page.inner_text("body"))

        print("\n--- 2. a mixed unit keeps its mix ---")
        start([SOLO, MIXED, BATCH])
        page.evaluate("() => { selectMode = true; render(); }")
        page.wait_for_timeout(200)
        label = card(page, 2).locator(".info").get_attribute("aria-label")
        check("select mode names both stages of the mixed unit", "4 " in label and "6 " in label and "Mixed squad" in label, label)
        check("a one-stage unit still names its stage", page.evaluate("STAGES[2]") in card(page, 1).locator(".info").get_attribute("aria-label"))
        page.evaluate("() => { selectMode = false; render(); }")
        page.wait_for_timeout(200)

        print("\n--- 3 and 4. Edit details and the names on the card ---")
        for uid in (1, 2):
            card(page, uid).locator(".details-toggle").click()
            page.wait_for_timeout(200)
        summ = card(page, 2).locator("summary", has_text="Edit details")
        check("Edit details is a button", summ.get_attribute("role") == "button")
        check("and says it is shut", summ.get_attribute("aria-expanded") == "false")
        summ.click()
        page.wait_for_timeout(200)
        check("and then open", summ.get_attribute("aria-expanded") == "true")
        check("the Edit details tick box is named by its label",
              card(page, 2).get_by_role("checkbox", name="Repaint project").count() == 1)
        check("Delete says which unit", card(page, 2).get_by_role("button", name="Delete Mixed squad").count() == 1)
        unnamed = page.evaluate("""() => [...document.querySelectorAll('li.unit button, li.unit select, li.unit input:not(.hidden), li.unit textarea, li.unit summary')]
            .filter(e => !(e.getAttribute('aria-label') || e.textContent.trim() || (e.labels && e.labels.length) || e.closest('label'))).length""")
        check("nothing on the open cards is without a name", unnamed == 0, unnamed)

        print("\n--- 5. Phones, dark and light ---")
        for scheme in ("dark", "light"):
            for width in (390, 360):
                page.set_viewport_size({"width": width, "height": 800})
                start([SOLO, MIXED], settings={"appearance": scheme})
                card(page, 2).locator(".details-toggle").click()
                page.wait_for_timeout(200)
                card(page, 2).locator("summary", has_text="Edit details").click()
                page.wait_for_timeout(200)
                sizes = page.evaluate("""() => [...document.querySelectorAll('li.unit .details-toggle, li.unit .edit-details > summary, li.unit .danger-button')]
                    .map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; })""")
                check(f"{width} px {scheme}: no sideways scroll, Details, Edit details and Delete are 44 px or more",
                      no_sideways(page) and len(sizes) >= 3 and all(a >= 44 and b >= 44 for a, b in sizes), sizes)

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
