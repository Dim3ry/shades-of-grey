"""v60 tests for Minifolio (chunk 1.3: import counts, and a stage for every row of the import check).

What changed:
 AI testers found that units from a pasted army list often came in as 1 model, because a count written on the unit's
 own line ("10x Boyz", "Boyz x10", "Boyz (10 models)") was never read. Counts were only taken from indented model lines
 under a "Name (N points)" line. They also could not give each unit its own stage: one menu set every unit's stage.

Checks:
1. Versions, the v60 Updates entry, DATA_VERSION is still 1.
2. Counts are read from a unit's own line, in Warhammer app lists and in lists typed by hand. The real export still
   gives 17 units and 75 models, and names with numbers in them (Broadside XV88) are left alone.
3. The import check: every row has a model count box and its own stage menu. "Set every row to" fills every row's
   menu and shows Mixed when they differ. The tick only says import or not. The import uses each row's stage and count,
   and Undo puts everything back.
4. CSV: a stage column that matches a stage name is used; an unknown one starts at the Set every row to stage.
5. Add and Replace use the same rows: switching keeps the row edits.
6. A long list (17 units): the Set every row to bar stays in view while scrolling.
7. 390 px and 360 px, dark and light: no sideways scroll, tap targets 44 px or more.
8. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
import test_v31 as t
import test_v44 as e   # fresh, main_tab

URL, read = t.URL, t.read
HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT = open(os.path.join(HERE, "real_40k_tyranids.txt"), encoding="utf-8").read()
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

OLD_UNIT = {"id": 1, "name": "Old unit", "hobby": "40K", "faction": "Orks", "stage": 0, "count": 1,
            "added": "2026-10-01", "log": [["2026-10-01", 0]]}

def stored(page):
    return json.loads(page.evaluate("localStorage.getItem('mini-tracker-models') || '[]'"))

def paste(page, text):
    e.main_tab(page, "units")
    page.click("#toggle-add")
    page.click("#add-wh")
    page.fill("#wh-text", text)
    page.click("#wh-read")
    page.wait_for_timeout(250)

def rows(page):
    return page.locator("#review-list li")

def main():
    errors, dialogs = [], []
    app, html = read("app.js"), read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        attach_notices(page, dialogs.append)

        # ---------- 1. Versions ----------
        print("\n--- 1. Versions and the Updates entry ---")
        t.load(page, units=[])
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v60 or later", float(version[1:]) >= 60, version)
        m = re.search(r'const VERSION = "v([\d.]+)"', read("sw.js"))
        check("sw.js VERSION matches", m and "v" + m.group(1) == version, m and m.group(1))
        tags = re.findall(r'<script src="[^"]+\?v=(\d+)"', html)
        check("all six script tags carry the version number", len(tags) == 6 and set(tags) == {version[1:]}, tags)
        check("the comments that name the number agree", f'The "?v={version[1:]}" makes' in html and f'e.g. "app.js?v={version[1:]}"' in app)
        entry = page.evaluate("CHANGELOG.find(c => c.version === 'v60')")
        check("the v60 Updates entry exists and is the newest while v60 is current", bool(entry) and (version != "v60" or page.evaluate("CHANGELOG[0].version") == "v60"))
        check("the entry mentions counts and Set every row to", entry and "10x Boyz" in " ".join(entry["changes"]) and "Set every row to" in " ".join(entry["changes"]), entry)
        check("no em dash in the v60 Updates entry", "—" not in app[app.index('{ version: "v60"'):app.index('{ version: "v59"')])
        check("DATA_VERSION is still 1", page.evaluate("DATA_VERSION") == 1)
        check("Help explains typed lists and the per-row stage", page.locator("#help-typed-list").count() == 1 and "Set every row to" in (page.text_content("#help-row-stage") or ""))

        # ---------- 2. Reading counts ----------
        print("\n--- 2. Counts from the unit's own line ---")
        names = page.evaluate("""() => ['10x Boyz', '10 x Boyz', 'Boyz x10', 'Boyz ×10', 'Boyz (10)', 'Boyz [10x]', 'Boyz (10 models)',
            'Boyz - 10 models', '10 Boyz', 'Broadside XV88', 'Squad 5', 'Boyz', 'Boyz x0', 'Boyz x5000'].map(countInName)""")
        check("ten ways of writing 10 Boyz all read as Boyz, 10", all(n == {"name": "Boyz", "count": 10} for n in names[:9]), names[:9])
        check("a name with a number in it is left alone (Broadside XV88, Squad 5)", names[9] == {"name": "Broadside XV88", "count": None} and names[10] == {"name": "Squad 5", "count": None}, names[9:11])
        check("no count stays no count; 0 isn't a count; a huge count is capped at 999",
              names[11]["count"] is None and names[12]["count"] is None and names[13] == {"name": "Boyz", "count": 999}, names[11:])
        app_list = page.evaluate("""() => parseWarhammerList('Ork list (500 points)\\n\\nOrks\\nStrike Force (2000 points)\\n\\n10x Boyz (85 points)\\n\\n' +
            'Nobz x5 (100 points)\\n  • 1x Big choppa\\n\\nGretchin (40 points)\\n  • 1x Runtherd\\n    • 1x Grabba stikk\\n  • 10x Gretchin\\n    • 10x Grot blasta\\n\\n' +
            'Warboss (75 points)\\n  • 1x Big choppa\\n\\nExported with App Version: v1.0')""")
        got = [(u["name"], u["count"]) for u in app_list["units"]] if app_list else app_list
        check("a Warhammer app style list reads counts on the unit line and still counts model lines",
              got == [("Boyz", 10), ("Nobz", 5), ("Gretchin", 11), ("Warboss", 1)], got)
        check("…and Strike Force (2000 points) is still not a unit", app_list and app_list["faction"] == "Orks")
        typed = page.evaluate("() => parseWarhammerList('My Orks\\n10x Boyz\\nWarboss\\n  Big choppa\\n- 5x Nobz\\nHQ\\nGretchin (11 models)')")
        got = [(u["name"], u["count"]) for u in typed["units"]] if typed else typed
        check("a list typed by hand: the first line is the list name, indented lines are wargear",
              typed and typed["listName"] == "My Orks" and got == [("Boyz", 10), ("Warboss", 1), ("Nobz", 5), ("HQ", 1), ("Gretchin", 11)], typed)
        check("text with no counts and no points is still refused", page.evaluate("() => parseWarhammerList('hello\\nthere\\nfriend')") is None)
        real = page.evaluate("(text) => parseWarhammerList(text)", EXPORT)
        check("the real export still gives 17 units and 75 models",
              len(real["units"]) == 17 and sum(u["count"] for u in real["units"]) == 75, real and len(real["units"]))

        # ---------- 3. The import check ----------
        print("\n--- 3. A count and a stage on every row ---")
        stages = page.evaluate("STAGES")
        paste(page, EXPORT)
        n = rows(page).count()
        check("17 rows, each with a count box and a stage menu",
              n == 17 and rows(page).locator("input[type=number]").count() == 17 and rows(page).locator("select.stage-pick").count() == 17, n)
        check("the count boxes show the counts from the list", rows(page).nth(4).locator("input[type=number]").input_value() == "10")
        check("the stage menus are named after their unit", rows(page).nth(0).locator("select.stage-pick").get_attribute("aria-label") == "Stage for Deathleaper")
        check("Set every row to is shown for an army list", page.is_visible("#wh-stage") and "Set every row to" in page.inner_text("#review-set-all"))
        page.select_option("#wh-stage", "2")
        page.wait_for_timeout(100)
        menus = page.evaluate("() => [...document.querySelectorAll('#review-list select.stage-pick')].map(s => s.value)")
        check("Set every row to fills every row's menu", menus == ["2"] * 17, menus)
        check("…and keeps the focus on itself", page.evaluate("document.activeElement && document.activeElement.id") == "wh-stage")
        rows(page).nth(1).locator("select.stage-pick").select_option("4")
        rows(page).nth(4).locator("input[type=number]").fill("12")
        page.wait_for_timeout(100)
        check("changing one row makes Set every row to say Mixed", page.input_value("#wh-stage") == "" and "Mixed" in page.inner_text("#wh-stage"))
        check("the summary counts the changed count", "77 models" in page.inner_text("#review-summary"), page.inner_text("#review-summary"))
        rows(page).nth(2).locator("input[type=checkbox]").uncheck()
        page.wait_for_timeout(100)
        check("unticking a row keeps its stage (the tick is only import or not)", rows(page).nth(2).locator("select.stage-pick").input_value() == "2")
        check("…and the other rows keep theirs", rows(page).nth(1).locator("select.stage-pick").input_value() == "4")
        page.click("#review-go")
        page.wait_for_timeout(300)
        units = stored(page)
        by_name = {}
        for u in units: by_name.setdefault(u["name"], []).append(u)
        check("16 units imported (one was unticked)", len(units) == 16, len(units))
        check("each unit has its row's stage", by_name["Hive Tyrant"][0]["stage"] == 4 and by_name["Deathleaper"][0]["stage"] == 2 and "Neurotyrant" not in by_name)
        check("each unit has its row's count", sorted(u["count"] for u in by_name["Gargoyles"]) == [10, 12])
        check("the history starts at the chosen stage", by_name["Hive Tyrant"][0]["log"][0][1] == 4)
        check("nothing extra is saved on the units", not any("stageGiven" in u or "models" in u for u in units))
        page.click("#toast button")
        page.wait_for_timeout(250)
        check("Undo straight after puts everything back", stored(page) == [])

        # ---------- 4. CSV ----------
        print("\n--- 4. CSV stages ---")
        csv = f"name,faction,stage,count\nBoyz,Orks,{stages[3]},10\nNobz,Orks,Not a stage,5\nWarboss,Orks,,1\n".encode()
        e.main_tab(page, "units")
        page.click("#toggle-add")
        with page.expect_file_chooser() as chooser:
            page.click("#add-csv")
        chooser.value.set_files(files=[{"name": "army.csv", "mimeType": "text/csv", "buffer": csv}])
        page.wait_for_timeout(300)
        menus = page.evaluate("() => [...document.querySelectorAll('#review-list select.stage-pick')].map(s => s.value)")
        check("a CSV stage that matches starts there; unknown or blank starts at the Set every row to stage", menus == ["3", "0", "0"], menus)
        check("Set every row to is shown for a CSV too", page.is_visible("#wh-stage"))
        page.select_option("#wh-stage", "1")
        page.wait_for_timeout(100)
        menus = page.evaluate("() => [...document.querySelectorAll('#review-list select.stage-pick')].map(s => s.value)")
        check("…and fills every CSV row", menus == ["1", "1", "1"], menus)
        page.click("#review-go")
        page.wait_for_timeout(300)
        check("the CSV units come in at that stage with their counts",
              sorted((u["name"], u["stage"], u["count"]) for u in stored(page)) == [("Boyz", 1, 10), ("Nobz", 1, 5), ("Warboss", 1, 1)], stored(page))

        # ---------- 5. Add and Replace use the same rows ----------
        print("\n--- 5. Add and Replace ---")
        t.load(page, units=[OLD_UNIT])
        paste(page, "List (200 points)\n\nOrks\n\n10x Boyz (85 points)\n\nWarboss (75 points)\n  • 1x Big choppa")
        rows(page).nth(0).locator("select.stage-pick").select_option("3")
        rows(page).nth(0).locator("input[type=number]").fill("15")
        page.click('#review-mode .mode-button[data-mode="replace"]')
        page.wait_for_timeout(150)
        check("switching to Replace keeps the row's stage and count",
              rows(page).nth(0).locator("select.stage-pick").input_value() == "3" and rows(page).nth(0).locator("input[type=number]").input_value() == "15")
        page.click('#review-mode .mode-button[data-mode="add"]')
        page.wait_for_timeout(150)
        check("…and so does switching back to Add", rows(page).nth(0).locator("select.stage-pick").input_value() == "3")
        page.click('#review-mode .mode-button[data-mode="replace"]')
        page.click("#review-go")
        page.wait_for_timeout(200)
        page.locator(".dialog-buttons button", has_text="Yes").first.click() if page.locator(".dialog-buttons button", has_text="Yes").count() else None
        page.wait_for_timeout(300)
        got = sorted((u["name"], u["stage"], u["count"]) for u in stored(page))
        check("Replace uses the row's stage and count", got == [("Boyz", 3, 15), ("Warboss", 0, 1)], got)
        page.click("#toast button")
        page.wait_for_timeout(250)
        check("Undo after Replace brings the old unit back", [u["name"] for u in stored(page)] == ["Old unit"])

        # ---------- 6 and 7. Long list, phone sizes, dark and light ----------
        for appearance in ["dark", "light"]:
            for width in [390, 360]:
                tag = f"{appearance} {width}px"
                print(f"\n--- 6/7. {tag} ---")
                page.set_viewport_size({"width": width, "height": 780})
                t.load(page, units=[], settings={"appearance": appearance})
                paste(page, EXPORT)
                page.evaluate("() => document.querySelector('#review-list li:last-child').scrollIntoView({ block: 'end' })")
                page.wait_for_timeout(150)
                box = page.evaluate("() => { const r = document.getElementById('review-set-all').getBoundingClientRect(); return [r.top, r.bottom]; }")
                check(f"{tag}: Set every row to stays in view at the bottom of a 17-unit list", box[0] >= 0 and box[1] <= 780 and box[0] < 80, box)
                check(f"{tag}: no sideways scroll", not page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth"))
                small = page.evaluate("""() => [...document.querySelectorAll('#review-list input[type=number], #review-list select.stage-pick, #wh-stage, #review-all, #review-none')]
                    .filter(el => el.offsetParent).map(el => [el.id || el.className, Math.round(el.getBoundingClientRect().height)]).filter(([, h]) => h < 44)""")
                check(f"{tag}: count boxes, stage menus and the set-all bar are 44 px or more", not small, small)
                os.makedirs(os.path.join(HERE, "screenshots"), exist_ok=True)
                page.screenshot(path=os.path.join(HERE, "screenshots", f"v60-review-{appearance}-{width}.png"))
        page.set_viewport_size({"width": 1280, "height": 800})
        t.load(page, units=[])
        paste(page, EXPORT)
        page.evaluate("() => document.querySelector('#review-list li:last-child').scrollIntoView({ block: 'end' })")
        page.wait_for_timeout(150)
        box = page.evaluate("""() => [document.getElementById('review-set-all').getBoundingClientRect().top,
                                      document.querySelector('.tabs').getBoundingClientRect().bottom]""")
        check("wide screen: the set-all bar sits below the tab bar, not under it", box[0] >= box[1] - 1, box)

        # ---------- 8. Safety ----------
        print("\n--- 8. Safety ---")
        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
