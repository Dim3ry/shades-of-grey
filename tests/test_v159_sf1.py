"""SF1 tests for Minifolio (Models page: Detailed / Simple removed, Sort button and "Sort models" sheet). New behaviour only:
1. No Detailed / Simple switch; an old saved modelRows setting loads without error.
2. The Sort button (two lines) and the sheet: four presets, a tick on the chosen one, Done, Escape, X.
3. Default order: game, faction, name (ignoring "The"), headings with a faction dot and a count; no game / no faction go last.
4. The three other presets order the list and show no headings.
5. The choice is saved, survives a reload and travels in a backup.
6. Sorting with a filter on, and the summary line.
7. 390, 360 and 320 px, dark and light: no sideways scroll, 44 px targets.
Run with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys, json
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def unit(i, name, game, faction, stage, count=1, log=None, added="2026-09-01"):
    u = {"id": i, "name": name, "stage": stage, "count": count, "added": added, "log": log or [[added, 0]]}
    if game: u["hobby"] = game
    if faction: u["faction"] = faction
    return u

UNITS = [
    unit(1, "The Zealots", "Alpha", "Reds", 2, 10, [["2026-09-01", 0], ["2026-10-05", 2]]),
    unit(2, "Brutes", "Alpha", "Reds", 4, 5, [["2026-09-01", 0], ["2026-09-20", 4]]),
    unit(3, "Archers", "Alpha", "Blues", 1, 20, [["2026-09-01", 1]]),
    unit(4, "Cavalry", "Beta", "Greens", 3, 3, [["2026-09-01", 0], ["2026-11-01", 3]]),
    unit(5, "Drifters", "", "", 0, 1, [["2026-08-01", 0]], added="2026-08-01"),
    unit(6, "Eagles", "Alpha", "", 0, 2),
]
BASE = {"examplesChecked": True, "recipeExamplesChecked": True, "feedbackShown": True, "backupNudgeDone": True}
NAMES = "() => [...document.querySelectorAll('#unit-list li.unit .unit-name, #unit-list li.unit h3')].map(e => e.textContent.trim())"
LIST = """() => [...document.querySelectorAll('#unit-list > li')].map(li => li.classList.contains('unit-head')
    ? 'H:' + li.textContent.replace(/\\s+/g, ' ').trim() : 'U:' + li.dataset.id)"""

def ids(page):
    return [x[2:] for x in page.evaluate(LIST) if x.startswith("U:")]

def heads(page):
    return [x[2:] for x in page.evaluate(LIST) if x.startswith("H:")]

def start(page, **kw):
    t.load(page, units=kw.pop("units", UNITS), settings={**BASE, **kw.pop("settings", {})})
    page.click('nav button[data-tab="units"]')
    page.wait_for_selector("#unit-list li.unit")

def open_sheet(page):
    page.click("#toggle-sort")
    page.wait_for_selector(".sort-sheet-box .sort-row")

def pick(page, mode):
    page.click(f'.sort-row[data-sort-mode="{mode}"]')
    page.wait_for_timeout(150)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. No Detailed / Simple switch ---")
        each = unit(7, "Each squad", "Alpha", "Reds", 1, 4)
        each.update({"each": True, "stages": [1, 1, 2, 3]})
        start(page, units=UNITS + [each], settings={"modelRows": "simple"})
        check("no switch on the page, even with a unit tracked model by model", page.locator("#model-rows-switch").count() == 0 and "Detailed" not in page.locator("#view-units").inner_text())
        check("an old saved modelRows setting loads without a page error", not errors, errors)
        check("the old setting is dropped from the saved settings", "modelRows" not in page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-settings'))"))

        print("\n--- 2. Sort button and sheet ---")
        start(page)
        btn = page.locator("#toggle-sort")
        check("the button has a small Sort label and the current order under it",
              btn.locator(".sort-label").text_content() == "Sort" and btn.locator(".sort-order").inner_text() == "Game › Faction › A–Z", btn.inner_text())
        check("the button is at least 44 px high", btn.bounding_box()["height"] >= 44, btn.bounding_box())
        open_sheet(page)
        check("sheet title is Sort models", page.locator("#dialog-message").inner_text() == "Sort models")
        rows = page.locator(".sort-row")
        check("four choices, default first, each with a second line",
              rows.count() == 4 and rows.nth(0).locator(".sort-row-title").inner_text() == "Game › Faction › A–Z"
              and all(rows.nth(i).locator(".sort-row-sub").inner_text() for i in range(4)), rows.all_inner_texts())
        check("the default is ticked and announced as checked", rows.nth(0).get_attribute("aria-checked") == "true" and "✓" in rows.nth(0).inner_text()
              and rows.nth(1).get_attribute("aria-checked") == "false")
        check("focus starts inside the sheet", page.evaluate("() => document.getElementById('dialog').contains(document.activeElement)"))
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
        check("Escape closes it", not page.locator("#dialog-backdrop").is_visible())
        open_sheet(page)
        page.click(".sort-x")
        check("the X button closes it", not page.locator("#dialog-backdrop").is_visible())
        open_sheet(page)
        page.click("#dialog-yes")
        check("Done closes it", not page.locator("#dialog-backdrop").is_visible())

        print("\n--- 3. Default order and headings ---")
        # Alpha: Blues (Archers), Reds (Brutes, The Zealots = Zealots), no faction (Eagles); Beta: Greens; no game: Drifters
        check("game, then faction, then name ignoring The; no faction last in its game, no game last of all",
              ids(page) == ["3", "2", "1", "6", "4", "5"], ids(page))
        h = heads(page)
        check("game headings and faction headings with unit counts, No faction and No game at the end",
              h[0].startswith("Alpha") and any(x.startswith("Blues") and "1 unit" in x for x in h) and any(x.startswith("Reds") and "2 units" in x for x in h)
              and "No faction" in " ".join(h) and "No game" in h, h)
        check("a faction heading carries a dot", page.locator("#unit-list .faction-head .head-dot").count() >= 3)

        print("\n--- 4. The other presets ---")
        open_sheet(page); pick(page, "az")
        check("A–Z: names only, ignoring The, flat list with no headings", ids(page) == ["3", "2", "4", "5", "6", "1"] and not heads(page), (ids(page), heads(page)))
        check("the choice applies at once and the button says A–Z", page.locator("#toggle-sort .sort-order").inner_text() == "A–Z"
              and page.locator('.sort-row[data-sort-mode="az"]').get_attribute("aria-checked") == "true")
        pick(page, "stage")
        check("Stage: furthest along first, then A–Z", ids(page) == ["2", "4", "1", "3", "5", "6"] and not heads(page), ids(page))
        pick(page, "recent")
        # 4: 1 Nov, 1: 5 Oct, 2: 20 Sep, 3 and 6: added 1 Sep (log date 1 Sep / added only), 5: 1 Aug
        check("Recently updated: last stage change first, then added date, then A–Z", ids(page) == ["4", "1", "2", "3", "6", "5"] and not heads(page), ids(page))

        print("\n--- 5. Saved ---")
        saved = page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-settings')).unitSort")
        check("saved with the other settings", saved == {"mode": "recent"}, saved)
        page.keyboard.press("Escape")
        page.reload(); t.app_ready(page); t.leave_launch(page)
        page.click('nav button[data-tab="units"]')
        page.wait_for_selector("#unit-list li.unit")
        page.wait_for_timeout(600)
        check("survives a reload", ids(page) == ["4", "1", "2", "3", "6", "5"] and page.locator("#toggle-sort .sort-order").inner_text() == "Recently updated",
              (ids(page), page.locator("#toggle-sort .sort-order").inner_text()))
        backup = page.evaluate("() => backupData().unitSort")
        check("travels in a backup", backup == {"mode": "recent"}, backup)
        t.load(page, units=UNITS, settings={**BASE, "unitSort": {"mode": "bogus"}})
        page.click('nav button[data-tab="units"]'); page.wait_for_selector("#unit-list li.unit")
        check("an unknown saved choice means the default", page.locator("#toggle-sort .sort-order").inner_text() == "Game › Faction › A–Z" and ids(page)[0] == "3")

        print("\n--- 6. Filters and the summary line ---")
        start(page, settings={"unitSort": {"mode": "stage"}})
        page.evaluate("() => goToUnits({ hobby: 'Alpha' })")   # how a Nexus shortcut opens Models filtered (the Filters panel itself is not this chunk's)
        page.wait_for_timeout(300)
        check("sorting works with a filter on", ids(page) == ["2", "1", "3", "6"], ids(page))
        note = page.locator("#filter-note").inner_text()
        check("the summary line stays right", note == "Alpha: 4 of 6 units (37 models)", note)
        page.evaluate("() => { clearFilters(); render(); }")
        page.wait_for_timeout(200)
        check("and without a filter", page.locator("#filter-note").inner_text() == "6 units, 41 models", page.locator("#filter-note").inner_text())
        start(page)
        page.click("#toggle-select")
        check("Select mode still lists the units in order", ids(page) == ["3", "2", "1", "6", "4", "5"], ids(page))
        page.click("#toggle-select")

        print("\n--- 7. Sizes, scrolling, looks ---")
        for w, hgt in [(390, 844), (360, 640), (320, 568)]:
            for scheme in ["dark", "light"]:
                c2 = browser.new_context(viewport={"width": w, "height": hgt}, service_workers="block", color_scheme=scheme, reduced_motion="reduce")
                pg = c2.new_page()
                start(pg, settings={"appearance": scheme})
                m = pg.evaluate("""() => { const b = document.getElementById('toggle-sort').getBoundingClientRect(), o = document.getElementById('sort-order');
                    return { h: b.height, right: b.right, vw: window.innerWidth, cut: o.scrollWidth > o.clientWidth + 1, wide: document.documentElement.scrollWidth > window.innerWidth + 1 }; }""")
                check(f"{w}px {scheme}: Sort button 44 px high, on screen, no sideways scroll", m["h"] >= 44 and m["right"] <= m["vw"] and not m["wide"], m)
                pg.click("#toggle-sort")
                pg.wait_for_selector(".sort-sheet-box .sort-row")
                s = pg.evaluate("""() => { const rows = [...document.querySelectorAll('.sort-row')].map(r => r.getBoundingClientRect().height),
                    box = document.getElementById('dialog').getBoundingClientRect(), x = document.querySelector('.sort-x').getBoundingClientRect();
                    return { rows, x: [x.width, x.height], inside: box.right <= window.innerWidth + 1 && box.left >= -1, wide: document.documentElement.scrollWidth > window.innerWidth + 1 }; }""")
                check(f"{w}px {scheme}: sheet rows and X are 44 px, nothing sideways", all(r >= 44 for r in s["rows"]) and min(s["x"]) >= 44 and s["inside"] and not s["wide"], s)
                c2.close()
        check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

main()
