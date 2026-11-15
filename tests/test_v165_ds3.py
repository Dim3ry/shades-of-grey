"""DS3 test for Minifolio: keeping the Wanted list safe. New behaviour only, with real taps where it matters.
1. The safety copy made before a restore holds the Wanted list and faction colours, and Recover brings them back (and Undo).
2. An old safety copy with neither field still recovers, and leaves your wanted models alone.
3. A backup with wanted models but no units restores (and Undo puts them back).
4. "Save a backup?" notices a change to the Wanted list (and is unchanged for a person with none).
5. Saving an edit to a wanted model finds it by id, so an edit survives another window swapping the list.
6. The kept copy of damaged settings is listed in Recover and removed after 30 days.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import tap_tab

results = []
def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

STAGES = ["Boxed", "Built", "Primed", "Painted"]
UNIT = {"id": 1, "name": "Squad", "hobby": "Skirmish", "faction": "Bright Host", "stage": 1, "count": 3, "added": "2026-09-01", "log": [["2026-09-01", 1]]}
UNIT2 = {"id": 2, "name": "Riders", "hobby": "Skirmish", "faction": "Dark Host", "stage": 2, "count": 2, "added": "2026-09-02", "log": [["2026-09-02", 2]]}
WISH = {"id": 1, "name": "Zed Riders", "count": 2, "game": "Skirmish", "faction": "Bright Host", "really": False, "note": "", "added": "2026-10-01"}
WISH2 = {"id": 7, "name": "Old Guard", "count": 5, "game": "Skirmish", "faction": "Dark Host", "really": True, "note": "", "added": "2026-10-02"}
BASE = {"examplesChecked": True, "stages": STAGES, "modelWishes": [WISH], "factionColours": {"Bright Host": "#112233"}}

def names(page): return page.evaluate("wishes().map(w => w.name)")
def colours(page): return page.evaluate("settings.factionColours")
def backup(data): return {"name": "b.json", "mimeType": "application/json", "buffer": json.dumps(data).encode()}
def restore(page, data):
    page.set_input_files("#restore-file", files=[backup(data)])
    page.wait_for_selector("#dialog-backdrop:not(.hidden)")
    q = page.text_content("#dialog-message"); page.click("#dialog-yes"); page.wait_for_timeout(700); return q
def open_settings(page):
    tap_tab(page, "settings"); t.quiet(page)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w, h, scheme in ((390, 844, "dark"), (360, 640, "light")):
            ctx = browser.new_context(viewport={"width": w, "height": h}, color_scheme=scheme, service_workers="block")
            page = ctx.new_page()
            page.on("pageerror", lambda x: errors.append(str(x)))
            page.on("dialog", lambda d: d.dismiss())
            print(f"\n--- 1. Safety copy and Recover ({w}px, {scheme}) ---")
            t.load(page, units=[UNIT], settings=BASE)
            open_settings(page)
            restore(page, {"app": "Minifolio", "dataVersion": 2, "models": [UNIT2], "modelWishes": [WISH2], "factionColours": {"Dark Host": "#445566"}})
            check("the restore replaced the wanted list and colours", names(page) == ["Old Guard"] and "Bright Host" not in colours(page), (names(page), colours(page)))
            saved = page.evaluate("JSON.parse(localStorage.getItem(STORAGE_KEY + '-before-restore'))")
            check("the safety copy holds the old wanted list and colours", [x["name"] for x in saved.get("wishes", [])] == ["Zed Riders"] and saved.get("factionColours") == {"Bright Host": "#112233"}, saved)
            open_settings(page)
            label = page.inner_text("#recover-list")
            check("Recover names the wanted models", "1 Wishlist model" in label, label)
            page.click('#recover-list button[aria-label="Recover: Before Restore backup"]')
            page.wait_for_selector("#dialog-backdrop:not(.hidden)")
            q = page.text_content("#dialog-message")
            check("the Recover question mentions wanted models", "2 Wishlist models" in q or "1 Wishlist model" in q, q)
            page.click("#dialog-yes"); page.wait_for_timeout(700)
            check("Recover brings back wanted models and colours with the units", names(page) == ["Zed Riders"] and colours(page) == {"Bright Host": "#112233"} and page.evaluate("models.map(m => m.name)") == ["Squad"], (names(page), colours(page)))
            page.click("#toast-undo"); page.wait_for_timeout(500)
            check("Undo puts the wanted list and colours back as they were", names(page) == ["Old Guard"] and colours(page) == {"Dark Host": "#445566"}, (names(page), colours(page)))
            check("no sideways scroll", page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
            ctx.close()

        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: d.dismiss())

        print("\n--- 2. An old safety copy ---")
        t.load(page, units=[UNIT], settings=BASE)
        page.evaluate("localStorage.setItem(STORAGE_KEY + '-before-delete-all', JSON.stringify({date: todayISO(), stages: STAGES, doneFrom: settings.doneFrom, models: [" + json.dumps(UNIT2) + "]}))")
        open_settings(page)
        page.click('#recover-list button[aria-label="Recover: Before Delete all units"]')
        page.wait_for_selector("#dialog-backdrop:not(.hidden)")
        q = page.text_content("#dialog-message"); page.click("#dialog-yes"); page.wait_for_timeout(700)
        check("an old copy recovers its units and leaves your wanted list alone", page.evaluate("models.map(m => m.name)") == ["Riders"] and names(page) == ["Zed Riders"] and "Wishlist" not in q, (q, names(page)))

        print("\n--- 3. A backup with wanted models and no units ---")
        t.load(page, units=[UNIT], settings=BASE)
        open_settings(page)
        q = restore(page, {"app": "Minifolio", "dataVersion": 2, "models": [], "modelWishes": [WISH2]})
        check("the question is about wanted models and leaves units and recipes", q.startswith("Replace your 1 Wishlist model with 1 Wishlist model") and "units and recipes stay" in q, q)
        check("the wanted list was replaced and the units stayed", names(page) == ["Old Guard"] and page.evaluate("models.map(m => m.name)") == ["Squad"], names(page))
        check("the copy before it holds the old wanted list", page.evaluate("JSON.parse(localStorage.getItem(STORAGE_KEY + '-before-restore')).wishes.map(w => w.name)") == ["Zed Riders"])
        page.click("#toast-undo"); page.wait_for_timeout(500)
        check("Undo brings the old wanted list back", names(page) == ["Zed Riders"], names(page))
        page.set_input_files("#restore-file", files=[backup({"app": "Minifolio", "dataVersion": 2, "models": [], "modelWishes": []})])
        page.wait_for_timeout(500)
        check("a backup with nothing at all is still refused", "no units, recipes or Wishlist models" in page.inner_text("#toast"), page.inner_text("#toast"))

        print("\n--- 4. Save a backup? notices wanted models ---")
        t.load(page, units=[UNIT], settings={**BASE, "modelWishes": []})
        a = page.evaluate("dataPrint()")
        b = page.evaluate("settings.modelWishes = []; dataPrint()")
        c = page.evaluate("settings.modelWishes = [" + json.dumps(WISH) + "]; dataPrint()")
        d = page.evaluate("settings.modelWishes[0].note = 'x'; dataPrint()")
        check("no wanted models: the print is the units and recipes only, as before", a == b and a == page.evaluate("(settings.modelWishes = [], dataPrint())"), (a, b))
        check("adding a wanted model changes the print", a != c, (a, c))
        check("editing one changes it again", c != d, (c, d))

        print("\n--- 5. Editing a wanted model after another window changed the list ---")
        t.load(page, units=[UNIT], settings=BASE)
        page.click('nav button[data-tab="units"]'); t.quiet(page)
        page.click('#models-seg button[data-mview="wishes"]'); t.quiet(page)
        page.click("#wish-list >> text=Zed Riders"); t.quiet(page)
        page.evaluate("settings.modelWishes = JSON.parse(JSON.stringify(settings.modelWishes))")   # what loadFromOtherWindow does: new objects
        page.fill(".w-count", "9"); page.click('#wish-form-slot button[type="submit"]'); t.quiet(page)
        check("the edit is in the list now in use, not lost", page.evaluate("wishes()[0].count") == 9, page.evaluate("wishes()[0].count"))
        check("and it was saved", page.evaluate("JSON.parse(localStorage.getItem(SETTINGS_KEY)).modelWishes[0].count") == 9)
        page.click("#wish-list >> text=Zed Riders"); t.quiet(page)
        page.evaluate("settings.modelWishes = []")   # removed in another window
        page.fill(".w-count", "4"); page.click('#wish-form-slot button[type="submit"]'); t.quiet(page)
        check("a wanted model removed elsewhere is not brought back, and the message says so", page.evaluate("wishes().length") == 0 and "removed in another window" in page.inner_text("#toast"), page.inner_text("#toast"))

        print("\n--- 6. Damaged settings copy ---")
        t.load(page, units=[UNIT], settings=BASE)
        page.evaluate("localStorage.setItem(SETTINGS_KEY, '{not json'); sessionStorage.clear()")
        page.reload(); page.wait_for_timeout(800)
        page.evaluate("document.getElementById('launch') && 0")
        has = page.evaluate("localStorage.getItem(SETTINGS_KEY + '-unreadable')")
        check("the damaged settings were kept", has == "{not json", has)
        open_settings(page)
        row = page.inner_text("#recover-list")
        check("Recover lists the unreadable settings with a way to save them", "Unreadable settings" in row and page.is_visible('#recover-list button[aria-label="Save as file: Unreadable settings"]'), row)
        page.evaluate("settings.unreadableDates = {...settings.unreadableDates, [SETTINGS_KEY]: '2020-01-01'}; saveSettings()")
        page.reload(); page.wait_for_timeout(800)
        check("after 30 days the copy is removed", page.evaluate("localStorage.getItem(SETTINGS_KEY + '-unreadable')") is None)
        ctx.close()
        browser.close()
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

main()
