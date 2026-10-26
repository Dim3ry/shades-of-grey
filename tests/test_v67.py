"""v67 tests for Minifolio (chunk 2.2: recipes and the shopping list agree).

What changed:
 The check in chunk 2.1 found the "Do you own these?" card never named the paints it meant, a half-typed paint
 name brought the card up and then made it vanish, a step with a brand but no paint name was dropped without a
 word, and the empty paint box's grey hint ("Paint, e.g. Macragge Blue") looked like a typed value.
 George also asked that nothing goes on the shopping list by itself: only Wishlist paints (every "Add to shopping
 list" button marks a paint Wishlist). So a recipe with missing paints gets one button that adds them.

Checks:
1. Versions, the v67 Updates entry, DATA_VERSION is still 1.
2. The shopping list holds only Wishlist paints: not missing recipe paints, not running low, not empty.
3. The recipe button: adds only real paints you don't own (never made-up ones), says how many, one Undo.
   It is gone when nothing is left to add. A step with no paint says "No paint" on its line.
4. "Do you own these?": names the paints; a half-typed name does not bring it up; a tap on None still lands
   when leaving a paint box adds a paint at that moment; None saves Not owned, and that is not on the list.
5. Save with a brand but no paint name stops, says which step and puts you in the box.
6. The paint box hint is "Paint name".
7. Help names the recipe button and says nothing is added by itself.
8. 390 px and 360 px, dark and light: no sideways scroll, the button is 44 px or more and fits.
9. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
import test_v31 as t
import test_v44 as e   # main_tab, sub_tab

read = t.read
HERE = os.path.dirname(os.path.abspath(__file__))
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

MADE_UP = "Example deep blue"   # replaced below by a real made-up name from EXAMPLE_RECIPES

def paints(made_up):
    return [
        {"id": 1, "brand": "Citadel", "name": "Macragge Blue", "colour": "#0d407f", "status": "owned"},
        {"id": 2, "brand": "Citadel", "name": "Nuln Oil", "colour": "#151515", "status": "notowned"},
        {"id": 3, "brand": "Vallejo", "name": "Turquoise", "colour": "#2fb5a8"},                      # no status yet
        {"id": 4, "brand": "Citadel", "name": "Eshin Grey", "colour": "#4a4d52", "status": "low"},
        {"id": 5, "brand": "Citadel", "name": "Rakarth Flesh", "colour": "#a7a28f", "status": "empty"},
        {"id": 6, "brand": "Citadel", "name": "Fire Dragon Bright", "colour": "#ff6a00", "status": "wishlist"},
        {"id": 7, "brand": "", "name": made_up, "colour": "#223355", "status": "notowned"},
    ]

def step(pids, technique="Layer"):
    return {"technique": technique, "coats": 1, "paints": [{"paint": pid, "mix": None} for pid in pids], "ratio": "", "note": "", "optional": False}

RECIPES = [{"id": 1, "name": "Blue test", "part": "Armour", "notes": "",
            "steps": [step([1]), step([2]), step([3]), step([7]), step([4]), step([], "")]}]
SETTINGS = {"tab": "recipes", "recipeView": "recipes", "examplesChecked": True}

def stored_paints(page):
    return json.loads(page.evaluate("localStorage.getItem('shades-of-grey-recipes')"))["paints"]

def by_name(page, name):
    return next((p for p in stored_paints(page) if p["name"] == name), None)

def list_names(page):
    return sorted(page.evaluate("shoppingItems().map(i => i.paint.name)"))

def open_recipe(page, rid=1):
    page.evaluate("(id) => openRecipe(id)", rid)
    page.wait_for_timeout(300)

def shop_button(page):
    return page.locator("#recipe-page button.recipe-shop-add")

def main():
    errors, dialogs = [], []
    app, html = read("app.js"), read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        notices = []
        attach_notices(page, notices.append)

        # ---------- 1. Versions ----------
        print("\n--- 1. Versions and the Updates entry ---")
        t.load(page, paints=[], settings=SETTINGS)
        made_up = page.evaluate("EXAMPLE_RECIPES[0].steps[0].paints[0][1]")
        PAINTS = paints(made_up)
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v67 or later", float(version[1:]) >= 67, version)
        m = re.search(r'const VERSION = "v([\d.]+)"', read("sw.js"))
        check("sw.js VERSION matches", m and "v" + m.group(1) == version, m and m.group(1))
        tags = re.findall(r'<script src="[^"]+\?v=(\d+)"', html)
        check("all six script tags carry the version number", len(tags) == 6 and set(tags) == {version[1:]}, tags)
        check("the comments that name the number agree", f'The "?v={version[1:]}" makes' in html and f'e.g. "app.js?v={version[1:]}"' in app)
        entry = page.evaluate("CHANGELOG.find(c => c.version === 'v67')")
        check("the v67 Updates entry exists and is the newest while v67 is current", bool(entry) and (version != "v67" or page.evaluate("CHANGELOG[0].version") == "v67"))
        words = " ".join(entry["changes"]) if entry else ""
        check("the entry names the recipe button and the Wishlist-only list", "Add missing paints to shopping list" in words and "Wishlist" in words, words)
        check("no em dash in the v67 Updates entry", "—" not in app[app.index('{ version: "v67"'):app.index('{ version: "v66"')])
        check("DATA_VERSION is still 1", page.evaluate("DATA_VERSION") == 1)

        # ---------- 2. Only Wishlist paints on the list ----------
        print("\n--- 2. The shopping list ---")
        t.load(page, paints=PAINTS, recipes=RECIPES, settings=SETTINGS)
        check("only the Wishlist paint is on the list (not missing, running low or empty ones)", list_names(page) == ["Fire Dragon Bright"], list_names(page))
        check("the basket count says 1", page.inner_text("#basket-button .basket-count").strip() == "1", page.inner_text("#basket-button"))
        check("Copy as text lists it without a reason after the name", "- Fire Dragon Bright" in page.evaluate("shoppingText(shoppingItems())")
              and "wishlist" not in page.evaluate("shoppingText(shoppingItems())"))
        check("the recipe card still says Missing", "Missing 2" in page.inner_text("#recipe-list"), page.inner_text("#recipe-list"))

        # ---------- 3. The recipe button ----------
        print("\n--- 3. Add missing paints to shopping list ---")
        open_recipe(page)
        check("the recipe shows the button with the count of real missing paints (not the made-up one)",
              shop_button(page).count() == 1 and shop_button(page).inner_text() == "Add missing paints to shopping list (2)",
              shop_button(page).all_inner_texts())
        lines = page.locator("#recipe-page .step-line").all_inner_texts()
        check("the step with no paint says No paint on its line", "No paint" in lines[5] and all("No paint" not in l for l in lines[:5]), lines)
        before = stored_paints(page)
        shop_button(page).click()
        page.wait_for_timeout(300)
        check("one tap adds the two real missing paints", list_names(page) == ["Fire Dragon Bright", "Nuln Oil", "Turquoise"], list_names(page))
        check("…the made-up paint stays off", by_name(page, made_up)["status"] == "notowned")
        check("…running low and owned paints are left alone", by_name(page, "Eshin Grey")["status"] == "low" and by_name(page, "Macragge Blue")["status"] == "owned")
        check("…each remembers the recipe", "Recipe: Blue test" in (by_name(page, "Nuln Oil").get("shopFrom") or []), by_name(page, "Nuln Oil"))
        check("…the message says how many, with an Undo", "Added 2 paints" in page.inner_text("#toast-text") and page.locator("#toast-undo").is_visible(), page.inner_text("#toast-text"))
        check("…and the button is gone, as nothing is left to add", shop_button(page).count() == 0)
        page.click("#toast-undo")
        page.wait_for_timeout(300)
        check("Undo puts every paint back as it was", stored_paints(page) == before, stored_paints(page))
        open_recipe(page)
        check("…and the button is back", shop_button(page).count() == 1)

        # ---------- 4. Do you own these? ----------
        print("\n--- 4. Do you own these? ---")
        t.load(page, paints=PAINTS[:1], settings=SETTINGS)
        t.open_editor(page)
        page.get_by_label("Recipe name").fill("Typing test")
        check("the empty paint box hint is Paint name", page.get_attribute('[data-key="step-0-paint-0"]', "placeholder") == "Paint name")
        box = page.locator('[data-key="step-0-paint-0"]')
        box.click()
        box.press_sequentially("Macragge Blu")
        page.wait_for_timeout(150)
        check("a half-typed name of a paint you have does not bring the card up", page.locator("#recipe-own").is_hidden())
        box.press_sequentially("e")
        page.wait_for_timeout(150)
        check("…nor once it is finished", page.locator("#recipe-own").is_hidden())
        t.add_step(page)
        box2 = page.locator('[data-key="step-1-paint-0"]')
        box2.click()
        box2.press_sequentially("Zqx Test Paint")
        page.wait_for_timeout(150)
        check("a new name not yet finished (box still in use) does not bring the card up", page.locator("#recipe-own").is_hidden())
        t.blur(page)
        check("leaving the box brings it up", page.locator("#recipe-own").is_visible())
        check("…and the card names the paint", "Zqx Test Paint" in page.inner_text("#recipe-own .own-names"), page.inner_text("#recipe-own"))
        t.add_step(page)
        box3 = page.locator('[data-key="step-2-paint-0"]')
        box3.click()
        box3.press_sequentially("Qzx Other Paint")
        page.click('#recipe-own .chip[data-own="none"]')   # this tap also leaves the box, which adds the second paint
        page.wait_for_timeout(200)
        check("a tap on None lands even though leaving the box added a paint at that moment",
              page.get_attribute('#recipe-own .chip[data-own="none"]', "aria-pressed") == "true" and page.evaluate("recipeDraft.own.mode") == "none")
        names = page.inner_text("#recipe-own .own-names")
        check("…and the card names both new paints, not the one you already had", "Zqx Test Paint" in names and "Qzx Other Paint" in names and "Macragge" not in names, names)
        page.click("#recipe-page button.primary-button:has-text('Save recipe')")
        page.wait_for_timeout(300)
        check("None saves both as Not owned", by_name(page, "Zqx Test Paint")["status"] == "notowned" and by_name(page, "Qzx Other Paint")["status"] == "notowned")
        check("…the paint you already had stays Owned", by_name(page, "Macragge Blue")["status"] == "owned")
        check("…and nothing goes on the shopping list by itself", list_names(page) == [], list_names(page))

        # ---------- 5. A brand but no paint name ----------
        print("\n--- 5. Save with a brand but no paint name ---")
        t.open_editor(page)
        page.get_by_label("Recipe name").fill("Gap test")
        page.locator("#recipe-page .paint-edit .paint-brand").first.fill("Citadel")
        notices.clear()
        # The "Saved" message from part 4 can still sit over the button, so the tap goes straight to it (as add_step does).
        page.locator("#recipe-page button.primary-button:has-text('Save recipe')").dispatch_event("click")
        page.wait_for_timeout(300)
        check("Save stops and says which step", any(n == "Step 1 has no paint name." for n in notices), notices)
        check("…the recipe is not saved and you are still writing it", page.evaluate("recipeDraft !== null") and not page.evaluate("book.recipes.some(r => r.name === 'Gap test')"))
        check("…and you are put in the empty paint box", page.evaluate("document.activeElement && document.activeElement.dataset.key") == "step-0-paint-0")
        page.locator('[data-key="step-0-paint-0"]').fill("Macragge Blue")
        t.blur(page)
        page.click("#recipe-page button.primary-button:has-text('Save recipe')")
        page.wait_for_timeout(300)
        check("with the name filled in it saves", page.evaluate("book.recipes.some(r => r.name === 'Gap test' && r.steps[0].paints.length === 1)"))

        # ---------- 6. Help ----------
        print("\n--- 6. Help ---")
        e.main_tab(page, "settings")
        e.sub_tab(page, "help")
        recipe_topic = page.text_content("#help-recipe-shop") or ""
        shop_topic = page.text_content("#help-shop") or ""
        check("Help names the recipe button and Undo", "Add missing paints to shopping list" in recipe_topic and "Undo" in recipe_topic, recipe_topic)
        check("Help says the list only holds what you put there", "Wishlist" in shop_topic and "Nothing is added by itself" in shop_topic, shop_topic)
        check("Help no longer says None puts paints on the list", "so they go on the shopping list" not in html)
        check("no em dash in the new Help lines", "—" not in recipe_topic + shop_topic)

        # ---------- 7. Phones, dark and light ----------
        for appearance in ["dark", "light"]:
            for width in [390, 360]:
                tag = f"{appearance} {width}px"
                print(f"\n--- 7. {tag} ---")
                page.set_viewport_size({"width": width, "height": 780})
                t.load(page, paints=PAINTS, recipes=RECIPES, settings=dict(SETTINGS, appearance=appearance))
                open_recipe(page)
                check(f"{tag}: no sideways scroll", not page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth"))
                size = page.evaluate("""() => { const b = document.querySelector('#recipe-page button.recipe-shop-add'); if (!b) return null;
                    const r = b.getBoundingClientRect(); return [Math.round(r.height), r.left >= 0 && r.right <= document.documentElement.clientWidth]; }""")
                check(f"{tag}: the button is 44 px or more and fits on screen", size and size[0] >= 44 and size[1], size)
                os.makedirs(os.path.join(HERE, "screenshots"), exist_ok=True)
                page.screenshot(path=os.path.join(HERE, "screenshots", f"v67-recipe-{appearance}-{width}.png"), full_page=True)

        # ---------- 8. Safety ----------
        print("\n--- 8. Safety ---")
        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
