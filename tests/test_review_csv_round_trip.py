"""Testing review (T6): Export CSV, then Import CSV of that same file, gives back the same units.

How it works: seven made-up units are loaded (a comma, quote marks and a new line in the text, an accent, a curly
apostrophe, two copies of one unit, a unit tracked model by model, a unit with no dates). Export CSV in Settings is
pressed and the downloaded file is picked with Import CSV, then Replace is chosen on the check screen. Checks:
1. The exported file: Excel's invisible mark at the start, the column titles Import CSV reads, one row per unit.
2. The check screen lists every unit and names no unknown stage and no left-out date.
3. After Replace, every unit comes back with the same name, game, faction, stage, nickname, model count, Repaint,
   notes, copy number, date added and date it reached its stage (what the CSV carries). Two things change on purpose:
   curly apostrophes in names and factions become straight ones (the import treats them as the same), and a unit with no dates
   is dated today (a row with no dates keeps today). What a CSV has no column for (each model's own stage, photos,
   linked recipes) is not compared.
4. Exporting again gives the same file, apart from that one unit's new dates.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import csv, io, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from launch_helpers import app_ready, leave_launch, open_settings, quiet
import fold_opener   # the Import card in Settings is folded shut on load

PORT = os.environ.get("SOG_PORT", "8000")
URL = f"http://localhost:{PORT}/index.html"
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "screenshots")
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# Made-up units (no real army names). Stage numbers are positions in the default stage list.
UNITS = [
    {"id": 1, "name": "Troop A", "hobby": "Test game", "faction": "Gloom Legion", "stage": 3, "count": 10,
     "nickname": "The Gold Squad", "repaint": False, "added": "2026-09-01", "log": [["2026-09-01", 0], ["2026-10-01", 3]]},
    {"id": 2, "name": "Walker, heavy", "hobby": "Test game", "faction": "Gloom Legion", "stage": 7, "count": 1, "repaint": True,
     "note": 'Magnetised, so can swap "guns"\nSecond line', "added": "2026-08-15",
     "log": [["2026-08-15", 2], ["2026-09-20", 5], ["2026-10-10", 7]]},
    {"id": 3, "name": "Scout", "hobby": "Skirmish", "faction": "Other Host", "stage": 0, "count": 5, "copy": 1,
     "added": "2026-10-02", "log": [["2026-10-02", 0]]},
    {"id": 4, "name": "Scout", "hobby": "Skirmish", "faction": "Other Host", "stage": 5, "count": 3, "copy": 2,
     "added": "2026-10-03", "log": [["2026-10-03", 1], ["2026-10-04", 5]]},
    {"id": 5, "name": "Café crew", "hobby": "Skirmish", "faction": "Other Host", "stage": 4, "count": 2, "nickname": "Les Bleus",
     "added": "2026-07-30", "log": [["2026-07-30", 4]]},
    {"id": 6, "name": "Hero band", "hobby": "Test game", "faction": "Hunter’s Lodge", "stage": 2, "count": 3, "each": True,
     "stages": [2, 4, 4], "added": "2026-09-05", "log": [["2026-09-05", 0], ["2026-09-10", 2], ["2026-09-12", 4, 1], ["2026-09-12", 4, 2]]},
    {"id": 7, "name": "Old box", "hobby": "", "faction": "", "stage": 1, "count": 4},   # from before the app kept dates
]
UNDATED = "Old box"
HEADER = ["name", "game", "faction", "stage", "nickname", "count", "repaint", "notes", "date_added", "date_stage"]

# What the CSV carries for each unit, as the app sees it (stageReachedOn is what Export CSV writes as date_stage).
SUMMARY = """() => models.map(m => ({ name: m.name, hobby: m.hobby || '', faction: m.faction || '', stage: m.stage,
    nickname: m.nickname || '', count: m.count, repaint: !!m.repaint, note: m.note || '', copy: m.copy || 0,
    added: m.added || '', reached: stageReachedOn(m) }))"""

def straight(text):
    return text.replace("‘", "'").replace("’", "'")

def export_csv(page):
    with page.expect_download() as dl:
        page.click("#csv-export-button")
    path = dl.value.path()
    with open(path, "rb") as f:
        return path, f.read().decode("utf-8")

def main():
    errors, dialogs = [], []
    os.makedirs(SHOTS, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce",
                                  accept_downloads=True)
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        fold_opener.open_cards_on_load(page)
        page.goto(URL)
        page.evaluate("""units => { localStorage.clear(); localStorage.setItem('mini-tracker-models', JSON.stringify(units));
            localStorage.setItem('shades-of-grey-settings', JSON.stringify({ examplesChecked: true, recipeExamplesChecked: true, tab: 'settings' })); }""",
                      UNITS)
        page.reload()
        app_ready(page)
        leave_launch(page)
        before = page.evaluate(SUMMARY)
        today = page.evaluate("todayISO()")

        print("--- 1. Export CSV ---")
        path, text = export_csv(page)
        check("the file starts with the mark that helps Excel read accents", text.startswith("﻿"), repr(text[:20]))
        rows = list(csv.reader(io.StringIO(text.lstrip("﻿"), newline="")))
        check("the first line is the column titles Import CSV reads", rows and rows[0] == HEADER, rows[:1])
        check("one row per unit, in order", [r[0] for r in rows[1:]] == [u["name"] for u in UNITS], [r[0] for r in rows[1:]])
        walker = next((r for r in rows if r and r[0] == "Walker, heavy"), None)
        check("a note with a comma, quote marks and a new line is kept whole in one cell",
              walker is not None and walker[7] == UNITS[1]["note"], walker)

        print("\n--- 2. Import CSV of the same file ---")
        with page.expect_file_chooser() as fc:
            page.click("#csv-button")
        fc.value.set_files(path)
        page.wait_for_selector("#review:not(.hidden)")
        summary = page.text_content("#review-summary")
        check("the check screen is for a CSV and lists all 7 units",
              page.text_content("#review-title") == "Check your CSV import" and page.locator("#review-list li").count() == len(UNITS),
              [page.text_content("#review-title"), page.locator("#review-list li").count()])
        check("…names no unknown stage and no left-out date", "don't match" not in summary and "Dates left out" not in summary, summary)
        page.click('#review .mode-button[data-mode="replace"]')
        page.wait_for_function("() => document.getElementById('review-go').textContent === 'Replace with 7 units'")
        page.click("#review-go")
        page.wait_for_selector("#dialog-yes", state="visible")
        page.click("#dialog-yes")
        page.wait_for_function("() => document.getElementById('review').classList.contains('hidden') && models.every(m => !m.each)")
        quiet(page)
        page.screenshot(path=os.path.join(SHOTS, "review_csv_round_trip_units.png"))
        after = page.evaluate(SUMMARY)

        print("\n--- 3. The same units come back ---")
        check("the same number of units, in the same order", [u["name"] for u in after] == [straight(u["name"]) for u in before],
              [u["name"] for u in after])
        pairs = list(zip(before, after))
        def same_field(label, keys, units=pairs):
            diffs = [f"{b['name']}: {k} was {b[k]!r}, now {a[k]!r}" for b, a in units for k in keys
                     if (straight(b[k]) if k in ("name", "faction") and isinstance(b[k], str) else b[k]) != a[k]]
            check(label, not diffs, "; ".join(diffs))
        same_field("names and nicknames, the accent kept", ["name", "nickname"])
        same_field("game and faction (a curly apostrophe made straight)", ["hobby", "faction"])
        same_field("stage, model count and Repaint", ["stage", "count", "repaint"])
        same_field("notes, including the comma, quotes and new line", ["note"])
        same_field("the two copies of Scout keep their numbers 1 and 2", ["copy"])
        dated = [(b, a) for b, a in pairs if b["name"] != UNDATED]
        same_field("the date each unit was added", ["added"], dated)
        same_field("the day each unit reached the stage it is at", ["reached"], dated)
        old = next((a for a in after if a["name"] == UNDATED), {})
        check("the unit with no dates is dated today (a row with no dates keeps today)",
              old.get("added") == today and old.get("reached") == today, old)
        hero = page.evaluate("() => { const m = models.find(x => x.name === 'Hero band'); return { faction: m.faction, log: m.log }; }")
        check("a unit tracked model by model comes back as one unit at its lowest stage, its diary the day it was added and the day it got there",
              hero["log"] == [["2026-09-05", 0], ["2026-09-10", 2]], hero)

        print("\n--- 4. Export again ---")
        open_settings(page)
        _, text2 = export_csv(page)
        undated_row = len(UNITS)   # the header is line 0
        first, second = text.split("\r\n"), text2.split("\r\n")
        changed = [i for i, (x, y) in enumerate(zip(first, second)) if x != y]
        straight_ok = all(straight(first[i]) == second[i] for i in changed if i != undated_row)
        check("a second export is the same file, apart from the undated unit's new dates (and straightened apostrophes)",
              len(first) == len(second) and set(changed) <= {undated_row, 6} and straight_ok
              and second[undated_row] == first[undated_row][:-1] + f"{today},{today}",
              [(first[i], second[i]) for i in changed])
        browser.close()

    check("no browser pop-ups", not dialogs, dialogs)
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
