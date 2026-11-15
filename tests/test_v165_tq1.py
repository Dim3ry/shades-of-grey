"""Chunk TQ1 tests for Minifolio: guards for the gaps found in the v164 review (d2, d3, d4). Tests only, no app change.
1. The paint catalogue block of app.js (from the PAINT RECIPES banner to the PAINT-NAME MATCHER banner) matches a recorded
   fingerprint, so an unintended change fails. File check, no page. Update it on purpose with CONTENT_CHANGE_OK=1 (see below).
2. Damaged recipes at start-up (units are fine): the damaged text stays exactly as it was, no examples replace it, saving
   pauses (a change made meanwhile writes nothing), and the banner names the recipes. (DS1's own test only covers damaged units.)
3. One full backup round trip with the newer data: a wanted model, a Gear item, a shopping item (a Wishlist paint), the Models
   sort choice and the Armies view. Save full backup, wipe storage, Restore backup: everything is back, and after a reload too.
The workflow file (.github/workflows/quick-tests.yml) runs the quick set on every pull request; it is not tested here.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import hashlib, json, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_v31 as t   # book(), rec(), unit(), PAINTS: the made-up data older tests use
from launch_helpers import app_ready, leave_launch, open_settings

ROOT = os.path.realpath(os.path.join(HERE, ".."))
BASE = f"http://localhost:{os.environ.get('SOG_PORT', '8000')}"
URL = f"{BASE}/index.html"
FINGERPRINT_FILE = os.path.join(HERE, "paint_catalogue_fingerprint.txt")
START_MARK = "// ================= PAINT RECIPES: THE DATA ================="
END_MARK = "// ================= v16: THE SHARED PAINT-NAME MATCHER ================="
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def catalogue_fingerprint():
    with open(os.path.join(ROOT, "app.js"), encoding="utf-8", newline="") as f:
        text = f.read().replace("\r\n", "\n")
    a, b = text.find(START_MARK), text.find(END_MARK)
    if a < 0 or b < a:
        return None
    return hashlib.sha256(text[a:b].encode("utf-8")).hexdigest()

UNITS_KEY, RECIPES_KEY, SETTINGS_KEY = "mini-tracker-models", "shades-of-grey-recipes", "shades-of-grey-settings"
SETTINGS = {"examplesChecked": True, "recipeExamplesChecked": True, "tab": "settings"}

def seed(page, units, recipes_text, settings):
    page.goto(f"{BASE}/manifest.json")   # a page of the same site with no app running
    page.evaluate("""([u, r, s]) => { localStorage.clear();
        localStorage.setItem('mini-tracker-models', u); localStorage.setItem('shades-of-grey-recipes', r);
        localStorage.setItem('shades-of-grey-settings', s); }""", [json.dumps(units), recipes_text, json.dumps(settings)])
    page.goto(URL)
    app_ready(page)
    leave_launch(page)

def stored(page, key):
    return page.evaluate("k => localStorage.getItem(k)", key)

# ---- the round trip's data ----
WISH = {"id": 7, "name": "Wanted knights", "count": 2, "game": "Test game", "faction": "Gloom Legion", "really": True,
        "note": "for the club night", "added": "2026-10-01"}
GEAR = {"id": "wet palette", "name": "wet palette", "from": "Test guide"}
SORT = {"mode": "stage"}
RT_UNITS = [dict(t.unit(1, "Troop A", "Gloom Legion", [101]), stage=3, added="2026-09-01", log=[["2026-09-01", 0], ["2026-10-01", 3]]),
            dict(t.unit(2, "Walker", "Other Host"), stage=1, count=1, added="2026-08-15", log=[["2026-08-15", 1]])]
RT_PAINTS = [dict(p) for p in t.PAINTS]
RT_PAINTS[2]["status"] = "wishlist"   # a shopping item: a paint on the Wishlist (Vallejo Turquoise)
RT_BOOK = t.book(paints=RT_PAINTS, recipes=[t.rec(101, "Armour blue", "Whole model", [1, 2])])
RT_BOOK["gear"] = [GEAR]
RT_SETTINGS = dict(SETTINGS, modelWishes=[WISH], unitSort=SORT, factionView="doughnuts", stages=["Bare", "Built", "Primed", "Painted", "Based"], doneFrom=3)
STATE = """() => ({ models: JSON.stringify(models), book: JSON.stringify(book),
    wishes: JSON.stringify(settings.modelWishes || []), sort: JSON.stringify(settings.unitSort || null), view: settings.factionView,
    shopping: shoppingItems().map(i => (i.paint && i.paint.name) || i.name || '').filter(Boolean), gear: gearItems().map(g => g.id) })"""

def main():
    # ---------- 1. The paint catalogue is unchanged ----------
    print("--- 1. The paint catalogue block ---")
    now = catalogue_fingerprint()
    recorded = open(FINGERPRINT_FILE, encoding="utf-8").read().strip() if os.path.exists(FINGERPRINT_FILE) else ""
    if os.environ.get("CONTENT_CHANGE_OK") == "1":
        print("SKIP: CONTENT_CHANGE_OK=1, this chunk changes the paint catalogue on purpose. Record the new fingerprint:", now)
    else:
        check("the paint catalogue block in app.js is unchanged (matches tests/paint_catalogue_fingerprint.txt)",
              now is not None and now == recorded,
              "The paint catalogue block in app.js (between the 'PAINT RECIPES: THE DATA' and 'THE SHARED PAINT-NAME MATCHER' banners) "
              "changed. If that is on purpose, run with CONTENT_CHANGE_OK=1, then put this line in tests/paint_catalogue_fingerprint.txt: "
              f"{now}")
    check("the two banners that fence the block are still in app.js", now is not None, "a banner was renamed or moved; update START_MARK or END_MARK")

    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", accept_downloads=True)
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        # ---------- 2. Damaged recipes at start-up ----------
        print("\n--- 2. Damaged recipes at start-up ---")
        good_units = [dict(t.unit(1, "Troop A", "Gloom Legion"), stage=2), dict(t.unit(2, "Walker", "Gloom Legion"), stage=1)]
        damaged = json.dumps(t.book(recipes=[t.rec(i, f"Recipe {i}", "Armour", [1]) for i in range(1, 60)]))[:-1]   # cut off: not valid JSON
        seed(page, good_units, damaged, SETTINGS)
        units_before = stored(page, UNITS_KEY)
        check("damaged recipes: the saved recipe text is left exactly as it was", stored(page, RECIPES_KEY) == damaged)
        check("…the units, which were fine, are still the person's own (not examples)",
              page.evaluate("models.map(m => m.name)") == ["Troop A", "Walker"], page.evaluate("models.map(m => m.name)"))
        banner_text = page.text_content("#save-banner-text")
        check("…the banner shows and says the recipes couldn't be read, with Save it as a file and Start again",
              page.is_visible("#save-banner") and "recipes couldn't be read" in banner_text and "units" not in banner_text
              and page.text_content("#banner-backup") == "Save it as a file" and page.text_content("#banner-retry") == "Start again", banner_text)
        page.evaluate("() => { models.push({ id: 9, name: 'New unit', stage: 0, count: 1, hobby: '', faction: '' }); render(); }")
        check("…saving is paused: a change made meanwhile writes nothing (recipes and units stay as they were)",
              stored(page, RECIPES_KEY) == damaged and stored(page, UNITS_KEY) == units_before)

        # ---------- 3. A full backup round trip with the newer data ----------
        print("\n--- 3. Full backup round trip: wanted model, Gear, shopping item, sort, Armies view ---")
        seed(page, RT_UNITS, json.dumps(RT_BOOK), RT_SETTINGS)
        before = page.evaluate(STATE)
        check("the seed loaded: a wanted model, a Gear item, a shopping item, the sort and the Armies view",
              json.loads(before["wishes"])[0]["name"] == "Wanted knights" and before["gear"] == ["wet palette"]
              and "Turquoise" in before["shopping"] and json.loads(before["sort"]) == SORT and before["view"] == "doughnuts", before)
        with page.expect_download() as dl:
            page.click("#full-export-button")
        with open(dl.value.path(), encoding="utf-8") as f:
            saved = json.load(f)
        check("the backup file carries the wish, the sort and the view (Gear and the shopping item ride in the recipe book)",
              saved.get("modelWishes", [{}])[0].get("name") == "Wanted knights" and saved.get("unitSort") == SORT
              and saved.get("factionView") == "doughnuts" and saved["recipes"].get("gear") == [GEAR], {k: saved.get(k) for k in ("modelWishes", "unitSort", "factionView")})

        page.goto(f"{BASE}/manifest.json")
        page.evaluate("() => localStorage.clear()")   # wipe storage
        page.goto(URL)
        app_ready(page)
        leave_launch(page)
        fresh = page.evaluate(STATE)
        check("the wiped app has none of it back yet (no wish, no Gear, rows view)",
              json.loads(fresh["wishes"]) == [] and fresh["gear"] == [] and fresh["view"] != "doughnuts", fresh)

        open_settings(page)
        with page.expect_file_chooser() as fc:
            page.click("#restore-button")
        fc.value.set_files(dl.value.path())
        page.wait_for_selector("#dialog-yes", state="visible")
        page.click("#dialog-yes")
        page.wait_for_function("() => document.getElementById('toast-text').textContent.startsWith('Backup restored')")
        after = page.evaluate(STATE)
        check("after Restore: the units and the recipe book (with Gear and the Wishlist paint) are exactly as before",
              after["models"] == before["models"] and after["book"] == before["book"], [k for k in ("models", "book") if after[k] != before[k]])
        check("…the wanted model is back", after["wishes"] == before["wishes"], after["wishes"])
        check("…the Gear item and the shopping item are on the list again", after["gear"] == ["wet palette"] and "Turquoise" in after["shopping"], after)
        check("…the sort choice and the Armies view are back", after["sort"] == before["sort"] and after["view"] == "doughnuts", [after["sort"], after["view"]])
        page.reload()
        app_ready(page)
        again = page.evaluate(STATE)
        check("after a reload all of it is still there (it was saved)", again == after, [k for k in after if again[k] != after[k]])
        browser.close()

    check("no browser pop-ups", not dialogs, dialogs)
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
