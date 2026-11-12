"""Chunk DS2 tests for Minifolio: speed, storage use, accessibility and tidy fixes from the 2 Nov code review. New behaviour only.
1. The storage line in Settings counts every saved name, safety copies included. When a save fails because storage is full,
   the red banner offers Remove safety copies; it asks first, then removes them and saves.
2. Only the section on screen is redrawn: a tap on Units leaves the hidden Dashboard and Recipes as they were, and each is right
   (and drawn) as soon as it is shown. Jumping to a unit from another section draws it first.
3. The nickname box saves half a second after typing stops, not on every key, and a reload straight after typing keeps it.
4. Every save no longer re-reads the settings when they have not changed.
5. The photo viewer keeps focus inside itself with Tab and Shift+Tab.
6. CSV cells that start with = + - @ are made safe.
7. A full backup with photos is the same file as before and restores with its photos.
8. The service worker keeps one copy of the page whatever "?..." is on the address, and a bad font download is not kept.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import datetime, json, os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import app_ready, leave_launch, quiet, tap_tab
from common import open_unit_card   # MC1: unit cards start closed

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# Fake "storage full" (as in test_v14): with window.__quota set, setItem throws once the total would pass it.
QUOTA = """(() => {
  const realSet = Storage.prototype.setItem;
  Storage.prototype.setItem = function (k, v) {
    if (window.__quota != null) {
      let total = 0;
      for (let i = 0; i < this.length; i++) { const key = this.key(i); if (key !== k) total += key.length + this.getItem(key).length; }
      if (total + k.length + String(v).length > window.__quota) throw new DOMException("full", "QuotaExceededError");
    }
    return realSet.call(this, k, v);
  };
})();"""

SETTINGS = {"examplesChecked": True, "recipeExamplesChecked": True, "tab": "dashboard"}
TODAY = datetime.date.today().isoformat()

def units(n, **extra):
    return [{"id": i, "name": f"Squad {i}", "hobby": "40K", "faction": "Iron Wolves", "stage": 1, "count": 5,
             "added": "2026-10-01", "log": [["2026-10-01", 1]], **({"recipes": [1]} if i == 1 else {}), **extra} for i in range(1, n + 1)]

BOOK = {"v15": True, "paints": [{"id": 1, "brand": "Citadel", "name": "Macragge Blue", "colour": "#1f3a8a", "status": "owned"}],
        "recipes": [{"id": 1, "name": "Blue armour", "part": "Armour", "notes": "",
                     "steps": [{"technique": "Base coat", "coats": 1, "paints": [{"paint": 1, "mix": None}]}]}], "schemes": []}

def start(page, unit_list, settings=None, extra=None, photos=None):
    page.goto(t.URL)
    page.evaluate("""async ([u, b, s, extra]) => { localStorage.clear();
        localStorage.setItem('mini-tracker-models', JSON.stringify(u));
        localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b));
        localStorage.setItem('shades-of-grey-settings', JSON.stringify(s));
        for (const [k, v] of Object.entries(extra || {})) localStorage.setItem(k, v);
        await new Promise(done => { const r = indexedDB.deleteDatabase('shades-of-grey-photos'); r.onsuccess = r.onerror = r.onblocked = () => done(); }); }""",
                  [unit_list, BOOK, settings or SETTINGS, extra])
    page.reload()
    app_ready(page)
    if photos:   # the photo files go in first, then the units are saved again and the app opened afresh (as in test_v46)
        page.evaluate("""async (ids) => { for (const id of ids) { const b = new Blob(['photo-' + id], { type: 'image/jpeg' });
            await putPhoto({ id, full: b, thumb: b }); } }""", photos)
        page.evaluate("u => localStorage.setItem('mini-tracker-models', JSON.stringify(u))", unit_list)
        page.reload()
        app_ready(page)
    leave_launch(page)

def stored(page, key):
    return page.evaluate("k => localStorage.getItem(k)", key)

def mark(page, selector):
    """Tag the element, so a redraw (which makes a new one) can be told from no redraw."""
    return page.evaluate("s => { const el = document.querySelector(s); if (el) el.__ds2 = true; return !!el; }", selector)

def same(page, selector):
    return page.evaluate("s => { const el = document.querySelector(s); return !!(el && el.__ds2); }", selector)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", accept_downloads=True)
        ctx.add_init_script(QUOTA)
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))

        # ---------- 1. Storage line and safety copies ----------
        print("\n--- 1. Storage use and safety copies ---")
        copy = json.dumps({"date": TODAY, "stages": None, "models": units(300, note="n" * 400)})
        start(page, units(3), settings={**SETTINGS, "tab": "settings"}, extra={"mini-tracker-models-before-restore": copy})
        summary = page.text_content("#data-summary")
        found = re.search(r"uses about ([\d,]+) KB", summary)
        kb = int(found.group(1).replace(",", "")) if found else 0
        check("the storage line counts the safety copies too", kb * 1024 >= len(copy) and "safety copies included" in summary, summary)
        check("…and still no words about photos freeing this space", "photo" not in page.evaluate("FULL_MESSAGE"))
        page.evaluate("() => { let used = 0; for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i); used += k.length + localStorage.getItem(k).length; } window.__quota = used + 50; }")
        page.evaluate("() => { models[0].note = 'a longer note '.repeat(20); commit('Saved'); }")
        quiet(page)
        check("a save that fails: the red banner is up", page.is_visible("#save-banner"))
        check("…and offers Remove safety copies", page.is_visible("#banner-copies") and page.text_content("#banner-copies") == "Remove safety copies")
        check("…its words no longer say to delete photos", "photo" not in page.text_content("#save-banner-text"), page.text_content("#save-banner-text"))
        page.click("#banner-copies")
        page.wait_for_selector("#dialog-yes", state="visible")
        check("it asks first, with the safe answer focused", "Remove the safety copies" in page.text_content("#dialog-message")
              and page.evaluate("document.activeElement.id") == "dialog-no", page.text_content("#dialog-message"))
        page.click("#dialog-no")
        check("No keeps the copy", stored(page, "mini-tracker-models-before-restore") == copy)
        page.click("#banner-copies")
        page.wait_for_selector("#dialog-yes", state="visible")
        page.click("#dialog-yes")
        quiet(page)
        saved = json.loads(stored(page, "mini-tracker-models") or "[]")
        check("Yes removes the safety copy and saves the change", stored(page, "mini-tracker-models-before-restore") is None
              and saved and saved[0].get("note", "").startswith("a longer note"), stored(page, "mini-tracker-models-before-restore") is None)
        check("…the banner goes and the message says so", not page.is_visible("#save-banner") and "Safety copies removed" in page.text_content("#toast-text"),
              page.text_content("#toast-text"))
        page.evaluate("window.__quota = null")

        # ---------- 2. Only the section on screen is redrawn ----------
        print("\n--- 2. Only the section on screen is redrawn ---")
        start(page, units(40))
        tap_tab(page, "recipes"); quiet(page)   # each section drawn once
        tap_tab(page, "units"); quiet(page)
        before = page.text_content("#done-button")
        page.evaluate("() => { document.querySelector('#overall-chart > *').__ds2 = true; document.querySelector('#recipe-list > li').__ds2 = true; }")
        open_unit_card(page, '#unit-list li.unit[data-id="1"]')   # MC1: the stepper is inside the opened card
        mark(page, '#unit-list li.unit[data-id="2"]')
        page.click('#unit-list li.unit[data-id="1"] .up-button')
        quiet(page)
        check("a stage tap on Units: the unit moves up and is saved", json.loads(stored(page, "mini-tracker-models"))[0]["stage"] == 2)
        check("…the hidden Dashboard is not redrawn", same(page, "#overall-chart > *") and page.text_content("#done-button") == before)
        check("…nor the hidden Recipes list", same(page, "#recipe-list > li"))
        check("…the Units list on screen is", page.evaluate("document.querySelector('#unit-list li.unit[data-id=\"1\"]').textContent.length > 0"))
        tap_tab(page, "dashboard"); quiet(page)
        legend = page.evaluate("() => [...document.querySelectorAll('#stage-legend .num')].map(n => n.textContent)")
        check("showing the Dashboard draws it with the change (one unit of 5 models moved from stage 2 to 3)",
              not same(page, "#overall-chart > *") and legend[1:3] == ["195", "5"], legend)
        check("…the basket count and the game suggestions stayed right while it was hidden",
              page.evaluate("document.getElementById('faction-options').options.length") == 1)
        page.evaluate("() => { models[3].name = 'Renamed squad'; render(); }")
        check("a change made on the Dashboard leaves Units to be drawn later", page.evaluate("staleTabs.has('units') && !staleTabs.has('dashboard')"))
        page.evaluate("goToUnit(4)")
        quiet(page)
        check("jumping to a unit (goToUnit) draws Units first: the renamed unit is there, open",
              page.evaluate("(() => { const c = document.querySelector('#unit-list li.unit[data-id=\"4\"]'); return !!c && c.textContent.includes('Renamed squad') && !!c.querySelector('.panel'); })()"))
        page.evaluate("() => { book.recipes[0].name = 'Deep blue armour'; render(); }")
        open_unit_card(page, '#unit-list li.unit[data-id="1"]')   # MC1: the recipe buttons are inside the opened card
        page.click('#unit-list li.unit[data-id="1"] .recipe-links button')
        quiet(page)
        check("a recipe link on a unit opens Recipes drawn with the change", "Deep blue armour" in page.text_content("#view-recipes"))

        # ---------- 3. Nickname box ----------
        print("\n--- 3. Nickname box ---")
        start(page, units(2), settings={**SETTINGS, "tab": "units"})
        open_unit_card(page, '#unit-list li.unit[data-id="1"]')   # MC1: the Details button is inside the opened card
        page.click('#unit-list li.unit[data-id="1"] .details-toggle')
        quiet(page)
        nick = page.locator('#unit-list li.unit[data-id="1"] input[placeholder="e.g. The Gold Squad"]')
        if not nick.is_visible():
            page.locator('#unit-list li.unit[data-id="1"] .panel').get_by_text("Edit details").first.click()
        nick.type("Gold", delay=20)
        right_away = json.loads(stored(page, "mini-tracker-models"))[0].get("nickname")
        page.wait_for_timeout(700)
        later = json.loads(stored(page, "mini-tracker-models"))[0].get("nickname")
        check("typing a nickname does not save on every key", right_away in (None, ""), right_away)
        check("…it is saved half a second after typing stops", later == "Gold", later)
        nick.type(" Squad", delay=20)
        page.reload(); app_ready(page)
        check("a reload straight after typing keeps it (saved as the page is left)",
              json.loads(stored(page, "mini-tracker-models"))[0].get("nickname") == "Gold Squad", stored(page, "mini-tracker-models")[:200])
        leave_launch(page)

        # ---------- 4. Settings read once per change ----------
        print("\n--- 4. Saving does not re-read unchanged settings ---")
        parses = page.evaluate("""() => { saveAll(); const real = JSON.parse; let n = 0;
            JSON.parse = function (...a) { n++; return real.apply(this, a); };
            try { for (let i = 0; i < 20; i++) saveAll(); } finally { JSON.parse = real; } return n; }""")
        check("20 saves in a row read and parse the settings no times", parses == 0, parses)
        newer = page.evaluate("""() => { const s = JSON.parse(localStorage.getItem('shades-of-grey-settings')); const keep = JSON.stringify(s);
            s.dataVersion = 99; localStorage.setItem('shades-of-grey-settings', JSON.stringify(s));
            const ok = saveAll(); localStorage.setItem('shades-of-grey-settings', keep); dataTooNew = false; hideSaveProblem(); return ok; }""")
        check("…but newer data saved since is still noticed (the save is refused)", newer is False, newer)

        # ---------- 5. Photo viewer focus ----------
        print("\n--- 5. Photo viewer keeps focus ---")
        start(page, [{**units(1)[0], "photos": [{"id": "p1", "stage": 1, "date": "2026-10-01"}, {"id": "p2", "stage": 1, "date": "2026-10-02"}]}],
              photos=["p1", "p2"])
        page.evaluate("openLightbox(1, 'p1')")
        page.wait_for_timeout(200)
        inside = []
        for _ in range(12):
            page.keyboard.press("Tab")
            inside.append(page.evaluate("document.getElementById('viewer').contains(document.activeElement)"))
        check("Tab twelve times: focus never leaves the photo viewer", all(inside), inside)
        back = []
        for _ in range(5):
            page.keyboard.press("Shift+Tab")
            back.append(page.evaluate("document.getElementById('viewer').contains(document.activeElement)"))
        check("Shift+Tab goes round inside it too", all(back), back)
        page.evaluate("document.querySelector('.tabs button[data-tab=units]').focus()")
        check("focus sent behind the viewer is brought back in", page.evaluate("document.getElementById('viewer').contains(document.activeElement)"))
        page.keyboard.press("Escape")
        check("Escape still closes it", page.evaluate("viewer === null"))

        # ---------- 6. CSV cells ----------
        print("\n--- 6. CSV export cells ---")
        cells = page.evaluate("['=SUM(A1)', '+44 squad', '-Ork boyz', '@home', 'Plain name', 'a=b', '=a,b'].map(csvCell)")
        check("cells that start with = + - @ get a ' in front", cells[:4] == ["'=SUM(A1)", "'+44 squad", "'-Ork boyz", "'@home"], cells)
        check("…other cells are unchanged, and quoting still works", cells[4:] == ["Plain name", "a=b", "\"'=a,b\""], cells)
        page.evaluate("() => { models[0].name = '=HYPERLINK(1)'; save(); }")
        page.evaluate("showTab('settings')")
        with page.expect_download() as info:
            page.evaluate("document.getElementById('csv-export-button').click()")
        text = open(info.value.path(), encoding="utf-8-sig").read()
        check("the exported file has the safe cell", "\n'=HYPERLINK(1)," in text.replace("\r\n", "\n"), text[:200])

        # ---------- 7. Full backup with photos ----------
        print("\n--- 7. Full backup with photos ---")
        made = page.evaluate("""async () => { const m = await buildFullBackup();
            const old = backupData(); old.photoFiles = {};
            for (const id of ['p1', 'p2']) { const r = await getPhoto(id); old.photoFiles[id] = { full: await blobToDataUrl(r.full), thumb: await blobToDataUrl(r.thumb) }; }
            return { isBlob: m.blob instanceof Blob, text: await m.blob.text(), count: m.count, missing: m.missing, old: JSON.stringify(old) }; }""")
        check("the full backup is made as a Blob (not one long string)", made["isBlob"] and made["count"] == 2 and made["missing"] == 0, made["count"])
        check("…and it is exactly the file the old way made", made["text"] == made["old"], (len(made["text"]), len(made["old"])))
        start(page, [], settings={**SETTINGS, "tab": "settings"})
        page.set_input_files("#restore-file", files=[{"name": "backup.json", "mimeType": "application/json", "buffer": made["text"].encode()}])
        page.wait_for_selector("#dialog-yes", state="visible")
        page.click("#dialog-yes")
        page.wait_for_function("() => models.length === 1", timeout=5000)
        page.wait_for_timeout(500)
        back_photos = page.evaluate("async () => { const a = await getPhoto('p1'), b = await getPhoto('p2'); return [a && await a.full.text(), b && await b.full.text()]; }")
        check("restoring it brings back the unit and both photos", page.evaluate("models[0].name") == "=HYPERLINK(1)" and back_photos == ["photo-p1", "photo-p2"], back_photos)
        ctx.close()

        # ---------- 8. Service worker ----------
        print("\n--- 8. Service worker ---")
        ctx = browser.new_context(viewport={"width": 390, "height": 844})
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(t.URL)
        page.wait_for_function("() => navigator.serviceWorker && navigator.serviceWorker.controller", timeout=15000)
        page.wait_for_timeout(800)
        count = """async () => { let n = 0; for (const name of await caches.keys()) if (/^shades-of-grey-v/.test(name)) n += (await (await caches.open(name)).keys()).length; return n; }"""
        n0 = page.evaluate(count)
        for i in range(1, 6):
            page.goto(t.URL + f"?junk={i}")
            page.wait_for_function("() => typeof settings === 'object'")
        page.wait_for_timeout(500)
        n1 = page.evaluate(count)
        check("five made-up addresses (index.html?junk=N) add no copies of the page", n1 == n0, (n0, n1))
        font = "fonts/oxanium-latin-600-normal.woff2"
        page.evaluate("f => caches.open('shades-of-grey-fonts').then(c => c.delete(f))", font)
        ctx.route("**/" + font, lambda route: route.fulfill(status=200, content_type="font/woff2", body="NOT A FONT"))
        first = page.evaluate("f => fetch(f).then(r => r.text())", font)
        page.wait_for_timeout(300)
        ctx.unroute("**/" + font)
        again = page.evaluate("f => fetch(f).then(r => r.arrayBuffer()).then(b => String.fromCharCode(...new Uint8Array(b).slice(0, 4)))", font)
        check("a bad font download (a 200 that isn't a font) is not kept: the next try gets the real font", first == "NOT A FONT" and again == "wOF2", (first, again))
        page.wait_for_timeout(300)
        kept = page.evaluate("f => caches.open('shades-of-grey-fonts').then(c => c.match(f)).then(r => r ? r.arrayBuffer() : null).then(b => b ? String.fromCharCode(...new Uint8Array(b).slice(0, 4)) : null)", font)
        check("…and the real one is kept", kept == "wOF2", kept)
        ctx.close()
        browser.close()

    check("no page errors", not errors, errors[:3])
    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)

if __name__ == "__main__":
    main()
