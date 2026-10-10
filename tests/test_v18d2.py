"""Test (v18d-2a): change a step, and leave a whole part or a part note out, in the Paste recipes preview.

- ✕ on a part's name leaves that whole part out.
- Each part note is on its own line with a ✕ to leave it out.
- ✎ on a step opens a small editor: change its technique (or set it back to Auto), or change
  or clear its mix ratio. Done or Esc closes it.
All of these only change the preview: your pasted notes in the box stay as they were, so Read
again brings back exactly what you pasted. Each change says what it did and offers Undo.

Serve the repo folder first (run_all.py does this for you), then run:
python3 tests/test_v18d2.py
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
Note: thin your paints
Note: do the trim last
Mephiston Red
2:1 Mephiston Red:Abaddon Black
Agrax Earthshade (wash)

Eyes:
Khorn red
Moot Green

Rocks:
Stirland Mud
Nuln Oil"""

TRICKY = """Test scheme

Cloak <img src=x onerror="window.__hacked=1">:
Note: <b>bold</b> note
Mephiston Red"""

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

def read_again(page):
    page.click("#import-page button.primary-button")
    page.wait_for_timeout(100)

def lines(page):
    return page.eval_on_selector_all("#import-page .import-line-body", "els => els.map(e => e.textContent.trim())")

def parts(page):
    return page.eval_on_selector_all("#import-page .import-part", "els => els.map(e => e.textContent.trim())")

def notes(page):
    return page.eval_on_selector_all("#import-page .import-note-line .step-note", "els => els.map(e => e.textContent.trim())")

def step_li(page, n):
    return page.locator("#import-page .import-steps li").nth(n)

def open_editor(page, n):
    step_li(page, n).locator(".import-edit").click()
    page.wait_for_timeout(50)

def editor(page):
    return page.locator("#import-page .import-step-editor")

def toast(page):
    return page.evaluate("document.getElementById('toast').classList.contains('hidden') ? '' : document.getElementById('toast').textContent")

def undo(page):
    page.click("#toast-undo")
    page.wait_for_timeout(50)

def focused(page):
    return page.evaluate("""() => { const a = document.activeElement;
      return a ? (a.className || a.tagName) + '|' + (a.dataset.importFocus || '') : ''; }""")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        start(page)

        # --- 1. The new buttons are there ---
        paste(page, NOTE)
        start_lines = lines(page)
        check("a ✕ on every part's name", page.locator("#import-page .import-drop-part").count() == 3)
        check("part names show just the name (no ✕ in the text)", parts(page) == ["Cloak", "Eyes", "Rocks"], parts(page))
        check("each part note on its own line, with a ✕", notes(page) == ["thin your paints", "do the trim last"]
              and page.locator("#import-page .import-drop-note").count() == 2, notes(page))
        check("a ✎ on every step line (and still one ✕ each)", page.locator("#import-page .import-edit").count() == 7
              == page.locator("#import-page .import-remove").count() == len(start_lines), len(start_lines))
        check("buttons say what they do (for screen readers)",
              page.locator("#import-page .import-drop-part").first.get_attribute("aria-label") == "Leave out the whole Cloak part"
              and page.locator("#import-page .import-drop-note").first.get_attribute("aria-label") == "Leave out the note “thin your paints” from Cloak"
              and step_li(page, 0).locator(".import-edit").get_attribute("aria-label") == "Change Mephiston Red in Cloak",
              page.locator("#import-page .import-drop-part").first.get_attribute("aria-label"))
        check("the hint mentions ✎ and the part ✕", "Tap ✎ on a step" in page.text_content("#import-page")
              and "✕ on a part's name" in page.text_content("#import-page"))

        # --- 2. Leave a part note out ---
        page.locator("#import-page .import-drop-note").first.click()
        page.wait_for_timeout(50)
        check("that note is gone, the other stays", notes(page) == ["do the trim last"], notes(page))
        check("says which note, with Undo", "Left out the note “thin your paints” from Cloak" in toast(page)
              and page.is_visible("#toast-undo"), toast(page))
        check("your pasted notes are unchanged", page.input_value("#import-text") == NOTE)
        undo(page)
        check("Undo: the note is back, in order", notes(page) == ["thin your paints", "do the trim last"], notes(page))

        # --- 3. Leave a whole part out ---
        check("starts with an unsure paint to check (Khorn red, in Eyes)", page.locator("#import-page .import-check").count() == 1)
        page.locator("#import-page .import-drop-part").nth(1).click()
        page.wait_for_timeout(50)
        check("the Eyes part and its steps are gone", parts(page) == ["Cloak", "Rocks"] and len(lines(page)) == 5, parts(page))
        check("says so, with Undo", "Left out Eyes (2 steps)" in toast(page), toast(page))
        check("its unsure paint no longer holds up Save", page.locator("#import-page .import-check").count() == 0
              and page.text_content("#import-save") == "Save 2 recipes", page.text_content("#import-save"))
        undo(page)
        check("Undo: Eyes is back in the middle", parts(page) == ["Cloak", "Eyes", "Rocks"] and lines(page) == start_lines, parts(page))
        check("Undo: the unsure paint is asked about again", page.locator("#import-page .import-check").count() == 1)
        page.locator("#import-page .import-drop-part").nth(1).focus()
        page.keyboard.press("Enter")
        page.wait_for_timeout(50)
        check("keyboard: focus moves to the next part's ✕",
              page.evaluate("document.activeElement === document.querySelectorAll('#import-page .import-drop-part')[1]"), focused(page))
        undo(page)

        # --- 4. Change a step's technique ---
        open_editor(page, 0)
        check("✎ opens a small editor under that step", editor(page).count() == 1
              and step_li(page, 0).locator(".import-step-editor").count() == 1)
        check("✎ shows it's open, and focus goes to the technique list",
              step_li(page, 0).locator(".import-edit").get_attribute("aria-expanded") == "true"
              and focused(page).endswith("|technique"), focused(page))
        check("a single-paint step has no ratio box", editor(page).locator("input").count() == 0)
        editor(page).locator("select").select_option("Base coat")
        page.wait_for_timeout(50)
        check("the line now says Base coat", lines(page)[0].startswith("Base coat") and "Mephiston Red" in lines(page)[0], lines(page)[0])
        check("says what changed, with Undo", "Mephiston Red: technique changed to Base coat" in toast(page), toast(page))
        check("the editor stays open, focus still on the list", editor(page).count() == 1 and focused(page).endswith("|technique"), focused(page))
        undo(page)
        check("Undo: back to the guess (auto)", lines(page)[0] == start_lines[0] and "(auto)" in lines(page)[0], lines(page)[0])
        editor(page).locator("select").select_option("Base coat")
        page.wait_for_timeout(50)

        # Set back to Auto
        open_editor(page, 2)
        check("only one editor open at a time", editor(page).count() == 1
              and step_li(page, 2).locator(".import-step-editor").count() == 1)
        check("the list starts on the step's own technique (Wash)", editor(page).locator("select").input_value() == "Wash",
              editor(page).locator("select").input_value())
        editor(page).locator("select").select_option("")
        page.wait_for_timeout(50)
        check("Auto: the line shows the guess", "(auto)" in lines(page)[2], lines(page)[2])
        undo(page)
        check("Undo: Wash again", lines(page)[2].startswith("Wash"), lines(page)[2])

        # --- 5. Change and clear the mix ratio ---
        open_editor(page, 1)
        ratio = editor(page).locator("input")
        check("a mix step has a ratio box with its ratio", ratio.count() == 1 and ratio.input_value() == "2:1", ratio.input_value())
        ratio.fill("3:1")
        ratio.press("Enter")
        page.wait_for_timeout(50)
        check("Enter sets the new ratio", "mix 3:1" in lines(page)[1] and "mix 2:1" not in lines(page)[1], lines(page)[1])
        check("says so, with Undo", "mix ratio set to 3:1" in toast(page), toast(page))
        undo(page)
        check("Undo: back to 2:1", "mix 2:1" in lines(page)[1], lines(page)[1])
        ratio = editor(page).locator("input")
        ratio.fill("1:2:3")
        ratio.press("Enter")
        page.wait_for_timeout(50)
        check("a ratio that doesn't fit isn't used, and it says why",
              "mix 2:1" in lines(page)[1] and editor(page).locator(".import-ratio-warning").is_visible()
              and "needs 2 numbers" in editor(page).locator(".import-ratio-warning").text_content(),
              editor(page).locator(".import-ratio-warning").text_content())
        editor(page).locator(".import-ratio-clear").click()
        page.wait_for_timeout(50)
        check("Clear takes the ratio off (even mix)", "mix" not in lines(page)[1], lines(page)[1])
        check("says so, and Clear is now greyed out", "mix ratio cleared" in toast(page)
              and editor(page).locator(".import-ratio-clear").is_disabled(), toast(page))
        undo(page)
        check("Undo: 2:1 is back", "mix 2:1" in lines(page)[1], lines(page)[1])
        # Type a ratio, then tap Done straight away
        editor(page).locator("input").fill("3:1")
        editor(page).locator(".import-edit-done").click()
        page.wait_for_timeout(50)
        check("Done keeps a typed ratio and closes the editor", "mix 3:1" in lines(page)[1] and editor(page).count() == 0, lines(page)[1])
        check("…and focus goes back to its ✎", page.evaluate(
            "document.activeElement === document.querySelectorAll('#import-page .import-edit')[1]"), focused(page))
        # Esc closes
        open_editor(page, 3)
        page.keyboard.press("Escape")
        page.wait_for_timeout(50)
        check("Esc closes the editor", editor(page).count() == 0)

        # --- 6. A change survives leaving out (and putting back) another step ---
        step_li(page, 6).locator(".import-remove").click()   # Nuln Oil
        page.wait_for_timeout(50)
        undo(page)
        check("changes you made are kept through another Undo",
              lines(page)[0].startswith("Base coat") and "mix 3:1" in lines(page)[1], lines(page)[:2])
        check("your pasted notes are still unchanged", page.input_value("#import-text") == NOTE)

        # --- 7. Read again brings back exactly what you pasted ---
        page.locator("#import-page .import-drop-note").first.click()
        page.locator("#import-page .import-drop-part").nth(2).click()
        page.wait_for_timeout(50)
        read_again(page)
        check("Read again: every part, note, technique and ratio as pasted",
              lines(page) == start_lines and parts(page) == ["Cloak", "Eyes", "Rocks"]
              and notes(page) == ["thin your paints", "do the trim last"], (lines(page), notes(page)))

        # --- 8. What gets saved ---
        open_editor(page, 0)
        editor(page).locator("select").select_option("Base coat")
        page.wait_for_timeout(50)
        open_editor(page, 1)
        editor(page).locator("input").fill("3:1")
        editor(page).locator("input").press("Enter")
        page.wait_for_timeout(50)
        page.locator("#import-page .import-drop-note").first.click()     # thin your paints
        page.locator("#import-page .import-drop-part").nth(2).click()    # Rocks
        page.wait_for_timeout(50)
        page.locator("#import-page .import-ask .chip", has_text="Khorne Red").first.click()
        page.wait_for_timeout(50)
        page.click("#import-save")
        page.wait_for_timeout(200)
        b = saved_book(page)
        recipes = {r["name"]: r for r in b.get("recipes", [])}
        names = {x["id"]: x["name"] for x in b.get("paints", [])}
        cloak = recipes.get("Cloak", {})
        steps = cloak.get("steps", [])
        check("saved: Cloak and Eyes, but not Rocks", sorted(recipes) == ["Cloak", "Eyes"], sorted(recipes))
        check("saved: only the note you kept", cloak.get("notes") == "do the trim last", cloak.get("notes"))
        check("saved: the technique you picked", len(steps) == 3 and steps[0]["technique"] == "Base coat", steps[:1])
        check("saved: the ratio you set (3:1 = 75% / 25%)", len(steps) > 1 and steps[1]["ratio"] == "3:1"
              and [x["mix"] for x in steps[1]["paints"]] == [75, 25], steps[1:2])
        check("saved: an untouched step keeps what was read (Wash)", len(steps) > 2 and steps[2]["technique"] == "Wash", steps[2:])
        check("saved: Rocks' paints aren't added to your palette",
              "Stirland Mud" not in names.values() and "Nuln Oil" not in names.values(), sorted(names.values()))

        # A cleared ratio saves as an even mix
        paste(page, NOTE)
        open_editor(page, 1)
        editor(page).locator(".import-ratio-clear").click()
        page.wait_for_timeout(50)
        # (Khorn red isn't asked about this time: your earlier answer was remembered.)
        page.click("#import-save")
        page.wait_for_timeout(200)
        b = saved_book(page)
        mix = [r for r in b["recipes"] if r["name"].startswith("Cloak (")]
        check("saved: a cleared ratio is an even mix (50% / 50%)", mix and mix[0]["steps"][1]["ratio"] == ""
              and [x["mix"] for x in mix[0]["steps"][1]["paints"]] == [50, 50], mix and mix[0]["steps"][1])

        # --- 9. Odd text is shown as plain text ---
        start(page)
        paste(page, TRICKY)
        check("part names and notes with HTML in them are plain text",
              page.evaluate("!window.__hacked") and page.locator("#import-page .import-part img").count() == 0
              and "<b>bold</b> note" in notes(page) and page.locator("#import-page .import-note-line b").count() == 0, notes(page))

        # --- 10. Small phone ---
        start(page)
        page.set_viewport_size({"width": 360, "height": 740})
        paste(page, NOTE)
        open_editor(page, 1)
        sizes = page.eval_on_selector_all("#import-page .import-edit, #import-page .import-drop-part, #import-page .import-drop-note",
                                          "els => els.map(e => [e.getBoundingClientRect().width, e.getBoundingClientRect().height])")
        check("small phone: ✎ and ✕ buttons are big enough to tap (32px)", sizes and all(w >= 32 and h >= 32 for w, h in sizes), sizes)
        check("small phone: no sideways scrolling, even with the editor open",
              page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"),
              page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]"))
        page.screenshot(path=os.path.join(os.path.dirname(__file__), "screenshots", "v18d2_editor_360.png"), full_page=True)

        check("no page errors", not errors, errors)
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
