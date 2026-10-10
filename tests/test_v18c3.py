"""Test (v18c-3): honest "Saved" / "Added" messages when the phone's storage is full.

Review section 2, "A paste import says Saved even when storage is full", and the commit()
helper idea in section 3b.

How the test fakes a full phone: before the app loads, the browser's "write to storage"
step (localStorage.setItem) is wrapped. While window.__storageFull is true it throws the
same "QuotaExceededError" a real full phone gives. The test switches it on and off.

1. Every "Saved …" / "Added …" message (unit added, unit saved, recipe, scheme, paint,
   merge, remove) only shows if the save worked. If it failed, the message says
   "Not saved", offers Save backup, and the red banner stays up. The change stays on
   screen, and the banner's Try again saves it once there's room.
2. Paste import: if the save fails, nothing is half-saved, the preview stays open with
   your notes and your "Do you own these?" answer, and tapping Save again later works.
3. Pot scan: "Added … to your palette" only if it was saved. If not, the paint is taken
   back out and the message says so; Add works once there's room.

Serve the repo folder first (run_all.py does this for you), then run:
python3 tests/test_v18c3.py
The port comes from the SOG_PORT environment variable, or 8765 if it isn't set."""
import json, os, sys
from playwright.sync_api import sync_playwright

PORT = os.environ.get("SOG_PORT", "8765")
BASE = f"http://localhost:{PORT}"
UNITS_KEY = "mini-tracker-models"
RECIPES_KEY = "shades-of-grey-recipes"

results = []
def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# The fake full storage. Added to every page before the app's own code runs.
FAKE_STORAGE = """
(() => {
  const realSetItem = Storage.prototype.setItem;
  window.__storageFull = false;
  Storage.prototype.setItem = function (key, value) {
    if (window.__storageFull) throw new DOMException("The quota has been exceeded.", "QuotaExceededError");
    return realSetItem.call(this, key, value);
  };
})();
"""

BOOK = {
    "paints": [
        {"id": 1, "brand": "Citadel", "name": "Mephiston Red", "colour": "#9a1115", "status": "owned"},
        {"id": 2, "brand": "Citadel", "name": "Old Junk", "colour": "#555555", "status": "owned"},
        {"id": 3, "brand": "", "name": "Mephistn Red", "colour": "#9a1115"},
    ],
    "recipes": [{"id": 1, "name": "Cloak", "part": "Cloak", "notes": "", "steps": [
        {"technique": "Base coat", "coats": 1, "paints": [{"paint": 1, "mix": 100}]},
        {"technique": "Layer", "coats": 1, "paints": [{"paint": 3, "mix": 100}]}]}],
    "schemes": [], "v15": True,
}
UNITS = [{"id": 1, "name": "Intercessors", "hobby": "40K", "faction": "Ultramarines", "stage": 0, "count": 5}]
NOTE = "Test scheme\n\nArmour:\nRetributor Armour\nAgrax Earthshade"

def start(page):
    page.goto(f"{BASE}/manifest.json")
    page.evaluate("""([units, book]) => { localStorage.clear();
                     localStorage.setItem('mini-tracker-models', JSON.stringify(units));
                     localStorage.setItem('shades-of-grey-recipes', JSON.stringify(book)); }""", [UNITS, BOOK])
    page.goto(f"{BASE}/index.html")
    page.wait_for_timeout(300)

def full(page, on):
    page.evaluate(f"window.__storageFull = {'true' if on else 'false'}")

def saved(page, key):
    return json.loads(page.evaluate(f"localStorage.getItem('{key}') || 'null'"))

def toast(page):
    return page.inner_text("#toast-text")

def toast_button(page):
    b = page.locator("#toast-undo")
    return b.inner_text() if b.is_visible() else ""

def banner_up(page):
    return page.locator("#save-banner").is_visible()

def not_saved_toast(page):
    return toast(page).startswith("Not saved") and toast_button(page) == "Save backup"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.add_init_script(FAKE_STORAGE)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: d.accept())

        # ---------- 0. The fake works ----------
        start(page)
        full(page, True)
        threw = page.evaluate("""() => { try { localStorage.setItem('x', '1'); return false; }
                                 catch (e) { return e.name === 'QuotaExceededError'; } }""")
        check("fake full storage: writing throws the 'storage full' error", threw)
        full(page, False)

        # ---------- 1. Units: Added / Saved ----------
        page.evaluate("showTab('units')")
        page.click("#toggle-add")
        page.fill("#name-input", "Hellblasters")
        page.click("#add-form button[type=submit]")
        page.wait_for_timeout(100)
        check("unit added (room): says Added", toast(page) == "Added Hellblasters", toast(page))
        check("unit added (room): it's in the saved copy",
              any(u["name"] == "Hellblasters" for u in saved(page, UNITS_KEY)))

        full(page, True)
        page.fill("#name-input", "Terminators")
        page.click("#add-form button[type=submit]")
        page.wait_for_timeout(100)
        check("unit added (full): no 'Added' message", "Added" not in toast(page), toast(page))
        check("unit added (full): says Not saved, offers Save backup", not_saved_toast(page),
              [toast(page), toast_button(page)])
        check("unit added (full): the red banner is up", banner_up(page))
        check("unit added (full): not in the saved copy",
              not any(u["name"] == "Terminators" for u in saved(page, UNITS_KEY)))
        check("unit added (full): still on screen", "Terminators" in page.inner_text("#unit-list"))

        page.evaluate("editUnit(models.find(m => m.name === 'Intercessors'), 'name', 'Assault Intercessors')")
        page.wait_for_timeout(50)
        check("unit saved (full): no 'Saved' message", not_saved_toast(page), toast(page))

        full(page, False)
        page.click("#banner-retry")
        page.wait_for_timeout(100)
        names = [u["name"] for u in saved(page, UNITS_KEY)]
        check("Try again (room): both changes are saved now",
              "Terminators" in names and "Assault Intercessors" in names, names)
        check("Try again (room): the banner goes", not banner_up(page))
        page.evaluate("editUnit(models.find(m => m.name === 'Terminators'), 'name', 'Deathwing Terminators')")
        page.wait_for_timeout(50)
        check("unit saved (room): says Saved", toast(page) == "Saved Deathwing Terminators", toast(page))

        # ---------- 2. Recipe, scheme, paint, merge, remove ----------
        def recipes_case(label, script, want_ok_text, saved_test):
            start(page)
            page.evaluate("settings.recipeView = 'palette'; showTab('recipes'); render()")
            before = saved(page, RECIPES_KEY)   # as saved after the app opened (it tidies on load)
            full(page, True)
            page.evaluate(script)
            page.wait_for_timeout(80)
            check(f"{label} (full): says Not saved, not '{want_ok_text.split()[0]}'",
                  not_saved_toast(page) and want_ok_text not in toast(page), toast(page))
            check(f"{label} (full): the saved copy hasn't changed", saved(page, RECIPES_KEY) == before)
            start(page)
            page.evaluate("settings.recipeView = 'palette'; showTab('recipes'); render()")
            page.evaluate(script)
            page.wait_for_timeout(80)
            check(f"{label} (room): says {want_ok_text}", toast(page).startswith(want_ok_text), toast(page))
            check(f"{label} (room): it's saved", saved_test(saved(page, RECIPES_KEY)))

        recipes_case("recipe saved",
                     "startNewRecipe(null); recipeDraft.name = 'Banner pole'; saveRecipeDraft()",
                     "Saved Banner pole",
                     lambda b: any(r["name"] == "Banner pole" for r in b["recipes"]))
        recipes_case("scheme saved",
                     "startScheme(null, 'Ultramarines'); schemeDraft.name = 'Blue boys'; schemeDraft.recipes = [1]; saveScheme()",
                     "Saved Blue boys",
                     lambda b: any(s["name"] == "Blue boys" for s in b["schemes"]))
        recipes_case("paint saved",
                     "editPaint(book.paints.find(p => p.name === 'Old Junk'), 'name', 'Abaddon Black')",
                     "Saved Abaddon Black",
                     lambda b: any(x["name"] == "Abaddon Black" for x in b["paints"]))
        recipes_case("paint merged",
                     "mergePaintInto(book.paints.find(p => p.id === 3), book.paints.find(p => p.id === 1))",
                     "Merged Mephistn Red into Mephiston Red",
                     lambda b: not any(x["id"] == 3 for x in b["paints"]))
        recipes_case("paint removed",
                     "removePaint(book.paints.find(p => p.name === 'Old Junk'))",
                     "Removed Old Junk",
                     lambda b: not any(x["name"] == "Old Junk" for x in b["paints"]))

        # ---------- 3. Paste import ----------
        start(page)
        page.evaluate("showTab('recipes'); startImport()")
        page.fill("#import-text", NOTE)
        page.click("#import-page button.primary-button")   # "Read notes"
        page.wait_for_timeout(100)
        page.click("#import-own [data-own=none]")          # "Do you own these?" None
        paints_before = page.evaluate("book.paints.length")
        before = saved(page, RECIPES_KEY)
        full(page, True)
        page.click("#import-save")
        page.wait_for_timeout(150)
        check("paste (full): no 'Saved' message", "Saved" not in toast(page), toast(page))
        check("paste (full): says Not saved and that the notes are still here",
              toast(page).startswith("Not saved") and "pasted notes are still here" in toast(page)
              and toast_button(page) == "Save backup", toast(page))
        check("paste (full): the paste screen stays open", page.locator("#import-page").is_visible())
        check("paste (full): your notes are still in the box", page.input_value("#import-text") == NOTE,
              page.input_value("#import-text"))
        check("paste (full): the preview and its Save button are still there",
              page.locator("#import-save").is_visible() and "Retributor Armour" in page.inner_text("#import-page"))
        check("paste (full): your 'None' answer is kept", page.locator("#import-own [data-own=none]")
              .get_attribute("aria-pressed") == "true")
        check("paste (full): nothing half-added on screen",
              page.evaluate("book.recipes.length") == 1 and page.evaluate("book.paints.length") == paints_before
              and page.evaluate("book.schemes.length") == 0)
        check("paste (full): the saved copy hasn't changed", saved(page, RECIPES_KEY) == before)

        full(page, False)
        page.click("#import-save")
        page.wait_for_timeout(150)
        b = saved(page, RECIPES_KEY)
        check("paste (room, Save again): says Saved", toast(page).startswith("Saved 1 scheme with 1 recipe"), toast(page))
        check("paste (room, Save again): the recipe and scheme are saved",
              any(r["name"] == "Armour" for r in b["recipes"]) and any(s["name"] == "Test scheme" for s in b["schemes"]))
        check("paste (room, Save again): each new paint added once",
              [x["name"] for x in b["paints"]].count("Retributor Armour") == 1
              and [x["name"] for x in b["paints"]].count("Agrax Earthshade") == 1, [x["name"] for x in b["paints"]])
        st = {x["name"]: x.get("status", "") for x in b["paints"]}
        check("paste (room, Save again): your 'None' answer was used",
              st.get("Retributor Armour") == "notowned" and st.get("Agrax Earthshade") == "notowned", st)
        check("paste (room, Save again): the paste screen closes", not page.locator("#import-page").is_visible())

        # ---------- 4. Pot scan: Added … to your palette ----------
        def scan_pick(name, typed):
            page.evaluate("openRecipeId = null; settings.recipeView = 'palette'; showTab('recipes'); renderRecipes()")
            page.click("#scan-button")
            page.fill("#scan-typed", typed)
            page.locator("#scan-typed").dispatch_event("change")
            page.wait_for_timeout(100)
            page.locator("#scan-panel .chip", has_text=name).first.click()

        start(page)
        scan_pick("Macragge Blue", "macragge blue")
        before = saved(page, RECIPES_KEY)
        full(page, True)
        page.locator("#scan-result button", has_text="Add to my palette").click()
        page.wait_for_timeout(100)
        check("scan (full): no 'Added' message", "Added" not in toast(page), toast(page))
        check("scan (full): says it wasn't added, offers Save backup",
              toast(page).startswith("Not added") and "Macragge Blue" in toast(page)
              and toast_button(page) == "Save backup", toast(page))
        check("scan (full): the paint isn't left in your palette on screen",
              not page.evaluate("book.paints.some(p => p.name === 'Macragge Blue')"))
        check("scan (full): still says 'Not in your palette yet', with Add",
              "Not in your palette yet" in page.inner_text("#scan-result")
              and page.locator("#scan-result button", has_text="Add to my palette").count() == 1)
        check("scan (full): the saved copy hasn't changed", saved(page, RECIPES_KEY) == before)

        full(page, False)
        page.locator("#scan-result button", has_text="Add to my palette").click()
        page.wait_for_timeout(100)
        check("scan (room): says Added … to your palette", toast(page) == "Added Macragge Blue to your palette", toast(page))
        mb = next((x for x in saved(page, RECIPES_KEY)["paints"] if x["name"] == "Macragge Blue"), None)
        check("scan (room): it's saved as Owned", mb is not None and (mb.get("status") == "owned" or mb.get("owned") is True), mb)

        check("no page errors", not errors, errors)
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
