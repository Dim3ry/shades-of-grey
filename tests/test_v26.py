"""v26 tests for Minifolio: unfinished work survives a reload (roadmap section 5, "not confirmed fixed").

The three things that used to be lost when the page reloaded are now kept, on this device only:
  the Add unit boxes (while the name box has something in it), a recipe being written or edited
  (while it has unsaved changes) and the text in Paste recipes. Each comes back through a small
  "We kept your unfinished..." card with Keep going and Discard. Nothing opens by itself.

Checks:
1. Version numbers (plain numbers, "v26 or later"), sw.js and both ?v= tags match, the Updates entry, kept things
   (CNAME, the ocr folder, LICENSE-paint-list.txt, the passive ZAP workflow, the CSP exactly as v21.4),
   the old storage names, and the data version (still 1).
2. The reported problem, with real typing and a real reload: the Add unit boxes, a recipe being written and
   Paste recipes' text all come back through Keep going. Nothing opens by itself.
3. What is NOT kept: an untouched form, boxes with no name, a new recipe nobody has typed in, blank paste text.
4. When a draft goes: Add, Save, Cancel (only after "yes"), leaving Paste recipes (after "yes"), Discard (after "yes").
   Saying "no" keeps it. A discarded draft never comes back, even after the safety timer and more reloads.
5. Never replaced by accident: starting a new draft while an old one waits asks first; the waiting draft is never
   touched; two kinds at once; a second window never removes the first one's draft.
6. Editing a recipe that already exists, and one that has been deleted since.
7. Bad or hostile saved drafts are repaired or ignored; a failing save changes nothing for the person.
8. Nothing else changes: units, recipes and settings are the same, backups don't carry drafts, DATA_VERSION stays 1,
   no network code, nothing leaves the app.
9. Dark and light at 390 and 360 px: cards on screen, 44 px targets, readable, no sideways scroll.
10. Help, Privacy and Updates wording (reached via Settings, then the Help / Updates switch).
11. No real browser pop-ups, no page errors and no CSP errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright
from launch_helpers import quiet
from launch_helpers import app_ready

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
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

V21_4_CSP = ("default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; "
             "img-src 'self' blob: data: https://dim3ry.goatcounter.com/count; media-src 'self' blob:; font-src 'self'; connect-src 'self'; worker-src 'self'; "
             "manifest-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-src 'none'")
DRAFTS = "shades-of-grey-drafts"
UNITS = [{"id": 1, "name": "Termagants", "hobby": "40K", "faction": "Tyranids", "stage": 2, "count": 10},
         {"id": 2, "name": "Hormagaunts", "hobby": "40K", "faction": "Tyranids", "stage": 4, "count": 10}]
NAME_BOX = 'input[placeholder="e.g. Ultramarine blue armour"]'
NOTES_BOX = 'textarea[placeholder^="Optional: tips"]'
PASTE_TEXT = "Chitin:\nLuxion purple\nGenestealer purple (drybrush)\n\nTeeth:\nWraithbone, Agrax"

def clear_photos(page):
    page.evaluate("""async () => { await new Promise(done => { const r = indexedDB.deleteDatabase('shades-of-grey-photos');
        r.onsuccess = r.onerror = r.onblocked = () => done(); }); }""")

def settle(page):
    app_ready(page)
    leave_launch(page)   # U4b (v89): a fresh load shows the start page; tap through to the saved section, as before

def fresh(page, settings=None):
    """A brand-new start: nothing saved at all (apart from the settings given)."""
    page.goto(URL)
    page.evaluate("(s) => { localStorage.clear(); if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }", settings)
    clear_photos(page)
    page.reload()
    settle(page)

def existing(page, settings=None, units=None):
    """Someone who has used the app before: units saved (and maybe settings)."""
    page.goto(URL)
    page.evaluate("""([u, s]) => { localStorage.clear();
        localStorage.setItem('mini-tracker-models', JSON.stringify(u));
        if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }""", [units or UNITS, settings])
    clear_photos(page)
    page.reload()
    settle(page)

def reload(page):
    page.reload()
    settle(page)

def blur(page):
    page.evaluate("() => document.activeElement && document.activeElement.blur()")
    quiet(page)

def main_tab(page, name):
    blur(page)
    page.click(f'nav button[data-tab="{name}"]')
    quiet(page)

def sub_tab(page, name):
    page.click(f'#more-seg button[data-page="{name}"]')
    page.wait_for_timeout(150)

def shot(page, name):
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=os.path.join(SHOTS, name))

def no_sideways(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")

def store_text(page):
    return page.evaluate("(k) => localStorage.getItem(k)", DRAFTS)

def store(page):
    t = store_text(page)
    return json.loads(t) if t else None

def wait_kept(page, kind):
    """Wait until the draft of this kind has been written down (the app writes a moment after you stop)."""
    page.wait_for_function("([k, kind]) => { try { const s = JSON.parse(localStorage.getItem(k) || 'null'); return !!(s && s[kind]); } catch (e) { return false; } }",
                           arg=[DRAFTS, kind])

def wait_gone(page, kind=None):
    page.wait_for_function("""([k, kind]) => { try { const s = JSON.parse(localStorage.getItem(k) || 'null');
        return !s || (kind ? !s[kind] : false); } catch (e) { return false; } }""", arg=[DRAFTS, kind])

def card(page, kind):
    return page.locator(f"#draft-card-{kind}")

def shown(page, kind):
    return card(page, kind).is_visible()

def type_unit(page, name="Half typed unit", count="7", game="40K", faction="Tyranids", stage="3"):
    main_tab(page, "units")
    page.click("#toggle-add")
    page.fill("#name-input", name)
    page.fill("#count-input", count)
    page.fill("#hobby-input", game)
    page.fill("#faction-input", faction)
    page.select_option("#stage-input", stage)
    blur(page)

def start_recipe(page, name="Half written recipe", notes="some notes", paint="Macragge Blue"):
    main_tab(page, "recipes")
    page.click("#new-recipe")
    page.wait_for_timeout(250)
    page.fill(NAME_BOX, name)
    page.fill(NOTES_BOX, notes)
    page.fill("#recipe-page .paint-name", paint)
    page.locator("#recipe-page button.add-step").dispatch_event("click")   # v50: the tab bar can sit over this button on a short page
    page.wait_for_timeout(200)
    page.fill("#recipe-page li.step-edit:nth-of-type(2) .paint-name", "Nuln Oil")
    blur(page)

def start_paste(page, text=PASTE_TEXT):
    main_tab(page, "recipes")
    page.click("#paste-recipes")
    page.wait_for_timeout(250)
    page.fill("#import-text", text)
    blur(page)

def ask_open(page):
    return page.locator("#dialog-backdrop").is_visible()

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

def seed(page, drafts):
    """Put drafts in the store as an earlier visit would have left them, then open the app again."""
    page.evaluate("([k, d]) => localStorage.setItem(k, typeof d === 'string' ? d : JSON.stringify(d))", [DRAFTS, drafts])
    reload(page)

GOOD_RECIPE = {"id": None, "name": "Seeded recipe", "part": "Armour", "notes": "n", "linkUnit": None,
               "steps": [{"technique": "Base coat", "coats": 2, "ratio": "", "note": "", "optional": False,
                          "paints": [{"brand": "Citadel", "name": "Macragge Blue", "colour": "#0d407f", "mix": 100}]}],
               "own": {"mode": "all", "notOwned": []}}

def main():
    errors, csp, popups, notices, outside = [], [], [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        context.on("request", lambda r: outside.append(r.url) if not (r.url.startswith(BASE) or r.url.startswith(("data:", "blob:", "about:"))) else None)
        page = context.new_page()
        attach_notices(page, notices.append)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)
        page.on("dialog", lambda d: (popups.append(d.message), d.dismiss()))

        # ---------- 1. Versions and kept things ----------
        print("\n--- 1. Versions and kept things ---")
        fresh(page)
        html, app, sw = read("index.html"), read("app.js"), read("sw.js")
        version = page.evaluate("APP_VERSION")
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        check("the comment in app.js names the same number", f'e.g. "app.js?v={version[1:]}"' in app)
        check("the newest Updates entry is the current version", page.evaluate("CHANGELOG[0].version") == version)
        check("a brand-new start saves no draft", store_text(page) is None)

        # ---------- 2. The reported problem: reload with work half done ----------
        print("\n--- 2. The reported problem, with real typing and a real reload ---")
        fresh(page)
        units_before = page.evaluate("() => localStorage.getItem('mini-tracker-models')")
        type_unit(page)
        wait_kept(page, "unit")
        kept = store(page)["unit"]
        check("the Add unit boxes are written down (name, number, game, faction, starting stage)",
              kept == {"name": "Half typed unit", "count": "7", "game": "40K", "faction": "Tyranids", "stage": page.evaluate("STAGES[3]")}, kept)
        reload(page)
        check("after the reload the Units tab opens on its own, as before", page.evaluate("settings.tab") == "units")
        check("a card says we kept your unfinished unit",
              shown(page, "unit") and "We kept your unfinished unit." in page.inner_text("#draft-card-unit")
              and "Half typed unit" in page.inner_text("#draft-card-unit"), page.inner_text("#draft-card-unit"))
        check("it says it is saved on this device only", "saved on this device only" in page.inner_text("#draft-card-unit"))
        check("the card has exactly Keep going and Discard, in that order",
              page.evaluate("() => [...document.querySelectorAll('#draft-card-unit button')].map(b => b.textContent)") == ["Keep going", "Discard"])
        check("nothing opened by itself: the Add form is closed and its boxes are empty",
              not page.is_visible("#add-form") and page.input_value("#name-input") == "" and page.input_value("#count-input") == "1")
        check("the kept unit is not in your units (nothing was added)", page.evaluate("() => localStorage.getItem('mini-tracker-models')") == units_before)
        page.click("#draft-card-unit .draft-keep")
        page.wait_for_timeout(250)
        got = page.evaluate("""() => [nameInput.value, countInput.value, hobbyInput.value, factionInput.value, stageInput.value]""")
        check("Keep going puts every box back", got == ["Half typed unit", "7", "40K", "Tyranids", "3"], got)
        check("the Add form is open, and the button says Close", page.is_visible("#add-form") and page.inner_text("#toggle-add") == "Close")
        check("the card has gone", not shown(page, "unit"))
        check("the name box has the cursor, so you can carry on typing", page.evaluate("() => document.activeElement && document.activeElement.id") == "name-input")
        page.keyboard.type(" and more")
        blur(page)
        page.wait_for_function("() => (JSON.parse(localStorage.getItem('shades-of-grey-drafts') || '{}').unit || {}).name === 'Half typed unit and more'")
        check("typing on carries on being kept (a real key press)", True)

        # a fast reload: page hidden straight after typing, before the short wait is over
        fresh(page)
        type_unit(page, name="Fast reload")
        reload(page)
        check("a reload straight after typing still keeps it (written as the page closes)", shown(page, "unit"), store_text(page))

        # Recipe
        fresh(page)
        start_recipe(page)
        wait_kept(page, "recipe")
        reload(page)
        check("a recipe being written: the editor is closed after the reload and a card is shown on the Recipes tab",
              page.evaluate("settings.tab") == "recipes" and shown(page, "recipe") and not page.locator(NAME_BOX).is_visible(), page.inner_text("#view-recipes")[:200])
        check("the card says we kept your unfinished recipe and names it",
              "We kept your unfinished recipe." in page.inner_text("#draft-card-recipe") and "Half written recipe" in page.inner_text("#draft-card-recipe"))
        page.click("#draft-card-recipe .draft-keep")
        page.wait_for_timeout(300)
        got = page.evaluate("""() => { const d = recipeDraft; return d && { name: d.name, notes: d.notes, steps: d.steps.length,
            first: d.steps[0].paints[0].name, second: d.steps[1].paints[0].name }; }""")
        check("Keep going opens the editor with the name, notes and both steps back", got == {"name": "Half written recipe", "notes": "some notes", "steps": 2,
              "first": "Macragge Blue", "second": "Nuln Oil"}, got)
        check("what is on screen matches (name and notes boxes)",
              page.input_value(NAME_BOX) == "Half written recipe" and page.input_value(NOTES_BOX) == "some notes")
        check("the card is gone while the editor is open", not shown(page, "recipe"))
        page.click("#recipe-page button:has-text('Save recipe')")
        page.wait_for_timeout(300)
        check("Save recipe saves it as a real recipe", page.evaluate("() => book.recipes.some(r => r.name === 'Half written recipe' && r.steps.length === 2)"))
        wait_gone(page, "recipe")
        check("saving removes the kept draft", store_text(page) is None, store_text(page))

        # Paste recipes
        fresh(page)
        start_paste(page)
        wait_kept(page, "paste")
        reload(page)
        check("pasted notes: the paste page is closed after the reload and a card is shown",
              shown(page, "paste") and not page.locator("#import-text").is_visible()
              and "We kept your pasted recipe notes." in page.inner_text("#draft-card-paste"), page.inner_text("#view-recipes")[:200])
        check("the card says how long the text is", f"{len(PASTE_TEXT)} characters" in page.inner_text("#draft-card-paste"), page.inner_text("#draft-card-paste"))
        page.click("#draft-card-paste .draft-keep")
        page.wait_for_timeout(300)
        check("Keep going opens Paste recipes with the text back, ready to Read notes",
              page.input_value("#import-text") == PASTE_TEXT and page.inner_text("#import-page .primary-button").startswith("Read notes"))
        page.click("#import-page .primary-button")
        page.wait_for_timeout(300)
        check("and it reads as before", page.evaluate("() => importDraft.parsed && importDraft.parsed.schemes.length") >= 1)

        # ---------- 3. What is not kept ----------
        print("\n--- 3. What is not kept ---")
        fresh(page)
        main_tab(page, "units")
        page.click("#toggle-add")
        page.fill("#hobby-input", "40K")
        page.fill("#faction-input", "Tyranids")
        page.fill("#count-input", "12")
        blur(page)
        page.wait_for_timeout(700)
        check("Add unit boxes with no name are not kept (the game and faction stay filled between units, by design)", store_text(page) is None, store_text(page))
        page.fill("#name-input", "   ")
        blur(page)
        page.wait_for_timeout(700)
        check("a name of only spaces is not kept", store_text(page) is None)
        main_tab(page, "recipes")
        page.click("#new-recipe")
        page.wait_for_timeout(700)
        check("a new recipe nobody has typed in is not kept", store_text(page) is None)
        page.fill(NAME_BOX, "x")
        blur(page)
        wait_kept(page, "recipe")
        page.fill(NAME_BOX, "")
        blur(page)
        wait_gone(page, "recipe")
        check("typing in a recipe and then taking it all out again removes the draft", store_text(page) is None)
        page.click("#recipe-page button:has-text('Cancel')")
        page.wait_for_timeout(200)
        start_paste(page, "   \n  ")
        page.wait_for_timeout(700)
        check("blank text in Paste recipes is not kept", store_text(page) is None)

        # ---------- 4. When a draft goes ----------
        print("\n--- 4. When a draft goes ---")
        # Add
        fresh(page)
        type_unit(page, name="Gaunts", game="40K", faction="Tyranids")
        wait_kept(page, "unit")
        page.click("#add-form button[type=submit]")
        wait_gone(page, "unit")
        check("Add removes the kept unit", store_text(page) is None)
        check("the unit really was added, and game and faction stay for the next one",
              page.evaluate("() => models.some(m => m.name === 'Gaunts')") and page.input_value("#hobby-input") == "40K"
              and page.input_value("#faction-input") == "Tyranids" and page.input_value("#name-input") == "")
        reload(page)
        check("after a reload there is no card", not shown(page, "unit"))
        # Add after Keep going
        type_unit(page, name="Warriors")
        wait_kept(page, "unit")
        reload(page)
        page.click("#draft-card-unit .draft-keep")
        page.wait_for_timeout(200)
        page.click("#add-form button[type=submit]")
        wait_gone(page, "unit")
        check("a unit brought back with Keep going can be added, and the draft goes",
              store_text(page) is None and page.evaluate("() => models.some(m => m.name === 'Warriors' && m.count === 7)"))
        # Cancel / No / Escape on a recipe
        start_recipe(page)
        wait_kept(page, "recipe")
        page.click("#recipe-page button:has-text('Cancel')")
        page.wait_for_timeout(200)
        check("Cancel with unsaved changes asks the usual question", ask_open(page) and "Discard the changes" in page.inner_text("#dialog-message"))
        page.click("#dialog-no")
        page.wait_for_timeout(300)
        check("answering No keeps the editor open and the draft saved", page.locator(NAME_BOX).is_visible() and store(page)["recipe"]["name"] == "Half written recipe")
        page.click("#recipe-page button:has-text('Cancel')")
        page.wait_for_timeout(200)
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        check("Escape also means No: nothing is lost", page.locator(NAME_BOX).is_visible() and store(page)["recipe"] is not None)
        page.click("#recipe-page button:has-text('Cancel')")
        page.wait_for_timeout(200)
        page.click("#dialog-yes")
        wait_gone(page, "recipe")
        check("answering Yes closes the editor and the draft goes", not page.locator(NAME_BOX).is_visible() and store_text(page) is None)
        # Paste: leave with yes / no
        start_paste(page)
        wait_kept(page, "paste")
        page.click("#import-page .link-button")
        page.wait_for_timeout(200)
        check("leaving Paste recipes with text in it asks first", ask_open(page) and "Leave without saving" in page.inner_text("#dialog-message"))
        page.click("#dialog-no")
        page.wait_for_timeout(300)
        check("No keeps the page open and the text kept", page.input_value("#import-text") == PASTE_TEXT and store(page)["paste"]["text"] == PASTE_TEXT)
        page.click("#import-page .link-button")
        page.wait_for_timeout(200)
        page.click("#dialog-yes")
        wait_gone(page, "paste")
        check("Yes leaves the page and the draft goes", not page.locator("#import-text").is_visible() and store_text(page) is None)
        # Paste: save (all paints are known Citadel ones, so nothing needs checking first)
        start_paste(page, "Armour:\nMacragge Blue\nNuln Oil\nCalgar Blue")
        wait_kept(page, "paste")
        page.click("#import-page .primary-button")
        page.wait_for_timeout(300)
        page.click("#import-save")
        page.wait_for_timeout(400)
        wait_gone(page, "paste")
        check("saving what was pasted saves the recipe and removes the kept notes",
              page.evaluate("() => book.recipes.some(r => r.name === 'Armour' || r.part === 'Armour')") and store_text(page) is None, store_text(page))
        reload(page)
        check("and after a reload there is no card", not shown(page, "paste") and not shown(page, "recipe"))

        # Discard
        fresh(page)
        type_unit(page, name="To be discarded")
        wait_kept(page, "unit")
        reload(page)
        before = store_text(page)
        page.click("#draft-card-unit .draft-discard")
        page.wait_for_timeout(250)
        check("Discard asks first, in the app's own box, and says it can't be undone",
              ask_open(page) and "Throw away your unfinished unit? This can't be undone." in page.inner_text("#dialog-message"), page.inner_text("#dialog-message"))
        check("the safe answer is the bold one (Keep it), the other says Discard",
              page.inner_text("#dialog-no") == "Keep it" and page.inner_text("#dialog-yes") == "Discard"
              and "primary-button" in page.get_attribute("#dialog-no", "class"))
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
        check("Escape means Keep it: the card and the saved draft are untouched", shown(page, "unit") and store_text(page) == before)
        page.click("#draft-card-unit .draft-discard")
        page.wait_for_timeout(250)
        page.click("#dialog-no")
        page.wait_for_timeout(250)
        check("Keep it: still there", shown(page, "unit") and store_text(page) == before)
        page.click("#draft-card-unit .draft-discard")
        page.wait_for_timeout(250)
        page.click("#dialog-yes")
        page.wait_for_timeout(300)
        check("Discard, then yes: the card is gone and nothing is saved", not shown(page, "unit") and store_text(page) is None)
        check("no Undo message is offered (a discarded draft never comes back)", page.locator("#toast-action:visible").count() == 0)
        check("the Add form is empty and closed", not page.is_visible("#add-form") and page.input_value("#name-input") == "")
        page.wait_for_timeout(4800)
        check("it stays gone after the safety timer has run", store_text(page) is None)
        reload(page)
        reload(page)
        check("and after two more reloads", not shown(page, "unit") and store_text(page) is None)
        page.click("#toggle-add")
        page.wait_for_timeout(250)
        check("opening the Add form now gives an empty form, with no question", not ask_open(page) and page.input_value("#name-input") == "")

        # ---------- 5. Never replaced by accident ----------
        print("\n--- 5. Never replaced by accident ---")
        fresh(page)
        start_recipe(page, name="Old recipe")
        wait_kept(page, "recipe")
        reload(page)
        old = store_text(page)
        main_tab(page, "recipes")
        page.click("#new-recipe")
        page.wait_for_timeout(250)
        check("starting a new recipe while one is kept asks first",
              ask_open(page) and "unfinished recipe kept from earlier" in page.inner_text("#dialog-message") and "Keep going with it first?" in page.inner_text("#dialog-message"),
              page.inner_text("#dialog-message"))
        check("the buttons are Keep going and Not now", page.inner_text("#dialog-yes") == "Keep going" and page.inner_text("#dialog-no") == "Not now")
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
        check("Escape: nothing was started and the old draft is exactly as it was",
              page.evaluate("recipeDraft") is None and store_text(page) == old and shown(page, "recipe"))
        page.click("#new-recipe")
        page.wait_for_timeout(250)
        page.click("#dialog-no")
        page.wait_for_timeout(250)
        check("Not now: the same", page.evaluate("recipeDraft") is None and store_text(page) == old)
        page.wait_for_timeout(4800)
        check("a waiting draft is never touched, even after the safety timer has run", store_text(page) == old)
        page.click("#new-recipe")
        page.wait_for_timeout(250)
        page.click("#dialog-yes")
        page.wait_for_timeout(300)
        check("Keep going: the old recipe opens (not a blank one)", page.input_value(NAME_BOX) == "Old recipe")
        # Paste waits the same way
        page.click("#recipe-page button:has-text('Cancel')")
        page.wait_for_timeout(200)
        page.click("#dialog-yes")
        wait_gone(page, "recipe")
        start_paste(page)
        wait_kept(page, "paste")
        reload(page)
        old = store_text(page)
        page.click("#paste-recipes")
        page.wait_for_timeout(250)
        check("opening Paste recipes while pasted notes are kept asks first", ask_open(page) and "pasted recipe notes kept from earlier" in page.inner_text("#dialog-message"), page.inner_text("#dialog-message"))
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
        check("Escape: the pasted notes are exactly as they were", page.evaluate("importDraft") is None and store_text(page) == old)
        page.click("#paste-recipes")
        page.wait_for_timeout(250)
        page.click("#dialog-yes")
        page.wait_for_timeout(300)
        check("Keep going: the pasted text is back", page.input_value("#import-text") == PASTE_TEXT)
        page.click("#import-page .link-button")
        page.wait_for_timeout(200)
        page.click("#dialog-yes")
        wait_gone(page, "paste")
        # and the Add form
        fresh(page)
        type_unit(page, name="Old unit")
        wait_kept(page, "unit")
        reload(page)
        old = store_text(page)
        page.click("#toggle-add")
        page.wait_for_timeout(250)
        check("opening the Add form while a unit is kept asks first, and the form stays shut",
              ask_open(page) and "unfinished unit kept from earlier" in page.inner_text("#dialog-message") and not page.is_visible("#add-form"))
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
        check("Escape: the form is still shut and the unit is still kept", not page.is_visible("#add-form") and store_text(page) == old and shown(page, "unit"))
        page.click("#toggle-add")
        page.wait_for_timeout(250)
        page.click("#dialog-yes")
        page.wait_for_timeout(250)
        check("Keep going brings it back into the form", page.input_value("#name-input") == "Old unit" and page.is_visible("#add-form"))

        # Two kinds at once
        fresh(page)
        type_unit(page, name="Unit one")
        wait_kept(page, "unit")
        start_recipe(page, name="Recipe one")
        wait_kept(page, "recipe")
        check("a unit and a recipe can both be kept at once", set(store(page)) == {"unit", "recipe"}, store_text(page))
        reload(page)
        check("the recipe card shows on the Recipes tab", shown(page, "recipe") and not shown(page, "paste"))
        main_tab(page, "units")
        check("the unit card shows on the Units tab", shown(page, "unit"))
        page.click("#draft-card-unit .draft-discard")
        page.wait_for_timeout(250)
        page.click("#dialog-yes")
        page.wait_for_timeout(300)
        check("discarding one leaves the other kept", list(store(page)) == ["recipe"], store_text(page))
        main_tab(page, "recipes")
        check("and its card is still there", shown(page, "recipe"))
        page.click("#draft-card-recipe .draft-keep")
        page.wait_for_timeout(300)
        page.click("#recipe-page button:has-text('Cancel')")
        page.wait_for_timeout(200)
        page.click("#dialog-yes")
        wait_gone(page, "recipe")

        # Two windows
        fresh(page)
        other = context.new_page()
        other.on("pageerror", lambda e: errors.append("other window: " + str(e)))
        other.goto(URL)
        settle(other)
        start_recipe(page, name="First window")
        wait_kept(page, "recipe")
        other.click('nav button[data-tab="units"]')
        other.wait_for_timeout(5000)
        check("a second window that never wrote a draft does not remove the first window's", store(page) and store(page).get("recipe", {}).get("name") == "First window", store_text(page))
        other.reload()
        settle(other)
        other.click('nav button[data-tab="recipes"]')
        other.wait_for_timeout(300)
        check("a window opened later offers it", other.locator("#draft-card-recipe").is_visible())
        other.close()

        # ---------- 6. Editing a recipe that already exists ----------
        print("\n--- 6. Editing a recipe that already exists ---")
        fresh(page)
        count = page.evaluate("book.recipes.length")
        first = page.evaluate("() => ({ id: book.recipes[0].id, name: book.recipes[0].name })")
        main_tab(page, "recipes")
        page.evaluate("(id) => { startRecipeDraft(draftFrom(recipeById(id))); }", first["id"])
        page.wait_for_timeout(250)
        page.fill(NAME_BOX, first["name"] + " (my version)")
        blur(page)
        wait_kept(page, "recipe")
        check("changing an existing recipe is kept, with the number of the recipe it was changing", store(page)["recipe"]["id"] == first["id"], store_text(page))
        reload(page)
        check("the card says changes to the recipe", "You hadn't saved changes to" in page.inner_text("#draft-card-recipe") and "(my version)" in page.inner_text("#draft-card-recipe"), page.inner_text("#draft-card-recipe"))
        check("the saved recipe itself is untouched meanwhile", page.evaluate("(id) => recipeById(id).name", first["id"]) == first["name"])
        page.click("#draft-card-recipe .draft-keep")
        page.wait_for_timeout(300)
        check("Keep going opens it as an edit of that recipe", page.evaluate("recipeDraft.id") == first["id"] and page.inner_text("#recipe-page h2") == "Edit recipe")
        page.click("#recipe-page button:has-text('Save recipe')")
        page.wait_for_timeout(300)
        check("Save changes that recipe and does not add another",
              page.evaluate("book.recipes.length") == count and page.evaluate("(id) => recipeById(id).name", first["id"]) == first["name"] + " (my version)")
        # Cancel on a restored edit
        main_tab(page, "recipes")
        page.evaluate("(id) => { openRecipeId = null; startRecipeDraft(draftFrom(recipeById(id))); }", first["id"])
        page.wait_for_timeout(250)
        page.fill(NAME_BOX, "Changed again")
        blur(page)
        wait_kept(page, "recipe")
        reload(page)
        page.click("#draft-card-recipe .draft-keep")
        page.wait_for_timeout(300)
        page.click("#recipe-page button:has-text('Cancel')")
        page.wait_for_timeout(200)
        check("Cancel on a brought-back edit still asks (it has unsaved changes)", ask_open(page))
        page.click("#dialog-yes")
        wait_gone(page, "recipe")
        check("and then it is gone, and the recipe is as it was", store_text(page) is None and page.evaluate("(id) => recipeById(id).name", first["id"]) == first["name"] + " (my version)")
        # The recipe was deleted since
        page.evaluate("(id) => { openRecipeId = null; startRecipeDraft(draftFrom(recipeById(id))); }", first["id"])
        page.wait_for_timeout(250)
        page.fill(NAME_BOX, "Edit of a recipe that will be gone")
        blur(page)
        wait_kept(page, "recipe")
        reload(page)
        page.evaluate("(id) => { book.recipes = book.recipes.filter(r => r.id !== id); }", first["id"])
        page.click("#draft-card-recipe .draft-keep")
        page.wait_for_timeout(300)
        check("if the recipe has been deleted since, the draft comes back as a new recipe, with no errors",
              page.evaluate("recipeDraft.id") is None and page.inner_text("#recipe-page h2") == "New recipe" and page.input_value(NAME_BOX) == "Edit of a recipe that will be gone")
        page.click("#recipe-page button:has-text('Cancel')")
        page.wait_for_timeout(200)
        page.click("#dialog-yes")
        wait_gone(page, "recipe")

        # ---------- 7. Bad saved drafts, and a save that fails ----------
        print("\n--- 7. Bad saved drafts, and a save that fails ---")
        fresh(page)
        def no_cards(page):
            main_tab(page, "units")
            a = shown(page, "unit")
            main_tab(page, "recipes")
            return not a and not shown(page, "recipe") and not shown(page, "paste")
        seed(page, "this is not json")
        check("an unreadable draft store: the app starts, no card, no errors", no_cards(page) and not errors, errors[:2])
        seed(page, {"unit": {"name": 5}, "recipe": {"steps": "x"}, "paste": {"text": "   "}, "other": 1})
        check("drafts with the wrong shape are not offered", no_cards(page))
        check("and they are tidied away", store_text(page) is None or "unit" not in store_text(page), store_text(page))
        seed(page, {"unit": {"name": "<img src=x onerror=alert(1)>Hostile", "count": "<b>9</b>", "game": "g", "faction": "f", "stage": "Nonexistent"}})
        main_tab(page, "units")
        check("a draft with page code in it is shown as plain text, never run",
              shown(page, "unit") and page.locator("#draft-card-unit img").count() == 0 and "<img src=x" in page.inner_text("#draft-card-unit") and not popups, popups)
        page.click("#draft-card-unit .draft-keep")
        page.wait_for_timeout(250)
        check("a stage that no longer exists falls back to the stage already picked", page.evaluate("stageInput.value") in [str(i) for i in range(10)])
        page.click("#toggle-add")
        page.wait_for_timeout(150)
        recipe_bad = json.loads(json.dumps(GOOD_RECIPE))
        recipe_bad.update({"id": 999, "linkUnit": 999, "name": "Bad bits"})
        recipe_bad["steps"] = [{"technique": "x", "coats": "lots", "paints": [{"brand": "b", "name": "n", "colour": "red; background:url(http://evil.example/x)", "mix": "banana"}]}] * 70
        recipe_bad["own"] = {"mode": "weird", "notOwned": [1, "ok"]}
        fresh(page)
        seed(page, {"recipe": recipe_bad})
        main_tab(page, "recipes")
        page.click("#draft-card-recipe .draft-keep")
        page.wait_for_timeout(300)
        got = page.evaluate("""() => ({ id: recipeDraft.id, link: recipeDraft.linkUnit, steps: recipeDraft.steps.length,
            colour: recipeDraft.steps[0].paints[0].colour, coats: recipeDraft.steps[0].coats, mix: recipeDraft.steps[0].paints[0].mix,
            own: recipeDraft.own.mode })""")
        check("a recipe draft is repaired: missing recipe and unit forgotten, steps capped at 60, colour and numbers made safe, odd choices reset",
              got == {"id": None, "link": None, "steps": 60, "colour": "#808080", "coats": 1, "mix": None, "own": "all"}, got)
        check("no page errors from any of that", not errors, errors[:2])
        page.click("#recipe-page button:has-text('Cancel')")
        page.wait_for_timeout(200)
        page.click("#dialog-yes")
        wait_gone(page, "recipe")
        good = json.loads(json.dumps(GOOD_RECIPE))
        good["own"] = {"mode": "pick", "notOwned": ["macragge blue"]}
        seed(page, {"recipe": good})
        main_tab(page, "recipes")
        page.click("#draft-card-recipe .draft-keep")
        page.wait_for_timeout(300)
        check("a good recipe draft keeps its Do-you-own-these choice", page.evaluate("recipeDraft.own.mode") == "pick" and page.evaluate("[...recipeDraft.own.notOwned]") == ["macragge blue"])
        page.click("#recipe-page button:has-text('Cancel')")
        page.wait_for_timeout(200)
        page.click("#dialog-yes")
        wait_gone(page, "recipe")
        # a lone drafts entry must not stop a brand-new start getting its examples
        page.evaluate("() => localStorage.clear()")
        page.evaluate("([k]) => localStorage.setItem(k, JSON.stringify({ paste: { text: 'x' } }))", [DRAFTS])
        reload(page)
        check("a drafts entry on its own does not count as having used the app (examples still appear)", page.evaluate("book.recipes.length") == 5, page.evaluate("book.recipes.length"))
        # Storage failing for drafts only
        fresh(page)
        page.evaluate("""() => { const orig = Storage.prototype.setItem; window.__orig = orig;
            Storage.prototype.setItem = function (k, v) { if (k === 'shades-of-grey-drafts') { const e = new Error('full'); e.name = 'QuotaExceededError'; throw e; } return orig.call(this, k, v); }; }""")
        notices.clear()
        type_unit(page, name="Cannot be kept")
        page.wait_for_timeout(900)
        check("if a draft can't be written, the app carries on quietly: no message, no red banner, no errors",
              not notices and page.locator("#save-banner").is_hidden() and not errors, (notices, errors[:2]))
        check("nothing was written", store_text(page) is None)
        page.evaluate("() => { Storage.prototype.setItem = window.__orig; }")
        page.fill("#name-input", "Can be kept now")
        blur(page)
        wait_kept(page, "unit")
        check("as soon as writing works again, the draft is kept (it tries again)", store(page)["unit"]["name"] == "Can be kept now")

        # ---------- 8. Nothing else changes ----------
        print("\n--- 8. Nothing else changes ---")
        existing(page)
        snap = page.evaluate("() => [localStorage.getItem('mini-tracker-models'), localStorage.getItem('shades-of-grey-recipes')]")
        type_unit(page, name="Draft only")
        start_recipe(page, name="Draft recipe")
        wait_kept(page, "recipe")
        after = page.evaluate("() => [localStorage.getItem('mini-tracker-models'), localStorage.getItem('shades-of-grey-recipes')]")
        check("keeping drafts writes nothing into your units or recipes", snap == after)
        check("and nothing about drafts goes into the settings", "draft" not in json.dumps(page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-settings'))")).lower())
        check("a backup does not carry drafts", "draft" not in page.evaluate("() => JSON.stringify(backupData())").lower())
        keys = page.evaluate("() => Object.keys(localStorage).sort()")
        check("the only new storage entry is the drafts one",
              set(keys) <= {"mini-tracker-models", "shades-of-grey-recipes", "shades-of-grey-settings", DRAFTS}, keys)
        start = app.index("v26: UNFINISHED WORK")
        # v27: its section sits just before the Updates list, so stop where v27's begins.
        stop = app.find("v27: COUNTING VISITS", start)
        section = app[start:(stop if stop > 0 else app.index("const CHANGELOG", start))]
        check("it uses no inline handlers, eval, innerHTML with typed text or browser pop-ups",
              not re.search(r"onclick=|eval\(|new Function|\balert\(|\bconfirm\(|\bprompt\(", section))
        check("it only reads and writes the one drafts entry", len(re.findall(r"localStorage\.(?:get|set|remove)Item\((?!DRAFTS_KEY)", section)) == 0)
        check("nothing left the app at any point", outside == [], outside)
        fresh(page)
        start_recipe(page)
        wait_kept(page, "recipe")
        reload(page)
        page.click("#draft-card-recipe .draft-keep")
        page.wait_for_timeout(400)
        page.evaluate("() => history.back()")
        page.wait_for_timeout(400)
        check("the phone's Back button still asks about unsaved changes", ask_open(page), page.evaluate("() => history.length"))
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        check("Escape: the editor is still open and the draft kept", page.locator(NAME_BOX).is_visible() and store(page)["recipe"] is not None)

        # ---------- 9. Dark and light, 390 and 360 ----------
        print("\n--- 9. Dark and light at 390 and 360 px ---")
        three = {"unit": {"name": "A unit with a really quite long name indeed, Intercessors of the Ninth Legion", "count": "5", "game": "40K", "faction": "Ultramarines", "stage": ""},
                 "recipe": dict(GOOD_RECIPE, name="Ultramarine armour with a long name to make it wrap across the card nicely"),
                 "paste": {"text": PASTE_TEXT}}
        for appearance in ("dark", "light"):
            for width in (390, 360):
                tag = f"{appearance} {width}px"
                page.set_viewport_size({"width": width, "height": 844})
                existing(page, {"appearance": appearance, "tab": "units"})
                seed(page, three)
                for kind, tab in (("unit", "units"), ("recipe", "recipes"), ("paste", "recipes")):
                    main_tab(page, tab)
                    page.wait_for_timeout(150)
                    box = page.evaluate("""(k) => { const r = document.getElementById('draft-card-' + k).getBoundingClientRect();
                        return { l: r.left, r: r.right, t: r.top, b: r.bottom, w: window.innerWidth, h: window.innerHeight }; }""", kind)
                    check(f"{tag}: the {kind} card is inside the screen and on screen without scrolling",
                          page.locator(f"#draft-card-{kind}").is_visible() and box["l"] >= 0 and box["r"] <= box["w"] + 0.5 and box["b"] <= box["h"], box)
                    sizes = page.evaluate("""(k) => [...document.querySelectorAll('#draft-card-' + k + ' button')]
                        .map(b => { const r = b.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height), b.scrollWidth <= b.clientWidth + 1]; })""", kind)
                    check(f"{tag}: the {kind} card's two buttons are at least 44 px and their words fit",
                          len(sizes) == 2 and all(w >= 44 and h >= 44 and fits for w, h, fits in sizes), sizes)
                    check(f"{tag}: nothing scrolls sideways on the {kind} page", no_sideways(page))
                    col = page.evaluate("""(k) => { const c = document.getElementById('draft-card-' + k);
                        const go = c.querySelector('.draft-keep'), bin = c.querySelector('.draft-discard');
                        const bg = (el) => { let e = el; while (e) { const v = getComputedStyle(e).backgroundColor;
                            if (v && v !== 'rgba(0, 0, 0, 0)' && v !== 'transparent') return v; e = e.parentElement; } return 'rgb(0,0,0)'; };
                        return { text: getComputedStyle(c.querySelector('p')).color, card: bg(c),
                                 goFg: getComputedStyle(go).color, goBg: bg(go), binFg: getComputedStyle(bin).color, binBg: bg(bin) }; }""", kind)
                    check(f"{tag}: the {kind} card's words and both buttons are readable (contrast at least 4.5)",
                          contrast(rgb(col["text"]), rgb(col["card"])) >= 4.5 and contrast(rgb(col["goFg"]), rgb(col["goBg"])) >= 4.5
                          and contrast(rgb(col["binFg"]), rgb(col["binBg"])) >= 4.5, col)
                    if width == 390 and kind != "paste":
                        shot(page, f"v26-draft-card-{kind}-{appearance}-390.png")
                page.click("#draft-card-recipe .draft-discard")
                page.wait_for_timeout(250)
                box = page.evaluate("""() => { const r = document.getElementById('dialog').getBoundingClientRect(); return { l: r.left, r: r.right, w: window.innerWidth }; }""")
                check(f"{tag}: the Discard question box is inside the screen", box["l"] >= 0 and box["r"] <= box["w"] + 0.5, box)
                page.keyboard.press("Escape")
                page.wait_for_timeout(200)
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 10. Help, Privacy and Updates ----------
        print("\n--- 10. Help, Privacy and Updates wording ---")
        fresh(page)
        main_tab(page, "settings")
        sub_tab(page, "help")
        help_text = page.evaluate("() => document.getElementById('help-unfinished-work').textContent")
        check("Help explains it (what is kept, the card, Keep going, Discard, no Undo, never replaced by accident, this device, not in backups)",
              all(w in help_text for w in ["Unfinished work is kept", "Keep going", "Discard", "no Undo", "never replaced by accident", "on this device", "not in your backups"]), help_text)
        privacy = page.evaluate("() => document.getElementById('privacy-drafts').textContent")
        sub_tab(page, "updates")
        updates = page.inner_text("#view-updates")
        check("\"Tell us what you think\" is still there", "Tell us what you think" in updates)

        check("no real browser pop-ups at any point", not popups, popups)
        check("no page errors", not errors, errors[:3])
        context.close()
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
