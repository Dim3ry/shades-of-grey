"""Test (v18d-2b): swap a paint in a step of the Paste recipes preview.

In the ✎ editor (from v18d-2a), each paint in the step has a row with its name and Change….
Change… opens a small box: type a name, then Use (or Enter). The name is matched the same way
as "Other…" in "Check N paints" (a paint it knows, a near-exact suggestion, or a new paint named
as typed). Only that step changes. "Check N paints", "Do you own these?" and the Save button
update to match. The mix ratio is unchanged. Undo puts the old paint back; Read again brings
back what was pasted.

Serve the repo folder first (run_all.py does this for you), then run:
python3 tests/test_v18d2b.py
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

# Steps in order: 0 Mephiston Red, 1 2:1 Mephiston Red:CM, 2 Agrax, 3 CM (Eyes), 4 Moot Green.
# "CM" is a paint it isn't sure about (it asks: Contrast Medium?), and it's in two steps.
NOTE = """Test scheme

Cloak:
Mephiston Red
2:1 Mephiston Red:CM
Agrax Earthshade (wash)

Eyes:
CM
Moot Green"""

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

def step_li(page, n):
    return page.locator("#import-page .import-steps li").nth(n)

def open_editor(page, n):
    step_li(page, n).locator(".import-edit").click()
    page.wait_for_timeout(50)

def editor(page):
    return page.locator("#import-page .import-step-editor")

def swap_names(page):
    return page.eval_on_selector_all("#import-page .import-swap-name", "els => els.map(e => e.textContent.trim())")

def change(page, i):
    editor(page).locator(".import-swap").nth(i).click()
    page.wait_for_timeout(50)

def type_swap(page, text, how="enter"):
    page.fill("#import-page .import-swap-input", text)
    if how == "enter":
        page.press("#import-page .import-swap-input", "Enter")
    else:
        page.click("#import-page .import-swap-use")
    page.wait_for_timeout(50)

def asks(page):
    return page.eval_on_selector_all("#import-page .import-check .import-typed", "els => els.map(e => e.textContent.trim())")

def save_text(page):
    return page.text_content("#import-save")

def own_labels(page):
    page.click("#import-own [data-own='pick']")
    page.wait_for_timeout(30)
    out = page.eval_on_selector_all("#import-own .own-paint", "els => els.map(e => e.getAttribute('aria-label').split(':')[0])")
    page.click("#import-own [data-own='all']")
    page.wait_for_timeout(30)
    return out

def toast(page):
    return page.evaluate("document.getElementById('toast').classList.contains('hidden') ? '' : document.getElementById('toast').textContent")

def undo(page):
    page.click("#toast-undo")
    page.wait_for_timeout(50)

def focused(page):
    return page.evaluate("""() => { const a = document.activeElement;
      return a ? (a.className || a.tagName) + '|' + (a.dataset.importFocus || '') : ''; }""")

def recipe_paints(book, name):
    by_id = {p["id"]: p for p in book.get("paints", [])}
    r = next((r for r in book.get("recipes", []) if r["name"] == name), None)
    if not r:
        return None
    return [([by_id[x["paint"]]["name"] for x in s["paints"]], s.get("ratio", ""), [x["mix"] for x in s["paints"]]) for s in r["steps"]]

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        start(page)

        # --- 1. The rows in the editor ---
        paste(page, NOTE)
        start_lines = lines(page)
        check("to start: asks about CM (twice), and Save waits for it",
              asks(page) == ["“CM” (2 times)"] and page.is_disabled("#import-save"), [asks(page), save_text(page)])
        open_editor(page, 1)
        check("the editor lists each paint in the step, with Change…",
              swap_names(page) == ["Mephiston Red", "CM?"] and editor(page).locator(".import-swap").count() == 2, swap_names(page))
        check("Change… says what it does (for screen readers)",
              editor(page).locator(".import-swap").nth(1).get_attribute("aria-label") == "Change CM? to a different paint",
              editor(page).locator(".import-swap").nth(1).get_attribute("aria-label"))
        check("the hint mentions changing paints", "change its technique, mix ratio or paints" in page.text_content("#import-page"))

        # --- 2. Open the box, swap the unsure CM in this step ---
        change(page, 1)
        check("Change… opens a box in the editor (not a pop-up), with focus in it",
              page.locator("#import-page .import-swap-box").count() == 1 and "swap-input" in focused(page)
              and editor(page).locator(".import-swap").nth(1).get_attribute("aria-expanded") == "true", focused(page))
        type_swap(page, "Abaddon Black")
        check("Enter swaps it: the step now shows CM → Abaddon Black", "CM → Abaddon Black" in lines(page)[1], lines(page)[1])
        check("…and the box closes, the editor stays open, focus back on that Change…",
              page.locator("#import-page .import-swap-box").count() == 0 and editor(page).count() == 1
              and focused(page).endswith("|swap-1"), focused(page))
        check("…the editor row shows the new paint and what was pasted",
              swap_names(page)[1] == "Abaddon Black (pasted as “CM”)", swap_names(page))
        check("…says what it did, with Undo", "CM changed to Abaddon Black" in toast(page), toast(page))
        check("…the mix ratio is unchanged (2:1)", "mix 2:1" in lines(page)[1]
              and page.input_value("#import-page .import-step-editor input[data-import-focus='ratio']") == "2:1", lines(page)[1])
        check("…only this step: CM is still asked about once, for the Eyes step",
              asks(page) == ["“CM”"] and "CM?" in lines(page)[3],
              [asks(page), lines(page)[3]])
        check("…and Save still waits for that one", page.is_disabled("#import-save") and "Pick 1 more paint" in save_text(page), save_text(page))

        undo(page)
        check("Undo: CM? is back in the step, and asked about twice again",
              "CM?" in lines(page)[1] and asks(page) == ["“CM” (2 times)"], [lines(page)[1], asks(page)])
        check("Undo: the editor row shows CM? again", swap_names(page) == ["Mephiston Red", "CM?"], swap_names(page))

        # --- 3. Swap both CMs: the question goes, Save is ready, "Do you own these?" updates ---
        change(page, 1)
        type_swap(page, "Abaddon Black", how="click")
        check("Use button works the same as Enter", "CM → Abaddon Black" in lines(page)[1], lines(page)[1])
        open_editor(page, 3)
        check("opening another step's ✎ closes the first", editor(page).count() == 1 and swap_names(page) == ["CM?"], swap_names(page))
        change(page, 0)
        type_swap(page, "Zzyzx Glow")
        check("a name it doesn't know becomes a new paint, as typed", "CM → Zzyzx Glow (new)" in lines(page)[3], lines(page)[3])
        check("no paints left to check: the card goes and Save is ready",
              page.locator("#import-page .import-check").count() == 0 and not page.is_disabled("#import-save")
              and save_text(page) == "Save 2 recipes", save_text(page))
        labels = own_labels(page)
        check("\"Do you own these?\" lists the new paints (and no CM)",
              any("Zzyzx Glow" in l for l in labels) and any("Abaddon Black" in l for l in labels)
              and not any(l.endswith("CM") or "Contrast Medium" in l for l in labels), labels)

        # --- 4. Swapping a paint it was sure about; same paint; Cancel and Esc ---
        open_editor(page, 0)
        change(page, 0)
        type_swap(page, "nuln")
        check("a sure paint can be swapped, matched like Other… (nuln = Nuln Oil)",
              "Mephiston Red → Nuln Oil" in lines(page)[0], lines(page)[0])
        check("…and the step's Auto technique follows the new paint", lines(page)[0].startswith("Wash (auto)"), lines(page)[0])
        change(page, 0)
        type_swap(page, "Nuln Oil")
        check("swapping to the same paint changes nothing and says so",
              "already that paint" in toast(page) and "Mephiston Red → Nuln Oil" in lines(page)[0], toast(page))
        change(page, 0)
        page.fill("#import-page .import-swap-input", "Leadbelcher")
        page.press("#import-page .import-swap-input", "Escape")
        page.wait_for_timeout(50)
        check("Esc in the box closes only the box (the editor stays open)",
              page.locator("#import-page .import-swap-box").count() == 0 and editor(page).count() == 1
              and "Nuln Oil" in lines(page)[0] and focused(page).endswith("|swap-0"), focused(page))
        change(page, 0)
        page.click("#import-page .import-swap-cancel")
        page.wait_for_timeout(50)
        check("Cancel closes the box without changing anything",
              page.locator("#import-page .import-swap-box").count() == 0 and "Nuln Oil" in lines(page)[0])
        change(page, 0)
        page.click("#import-page .import-swap-use")
        page.wait_for_timeout(50)
        check("Use with nothing typed does nothing", page.locator("#import-page .import-swap-box").count() == 1
              and "Nuln Oil" in lines(page)[0])
        page.fill("#import-page .import-swap-input", "sand")
        page.click("#import-page .import-edit-done")
        page.wait_for_timeout(50)
        check("Done uses a name typed in the box, then closes the editor",
              editor(page).count() == 0 and "Mephiston Red → Sand" in lines(page)[0]
              and "import-edit" in focused(page), [lines(page)[0], focused(page)])

        # --- 5. Swaps survive another change's Undo ---
        step_li(page, 2).locator(".import-remove").click()
        page.wait_for_timeout(50)
        undo(page)
        check("swaps are kept through another Undo (leaving a step out, then Undo)",
              "Mephiston Red → Sand" in lines(page)[0] and "CM → Abaddon Black" in lines(page)[1]
              and "CM → Zzyzx Glow" in lines(page)[3], lines(page))
        check("your pasted notes are still unchanged", page.input_value("#import-text") == NOTE)

        # --- 6. Save ---
        page.click("#import-save")
        page.wait_for_timeout(150)
        book = saved_book(page)
        cloak, eyes = recipe_paints(book, "Cloak"), recipe_paints(book, "Eyes")
        check("saved: the swapped paints", cloak and eyes and cloak[0][0] == ["Sand"] and cloak[1][0] == ["Mephiston Red", "Abaddon Black"]
              and eyes[0][0] == ["Zzyzx Glow"], [cloak, eyes])
        check("saved: the mix ratio as pasted (2:1)", cloak and cloak[1][1] == "2:1" and cloak[1][2][0] > cloak[1][2][1], cloak and cloak[1])
        sand = next((x for x in book.get("paints", []) if x["name"] == "Sand"), {})
        check("saved: a basing material typed in the box is saved as a material", sand.get("type") == "material", sand)
        check("saved: a swap doesn't teach the app that CM means that paint",
              "cm" not in (book.get("shorthand") or {}), book.get("shorthand"))

        # --- 7. Answers in "Check N paints" are kept; Undo brings the question back answered ---
        start(page)
        paste(page, NOTE)
        page.locator("#import-page .import-check .chips button", has_text="Contrast Medium").click()
        page.wait_for_timeout(50)
        check("answering CM covers both steps", "CM → Contrast Medium" in lines(page)[1] and "CM → Contrast Medium" in lines(page)[3]
              and not page.is_disabled("#import-save"), lines(page))
        open_editor(page, 3)
        check("an answered paint shows its answer in the editor", swap_names(page) == ["Contrast Medium"], swap_names(page))
        change(page, 0)
        type_swap(page, "Moot Green")
        check("swapping one step leaves your answer for the other",
              "CM → Moot Green" in lines(page)[3] and "CM → Contrast Medium" in lines(page)[1]
              and asks(page) == ["“CM”"] and not page.is_disabled("#import-save"), [lines(page), asks(page)])
        undo(page)
        check("Undo: the question is back to 2 steps, still answered",
              asks(page) == ["“CM” (2 times)"] and "CM → Contrast Medium" in lines(page)[3]
              and not page.is_disabled("#import-save"), [asks(page), lines(page)[3]])

        # --- 8. Read again brings everything back ---
        change(page, 0)
        type_swap(page, "Leadbelcher")
        read_again(page)
        check("Read again: every paint as pasted, CM asked about again",
              lines(page) == start_lines and asks(page) == ["“CM” (2 times)"]
              and editor(page).count() == 0, [lines(page), asks(page)])

        # --- 9. Odd text is shown as plain text ---
        open_editor(page, 0)
        change(page, 0)
        type_swap(page, '<img src=x onerror="window.__hacked=1">')
        check("a name with HTML in it is shown as plain text", page.evaluate("!window.__hacked")
              and page.locator("#import-page .import-steps img, #import-page .import-swap-name img").count() == 0, lines(page)[0])

        # --- 10. Small phone ---
        start(page)
        page.set_viewport_size({"width": 360, "height": 740})
        paste(page, NOTE)
        open_editor(page, 1)
        change(page, 1)
        sizes = page.eval_on_selector_all("#import-page .import-swap, #import-page .import-swap-use, #import-page .import-swap-cancel",
                                          "els => els.map(e => [e.getBoundingClientRect().width, e.getBoundingClientRect().height])")
        check("small phone: Change…, Use and Cancel are big enough to tap (32px)",
              sizes and all(w >= 32 and h >= 32 for w, h in sizes), sizes)
        check("small phone: no sideways scrolling with the box open",
              page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"),
              page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]"))
        os.makedirs(os.path.join(os.path.dirname(__file__), "screenshots"), exist_ok=True)
        step_li(page, 1).screenshot(path=os.path.join(os.path.dirname(__file__), "screenshots", "v18d2b_swap_360.png"))

        check("no page errors", not errors, errors)
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
