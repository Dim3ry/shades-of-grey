"""v62 tests for Minifolio (chunk 3.2: put a Compendium paint into a recipe).

What changed:
 A paint in the Compendium (a colour idea row, and the open panel of a colour wheel paint) has two buttons:
 "Use in a recipe" (a new recipe with the paint in step 1) and "Add to a recipe" (pick a recipe, then a step or a new step;
 saved at once). Both have Undo. A paint that is not in Your Palette is added as Not owned and the confirmation line says so.
 Made-up example paints are not offered. The "Save into a new recipe" code is reused.

Checks:
1. Versions, the v62 Updates entry, DATA_VERSION is still 1.
2. A colour idea row has both buttons; the recipe editor's own colour ideas do not.
3. Use in a recipe: a new recipe with the paint in step 1, Not owned in Your Palette, the line says so, Undo closes it and
   puts Your Palette back.
4. Add to a recipe: a new step, and an existing step (even split), each saved at once, each with Undo; the recipe and
   Your Palette come back exactly.
5. A paint already in Your Palette: the line does not claim it was added.
6. The wheel paint's open panel has both buttons.
7. Made-up example paints are not offered; the recipe editor (no share) is not offered.
8. Help names both buttons. No em dash in the new Updates entry.
9. 390 px and 360 px, dark and light: no sideways scroll, buttons 44 px or more.
10. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
import test_v31 as t
import test_v35 as c   # Compendium helpers (open every part, pick a start colour)
import test_v39 as h   # wheel and paint-panel helpers, the made-up Probe paints

read, load, no_sideways = t.read, t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

BASE = "test paints|probe blue"
NOT_OWNED_LINE = "Added to Your Palette as Not owned."
RECIPES = [{"id": 1, "name": "Probe armour", "part": "Armour", "notes": "", "steps": [
    {"technique": "Base coat", "coats": 2, "paints": [{"paint": 1, "mix": 100}], "ratio": "", "note": "", "optional": False},
    {"technique": "Wash", "coats": 1, "paints": [{"paint": 1, "mix": 100}], "ratio": "", "note": "", "optional": False}]}]

def open_ideas(page, paints, recipes=None):
    load(page, paints=paints, recipes=recipes)
    c.open_comp(page)
    c.pick_base(page, BASE)
    page.wait_for_timeout(150)

def first_row(page):
    return page.locator("#cmp-fold-ideas-panel > .idea-list > li").first

def row_name(row):
    return row.locator(".idea-name").evaluate("el => el.childNodes[0].textContent")

def stored(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-recipes'))")

def palette_entry(page, name):
    return next((p for p in stored(page)["paints"] if p["name"] == name), None)

def toast_text(page):
    return page.evaluate("() => document.getElementById('toast-text').textContent")

def tap_undo(page):
    page.click("#toast-undo")
    page.wait_for_timeout(250)

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
        load(page, paints=h.JUST_BLUE)
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v62 or later", float(version[1:]) >= 62, version)
        m = re.search(r'const VERSION = "v([\d.]+)"', read("sw.js"))
        check("sw.js VERSION matches", m and "v" + m.group(1) == version, m and m.group(1))
        tags = re.findall(r'<script src="[^"]+\?v=(\d+)"', html)
        check("all six script tags carry the version number", len(tags) == 6 and set(tags) == {version[1:]}, tags)
        check("the comments that name the number agree", f'The "?v={version[1:]}" makes' in html and f'e.g. "app.js?v={version[1:]}"' in app)
        entry = page.evaluate("CHANGELOG.find(c => c.version === 'v62')")
        check("the v62 Updates entry exists and is the newest while v62 is current", bool(entry) and (version != "v62" or page.evaluate("CHANGELOG[0].version") == "v62"))
        joined = " ".join(entry["changes"]) if entry else ""
        check("the entry names both buttons and Not owned", "Use in a recipe" in joined and "Add to a recipe" in joined and "Not owned" in joined, joined)
        check("no em dash in the v62 Updates entry", "—" not in app[app.index('{ version: "v62"'):app.index('{ version: "v61"')])
        check("DATA_VERSION is 2 (v68 raised it from 1 for the Needs touch-ups rename, so this test now expects 2)", page.evaluate("DATA_VERSION") == 2)

        # ---------- 2. The buttons on a colour idea ----------
        print("\n--- 2. The buttons ---")
        open_ideas(page, h.JUST_BLUE, RECIPES)
        row = first_row(page)
        name = row_name(row)
        labels = row.locator(".paint-recipe .paint-recipe-buttons button").all_inner_texts()
        check("a colour idea row has Use in a recipe and Add to a recipe (v65 adds Similar paints after them)", labels[:2] == ["Use in a recipe", "Add to a recipe"] and labels[2:] in ([], ["Similar paints"]), labels)
        check("that paint is not in Your Palette yet", palette_entry(page, name) is None, name)
        check("the recipe editor's own colour ideas have no such buttons (door has no share)",
              page.evaluate("() => paintToRecipeOffered({ share: null }, { name: 'X', brand: '' })") is False)

        # ---------- 3. Use in a recipe ----------
        print("\n--- 3. Use in a recipe ---")
        before = json.dumps(stored(page), sort_keys=True)
        row.locator("button", has_text="Use in a recipe").click()
        page.wait_for_timeout(300)
        draft = page.evaluate("() => recipeDraft && { id: recipeDraft.id, steps: recipeDraft.steps.map(s => s.paints.map(p => p.name)) }")
        check("a new recipe opened with the paint in step 1 only", draft and draft["id"] is None and draft["steps"] == [[name]], draft)
        check("the recipes tab is showing", page.evaluate("() => !document.getElementById('view-recipes').classList.contains('hidden')"))
        entry_now = palette_entry(page, name)
        check("the paint is in Your Palette as Not owned", entry_now and entry_now.get("status") == "notowned", entry_now)
        line = toast_text(page)
        check("the line names the paint and says it was added as Not owned", name in line and NOT_OWNED_LINE in line, line)
        check("the line has an Undo button", page.is_visible("#toast-undo"))
        check("no em dash in the line", "—" not in line)
        tap_undo(page)
        check("Undo closes the new recipe", page.evaluate("() => recipeDraft") is None)
        check("Undo puts Your Palette back exactly", json.dumps(stored(page), sort_keys=True) == before)

        # ---------- 4. Add to a recipe ----------
        print("\n--- 4. Add to a recipe ---")
        open_ideas(page, h.JUST_BLUE, RECIPES)
        row = first_row(page)
        name = row_name(row)
        before = json.dumps(stored(page), sort_keys=True)
        row.locator("button", has_text="Add to a recipe").click()
        picker = row.locator(".paint-recipe-picker")
        check("the picker opens under the buttons", picker.count() == 1)
        check("the step list is hidden until a recipe is chosen", picker.locator("select").nth(1).evaluate("el => el.classList.contains('hidden')"))
        picker.locator("select").nth(0).select_option("1")
        steps = picker.locator("select").nth(1).locator("option").all_inner_texts()
        check("the step list offers a new step and each step", steps[0] == "A new step" and len(steps) == 3 and steps[1].startswith("Step 1: Base coat"), steps)
        picker.locator("button", has_text="Add").click()
        page.wait_for_timeout(300)
        recipe = stored(page)["recipes"][0]
        added = palette_entry(page, name)
        check("a new last step holds the paint", len(recipe["steps"]) == 3 and recipe["steps"][2]["paints"] == [{"paint": added["id"], "mix": 100}], recipe["steps"][-1])
        check("the paint is Not owned in Your Palette", added.get("status") == "notowned", added)
        line = toast_text(page)
        check("the line says it went into a new step and was added as Not owned", name in line and "new step 3" in line and NOT_OWNED_LINE in line, line)
        tap_undo(page)
        check("Undo puts the recipe and Your Palette back exactly", json.dumps(stored(page), sort_keys=True) == before)

        c.open_comp(page)
        c.pick_base(page, BASE)
        row = first_row(page)
        row.locator("button", has_text="Add to a recipe").click()
        picker = row.locator(".paint-recipe-picker")
        picker.locator("select").nth(0).select_option("1")
        picker.locator("select").nth(1).select_option("0")
        picker.locator("button", has_text="Add").click()
        page.wait_for_timeout(300)
        recipe = stored(page)["recipes"][0]
        added = palette_entry(page, name)
        mixes = [sp["mix"] for sp in recipe["steps"][0]["paints"]]
        check("the paint joined step 1 with an even split", len(recipe["steps"]) == 2 and len(mixes) == 2 and mixes == [50, 50] and recipe["steps"][0]["paints"][1]["paint"] == added["id"], recipe["steps"][0])
        check("the line says step 1", "step 1" in toast_text(page), toast_text(page))
        tap_undo(page)
        check("Undo again puts everything back", json.dumps(stored(page), sort_keys=True) == before)

        # ---------- 5. A paint already in Your Palette ----------
        print("\n--- 5. A paint you already have ---")
        open_ideas(page, h.JUST_BLUE, RECIPES)
        pick = page.evaluate("""(n) => { const k = searchedPaints.find(x => x.name === n); return { brand: k.brand, name: k.name, colour: k.colour }; }""", row_name(first_row(page)))
        mine = dict(pick, id=2, status="notowned")
        open_ideas(page, h.JUST_BLUE + [mine], RECIPES)
        rows = page.locator("#cmp-fold-ideas-panel > .idea-list > li")
        row = next((rows.nth(i) for i in range(rows.count()) if row_name(rows.nth(i)) == pick["name"]), None)
        name = pick["name"]
        known = palette_entry(page, name)
        check("this idea is a paint already in Your Palette", row is not None and known is not None, name)
        row.locator("button", has_text="Use in a recipe").click()
        page.wait_for_timeout(300)
        line = toast_text(page)
        check("the line does not say it was added to Your Palette", name in line and "Not owned" not in line, line)
        check("its status is left alone", palette_entry(page, name).get("status") == known.get("status"))
        tap_undo(page)
        check("Undo closes the new recipe", page.evaluate("() => recipeDraft") is None)

        # ---------- 6. The wheel paint's panel ----------
        print("\n--- 6. A colour wheel paint ---")
        load(page, paints=h.UNOWNED)
        h.open_tab(page)
        h.tap(page, "blue")
        h.open_row(page, "Probe Blue")
        panel = page.locator("#cmp-paint-panel")
        wheel_labels = panel.locator(":scope > .paint-recipe .paint-recipe-buttons button").all_inner_texts()
        check("the open panel has both buttons for the wheel paint (v65 adds Similar paints after them)", wheel_labels[:2] == ["Use in a recipe", "Add to a recipe"] and wheel_labels[2:] in ([], ["Similar paints"]), wheel_labels)
        panel.locator(":scope > .paint-recipe button", has_text="Add to a recipe").click()
        check("with no recipes yet, Add to a recipe says so and opens no picker", panel.locator(".paint-recipe-picker").count() == 0)

        # ---------- 7. Made-up example paints are not offered ----------
        print("\n--- 7. Example paints ---")
        load(page, paints=h.JUST_BLUE + [{"id": 9, "brand": "", "name": "Example deep blue", "colour": "#223388"}])
        offered = page.evaluate("""() => ({
            made_up: paintToRecipeOffered({ share: {} }, { name: 'Example deep blue', brand: '' }),
            real: paintToRecipeOffered({ share: {} }, { name: 'Probe Blue', brand: 'Test Paints' }),
            catalogue: paintToRecipeOffered({ share: {} }, { name: 'Not In Palette Paint', brand: 'Someone' }) })""")
        check("a made-up example paint is not offered", offered["made_up"] is False, offered)
        check("a real paint is offered, in your palette or not", offered["real"] is True and offered["catalogue"] is True, offered)

        # ---------- 8. Help ----------
        print("\n--- 8. Help ---")
        help_text = page.evaluate("() => (document.getElementById('help-paint-to-recipe') || {}).textContent || ''")
        check("Help names both buttons, Undo and Not owned", all(w in help_text for w in ["Use in a recipe", "Add to a recipe", "Undo", "Not owned"]), help_text)
        check("no em dash in the Help item", "—" not in help_text)

        # ---------- 9. Phones, dark and light ----------
        print("\n--- 9. Phones ---")
        for width in (390, 360):
            for scheme in ("dark", "light"):
                page.set_viewport_size({"width": width, "height": 844})
                page.emulate_media(color_scheme=scheme)
                open_ideas(page, h.JUST_BLUE, RECIPES)
                row = first_row(page)
                row.locator("button", has_text="Add to a recipe").click()
                row.locator(".paint-recipe-picker select").nth(0).select_option("1")
                page.wait_for_timeout(100)
                sizes = page.evaluate("""() => [...document.querySelectorAll('#cmp-fold-ideas-panel .paint-recipe button, #cmp-fold-ideas-panel .paint-recipe select')]
                    .filter(el => el.offsetParent).map(el => Math.round(el.getBoundingClientRect().height))""")
                check(f"{width} px {scheme}: no sideways scroll", no_sideways(page))
                check(f"{width} px {scheme}: the buttons and pickers are 44 px or more", sizes and min(sizes) >= 44, sizes)

        # ---------- 10. Errors ----------
        print("\n--- 10. Errors ---")
        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
