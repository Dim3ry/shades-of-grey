"""A2 tests for Minifolio (behaviour fixes from the 31 Oct review). New behaviour only.

1. One unit reads "1 unit" (counter line on Models and in the Dashboard summary).
2. A message past its time goes when the page wakes up or comes back to the front (a frozen timer can't leave it up).
3. A kept unfinished unit: tapping Add unit shows no second box; the top card is the only offer.
4. Unit name, game and faction boxes stop at 80 characters; longer saved values still load and show unchanged.
5. Every Undo message lasts 10 seconds from one shared setting (UNDO_SECONDS); it sits above the menu and is readable at 390, 360, 320 px.
6. The start circle's four segments arrive Dashboard, Models, Tools, Painting (clockwise); where they sit is unchanged.
7. The Minifolio title takes every section to a clean start page (nothing from the old screen left behind).
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import tap_tab, quiet, wait_settled, app_ready, leave_launch

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def unit(i, **kw):
    u = {"id": i, "name": "Unit %d" % i, "count": 5, "stage": 1, "faction": "Orks", "hobby": "40K", "paints": [], "photos": []}
    u.update(kw)
    return u

TOAST = """() => { const e = document.getElementById('toast');
  return { shown: !e.classList.contains('hidden'), life: e.style.getPropertyValue('--toast-life'),
           undo: !document.getElementById('toast-undo').classList.contains('hidden') }; }"""

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. One unit ---")
        t.load(page, units=[unit(1)])
        tap_tab(page, "units")
        quiet(page)
        check("Models says 1 unit, 5 models", "1 unit, 5 models" in page.inner_text("#view-units") and "1 units" not in page.inner_text("#view-units"),
              page.inner_text("#filter-note") if page.locator("#filter-note").count() else "")
        t.load(page, units=[unit(1), unit(2)])
        tap_tab(page, "units")
        quiet(page)
        check("two units still read 2 units", "2 units, 10 models" in page.inner_text("#view-units"))

        print("\n--- 2. A message past its time goes ---")
        t.load(page)
        page.evaluate("() => showToast('Added 1 paint to your shopping list', () => {})")
        page.evaluate("() => document.dispatchEvent(new Event('visibilitychange'))")
        check("waking up inside its time leaves the message up", page.evaluate(TOAST)["shown"])
        page.evaluate("() => { toastUntil = Date.now() - 1; }")   # as if the phone froze the page past the message's time
        page.evaluate("() => document.dispatchEvent(new Event('visibilitychange'))")
        check("waking up past its time takes it away", not page.evaluate(TOAST)["shown"])
        page.evaluate("() => showToast('Again', () => {})")
        page.evaluate("() => { toastUntil = Date.now() - 1; }")
        page.evaluate("() => window.dispatchEvent(new Event('pageshow'))")
        check("coming back to the front (pageshow) does the same", not page.evaluate(TOAST)["shown"])

        print("\n--- 3. Kept unfinished unit: one offer ---")
        t.load(page)
        tap_tab(page, "units")
        quiet(page)
        page.click("#toggle-add")
        page.fill("#name-input", "Halfway")
        page.wait_for_timeout(1500)   # the draft is saved a moment after typing
        page.reload()
        app_ready(page)
        leave_launch(page)
        tap_tab(page, "units")
        quiet(page)
        check("the top card is showing", page.locator("#draft-card-unit").is_visible() and "We kept your unfinished unit" in page.inner_text("#draft-card-unit"))
        check("no second box at the bottom", page.locator("#dialog-backdrop").is_hidden())
        page.click("#toggle-add")
        page.wait_for_timeout(300)
        check("tapping Add unit adds no box, the form stays shut", page.locator("#dialog-backdrop").is_hidden() and not page.is_visible("#add-form"))

        print("\n--- 4. Length limits ---")
        t.load(page)
        tap_tab(page, "units")
        quiet(page)
        page.click("#toggle-add")
        check("the three boxes carry maxlength 80", page.evaluate("() => ['name-input', 'hobby-input', 'faction-input'].map(i => document.getElementById(i).maxLength)") == [80, 80, 80])
        page.fill("#name-input", "")
        page.type("#name-input", "N" * 600, delay=0)
        check("typing 600 characters keeps 80", len(page.input_value("#name-input")) == 80)
        long_name = "L" * 200
        t.load(page, units=[unit(1, name=long_name, faction="F" * 150, hobby="H" * 120)])
        tap_tab(page, "units")
        quiet(page)
        saved = page.evaluate("() => models[0]")
        check("a longer name, game and faction saved earlier load unchanged", saved["name"] == long_name and len(saved["faction"]) == 150 and len(saved["hobby"]) == 120, saved["name"][:20])
        check("the card still shows the long name", long_name in page.inner_text("#view-units"))

        print("\n--- 5. Undo messages ---")
        t.load(page, units=[unit(1), unit(2)])
        tap_tab(page, "units")
        quiet(page)
        check("one named setting, 10 seconds", page.evaluate("UNDO_SECONDS") == 10)
        page.evaluate("() => showToast('Anything', () => {})")
        check("a message with Undo lasts the shared time", page.evaluate(TOAST)["life"] == "10s")
        page.evaluate("() => showToast('Plain note')")
        check("a plain message keeps its short time", page.evaluate(TOAST)["life"] == "4s")
        sample = {
            "stage move": "() => changeStage(models[1].id, 1)",
            "delete recipe": "() => deleteRecipeNow(book.recipes[0].id)",
            "shopping list": "() => addSchemePaintsToShoppingList([{ brand: 'Citadel', name: 'Retributor Armour' }], 'x')",
        }
        page.evaluate("() => { book.recipes.push({ id: 'r9', name: 'Rec', part: 'Whole model', steps: [] }); }")
        for name, js in sample.items():
            page.evaluate(js)
            got = page.evaluate(TOAST)
            check(f"{name}: shown with Undo for 10 s", got["shown"] and got["undo"] and got["life"] == "10s", got)
        page.evaluate("() => deleteModelNow(models[0].id)")
        check("delete unit: 10 s", page.evaluate(TOAST)["life"] == "10s")
        page.wait_for_timeout(5000)   # longer than the old 4 s and 8 s limits; the older v24 and v44 tests wait out the full 10 s
        check("delete unit: still offered at 5 s", page.evaluate(TOAST)["shown"])
        for w, h in ((390, 844), (360, 640), (320, 568)):
            page.set_viewport_size({"width": w, "height": h})
            page.evaluate("() => showToast('Deleted a unit with a rather long name for a small phone, Intercessor Veterans', () => {})")
            page.wait_for_timeout(450)
            r = page.evaluate("""() => { const b = document.getElementById('toast').getBoundingClientRect(), u = document.getElementById('toast-undo').getBoundingClientRect(),
                bar = document.querySelector('.tabs').getBoundingClientRect(), s = document.getElementById('toast-text');
                return { bottom: b.bottom, barTop: bar.top, left: b.left, right: b.right, undoH: u.height, undoIn: u.left >= b.left && u.right <= b.right,
                         text: s.textContent, noCountdown: !/\\d+\\s*s\\b/.test(document.getElementById('toast').textContent), scrollX: document.documentElement.scrollWidth > innerWidth }; }""")
            check(f"{w}x{h}: above the menu, inside the screen, Undo 44 px and inside, no countdown, no sideways scroll",
                  r["bottom"] <= r["barTop"] + 0.5 and r["left"] >= 0 and r["right"] <= w and r["undoH"] >= 44 and r["undoIn"] and r["noCountdown"] and not r["scrollX"], r)
        page.set_viewport_size({"width": 390, "height": 844})

        print("\n--- 6. Start circle arrival order ---")
        t.load(page, launch=True)
        page.reload()
        order = page.evaluate("""() => new Promise(done => { const seen = [], t0 = performance.now();
            const f = () => { for (const b of document.querySelectorAll('.arc [data-tab]'))
                if (!b.classList.contains('ring-hold') && !seen.includes(b.dataset.tab) && document.querySelector('.mo-load')) seen.push(b.dataset.tab);
              if (!document.querySelector('.mo-load') && performance.now() - t0 > 300 || performance.now() - t0 > 5000) done(seen); else requestAnimationFrame(f); }; f(); })""")
        check("they arrive Dashboard, Models, Tools, Painting", order == ["dashboard", "units", "guides", "recipes"], order)
        wait_settled(page)
        page.wait_for_function("() => !document.querySelector('.mo-load')")
        pos = page.evaluate("""() => Object.fromEntries([...document.querySelectorAll('.arc [data-tab]')].map(b => { const r = b.getBoundingClientRect();
            return [b.dataset.tab, [r.left + r.width / 2, r.top + r.height / 2]]; }))""")
        check("they still sit Dashboard top left, Models top right, Painting bottom left, Tools bottom right",
              pos["dashboard"][0] < pos["units"][0] and pos["dashboard"][1] < pos["recipes"][1] and pos["recipes"][0] < pos["guides"][0]
              and abs(pos["dashboard"][1] - pos["units"][1]) < 5 and abs(pos["recipes"][1] - pos["guides"][1]) < 5, pos)

        print("\n--- 7. Title button: clean start page from every section ---")
        CLEAN = """() => ({ launching: document.body.classList.contains('launching'),
            content: [...document.querySelectorAll('main > *')].filter(e => !e.classList.contains('app-bar') && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().height > 0).map(e => e.id || e.tagName),
            layers: [...document.querySelectorAll('.mo-out, .mo-box, .mo-ring, .mo-ghost, .mo-tr')].length })"""
        for scheme, (w, h) in (("dark", (390, 844)), ("light", (360, 640))):
            page.set_viewport_size({"width": w, "height": h})
            t.load(page, units=[unit(i, stage=i % 8) for i in range(1, 13)], settings={"appearance": scheme})
            for tab in (("dashboard", "units", "recipes", "guides") if scheme == "dark" else ("dashboard", "guides")):
                tap_tab(page, tab)
                wait_settled(page)
                page.click("#home-button")
                page.wait_for_function("() => document.body.classList.contains('launching') && !document.querySelector('.mo-tr')", timeout=8000)
                wait_settled(page)
                r = page.evaluate(CLEAN)
                check(f"{w}x{h} {scheme}: from {tab} the start page is clean", r["launching"] and r["content"] in ([], ["start-line"]) and r["layers"] == 0, r)
                leave_launch(page)

        check("no page errors", not errors, errors)
        browser.close()
    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
