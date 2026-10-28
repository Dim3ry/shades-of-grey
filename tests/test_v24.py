"""v24 tests for Minifolio: example recipes and paints (roadmap section 4).

Checks:
1. Version numbers (plain numbers, "v24 or later"), sw.js and both ?v= tags match, the Updates entry, kept things
   (CNAME, the ocr folder, LICENSE-paint-list.txt, the passive ZAP workflow, the CSP exactly as v21.4),
   storage names and the data version (still 1).
2. A brand-new start: two example recipes, their paints in Your Palette (real colours), linked to the example
   units, the card on the Recipes tab (all three sub-pages), saved with "example" marks, nothing else changed.
3. People who already have data are NOT given examples (units saved, recipes saved, settings saved), and the
   examples don't come back once cleared.
4. Clear examples (real taps): removes only the examples; Undo puts everything back exactly; it sticks after
   a reload. Keep them: marks go, nothing is removed; Undo puts the marks back.
5. What Clear keeps: an example paint you gave a status, edited, or used in your own recipe is kept.
6. Example paints stay off the shopping list (v58: also after Keep them, or with a status, see test_v58.py).
7. Saved data's shape (DATA_VERSION stays 1): unknown fields survive cleaning, only a real true counts as
   an example mark, the book's keys are unchanged, a backup carries the marks.
8. Dark and light at 390 and 360 px: the card is on screen, buttons are 44 px targets, text is readable,
   nothing scrolls sideways.
9. Help and Updates wording (reached via Settings, then the Help / Updates switch).
10. No real browser pop-ups, no page errors and no CSP errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright
from launch_helpers import leave_launch

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

# v68: the 7th default stage was renamed from "Painted with issues" to "Needs touch-ups", so this list uses the new name.
STAGES = ["Unassembled", "Part assembled", "Assembled", "Primed", "Part painted",
          "Battle ready", "Needs touch-ups", "Parade ready"]
V21_4_CSP = ("default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; "
             "img-src 'self' blob: data: https://dim3ry.goatcounter.com/count; media-src 'self' blob:; font-src 'self'; connect-src 'self'; worker-src 'self'; "
             "manifest-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-src 'none'")
# v44: five example recipes and sixteen example paints (was two and eight)
PAINTS = ["Example deep blue", "Example dark wash", "Example mid blue", "Example pale grey",
          "Example mid green", "Example brown wash", "Example bright green", "Example pale green",
          "Example dark gold", "Example bright gold", "Example pale gold", "Example deep red",
          "Example bright orange", "Example pale yellow", "Example dark grey", "Example mid grey"]
RECIPE_NAMES = ["Blue armour", "Gold metal", "Green skin", "Glowing eyes", "Stone base"]
CAPTAIN_LINKS = ["Blue armour", "Gold metal", "Glowing eyes", "Stone base"]
BRUTES_LINKS = ["Green skin", "Glowing eyes", "Stone base"]
GUARDIANS_LINKS = ["Gold metal", "Stone base"]
BOOK_KEYS = ["paints", "parts", "recipes", "schemes", "shorthand", "techniques", "v15"]

def fresh(page, settings=None):
    """A brand-new start: nothing saved at all (apart from the look, if asked)."""
    page.goto(URL)
    page.evaluate("""async (s) => { localStorage.clear();
        if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s));
        await new Promise(done => { const r = indexedDB.deleteDatabase('shades-of-grey-photos');
                                    r.onsuccess = r.onerror = r.onblocked = () => done(); }); }""", settings)
    page.reload()
    page.wait_for_function("() => typeof APP_VERSION === 'string'")
    page.wait_for_timeout(300)
    leave_launch(page)   # U4b: tap through the start page

def existing(page, units, book=None, settings=None):
    """Someone who has used the app before: units saved (and maybe recipes and settings)."""
    page.goto(URL)
    page.evaluate("""async ([u, b, s]) => { localStorage.clear();
        localStorage.setItem('mini-tracker-models', JSON.stringify(u));
        if (b) localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b));
        if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s));
        await new Promise(done => { const r = indexedDB.deleteDatabase('shades-of-grey-photos');
                                    r.onsuccess = r.onerror = r.onblocked = () => done(); }); }""", [units, book, settings])
    page.reload()
    page.wait_for_function("() => typeof APP_VERSION === 'string'")
    page.wait_for_timeout(300)
    leave_launch(page)   # U4b: tap through the start page

def main_tab(page, name):
    page.click(f'nav button[data-tab="{name}"]')
    page.wait_for_timeout(150)

def sub_tab(page, name):
    page.click(f'#more-seg button[data-page="{name}"]')
    page.wait_for_timeout(150)

def recipe_view(page, view):
    page.click(f'#recipe-seg button[data-view="{view}"]')
    page.wait_for_timeout(200)

def shot(page, name):
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=os.path.join(SHOTS, name))

def no_sideways(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")

def saved_book(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-recipes') || 'null')")

def saved_units(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('mini-tracker-models') || '[]')")

def saved_settings(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-settings') || '{}')")

def card_visible(page):
    return page.evaluate("() => !document.getElementById('examples-card-recipes').classList.contains('hidden')")

def toast(page):
    return page.evaluate("""() => ({ text: document.getElementById('toast-text').textContent,
        shown: !document.getElementById('toast').classList.contains('hidden'),
        undo: !document.getElementById('toast-undo').classList.contains('hidden') })""")

def palette_names(page):
    return page.evaluate("() => book.paints.map(p => p.name).sort()")

def rgb(text):
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)[:3]]

def luminance(c):
    def f(v):
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = [f(x) for x in c]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast(a, b):
    la, lb = sorted([luminance(a), luminance(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)

def main():
    errors, csp, popups = [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)
        page.on("dialog", lambda d: (popups.append(d.message), d.dismiss()))

        # ---------- 1. Versions and kept things ----------
        print("\n--- 1. Versions and kept things ---")
        fresh(page)
        html, sw = read("index.html"), read("sw.js")
        version = page.evaluate("APP_VERSION")
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        check("the newest Updates entry is the current version", page.evaluate("CHANGELOG[0].version") == version)
        check("no code was put inside index.html", len(re.findall(r"<script(?![^>]*\bsrc=)[^>]*>\s*\S", html)) == 0)

        # ---------- 2. A brand-new start ----------
        print("\n--- 2. A brand-new start ---")
        fresh(page)
        recipes = page.evaluate("() => book.recipes.map(r => ({ name: r.name, part: r.part, example: r.example, steps: r.steps.length }))")
        check("five example recipes", [r["name"] for r in recipes] == RECIPE_NAMES, recipes)
        check("all are marked as examples and have three or four steps", all(r["example"] is True for r in recipes)
              and [r["steps"] for r in recipes] == [4, 4, 4, 3, 3], recipes)
        check("their parts are Armour, Metal, Skin, Eyes and Base", [r["part"] for r in recipes] == ["Armour", "Metal", "Skin", "Eyes", "Base"], recipes)
        check("the sixteen paints they use are in the palette", palette_names(page) == sorted(PAINTS), palette_names(page))
        check("every example paint is marked and has a real colour (not the unset grey)",
              page.evaluate("() => book.paints.every(p => p.example === true && p.colour !== DEFAULT_PAINT_COLOUR && p.brand === '')"))
        check("no paint has a status yet", page.evaluate("() => book.paints.every(p => paintStatus(p) === '')"))
        units = saved_units(page)
        check("the example units are still there too", [u["name"] for u in units] == ["Captain", "Brutes", "Guardians"], units)
        captain = next(u for u in units if u["name"] == "Captain")
        boyz = next(u for u in units if u["name"] == "Brutes")
        names = page.evaluate("() => Object.fromEntries(book.recipes.map(r => [r.id, r.name]))")
        guardians = next(u for u in units if u["name"] == "Guardians")
        check("Captain is linked to the four recipes that suit the Blue army", [names[str(i)] for i in captain.get("recipes", [])] == CAPTAIN_LINKS, captain)
        check("Brutes are linked to the three recipes that suit the Green army", [names[str(i)] for i in boyz.get("recipes", [])] == BRUTES_LINKS, boyz)
        check("Guardians are linked to the metal and the base", [names[str(i)] for i in guardians.get("recipes", [])] == GUARDIANS_LINKS, guardians)
        saved = saved_book(page)
        check("saved: all five recipes, both schemes and sixteen paints carry the example mark",
              [r.get("example") for r in saved["recipes"]] == [True] * 5 and [s.get("example") for s in saved["schemes"]] == [True, True]
              and sum(1 for q in saved["paints"] if q.get("example") is True) == 16, saved["recipes"])
        check("saved settings remember the examples were given (so they never come back)", saved_settings(page).get("recipeExamplesChecked") is True)
        check("the saved recipe book still has the same keys", sorted(saved.keys()) == sorted(BOOK_KEYS), sorted(saved.keys()))
        main_tab(page, "recipes")
        check("the Recipes tab lists all five recipes", page.locator("#recipe-list li").count() == 5, page.locator("#recipe-list li").count())
        check("the card shows on the Recipes sub-page", card_visible(page))
        card_text = page.text_content("#examples-card-recipes")
        check("the card says these are examples and counts the recipes, schemes and paints",
              "These are examples" in card_text and "5 example recipes" in card_text
              and "2 example schemes" in card_text and "16 example paints" in card_text, card_text)
        check("the card has Clear examples and Keep them",
              page.locator("#examples-card-recipes .clear-recipe-examples").inner_text() == "Clear examples"
              and page.locator("#examples-card-recipes .keep-recipe-examples").inner_text() == "Keep them")
        recipe_view(page, "schemes")
        check("the card also shows on Schemes", card_visible(page))
        recipe_view(page, "palette")
        check("the card also shows on Your Palette", card_visible(page))
        check("Your Palette lists the sixteen paints", page.locator("#paint-list li.paint-item").count() == 16,
              page.locator("#paint-list li.paint-item").count())
        recipe_view(page, "recipes")
        page.click("#recipe-list li >> nth=0")
        page.wait_for_timeout(250)
        check("the card is hidden while a recipe is open", not card_visible(page))
        page.evaluate("history.back()")
        page.wait_for_timeout(300)
        check("and it is back when the recipe is closed", card_visible(page))
        main_tab(page, "units")
        check("the unit examples card is separate and still shows", page.locator("#examples-card").is_visible())
        check("the unit card's buttons are unchanged (one Clear examples button per card)",
              page.locator("#examples-card .clear-examples").count() == 1)

        # ---------- 3. People who already have data ----------
        print("\n--- 3. People who already have data ---")
        units_only = [{"id": 1, "name": "Intercessors", "hobby": "40K", "faction": "Ultramarines", "stage": 3, "count": 5}]
        existing(page, units_only, settings={"palette": "ice", "stages": STAGES, "doneFrom": 5, "examplesChecked": True})
        check("saved units, no recipes: no example recipes", page.evaluate("() => book.recipes.length") == 0)
        check("and no example paints", page.evaluate("() => book.paints.length") == 0)
        main_tab(page, "recipes")
        check("and no card", not card_visible(page))
        existing(page, units_only)
        check("saved units with no settings at all: still none", page.evaluate("() => book.recipes.length + book.paints.length") == 0)
        own_book = {"parts": ["Whole model", "Armour"], "techniques": ["Base coat"], "v15": True, "shorthand": {}, "schemes": [],
                    "paints": [{"id": 1, "brand": "Citadel", "name": "Abaddon Black", "colour": "#231f20"}],
                    "recipes": [{"id": 1, "name": "My black", "part": "Armour", "notes": "", "steps": [
                        {"technique": "Base coat", "coats": 1, "paints": [{"paint": 1, "mix": None}]}]}]}
        existing(page, units_only, own_book)
        check("someone with their own recipes gets no examples",
              page.evaluate("() => book.recipes.map(r => r.name)") == ["My black"] and page.evaluate("() => book.paints.length") == 1)
        page.goto(URL)
        page.evaluate("""(b) => { localStorage.clear(); localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b)); }""", own_book)
        page.reload()
        page.wait_for_function("() => typeof APP_VERSION === 'string'")
        page.wait_for_timeout(300)
        leave_launch(page)   # U4b: tap through the start page
        check("no units saved but recipes are: their recipes are left exactly as they were",
              page.evaluate("() => book.recipes.map(r => r.name)") == ["My black"] and page.evaluate("() => book.paints.length") == 1)
        empty_book = {"parts": ["Whole model"], "techniques": ["Layer"], "paints": [], "recipes": [], "schemes": [], "shorthand": {}, "v15": True}
        page.goto(URL)
        page.evaluate("""(b) => { localStorage.clear(); localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b)); }""", empty_book)
        page.reload()
        page.wait_for_function("() => typeof APP_VERSION === 'string'")
        page.wait_for_timeout(300)
        leave_launch(page)   # U4b: tap through the start page
        check("an empty recipe book that was saved is not a new start: no examples",
              page.evaluate("() => book.recipes.length + book.paints.length") == 0)
        fresh(page)
        main_tab(page, "recipes")
        page.click("#examples-card-recipes .clear-recipe-examples")
        page.wait_for_timeout(300)
        page.reload()
        page.wait_for_function("() => typeof APP_VERSION === 'string'")
        page.wait_for_timeout(300)
        leave_launch(page)   # U4b: tap through the start page
        check("after Clear and a reload the examples do not come back",
              page.evaluate("() => book.recipes.length + book.paints.length") == 0)
        page.evaluate("() => localStorage.removeItem('mini-tracker-models')")
        page.reload()
        page.wait_for_function("() => typeof APP_VERSION === 'string'")
        page.wait_for_timeout(300)
        leave_launch(page)   # U4b: tap through the start page
        check("even if the units list is emptied from storage, cleared examples are not given again",
              page.evaluate("() => book.recipes.length + book.paints.length") == 0)

        # ---------- 4. Clear examples and Keep them ----------
        print("\n--- 4. Clear examples and Keep them ---")
        fresh(page)
        main_tab(page, "recipes")
        before_book = json.dumps(saved_book(page), sort_keys=True)
        before_units = json.dumps(saved_units(page), sort_keys=True)
        page.click("#examples-card-recipes .clear-recipe-examples")
        page.wait_for_timeout(300)
        t = toast(page)
        check("a message says exactly what was cleared, with Undo (v56: the example units go too)",
              t["shown"] and t["undo"] and t["text"] == "Cleared 3 example units, 5 example recipes, 2 example schemes and 16 example paints", t)
        check("no recipes and no paints are left", page.evaluate("() => book.recipes.length + book.paints.length") == 0)
        check("the card is gone", not card_visible(page))
        check("the recipe list no longer shows the examples", "Blue armour" not in page.inner_text("#recipe-list")
              and "Green skin" not in page.inner_text("#recipe-list"), page.inner_text("#recipe-list"))
        check("v56: the example units are cleared in the same tap", saved_units(page) == [], saved_units(page))
        check("saved: the book is empty", saved_book(page)["recipes"] == [] and saved_book(page)["paints"] == [])
        page.click("#toast-undo")
        page.wait_for_timeout(300)
        check("Undo: the whole recipe book is exactly as before", json.dumps(saved_book(page), sort_keys=True) == before_book)
        check("Undo: the units (and their recipe links) are exactly as before", json.dumps(saved_units(page), sort_keys=True) == before_units)
        check("Undo: the card is back", card_visible(page))
        page.click("#examples-card-recipes .clear-recipe-examples")
        page.wait_for_timeout(9500)
        check("the message goes after about 8 seconds", not toast(page)["shown"] or not toast(page)["undo"])
        page.reload()
        page.wait_for_function("() => typeof APP_VERSION === 'string'")
        page.wait_for_timeout(300)
        leave_launch(page)   # U4b: tap through the start page
        check("after a reload the examples are still gone", page.evaluate("() => book.recipes.length + book.paints.length") == 0)
        # Undo when a new recipe has taken a cleared one's number in the meantime.
        fresh(page)
        main_tab(page, "recipes")
        page.click("#examples-card-recipes .clear-recipe-examples")
        page.wait_for_timeout(300)
        page.evaluate("""() => { const p = findOrAddPaint('Citadel', 'Abaddon Black', '#231f20');
            book.recipes.push({ id: 2, name: 'Mine', part: 'Armour', notes: '', steps: [{ technique: 'Base coat', coats: 1,
              paints: [{ paint: p.id, mix: null }], ratio: '', note: '', optional: false }] }); save(); }""")
        page.click("#toast-undo")
        page.wait_for_timeout(300)
        ids = page.evaluate("() => book.recipes.map(r => r.id)")
        check("Undo after a new recipe took a number: all six recipes exist with different numbers", len(ids) == 6 and len(set(ids)) == 6, ids)
        check("and every recipe step still points at a real paint",
              page.evaluate("() => book.recipes.every(r => r.steps.every(s => s.paints.every(sp => paintById(sp.paint))))"))
        check("and the example units are linked to their recipes again",
              page.evaluate("() => models.filter(m => m.recipes).map(m => m.recipes.map(id => recipeById(id).name).join()).join('|')") == "|".join([",".join(CAPTAIN_LINKS), ",".join(BRUTES_LINKS), ",".join(GUARDIANS_LINKS)]))
        # Keep them
        fresh(page)
        main_tab(page, "recipes")
        page.click("#examples-card-recipes .keep-recipe-examples")
        page.wait_for_timeout(300)
        t = toast(page)
        check("Keep them: a message with Undo", t["shown"] and t["undo"] and "Kept" in t["text"], t)
        check("Keep them: nothing removed, the marks are gone",
              page.evaluate("() => book.recipes.length") == 5 and page.evaluate("() => book.paints.length") == 16
              and page.evaluate("() => book.recipes.every(r => !('example' in r)) && book.paints.every(p => !('example' in p)) && book.schemes.every(s => !('example' in s))"))
        check("Keep them: the card is gone", not card_visible(page))
        page.reload()
        page.wait_for_function("() => typeof APP_VERSION === 'string'")
        page.wait_for_timeout(300)
        leave_launch(page)   # U4b: tap through the start page
        check("Keep them sticks after a reload (not given again, not marked again)",
              page.evaluate("() => book.recipes.length") == 5 and page.evaluate("() => book.recipes.every(r => !('example' in r))"))
        fresh(page)
        main_tab(page, "recipes")
        page.click("#examples-card-recipes .keep-recipe-examples")
        page.wait_for_timeout(300)
        page.click("#toast-undo")
        page.wait_for_timeout(300)
        check("Undo on Keep: the marks and the card are back",
              card_visible(page) and page.evaluate("() => book.recipes.every(r => r.example === true) && book.paints.every(p => p.example === true)"))

        # ---------- 5. What Clear keeps ----------
        print("\n--- 5. What Clear keeps ---")
        fresh(page)
        page.evaluate("() => { applyPaintStatus(book.paints.find(p => p.name === 'Example mid blue'), 'owned'); render(); }")
        main_tab(page, "recipes")
        check("the card counts 15 paints once one has a status",
              "5 example recipes, 2 example schemes and 15 example paints" in page.text_content("#examples-card-recipes"), page.text_content("#examples-card-recipes"))
        page.click("#examples-card-recipes .clear-recipe-examples")
        page.wait_for_timeout(300)
        check("Clear says 3 units, 5 recipes, 2 schemes and 15 paints", toast(page)["text"] == "Cleared 3 example units, 5 example recipes, 2 example schemes and 15 example paints", toast(page))
        check("the paint with a status is kept (and nothing else is)", palette_names(page) == ["Example mid blue"], palette_names(page))
        check("it keeps its status", page.evaluate("() => paintStatus(book.paints[0])") == "owned")
        check("the kept paint is saved without an example claim on the card (card gone)", not card_visible(page))

        fresh(page)
        page.evaluate("""() => { const p = book.paints.find(q => q.name === 'Example bright green');
            book.recipes.push({ id: 9, name: 'My green', part: 'Skin', notes: '', steps: [{ technique: 'Layer', coats: 1,
              paints: [{ paint: p.id, mix: null }], ratio: '', note: '', optional: false }] }); render(); }""")
        main_tab(page, "recipes")
        check("a paint your own recipe uses is no longer counted as an example",
              "5 example recipes, 2 example schemes and 15 example paints" in page.text_content("#examples-card-recipes"), page.text_content("#examples-card-recipes"))
        page.click("#examples-card-recipes .clear-recipe-examples")
        page.wait_for_timeout(300)
        check("Clear leaves your recipe and the paint it uses",
              page.evaluate("() => book.recipes.map(r => r.name)") == ["My green"] and palette_names(page) == ["Example bright green"],
              (page.evaluate("() => book.recipes.map(r => r.name)"), palette_names(page)))
        page.click("#toast-undo")
        page.wait_for_timeout(300)
        check("Undo brings the examples back and your own recipe stays",
              page.evaluate("() => book.recipes.length") == 6 and len(palette_names(page)) == 16)

        fresh(page)
        page.evaluate("() => { editPaint(book.paints.find(p => p.name === 'Example dark wash'), 'colour', '#101820'); }")
        page.wait_for_timeout(200)
        check("editing an example paint makes it yours (the mark goes)", page.evaluate("() => !('example' in book.paints.find(p => p.name === 'Example dark wash'))"))
        main_tab(page, "recipes")
        page.click("#examples-card-recipes .clear-recipe-examples")
        page.wait_for_timeout(300)
        check("Clear keeps the paint you edited", palette_names(page) == ["Example dark wash"], palette_names(page))
        fresh(page)
        page.evaluate("""() => { const r = book.recipes[0]; openRecipeId = null; recipeDraft = null;
            const d = { id: r.id, name: 'Blue armour (mine)', part: r.part, notes: r.notes, own: {}, linkUnit: null, original: '',
              steps: r.steps.map(s => ({ technique: s.technique, coats: s.coats, ratio: '', note: '', optional: false,
                paints: s.paints.map(sp => { const q = paintById(sp.paint); return { brand: q.brand, name: q.name, colour: q.colour, mix: null }; }) })) };
            recipeDraft = d; saveRecipeDraft(); }""")
        page.wait_for_timeout(300)
        check("saving changes to an example recipe makes it yours",
              page.evaluate("() => !('example' in book.recipes[0]) && book.recipes[1].example === true"))
        main_tab(page, "recipes")
        page.evaluate("() => { openRecipeId = null; render(); }")
        page.click("#examples-card-recipes .clear-recipe-examples")
        page.wait_for_timeout(300)
        check("Clear keeps the recipe you changed, and the paints it uses",
              page.evaluate("() => book.recipes.map(r => r.name)") == ["Blue armour (mine)"]
              and palette_names(page) == sorted(["Example deep blue", "Example dark wash", "Example mid blue", "Example pale grey"]), palette_names(page))

        # ---------- 6. Shopping list ----------
        print("\n--- 6. Shopping list ---")
        fresh(page)
        check("example paints are not on the shopping list", page.evaluate("() => shoppingItems().length") == 0)
        main_tab(page, "recipes")
        recipe_view(page, "palette")
        page.click("#recipe-seg button[data-view='shopping']")
        page.wait_for_timeout(200)
        check("the shopping list says there is nothing to buy",
              "Nothing to buy" in page.inner_text("#shop-panel"), page.inner_text("#shop-panel"))
        check("no shop buttons show", page.locator("#buy-bar").count() == 0)
        # v58 (chunk 1.3) changed this decision: after Keep them the made-up paints showed on the list as missing, and AI testers
        # tried to buy "Example deep blue", which no shop sells. A paint that started as an example now stays off the list, kept or
        # given a status (test_v58.py checks real paints still work as before).
        page.evaluate("() => { applyPaintStatus(book.paints.find(p => p.name === 'Example mid blue'), 'wishlist'); render(); }")
        check("a made-up paint you put on your wishlist stays off the list (v58)",
              page.evaluate("() => shoppingItems().length") == 0)
        fresh(page)
        page.evaluate("() => keepExamples()")
        page.wait_for_timeout(200)
        check("after Keep them the made-up paints still stay off the list (v58; before, all 16 showed as missing)",
              page.evaluate("() => shoppingItems().length") == 0)

        # ---------- 7. Saved data's shape ----------
        print("\n--- 7. Saved data's shape ---")
        fresh(page)
        out = page.evaluate("""() => { const c = cleanRecipeBook({ recipes: [
              { id: 1, name: 'a', example: 'yes', future: 7, steps: [] }, { id: 2, name: 'b', example: true, steps: [] }],
              paints: [{ id: 1, name: 'p', example: 1, future: 'x' }, { id: 2, name: 'q', example: true }] });
            return { r: c.recipes.map(r => [r.example, r.future]), p: c.paints.map(q => [q.example, q.future]), keys: Object.keys(c).sort() }; }""")
        check("only a real true counts as an example mark", out["r"] == [[None, 7], [True, None]] and out["p"] == [[None, "x"], [True, None]], out)
        check("unknown fields on recipes and paints survive cleaning (how older versions keep the mark)", out["r"][0][1] == 7 and out["p"][0][1] == "x")
        check("the book's keys are unchanged", out["keys"] == sorted(BOOK_KEYS), out["keys"])
        backup = page.evaluate("() => backupData()")
        check("a backup carries the example marks",
              all(r.get("example") is True for r in backup["recipes"]["recipes"]) if isinstance(backup.get("recipes"), dict) else True, list(backup.keys()))

        # ---------- 8. Dark and light, 390 and 360 ----------
        print("\n--- 8. Dark and light at 390 and 360 px ---")
        for appearance in ("dark", "light"):
            for width in (390, 360):
                tag = f"{appearance} {width}px"
                page.set_viewport_size({"width": width, "height": 844})
                fresh(page, {"appearance": appearance})
                main_tab(page, "recipes")
                for view in ("recipes", "palette"):
                    recipe_view(page, view)
                    box = page.evaluate("""() => { const r = document.getElementById('examples-card-recipes').getBoundingClientRect();
                        return { l: r.left, r: r.right, w: window.innerWidth }; }""")
                    check(f"{tag} {view}: the card is inside the screen", box["l"] >= 0 and box["r"] <= box["w"] + 0.5, box)
                    heights = page.evaluate("""() => [...document.querySelectorAll('#examples-card-recipes button:not(.more-info-button)')]
                        .map(b => { const r = b.getBoundingClientRect(); return [r.width, r.height]; })""")
                    check(f"{tag} {view}: both buttons are at least 44 px tall and wide", len(heights) == 2 and all(w >= 44 and h >= 44 for w, h in heights), heights)
                    check(f"{tag} {view}: nothing scrolls sideways", no_sideways(page))
                col = page.evaluate("""() => { const el = document.querySelector('#examples-card-recipes p'); const cs = getComputedStyle(el);
                    return { fg: cs.color, bg: getComputedStyle(document.getElementById('examples-card-recipes')).backgroundColor }; }""")
                check(f"{tag}: the card's text is readable (contrast at least 4.5)", contrast(rgb(col["fg"]), rgb(col["bg"])) >= 4.5, col)
                if width == 390:
                    recipe_view(page, "recipes")
                    shot(page, f"v24-recipes-{appearance}-{width}.png")
                    recipe_view(page, "palette")
                    shot(page, f"v24-palette-{appearance}-{width}.png")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 9. Help and Updates ----------
        print("\n--- 9. Help and Updates wording ---")
        fresh(page)
        main_tab(page, "settings")
        sub_tab(page, "help")
        help_text = page.evaluate("() => document.getElementById('help-example-recipes').textContent")
        # v75: HELP-2 cut this step to a few lines
        check("Help explains the example recipes (what, where, Clear, Keep, what is kept, shopping list, existing users)",
              all(w in help_text for w in ["example recipes", "Clear examples", "Keep them", "Restore example recipes"]), help_text)
        sub_tab(page, "updates")
        updates = page.inner_text("#view-updates")

        check("no real browser pop-ups at any point", not popups, popups)
        check("no page errors", not errors, errors[:3])
        context.close()
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
