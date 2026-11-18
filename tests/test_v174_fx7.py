"""FX7 tests for Minifolio: toasts, counts and small text (AR4 findings 10 to 15). New behaviour only.
1. A message with no words never shows (so no empty Undo bar), and a message older than a moment goes when you tap another screen.
2. "'Ardcoat" keeps its leading apostrophe through matching, recipe notes, the Your Palette search box and the paste preview, and the
   preview puts a real space between the step name and the paint.
3. "Opens the shop's website" is no longer page text (it is still the description of a shop link).
4. Colour ideas: the empty line names the "Start from" box instead of "above".
5. The restore question names Gear and shopping paints, only when there are some.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import leave_launch, tap_tab

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

UNITS = [{"id": 1, "name": "Squad 1", "hobby": "Skirmish", "faction": "Bright Host", "stage": 1, "count": 3, "added": "2026-09-01", "log": [["2026-09-01", 1]]}]
PAINTS = [{"id": 1, "brand": "Citadel", "name": "Mephiston Red", "colour": "#9a1115", "status": "wishlist"},
          {"id": 2, "brand": "Citadel", "name": "Abaddon Black", "colour": "#231f20", "status": "owned"}]

def toast(page):
    return page.evaluate("[!document.getElementById('toast').classList.contains('hidden'), document.getElementById('toast-text').textContent]")

def restore(page, data):
    page.set_input_files("#restore-file", files=[{"name": "b.json", "mimeType": "application/json", "buffer": json.dumps(data).encode()}])
    page.wait_for_selector("#dialog-backdrop:not(.hidden)")
    q = page.text_content("#dialog-message")
    page.click("#dialog-no")
    page.wait_for_timeout(200)
    return q

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. Messages ---")
        t.load(page, paints=PAINTS, units=UNITS, settings={"tab": "units", "examplesChecked": True}); leave_launch(page)
        page.evaluate("showToast('', () => {}, 'Undo', UNDO_SECONDS)")
        check("an Undo with no words shows nothing at all", toast(page)[0] is False, toast(page))
        page.evaluate("showToast(undefined, () => {})")
        check("no message at all shows nothing either", toast(page)[0] is False)
        page.evaluate("showToast('Removed Thing', () => {}, 'Undo', UNDO_SECONDS)")
        check("a message with words still shows, with its Undo", toast(page) == [True, "Removed Thing"] and page.is_visible("#toast-undo"), toast(page))
        page.wait_for_timeout(800)
        tap_tab(page, "dashboard")
        page.wait_for_timeout(700)   # (the fading copy of the message is gone by then)
        check("a message 0.8 s old goes when you tap another screen", toast(page)[0] is False and "Removed Thing" not in page.evaluate("document.body.textContent"), toast(page))

        print("\n--- 2. 'Ardcoat ---")
        r = page.evaluate("""() => { const o = {};
            for (const x of ["'Ardcoat", "Ardcoat", "'ardcoat'", "Citadel 'Ardcoat"]) o[x] = matchPaint(x).paint.name;
            o.steps = parseRecipeText("Scheme\\nGloss: 'Ardcoat\\nVarnish 'Ardcoat\\n").schemes[0].parts.flatMap(pt => pt.steps.flatMap(s => s.paints.map(m => m.paint.name)));
            return o; }""")
        check("matching keeps the apostrophe however it is typed", all(r[k] == "'Ardcoat" for k in ["'Ardcoat", "Ardcoat", "'ardcoat'", "Citadel 'Ardcoat"]), r)
        check("pasted recipe notes keep it on every step", r["steps"] == ["'Ardcoat", "'Ardcoat"], r["steps"])
        page.evaluate("showTab('recipes')")
        page.click("#recipe-seg button[data-view='palette']")
        page.fill("#palette-search", "'Ardcoat")
        page.wait_for_timeout(200)
        check("the Your Palette box shows the paint with its apostrophe", "'Ardcoat" in page.inner_text("#palette-search-result"), page.inner_text("#palette-search-result"))
        page.click("#recipe-seg button[data-view='recipes']")
        page.click("#paste-recipes")
        page.fill("#import-text", "Test scheme\n\nWhole model:\nVarnish: 'Ardcoat")
        page.click("text=Read notes")
        page.wait_for_timeout(300)
        line = page.evaluate("""() => { const tech = document.querySelector('.import-tech'); const li = tech.closest('li') || tech.parentElement;
            return { text: li.textContent, spaced: tech.nextSibling && tech.nextSibling.nodeType === 3 && tech.nextSibling.textContent === ' ' }; }""")
        check("the paste preview line reads step name, space, 'Ardcoat", line["spaced"] and "'Ardcoat" in line["text"] and ")'Ardcoat" not in line["text"] and "Varnish'Ardcoat" not in line["text"], line)

        print("\n--- 3. The shop line ---")
        page.evaluate("opensSiteId()")
        h = page.evaluate("""() => { const e = document.getElementById('opens-site'); return { display: getComputedStyle(e).display, text: e.textContent, inPage: document.body.innerText.includes("Opens the shop") }; }""")
        check("it is display:none, so it is not page text", h["display"] == "none" and not h["inPage"], h)
        check("it still says the same words for a link to point at", h["text"] == "Opens the shop's website")

        print("\n--- 4. Colour ideas ---")
        t.load(page, paints=PAINTS, units=UNITS, settings={"tab": "recipes", "recipeView": "colourlab", "examplesChecked": True, "recipeExamplesChecked": True}); leave_launch(page)
        page.evaluate("openColourLab('ideas')")
        page.wait_for_timeout(200)
        line = page.text_content("#cmp-colour-ideas-none")
        check("with nothing chosen the line names the Start from box", line == "Pick a paint in Start from to get 3 that go with it.", line)

        print("\n--- 5. The restore question ---")
        book = {"parts": ["Whole model"], "techniques": ["Layer"], "paints": [dict(x) for x in PAINTS] + [{"id": 3, "brand": "Citadel", "name": "Nuln Oil", "colour": "#222222", "status": "wishlist"}],
                "recipes": [], "schemes": [], "shorthand": {}, "v15": True,
                "gear": [{"id": "wet palette", "name": "wet palette"}, {"id": "brush soap", "name": "brush soap"}]}
        t.load(page, units=UNITS, settings={"tab": "settings", "examplesChecked": True}); leave_launch(page)
        q = restore(page, {"app": "Minifolio", "dataVersion": 3, "models": UNITS, "recipes": book})
        check("it names 2 Gear items and 2 shopping paints from the backup", "2 Gear items and 2 shopping paints" in q and q.endswith("from the backup?"), q)
        plain = {k: v for k, v in book.items() if k != "gear"}
        plain["paints"] = [x for x in plain["paints"] if x["status"] != "wishlist"]
        q2 = restore(page, {"app": "Minifolio", "dataVersion": 3, "models": UNITS, "recipes": plain})
        check("with none of either in the backup, the new side does not mention them (yours, 1 shopping paint, still is)", "Gear" not in q2 and "shopping paint" not in q2.split(" with ", 1)[1] and "1 shopping paint" in q2, q2)

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

main()
