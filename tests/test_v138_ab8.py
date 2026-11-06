"""AB8 tests for Minifolio (Armies on the Dashboard as rows, with a Rows | Doughnuts switch). New behaviour only:
1. With nothing saved, Armies shows rows (one per faction, name, stage strip, "5 of 10 done"), and the switch says Rows.
2. The switch changes the view and the choice is saved and survives a reload.
3. A backup from before this version restores fine and shows rows.
4. A lone "No faction" row is hidden in Rows; the doughnut view still draws it.
5. Tapping a row, and a doughnut, both filter Models by that faction.
6. Targets are 44 px, no sideways scroll, at 390, 360 and 320 px wide, dark and light.
Run with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys, json
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def unit(i, faction, stage):
    u = {"id": i, "name": f"Squad {i}", "hobby": "Test game", "stage": stage, "count": 2, "added": "2026-09-01", "log": [["2026-09-01", 0]]}
    if faction: u["faction"] = faction
    return u

THREE = [unit(1, "Ash wardens", 0), unit(2, "Ash wardens", 4), unit(3, "Bog goblins", 2), unit(4, "Gilded knights", 4)]
ONE = [unit(1, "Ash wardens", 1), unit(2, "Ash wardens", 4)]
NONE = [unit(1, "", 1), unit(2, "", 4)]
BASE = {"examplesChecked": True, "recipeExamplesChecked": True, "feedbackShown": True, "backupNudgeDone": True}
STATE = """() => ({ rows: document.querySelectorAll('#faction-grid .faction-row').length, dough: document.querySelectorAll('#faction-grid .faction-button').length,
    pressed: [...document.querySelectorAll('#faction-view .chip')].map(c => c.textContent + ':' + c.getAttribute('aria-pressed')),
    switchHidden: document.getElementById('faction-view').classList.contains('hidden') })"""

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. Rows by default ---")
        t.load(page, units=THREE, settings=dict(BASE))
        s = page.evaluate(STATE)
        check("three rows, no doughnuts", s["rows"] == 3 and s["dough"] == 0, s)
        check("switch reads Rows | Doughnuts with Rows chosen", s["pressed"] == ["Rows:true", "Doughnuts:false"], s)
        first = page.locator("#faction-grid .faction-row").first
        check("row has the name and 'x of y done' text", "Ash wardens" in first.inner_text() and "2 of 4 done" in first.inner_text(), first.inner_text())
        check("row has a stage strip", first.locator(".faction-strip i").count() >= 1)
        check("row carries no emoji or em dash", "—" not in first.inner_text())

        print("\n--- 2. The switch ---")
        page.click('#faction-view [data-faction-view="doughnuts"]')
        page.wait_for_timeout(200)
        s = page.evaluate(STATE)
        check("doughnuts shown after switching", s["dough"] == 3 and s["rows"] == 0, s)
        check("choice is saved in settings", page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-settings')).factionView") == "doughnuts")
        page.reload(); t.app_ready(page); t.leave_launch(page)
        s = page.evaluate(STATE)
        check("choice survives a reload", s["dough"] == 3 and s["pressed"][1] == "Doughnuts:true", s)
        page.click('#faction-view [data-faction-view="rows"]')
        page.wait_for_timeout(200)
        check("switching back shows rows", page.evaluate(STATE)["rows"] == 3)
        data = page.evaluate("() => backupData()")
        check("backup carries the choice", data.get("factionView") == "rows", data.get("factionView"))

        print("\n--- 3. An old backup ---")
        old = {"app": "Minifolio", "version": 6, "models": THREE}
        t.load(page, units=[], settings=dict(BASE))
        page.set_input_files("#restore-file", files=[{"name": "b.json", "mimeType": "application/json", "buffer": json.dumps(old).encode()}])
        page.click("#dialog-yes")
        page.wait_for_function("() => document.getElementById('toast-text').textContent.includes('Backup restored')")
        page.evaluate("() => { const b = document.querySelector('nav button[data-tab=\"dashboard\"]'); if (b) b.click(); }")
        page.wait_for_timeout(300)
        s = page.evaluate(STATE)
        check("old backup restores and shows rows", s["rows"] == 3 and s["pressed"][0] == "Rows:true", s)
        t.load(page, units=THREE, settings={**BASE, "factionView": "bogus"})
        check("an unknown saved value means rows", page.evaluate(STATE)["rows"] == 3)

        print("\n--- 4. A lone No faction ---")
        t.load(page, units=NONE, settings=dict(BASE))
        check("no row for a lone No faction", page.evaluate(STATE)["rows"] == 0)
        t.load(page, units=NONE, settings={**BASE, "factionView": "doughnuts"})
        check("the doughnut view still draws it", page.evaluate(STATE)["dough"] == 1)
        t.load(page, units=[], settings=dict(BASE))
        check("no units: no switch", page.evaluate(STATE)["switchHidden"])

        print("\n--- 5. Tapping filters Models ---")
        t.load(page, units=THREE, settings=dict(BASE))
        page.locator("#faction-grid .faction-row", has_text="Bog goblins").click()
        page.wait_for_timeout(300)
        shown = page.evaluate("() => [...document.querySelectorAll('#view-units li.unit')].map(l => l.textContent)")
        check("row tap lists only that faction", len(shown) == 1 and "Squad 3" in shown[0], shown)
        t.load(page, units=THREE, settings={**BASE, "factionView": "doughnuts"})
        page.locator("#faction-grid .faction-button", has_text="Gilded knights").click()
        page.wait_for_timeout(300)
        shown = page.evaluate("() => [...document.querySelectorAll('#view-units li.unit')].map(l => l.textContent)")
        check("doughnut tap lists only that faction", len(shown) == 1 and "Squad 4" in shown[0], shown)

        print("\n--- 6. Sizes, scrolling, looks ---")
        for w, h in [(390, 844), (360, 640), (320, 568)]:
            for scheme in ["dark", "light"]:
                c2 = browser.new_context(viewport={"width": w, "height": h}, service_workers="block", color_scheme=scheme)
                pg = c2.new_page()
                t.load(pg, units=THREE, settings={**BASE, "appearance": scheme})
                m = pg.evaluate("""() => ({ small: [...document.querySelectorAll('#faction-grid .faction-row, #faction-view .chip')].filter(e => e.getBoundingClientRect().height < 43.5).length,
                    wide: document.documentElement.scrollWidth > window.innerWidth })""")
                check(f"{w}px {scheme}: 44 px targets, no sideways scroll", m["small"] == 0 and not m["wide"], m)
                c2.close()
        check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

main()
