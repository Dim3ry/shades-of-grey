"""v75 tests for Minifolio (chunk 5.2: less small print, bigger preview buttons).

What changed:
 Many hints and notes are shorter or gone (see the Updates entry). The paste-recipes preview buttons (the ✕ and ✎ on steps, part
 names and notes) are 44 px, and the ones that name a paint are read together with the step's own text.

Checks:
1. Paste-recipes preview: every ✕ and ✎ is 44 px or more, at 390 px and 360 px, with no sideways scroll.
2. Those buttons are named from the step's text (the paint name is in the name), and so are the Change... button and its box.
3. The Counting visits and Shop links notes say just On or Off; the Backups card has no share hint.
4. The Dashboard graph note for undated units is short.
5. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright
from launch_helpers import open_settings

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

NOTE = """Test scheme

Cloak:
Note: thin your paints
Mephiston Red
2:1 Mephiston Red:Abaddon Black"""

UNDATED = {"id": 1, "name": "Old unit", "hobby": "40K", "faction": "Orks", "stage": 2, "count": 2}

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        print("\n--- 1 and 2. Paste-recipes preview buttons ---")
        load(page, units=[])
        page.evaluate("startImport()")
        page.fill("#import-text", NOTE)
        page.click("#import-page button.primary-button")
        page.wait_for_timeout(150)
        sel = "#import-page .import-remove, #import-page .import-edit, #import-page .import-drop-part, #import-page .import-drop-note"
        for width, scheme in ((390, "dark"), (390, "light"), (360, "dark"), (360, "light")):
            page.set_viewport_size({"width": width, "height": 844})
            page.emulate_media(color_scheme=scheme)
            page.wait_for_timeout(100)
            sizes = page.eval_on_selector_all(sel, "els => els.map(e => { const r = e.getBoundingClientRect(); return Math.min(r.width, r.height); })")
            check(f"{width} px {scheme}: every preview button is 44 px or more, no sideways scroll",
                  len(sizes) >= 6 and min(sizes) >= 44 and no_sideways(page), sizes)
        page.set_viewport_size({"width": 390, "height": 844})
        check("a ✕ is named with its step's paint", page.get_by_role("button", name=re.compile(r"Leave out.*Mephiston Red")).count() >= 1)
        check("a ✎ is named with its step's paint", page.get_by_role("button", name=re.compile(r"Change.*Mephiston Red")).count() >= 1)
        page.locator("#import-page .import-edit").first.click()
        page.wait_for_timeout(150)
        page.locator("#import-page .import-swap").first.click()
        page.wait_for_timeout(150)
        check("the Change... button names its paint", page.get_by_role("button", name=re.compile(r"^Change.*Mephiston Red")).count() >= 1)
        check("the new-paint box is named by its visible label", page.get_by_role("textbox", name=re.compile(r"Change .* to")).count() == 1)
        page.locator("#import-page .import-edit").last.click()
        page.wait_for_timeout(150)
        check("the mix ratio box is named with its paints",
              page.get_by_role("textbox", name=re.compile(r"Mix ratio.*Abaddon Black")).count() == 1)

        print("\n--- 3. Settings notes ---")
        load(page, units=[])
        open_settings(page)
        page.wait_for_timeout(150)
        check("Counting visits note is just On or Off", page.text_content("#counting-note").strip() in ("On.", "Off."), page.text_content("#counting-note"))
        check("Shop links note is just On or Off", page.text_content("#shoplinks-note").strip() in ("On.", "Off."), page.text_content("#shoplinks-note"))
        check("the Backups card has no share hint", page.locator("#share-hint").count() == 0)

        print("\n--- 4. Dashboard graph note ---")
        load(page, units=[UNDATED])
        page.click('nav button[data-tab="dashboard"]')
        page.wait_for_timeout(200)
        note = page.text_content("#history-note").strip()
        check("the undated note is short and has no version number", 0 < len(note) < 60 and "(v4)" not in note, note)

        print("\n--- 5. Errors ---")
        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
