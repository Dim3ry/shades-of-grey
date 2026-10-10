"""v19 tests for Minifolio: navigation (Back button), army-list paste on the Units tab, Privacy.

(This is the first half of the v19 plan, called "v19a" in the notes. App version: v19.)

Checks:
1. Version numbers, the Updates entry, CNAME and the ocr folder kept, storage names unchanged.
2. Back button: each press closes ONE open thing (photo viewer, scan panel, a recipe, a recipe
   being written (asking first if it has changes), Paste recipes, a scheme, the Units import box),
   then goes to the Dashboard; on the Dashboard with nothing open there's no spare back step,
   so Back leaves the app as normal. Closing something yourself removes the spare step.
3. Army list on the Units tab: + Add unit has Paste army list and Import CSV; an empty Units list
   has them too; an import (from Units OR Settings) ends on the Units tab; Settings still works.
4. Help: Privacy topic, Back button note, Getting started and Importing point to the new buttons.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

PORT = os.environ.get("SOG_PORT", "8765")
BASE = f"http://localhost:{PORT}/"
URL = BASE + "index.html"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "screenshots")
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()

BOOK = {
    "paints": [{"id": 1, "brand": "Citadel", "name": "Macragge Blue", "colour": "#1f3a8a"}],
    "recipes": [{"id": 1, "name": "Blue armour", "part": "Armour", "notes": "",
                 "steps": [{"technique": "Base coat", "coats": 1, "paints": [{"paint": 1, "mix": None}]}]}],
    "schemes": [],
}
UNIT = [{"id": 1, "name": "Intercessors", "hobby": "40K", "faction": "Ultramarines", "stage": 0, "count": 5,
         "photos": [{"id": "p1", "stage": 0, "date": "2026-10-01"}]}]

# The photo file isn't stored in these tests, so the photo is put straight into the unit in memory.
OPEN_VIEWER = ("models[0].photos = [{ id: 'p1', stage: 0, date: '2026-10-01' }]; thumbUrls.set('p1', 'data:,');"
               " openLightbox(models[0].id, 'p1'); syncBackStep();")

def seed(page, units=None, book=None, tab="dashboard"):
    page.goto(URL)
    page.evaluate("""([u, b, tab]) => { localStorage.clear();
        localStorage.setItem('mini-tracker-models', JSON.stringify(u || []));
        if (b) localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b));
        const s = JSON.parse(localStorage.getItem('shades-of-grey-settings') || '{}'); }""", [units, book, tab])
    page.reload()
    page.wait_for_timeout(300)

def tab(page, name):
    page.click(f'nav button[data-tab="{name}"]')
    page.wait_for_timeout(80)

def back(page):
    page.evaluate("history.back()")
    page.wait_for_timeout(250)

def current_tab(page):
    return page.evaluate("settings.tab")

def has_step(page):
    return page.evaluate("!!(history.state && history.state.minifolio === 'back')")

def stored_units(page):
    return json.loads(page.evaluate("localStorage.getItem('mini-tracker-models') || '[]'"))

def main():
    sw = read("sw.js")
    html = read("index.html")
    export = open(os.path.join(HERE, "real_40k_tyranids.txt"), encoding="utf-8").read()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        dialogs = []
        answer = {"accept": True}
        def on_dialog(d):
            dialogs.append(d.message)
            d.accept() if answer["accept"] else d.dismiss()
        page.on("dialog", on_dialog)

        # ---------- 1. Versions and kept things ----------
        print("--- 1. Versions and kept things ---")
        seed(page)
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v19 or later", float(version[1:]) >= 19, version)
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        check("sw.js VERSION matches APP_VERSION", m and m.group(1) == version, m and m.group(1))
        tab(page, "updates")
        heads = page.locator("#changelog h3").all_inner_texts()
        v19 = [i for i, h in enumerate(heads) if h.startswith("v19")]
        check("the Updates tab has a v19 entry", bool(v19), heads[:3])
        if v19:
            text = page.locator("#changelog .release").nth(v19[-1]).inner_text()
            check("the v19 entry mentions Back, Paste army list and Privacy",
                  "Back" in text and "Paste army list" in text and "Privacy" in text, text)
        check("CNAME file kept (minifolio.app)", read("CNAME").strip() == "minifolio.app")
        check("ocr folder kept", all(os.path.exists(os.path.join(ROOT, "ocr", f)) for f in
                                     ["ocr-worker.js", "eng.traineddata", "tesseract-core-simd-lstm.wasm"]))
        for key in ['STORAGE_KEY = "mini-tracker-models"', 'SETTINGS_KEY = "shades-of-grey-settings"',
                    'RECIPES_KEY = "shades-of-grey-recipes"', "shades-of-grey-recipes-before-recipes-restore"]:
            check(f"storage name kept: {key}", key in html)
        check("DATA_VERSION unchanged (saved data didn't change shape)", page.evaluate("DATA_VERSION") == 1)

        # ---------- 2. Back button ----------
        print("--- 2. Back button ---")
        seed(page, UNIT, BOOK)
        start_url = page.url
        check("on the Dashboard with nothing open there's no back step", not has_step(page))
        tab(page, "units")
        check("going to Units adds a back step", has_step(page))
        length = page.evaluate("history.length")
        tab(page, "settings")
        tab(page, "help")
        check("switching between other tabs doesn't pile up steps", page.evaluate("history.length") == length,
              page.evaluate("history.length"))
        back(page)
        check("Back from Help goes to the Dashboard", current_tab(page) == "dashboard", current_tab(page))
        check("…and the app is still open at the same address", page.url == start_url and page.is_visible("#view-dashboard"))
        check("…with no spare step left, so the next Back leaves the app", not has_step(page))

        # Tab bar to Dashboard yourself: the spare step goes too.
        tab(page, "units")
        tab(page, "dashboard")
        check("tapping Dashboard yourself removes the spare step", not has_step(page))

        # Photo viewer (opened directly; the photo file itself isn't needed for this check).
        tab(page, "units")
        page.evaluate(OPEN_VIEWER)
        page.wait_for_timeout(100)
        check("the photo viewer is open", page.is_visible("#viewer"))
        back(page)
        check("Back closes the photo viewer", not page.is_visible("#viewer"))
        check("…and stays on Units", current_tab(page) == "units", current_tab(page))
        check("…and still has a step for Units", has_step(page))
        back(page)
        check("the next Back goes to the Dashboard", current_tab(page) == "dashboard")

        # Viewer closed with ✕ on the Dashboard: no dead Back press left behind.
        page.evaluate(OPEN_VIEWER)
        page.wait_for_timeout(100)
        check("viewer open on the Dashboard has a step", has_step(page))
        page.click("#viewer-close")
        page.wait_for_timeout(250)
        check("closing the viewer with ✕ removes the spare step", not has_step(page) and current_tab(page) == "dashboard")

        # A recipe being read.
        tab(page, "recipes")
        page.evaluate("settings.recipeView = 'recipes'; renderRecipes();")
        page.click("#recipe-list .recipe-item")
        page.wait_for_timeout(100)
        check("a recipe is open", page.is_visible("#recipe-page"))
        back(page)
        check("Back closes the recipe and shows the recipe list", not page.is_visible("#recipe-page") and page.is_visible("#recipe-list"))
        check("…still on Recipes", current_tab(page) == "recipes")
        back(page)
        check("the next Back goes to the Dashboard", current_tab(page) == "dashboard")

        # A recipe being written, with a change: Back asks first.
        tab(page, "recipes")
        page.click("#new-recipe")
        page.wait_for_timeout(100)
        page.locator("#recipe-page input").first.fill("Half-written recipe")
        page.wait_for_timeout(100)
        answer["accept"] = False
        dialogs.clear()
        back(page)
        check("Back on a changed recipe asks before leaving", any("Discard" in d for d in dialogs), dialogs)
        check("…saying No keeps the recipe open", page.evaluate("!!recipeDraft") and page.is_visible("#recipe-page"))
        check("…and Back is ready again", has_step(page))
        answer["accept"] = True
        back(page)
        check("…saying Yes closes it", not page.evaluate("!!recipeDraft"))
        tab(page, "dashboard")

        # Paste recipes page.
        tab(page, "recipes")
        page.click("#paste-recipes")
        page.wait_for_timeout(100)
        check("Paste recipes is open", page.is_visible("#import-page"))
        back(page)
        check("Back closes Paste recipes", not page.is_visible("#import-page") and current_tab(page) == "recipes")
        tab(page, "dashboard")

        # A scheme being written.
        tab(page, "recipes")
        page.click('#recipe-seg button[data-view="schemes"]')
        page.click("#new-scheme")
        page.wait_for_timeout(100)
        check("the scheme editor is open", page.evaluate("!!schemeDraft"))
        back(page)
        check("Back closes the scheme editor", not page.evaluate("!!schemeDraft") and current_tab(page) == "recipes")
        tab(page, "dashboard")

        # The scan panel on Your Palette.
        tab(page, "recipes")
        page.click('#recipe-seg button[data-view="palette"]')
        page.click("#scan-button")
        page.wait_for_timeout(100)
        check("the scan panel is open", page.is_visible("#scan-panel"))
        back(page)
        check("Back closes the scan panel", not page.is_visible("#scan-panel") and current_tab(page) == "recipes")
        back(page)
        check("the next Back goes to the Dashboard", current_tab(page) == "dashboard")
        page.click('nav button[data-tab="recipes"]')
        page.click('#recipe-seg button[data-view="recipes"]')
        tab(page, "dashboard")

        # The import box on the Units tab.
        tab(page, "units")
        page.click("#toggle-add")
        page.click("#add-wh")
        page.wait_for_timeout(100)
        check("the Units import box is open", page.is_visible("#units-import"))
        back(page)
        check("Back closes the Units import box", not page.is_visible("#units-import") and current_tab(page) == "units")
        back(page)
        check("the next Back goes to the Dashboard", current_tab(page) == "dashboard")
        check("no page errors during the Back checks", not errors, errors)

        # ---------- 3. Army list on the Units tab ----------
        print("--- 3. Army list on the Units tab ---")
        seed(page, [], None)
        tab(page, "units")
        check("an empty Units list offers Paste army list and Import CSV",
              page.is_visible("#empty-wh") and page.is_visible("#empty-csv"))
        page.click("#toggle-add")
        check("+ Add unit shows Paste army list and Import CSV",
              page.is_visible("#add-wh") and page.is_visible("#add-csv"))
        page.click("#add-wh")
        page.wait_for_timeout(150)
        check("Paste army list opens the paste box on the Units tab",
              page.is_visible("#wh-text") and page.evaluate("document.getElementById('view-units').contains(document.getElementById('wh-text'))"))
        page.screenshot(path=f"{SHOTS}/v19-units-paste.png")
        page.fill("#wh-text", export)
        page.click("#wh-read")
        page.wait_for_timeout(150)
        check("the import check shows on the Units tab", page.is_visible("#review") and current_tab(page) == "units")
        page.screenshot(path=f"{SHOTS}/v19-units-review.png")
        page.click("#review-go")
        page.wait_for_timeout(300)
        units = stored_units(page)
        check("all 17 units from the real export are imported", len(units) == 17, len(units))
        check("after the import the Units tab is showing", current_tab(page) == "units" and page.is_visible("#view-units"))
        check("…the import box and the Add form have closed",
              not page.is_visible("#units-import") and not page.is_visible("#add-form"))
        check("…and the new units are listed", page.locator("#unit-list li.unit").count() == 17,
              page.locator("#unit-list li.unit").count())
        page.screenshot(path=f"{SHOTS}/v19-units-after-import.png")
        page.click("#toast button")
        page.wait_for_timeout(200)
        check("Undo straight after removes the imported units", len(stored_units(page)) == 0, len(stored_units(page)))

        # Empty list button.
        page.click("#empty-wh")
        page.wait_for_timeout(100)
        check("the empty list's Paste army list opens the paste box", page.is_visible("#wh-text") and current_tab(page) == "units")
        page.click("#units-import-close")
        page.wait_for_timeout(100)
        check("Close shuts the Units import box", not page.is_visible("#units-import"))

        # CSV from the Units tab.
        csv_path = os.path.join(SHOTS, "v19-test.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("name,game,faction,stage,nickname,count,repaint,notes\nBoyz,40K,Orks,,,10,no,\nWarboss,40K,Orks,,,1,no,\n")
        page.click("#toggle-add")
        with page.expect_file_chooser() as chooser:
            page.click("#add-csv")
        chooser.value.set_files(csv_path)
        page.wait_for_timeout(300)
        check("Import CSV from Units shows the check on the Units tab",
              page.is_visible("#review") and page.evaluate("document.getElementById('view-units').contains(document.getElementById('review'))"))
        page.click("#review-go")
        page.wait_for_timeout(300)
        names = sorted(u["name"] for u in stored_units(page))
        check("the CSV units are imported", names == ["Boyz", "Warboss"], names)
        check("…and the Units tab is showing", current_tab(page) == "units")

        # Settings still works, and an import there also ends on Units.
        tab(page, "settings")
        page.click("#wh-button")
        page.wait_for_timeout(100)
        check("Settings → Paste an army list opens the paste box in Settings",
              page.is_visible("#wh-text") and page.evaluate("document.getElementById('view-settings').contains(document.getElementById('wh-text'))"))
        check("…the paste box is no longer on the Units tab", not page.evaluate("document.getElementById('view-units').contains(document.getElementById('wh-text'))"))
        page.fill("#wh-text", "Small list (200 points)\n\nOrks\nStrike Force (2000 points)\n\nNobz (100 points)\n  • 5x Nob\n\nExported with App Version: v1.0")
        page.click("#wh-read")
        page.wait_for_timeout(150)
        page.click("#review-go")
        page.wait_for_timeout(300)
        check("an import from Settings also ends on the Units tab", current_tab(page) == "units")
        check("…with the new unit added", any(u["name"] == "Nobz" for u in stored_units(page)))
        check("no page errors during the import checks", not errors, errors)

        # ---------- 4. Help ----------
        print("--- 4. Help ---")
        tab(page, "help")
        page.click("#privacy summary")
        privacy = page.inner_text("#privacy")
        check("Help has a Privacy topic", privacy.startswith("Privacy"), privacy[:40])
        for words in ["Stays on your phone", "What goes out", "No tracking", "Give feedback", "never leaves"]:
            check(f"Privacy says: {words}", words in privacy, privacy)
        page.screenshot(path=f"{SHOTS}/v19-privacy.png")
        page.locator("#view-help summary", has_text="Importing").click()   # open the Importing topic
        help_text = page.inner_text("#view-help")
        check("Getting started points to Paste army list on the Units tab", "Paste army list" in help_text)
        check("Help explains the Back button", page.locator("#help-back").count() == 1 and "Back" in page.inner_text("#help-back"))
        check("Importing says where to find it (+ Add unit → Paste army list)", "+ Add unit → Paste army list" in help_text)
        check("Importing says the Units tab opens after an import", "Units tab opens" in help_text)
        check("no page errors", not errors, errors)

        browser.close()

    passed = sum(results)
    print(f"\n{passed} passed, {len(results) - passed} failed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
