"""Test (v18c-2): Remove and Merge into… on Your Palette, and the About wording.

1. Remove (review section 2, "Junk paints can't be removed"). An open paint that no recipe
   uses has a Remove button. It takes the paint out of your palette, with Undo. A paint used in
   a recipe has no Remove button.

2. Merge into… For a misspelt copy: pick the right paint and every recipe that used the copy
   uses the right one instead. The copy leaves your palette. The right paint keeps its own
   details, and only takes the status or colour from the copy where it had none. The misspelt
   name is remembered, so pasting it again finds the right paint. Undo puts everything back.
   Renaming a paint to the name of one you have already merged them, but a copy with a status
   was left behind; that now uses the same merge.

3. About (review section 1, item 8): the wording no longer says the app holds no unit lists,
   or that nothing is ever sent anywhere (the pot scan downloads its text-reading tool).

Serve the repo folder first (run_all.py does this for you), then run:
python3 tests/test_v18c2.py
The port comes from the SOG_PORT environment variable, or 8765 if it isn't set."""
import json, os, sys
from playwright.sync_api import sync_playwright

PORT = os.environ.get("SOG_PORT", "8765")
BASE = f"http://localhost:{PORT}"
GREY = "#808080"

results = []
def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def paint(pid, name, brand="Citadel", colour="#3b5b7a", **extra):
    return {"id": pid, "brand": brand, "name": name, "colour": colour, **extra}

BOOK = {
    "paints": [
        paint(1, "Macragge Blue", colour=GREY),                              # the right one: no status, no colour
        paint(2, "Macrage Blue", brand="", colour="#112233", status="wishlist"),   # the misspelt copy
        paint(3, "Old Junk", status="owned"),                                # in no recipe
        paint(4, "Mephiston Red", status="owned"),
        paint(5, "Retributor Armour", status="owned"),
        paint(6, "Retributer Armour", status="empty"),                       # in no recipe, has a status
    ],
    "recipes": [{"id": 1, "name": "Armour", "part": "Armour", "notes": "", "steps": [
        {"technique": "Base coat", "coats": 1, "paints": [{"paint": 2, "mix": 100}]},
        {"technique": "Layer", "coats": 1, "paints": [{"paint": 4, "mix": 100}]}]}],
    "schemes": [], "v15": True,
    "shorthand": {"mb": {"brand": "", "name": "Macrage Blue"}},
}

def start(page):
    page.goto(f"{BASE}/manifest.json")
    page.evaluate("""book => { localStorage.clear(); localStorage.setItem('mini-tracker-models', '[]');
                     localStorage.setItem('shades-of-grey-recipes', JSON.stringify(book)); }""", BOOK)
    page.goto(f"{BASE}/index.html")
    page.wait_for_timeout(300)

def saved_book(page):
    return json.loads(page.evaluate("localStorage.getItem('shades-of-grey-recipes') || '{}'"))

def open_paint(page, pid):
    """Your Palette, with this paint opened."""
    page.evaluate("""pid => { settings.recipeView = 'palette'; showTab('recipes');
                     openPaintIds.clear(); openPaintIds.add(pid); render(); }""", pid)
    page.wait_for_timeout(50)

def by_id(book, pid):
    return next((p for p in book.get("paints", []) if p["id"] == pid), None)

def step_paints(book):
    return [sp["paint"] for s in book["recipes"][0]["steps"] for sp in s["paints"]]

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: d.accept())   # the "Merge the two?" question when renaming

        # ---------- 1. Remove ----------
        start(page)
        open_paint(page, 3)
        remove = page.locator("button[aria-label='Remove Old Junk from your palette']")
        check("Remove: a paint in no recipes has a Remove button", remove.count() == 1 and remove.is_visible())
        remove.click()
        page.wait_for_timeout(100)
        check("Remove: the paint leaves your palette (and the saved copy)", by_id(saved_book(page), 3) is None)
        check("Remove: the message says what was removed, with Undo",
              "Removed Old Junk" in page.inner_text("#toast-text") and page.locator("#toast-undo").is_visible(),
              page.inner_text("#toast-text"))
        page.click("#toast-undo")
        page.wait_for_timeout(100)
        back = by_id(saved_book(page), 3)
        check("Remove: Undo puts it back, status and all", back is not None and back.get("status") == "owned", back)

        open_paint(page, 4)
        check("Remove: a paint used in a recipe has no Remove button",
              page.locator("button[aria-label^='Remove Mephiston Red']").count() == 0)
        check("Remove: and it says why", "Only paints in no recipes can be removed." in page.inner_text("#paint-list"))

        # ---------- 2. Merge into… ----------
        start(page)
        open_paint(page, 2)
        pick = page.locator("select[aria-label='Merge Macrage Blue into']")
        check("Merge: the picker is hidden until you tap Merge into…", pick.count() == 1 and not pick.is_visible())
        page.click("#paint-list button:has-text('Merge into…')")
        check("Merge: tapping Merge into… shows the picker", pick.is_visible())
        go = page.locator("#paint-list button.merge-go")
        check("Merge: the Merge button waits until a paint is picked", go.is_disabled())
        options = pick.locator("option").all_inner_texts()
        check("Merge: the list has every other paint, not this one",
              "Macragge Blue (Citadel)" in options and not any(o.startswith("Macrage Blue") for o in options), options)
        pick.select_option("1")
        go.click()
        page.wait_for_timeout(100)
        book = saved_book(page)
        check("Merge: the copy leaves your palette", by_id(book, 2) is None, [x["name"] for x in book["paints"]])
        check("Merge: the recipe now uses the right paint", step_paints(book) == [1, 4], step_paints(book))
        right = by_id(book, 1)
        check("Merge: the right paint takes the copy's status and colour (it had none)",
              right and right.get("status") == "wishlist" and right.get("colour") == "#112233", right)
        check("Merge: the right paint keeps its own name and brand",
              right and right["name"] == "Macragge Blue" and right["brand"] == "Citadel", right)
        check("Merge: shorthand that pointed at the copy now points at the right paint",
              book["shorthand"].get("mb", {}).get("name") == "Macragge Blue", book["shorthand"])
        found = page.evaluate("(matchPaint('Macrage Blue').paint || {}).name || null")
        check("Merge: pasting the misspelt name again finds the right paint", found == "Macragge Blue", found)
        check("Merge: the message says what happened",
              "Merged Macrage Blue into Macragge Blue" in page.inner_text("#toast-text"), page.inner_text("#toast-text"))
        page.click("#toast-undo")
        page.wait_for_timeout(100)
        book = saved_book(page)
        check("Merge: Undo puts the copy back and the recipe uses it again",
              by_id(book, 2) is not None and step_paints(book) == [2, 4], step_paints(book))
        check("Merge: Undo puts the right paint back as it was",
              by_id(book, 1).get("status") is None and by_id(book, 1)["colour"] == GREY, by_id(book, 1))

        # A paint with its own status keeps it.
        start(page)
        open_paint(page, 6)
        page.click("#paint-list button:has-text('Merge into…')")
        page.select_option("select[aria-label='Merge Retributer Armour into']", "5")
        page.click("#paint-list button.merge-go")
        page.wait_for_timeout(100)
        kept = by_id(saved_book(page), 5)
        check("Merge: a paint with its own status keeps it", kept and kept.get("status") == "owned", kept)

        # Renaming to a paint you already have: the copy (with a status) no longer stays behind.
        start(page)
        page.evaluate("editPaint(book.paints.find(p => p.id === 6), 'name', 'Retributor Armour')")
        page.wait_for_timeout(100)
        names = [x["name"] for x in saved_book(page)["paints"]]
        check("Rename to a twin: only one Retributor Armour is left", names.count("Retributor Armour") == 1, names)

        # Paste after a merge: the misspelling maps to the right paint, no new paint.
        start(page)
        open_paint(page, 2)
        page.click("#paint-list button:has-text('Merge into…')")
        page.select_option("select[aria-label='Merge Macrage Blue into']", "1")
        page.click("#paint-list button.merge-go")
        page.wait_for_timeout(100)
        page.evaluate("startImport()")
        page.fill("#import-text", "Test scheme\n\nHelmet:\nMacrage Blue")
        page.click("#import-page button.primary-button")
        page.wait_for_timeout(100)
        before = len(saved_book(page)["paints"])
        page.click("#import-save")
        page.wait_for_timeout(150)
        book = saved_book(page)
        new_recipe = max(book["recipes"], key=lambda r: r["id"])
        used = [sp["paint"] for s in new_recipe["steps"] for sp in s["paints"]]
        check("Paste after a merge: the misspelling uses the right paint, no new paint",
              used == [1] and len(book["paints"]) == before, (used, len(book["paints"]), before))

        # ---------- 3. About ----------
        about = page.evaluate("document.getElementById('about').textContent")
        check("About: no Games Workshop artwork, rules, points or stats",
              "No Games Workshop artwork, rules, points or stats" in about, about)
        check("About: says the app knows paint and faction names", "knows paint and faction names" in about, about)
        # v18.3: the scan library is part of the app now, so the download sentence was removed.
        check("About: no longer mentions a scan download (v18.3 hosts the reader itself)",
              "text-reading tool" not in about, about)
        check("About: the old untrue lines are gone",
              "unit lists" not in about and "nothing is sent anywhere" not in about, about)

        check("no page errors", not errors, errors)
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
