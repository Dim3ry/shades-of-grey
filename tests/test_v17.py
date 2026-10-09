"""v17 tests for Shades of Grey (paint status, search or add, have/missing badges, "What can I paint now?",
shopping list). Serve the repo folder with `python3 -m http.server 8765`, then run:
python3 tests/test_v17.py <folder for screenshots>. Also run test_v14.py to test_v16.py to check nothing broke."""
import json, os, sys
from playwright.sync_api import sync_playwright
import os as _os
PORT = _os.environ.get("SOG_PORT", "8765")

URL = f"http://localhost:{PORT}/index.html"
SHOTS = sys.argv[1] if len(sys.argv) > 1 else "."
KEEP_NOTE = open(os.path.join(os.path.dirname(__file__), "keep_note.txt")).read()
results = []
def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# A v16 book: one paint added by scan (owned: true), one unused paint with no status.
V16_OWNED_BOOK = {
    "v15": True, "parts": ["Whole model", "Armour"], "techniques": ["Prime", "Layer", "Wash"],
    "paints": [{"id": 1, "brand": "Citadel", "name": "Nuln Oil", "colour": "#222222", "owned": True},
               {"id": 2, "brand": "Citadel", "name": "Old Paint", "colour": "#333333"}],
    "recipes": [{"id": 1, "name": "Black armour", "part": "Armour", "notes": "",
                 "steps": [{"technique": "Wash", "coats": 1, "ratio": "", "note": "", "optional": False,
                            "paints": [{"paint": 1, "mix": 100}]}]}],
    "schemes": [],
}

# A small book for statuses, the recipe filter and the shopping list. Paint 2 is unused, so it's tidied away
# by pruneUnusedPaints unless it has a status (it has none here, so it goes).
V17_BOOK = {
    "v15": True, "parts": ["Whole model", "Armour"], "techniques": ["Prime", "Layer", "Wash"],
    "paints": [
        {"id": 1, "brand": "Citadel", "name": "Nuln Oil", "colour": "#222222", "status": "low", "spare": True, "owned": True},
        {"id": 2, "brand": "Citadel", "name": "Mephiston Red", "colour": "#aa2222", "status": "empty", "owned": False},
        {"id": 3, "brand": "Vallejo", "name": "Mystic Blue", "colour": "#2244aa", "status": "wishlist", "owned": False},
        {"id": 4, "brand": "Citadel", "name": "Abaddon Black", "colour": "#111111"},
        {"id": 5, "brand": "Citadel", "name": "Macragge Blue", "colour": "#2255cc", "status": "owned", "owned": True},
        {"id": 6, "brand": "Citadel", "name": "Leadbelcher", "colour": "#888888", "status": "notowned", "owned": False},
    ],
    "recipes": [
        {"id": 1, "name": "Blue armour", "part": "Armour", "notes": "", "steps": [
            {"technique": "Layer", "coats": 1, "ratio": "", "note": "", "optional": False, "paints": [{"paint": 5, "mix": 100}]}]},
        {"id": 2, "name": "Black trim", "part": "Armour", "notes": "", "steps": [
            {"technique": "Layer", "coats": 1, "ratio": "", "note": "", "optional": False, "paints": [{"paint": 1, "mix": 50}, {"paint": 4, "mix": 50}]}]},
        {"id": 3, "name": "Chainmail", "part": "Armour", "notes": "", "steps": [
            {"technique": "Layer", "coats": 1, "ratio": "", "note": "", "optional": False, "paints": [{"paint": 6, "mix": 100}]}]},
    ],
    "schemes": [],
}
EXPECTED_SHOPPING = """Shopping list

Citadel
- Abaddon Black: missing, used in 1 recipe
- Leadbelcher: missing, used in 1 recipe
- Mephiston Red: empty
- Nuln Oil: running low (spare in stock)

Vallejo
- Mystic Blue: wishlist"""

# How George answers the questions the Keep note raises (same as v16).
ANSWERS = {"Bleck Templar": "Black Templar", "CM": "Contrast Medium", "Ice": "Basing material", "SS": "Screaming Skull",
           "Khorn red": "Khorne Red", "gothor brown": "Gorthor Brown", "white": "White Primer",
           "blangels red": "Blood Angels Red", "ultramarine blue": "Ultramarines Blue"}

def load(page, book):
    page.goto(URL)
    page.evaluate("b => { localStorage.clear(); localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b)); }", book)
    page.reload()
    page.wait_for_timeout(300)

def saved(page):
    return page.evaluate("JSON.parse(localStorage.getItem('shades-of-grey-recipes'))")

with sync_playwright() as pw:
    browser = pw.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])
    for size, (w, h) in {"phone": (390, 844), "desktop": (1280, 900)}.items():
        page = browser.new_page(viewport={"width": w, "height": h})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        # ---- Old data: a v16 book with a scanned paint (owned: true) ----
        load(page, V16_OWNED_BOOK)
        if size == "phone":
            check("version starts with v17 (v17.1 is a patch)", page.evaluate("APP_VERSION").startswith("v17"))
            check("sw.js is v17 (or a v17 patch)", "const VERSION = \"v17" in open(os.path.join(os.path.dirname(__file__), "..", "sw.js")).read())
            check("v16 book: scanned paint shows as Owned", page.evaluate("paintStatus(book.paints.find(p => p.id === 1))") == "owned")
            check("v16 book: owned field kept", page.evaluate("book.paints.find(p => p.id === 1).owned") is True)
            check("v16 book: no status set on old paints", page.evaluate("book.paints.find(p => p.id === 1).status") is None)
            page.evaluate("pruneUnusedPaints()")
            names = page.evaluate("book.paints.map(p => p.name)")
            check("prune: scanned paint kept, unused blank paint tidied", "Nuln Oil" in names and "Old Paint" not in names, names)
            page.evaluate("book.paints.push({id: 7, brand: 'Citadel', name: 'Old Paint', colour: '#333333', status: 'wishlist'}); pruneUnusedPaints();")
            check("prune: unused paint with a status is kept", "Old Paint" in page.evaluate("book.paints.map(p => p.name)"))
            check("no status shown on Recipes when nothing set", page.locator(".have-badge").count() == 0)

        # ---- Each status, set by tapping ----
        load(page, V17_BOOK)
        page.evaluate("showTab('recipes')")
        page.click("#recipe-seg button[data-view='palette']")
        def open_paint(name):
            page.locator(".paint-item", has_text=name).locator("button.paint-head").click()
        open_paint("Abaddon Black")
        for key in ["owned", "low", "empty", "wishlist", "notowned"]:
            page.locator(".paint-item", has_text="Abaddon Black").locator(f'.status-chip[data-status="{key}"]').click()
            got = page.evaluate("paintStatus(book.paints.find(p => p.name === 'Abaddon Black'))")
            check(f"{size}: tap sets {key}", got == key, got)
        page.locator(".paint-item", has_text="Abaddon Black").locator('.status-chip[data-status="notowned"]').click()
        check(f"{size}: tapping the same status again clears it", page.evaluate("paintStatus(book.paints.find(p => p.name === 'Abaddon Black'))") == "")
        check(f"{size}: cleared status is saved as blank", page.evaluate("'status' in book.paints.find(p => p.name === 'Abaddon Black')") is False)
        page.evaluate("showTab('recipes')")
        page.click("#recipe-seg button[data-view='palette']")
        open_paint("Nuln Oil")
        spare = page.locator(".paint-item", has_text="Nuln Oil").locator(".spare-tick input")
        check(f"{size}: running low shows spare in stock tick", spare.count() == 1)
        spare.uncheck()
        check(f"{size}: spare tick saves", page.evaluate("book.paints.find(p => p.name === 'Nuln Oil').spare") is False)
        page.locator(".paint-item", has_text="Nuln Oil").locator('.status-chip[data-status="owned"]').click()
        check(f"{size}: spare tick goes when status is not running low", page.evaluate("'spare' in book.paints.find(p => p.name === 'Nuln Oil')") is False)
        page.locator(".paint-item", has_text="Nuln Oil").locator('.status-chip[data-status="low"]').click()
        page.locator(".paint-item", has_text="Nuln Oil").locator(".spare-tick input").check()
        page.screenshot(path=f"{SHOTS}/v17-{size}-palette-status.png", full_page=False)

        # ---- Search or add on Your Palette ----
        page.fill("#palette-search", "Mystic blue")
        res = page.locator("#palette-search-result").text_content()
        check(f"{size}: search shows status of a paint you have", "In your palette: wishlist" in res, res)
        page.fill("#palette-search", "Nurgle rot")
        res = page.locator("#palette-search-result").text_content()
        check(f"{size}: search says when you don't have it", "Not in your palette yet" in res, res)
        page.locator("#palette-search-result .status-chip[data-status='owned']").click()
        added = page.evaluate("book.paints.find(p => /Nurgle/.test(p.name))")
        check(f"{size}: add by typing as Owned", added and added.get("status") == "owned" and added.get("owned") is True, added)
        page.fill("#palette-search", "Khorn red")
        res = page.locator("#palette-search-result").text_content()
        check(f"{size}: typo is asked, not guessed", "Which paint do you mean?" in res, res)
        page.locator("#palette-search-result .chip", has_text="Khorne Red").first.click()
        check(f"{size}: picking a suggestion shows its status", "Not in your palette yet" in page.locator("#palette-search-result").text_content())
        page.fill("#palette-search", "")
        page.screenshot(path=f"{SHOTS}/v17-{size}-palette-search.png", full_page=False)

        # ---- Scan result shows status ----
        if size == "phone":
            page.click("#scan-button")
            page.fill("#scan-typed", "Nuln oil")
            page.press("#scan-typed", "Enter")
            page.wait_for_timeout(150)
            page.locator("#scan-panel .chip", has_text="Nuln Oil").first.click()
            verdict = page.locator("#scan-result").text_content()
            check("scan: 'Do I own this?' shows status", "running low" in verdict, verdict)

        # ---- Recipes: badges and "What can I paint now?" ----
        page.evaluate("showTab('recipes')")
        page.click("#recipe-seg button[data-view='recipes']")
        page.locator(".recipe-item", has_text="Black trim").click()
        badges = page.locator(".have-badge").all_text_contents()
        check(f"{size}: recipe shows Have and Missing badges", "✓ Have" in badges and "✗ Missing" in badges, badges)
        page.screenshot(path=f"{SHOTS}/v17-{size}-recipe-badges.png", full_page=False)
        page.click("text=← All recipes")
        page.locator("#can-paint-box .chip", has_text="What can I paint now?").click()
        titles = page.locator("#recipe-list .recipe-item .name").all_text_contents()
        check(f"{size}: 'What can I paint now?' shows only recipes you can paint", titles == ["Blue armour"], titles)
        page.screenshot(path=f"{SHOTS}/v17-{size}-can-paint.png", full_page=False)
        page.locator("#can-paint-box .chip", has_text="What can I paint now?").click()
        check(f"{size}: filter off shows all recipes again", len(page.locator("#recipe-list .recipe-item").all()) == 3)

        # ---- Shopping list ----
        page.evaluate("showTab('recipes')")
        page.click("#recipe-seg button[data-view='palette']")
        page.click("#shop-button")
        text = page.evaluate("shoppingText(shoppingItems())")
        check(f"{size}: shopping list text", text == EXPECTED_SHOPPING, text)
        check(f"{size}: shop panel shows copy button", page.locator("#shop-panel button", has_text="Copy as text").count() == 1)
        check(f"{size}: shop links slot is labelled, no links yet", "No links are added yet" in page.locator("#shop-links-slot").text_content())
        page.screenshot(path=f"{SHOTS}/v17-{size}-shopping.png", full_page=True)

        # ---- Keep note: "What can I paint now?" with the real paste ----
        if size == "phone":
            load(page, {"v15": True, "parts": ["Whole model"], "techniques": ["Layer"], "paints": [], "recipes": [], "schemes": []})
            page.evaluate("showTab('recipes')")
            page.click("#paste-recipes")
            page.fill("#import-text", KEEP_NOTE)
            page.click("text=Read notes")
            page.wait_for_timeout(200)
            for typed, answer in ANSWERS.items():
                row = page.locator(".import-ask", has=page.locator(".import-typed", has_text=f"“{typed}”"))
                row.locator("button.chip", has_text=answer).first.click()
            page.click("#import-save")
            page.wait_for_timeout(300)
            total = page.evaluate("book.recipes.length")
            check("keep: 24 recipes imported", total == 24, total)
            # Own every paint in the Tyranid scheme except Ice, then ask what you can paint.
            page.evaluate("""() => {
                const tyr = book.schemes.find(s => s.name === 'Tyranids');
                const ids = new Set();
                for (const rid of tyr.recipes) for (const s of book.recipes.find(r => r.id === rid).steps) for (const sp of s.paints) ids.add(sp.paint);
                for (const p of book.paints) if (ids.has(p.id) && p.name !== 'Ice') applyPaintStatus(p, 'owned');
                save();
            }""")
            expected = page.evaluate("book.recipes.filter(r => canPaintNow(r)).map(r => r.name).sort()")
            page.evaluate("showTab('recipes')")
            page.click("#recipe-seg button[data-view='recipes']")
            page.locator("#can-paint-box .chip", has_text="What can I paint now?").click()
            shown = sorted(page.locator("#recipe-list .recipe-item .name").all_text_contents())
            check("keep: filter matches the Tyranid recipes you own", shown == expected and len(shown) > 0 and "Ice" not in str(shown), (shown, expected))
            page.screenshot(path=f"{SHOTS}/v17-{size}-keep-can-paint.png", full_page=True)

        page.close()
    browser.close()

print()
print(f"{sum(results)} of {len(results)} checks passed")
if errors:
    print("Page errors:", errors)
sys.exit(0 if all(results) and not errors else 1)
