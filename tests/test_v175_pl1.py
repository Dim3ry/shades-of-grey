"""PL1 tests for Minifolio: Paste a list of paints (Your Palette). New behaviour only.
Reading a list (bullets, numbers, brand lines, quantities, commas), the three groups, Set all and the row menus, the Owned or Wishlist rule on
paints already in the palette, Not found ticks, no recipes made, Undo, re-pasting, 'Ardcoat, tap sizes and no sideways scroll.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys, time
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import leave_launch

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

PAINTS = [{"id": 1, "brand": "Citadel", "name": "Abaddon Black", "colour": "#231f20", "status": "owned"},
          {"id": 2, "brand": "Citadel", "name": "Mephiston Red", "colour": "#9a1115", "status": "wishlist"},
          {"id": 3, "brand": "Citadel", "name": "Nuln Oil", "colour": "#222222", "status": "empty"},
          {"id": 4, "brand": "Citadel", "name": "Khorne Red", "colour": "#6a0001", "status": "low"}]
LIST = "Citadel:\n- Abaddon Black\n2x Mephiston Red\nabaddon, bleck templar\nGreenskin Special\n'Ardcoat\nWraithbone x3\n1) Nuln Oil (2)\n*Khorne Red\n\n---"

def status(page, name):
    return page.evaluate("n => { const p = book.paints.find(x => x.name === n); return p ? [paintStatus(p), p.qty || 0] : null; }", name)

def open_panel(page, text):
    page.evaluate("openRecipeId = null; settings.recipeView = 'palette'; showTab('recipes'); renderRecipes()")
    page.wait_for_selector("#paste-list-button")
    page.evaluate("pasteList = null; renderPasteList()")   # closed, so the next tap opens a fresh panel
    page.click("#paste-list-button")
    page.fill("#paste-list-text", text)
    page.click("#paste-list-read")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. The button and the panel ---")
        t.load(page, paints=PAINTS, settings={"tab": "recipes", "examplesChecked": True}); leave_launch(page)
        page.evaluate("openRecipeId = null; settings.recipeView = 'palette'; showTab('recipes'); renderRecipes()")
        check("the button sits directly under Scan a paint pot", page.evaluate("document.getElementById('scan-panel').nextElementSibling.id") == "paste-list-button")
        check("the button says Paste a list of paints", page.text_content("#paste-list-button").strip() == "Paste a list of paints")
        page.click("#paste-list-button")
        check("it opens a panel in the same card with a box, Read list and Close",
              page.is_visible("#paste-list-text") and page.is_visible("#paste-list-read") and page.locator("#paste-list-panel button", has_text="Close").count() == 1
              and page.evaluate("document.getElementById('paste-list-panel').closest('.card') === document.getElementById('scan-button').closest('.card')"))
        page.fill("#paste-list-text", LIST)
        page.locator("#paste-list-panel button", has_text="Close").click()
        page.click("#paste-list-button")
        check("what you typed is kept after Close and open again", page.input_value("#paste-list-text") == LIST)

        print("\n--- 2. Reading the list ---")
        t0 = time.time()
        page.click("#paste-list-read")
        rows = page.evaluate("pasteList.rows.map(r => [r.kind, r.typed, r.qty, r.status, r.tick])")
        found = [r for r in rows if r[0] == "found"]; chk = [r for r in rows if r[0] == "check"]; none = [r for r in rows if r[0] == "none"]
        check("one row per paint: 'abaddon' and 'Abaddon Black' are one row", sum(1 for r in rows if "baddon" in r[1].lower()) == 1, rows)
        check("a bullet, a number and a star come off the front and the paint is found", {"Nuln Oil", "Khorne Red", "Abaddon Black"} <= {r[1] for r in found}, rows)
        check("the 'Citadel:' line is not a paint of its own", not any("citadel" == r[1].lower().rstrip(":") for r in rows), rows)
        check("a comma splits a line into two paints", any(r[1] == "bleck templar" for r in rows) and any(r[1].lower() == "abaddon" or r[1] == "Abaddon Black" for r in rows))
        check("2x, x3 and (2) set the quantity", {r[1]: r[2] for r in found}.get("Mephiston Red") == 2 and {r[1]: r[2] for r in found}.get("Wraithbone") == 3 and {r[1]: r[2] for r in found}.get("Nuln Oil") == 2, found)
        check("'Ardcoat keeps its apostrophe", any(r[1] == "'Ardcoat" for r in found) and page.evaluate("pasteList.rows.find(r => r.typed === \"'Ardcoat\").paint.name") == "'Ardcoat")
        check("a misspelt name goes under Check with its best guess picked", len(chk) == 1 and page.evaluate("pasteList.rows.find(r => r.kind === 'check').options[0].name") == "Black Templar", chk)
        check("an unknown name goes under Not found, untick", len(none) == 1 and none[0][1] == "Greenskin Special" and none[0][4] is False, none)
        check("found rows and check rows start ticked", all(r[4] for r in found + chk))
        check("every row starts as Owned", all(r[3] == "owned" for r in rows))
        heads = page.locator("#paste-list-panel .pl1-group").all_text_contents()
        check("the three groups are headed with their counts", heads == [f"Found ({len(found)})", "Check (1)", "Not found (1)"], heads)
        check("a Check card offers its guess and Keep as typed", page.locator('.pl1-row[data-kind="check"] .import-option').all_text_contents()[-1].strip() == "Keep as typed")
        check("Not found says Add as your own paint", page.locator('.pl1-row[data-kind="none"] .pl1-tick').text_content().startswith("Add as your own paint"))
        label = page.text_content("#paste-list-add").strip()
        check("Add N paints follows the ticked rows", label == f"Add {len(found) + len(chk)} paints", label)

        print("\n--- 3. Status rules on paints already there ---")
        notes = page.locator(".pl1-row .pl1-note").all_text_contents()
        check("a row names what the paint is now, in words", "Owned now" in notes and "Wishlist now" in notes and "Empty now" in notes and "Running low now" in notes, notes)
        page.locator("#paste-list-panel input[name='pl1-all'][value='wishlist']").check()
        check("Set all to Wishlist changes every row", page.evaluate("pasteList.rows.every(r => r.status === 'wishlist')"))
        notes = page.locator(".pl1-row .pl1-note").all_text_contents()
        check("a Wishlist row on an Owned or Running low paint says it is already, and is unticked and off",
              "Owned already" in notes and "Running low already" in notes
              and page.locator("#paste-list-panel input[type=checkbox]:disabled").count() == 2
              and page.locator("#paste-list-panel input[type=checkbox]:disabled:checked").count() == 0, notes)
        page.locator('.pl1-row select.pl1-status').first.select_option("owned")
        check("a row menu changes only that row", page.evaluate("pasteList.rows.filter(r => r.status === 'owned').length") == 1)
        page.locator("#paste-list-panel input[name='pl1-all'][value='owned']").check()

        print("\n--- 4. Adding, Undo, and again ---")
        before = page.evaluate("JSON.stringify([book.recipes, book.schemes, book.parts])")
        page.locator('.pl1-row[data-kind="check"] .pl1-tick input').uncheck()
        page.click("#paste-list-add")
        page.wait_for_timeout(300)
        toast = page.text_content("#toast-text")
        check("the toast says how many were added, as Owned", toast.startswith("Added ") and toast.endswith(" paints as Owned"), toast)
        check("Undo is on the toast", page.is_visible("#toast-undo"))
        check("a Wishlist or Empty paint became Owned", status(page, "Mephiston Red")[0] == "owned" and status(page, "Nuln Oil")[0] == "owned")
        check("the quantity is stored on an Owned paint", status(page, "Mephiston Red")[1] == 2 and status(page, "Wraithbone") == ["owned", 3], status(page, "Wraithbone"))
        check("a quantity replaces, and no quantity leaves it", status(page, "Nuln Oil")[1] == 2 and status(page, "Abaddon Black") == ["owned", 0])
        check("the ticked-off Check row was not added", status(page, "Black Templar") is None)
        check("the Not found paint, left unticked, was not added", status(page, "Greenskin Special") is None)
        check("'Ardcoat was added with its apostrophe", status(page, "'Ardcoat") == ["owned", 0], status(page, "'Ardcoat"))
        check("no recipes, schemes or parts were made", page.evaluate("JSON.stringify([book.recipes, book.schemes, book.parts])") == before)
        check("the panel closed after adding", page.locator("#paste-list-panel.hidden").count() == 1)
        snap = page.evaluate("JSON.stringify(book.paints)")
        page.click("#toast-undo")
        page.wait_for_timeout(200)
        check("Undo puts every status and quantity back", status(page, "Mephiston Red") == ["wishlist", 0] and status(page, "Nuln Oil")[0] == "empty" and status(page, "Wraithbone") is None
              and status(page, "'Ardcoat") is None and len(page.evaluate("book.paints")) == 4)

        open_panel(page, LIST)
        page.click("#paste-list-add"); page.wait_for_timeout(200)
        first = page.evaluate("JSON.stringify(book.paints)")
        open_panel(page, LIST)
        page.click("#paste-list-add"); page.wait_for_timeout(200)
        check("pasting the same list again changes nothing", page.evaluate("JSON.stringify(book.paints)") == first)

        print("\n--- 5. Wishlist, own paints, mixed ---")
        t.load(page, paints=PAINTS, settings={"tab": "recipes", "examplesChecked": True}); leave_launch(page)
        open_panel(page, "Wraithbone\n2x Mephiston Red\nNuln Oil\nKhorne Red\nGreenskin Special")
        page.locator("#paste-list-panel input[name='pl1-all'][value='wishlist']").check()
        page.locator('.pl1-row[data-kind="none"] .pl1-tick input').check()
        check("ticking a Not found row counts it", page.text_content("#paste-list-add").strip() == "Add 4 paints", page.text_content("#paste-list-add"))
        page.click("#paste-list-add"); page.wait_for_timeout(200)
        check("a Wishlist toast names Wishlist", page.text_content("#toast-text") == "Added 4 paints as Wishlist", page.text_content("#toast-text"))
        check("a new paint, and an Empty paint, are Wishlist; Wishlist stays", status(page, "Wraithbone")[0] == "wishlist" and status(page, "Nuln Oil")[0] == "wishlist" and status(page, "Mephiston Red") == ["wishlist", 0])
        check("an Owned and a Running low paint are left alone", status(page, "Abaddon Black")[0] == "owned" and status(page, "Khorne Red")[0] == "low")
        own = page.evaluate("book.paints.find(p => p.name === 'Greenskin Special')")
        check("an own paint has the name as typed and no brand", own and own["brand"] == "", own)
        check("Wishlist rows ignore the quantity", "qty" not in page.evaluate("book.paints.find(p => p.name === 'Mephiston Red')"))
        open_panel(page, "Wraithbone\nNuln Oil")
        page.locator('.pl1-row select.pl1-status').first.select_option("wishlist")
        page.locator('.pl1-row select.pl1-status').nth(1).select_option("owned")
        page.click("#paste-list-add"); page.wait_for_timeout(200)
        check("a mixed list gives a toast with no status in it", page.text_content("#toast-text") == "Added 2 paints", page.text_content("#toast-text"))
        open_panel(page, "zzzz qqqq")
        check("nothing readable leaves Add off", page.locator("#paste-list-add").is_disabled())

        print("\n--- 6. Speed and size of the list ---")
        names = page.evaluate("searchedPaints.slice(0, 50).map(p => p.name)")
        text50 = "\n".join(names) + "\nBleck Templar\nKhorn Red\nZzzz One\nYyyy Two\nCitadel:\n- Abaddon Black\n3x Wraithbone"
        page.evaluate("pasteList = null")
        open_panel(page, text50)
        ms = page.evaluate("t => { const a = performance.now(); readPasteList(t, 'owned'); return performance.now() - a; }", text50)
        check("a 50 line list reads in under 2 seconds", ms < 2000, ms)
        over = page.evaluate("readPasteList('Abaddon Black\\n'.repeat(450), 'owned').over")
        check("more than 400 lines is noticed", over is True)

        print("\n--- 7. Sizes at 390 and 360 ---")
        for width in (390, 360):
            page.set_viewport_size({"width": width, "height": 844})
            open_panel(page, LIST)
            page.wait_for_timeout(200)
            small = page.evaluate("""() => [...document.querySelectorAll('#paste-list-panel .pl1-tick, #paste-list-panel .pl1-radio, #paste-list-panel .import-option, #paste-list-panel select, #paste-list-panel button')]
                .filter(e => e.offsetParent).map(e => { const r = e.getBoundingClientRect(); return [e.className || e.tagName, Math.round(r.width), Math.round(r.height)]; })
                .filter(x => x[1] < 44 || x[2] < 44)""")
            check(f"{width}: every tick, radio, menu and button is 44 px or more", not small, small)
            check(f"{width}: no sideways scroll", page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        page.emulate_media(color_scheme="light")
        page.evaluate("document.documentElement.dataset.theme = 'light'")
        check("light: no sideways scroll", page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

main()
