"""Chunk DV3 tests for Minifolio: Gear protected from older open copies, and the last Undo fixes. New behaviour only.
1. An older open copy (data version 2) stops saving and shows its Reload banner once this copy has saved data at the new number,
   so it cannot save the recipe book without Gear. Going up changes no data. A version 2 backup still restores.
2. Delete recipe and "Palette updated" Undo by difference: a change made after the delete / update is kept by Undo.
3. Delete recipe, delete scheme, apply scheme and cover photo say "Not saved" when the save fails (they used to say success).
4. Phone sizes (390 and 360 wide, dark and light): the Not saved message fits and its button is 44 px or taller.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from launch_helpers import app_ready, leave_launch, quiet
import version_helpers as vh

PORT = os.environ.get("SOG_PORT", "8765")
URL = f"http://localhost:{PORT}/index.html"
ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

UNITS_KEY, BOOK_KEY, SETTINGS_KEY = "mini-tracker-models", "shades-of-grey-recipes", "shades-of-grey-settings"

def paint(i, name, status="owned"):
    return {"id": i, "brand": "Vallejo", "name": name, "colour": "#3b6fb0", "status": status}

def step(paint_id):
    return {"technique": "", "coats": 1, "paints": [{"paint": paint_id, "mix": 100}], "ratio": "", "note": "", "optional": False}

def make_book():
    return {"v15": True, "parts": ["Whole model", "Armour"], "techniques": ["Layer"],
            "paints": [paint(1, "Blue One"), paint(2, "Red Two"), paint(3, "Green Three")],
            "recipes": [{"id": 1, "name": "Armour blue", "steps": [step(1)]},
                        {"id": 2, "name": "Trim red", "steps": [step(2)]},
                        {"id": 3, "name": "Base green", "steps": [step(3)]}],
            "schemes": [{"id": 1, "name": "Blue squad", "faction": "Guard", "recipes": [1, 2]}],
            "shorthand": {}, "gear": [{"id": "g1", "name": "Wet palette"}, {"id": "g2", "name": "Size 1 brush"}]}

UNITS = [{"id": 1, "name": "Squad", "hobby": "", "faction": "Guard", "stage": 0, "count": 5, "recipes": [1, 2]},
         {"id": 2, "name": "Tank", "hobby": "", "faction": "Guard", "stage": 0, "count": 1}]

def start(page, settings=None, book=None, units=None):
    page.goto(URL)
    page.evaluate("""([b, u, s]) => { localStorage.clear();
        localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b));
        localStorage.setItem('mini-tracker-models', JSON.stringify(u));
        localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }""",
                  [book or make_book(), units or UNITS,
                   settings or {"examplesChecked": True, "recipeExamplesChecked": True, "tab": "units"}])
    page.reload()
    app_ready(page)
    leave_launch(page)

def stored(page, key):
    return json.loads(page.evaluate("k => localStorage.getItem(k)", key) or "null")

def toast(page):
    return page.inner_text("#toast-text") if page.is_visible("#toast") else ""

def fill_up(page):
    """From now on every write to storage fails, as if it were full."""
    page.evaluate("""() => { Storage.prototype.setItem = function () {
        const e = new Error('full'); e.name = 'QuotaExceededError'; e.code = 22; throw e; }; }""")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", accept_downloads=True)
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        popups = []
        page.on("dialog", lambda d: (popups.append(d.message), d.dismiss()))

        # ---------- 1. Older open copy, migration, restore ----------
        print("\n--- 1. Older open copy ---")
        old_settings = {"examplesChecked": True, "recipeExamplesChecked": True, "tab": "units", "dataVersion": 2}
        start(page, settings=old_settings)
        s = stored(page, SETTINGS_KEY)
        check("a device saved at version 2 is moved to version 3", s["dataVersion"] == 3, s.get("dataVersion"))
        b = stored(page, BOOK_KEY)
        check("…and moving up changes no data (Gear, recipes, schemes, units as they were)",
              [g["name"] for g in b["gear"]] == ["Wet palette", "Size 1 brush"] and [r["name"] for r in b["recipes"]] == ["Armour blue", "Trim red", "Base green"]
              and b["schemes"][0]["name"] == "Blue squad" and [u["name"] for u in stored(page, UNITS_KEY)] == ["Squad", "Tank"], b)

        # A real older copy: the same app with the number it had before (2), in a second window on the same device.
        old_js = vh.app_js_with_data_version(2)
        page2 = ctx.new_page()
        page2.on("dialog", lambda d: d.dismiss())
        page2.route(re.compile(r".*/app\.js(\?.*)?$"), lambda route: route.fulfill(
            status=200, content_type="application/javascript", body=old_js))
        page2.goto(URL)
        app_ready(page2)
        leave_launch(page2)
        before_book, before_units = page2.evaluate("localStorage.getItem('%s')" % BOOK_KEY), page2.evaluate("localStorage.getItem('%s')" % UNITS_KEY)
        check("the older copy really is the older one", page2.evaluate("backupData().dataVersion") == 2)
        check("…it shows the Reload banner at once", page2.is_visible("#save-banner") and page2.inner_text("#banner-retry") == "Reload",
              page2.inner_text("#save-banner") if page2.is_visible("#save-banner") else "no banner")
        saved = page2.evaluate("""() => { models[0].name = 'Changed by old copy'; book.gear = []; return saveAll(); }""")
        check("…and refuses to save, so the recipe book keeps its Gear",
              saved is False and page2.evaluate("localStorage.getItem('%s')" % BOOK_KEY) == before_book
              and page2.evaluate("localStorage.getItem('%s')" % UNITS_KEY) == before_units
              and [g["name"] for g in stored(page2, BOOK_KEY)["gear"]] == ["Wet palette", "Size 1 brush"])
        check("…the stored version stays at 3", stored(page2, SETTINGS_KEY)["dataVersion"] == 3)
        page2.close()

        # A version 2 backup still restores into this copy.
        backup = {"app": "Minifolio", "version": 6, "dataVersion": 2, "models": [{"id": 7, "name": "From backup", "stage": 0}],
                  "recipes": make_book()}
        page.set_input_files("#restore-file", files=[{"name": "old.json", "mimeType": "application/json", "buffer": json.dumps(backup).encode()}])
        page.wait_for_selector("#dialog-yes", state="visible")
        page.click("#dialog-yes")
        page.wait_for_timeout(500)
        check("a version 2 backup still restores", [u["name"] for u in stored(page, UNITS_KEY)] == ["From backup"], stored(page, UNITS_KEY))
        check("…and the device is stamped 3 again", stored(page, SETTINGS_KEY)["dataVersion"] == 3)

        # ---------- 2. Undo by difference ----------
        print("\n--- 2. Undo by difference ---")
        start(page)
        page.evaluate("() => deleteRecipeNow(1)")
        check("delete recipe: the recipe goes and the Undo message shows",
              page.evaluate("book.recipes.map(r => r.id)") == [2, 3] and "Deleted Armour blue" in toast(page), toast(page))
        page.evaluate("() => { recipeById(3).name = 'Base green EDITED'; render(); }")   # a later change to another recipe
        page.click("#toast-undo")
        quiet(page)
        r = page.evaluate("() => ({ names: book.recipes.map(r => r.name), links: models[0].recipes, scheme: book.schemes[0].recipes })")
        check("delete recipe Undo brings the recipe back where it was", r["names"][0] == "Armour blue" and len(r["names"]) == 3, r)
        check("…keeps the later change to another recipe", "Base green EDITED" in r["names"], r)
        check("…and puts back the unit link and the scheme link", sorted(r["links"]) == [1, 2] and r["scheme"] == [1, 2], r)
        check("…and the undone book is what is saved", [x["name"] for x in stored(page, BOOK_KEY)["recipes"]] == r["names"])

        start(page)
        page.evaluate("""() => { openOwnSheet([paintById(1), paintById(2)]); }""")
        page.locator(".own-sheet-row").nth(0).locator(".pick-tick").click()   # untick Blue One (owned)
        page.click("#dialog-yes")
        quiet(page)
        check("Palette updated: the status change is made", page.evaluate("paintById(1).status") != "owned"
              and "Palette updated" in toast(page), toast(page))
        page.evaluate("() => { paintById(3).status = 'wishlist'; render(); }")   # a later change to another paint
        page.click("#toast-undo")
        quiet(page)
        r = page.evaluate("() => [paintById(1).status, paintById(3).status]")
        check("…Undo puts the first paint back to owned", r[0] == "owned", r)
        check("…and keeps the later change to the other paint", r[1] == "wishlist", r)

        # ---------- 3. Not saved ----------
        print("\n--- 3. Not saved when the save fails ---")
        cases = [
            ("delete recipe", "() => deleteRecipeNow(2)", "Deleted Trim red"),
            ("delete scheme", "() => deleteSchemeNow(1)", "Deleted Blue squad"),
            ("apply scheme", "() => applyScheme(book.schemes[0], [models[1]])", "Blue squad applied"),
            ("cover photo", "() => setCoverPhoto(models[0], 'p1')", "Cover photo set"),
        ]
        for label, call, success in cases:
            start(page)
            fill_up(page)
            page.evaluate(call)
            quiet(page)
            text = toast(page)
            check(f"{label}: a failed save says Not saved", text.startswith("Not saved") and success not in text, text)
            check(f"{label}: …and shows the red banner", page.is_visible("#save-banner"))
        # and when it saves, they still say what they did
        start(page)
        page.evaluate("() => applyScheme(book.schemes[0], [models[1]])")
        quiet(page)
        check("apply scheme: a good save still says so, and Undo works",
              "Blue squad applied to 1 unit" in toast(page) and page.evaluate("models[1].recipes") == [1, 2], toast(page))
        page.click("#toast-undo")
        quiet(page)
        check("…Undo takes the links off again", page.evaluate("models[1].recipes === undefined || models[1].recipes.length === 0"))
        start(page)
        page.evaluate("() => deleteSchemeNow(1)")
        check("delete scheme: a good save says Deleted, and Undo puts the scheme back",
              "Deleted Blue squad" in toast(page) and page.evaluate("book.schemes.length") == 0)
        page.click("#toast-undo")
        quiet(page)
        check("…the scheme is back", page.evaluate("book.schemes.map(s => s.name)") == ["Blue squad"])

        # ---------- 4. Phone sizes ----------
        print("\n--- 4. Phone sizes ---")
        for (w, h) in ((390, 844), (360, 640)):
            for scheme in ("dark", "light"):
                ctx2 = browser.new_context(viewport={"width": w, "height": h}, service_workers="block", color_scheme=scheme)
                pg = ctx2.new_page()
                start(pg)
                fill_up(pg)
                pg.evaluate("() => deleteRecipeNow(2)")
                quiet(pg)
                box = pg.locator("#toast-undo").bounding_box()
                fits = pg.evaluate("() => { const t = document.getElementById('toast').getBoundingClientRect();"
                                   " return t.left >= 0 && t.right <= innerWidth; }")
                sideways = pg.evaluate("() => document.documentElement.scrollWidth > innerWidth")
                check(f"{w}x{h} {scheme}: the Not saved message fits, its button is 44 px or more, no sideways scroll",
                      fits and not sideways and box and box["height"] >= 44 - 0.5 and box["width"] >= 44 - 0.5, (fits, sideways, box))
                ctx2.close()

        check("no page errors", not errors, errors)
        check("no pop-ups", not popups, popups)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

main()
