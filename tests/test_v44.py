"""v44 tests for Minifolio: richer example recipes and schemes, and Restore example recipes in Settings (E1).

Checks:
1. Version numbers ("v44 or later"), every script tag and both comments, sw.js, the Updates entry, kept things
   (CSP, DATA_VERSION 1, storage names, no code in index.html).
2. A brand-new start: five example recipes, two example schemes that group them, sixteen made-up paints, linked to
   the example units that suit them, all marked "example: true"; the card on the Recipes tab counts them.
3. People who already have data are NOT given examples by the automatic start-up seeding.
4. Word scan: nothing the examples add has a Games Workshop name (recipes, schemes, paints, card, Help, Updates, messages).
5. Clear examples (real taps): removes example recipes, schemes and the example paints nothing of yours uses; what you
   edited, used or gave a status stays; Undo restores everything exactly (also when a number was taken meanwhile).
6. Keep them: marks go (schemes too), nothing is removed, Undo puts them back.
7. The card does not keep showing once everything is cleared or kept (all pages, after a reload, after Undo it returns).
8. Settings -> Restore example recipes: after Clear it gives back exactly the fresh-start examples; with leftovers it adds
   only what is missing; never duplicates; works for existing users; never changes your own data; the card returns.
9. Saved data's shape: schemes keep only a real true mark, unknown fields survive, a backup carries the marks.
10. Safety: text from your data stays plain text, example paints stay off the shopping list.
11. Phone widths 360 to 400 px, dark and light: the card, the Schemes page and the Settings section fit and are readable.
12. Help and Updates wording. 13. No real pop-ups, page errors or CSP errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t   # shared helpers and the Games Workshop word lists

URL, read, shot, no_sideways = t.URL, t.read, t.shot, t.no_sideways
GW_WORDS, GW_MORE = t.GW_WORDS, t.GW_MORE
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

OLD_WORDS = re.compile(r"\b(boyz|boy|liberators?|nuln|macragge|calgar|fenrisian|waaagh|agrax|warboss|skarsnik|baal|seraphim|ushabti|"
                       r"wraithbone|death guard|stormcast|eternals?|ork|abaddon|retributor|mephiston|khorne|leadbelcher|"
                       r"mournfang|wazdakka|zandri)\b", re.I)

def dirty(text):
    return bool(GW_WORDS.search(text) or GW_MORE.search(text) or OLD_WORDS.search(text))

V21_4_CSP = ("default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; "
             "img-src 'self' blob: data: https://dim3ry.goatcounter.com/count; media-src 'self' blob:; font-src 'self'; connect-src 'self'; worker-src 'self'; "
             "manifest-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-src 'none'")
RECIPES = ["Blue armour", "Gold metal", "Green skin", "Glowing eyes", "Stone base"]
PARTS = ["Armour", "Metal", "Skin", "Eyes", "Base"]
SCHEMES = {"Blue army colours": ("Blue army", ["Blue armour", "Gold metal", "Glowing eyes", "Stone base"]),
           "Green army colours": ("Green army", ["Green skin", "Glowing eyes", "Stone base"])}
PAINTS = sorted(["Example deep blue", "Example dark wash", "Example mid blue", "Example pale grey",
                 "Example mid green", "Example brown wash", "Example bright green", "Example pale green",
                 "Example dark gold", "Example bright gold", "Example pale gold", "Example deep red",
                 "Example bright orange", "Example pale yellow", "Example dark grey", "Example mid grey"])
LINKS = {"Captain": ["Blue armour", "Gold metal", "Glowing eyes", "Stone base"],
         "Brutes": ["Green skin", "Glowing eyes", "Stone base"],
         "Guardians": ["Gold metal", "Stone base"]}
BOOK_KEYS = ["paints", "parts", "recipes", "schemes", "shorthand", "techniques", "v15"]
STAGES = ["Unassembled", "Part assembled", "Assembled", "Primed", "Part painted",
          "Battle ready", "Painted with issues", "Parade ready"]
ALL_WORDS = "5 example recipes, 2 example schemes and 16 example paints"

def wait_loaded(page):
    page.wait_for_function("() => typeof APP_VERSION === 'string'")
    page.wait_for_timeout(300)

def reload(page):
    page.reload()
    wait_loaded(page)

def fresh(page, settings=None):
    """A brand-new start: nothing saved at all (apart from the look, if asked)."""
    page.goto(URL)
    page.evaluate("""async (s) => { localStorage.clear();
        if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s));
        await new Promise(done => { const r = indexedDB.deleteDatabase('shades-of-grey-photos');
                                    r.onsuccess = r.onerror = r.onblocked = () => done(); }); }""", settings)
    reload(page)

def existing(page, units, book=None, settings=None):
    """Someone who has used the app before: units saved (and maybe recipes and settings)."""
    page.goto(URL)
    page.evaluate("""async ([u, b, s]) => { localStorage.clear();
        localStorage.setItem('mini-tracker-models', JSON.stringify(u));
        if (b) localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b));
        if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s));
        await new Promise(done => { const r = indexedDB.deleteDatabase('shades-of-grey-photos');
                                    r.onsuccess = r.onerror = r.onblocked = () => done(); }); }""", [units, book, settings])
    reload(page)

def main_tab(page, name):
    page.evaluate("() => document.activeElement && document.activeElement.blur()")
    page.click(f'nav button[data-tab="{name}"]')
    page.wait_for_timeout(200)

def sub_tab(page, name):
    page.click(f'#more-seg button[data-page="{name}"]')
    page.wait_for_timeout(150)

def recipe_view(page, view):
    page.click(f'#recipe-seg button[data-view="{view}"]')
    page.wait_for_timeout(200)

def saved_book(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-recipes') || 'null')")

def saved_units(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('mini-tracker-models') || '[]')")

def saved_settings(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-settings') || '{}')")

def snap(page):
    """The saved recipe book and units as sorted text, to compare 'exactly as before'."""
    return json.dumps(saved_book(page), sort_keys=True), json.dumps(saved_units(page), sort_keys=True)

def card_shown(page):
    return page.locator("#examples-card-recipes").is_visible()

def card_text(page):
    return page.text_content("#examples-card-recipes") if card_shown(page) else ""   # v50: the explanation sits behind More info

def toast(page):
    return page.evaluate("""() => ({ text: document.getElementById('toast-text').textContent,
        shown: !document.getElementById('toast').classList.contains('hidden'),
        undo: !document.getElementById('toast-undo').classList.contains('hidden') })""")

def names(page, what):
    return page.evaluate(f"() => book.{what}.map(x => x.name)")

def palette_names(page):
    return sorted(names(page, "paints"))

def clear_on_card(page):
    main_tab(page, "recipes")
    page.click("#examples-card-recipes .clear-recipe-examples")
    page.wait_for_timeout(300)

def restore_in_settings(page):
    main_tab(page, "settings")
    page.evaluate("() => document.getElementById('restore-examples').scrollIntoView({ block: 'center' })")
    page.click("#restore-examples")
    page.wait_for_timeout(300)

def own_recipe(page, name="My recipe", paint="My own paint", colour="#336699"):
    page.evaluate("""([n, pn, c]) => { const p = findOrAddPaint('', pn, c);
        book.recipes.push({ id: Math.max(0, ...book.recipes.map(r => r.id)) + 1, name: n, part: 'Armour', notes: '',
          steps: [{ technique: 'Base coat', coats: 1, paints: [{ paint: p.id, mix: null }], ratio: '', note: '', optional: false }] }); render(); }""",
                  [name, paint, colour])

def edit_recipe(page, old, new):
    page.evaluate("""([o, n]) => { const r = book.recipes.find(x => x.name === o); openRecipeId = null; recipeDraft = null;
        recipeDraft = { id: r.id, name: n, part: r.part, notes: r.notes, own: {}, linkUnit: null, original: '',
          steps: r.steps.map(s => ({ technique: s.technique, coats: s.coats, ratio: '', note: '', optional: false,
            paints: s.paints.map(sp => { const q = paintById(sp.paint); return { brand: q.brand, name: q.name, colour: q.colour, mix: null }; }) })) };
        saveRecipeDraft(); openRecipeId = null; recipeDraft = null; render(); }""", [old, new])
    page.wait_for_timeout(250)

def edit_scheme(page, old, new):
    page.evaluate("""([o, n]) => { startScheme(book.schemes.find(s => s.name === o)); schemeDraft.name = n; schemeDraft.auto = false; saveScheme(); }""", [old, new])
    page.wait_for_timeout(250)

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
        html, app, sw = read("index.html"), read("app.js"), read("sw.js")
        version = page.evaluate("APP_VERSION")
        num = version[1:]
        check("APP_VERSION is v44 or later", float(num) >= 44, version)
        check("version is a plain number", re.fullmatch(r"v\d+(\.\d+)?", version) is not None, version)
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        check("sw.js VERSION matches APP_VERSION", m and m.group(1) == version, m and m.group(1))
        tags = re.findall(r'<script src="([^"?]+)\?v=([\d.]+)"', html)
        check("all six script tags are there and carry ?v= matching APP_VERSION",
              sorted(a for a, _ in tags) == sorted(["early.js", "colour.js", "schemes.js", "detail-recipes.js", "basing-tips.js", "app.js"])
              and all(v == num for _, v in tags), tags)
        check("the comment in index.html names the same number", f'The "?v={num}" makes' in html)
        check("the comment above APP_VERSION names the same number", f'"app.js?v={num}"' in app)
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v44')")
        check("Updates has a v44 entry with two lines", entry and len(entry["changes"]) >= 2, entry)
        check("the newest Updates entry is the current version", page.evaluate("CHANGELOG[0].version") == version)
        csp_meta = re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]+)"', html, re.S)
        check("the CSP is unchanged", csp_meta and " ".join(csp_meta.group(1).split()) == V21_4_CSP, csp_meta and csp_meta.group(1))
        check("DATA_VERSION is still 1", page.evaluate("DATA_VERSION") == 1)
        check("storage names unchanged",
              all(k in app for k in ['STORAGE_KEY = "mini-tracker-models"', 'SETTINGS_KEY = "shades-of-grey-settings"',
                                     'RECIPES_KEY = "shades-of-grey-recipes"']))
        check("no code was put inside index.html", len(re.findall(r"<script(?![^>]*\bsrc=)[^>]*>\s*\S", html)) == 0)

        # ---------- 2. A brand-new start ----------
        print("\n--- 2. A brand-new start ---")
        fresh(page)
        recipes = page.evaluate("() => book.recipes.map(r => ({ name: r.name, part: r.part, example: r.example, steps: r.steps.length }))")
        check("five example recipes in order", [r["name"] for r in recipes] == RECIPES, recipes)
        check("their parts are Armour, Metal, Skin, Eyes and Base", [r["part"] for r in recipes] == PARTS, recipes)
        check("all are marked as examples, with 4, 4, 4, 3 and 3 steps",
              all(r["example"] is True for r in recipes) and [r["steps"] for r in recipes] == [4, 4, 4, 3, 3], recipes)
        check("every part and technique they use is one the app already offers",
              page.evaluate("() => book.recipes.every(r => book.parts.includes(r.part) && r.steps.every(s => book.techniques.includes(s.technique)))"))
        check("the sixteen paints are in the palette", palette_names(page) == PAINTS, palette_names(page))
        check("every example paint is marked, has no brand and a real colour",
              page.evaluate("() => book.paints.every(p => p.example === true && p.brand === '' && p.colour !== DEFAULT_PAINT_COLOUR)"))
        check("no example paint shares a name with a real paint in the built-in list",
              not page.evaluate("() => book.paints.some(p => KNOWN_PAINTS.some(k => sameText(k.name, p.name)))"))
        check("no paint has a status yet", page.evaluate("() => book.paints.every(p => paintStatus(p) === '')"))
        sch = page.evaluate("""() => book.schemes.map(s => ({ name: s.name, faction: s.faction, auto: s.auto, example: s.example,
                                recipes: s.recipes.map(id => recipeById(id).name) }))""")
        check("two example schemes with plain names", sorted(s["name"] for s in sch) == sorted(SCHEMES), sch)
        check("each has the faction of the example units and groups the right recipes",
              all(SCHEMES[s["name"]] == (s["faction"], s["recipes"]) for s in sch), sch)
        check("both are marked as examples, and 'new units get it' is off", all(s["example"] is True and s["auto"] is False for s in sch), sch)
        units = saved_units(page)
        check("the example units are still there", [u["name"] for u in units] == ["Captain", "Brutes", "Guardians"], units)
        id_name = page.evaluate("() => Object.fromEntries(book.recipes.map(r => [r.id, r.name]))")
        linked = {u["name"]: [id_name[str(i)] for i in u.get("recipes", [])] for u in units}
        check("each recipe is linked to the example units that suit it", linked == LINKS, linked)
        check("the two schemes' factions match example units", {u["faction"] for u in units} >= {"Blue army", "Green army"})
        saved = saved_book(page)
        check("saved: five recipes, two schemes and sixteen paints carry the example mark",
              [r.get("example") for r in saved["recipes"]] == [True] * 5 and [s.get("example") for s in saved["schemes"]] == [True] * 2
              and sum(1 for q in saved["paints"] if q.get("example") is True) == 16, saved)
        check("saved settings remember the examples were given", saved_settings(page).get("recipeExamplesChecked") is True)
        check("the saved recipe book has the same keys as before", sorted(saved.keys()) == sorted(BOOK_KEYS), sorted(saved.keys()))
        main_tab(page, "recipes")
        check("the Recipes tab lists all five", page.locator("#recipe-list li").count() == 5, page.locator("#recipe-list li").count())
        check("the card shows and counts recipes, schemes and paints", card_shown(page) and "These are examples." in card_text(page)
              and ALL_WORDS in card_text(page), card_text(page))
        check("the card has Clear examples and Keep them",
              page.locator("#examples-card-recipes .clear-recipe-examples").inner_text() == "Clear examples"
              and page.locator("#examples-card-recipes .keep-recipe-examples").inner_text() == "Keep them")
        recipe_view(page, "schemes")
        check("the card also shows on Schemes", card_shown(page))
        check("the Schemes page lists both example schemes with their recipes",
              page.locator("#scheme-list li").count() == 2 and "Blue army colours" in page.inner_text("#scheme-list")
              and "4 recipes" in page.inner_text("#scheme-list") and "3 recipes" in page.inner_text("#scheme-list"), page.inner_text("#scheme-list"))
        check("the example units already have their schemes (no 'Apply' button)", page.locator("#scheme-list button:has-text('Apply')").count() == 0)
        recipe_view(page, "palette")
        check("the card also shows on Your Palette, which lists sixteen paints", card_shown(page) and page.locator("#paint-list li.paint-item").count() == 16)
        recipe_view(page, "recipes")
        page.click("#recipe-list li >> nth=0")
        page.wait_for_timeout(250)
        check("the card is hidden while a recipe is open", not card_shown(page))
        page.evaluate("history.back()")
        page.wait_for_timeout(300)
        check("and it is back when the recipe is closed", card_shown(page))
        main_tab(page, "units")
        check("the units card is separate and still has its own single Clear examples button",
              page.locator("#examples-card").is_visible() and page.locator("#examples-card .clear-examples").count() == 1)

        # ---------- 3. People who already have data ----------
        print("\n--- 3. People who already have data ---")
        units_only = [{"id": 1, "name": "Intercessors", "hobby": "Sci-fi", "faction": "Red army", "stage": 3, "count": 5}]
        own_book = {"parts": ["Whole model", "Armour"], "techniques": ["Base coat"], "v15": True, "shorthand": {},
                    "schemes": [{"id": 1, "name": "My red", "faction": "Red army", "auto": True, "recipes": [1]}],
                    "paints": [{"id": 1, "brand": "", "name": "My black", "colour": "#231f20"}],
                    "recipes": [{"id": 1, "name": "My black", "part": "Armour", "notes": "", "steps": [
                        {"technique": "Base coat", "coats": 1, "paints": [{"paint": 1, "mix": None}]}]}]}
        existing(page, units_only, settings={"palette": "ice", "stages": STAGES, "doneFrom": 5, "examplesChecked": True})
        check("saved units and settings, no recipes: nothing is added",
              page.evaluate("() => book.recipes.length + book.paints.length + book.schemes.length") == 0)
        main_tab(page, "recipes")
        check("and there is no card", not card_shown(page))
        existing(page, units_only)
        check("saved units and no settings at all: nothing is added",
              page.evaluate("() => book.recipes.length + book.paints.length + book.schemes.length") == 0)
        existing(page, units_only, own_book)
        check("someone with their own recipes and scheme: nothing is added",
              names(page, "recipes") == ["My black"] and names(page, "schemes") == ["My red"] and names(page, "paints") == ["My black"])
        page.goto(URL)
        page.evaluate("""(b) => { localStorage.clear(); localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b)); }""", own_book)
        reload(page)
        check("no units saved but a recipe book is: it is left alone", names(page, "recipes") == ["My black"] and names(page, "schemes") == ["My red"])
        empty_book = {"parts": ["Whole model"], "techniques": ["Layer"], "paints": [], "recipes": [], "schemes": [], "shorthand": {}, "v15": True}
        page.goto(URL)
        page.evaluate("""(b) => { localStorage.clear(); localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b)); }""", empty_book)
        reload(page)
        check("an empty saved recipe book is not a new start: nothing is added",
              page.evaluate("() => book.recipes.length + book.paints.length + book.schemes.length") == 0)
        fresh(page)
        clear_on_card(page)
        reload(page)
        check("after Clear and a reload the examples do not come back (recipes, schemes or paints)",
              page.evaluate("() => book.recipes.length + book.paints.length + book.schemes.length") == 0)
        page.evaluate("() => localStorage.removeItem('mini-tracker-models')")
        reload(page)
        check("even with the units list gone from storage, cleared examples are not given again",
              page.evaluate("() => book.recipes.length + book.paints.length + book.schemes.length") == 0)

        # ---------- 4. Word scan ----------
        print("\n--- 4. No Games Workshop names ---")
        fresh(page)
        main_tab(page, "recipes")
        everything = page.evaluate("() => JSON.stringify({ r: book.recipes, s: book.schemes, p: book.paints, u: models })")
        check("recipes, schemes, paints and example units have no Games Workshop word", not dirty(everything), everything[:300])
        check("the card has none", not dirty(card_text(page)), card_text(page))
        main_tab(page, "settings")
        restore_text = page.evaluate("() => document.getElementById('restore-examples-section').textContent")
        check("the Settings section has none", not dirty(restore_text), restore_text)
        sub_tab(page, "help")
        help_text = page.evaluate("() => document.getElementById('help-example-recipes').textContent")
        check("the Help lines about the examples have none", not dirty(help_text), help_text)
        entry_text = " ".join(page.evaluate("CHANGELOG.find(r => r.version === 'v44').changes"))
        check("the v44 Updates text has none", not dirty(entry_text), entry_text)
        a0 = app.index("----- v24: EXAMPLE RECIPES AND PAINTS")
        src = app[a0:app.index("----- v21: JUMP TO STAGE", a0)]
        check("the example code was found (so the scans of it mean something)", len(src) > 8000 and "function addExamples" in src and "function restoreExampleRecipes" in src, len(src))
        check("the new example code has none", not dirty(re.sub(r"^\s*//.*$", "", src, flags=re.M)), "")
        fresh(page)
        clear_on_card(page)
        words = [toast(page)["text"]]
        restore_in_settings(page)
        words.append(toast(page)["text"])
        check("the Clear and Restore messages have none", not any(dirty(w) for w in words), words)

        # ---------- 5. Clear examples ----------
        print("\n--- 5. Clear examples ---")
        fresh(page)
        before = snap(page)
        clear_on_card(page)
        tt = toast(page)
        check("a message says exactly what was cleared, with Undo",
              tt["shown"] and tt["undo"] and tt["text"] == "Cleared " + ALL_WORDS, tt)
        check("no recipes, schemes or paints are left", page.evaluate("() => book.recipes.length + book.schemes.length + book.paints.length") == 0)
        check("the card is gone", not card_shown(page))
        check("the example units are untouched except that the recipe links are gone",
              [u["name"] for u in saved_units(page)] == ["Captain", "Brutes", "Guardians"] and all("recipes" not in u for u in saved_units(page)))
        recipe_view(page, "schemes")
        check("the Schemes page no longer lists the examples", "Blue army colours" not in page.inner_text("#scheme-list"))
        saved = saved_book(page)
        check("saved: the book has no recipes, schemes or paints", saved["recipes"] == [] and saved["schemes"] == [] and saved["paints"] == [])
        page.click("#toast-undo")
        page.wait_for_timeout(300)
        check("Undo: the saved recipe book is exactly as before", snap(page)[0] == before[0])
        check("Undo: the units and their links are exactly as before", snap(page)[1] == before[1])
        check("Undo: the card is back", card_shown(page))

        # what is yours is kept
        fresh(page)
        page.evaluate("() => { applyPaintStatus(book.paints.find(p => p.name === 'Example mid blue'), 'owned'); render(); }")
        own_recipe(page, "My green", "Example bright green", "#6fa03a")
        page.evaluate("""() => { const m = book.recipes.find(r => r.name === 'My green'); m.id = 9; render(); }""")
        edit_recipe(page, "Gold metal", "Gold metal (mine)")
        edit_scheme(page, "Green army colours", "Green army colours (mine)")
        page.evaluate("""() => { const eyes = book.recipes.find(r => r.name === 'Glowing eyes').id;
            book.schemes.push({ id: Math.max(0, ...book.schemes.map(s => s.id)) + 1, name: 'My scheme', faction: 'Red army', auto: false,
                                recipes: [eyes, 9] }); render(); }""")
        check("editing a recipe or a scheme makes it yours (the mark goes)",
              page.evaluate("() => !('example' in book.recipes.find(r => r.name === 'Gold metal (mine)')) && !('example' in book.schemes.find(s => s.name === 'Green army colours (mine)'))"))
        main_tab(page, "recipes")
        check("the card counts only what is still an example (4 recipes, 1 scheme, 10 paints)",
              "4 example recipes, 1 example scheme and 10 example paints" in card_text(page), card_text(page))
        mine_before = page.evaluate("""() => JSON.stringify({ gm: book.recipes.find(r => r.name === 'Gold metal (mine)'),
            my: book.recipes.find(r => r.name === 'My green'), ms: book.schemes.find(s => s.name === 'My scheme') })""")
        before = snap(page)
        page.click("#examples-card-recipes .clear-recipe-examples")
        page.wait_for_timeout(300)
        check("Clear says 4 recipes, 1 scheme and 10 paints", toast(page)["text"] == "Cleared 4 example recipes, 1 example scheme and 10 example paints", toast(page))
        check("what is yours stays: the edited recipe and your own recipe",
              names(page, "recipes") == ["Gold metal (mine)", "My green"], names(page, "recipes"))
        check("what is yours stays: the edited scheme and your own scheme",
              sorted(names(page, "schemes")) == ["Green army colours (mine)", "My scheme"], names(page, "schemes"))
        check("what is yours stays: the paint with a status, the paints your recipes use",
              palette_names(page) == sorted(["Example mid blue", "Example bright green", "Example dark gold", "Example dark wash",
                                             "Example bright gold", "Example pale gold"]), palette_names(page))
        check("the paint with a status keeps it", page.evaluate("() => paintStatus(book.paints.find(p => p.name === 'Example mid blue'))") == "owned")
        check("no scheme is left pointing at a recipe that is gone",
              page.evaluate("() => book.schemes.every(s => s.recipes.every(id => !!recipeById(id)))"))
        check("your own scheme keeps your own recipe", page.evaluate("() => book.schemes.find(s => s.name === 'My scheme').recipes.length") == 1)
        check("the card is gone", not card_shown(page))
        page.click("#toast-undo")
        page.wait_for_timeout(300)
        check("Undo: everything is exactly as before (recipes, schemes, paints, units)", snap(page) == before)
        check("Undo: your own things are untouched",
              page.evaluate("""() => JSON.stringify({ gm: book.recipes.find(r => r.name === 'Gold metal (mine)'),
            my: book.recipes.find(r => r.name === 'My green'), ms: book.schemes.find(s => s.name === 'My scheme') })""") == mine_before)

        # Undo when numbers were taken meanwhile
        fresh(page)
        clear_on_card(page)
        page.evaluate("""() => { const p = findOrAddPaint('', 'Taken paint', '#223344');
            book.recipes.push({ id: 2, name: 'Mine', part: 'Armour', notes: '', steps: [{ technique: 'Base coat', coats: 1,
              paints: [{ paint: p.id, mix: null }], ratio: '', note: '', optional: false }] });
            book.schemes.push({ id: 1, name: 'Mine too', faction: 'Red army', auto: false, recipes: [2] }); render(); }""")
        page.click("#toast-undo")
        page.wait_for_timeout(300)
        ids = page.evaluate("() => [book.recipes.map(r => r.id), book.schemes.map(s => s.id), book.paints.map(p => p.id)]")
        check("Undo after new things took numbers: everything exists and every number is different",
              [len(x) for x in ids] == [6, 3, 17] and all(len(set(x)) == len(x) for x in ids), ids)
        check("every step still points at a real paint and every scheme at real recipes",
              page.evaluate("() => book.recipes.every(r => r.steps.every(s => s.paints.every(sp => paintById(sp.paint)))) && book.schemes.every(s => s.recipes.every(id => recipeById(id)))"))
        check("the example schemes still group the right recipes (by name)",
              page.evaluate("() => Object.fromEntries(book.schemes.filter(s => s.example).map(s => [s.name, s.recipes.map(id => recipeById(id).name)]))") == {k: v[1] for k, v in SCHEMES.items()})
        check("and the example units are linked to their recipes again",
              page.evaluate("() => Object.fromEntries(models.filter(m => m.recipes).map(m => [m.name, m.recipes.map(id => recipeById(id).name)]))") == LINKS)
        check("your own recipe and scheme are still there", "Mine" in names(page, "recipes") and "Mine too" in names(page, "schemes"))

        # only schemes left
        fresh(page)
        page.evaluate("() => { for (const r of book.recipes.slice()) deleteRecipeNow(r.id); }")
        page.wait_for_timeout(200)
        main_tab(page, "recipes")
        check("with only example schemes left, the card still shows and says so", card_shown(page) and "2 example schemes" in card_text(page), card_text(page))
        page.click("#examples-card-recipes .clear-recipe-examples")
        page.wait_for_timeout(300)
        check("Clear then says only that", toast(page)["text"] == "Cleared 2 example schemes", toast(page))

        # ---------- 6. Keep them ----------
        print("\n--- 6. Keep them ---")
        fresh(page)
        main_tab(page, "recipes")
        page.click("#examples-card-recipes .keep-recipe-examples")
        page.wait_for_timeout(300)
        tt = toast(page)
        check("Keep them: a message with Undo", tt["shown"] and tt["undo"] and "Kept" in tt["text"], tt)
        check("nothing removed, every mark gone (recipes, schemes and paints)",
              page.evaluate("() => book.recipes.length") == 5 and page.evaluate("() => book.schemes.length") == 2
              and page.evaluate("() => book.paints.length") == 16
              and page.evaluate("() => [...book.recipes, ...book.schemes, ...book.paints].every(x => !('example' in x))"))
        check("the card is gone", not card_shown(page))
        reload(page)
        check("Keep sticks after a reload (nothing given again, nothing marked again)",
              page.evaluate("() => book.recipes.length") == 5 and page.evaluate("() => book.schemes.length") == 2
              and page.evaluate("() => [...book.recipes, ...book.schemes, ...book.paints].every(x => !('example' in x))"))
        fresh(page)
        main_tab(page, "recipes")
        page.click("#examples-card-recipes .keep-recipe-examples")
        page.wait_for_timeout(300)
        page.click("#toast-undo")
        page.wait_for_timeout(300)
        check("Undo on Keep: the marks (schemes too) and the card are back",
              card_shown(page) and page.evaluate("() => [...book.recipes, ...book.schemes, ...book.paints].every(x => x.example === true)"))

        # ---------- 7. The card does not keep showing ----------
        print("\n--- 7. The card goes and stays gone ---")
        fresh(page)
        clear_on_card(page)
        gone = []
        for view in ("recipes", "schemes", "palette"):
            recipe_view(page, view)
            gone.append(not card_shown(page) and page.evaluate("() => document.getElementById('examples-card-recipes').getBoundingClientRect().height") == 0)
        check("after Clear it is gone on every page of the Recipes tab (no space left either)", all(gone), gone)
        main_tab(page, "units")
        main_tab(page, "recipes")
        check("and stays gone after leaving the tab and coming back", not card_shown(page))
        page.wait_for_timeout(9500)
        check("the Undo message goes by itself after about 8 seconds", not toast(page)["shown"] or not toast(page)["undo"])
        reload(page)
        main_tab(page, "recipes")
        check("and stays gone after a reload", not card_shown(page))
        fresh(page)
        main_tab(page, "recipes")
        page.click("#examples-card-recipes .keep-recipe-examples")
        page.wait_for_timeout(300)
        gone = []
        for view in ("recipes", "schemes", "palette"):
            recipe_view(page, view)
            gone.append(not card_shown(page))
        check("after Keep it is gone on every page too", all(gone), gone)
        reload(page)
        main_tab(page, "recipes")
        check("and stays gone after a reload", not card_shown(page))
        # leftovers that are yours do not keep the card up either
        fresh(page)
        page.evaluate("() => { for (const p of book.paints) applyPaintStatus(p, 'owned'); render(); }")
        edit_recipe(page, "Blue armour", "A")
        main_tab(page, "recipes")
        page.click("#examples-card-recipes .clear-recipe-examples")
        page.wait_for_timeout(300)
        check("with paints you own and a recipe you changed left over, the card is still gone after Clear", not card_shown(page))
        reload(page)
        main_tab(page, "recipes")
        check("and after a reload", not card_shown(page))

        # ---------- 8. Settings: Restore example recipes ----------
        print("\n--- 8. Restore example recipes ---")
        fresh(page)
        main_tab(page, "settings")
        in_settings = page.evaluate("""() => { const s = document.getElementById('restore-examples-section');
            return { inSettings: !!s && document.getElementById('view-settings').contains(s),
                     inRecipes: document.getElementById('view-recipes').contains(s),
                     heading: s.querySelector('h3').textContent, button: document.getElementById('restore-examples').textContent,
                     cls: document.getElementById('restore-examples').className, hint: document.getElementById('restore-examples-hint').textContent }; }""")
        check("the section is in Settings, not on the Recipes page", in_settings["inSettings"] and not in_settings["inRecipes"], in_settings)
        check("it is called Restore example recipes, and the button is plain (not loud)",
              in_settings["heading"] == "Restore example recipes" and in_settings["button"] == "Restore example recipes"
              and "plain-button" in in_settings["cls"] and "danger" not in in_settings["cls"] and "primary" not in in_settings["cls"], in_settings)
        check("the hint says what it does, that your own things are never changed and nothing is added twice",
              all(w in in_settings["hint"] for w in ["example recipes, schemes and paints", "never changed", "twice"]), in_settings["hint"])
        check("the Recipes page itself has no Restore button", page.locator("#view-recipes button:has-text('Restore example')").count() == 0)

        # a) after Clear, Restore gives back exactly the fresh start
        fresh(page)
        before = snap(page)
        clear_on_card(page)
        restore_in_settings(page)
        tt = toast(page)
        check("Restore after Clear: a message says what was added",
              tt["shown"] and tt["text"] == "Added " + ALL_WORDS + ". You'll find them on the Recipes tab.", tt)
        check("the recipe book is exactly the fresh start's again", snap(page)[0] == before[0])
        check("the example units are linked exactly as at the start", snap(page)[1] == before[1])
        main_tab(page, "recipes")
        check("the Recipes card is back with Clear and Keep",
              card_shown(page) and page.locator("#examples-card-recipes .clear-recipe-examples").count() == 1
              and page.locator("#examples-card-recipes .keep-recipe-examples").count() == 1 and ALL_WORDS in card_text(page), card_text(page))
        page.click("#examples-card-recipes .clear-recipe-examples")
        page.wait_for_timeout(300)
        check("and Clear works on the restored examples", page.evaluate("() => book.recipes.length + book.schemes.length + book.paints.length") == 0)

        # b) everything is there: nothing happens
        fresh(page)
        before = snap(page)
        restore_in_settings(page)
        tt = toast(page)
        check("Restore with everything still there says so and changes nothing",
              tt["shown"] and "already here" in tt["text"] and snap(page) == before, tt)
        restore_in_settings(page)
        check("pressing it again changes nothing either", snap(page) == before)

        # c) leftovers: only what is missing is added
        fresh(page)
        page.evaluate("""() => { deleteRecipeNow(book.recipes.find(r => r.name === 'Gold metal').id);
            deleteSchemeNow(book.schemes.find(s => s.name === 'Green army colours').id); }""")
        page.wait_for_timeout(200)
        restore_in_settings(page)
        tt = toast(page)
        check("Restore adds only what is missing (1 recipe, 1 scheme and the 3 gold paints)",
              tt["text"] == "Added 1 example recipe, 1 example scheme and 3 example paints. You'll find them on the Recipes tab.", tt)
        rn = names(page, "recipes")
        check("every example is there once", sorted(rn) == sorted(RECIPES), rn)
        check("no recipe, scheme or paint name appears twice",
              len({x.lower() for x in rn}) == len(rn) and len(set(names(page, "schemes"))) == 2
              and len(set(palette_names(page))) == len(palette_names(page)), (rn, names(page, "schemes")))
        check("the restored recipe is marked and linked to the example units again",
              page.evaluate("() => { const r = book.recipes.find(x => x.name === 'Gold metal'); return r.example === true && models.filter(m => (m.recipes || []).includes(r.id)).map(m => m.name).join() === 'Captain,Guardians'; }"))
        check("the scheme that was still there is left as it was (Restore does not rewrite it)",
              page.evaluate("() => book.schemes.find(s => s.name === 'Blue army colours').recipes.length") == 3)

        # c2) your own recipe with an example's name (whatever the capitals) counts as already there
        fresh(page)
        clear_on_card(page)
        own_recipe(page, "BLUE ARMOUR", "My own paint", "#445566")
        own_before = page.evaluate("() => JSON.stringify(book.recipes.find(r => r.name === 'BLUE ARMOUR'))")
        restore_in_settings(page)
        tt = toast(page)
        check("a recipe of yours named like an example counts as already there (4 recipes added, not 5; its two own paints not made)",
              tt["text"] == "Added 4 example recipes, 2 example schemes and 14 example paints. You'll find them on the Recipes tab.", tt)
        rn = names(page, "recipes")
        check("there is no second Blue armour", [x.lower() for x in rn].count("blue armour") == 1 and "BLUE ARMOUR" in rn, rn)
        check("your recipe is exactly as it was", page.evaluate("() => JSON.stringify(book.recipes.find(r => r.name === 'BLUE ARMOUR'))") == own_before)
        check("the example scheme groups your recipe in place of the one that was not added",
              page.evaluate("() => book.schemes.find(s => s.name === 'Blue army colours').recipes.map(id => recipeById(id).name)") == ["BLUE ARMOUR", "Gold metal", "Glowing eyes", "Stone base"])
        main_tab(page, "recipes")
        page.click("#examples-card-recipes .clear-recipe-examples")
        page.wait_for_timeout(300)
        check("Clear after that keeps your recipe (and removes the schemes that grouped it)",
              names(page, "recipes") == ["BLUE ARMOUR"] and names(page, "schemes") == [])

        # d) leftovers after Clear: what is yours is reused as it is
        fresh(page)
        clear_on_card(page)
        page.evaluate("""() => { book.paints.push({ id: Math.max(0, ...book.paints.map(p => p.id)) + 1, brand: '', name: 'Example deep blue', colour: '#123456' }); render(); }""")
        own_recipe(page, "Mine blue", "Example deep blue", "#123456")
        mine = page.evaluate("() => JSON.stringify(book.paints.find(p => p.name === 'Example deep blue'))")
        restore_in_settings(page)
        tt = toast(page)
        check("Restore reuses a paint you already have by that name (15 new paints, not 16)",
              tt["text"] == "Added 5 example recipes, 2 example schemes and 15 example paints. You'll find them on the Recipes tab.", tt)
        check("that paint keeps its colour and is not turned into an example",
              page.evaluate("() => JSON.stringify(book.paints.find(p => p.name === 'Example deep blue'))") == mine)
        check("only one paint has that name, and the restored recipe uses it",
              palette_names(page).count("Example deep blue") == 1 and page.evaluate(
                  "() => { const p = book.paints.find(x => x.name === 'Example deep blue'); return book.recipes.find(r => r.name === 'Blue armour').steps[0].paints[0].paint === p.id; }"))
        main_tab(page, "recipes")
        page.click("#examples-card-recipes .clear-recipe-examples")
        page.wait_for_timeout(300)
        check("Clear after that keeps the paint and your recipe", "Example deep blue" in palette_names(page) and "Mine blue" in names(page, "recipes"))

        # d2) a paint with a status and an edited recipe survive a Clear and a Restore
        fresh(page)
        page.evaluate("() => { applyPaintStatus(book.paints.find(p => p.name === 'Example mid blue'), 'owned'); render(); }")
        edit_recipe(page, "Blue armour", "Blue armour (mine)")
        clear_on_card(page)
        mine = page.evaluate("() => JSON.stringify([book.recipes.find(r => r.name === 'Blue armour (mine)'), book.paints.find(p => p.name === 'Example mid blue')])")
        restore_in_settings(page)
        check("Restore leaves your edited recipe and your owned paint exactly as they were",
              page.evaluate("() => JSON.stringify([book.recipes.find(r => r.name === 'Blue armour (mine)'), book.paints.find(p => p.name === 'Example mid blue')])") == mine)
        check("and the owned paint is still owned, once", page.evaluate("() => book.paints.filter(p => p.name === 'Example mid blue').length") == 1
              and page.evaluate("() => paintStatus(book.paints.find(p => p.name === 'Example mid blue'))") == "owned")
        check("a fresh Blue armour was added next to your edited one", "Blue armour" in names(page, "recipes") and "Blue armour (mine)" in names(page, "recipes"))

        # e) existing user, own data
        existing(page, units_only, own_book)
        own_before = page.evaluate("() => JSON.stringify({ r: book.recipes, s: book.schemes, p: book.paints })")
        units_before = json.dumps(saved_units(page), sort_keys=True)
        full_before = snap(page)[0]
        check("an existing user starts with no examples and no card", names(page, "recipes") == ["My black"])
        restore_in_settings(page)
        tt = toast(page)
        check("Restore works for an existing user",
              tt["text"] == "Added " + ALL_WORDS + ". You'll find them on the Recipes tab.", tt)
        check("their own recipes, schemes and paints are exactly as they were",
              page.evaluate("() => JSON.stringify({ r: book.recipes.filter(x => !x.example), s: book.schemes.filter(x => !x.example), p: book.paints.filter(x => !x.example) })") == own_before)
        check("their units are untouched (there are no example units, so nothing is linked)", json.dumps(saved_units(page), sort_keys=True) == units_before)
        check("their settings remember the examples were handled, so start-up never adds them by itself",
              saved_settings(page).get("recipeExamplesChecked") is True)
        main_tab(page, "recipes")
        check("the Recipes card shows for them too, with Clear and Keep",
              card_shown(page) and page.locator("#examples-card-recipes button:not(.more-info-button)").count() == 2)
        reload(page)
        check("after a reload they still have the examples once (nothing doubled)",
              len(names(page, "recipes")) == 6 and len(names(page, "schemes")) == 3)
        main_tab(page, "recipes")
        page.click("#examples-card-recipes .clear-recipe-examples")
        page.wait_for_timeout(300)
        check("Clear takes them away again and leaves the book exactly as it was before Restore", snap(page)[0] == full_before)

        # f) after Keep, the same names exist unmarked: nothing is added
        fresh(page)
        main_tab(page, "recipes")
        page.click("#examples-card-recipes .keep-recipe-examples")
        page.wait_for_timeout(300)
        before = snap(page)
        restore_in_settings(page)
        check("after Keep them, Restore adds nothing (no duplicates of what you kept)",
              "already here" in toast(page)["text"] and snap(page) == before, toast(page))

        # g) never on the shopping list
        fresh(page)
        clear_on_card(page)
        restore_in_settings(page)
        check("restored example paints are not on the shopping list", page.evaluate("() => shoppingItems().length") == 0)
        main_tab(page, "recipes")
        page.click("#recipe-seg button[data-view='shopping']")
        page.wait_for_timeout(200)
        check("the shopping page says there is nothing to buy", "Nothing to buy" in page.inner_text("#shop-panel"), page.inner_text("#shop-panel"))
        page.evaluate("() => { applyPaintStatus(book.paints.find(p => p.name === 'Example mid blue'), 'wishlist'); render(); }")
        check("a paint you put on your wishlist does appear (it is yours then)",
              page.evaluate("() => shoppingItems().map(i => i.paint.name)") == ["Example mid blue"])
        fresh(page)
        page.evaluate("() => keepRecipeExamples()")
        page.wait_for_timeout(200)
        check("after Keep them all sixteen count like any paint", page.evaluate("() => shoppingItems().length") == 16)

        # ---------- 9. Saved data's shape ----------
        print("\n--- 9. Saved data's shape ---")
        fresh(page)
        out = page.evaluate("""() => { const c = cleanRecipeBook({ recipes: [], paints: [], schemes: [
              { id: 1, name: 'a', faction: 'x', example: 'yes', future: 7, recipes: [] },
              { id: 2, name: 'b', faction: 'x', example: true, recipes: [] },
              { id: 3, name: 'c', faction: 'x', recipes: [] },
              { id: 4, name: 'd', faction: 'x', example: 1, recipes: [] }] });
            return { s: c.schemes.map(s => [s.example, s.future]), keys: Object.keys(c).sort() }; }""")
        check("a scheme keeps its example mark only if it is a real true",
              out["s"] == [[None, 7], [True, None], [None, None], [None, None]], out)
        check("unknown fields on schemes survive cleaning (how older versions keep the mark)", out["s"][0][1] == 7)
        check("the book's keys are unchanged", out["keys"] == sorted(BOOK_KEYS), out["keys"])
        backup = page.evaluate("() => backupData()")
        bk = backup["recipes"] if isinstance(backup.get("recipes"), dict) else {}
        check("a backup carries the example marks on recipes, schemes and paints",
              all(x.get("example") is True for x in bk.get("recipes", [])) and len(bk.get("recipes", [])) == 5
              and all(x.get("example") is True for x in bk.get("schemes", [])) and len(bk.get("schemes", [])) == 2
              and all(x.get("example") is True for x in bk.get("paints", [])) and len(bk.get("paints", [])) == 16, list(bk.keys()))
        again = page.evaluate("(b) => { const c = cleanRecipeBook(b); return c.schemes.map(s => s.example); }", bk)
        check("and reading that backup back keeps the scheme marks", again == [True, True], again)
        check("a backup still says data version 1", backup["dataVersion"] == 1)
        v43_book = {"parts": ["Whole model"], "techniques": ["Layer"], "paints": [], "recipes": [], "v15": True, "shorthand": {},
                    "schemes": [{"id": 1, "name": "Old", "faction": "Red army", "auto": True, "recipes": []}]}
        existing(page, units_only, v43_book)
        check("a book saved by v43 (no marks on schemes) loads as before", page.evaluate("() => book.schemes.map(s => [s.name, 'example' in s])") == [["Old", False]])

        # ---------- 10. Safety: plain text ----------
        print("\n--- 10. Text stays plain text ---")
        inner = [ln for ln in src.splitlines() if "innerHTML" in ln]
        check("the new example code only ever uses innerHTML to empty an element", inner and all(re.search(r'innerHTML\s*=\s*""', ln) for ln in inner), inner)
        fresh(page)
        clear_on_card(page)
        evil = '<img src=x onerror="window.__pwn=1">Evil'
        page.evaluate("""(n) => { const p = findOrAddPaint('', n, '#334455');
            book.recipes.push({ id: 1, name: n, part: 'Armour', notes: '', steps: [{ technique: 'Base coat', coats: 1,
              paints: [{ paint: p.id, mix: null }], ratio: '', note: '', optional: false }] });
            book.schemes.push({ id: 1, name: n, faction: n, auto: false, recipes: [1] }); render(); }""", evil)
        restore_in_settings(page)
        main_tab(page, "recipes")
        recipe_view(page, "schemes")
        check("a recipe, scheme and paint named with markup show as plain text, nothing runs",
              page.evaluate("() => window.__pwn === undefined")
              and page.locator("#examples-card-recipes img, #scheme-list img, #recipe-list img, #paint-list img").count() == 0
              and "<img" in page.inner_text("#scheme-list"), page.inner_text("#scheme-list")[:200])
        recipe_view(page, "recipes")
        check("and the card and the messages carry no markup either", "<" not in card_text(page) and "<" not in toast(page)["text"])

        # ---------- 11. Phone widths, dark and light ----------
        print("\n--- 11. Phone widths 360 to 400 px, dark and light ---")
        for appearance in ("dark", "light"):
            for width in (360, 375, 390, 400):
                tag = f"{appearance} {width}px"
                page.set_viewport_size({"width": width, "height": 844})
                fresh(page, {"appearance": appearance})
                main_tab(page, "recipes")
                box = page.evaluate("""() => { const r = document.getElementById('examples-card-recipes').getBoundingClientRect();
                    return { l: r.left, r: r.right, w: window.innerWidth }; }""")
                check(f"{tag} Recipes: the card is inside the screen", box["l"] >= 0 and box["r"] <= box["w"] + 0.5, box)
                sizes = page.evaluate("""() => [...document.querySelectorAll('#examples-card-recipes button:not(.more-info-button)')]
                    .map(b => { const r = b.getBoundingClientRect(); return [r.width, r.height]; })""")
                check(f"{tag} Recipes: both buttons are at least 44 px tall and wide", len(sizes) == 2 and all(w >= 44 and h >= 44 for w, h in sizes), sizes)
                col = page.evaluate("""() => { const el = document.querySelector('#examples-card-recipes p');
                    return { fg: getComputedStyle(el).color, bg: getComputedStyle(document.getElementById('examples-card-recipes')).backgroundColor }; }""")
                check(f"{tag} Recipes: the card's text is readable (contrast at least 4.5)", contrast(rgb(col["fg"]), rgb(col["bg"])) >= 4.5, col)
                check(f"{tag} Recipes: nothing scrolls sideways", no_sideways(page))
                recipe_view(page, "schemes")
                inside = page.evaluate("""() => [...document.querySelectorAll('#scheme-list .recipe-item')].every(e => { const r = e.getBoundingClientRect();
                    return r.left >= 0 && r.right <= window.innerWidth + 0.5; })""")
                check(f"{tag} Schemes: both example schemes fit and nothing scrolls sideways", inside and no_sideways(page) and page.locator("#scheme-list li").count() == 2)
                if width in (360, 390):
                    shot(page, f"v44-schemes-{appearance}-{width}.png")
                recipe_view(page, "recipes")
                if width in (360, 390):
                    shot(page, f"v44-recipes-{appearance}-{width}.png")
                main_tab(page, "settings")
                page.evaluate("() => document.getElementById('restore-examples').scrollIntoView({ block: 'center' })")
                page.wait_for_timeout(150)
                info = page.evaluate("""() => { const b = document.getElementById('restore-examples').getBoundingClientRect();
                    const h = document.getElementById('restore-examples-hint'); const card = h.closest('.card');
                    return { l: b.left, r: b.right, w: b.width, h: b.height, vw: window.innerWidth, fg: getComputedStyle(h).color,
                             bg: getComputedStyle(card).backgroundColor, bfg: getComputedStyle(document.getElementById('restore-examples')).color,
                             bbg: getComputedStyle(document.getElementById('restore-examples')).backgroundColor }; }""")
                check(f"{tag} Settings: the button is inside the screen and at least 44 px tall and wide",
                      info["l"] >= 0 and info["r"] <= info["vw"] + 0.5 and info["h"] >= 44 and info["w"] >= 44, info)
                check(f"{tag} Settings: the hint is readable (contrast at least 4.5)", contrast(rgb(info["fg"]), rgb(info["bg"])) >= 4.5, info)
                behind = info["bg"] if re.search(r",\s*0\)$", info["bbg"]) else info["bbg"]
                check(f"{tag} Settings: the button text is readable (contrast at least 4.5)", contrast(rgb(info["bfg"]), rgb(behind)) >= 4.5, info)
                check(f"{tag} Settings: nothing scrolls sideways", no_sideways(page))
                if width in (360, 390):
                    shot(page, f"v44-settings-{appearance}-{width}.png")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 12. Help and Updates ----------
        print("\n--- 12. Help and Updates wording ---")
        fresh(page)
        main_tab(page, "settings")
        sub_tab(page, "help")
        help_text = page.evaluate("() => document.getElementById('help-example-recipes').textContent")
        check("Help explains the examples (what, schemes, Clear, Keep, what is kept, shopping list, existing users, Restore)",
              all(w in help_text for w in ["five", "example recipes", "example schemes", "Your Palette", "Clear examples", "Keep them",
                                           "shopping list", "already had recipes", "Restore example recipes", "twice"]), help_text)
        sub_tab(page, "updates")
        updates = page.inner_text("#view-updates")
        # v49: the Updates page shows only the newest five entries, so v44 may have moved off the page; then read it from the list
        v44_text = updates if "v44" in updates else " ".join(page.evaluate("(CHANGELOG.find(c => c.version === 'v44') || { changes: [] }).changes"))
        check("the Updates page has the v44 entry in plain words",
              "example schemes" in v44_text and "Restore example recipes" in v44_text and "Clear examples" in v44_text, v44_text[:500])

        check("no real browser pop-ups at any point", not popups, popups)
        check("no page errors", not errors, errors[:3])
        check("no CSP errors", not csp, csp[:3])
        context.close()
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
