"""IM1 tests for Minifolio (two optional CSV date columns, so an imported collection gets a real progress graph). New behaviour only:
1. date_added and date_stage: both accepted styles (2026-03-01 and 01/02/2026, day first), a stage date with no joined date,
   a joined date after the stage date, a date that is not a real day, a date in the future and another style are handled as
   the prompt says. The rows still come in, and the import check shows one line with how many rows lost a date and their row
   numbers (spreadsheet numbering, blank rows counted). The units' history holds the dates, and the graph counts them on those days.
2. A file without the date columns imports as before: joined today, history starts today.
3. Undo straight after removes the dated units (and their dates).
4. Export CSV writes date_added and date_stage (blank where there is none), and exporting then importing (Replace) gives the
   same units and dates. The CSV template has the two columns with one row filled in.
5. An Excel-style file (the invisible first character, CRLF line ends, day-first dates) of 500 rows reads correctly and quickly.
6. 390x844 dark, 360x640 dark and light, 320 px light: the import check with the date line has no sideways scroll.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import datetime, json, os, sys, time
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
import test_v44 as e   # main_tab

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

TODAY = datetime.date.today().isoformat()
FUTURE = (datetime.date.today() + datetime.timedelta(days=30)).strftime("%d/%m/%Y")
OLD_UNIT = {"id": 1, "name": "Old unit", "hobby": "40K", "faction": "Orks", "stage": 0, "count": 1,
            "added": "2026-01-05", "log": [["2026-01-05", 0]]}

def stored(page):
    return json.loads(page.evaluate("localStorage.getItem('mini-tracker-models') || '[]'"))

def import_csv(page, data, name="army.csv"):
    e.main_tab(page, "units")
    page.click("#toggle-add")
    with page.expect_file_chooser() as chooser:
        page.click("#add-csv")
    chooser.value.set_files(files=[{"name": name, "mimeType": "text/csv", "buffer": data}])
    page.wait_for_selector("#review:not(.hidden)")

def go(page, replace=False):
    if replace:
        page.click('#review-mode .mode-button[data-mode="replace"]')
    page.click("#review-go")
    if replace:
        page.locator(".dialog-buttons button", has_text="Yes").first.click()
    page.wait_for_selector("#review", state="hidden")

def download(page, button):
    with page.expect_download() as d:
        page.evaluate(f"document.getElementById('{button}').click()")
    with open(d.value.path(), encoding="utf-8", newline="") as f:
        return f.read()

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce", accept_downloads=True)
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        print("\n--- 1. Date columns ---")
        t.load(page, units=[OLD_UNIT])
        stages = page.evaluate("STAGES")
        last = len(stages) - 1
        csv = (f"name,faction,stage,count,date_added,date_stage\n"
               f"Iso,Orks,{stages[last]},5,2026-03-01,2026-04-15\n"            # row 2
               f"Uk,Orks,{stages[1]},3,01/02/2026,10/02/2026\n"                # row 3
               f"StageOnly,Orks,{stages[2]},1,,2026-05-05\n"                   # row 4
               f"Swapped,Orks,{stages[1]},1,2026-06-10,2026-06-01\n"           # row 5: joined after its stage date
               f"BadDay,Orks,,1,31/02/2026,\n"                                 # row 6: no such day
               f"Future,Orks,,1,{FUTURE},\n"                                   # row 7
               f"OtherStyle,Orks,,1,2/11/2026,\n"                              # row 8: not two-digit day first
               f"\n"                                                           # row 9: blank, still counted
               f"NoDates,Orks,,2,,\n"                                          # row 10
               f"AddedOnly,Orks,{stages[1]},1,2026-07-07,\n").encode()         # row 11
        brief = lambda: [(u["name"], u.get("added"), u.get("log")) for u in stored(page)]
        before = brief()
        import_csv(page, csv)
        summary = page.text_content("#review-summary")
        check("one line names the rows that lost a date, in spreadsheet row numbers",
              "Dates left out on 4 rows: 5, 6, 7, 8." in summary, summary)
        check("every row still comes in", page.locator("#review-list li").count() == 9)
        go(page)
        by = {u["name"]: u for u in stored(page)}
        hist = lambda n: (by[n].get("added"), by[n].get("log"))
        check("ISO dates: joined on date_added, reached its stage on date_stage",
              hist("Iso") == ("2026-03-01", [["2026-03-01", 0], ["2026-04-15", last]]), hist("Iso"))
        check("day-first dates read as UK order", hist("Uk") == ("2026-02-01", [["2026-02-01", 0], ["2026-02-10", 1]]), hist("Uk"))
        check("date_stage alone is used for both", hist("StageOnly") == ("2026-05-05", [["2026-05-05", 2]]), hist("StageOnly"))
        check("date_added after date_stage: date_stage for both", hist("Swapped") == ("2026-06-01", [["2026-06-01", 1]]), hist("Swapped"))
        check("date_added alone: joined that day at its stage", hist("AddedOnly") == ("2026-07-07", [["2026-07-07", 1]]), hist("AddedOnly"))
        check("a bad, future or other-style date is left out: that unit joins today",
              all(hist(n) == (TODAY, [[TODAY, 0]]) for n in ["BadDay", "Future", "OtherStyle", "NoDates"]),
              [hist(n) for n in ["BadDay", "Future", "OtherStyle", "NoDates"]])
        check("nothing extra is saved on the units", not any(k in u for u in by.values() for k in ("dateAdded", "dateStage", "stageGiven")))
        g = page.evaluate("""() => { const h = historyData(), on = (d) => h.valuesOn(dayNumber(d));
            return { first: h.first === dayNumber('2026-01-05'), a: on('2026-02-28'), b: on('2026-03-01'), c: on('2026-04-14'), d: on('2026-04-15'),
                     doneLast: isDone(STAGES.length - 1) }; }""")
        check("the graph adds the models on the day they joined", g["b"]["added"] - g["a"]["added"] == 5 and g["first"], g)
        check("…and counts them painted on their stage date, not before", g["doneLast"] and g["d"]["done"] - g["c"]["done"] == 5 and g["c"]["added"] == g["d"]["added"], g)
        e.main_tab(page, "dashboard")
        check("the graph draws with the past dates", page.locator("#history-chart svg").count() == 1 and not errors, errors)

        print("\n--- 2. Undo ---")
        page.click("#toast button")
        page.wait_for_function("JSON.parse(localStorage.getItem('mini-tracker-models') || '[]').length === 1")
        check("Undo straight after removes the dated units and their dates", brief() == before, brief())

        print("\n--- 3. A file without date columns ---")
        import_csv(page, b"name,faction,stage\nBoyz,Orks,2\n")
        check("no date line when the file has no dates", "Dates left out" not in page.text_content("#review-summary"))
        go(page)
        boyz = [u for u in stored(page) if u["name"] == "Boyz"][0]
        check("it imports as before: joined today, history starts today", (boyz["added"], boyz["log"]) == (TODAY, [[TODAY, 2]]), boyz)

        print("\n--- 4. Export, template and the round trip ---")
        units = [OLD_UNIT,
                 {"id": 2, "name": "Painted, \"Best\"", "hobby": "40K", "faction": "Orks", "stage": last, "count": 5,
                  "added": "2026-03-01", "log": [["2026-03-01", 0], ["2026-03-20", 2], ["2026-04-15", last]]},
                 {"id": 3, "name": "No dates", "hobby": "40K", "faction": "Orks", "stage": 1, "count": 2, "log": []},
                 {"id": 4, "name": "Each", "hobby": "40K", "faction": "Orks", "stage": 1, "count": 2, "each": True, "stages": [1, 2],
                  "added": "2026-02-01", "log": [["2026-02-01", 0], ["2026-02-03", 1, 0], ["2026-02-09", 1, 1], ["2026-02-20", 2, 1]]}]
        t.load(page, units=units)
        text = download(page, "csv-export-button")
        lines = text.lstrip("﻿").split("\r\n")
        check("Export CSV writes the two date columns", lines[0].endswith(",date_added,date_stage"), lines[0])
        check("…with the joined day and the day it reached its stage", lines[2].endswith(",2026-03-01,2026-04-15"), lines[2])
        check("…blank when the app has no date", lines[3].endswith(",,"), lines[3])
        check("…and for a track-each-model unit, the day its slowest model got there", lines[4].endswith(",2026-02-01,2026-02-09"), lines[4])
        import_csv(page, text.encode("utf-8"), "minifolio.csv")
        go(page, replace=True)
        back = {u["name"]: (u.get("added"), u["stage"], u["count"]) for u in stored(page)}
        dates = page.evaluate("() => models.map(m => [m.name, stageReachedOn(m)])")
        check("export then import (Replace) gives the same units and dates",
              back == {"Old unit": ("2026-01-05", 0, 1), 'Painted, "Best"': ("2026-03-01", last, 5), "No dates": (TODAY, 1, 2), "Each": ("2026-02-01", 1, 2)}, back)
        check("…and the same stage dates", dict(dates) == {"Old unit": "2026-01-05", 'Painted, "Best"': "2026-04-15", "No dates": TODAY, "Each": "2026-02-09"}, dates)
        tpl = download(page, "template-button").splitlines()
        filled = [l for l in tpl[1:] if not l.endswith(",,")]
        check("the template has the two columns and one row with dates filled in",
              tpl[0].endswith(",date_added,date_stage") and len(filled) == 1 and filled[0].split(",")[-1] < TODAY, tpl)

        print("\n--- 5. A 500-row file saved by Excel ---")
        t.load(page, units=[])
        rows = ["name,game,faction,stage,nickname,count,repaint,notes,date_added,date_stage"]
        for i in range(500):
            d = datetime.date(2025, 1, 1) + datetime.timedelta(days=i)
            bad = "32/01/2026" if i % 50 == 7 else d.strftime("%d/%m/%Y")
            rows.append(f"Unit {i},40K,Orks,{stages[last] if i % 2 else stages[0]},,1,no,,{bad},{(d + datetime.timedelta(days=10)).strftime('%d/%m/%Y')}")
        data = ("﻿" + "\r\n".join(rows) + "\r\n").encode("utf-8")
        e.main_tab(page, "units")
        page.click("#toggle-add")
        with page.expect_file_chooser() as chooser:
            page.click("#add-csv")
        start = time.time()
        chooser.value.set_files(files=[{"name": "excel.csv", "mimeType": "text/csv", "buffer": data}])
        page.wait_for_selector("#review:not(.hidden)")
        opened = time.time() - start
        summary = page.text_content("#review-summary")
        check("the invisible first character and day-first dates read correctly; the line lists the first five rows",
              "Dates left out on 10 rows: 9, 59, 109, 159, 209 and 5 more." in summary, summary)
        start = time.time()
        go(page)
        spent = time.time() - start
        e.main_tab(page, "dashboard")
        print(f"  (500 rows: check opened in {opened:.1f} s, import took {spent:.1f} s)")
        u = {x["name"]: x for x in stored(page)}
        check("500 rows: check opens and imports without freezing", opened < 8 and spent < 8 and len(u) == 500, (opened, spent, len(u)))
        check("…with the right dates", u["Unit 1"]["added"] == "2025-01-02" and u["Unit 1"]["log"][-1] == ["2025-01-12", last]
              and u["Unit 7"]["added"] == "2025-01-18", (u["Unit 1"], u["Unit 7"]))

        print("\n--- 6. Phone sizes, dark and light ---")
        csv = f"name,faction,date_added\n{chr(10).join(f'U{i},Orks,99/99/2026' for i in range(12))}\n".encode()
        bad = []
        for appearance, w, h in [("dark", 390, 844), ("light", 360, 640), ("dark", 360, 640), ("light", 320, 640)]:
            page.set_viewport_size({"width": w, "height": h})
            t.load(page, units=[OLD_UNIT], settings={"appearance": appearance, "examplesChecked": True})
            import_csv(page, csv)
            over = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
            inside = page.evaluate("() => document.getElementById('review-summary').getBoundingClientRect().right <= window.innerWidth")
            if over or not inside:
                bad.append((appearance, w, over, inside))
            if appearance == "dark" and w == 360:
                page.locator("#review").screenshot(path=os.path.join(t.SHOTS, "im1-review-360-dark.png"))
        check("the date line fits at 390 (dark), 360 (dark and light) and 320 px (light), with no sideways scroll", not bad, bad)

        check("no page errors", not errors, errors[:3])
        check("no browser pop-ups", not dialogs, dialogs[:3])
        browser.close()

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)

if __name__ == "__main__":
    main()
