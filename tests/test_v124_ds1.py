"""Chunk DS1 tests for Minifolio: data safety fixes from the 2 Nov code review. New behaviour only.
1. Damaged units at start-up are not written over: saving pauses, the banner says so with Save it as a file and Start again.
   Start again asks first (focus on the safe answer), keeps an "-unreadable" copy, and that copy is listed under Recover.
2. Recover keeps units and recipes together; an older separate recipes copy is still offered and restored.
3. An Undo after an unrelated change keeps that change.
4. A recipes-only restore leaves no unit linked to the wrong recipe (matched by name, otherwise dropped).
5. A restore with no room for its safety copy changes nothing.
6. Danger questions start with focus on the safe answer.
7. A window coming back from the back-forward cache picks up newer saved data; a note is saved when the app goes to the background.
8. No success message when the save failed; the old stage upgrade respects newer data.
The service worker checks are in test_v124_ds1b.py.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import app_ready, leave_launch, quiet

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

UNITS = "mini-tracker-models"
RECIPES = "shades-of-grey-recipes"
SETTINGS = {"examplesChecked": True, "recipeExamplesChecked": True, "tab": "settings"}

def start(page, units=None, recipes=None, settings=None, raw_units=None):
    """Fresh storage, then a reload. raw_units is saved exactly as given (for damaged data)."""
    page.goto(t.URL)
    page.evaluate("""([u, r, s, raw]) => { localStorage.clear();
        if (raw !== null) localStorage.setItem('mini-tracker-models', raw);
        else if (u) localStorage.setItem('mini-tracker-models', JSON.stringify(u));
        if (r) localStorage.setItem('shades-of-grey-recipes', JSON.stringify(r));
        localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }""",
                  [units, recipes, settings or SETTINGS, raw_units])
    page.reload()
    app_ready(page)
    leave_launch(page)

def book(names, paints=None):
    return {"v15": True, "paints": paints or [], "recipes": [{"id": i + 1, "name": n, "steps": []} for i, n in enumerate(names)], "schemes": []}

def restore(page, data):
    page.set_input_files("#restore-file", files=[{"name": "backup.json", "mimeType": "application/json",
                                                   "buffer": json.dumps(data).encode()}])
    page.wait_for_selector("#dialog-yes", state="visible")
    page.click("#dialog-yes")
    page.wait_for_timeout(400)

def stored(page, key):
    return page.evaluate("k => localStorage.getItem(k)", key)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", accept_downloads=True)
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        popups = []
        page.on("dialog", lambda d: (popups.append(d.message), d.dismiss()))

        # 1. Damaged units at start-up.
        damaged = json.dumps([{"id": i, "name": f"Unit {i}", "stage": 1, "note": "x" * 400} for i in range(1, 400)])[:-1]
        start(page, raw_units=damaged, recipes=book(["Blue armour"]))
        check("damaged units: the saved text is left exactly as it was", stored(page, UNITS) == damaged)
        check("…no examples are shown in its place", page.evaluate("models.length") == 0)
        banner = page.locator("#save-banner")
        text = page.text_content("#save-banner-text")
        check("…the banner says the units couldn't be read", banner.is_visible() and "units couldn't be read" in text, text)
        check("…with Save it as a file and Start again", page.text_content("#banner-backup") == "Save it as a file"
              and page.text_content("#banner-retry") == "Start again" and page.is_visible("#banner-backup"))
        page.evaluate("() => { models.push({ id: 1, name: 'New', stage: 0, count: 1, hobby: '', faction: '' }); render(); }")
        check("…a change made meanwhile doesn't write over it", stored(page, UNITS) == damaged)
        with page.expect_download() as dl:
            page.click("#banner-backup")
        saved_file = dl.value
        check("Save it as a file downloads the saved text as it is",
              saved_file.suggested_filename.startswith("minifolio-unreadable-units") and open(saved_file.path()).read() == damaged,
              saved_file.suggested_filename)
        page.click("#banner-retry"); quiet(page)
        check("Start again asks first, with focus on the safe answer",
              page.is_visible("#dialog-yes") and page.evaluate("document.activeElement.id") == "dialog-no")
        page.click("#dialog-yes"); quiet(page)
        check("…then saving works again and the banner goes", not banner.is_visible() and stored(page, UNITS) == "[]")
        check("…and a copy is kept under -unreadable", stored(page, UNITS + "-unreadable") == damaged)
        page.evaluate("renderSettings()")
        row = page.locator("#recover-list li", has_text="Unreadable units")
        check("…listed under Recover earlier data with Save as file", row.count() == 1 and row.locator("button").text_content() == "Save as file")

        # 2. Recover keeps units and recipes together.
        start(page, units=[{"id": 1, "name": "A unit", "stage": 0}], recipes=book(["RA"]))
        restore(page, {"app": "Minifolio", "version": 6, "dataVersion": 2, "models": [{"id": 1, "name": "B unit", "stage": 0}],
                       "recipes": book(["RB1", "RB2"])})
        restore(page, [{"id": 1, "name": "C unit", "stage": 0}])
        check("a units-only restore leaves no separate recipes copy behind", stored(page, RECIPES + "-before-restore") is None)
        page.evaluate("recoverSafetyCopy('-before-restore')")
        page.wait_for_selector("#dialog-yes", state="visible")
        question = page.text_content("#dialog-message")
        check("recovering it doesn't promise recipes it hasn't got", "recipes" not in question, question)
        page.click("#dialog-yes"); quiet(page)
        got = page.evaluate("({ units: models.map(m => m.name), recipes: book.recipes.map(r => r.name) })")
        check("…units come back and the current recipes stay", got == {"units": ["B unit"], "recipes": ["RB1", "RB2"]}, got)
        # An older pair of copies (units and recipes under separate names) is still offered and restored together.
        page.evaluate("""() => { localStorage.setItem('mini-tracker-models-before-replace', JSON.stringify({ date: todayISO(),
            stages: STAGES, doneFrom: settings.doneFrom, models: [{ id: 1, name: 'Old unit', stage: 0 }] }));
            localStorage.setItem('shades-of-grey-recipes-before-replace', JSON.stringify({ paints: [], recipes: [{ id: 1, name: 'Old recipe', steps: [] }], schemes: [] }));
            recoverSafetyCopy('-before-replace'); }""")
        page.wait_for_selector("#dialog-yes", state="visible")
        check("an older separate recipes copy is still offered", "(and its recipes)" in page.text_content("#dialog-message"))
        page.click("#dialog-yes"); quiet(page)
        got = page.evaluate("({ units: models.map(m => m.name), recipes: book.recipes.map(r => r.name) })")
        check("…and restored with its units", got == {"units": ["Old unit"], "recipes": ["Old recipe"]}, got)
        copy = page.evaluate("JSON.parse(localStorage.getItem('mini-tracker-models-before-recover'))")
        check("the copy kept by that recover holds its recipes in the same record",
              [r["name"] for r in copy.get("book", {}).get("recipes", [])] == ["RB1", "RB2"] and stored(page, RECIPES + "-before-recover") is None)

        # 3. Undo after an unrelated change.
        paints = [{"id": 1, "brand": "Citadel", "name": "Mephiston Red", "colour": "#960c09"},
                  {"id": 2, "brand": "Citadel", "name": "Abaddon Black", "colour": "#231f20", "status": "wishlist"}]
        start(page, units=[], recipes=book([], paints))
        r = page.evaluate("""() => {
            addToShoppingList({ brand: 'Citadel', name: 'Retributor Armour' }, 'test');
            applyPaintStatus(book.paints.find(x => x.name === 'Abaddon Black'), 'owned'); render();
            document.getElementById('toast-undo').click();
            const saved = JSON.parse(localStorage.getItem('shades-of-grey-recipes')).paints;
            return { other: saved.find(x => x.name === 'Abaddon Black').status, added: saved.some(x => x.name === 'Retributor Armour') }; }""")
        check("Undo takes back only its own change (the added paint goes)", not r["added"], r)
        check("…and keeps the Status change made meanwhile", r["other"] == "owned", r)
        r = page.evaluate("""() => {
            const red = book.paints.find(x => x.name === 'Mephiston Red'); removePaint(red);
            book.paints.find(x => x.name === 'Abaddon Black').status = 'wishlist'; render();
            document.getElementById('toast-undo').click();
            return { back: book.paints.findIndex(x => x.name === 'Mephiston Red'), other: paintStatus(book.paints.find(x => x.name === 'Abaddon Black')) }; }""")
        check("Undo of Remove puts the paint back in its place and keeps the other change", r == {"back": 0, "other": "wishlist"}, r)

        # 4. Recipes-only restore and unit links.
        start(page, units=[{"id": 1, "name": "Intercessors", "stage": 0, "recipes": [1]}, {"id": 2, "name": "Skeletons", "stage": 0, "recipes": [2]}],
              recipes=book(["Blue armour", "Bone"]))
        restore(page, {"app": "Minifolio", "version": 6, "dataVersion": 2, "models": [], "recipes": book(["Ork skin", "Gold", "Bone"])})
        links = page.evaluate("models.map(m => (m.recipes || []).map(id => book.recipes.find(r => r.id === id).name))")
        check("a recipes-only restore matches links by recipe name", links[1] == ["Bone"], links)
        check("…and drops a link with no match instead of pointing at another recipe", links[0] == [], links)
        page.click("#toast-undo"); quiet(page)
        links = page.evaluate("models.map(m => (m.recipes || []).map(id => book.recipes.find(r => r.id === id).name))")
        check("…Undo puts the old book and links back", links == [["Blue armour"], ["Bone"]], links)

        # 5. A restore with no room for its safety copy changes nothing.
        units = [{"id": i, "name": f"Unit {i}", "stage": 0, "note": "n" * 2000} for i in range(1, 200)]
        start(page, units=units, recipes=book(["Mine"]))
        before = stored(page, UNITS)
        page.evaluate("""() => { let size = 1 << 20, i = 0;
            while (size >= 1024) { try { localStorage.setItem('filler-' + (i++), 'f'.repeat(size)); } catch (e) { size = size >> 1; } } }""")
        restore(page, {"app": "Minifolio", "version": 6, "dataVersion": 2, "models": [{"id": 1, "name": "Backup unit", "stage": 0}],
                       "recipes": book(["Theirs"])})
        note = page.text_content("#dialog-message") if page.is_visible("#dialog-message") else page.text_content("#toast")
        check("no room for the safety copy: the restore says nothing has changed", "nothing has changed" in (note or ""), note)
        check("…units and recipes are unchanged", stored(page, UNITS) == before and page.evaluate("book.recipes.map(r => r.name)") == ["Mine"])
        check("…and no copy is listed as if it were this one", stored(page, UNITS + "-before-restore") is None)
        page.evaluate("() => Object.keys(localStorage).filter(k => k.startsWith('filler-')).forEach(k => localStorage.removeItem(k))")
        page.keyboard.press("Escape"); quiet(page)

        # 6. Danger questions focus the safe answer.
        page.evaluate("askYesNo('Plain question?', () => {})")
        check("an ordinary question starts on Yes", page.evaluate("document.activeElement.id") == "dialog-yes")
        page.keyboard.press("Escape"); quiet(page)
        page.click("#delete-all") if page.is_visible("#delete-all") else page.evaluate("document.getElementById('delete-all').click()")
        quiet(page)
        check("Delete all starts on the safe answer", page.evaluate("document.activeElement.id") == "dialog-no")
        page.keyboard.press("Enter"); quiet(page)
        check("…so Enter keeps the units", page.evaluate("models.length") == len(units) and not page.is_visible("#dialog-yes"))

        # 7. Back-forward cache and background.
        start(page, units=[{"id": 1, "name": "Mine", "stage": 0}], recipes=book([]))
        page.evaluate("""() => { localStorage.setItem('mini-tracker-models', JSON.stringify([{ id: 1, name: 'Mine', stage: 0 }, { id: 2, name: 'From the other window', stage: 0 }]));
            window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true })); }""")
        check("back from the back-forward cache: newer saved units are loaded", page.evaluate("models.length") == 2)
        page.evaluate("() => { models[0].nickname = 'Nick'; render(); }")
        check("…so the next save keeps them", len(json.loads(stored(page, UNITS))) == 2)
        page.evaluate("""() => { models[0].note = 'last words'; saveFieldSoon();
            Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true });
            document.dispatchEvent(new Event('visibilitychange'));
            Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true }); }""")
        check("a note waiting to save is saved when the app goes to the background", json.loads(stored(page, UNITS))[0].get("note") == "last words")

        # 8. No success message when the save failed.
        page.evaluate("""() => { const real = Storage.prototype.setItem;
            window.__realSet = real;
            Storage.prototype.setItem = function (k, v) { if (k === 'mini-tracker-models') throw new DOMException('full', 'QuotaExceededError'); return real.call(this, k, v); };
            changeStage(1, 1); }""")
        toast = page.text_content("#toast")
        check("a stage move that wasn't saved says Not saved", "Not saved" in toast and "→" not in toast, toast)
        page.evaluate("() => { Storage.prototype.setItem = window.__realSet; saveAll(); }")
        # The old (pre-v3) stage upgrade doesn't write units over data saved by a newer version.
        old_units = json.dumps([{"id": 1, "name": "Old", "stage": 5}])
        start(page, raw_units=old_units, recipes=book([]), settings={**SETTINGS, "dataVersion": 99,
              "stages": ["Unassembled", "Part assembled", "Assembled", "Primed", "Part painted", "Painted with issues", "Battle ready"]})
        check("the old stage upgrade leaves newer data alone", stored(page, UNITS) == old_units)

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not popups, popups)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
