"""v83 polish tests for Minifolio (chunk 5.4a: A6, A8, A9 dates, C5, C6).

What changed:
 A9: a long history graph labels its dates "Mar 2025" (not "Mar 25", which reads as 25 March); a middle date that would repeat or crowd another is left out.
 C5: the Add unit form starts with the last game and faction you used, even after closing the app.
 C6: Settings > Your data says "Works offline." once the offline copy is in place.
 A6 and A8 were checked and found already fine: the Settings count matches the Units tab, and the restore question is a box over the screen.

Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def unit(i, count, added=None):
    u = {"id": i, "name": f"Unit {i}", "hobby": "40K", "faction": "Orks", "stage": 1, "count": count}
    if added: u["added"] = added
    return u

def sideways(page):
    return page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth + 1")

def tick_labels(page):
    return page.evaluate("""() => [...document.querySelectorAll('#history-chart svg text')]
        .filter(t => t.getAttribute('y') && Number(t.getAttribute('y')) > 190 && !/^\\d+$/.test(t.textContent)).map(t => t.textContent)""")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844})   # service worker allowed, for C6
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- A6: Settings count matches the Units tab ---")
        t.load(page, units=[unit(i, 10) for i in range(1, 7)])
        page.click('nav button[data-tab="settings"]')
        summary = page.evaluate("() => document.getElementById('data-summary').textContent")
        check("Settings says 6 units, 60 models", summary.startswith("6 units, 60 models"), summary)

        print("\n--- A8: the restore question is a box over the screen, not at the page bottom ---")
        backup = {"app": "Shades of Grey", "version": 6, "models": [unit(1, 2)]}
        page.set_input_files("#restore-file", files=[{"name": "b.json", "mimeType": "application/json", "buffer": json.dumps(backup).encode()}])
        page.wait_for_selector("#dialog", state="visible")
        box = page.evaluate("() => document.getElementById('dialog').getBoundingClientRect().toJSON()")
        check("question is fully on screen", box["top"] >= 0 and box["bottom"] <= 844, box)
        page.click("#dialog-no")

        print("\n--- C6: Works offline ---")
        page.evaluate("() => navigator.serviceWorker.ready")
        page.reload(); page.wait_for_function("() => !!document.getElementById('toggle-add')")
        page.click('nav button[data-tab="settings"]')
        page.wait_for_function("() => document.getElementById('offline-note').textContent === 'Works offline.'", timeout=8000)
        check("offline note shown once the offline copy is ready", True)
        for width in (390, 360):
            page.set_viewport_size({"width": width, "height": 844})
            check(f"{width} px: no sideways scroll on Settings", not sideways(page))

        print("\n--- C5: Add unit remembers game and faction ---")
        page.click('nav button[data-tab="units"]')
        page.click("#toggle-add")
        check("form starts empty when nothing is remembered", page.input_value("#hobby-input") == "" and page.input_value("#faction-input") == "")
        page.fill("#name-input", "Hormagaunts"); page.fill("#hobby-input", "Sci-fi"); page.fill("#faction-input", "Tyranids")
        page.click("#add-form button[type=submit]")
        page.wait_for_timeout(300)
        page.reload(); page.wait_for_function("() => !!document.getElementById('toggle-add')")
        page.click('nav button[data-tab="units"]')
        page.click("#toggle-add")
        check("after a reload the game is filled in", page.input_value("#hobby-input") == "Sci-fi", page.input_value("#hobby-input"))
        check("after a reload the faction is filled in", page.input_value("#faction-input") == "Tyranids", page.input_value("#faction-input"))
        check("name box is still empty", page.input_value("#name-input") == "")
        for width in (390, 360):
            page.set_viewport_size({"width": width, "height": 844})
            check(f"{width} px: no sideways scroll on Units with the form open", not sideways(page))
        ctx.close()

        print("\n--- A9: history graph dates ---")
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        for scheme in ("dark", "light"):
            page.emulate_media(color_scheme=scheme)
            t.load(page, units=[unit(1, 5, "2024-01-10"), unit(2, 5, "2025-05-20")])
            page.click('nav button[data-tab="dashboard"]'); page.wait_for_timeout(300)
            labels = tick_labels(page)
            check(f"{scheme}: long range uses month and four-digit year", labels and re.match(r"^[A-Z][a-z]{2} 20\d\d$", labels[0]) and labels[-1] == "Today", labels)
            check(f"{scheme}: no sideways scroll", not sideways(page))
        import datetime
        recent = (datetime.date.today() - datetime.timedelta(days=2)).isoformat()
        t.load(page, units=[unit(1, 5, recent)])
        page.click('nav button[data-tab="dashboard"]'); page.wait_for_timeout(300)
        labels = tick_labels(page)
        check("a two day graph has no repeated date labels", len(labels) == len(set(labels)), labels)
        check("no page errors", not errors, errors)
        browser.close()
    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)

main()
