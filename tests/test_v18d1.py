"""Test (v18d-1): a ✕ on each step line of the Paste recipes preview.

Tapping ✕ leaves that step out of what will be saved. Your pasted notes in the box don't
change, so Read again brings every step back. A part with no steps left is left out too, and
a scheme with no parts left. Undo puts back exactly what was there.

Leaving a step out also tidies the rest of the preview:
- an unsure paint that was only in that step stops being asked about (so it can't hold up Save),
  and answers you've already given to other paints are kept;
- a new paint that was only in that step drops off "Do you own these?" and isn't added;
- a scheme name you typed is kept.

Serve the repo folder first (run_all.py does this for you), then run:
python3 tests/test_v18d1.py
The port comes from the SOG_PORT environment variable, or 8765 if it isn't set."""
import json, os, sys
from playwright.sync_api import sync_playwright

PORT = os.environ.get("SOG_PORT", "8765")
BASE = f"http://localhost:{PORT}"
RECIPES_KEY = "shades-of-grey-recipes"

results = []
def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

NOTE = """Test scheme

Cloak:
Mephiston Red
Khorn red
Agrax Earthshade

Eyes:
Zorblax Goo

Rocks:
Stirland Mud
Nuln Oil"""

TWO_SCHEMES = """Tyranids

Chitin:
Naggaroth Night

Ultramarines

Armour:
Macragge Blue
Nuln Oil"""

def start(page):
    page.goto(f"{BASE}/manifest.json")
    page.evaluate("() => { localStorage.clear(); localStorage.setItem('mini-tracker-models', '[]'); }")
    page.goto(f"{BASE}/index.html")
    page.wait_for_timeout(300)

def saved_book(page):
    return json.loads(page.evaluate(f"localStorage.getItem('{RECIPES_KEY}') || '{{}}'"))

def paste(page, text):
    page.evaluate("startImport()")
    page.fill("#import-text", text)
    page.click("#import-page button.primary-button")   # "Read notes"
    page.wait_for_timeout(100)

def lines(page):
    """The step lines in the preview, as their text (without the ✕)."""
    return page.eval_on_selector_all("#import-page .import-line-body", "els => els.map(e => e.textContent.trim())")

def parts(page):
    return page.eval_on_selector_all("#import-page .import-part", "els => els.map(e => e.textContent.trim())")

def remove_line(page, has_text):
    page.locator("#import-page .import-steps li", has_text=has_text).locator(".import-remove").click()
    page.wait_for_timeout(50)

def toast(page):
    return page.evaluate("document.getElementById('toast').classList.contains('hidden') ? '' : document.getElementById('toast').textContent")

def undo(page):
    page.click("#toast-undo")
    page.wait_for_timeout(50)

def save_text(page):
    return page.text_content("#import-save")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        start(page)

        # --- 1. Every step line has a ✕ ---
        paste(page, NOTE)
        start_lines = lines(page)
        check("one ✕ on every step line", page.locator("#import-page .import-remove").count() == len(start_lines) == 6,
              (page.locator("#import-page .import-remove").count(), start_lines))
        check("the ✕ says what it leaves out (for screen readers)",
              page.locator("#import-page .import-remove").first.get_attribute("aria-label") == "Leave out Mephiston Red from Cloak",
              page.locator("#import-page .import-remove").first.get_attribute("aria-label"))
        check("a hint explains the ✕", "Tap ✕ on a step to leave it out" in page.text_content("#import-page"))
        check("starts with an unsure paint to check", page.locator("#import-page .import-check").count() == 1)
        check("Save waits for it", page.locator("#import-save").is_disabled(), save_text(page))
        page.click("#import-page [data-own=pick]")
        own_before = page.eval_on_selector_all("#import-page .own-paint", "els => els.map(e => e.textContent)")
        check("the new paint is asked about under Do you own these?", any("Zorblax Goo" in t for t in own_before), own_before)

        # --- 2. Leave out one step (the part keeps its other steps) ---
        remove_line(page, "Mephiston Red")
        now = lines(page)
        check("that line is gone", len(now) == 5 and not any("Mephiston Red" in t for t in now), now)
        check("the other lines are still in order", now == start_lines[1:], now)
        check("says what was left out, with Undo", "Left out “Mephiston Red” from Cloak" in toast(page)
              and page.is_visible("#toast-undo"), toast(page))
        check("still 3 recipes to save (no part lost)", parts(page) == ["Cloak", "Eyes", "Rocks"], parts(page))
        check("your pasted notes are unchanged", page.input_value("#import-text") == NOTE)

        # --- 3. An unsure paint only in a left-out step stops holding up Save ---
        remove_line(page, "Khorn red")
        check("the unsure paint isn't asked about any more", page.locator("#import-page .import-check").count() == 0)
        check("Save is ready", not page.locator("#import-save").is_disabled() and save_text(page) == "Save 3 recipes", save_text(page))

        # --- 4. Undo puts it back, in the same place ---
        undo(page)
        check("Undo: the line is back in its place", lines(page) == start_lines[1:], lines(page))
        check("Undo: the unsure paint is asked about again", page.locator("#import-page .import-check").count() == 1)

        # --- 5. An answer you've given is kept when another step is left out ---
        page.locator("#import-page .import-ask .chip", has_text="Khorne Red").first.click()
        remove_line(page, "Agrax Earthshade")
        check("your answer (Khorne Red) is kept", page.locator("#import-page .import-check").count() == 1
              and page.locator("#import-page .import-ask.answered").count() == 1
              and any("Khorn red → Khorne Red" in t for t in lines(page)), lines(page))
        undo(page)

        # --- 6. Leaving out a part's last step leaves the part out ---
        page.fill("#import-page input[aria-label='Scheme 1 name']", "My Sisters")
        remove_line(page, "Zorblax Goo")
        check("Eyes had one step, so it's gone too", parts(page) == ["Cloak", "Rocks"], parts(page))
        check("the message says so", "Eyes had no steps left" in toast(page), toast(page))
        check("Save counts one fewer recipe", save_text(page) == "Pick 1 more paint first" or save_text(page) == "Save 2 recipes", save_text(page))
        own_after = page.eval_on_selector_all("#import-page .own-paint", "els => els.map(e => e.textContent)")
        check("its new paint drops off Do you own these?", own_after and not any("Zorblax Goo" in t for t in own_after), own_after)
        check("the scheme name you typed is kept", page.input_value("#import-page input[aria-label='Scheme 1 name']") == "My Sisters")
        undo(page)
        check("Undo brings the part back", parts(page) == ["Cloak", "Eyes", "Rocks"], parts(page))
        check("…with its new paint", any("Zorblax Goo" in t for t in lines(page)), lines(page))
        check("…and keeps the scheme name you typed", page.input_value("#import-page input[aria-label='Scheme 1 name']") == "My Sisters")
        remove_line(page, "Zorblax Goo")

        # --- 7. Focus moves to the next ✕ (for keyboard users) ---
        page.locator("#import-page .import-steps li", has_text="Stirland Mud").locator(".import-remove").focus()
        page.keyboard.press("Enter")
        page.wait_for_timeout(50)
        focused = page.evaluate("document.activeElement && document.activeElement.getAttribute('aria-label')")
        check("after Enter on ✕, focus moves to the next ✕", focused == "Leave out Nuln Oil from Rocks", focused)
        undo(page)

        # --- 8. Saving leaves the step out for real ---
        # Mephiston Red was left out in part 2 (never undone), so Cloak keeps only "Khorn red → Khorne Red".
        remove_line(page, "Agrax Earthshade")
        page.click("#import-save")
        page.wait_for_timeout(200)
        book = saved_book(page)
        names = {x["id"]: x["name"] for x in book.get("paints", [])}
        recipes = {r["name"]: [[names.get(sp["paint"]) for sp in s["paints"]] for s in r["steps"]] for r in book.get("recipes", [])}
        check("saved: Cloak has only the steps you kept", recipes.get("Cloak") == [["Khorne Red"]], recipes)
        check("saved: Eyes (left out) isn't saved", "Eyes" not in recipes, recipes)
        check("saved: Rocks is saved whole", recipes.get("Rocks") == [["Stirland Mud"], ["Nuln Oil"]], recipes)
        check("saved: left-out paints aren't added to your palette",
              "Zorblax Goo" not in names.values() and "Agrax Earthshade" not in names.values(), sorted(names.values()))
        check("saved: under the name you typed", [s["name"] for s in book.get("schemes", [])] == ["My Sisters"], book.get("schemes"))

        # --- 9. Leave out everything, then Read again ---
        start(page)
        paste(page, TWO_SCHEMES)
        page.fill("#import-page input[aria-label='Scheme 2 name']", "Blue boys")
        remove_line(page, "Naggaroth Night")
        check("a scheme with no parts left is gone", page.locator("#import-page input[aria-label^='Scheme']").count() == 1)
        check("the scheme that's left keeps the name you typed",
              page.input_value("#import-page input[aria-label='Scheme 1 name']") == "Blue boys")
        undo(page)
        check("Undo brings the scheme back, names in the right boxes",
              page.input_value("#import-page input[aria-label='Scheme 1 name']") == "Tyranids"
              and page.input_value("#import-page input[aria-label='Scheme 2 name']") == "Blue boys")
        for t in ["Naggaroth Night", "Macragge Blue", "Nuln Oil"]:
            remove_line(page, t)
        check("everything left out: says so, and how to get it back",
              "left every step out" in page.text_content("#import-page") and "Read again" in page.text_content("#import-page"))
        check("everything left out: no Save button", page.locator("#import-save").count() == 0)
        page.click("#import-page button.primary-button")   # Read again
        page.wait_for_timeout(100)
        check("Read again brings every step back", len(lines(page)) == 3 and len(parts(page)) == 2, lines(page))

        # --- 10. Fits a small phone ---
        page.set_viewport_size({"width": 360, "height": 740})
        page.evaluate("startImport()")
        page.fill("#import-text", "Long one\n\nCloak:\n" + "Mephiston Red + Khorne Red + Evil Sunz Scarlet + Wild Rider Red 1:1:1:1 (thin, two coats, let dry)")
        page.click("#import-page button.primary-button")
        page.wait_for_timeout(100)
        box = page.locator("#import-page .import-remove").first.bounding_box()
        check("small phone: the ✕ is big enough to tap (32px)", box and box["width"] >= 32 and box["height"] >= 32, box)
        wide = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        check("small phone: no sideways scrolling", not wide)
        page.screenshot(path=os.path.join(os.path.dirname(__file__), "screenshots", "v18d1-preview.png"), full_page=True)

        check("no page errors", not errors, errors)
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    os.makedirs(os.path.join(os.path.dirname(__file__), "screenshots"), exist_ok=True)
    main()
