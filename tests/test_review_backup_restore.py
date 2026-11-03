"""Testing review (T6): Save full backup with photos, then Restore backup on an emptied device, gives back the same data.

How it works: three made-up units (one with a photo and a diary, two linked to recipes), two recipes with paints, and
settings a backup carries (a custom stage list and Done marker, a faction colour, a stage colour set, Appearance, Theme,
switched-off paint brands, custom stage colours) are saved, and one small JPEG photo is put in the photo store. "Save full
backup with photos" is pressed in Settings. Then everything on the device is cleared (saved data and the photo store), the
app opens fresh, and the downloaded file is picked with Restore backup. Checks:
1. The backup file holds the units, the recipes, the settings and the photo as the same picture text.
2. The emptied device really has no units of ours and no photo before the restore.
3. Restore asks first, naming the units, recipes and the photo, and says Backup restored.
4. Units (with the photo note, diary and recipe links) and the recipe book come back exactly the same.
5. Every setting the backup carries comes back.
6. The photo comes back with the same picture and thumbnail (byte for byte) and shows on the unit's card.
7. All of it is still there after a reload.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_v31 as t   # book(), rec() and unit(): the made-up paints, recipes and units older tests use
from launch_helpers import app_ready, leave_launch, open_settings, quiet, tap_tab

PORT = os.environ.get("SOG_PORT", "8000")
BASE = f"http://localhost:{PORT}"
URL = f"{BASE}/index.html"
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "screenshots")
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

PHOTO_ID = "p-review-photo"
STAGES = ["Bare", "Built", "Primed", "Painted", "Based"]
RECIPES = [t.rec(101, "Armour blue", "Whole model", [1, 22]), t.rec(102, "Orange trim", "Armour", [2])]
UNITS = [dict(t.unit(1, "Troop A", "Gloom Legion", [101]), stage=3, nickname="Blue boys", note="Photo taken outside",
              added="2026-09-01", log=[["2026-09-01", 0], ["2026-10-01", 3]],
              photos=[{"id": PHOTO_ID, "date": "2026-10-01", "stage": 3}], coverPhoto=PHOTO_ID),
         dict(t.unit(2, "Walker", "Gloom Legion", [101, 102]), stage=4, count=1, repaint=True, added="2026-08-15",
              log=[["2026-08-15", 1], ["2026-09-20", 4]]),
         dict(t.unit(3, "Scout", "Other Host"), stage=0, count=3, added="2026-10-02", log=[["2026-10-02", 0]])]
CUSTOM = ["#112233", "#445566", "#778899", "#aabbcc", "#ddeeff"]
SETTINGS = {"examplesChecked": True, "recipeExamplesChecked": True, "tab": "settings", "stages": STAGES, "doneFrom": 3,
            "factionColours": {"Gloom Legion": "#336699"}, "palette": "forge", "appearance": "light", "theme": "parchment",
            "brandsOff": ["Vallejo"], "useCustom": True, "customColours": CUSTOM}
CARRIED = ["stages", "doneFrom", "factionColours", "palette", "appearance", "theme", "brandsOff", "useCustom", "customColours"]

# On a page of the same site with no app running: empty the saved data and the photo store, and (seed=True) put one
# small JPEG photo and its thumbnail in the store, made the way a phone camera picture would be (a JPEG blob).
CLEAR_AND_SEED = """async (seed) => {
    localStorage.clear();
    const gone = await new Promise(done => { const r = indexedDB.deleteDatabase('shades-of-grey-photos');
        r.onsuccess = () => done('deleted'); r.onerror = () => done('error'); r.onblocked = () => done('blocked'); });
    if (!seed) return { gone };
    const jpeg = async (w, h) => { const c = new OffscreenCanvas(w, h), g = c.getContext('2d');
        g.fillStyle = '#2050c0'; g.fillRect(0, 0, w, h); g.fillStyle = '#f0c040'; g.fillRect(w / 4, h / 4, w / 2, h / 2);
        return c.convertToBlob({ type: 'image/jpeg', quality: 0.8 }); };
    const full = await jpeg(48, 32), thumb = await jpeg(24, 16);
    const db = await new Promise((ok, bad) => { const r = indexedDB.open('shades-of-grey-photos', 1);
        r.onupgradeneeded = () => r.result.createObjectStore('photos', { keyPath: 'id' }); r.onsuccess = () => ok(r.result); r.onerror = () => bad(r.error); });
    await new Promise((ok, bad) => { const tx = db.transaction('photos', 'readwrite');
        tx.objectStore('photos').put({ id: '%s', full, thumb }); tx.oncomplete = ok; tx.onerror = () => bad(tx.error); });
    db.close();
    return { gone };
}""" % PHOTO_ID

PHOTO_TEXT = """async (id) => { const r = await getPhoto(id); return r ? { full: await blobToDataUrl(r.full), thumb: await blobToDataUrl(r.thumb) } : null; }"""
STATE = """() => ({ models: JSON.stringify(models), book: JSON.stringify(book), stages: STAGES.slice(),
    settings: Object.fromEntries(%s.map(k => [k, settings[k]])) })""" % json.dumps(CARRIED)

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

        # Seed, then open the app.
        page.goto(f"{BASE}/manifest.json")
        page.evaluate(CLEAR_AND_SEED, True)
        page.evaluate("""([u, b, s]) => { localStorage.setItem('mini-tracker-models', JSON.stringify(u));
            localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b)); localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }""",
                      [UNITS, t.book(recipes=RECIPES), SETTINGS])
        page.goto(URL)
        app_ready(page)
        leave_launch(page)
        page.wait_for_function("() => thumbUrls.has('%s')" % PHOTO_ID)   # the photo was found in the store on start-up
        before = page.evaluate(STATE)
        photo_before = page.evaluate(PHOTO_TEXT, PHOTO_ID)
        check("the seed loaded: 3 units with the photo note, 2 recipes, the settings",
              len(json.loads(before["models"])) == 3 and json.loads(before["models"])[0].get("photos") and len(json.loads(before["book"])["recipes"]) == 2
              and before["stages"] == STAGES and before["settings"]["theme"] == "parchment" and photo_before
              and photo_before["full"].startswith("data:image/jpeg;base64,"), [before, photo_before and photo_before["full"][:40]])

        print("--- 1. Save full backup with photos ---")
        with page.expect_download() as dl:
            page.click("#full-export-button")
        path = dl.value.path()
        with open(path, encoding="utf-8") as f:
            saved = json.load(f)
        check("the file holds the 3 units and 2 recipes", len(saved.get("models", [])) == 3 and len(saved.get("recipes", {}).get("recipes", [])) == 2,
              [len(saved.get("models", [])), list(saved)])
        check("…the settings a backup carries",
              saved.get("stages") == STAGES and saved.get("doneFrom") == 3 and saved.get("theme") == "parchment" and saved.get("palette") == "forge"
              and saved.get("appearance") == "light" and saved.get("useCustom") is True and saved.get("brandsOff") == ["Vallejo"],
              {k: saved.get(k) for k in ["stages", "doneFrom", "theme", "palette", "appearance", "useCustom", "brandsOff"]})
        check("…and the photo, as the same picture and thumbnail text", saved.get("photoFiles", {}).get(PHOTO_ID) == photo_before,
              list(saved.get("photoFiles", {})))

        print("\n--- 2. Clear everything, open the app fresh ---")
        page.goto(f"{BASE}/manifest.json")
        cleared = page.evaluate(CLEAR_AND_SEED, False)
        check("the photo store is deleted (nothing holds it open)", cleared["gone"] == "deleted", cleared)
        page.goto(URL)
        app_ready(page)
        leave_launch(page)
        fresh = page.evaluate("""async (id) => ({ names: models.map(m => m.name), photo: !!(await getPhoto(id)), stages: STAGES.slice(),
            theme: settings.theme || 'classic', palette: settings.palette, custom: settings.useCustom === true })""", PHOTO_ID)
        check("the fresh app has none of our units, no photo, the default stages and none of our look",
              not {"Troop A", "Walker", "Scout"} & set(fresh["names"]) and not fresh["photo"] and fresh["stages"] != STAGES
              and fresh["theme"] != "parchment" and fresh["palette"] != "forge" and not fresh["custom"], fresh)

        print("\n--- 3. Restore backup ---")
        open_settings(page)
        with page.expect_file_chooser() as fc:
            page.click("#restore-button")
        fc.value.set_files(path)
        page.wait_for_selector("#dialog-yes", state="visible")
        question = page.text_content("#dialog-backdrop")
        check("Restore asks first, naming 3 units, 2 recipes and 1 photo",
              "with 3 units and 2 recipes from the backup" in question and "It includes 1 photo." in question, question)
        page.click("#dialog-yes")
        page.wait_for_function("() => document.getElementById('toast-text').textContent.startsWith('Backup restored')")
        check("…and says Backup restored", page.text_content("#toast-text") == "Backup restored", page.text_content("#toast-text"))
        after = page.evaluate(STATE)

        print("\n--- 4. and 5. The same data ---")
        check("the units come back exactly (photo note, diary, recipe links, nickname, notes)", after["models"] == before["models"],
              [before["models"], after["models"]])
        check("the recipe book comes back exactly", after["book"] == before["book"], [before["book"][:300], after["book"][:300]])
        check("the stage list is back in use", after["stages"] == STAGES, after["stages"])
        diffs = {k: [before["settings"][k], after["settings"][k]] for k in CARRIED if before["settings"][k] != after["settings"][k]}
        check("every setting a backup carries is back (Done marker, faction colour, colour set, Appearance, Theme, brands, custom colours)",
              not diffs, diffs)

        print("\n--- 6. The photo ---")
        photo_after = page.evaluate(PHOTO_TEXT, PHOTO_ID)
        check("the photo is back in the store with the same picture, byte for byte", photo_after and photo_after["full"] == photo_before["full"],
              photo_after and photo_after["full"][:60])
        check("…and the same thumbnail", photo_after and photo_after["thumb"] == photo_before["thumb"], photo_after and photo_after["thumb"][:60])
        tap_tab(page, "units")
        quiet(page)
        page.wait_for_function("() => { const i = document.querySelector('li.unit[data-id=\"1\"] img'); return i && i.complete && i.naturalWidth > 0; }")
        width = page.evaluate("() => document.querySelector('li.unit[data-id=\"1\"] img').naturalWidth")
        check("…and it shows on the unit's card (the 24 px wide thumbnail)", width == 24, width)
        page.screenshot(path=os.path.join(SHOTS, "review_backup_restore_units.png"))

        page.reload()
        app_ready(page)
        again = page.evaluate(STATE)
        photo_again = page.evaluate(PHOTO_TEXT, PHOTO_ID)
        check("after a reload the restored units, recipes, settings and photo are all still there (they were saved)",
              again == after and photo_again == photo_before, [k for k in after if again.get(k) != after[k]])
        browser.close()

    check("no browser pop-ups", not dialogs, dialogs)
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
